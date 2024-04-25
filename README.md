# AnomalousJet

## Setup
This code requires `python` and the `coffea` package ([link](https://coffeateam.github.io/coffea/)).<br>
To setup `python` and `coffea`, follow the steps here (tested on CERN lxplus):

Setup python (steps copied from [here](https://abpcomputing.web.cern.ch/guides/python_inst/)).
Download and install the most recent version of Miniforge: 
```
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-latest-Linux-x86_64.sh  
```
Activate miniforge
```
source /home/user/XXX/miniforge3/bin/activate
```

Install `coffea` into a separate environment.
```
conda install -n coffea coffea
```

Code may require additional python packages, install them via
```
conda install -n coffea [PACKAGE_NAME]
```
   
After each login, activate the miniforge installation and the coffea environment:
```
source /home/user/XXX/miniforge3/bin/activate
conda activate coffea
```

## Example Files
The code aims to dump the inputs for an anomalous jet search and save them to parquet files. These files can be opened with the python package `awkward`. An example file can be found [here](AnomalousJet/test_QCD.parquet).<br>
Information from the file can be loaded like demonstrated in the following:
```
import awkward as ak
test = ak.from_parquet("test_QCD.parquet")
print(test.fields) # to get all properties stored in the array
feature = test.rho
```
The awkward arrays can also coverted to NumPy arrays:
```
print(feature)
array = ak.to_numpy(feature)
```

## Training code
The QUAK training repository can be found [here](https://github.com/SangeonPark/QUAK/).
