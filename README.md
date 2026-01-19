# GV Data Visualization

Visualization of meter data sampled via GasViewer protocol.



## Requirements

Interpreter: Python >= 3.10.

Packages: listed in [`requirements.txt`](requirements.txt), can be installed via
```sh
pip install -r requirements.txt
```


## Usage

Usage:
```sh
python plot_gv_sampling.py [-h] -d GV_SAMPLING_DIR_PATH [-o]
```
Options:
- `-h`, `--help`: show this help message and exit
- `-d GV_SAMPLING_DIR_PATH`, `--gv-sampling-dir-path GV_SAMPLING_DIR_PATH` GasViewer data directory path
- `-o`, `--open` open the plot in the browser (default: False)

Example:
```sh
python plot_gv_sampling.py -d ./gv_sampling_results -o
```
