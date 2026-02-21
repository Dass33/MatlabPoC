# NSM Data Processing

mh, v1.0, 2026_02_19

### Overview

This project develops Matlab tools for data processing in Nanofluidic Scattering Microscopy (NSM) [Spackova-Moberg-etal_2022].

### Software Requirements

Matlab with Image processing and Curve fitting toolbox is required. Version R2024b has been used in the development.

### Instructions for Use

The main script for data processing is `analyzeExperiment.m` m-file. This script processes set of raw kymograph data from a selected folder and export multiple files, namely: a table with analysis as a `Analysis.mat`  file,  `Setting.json`  file containing the values of processing parameters.

Several variables in `analyzeExperiment.m` needs to be set. Variable controls wether to load processing parameters from some `Setting.json`  file. Paths to the project folder, folder to the raw data, and folder to the processing parameters need to be selected by setting variables `projectFolder`, `experimentFolder`,  and `settingFile` . Name of export folder is specified by variable `analysisName`.

The basic functionality is demonstrated on demo data placed in the folder `data\demo_data`. File paths are set to this demo data by default.

### Licence

### References

[Spackova-Moberg-etal_2022], Label-Free Nanofluidic Scattering Microscopy of Size and Mass of Single Diffusing Molecules and Nanoparticles, Nature Methods, https://www.nature.com/articles/s41592-022-01491-6
