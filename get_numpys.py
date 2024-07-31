import awkward as ak
import sys
import numpy as np
import os

filepath = sys.argv[1]
#outpath = sys.argv[2]
o = "/uscmst1b_scratch/lpc1/3DayLifetime/creissel/arrays/"
if not os.path.exists(o):
    os.makedirs(o)

datasets = [
    #"GluGluHToBB",
    #"QCD_HT1000to1500",
    #"QCD_HT1500to2000",
    #"QCD_HT2000toInf",
    #"QCD_HT700to1000",
    #"TTTo2L2Nu",
    "TTToHadronic",
    "TTToSemiLeptonic",
    "ZJetsToQQ_HT-600to800",
    "ZJetsToQQ_HT-800toInf",
    ]


for dirname in datasets:
    print("Loading parquet for dataset "+ dirname +  " ...")

    outpath = o+dirname
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    with open("log/"+dirname+".log", "r") as f:
        files = f.read().splitlines()

    for nfile, f in enumerate(files):
        d = ak.from_parquet(filepath+"/"+dirname +"/"+f)
        
        # make per-candidate array
        pf_feats = ["deta","dphi","dr","lpt","lptf","f1","f2","pdgId"]
        d_pf = ak.zip({i: getattr(d,i) for i in pf_feats})
        pf_arr = ak.to_numpy(d_pf)

        # make per-jet array
        jet_feats = ["rho","tau21","tau32","tau43","sqrttau21_tau1","nConst","btag"]
        d_jet = ak.zip({i: getattr(d,i) for i in jet_feats})
        jet_arr = ak.to_numpy(d_jet)

        np.savez_compressed(outpath+"/"+f.split(".")[0]+".npz", jet=jet_arr, pf=pf_arr)
