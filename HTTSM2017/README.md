# Instructions on how to run 1D limits (05.Jul.2018)
===============

These instructions run the observed limit. For the expected, one needs to add -t -1 for every combine command. 
```
cd bin
MorphingSM2017 --output_folder="TestJune26" --postfix="-2D" --control_region=0 --manual_rebin=false --real_data=false --mm_fit=false --ttbar_fit=false
sh _do_mc_Stat.sh  output/TestJune26
cd output/TestJune26
combineTool.py -M T2W -i {cmb,tt}/* -o workspace.root --parallel 18
cp ../../../scripts/texName.json .
cp ../../../scripts/plot1DScan.py .
combine -M MultiDimFit -m 125 --algo grid --points 101 --rMin 0 --rMax 10 cmb/125/workspace.root -n nominal
combine -M MultiDimFit --algo none --rMin 0 --rMax 10 cmb/125/workspace.root -m 125 -n bestfit --saveWorkspace
combine -M MultiDimFit --algo grid --points 101 --rMin 0 --rMax 10 -m 125 -n stat higgsCombinebestfit.MultiDimFit.mH125.root --snapshotName MultiDimFit --freezeParameters all --fastScan
python ./plot1DScan.py --main higgsCombinenominal.MultiDimFit.mH125.root --POI r -o cms_output_freeze_All --others 'higgsCombinestat.MultiDimFit.mH125.root:Freeze all:2' --breakdown syst,stat
```

