import awkward as ak
from coffea.nanoevents import NanoEventsFactory, NanoAODSchema
from coffea.nanoevents.schemas import PFNanoAODSchema
import numpy as np
from coffea.analysis_tools import Weights, PackedSelection
from coffea import util

from coffea import processor
import dask
import dask_awkward as dak
import correctionlib
import json

lumi = 4148.0

# function for msoftdrop correction -> TODO: move to separate correction file
msdcorr = {}
msdcorr['2017'] = correctionlib.CorrectionSet.from_file('msdcorr_2017.json')
def corrected_msoftdrop(fatjets, year):
    msdraw = np.sqrt(
        np.maximum(
            0.0,
            (fatjets.subjets * (1 - fatjets.subjets.rawFactor)).sum().mass2,
        )
    )
    msoftdrop = fatjets.msoftdrop
    msdfjcorr = msdraw / (1 - fatjets.rawFactor)

    if year=='2016APV': year='2016'
    corr = msdcorr[year]["msdfjcorr"].evaluate(
        (msdfjcorr / fatjets.pt),
        (np.log(fatjets.pt)),
        (fatjets.eta),
    )

    corrected_mass = msdfjcorr * corr
    return corrected_mass

# main processor
class MyProcessor(processor.ProcessorABC):
    def __init__(self):
        pass

    def process(self, events):
        dataset = events.metadata["dataset"]
        XS = events.metadata["XS"]

        # Event filters
        filters = (events.Flag.goodVertices & events.Flag.globalSuperTightHalo2016Filter & events.Flag.HBHENoiseFilter & events.Flag.HBHENoiseIsoFilter & events.Flag.EcalDeadCellTriggerPrimitiveFilter & events.Flag.BadPFMuonFilter & events.Flag.BadPFMuonDzFilter & events.Flag.eeBadScFilter & events.Flag.ecalBadCalibFilter)
        # Event triggers
        triggers = (events.HLT.PFHT1050 | events.HLT.PFJet500 | events.HLT.AK8PFJet500 | events.HLT.AK8PFHT800_TrimMass50 | events.HLT.AK8PFJet400_TrimMass30 | events.HLT.AK8PFJet420_TrimMass30) 


        # Basic lepton selection
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


        # Basic jet selection
        fatjets = events.FatJet
        fatjets['msdcorr'] = corrected_msoftdrop(fatjets, '2017')
        fatjets = fatjets[(fatjets.pt > 600) &
                (np.abs(fatjets.eta) < 2.5) &
                (fatjets.msdcorr > 40) &
                (2*np.log(fatjets.msdcorr/fatjets.pt) >-8) &
                (2*np.log(fatjets.msdcorr/fatjets.pt) <-1) &
                (fatjets.jetId>0)]
        candidatejet = ak.firsts(fatjets)

        jets = events.Jet
        jets = jets[(jets.pt > 30) &
                (np.abs(jets.eta) < 2.5) &
                (jets.jetId > 0)] # check what is happening with the puID in Run3?

        opp_hemisphere_jets = jets[(jets.delta_phi(candidatejet) > np.pi/2.)]
        idx = ak.argsort(opp_hemisphere_jets.btagDeepFlavB, axis=1, ascending=False)
        opp_hemisphere_btag = ak.fill_none(ak.firsts(opp_hemisphere_jets[idx].btagDeepFlavB),0.0)

        # Weights
        weights = {}
        weights["genweight"] = events.genWeight

        # Event selection
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
        #print(SR)
        cutflow = SR.cutflow("Filter", "Triggers", ">0 Fatjets", "Veto Leptons", "Anti-top cuts")
        #cutflow.print()
     
        # Training inputs for whatever downstream ML task
        def make_inputs(fatjets, events):

            def pad(arr):
                return ak.fill_none(
                    ak.pad_none(arr, 100, axis=1, clip=True),
                    0.0,
                )
            
            inputs = ak.zip(
                    {
                    # per-jet features
                        "rho": np.log(fatjets.msdcorr/fatjets.pt),
                        "tau21": fatjets.tau2/fatjets.tau1,
                        "tau32": fatjets.tau3/fatjets.tau2,
                        "tau43": fatjets.tau4/fatjets.tau3,
                        "sqrttau21_tau1": np.sqrt(fatjets.tau2/fatjets.tau1)/fatjets.tau1,
                        "nConst": fatjets.nConstituents,
                        "btag": fatjets.particleNetMD_Xbb, #particleNet_HbbvsQCD
                        "msdcorr": fatjets.msdcorr, #particleNet_HbbvsQCD
                    # per-constituent features
                        "deta": pad(fatjets.eta - fatjets.constituents.pf.eta),
                        "dphi": pad(fatjets.delta_phi(fatjets.constituents.pf)),
                        "dr": pad(fatjets.delta_r(fatjets.constituents.pf)),
                        "lpt": pad(np.log(fatjets.constituents.pf.pt)),
                        "lptf": pad(np.log(fatjets.constituents.pf.pt / fatjets.pt)),
                        "f1": pad(np.log(np.abs(fatjets.constituents.pf.d0) + 1)),
                        "f2": pad(np.log(np.abs(fatjets.constituents.pf.dz) + 1)), 
                        "pdgId": pad(fatjets.constituents.pf.pdgId),
                    # event identifiation & monitoring
                        "event": events['event'],
                        "run": events['run'],
                        "luminosityBlock": events['luminosityBlock'],
                        "weight": events.genWeight, 
                    }, depth_limit=1)
            return inputs


        cut = SR.all()
        # apply event selection & consider only highest pt FatJet
        selc_fatjets = fatjets[cut][:,0] # SR events (w/o btag) and highest pt jet
        selc_events = events[cut]
        inputs = make_inputs(selc_fatjets, selc_events)
    
        # Save all information needed for NPLM/ Monitoring
        sumw = ak.sum(events.genWeight)
        sumw_selc = ak.sum(events[cut].genWeight)
        nevents = cutflow.result().nevcutflow[0]
        nevents_selc = cutflow.result().nevcutflow[-1]

        
        return {      
                #"entries": ak.num(events[SR.all()],axis=0),
                #"genSumW": sumw,
                #"weights": weights["genweight"], 
                #"cutflow": cutflow,
                "inputs": inputs,
                "log": {'nevents':nevents, 'nevents_selc':nevents_selc, 'sumw':sumw, 'sumw_selc':sumw_selc},
                }

    def postprocess(self,accumulator):
        pass
        #return accumulator



# Run the processor
if __name__ == '__main__':

    #fname = "file://VectorZPrimeToQQ_M200_pT300_test_2017.root"
    fname = "file://QCD_test_2017.root"

    events = NanoEventsFactory.from_root(
        {fname: "Events"},
        #schemaclass=NanoAODSchema,
        schemaclass=PFNanoAODSchema,
        #metadata={"dataset": "Zprime"},
        metadata={"dataset": "QCD", "XS": 1118.0}, # XS taken from https://github.com/jeffkrupa/zprime-bamboo/blob/main/samples_2017_jet.yml
    ).events()

    p = MyProcessor()
    out = p.process(events)
    to_compute = dak.to_parquet(out["inputs"],"QCD",compute=False)
    dask.compute(to_compute)
    log = {}
    for l in out['log'].keys():
        log[l] = float(out['log'][l].compute())
    with open('QCD/monitor.json','w') as outfile:
        json.dump(log, outfile)
    import pdb
    pdb.set_trace()

