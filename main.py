import awkward as ak
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema
from coffea.nanoevents.schemas import PFNanoAODSchema
import numpy as np
from coffea.ml_tools.torch_wrapper import torch_wrapper

from coffea import processor
import dask

class MyProcessor(processor.ProcessorABC):
    def __init__(self):
        pass

    def process(self, events):
        dataset = events.metadata["dataset"]

        # event filters
        filters = (events.Flag.goodVertices & events.Flag.globalSuperTightHalo2016Filter & events.Flag.HBHENoiseFilter & events.Flag.HBHENoiseIsoFilter & events.Flag.EcalDeadCellTriggerPrimitiveFilter & events.Flag.BadPFMuonFilter & events.Flag.BadPFMuonDzFilter & events.Flag.eeBadScFilter & events.Flag.ecalBadCalibFilter)
        # event triggers
        triggers = (events.HLT.PFHT1050 | events.HLT.PFJet500 | events.HLT.AK8PFJet500 | events.HLT.AK8PFHT800_TrimMass50 | events.HLT.AK8PFJet400_TrimMass30 | events.HLT.AK8PFJet420_TrimMass30) 


        # basic lepton selection
        muons = events.Muon
        loose_muons = muons[(muons.pt > 10.) &
                (np.abs(muons.eta) < 2.4) &
                (np.abs(muons.pfRelIso04_all) < 0.05)]

        electrons = events.Electron
        electrons = electrons[(electrons.pt > 10.) &
                (electrons.cutBased >= 1.) &
                (np.abs(electrons.eta) < 2.5)]

        taus = events.Tau
        taus = taus[(taus.pt > 20.) &
                taus.decayMode >=0 &
                (np.abs(taus.eta) < 2.3) &
                (taus.idDeepTau2017v2p1VSe >=2) &
                (taus.idDeepTau2017v2p1VSjet >= 16) &
                (taus.idDeepTau2017v2p1VSmu >= 8)]


        # basic jet selection
        fatjets = events.FatJet
        fatjets = fatjets[(fatjets.pt > 400) &
                (np.abs(fatjets.eta) < 2.5) &
                (fatjets.msoftdrop > 40) &
                (2*np.log(fatjets.msoftdrop/fatjets.pt) >-8) &
                (2*np.log(fatjets.msoftdrop/fatjets.pt) <-1) &
                (fatjets.jetId>0)]
        candidatejet = ak.firsts(fatjets)

        jets = events.Jet
        jets = jets[(jets.pt > 30) &
                (np.abs(jets.eta) < 2.5) &
                (jets.jetId > 0)] # check what is happening with the puID in Run3?

        #bjets = jets[]
        opp_hemisphere_jets = jets[(jets.delta_phi(candidatejet) > np.pi/2.)]
        idx = ak.argsort(opp_hemisphere_jets.btagDeepFlavB, axis=1, ascending=False)
        opp_hemisphere_btag = ak.fill_none(ak.firsts(opp_hemisphere_jets[idx].btagDeepFlavB),0.0)

        # event selection
        from coffea.analysis_tools import PackedSelection
        SR = PackedSelection()
        SR.add_multiple(
                {
                    "Filter": filters,
                    "Triggers": triggers,
                    ">0 Fatjets": (ak.num(fatjets)>0),
                    "Veto Leptons": ((ak.num(loose_muons)==0) & (ak.num(electrons)==0) & (ak.num(taus)==0)),
                    "Anti-top cuts": ((events.MET.pt < 140.) & (ak.num(jets)<6)) & (opp_hemisphere_btag<0.3040),
                }
        )
        print(SR)
        cutflow = SR.cutflow("Filter", "Triggers", ">0 Fatjets", "Veto Leptons", "Anti-top cuts")
        cutflow.print()
       
        def make_inputs(fatjets):

            def pad(arr):
                return ak.fill_none(
                    ak.pad_none(arr, 100, axis=1, clip=True),
                    0.0,
                )
            
            inputs = ak.zip(
                    {
                    # per-jet features
                        "rho": np.log(fatjets.msoftdrop/fatjets.pt),
                        "tau21": fatjets.tau2/fatjets.tau1,
                        "tau32": fatjets.tau3/fatjets.tau2,
                        "tau43": fatjets.tau4/fatjets.tau3,
                        "sqrttau21_tau1": np.sqrt(fatjets.tau2/fatjets.tau1)/fatjets.tau1,
                        "nConst": fatjets.nConstituents,
                        "btag": fatjets.particleNetMD_Xbb, #particleNet_HbbvsQCD
                    # per-constituent features
                        "deta": pad(fatjets.eta - fatjets.constituents.pf.eta),
                        "dphi": pad(fatjets.delta_phi(fatjets.constituents.pf)),
                        "dr": pad(fatjets.delta_r(fatjets.constituents.pf)),
                        "lpt": pad(np.log(fatjets.constituents.pf.pt)),
                        "lptf": pad(np.log(fatjets.constituents.pf.pt / fatjets.pt)),
                        "f1": pad(np.log(np.abs(fatjets.constituents.pf.d0) + 1)),
                        "f2": pad(np.log(np.abs(fatjets.constituents.pf.dz) + 1)), 
                    }, depth_limit=1)
            return inputs


        # apply event selection & consider only highest pt FatJet
        selc_fatjets = fatjets[SR.all()][:,0] # SR events (w/o btag) and highest pt jet
        inputs = make_inputs(selc_fatjets)
       
        ak.to_parquet(inputs, dataset)
        return {
            dataset: {
                "entries": ak.num(events[SR.all()],axis=0),
                "inputs": inputs,
                }
            }

    def postprocess(self,accumulator):
        pass



# Run the processor
if __name__ == '__main__':

    #fname = "file://VectorZPrimeToQQ_M200_pT300_test_2017.root"
    fname = "file://QCD_test_2017.root"

    events = NanoEventsFactory.from_root(
        {fname: "Events"},
        #schemaclass=NanoAODSchema,
        schemaclass=PFNanoAODSchema,
        #metadata={"dataset": "Zprime"},
        metadata={"dataset": "QCD"},
    ).events()

    p = MyProcessor()
    out = p.process(events)
    (computed, ) = dask.compute(out)

    

    import pdb
    pdb.set_trace()
