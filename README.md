# AnomalousJet

## Setup code
This code requires `python` and the `coffea` package ([link](https://coffeateam.github.io/coffea/)).
To setup `python` and `coffea`, follow the steps here (tested on CERN lxplus):

1. Setup python (steps copied from [here](https://abpcomputing.web.cern.ch/guides/python_inst/) .
   Download and install the most recent version of Miniforge: 
   ```
   wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
   bash Miniforge3-latest-Linux-x86_64.sh
   
   ```
   Activate miniforge
   ```
   source /home/user/XXX/miniforge3/bin/activate
   ```

2. Install `coffea` into separate environment
   ```
   conda install -n coffea coffea
   ```

3. Code may require additional python pagackages, install them via
   ```
   conda install -n coffea [PACKAGE_NAME]
   ```
   
After each login, activate the miniforge installation and the coffea environment:
```
source /home/user/XXX/miniforge3/bin/activate
conda activate coffea
```
    
