import os, sys
import subprocess
import uproot
import dask

#from coffea import processor, util, hist
from coffea import processor, util
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema, PFNanoAODSchema
from coffea.dataset_tools import (
    apply_to_fileset,
    apply_to_dataset,
    max_chunks,
    preprocess,
)

# Add path so the script sees the modules in parent directory
sys.path.append('/srv')

#Import processor
from main import MyProcessor

from distributed import Client
from lpcjobqueue import LPCCondorCluster
from dask.distributed import performance_report
from dask_jobqueue import HTCondorCluster, SLURMCluster

from datetime import datetime

env_extra = [
    f"export PYTHONPATH=$PYTHONPATH:{os.getcwd()}",
]

cluster = LPCCondorCluster(
    shared_temp_directory="/tmp",
#    transfer_input_files=["boostedhiggs"],
    ship_env=True,
    memory="10GB"
#    image="coffeateam/coffea-dask:0.7.11-fastjet-3.3.4.0rc9-ga05a1f8",
)

#out_path = "/eos/uscms/store/user/creissel/AnomalousJet/test/"
out_path = "/uscms/homes/c/creissel/AnomalousJet/output/"
os.system('mkdir -p  %s' %out_path)

cluster.adapt(minimum=1, maximum=250)
with Client(cluster) as client:
    
    print(datetime.now())
    print("Waiting for at least one worker...")  # noqa
    client.wait_for_workers(1)
    print(datetime.now())

    with performance_report(filename="dask-report.html"):
       
        fileset = {
                "QCD": {
                    "files": {"root://cmsxrootd.fnal.gov//store/user/lpcpfnano/cmantill/v2_3/2017/QCD/QCD_HT1000to1500_TuneCP5_PSWeights_13TeV-madgraph-pythia8/QCD_HT1000to1500/220808_164439/0000/nano_mc2017_1-1.root" : "Events"},
                    "metadata" : {"XS": 1118.0}, # XS taken from https://github.com/jeffkrupa/zprime-bamboo/blob/main/samples_2017_jet.yml
                    }
        }


        outfile = 'test_dask_{}.coffea'.format("QCD")

        if os.path.isfile(outfile):
            print("File " + outfile + " already exists. Skipping.")
        else:
            print("Begin running " + outfile)
            print(datetime.now())

            #RUN MAIN PROCESSOR
            p = MyProcessor()

            dataset_runnable, dataset_updated = preprocess(
                fileset,
                align_clusters=False,
                step_size=100_000,
                files_per_batch=1,
                skip_bad_files=True,
                save_form=False,
            )

            to_compute = apply_to_fileset(
                            MyProcessor(),
                            max_chunks(dataset_runnable, 300),
                            schemaclass=PFNanoAODSchema,
                       )
            (out,) = dask.compute(to_compute)
            print(out)

            #Save output files
            util.save(out, outfile)
            print("saved " + outfile)
            print(datetime.now())
