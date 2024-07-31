import os, sys
import subprocess
import uproot
import dask
import json
import awkward as ak

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
import dask_awkward as dak

from datetime import datetime

env_extra = [
    f"export PYTHONPATH=$PYTHONPATH:{os.getcwd()}",
]

cluster = LPCCondorCluster(
    shared_temp_directory="/tmp",
    ship_env=True,
    memory="10GB"
#    image="coffeateam/coffea-dask:0.7.11-fastjet-3.3.4.0rc9-ga05a1f8",
)

cluster.adapt(minimum=1, maximum=100)
with Client(cluster) as client:

    client.restart()
    
    print(datetime.now())
    print("Waiting for at least one worker...")  # noqa
    client.wait_for_workers(1)
    print(datetime.now())

    with performance_report(filename="dask-report.html"):
      
        json_file = sys.argv[1]
        dataset = sys.argv[2]
        with open(json_file, 'r') as f:
            fileset = json.load(f)

        #fileset = {
        #        "QCD": {
        #            "files": {"root://cmsxrootd.fnal.gov//store/user/lpcpfnano/cmantill/v2_3/2017/QCD/QCD_HT1000to1500_TuneCP5_PSWeights_13TeV-madgraph-pythia8/QCD_HT1000to1500/220808_164439/0000/nano_mc2017_1-1.root" : "Events"},
        #            "metadata" : {"XS": 1118.0}, # XS taken from https://github.com/jeffkrupa/zprime-bamboo/blob/main/samples_2017_jet.yml
        #            }
        #}

        print("Begin running ")
        print(datetime.now())

        uproot.open.defaults["xrootd_handler"] = uproot.source.xrootd.MultithreadedXRootDSource

        #RUN MAIN PROCESSOR
        p = MyProcessor()

        dataset_runnable, dataset_updated = preprocess(
            fileset,
            align_clusters=False,
            #step_size=100_000,
            step_size=20_000, # needs to be adopted due to uproot issue
            files_per_batch=1,
            skip_bad_files=True,
            save_form=False,
            uproot_options={"allow_read_errors_with_report": True},
        )

        to_compute = apply_to_fileset(
                        MyProcessor(),
                        max_chunks(dataset_runnable, 300),
                        schemaclass=PFNanoAODSchema,
                   )
        
        #Save output files
        dak.to_parquet(to_compute[dataset]['inputs'],"root://cmseos.fnal.gov//store/user/creissel/AnomalousJet/v1_240726/{}/".format(dataset))
        print("saved all files")
        print(datetime.now())
        
        #Save monitor files
        log = {}
        for l in to_compute[dataset]['log'].keys():
            log[l] = float(to_compute[dataset]['log'][l].compute())
        with open('monitor_{}.json'.format(dataset),'w') as outfile:
            json.dump(log, outfile)
        print("saved monitor dir")
        print(datetime.now())
