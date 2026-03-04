/// Flat row-major kymograph matrix: element (t, x) lives at index t * nx + x.
pub struct KymoMatrix {
    pub data: Vec<f64>,
    pub nt: usize,
    pub nx: usize,
}

impl KymoMatrix {
    #[inline(always)]
    pub fn get(&self, t: usize, x: usize) -> f64 {
        self.data[t * self.nx + x]
    }

    #[inline(always)]
    pub fn row(&self, t: usize) -> &[f64] {
        &self.data[t * self.nx..(t + 1) * self.nx]
    }
}
