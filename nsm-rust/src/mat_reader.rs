/// MATLAB v7.3 (.mat HDF5) file reader.
///
/// Layout expected:
///   /collection/iOC               float64 1×N
///   /collection/STDiOC            float64 1×N
///   /collection/D                 float64 1×N
///   /collection/velocity          float64 1×N
///   /collection/N                 float64 1×N
///   /collection/positionRefined   cell (HDF5 obj-ref array) → each ref → float64 vec
///   /collection/iOCprofile        cell (HDF5 obj-ref array) → each ref → float64 vec
///   /collection/timeFrame         cell (HDF5 obj-ref array) → each ref → float64 vec
///   /collection/ExperimentTimeStamp cell → each ref → uint16 vec (UTF-16LE string)

use std::path::Path;
use std::ffi::CString;

use hdf5::File as Hdf5File;
#[allow(deprecated)]
use hdf5_sys::{
    h5d::{H5Dclose, H5Dget_space, H5Dopen2, H5Dread},
    h5p::H5P_DEFAULT,
    h5r::{H5Rdereference1, H5R_type_t},
    h5s::{H5Sclose, H5Sget_simple_extent_npoints, H5S_ALL},
    h5t::{H5T_NATIVE_DOUBLE, H5T_NATIVE_USHORT, H5T_STD_REF_OBJ},
};

use crate::models::Collection;

pub fn load_collection(mat_path: &Path) -> anyhow::Result<Collection> {
    let file  = Hdf5File::open(mat_path)?;
    let group = file.group("collection")?;

    let ioc      = read_flat_f64(&group, "iOC")?;
    let std_ioc  = read_flat_f64(&group, "STDiOC")?;
    let d        = read_flat_f64(&group, "D")?;
    let velocity = read_flat_f64(&group, "velocity")?;
    let n        = read_flat_f64(&group, "N")?;

    let file_id  = file.id();
    let group_id = group.id();

    let position_refined = unsafe { read_cell_f64(file_id, group_id, "positionRefined")? };
    let ioc_profile      = unsafe { read_cell_f64(file_id, group_id, "iOCprofile")? };
    let time_frame       = unsafe { read_cell_f64(file_id, group_id, "timeFrame")? };

    let experiment_time_stamp = unsafe {
        read_cell_strings(file_id, group_id, "ExperimentTimeStamp")
            .unwrap_or_else(|_| vec!["unknown".into(); ioc.len()])
    };

    let position_start: Vec<f64> = position_refined
        .iter()
        .map(|v| v.iter().cloned().filter(|x| x.is_finite()).fold(f64::INFINITY, f64::min))
        .collect();
    let position_end: Vec<f64> = position_refined
        .iter()
        .map(|v| v.iter().cloned().filter(|x| x.is_finite()).fold(f64::NEG_INFINITY, f64::max))
        .collect();

    Ok(Collection {
        ioc,
        std_ioc,
        d,
        velocity,
        n,
        position_start,
        position_end,
        ioc_profile,
        position_refined,
        time_frame,
        experiment_time_stamp,
    })
}

fn read_flat_f64(group: &hdf5::Group, name: &str) -> anyhow::Result<Vec<f64>> {
    let arr: ndarray::ArrayD<f64> = group.dataset(name)?.read_dyn()?;
    Ok(arr.into_iter().collect())
}

/// Read a MATLAB HDF5 cell array of float64 vectors.
///
/// MATLAB v7.3 cell arrays are stored as datasets of HDF5 object references.
/// Each reference points to a separate dataset containing the actual float64 data.
#[allow(deprecated)]
unsafe fn read_cell_f64(
    file_id: hdf5_sys::h5i::hid_t,
    group_id: hdf5_sys::h5i::hid_t,
    name: &str,
) -> anyhow::Result<Vec<Vec<f64>>> {
    let refs = read_obj_refs(group_id, name)?;
    let mut result = Vec::with_capacity(refs.len());
    for r in &refs {
        let sub_id = H5Rdereference1(file_id, H5R_type_t::H5R_OBJECT, r as *const _ as *const _);
        anyhow::ensure!(sub_id >= 0, "H5Rdereference1 failed for element of {}", name);

        let sub_space = H5Dget_space(sub_id);
        let m = H5Sget_simple_extent_npoints(sub_space) as usize;
        H5Sclose(sub_space);

        let mut data = vec![0.0f64; m];
        H5Dread(
            sub_id,
            *H5T_NATIVE_DOUBLE,
            H5S_ALL,
            H5S_ALL,
            H5P_DEFAULT,
            data.as_mut_ptr() as *mut _,
        );
        H5Dclose(sub_id);
        result.push(data);
    }
    Ok(result)
}

/// Read a MATLAB HDF5 cell array of strings (stored as uint16 / UTF-16LE).
#[allow(deprecated)]
unsafe fn read_cell_strings(
    file_id: hdf5_sys::h5i::hid_t,
    group_id: hdf5_sys::h5i::hid_t,
    name: &str,
) -> anyhow::Result<Vec<String>> {
    let refs = read_obj_refs(group_id, name)?;
    let mut result = Vec::with_capacity(refs.len());
    for r in &refs {
        let sub_id = H5Rdereference1(file_id, H5R_type_t::H5R_OBJECT, r as *const _ as *const _);
        anyhow::ensure!(sub_id >= 0, "H5Rdereference1 failed for element of {}", name);

        let sub_space = H5Dget_space(sub_id);
        let m = H5Sget_simple_extent_npoints(sub_space) as usize;
        H5Sclose(sub_space);

        let mut chars = vec![0u16; m];
        H5Dread(
            sub_id,
            *H5T_NATIVE_USHORT,
            H5S_ALL,
            H5S_ALL,
            H5P_DEFAULT,
            chars.as_mut_ptr() as *mut _,
        );
        H5Dclose(sub_id);

        let s = String::from_utf16_lossy(&chars)
            .trim_end_matches('\0')
            .to_owned();
        result.push(s);
    }
    Ok(result)
}

/// Read a cell-array dataset as a flat list of HDF5 object references (u64 = hobj_ref_t).
unsafe fn read_obj_refs(
    group_id: hdf5_sys::h5i::hid_t,
    name: &str,
) -> anyhow::Result<Vec<u64>> {
    let c_name = CString::new(name)?;
    let ds_id = H5Dopen2(group_id, c_name.as_ptr(), H5P_DEFAULT);
    anyhow::ensure!(ds_id >= 0, "Could not open dataset {}", name);

    let space_id = H5Dget_space(ds_id);
    let n = H5Sget_simple_extent_npoints(space_id) as usize;
    H5Sclose(space_id);

    // hobj_ref_t = haddr_t = u64 on all platforms hdf5-sys targets
    let mut refs = vec![0u64; n];
    let ret = H5Dread(
        ds_id,
        *H5T_STD_REF_OBJ,
        H5S_ALL,
        H5S_ALL,
        H5P_DEFAULT,
        refs.as_mut_ptr() as *mut _,
    );
    H5Dclose(ds_id);
    anyhow::ensure!(ret >= 0, "H5Dread failed for {}", name);

    Ok(refs)
}
