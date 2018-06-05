#!/usr/bin/python

import argparse
import os
import sys
from time import localtime, strftime

CMSSW_BASE=os.environ['CMSSW_BASE']
rundir=CMSSW_BASE+'/src/CombineHarvester/MSSMFull2016/'
mdir=strftime("%Y-%m-%d_%Hh%Mm%S", localtime())
physdir=rundir+'output/'+mdir+'/'
symdir='latest/'
basedir=rundir+'output/'+symdir
logfile=basedir+'log.txt'

baselumi=36.9
dryrun=False

def main(argv):


  parser = argparse.ArgumentParser(description='Steer the projection')
  parser.add_argument('mode', nargs='?',                         default=['all'],  choices=['all','datacard','ws','limit','mlfit','np'],     help='Mode of operation')
  parser.add_argument('--lumi',     dest='lumi',     type=float, default=baselumi,                                    help='Luminosity in fb-1')
  parser.add_argument('--nosyst',   dest='syst', nargs='?',      default=True, const=False,                           help='Flag to disable ystematics')
  parser.add_argument('--scale',    dest='scale',                default='none',   choices=[ 'all' , 'bbb', 'none' ], help='Scaling of uncertainties. Options: all, bbb, none')
  parser.add_argument('--loglevel', dest='loglevel', type=int,   default=1,                                           help='Verbosity, 0-essential, 1-most commands, 2-all commands')
  parser.add_argument('--symdir',   dest='symdir',               default='latest/',                                   help='Symlink of output dir (change when running parallel!)')

  args = parser.parse_args()

  lumiscale=round(args.lumi/baselumi,2)
  syst=args.syst
  scale=args.scale
  global loglevel
  loglevel=args.loglevel
  global mdir,physdir
  mdir+='_lumi-'+str(args.lumi)
  if not syst: mdir+='_nosyst'
  if not scale=='none': mdir+='_scale-'+scale
  physdir=rundir+'output/'+mdir+'/'

  global symdir,basedir,logfile
  symdir=args.symdir
  if not symdir.endswith('/'): symdir+='/'
  basedir=rundir+'output/'+symdir
  logfile=basedir+'log.txt'

  if 'all' in args.mode:
    args.mode.remove('all')
    args.mode.append('datacard')
    args.mode.append('ws')
    args.mode.append('limit')
    args.mode.append('np')

  if 'datacard' in args.mode:
    create_output_dir()

  make_print ( ' '.join(sys.argv)+' #COMMAND' , 0)
  make_print ( 'Mode: '+str(args.mode) )
  make_print ( 'Projecting to lumi='+str(args.lumi)+' using a lumi scale of '+str(lumiscale)+' to scale the base lumi of '+str(baselumi) )
  make_print ( 'Applying systematics: '+str(syst) )
  make_print ( 'Scaling uncertainties: '+scale )
  make_print ( 'Writing to '+physdir )

  os.chdir(rundir)
  ############################################## DATACARD
  if 'datacard' in args.mode:
    pcall='MorphingMSSMFull2016 --output_folder='+symdir+' -m MH --manual_rebin=true --real_data=false ' +' >'+basedir+'/log_datacard.txt'         #model-independent
    make_pcall(pcall,'Producing data cards',0)
  ############################################## DATACARD

  ############################################## WORKSPACE
  if 'ws' in args.mode:
    scale_bbb='--X-nuisance-function \'CMS_htt_.*bin_[0-9]+\' \'"expr::lumisyst(\\"1/sqrt(@0)\\",lumi[1])"\''
    scale_all='--X-nuisance-function \'CMS_+\' \'"expr::lumisyst(\\"1/sqrt(@0)\\",lumi[1])"\''  +  ' --X-nuisance-function \'lumi_+\' \'"expr::lumisyst(\\"1/sqrt(@0)\\",lumi[1])"\''

    scaleterm=''
    if scale=='all':
      scaleterm=scale_all
    if scale=='bbb':
      scaleterm=scale_bbb

    pcall='combineTool.py -M T2W -o ws.root -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO \'"map=^.*/ggH.?$:r_ggH[0,0,200]"\' --PO \'"map=^.*/bbH$:r_bbH[0,0,200]"\' '+scaleterm+' -i output/'+symdir+'* &> '+basedir+'/log_ws.txt'
    make_pcall(pcall,'Producing workspace',0)
  ############################################## WORKSPACE

  ############################################## LIMIT
  if 'limit' in args.mode:
    nfreeze='lumi'
    if not syst: nfreeze='all'

    proc=[ 'ggH' , 'bbH' ]
    make_pcall('echo Processes: '+str(proc)+' > '+basedir+'/log_lim.txt','',2)
    for p in proc:
      pcall1='combineTool.py -m "90,100,110,120,130,140,160,180,200,250,350,400,450,500,600,700,800,900,1000,1200,1400,1600,1800,2000,2300,2600,2900,3200" -M Asymptotic -t -1 --parallel 8 --rAbsAcc 0 --rRelAcc 0.0005 --boundlist input/mssm_boundaries-100.json --setPhysicsModelParameters r_ggH=0,r_bbH=0,lumi='+str(lumiscale)+' --freezeNuisances '+nfreeze+' --redefineSignalPOIs r_'+p+' -d output/'+symdir+'cmb/ws.root --there -n ".'+p+'" >> '+basedir+'/log_lim.txt'
      pcall2='combineTool.py -M CollectLimits output/'+symdir+'cmb/higgsCombine.'+p+'*.root --use-dirs -o "output/'+symdir+p+'.json" >> '+basedir+'/log_lim.txt'
      pcall3='python scripts/plotMSSMLimits.py --logy --logx --show exp output/'+symdir+p+'_cmb.json --cms-sub="Preliminary" -o output/'+symdir+p+'_cmb --process=\''+p[0:2]+'#phi\' --title-right="'+str(args.lumi)+' fb^{-1} (13 TeV)" --use-hig-17-020-style >> '+basedir+'/log_lim.txt'
      make_pcall(pcall1,'Producing  limit for '+p,0)
      make_pcall(pcall2,'Collecting limit for '+p,0)
      make_pcall(pcall3,'Plotting   limit for '+p,0)

  ############################################## LIMIT

  ############################################## NP
  smass=700
  os.chdir(basedir)
  if 'mlfit' in args.mode:
    #first the ml fit
    mllog=basedir+'log_mlfit.txt'
    pcall2='combineTool.py -M MaxLikelihoodFit --setPhysicsModelParameters r_ggH=0.0,r_bbH=0.0 --freezeNuisances r_bbH --setPhysicsModelParameterRanges r_ggH=-0.000001,0.000001 --setPhysicsModelParameterRanges r_bbH=-0.000001,0.000001 -d cmb/ws.root --redefineSignalPOIs r_ggH --there -m '+str(smass)+' --boundlist '+rundir+'/input/mssm_boundaries.json --minimizerTolerance 0.1 --minimizerStrategy 0 --name ".res" '+' &>'+mllog
    make_pcall(pcall2)
    make_pcall('mv cmb/mlfit.res.root cmb/mlfit.root','Renaming mlfit output files',2)

    make_print( '########################################################################################' )
    ret=os.popen('root -l cmb/mlfit.root <<<"fit_b->Print();" | grep "covariance matrix quality"').read().rstrip()
    make_print( ret , 0 )
    print_file(ret,mllog,'a')
    make_print( '########################################################################################' )

  if 'np' in args.mode:
#    pcall='python '+CMSSW_BASE+'/src/HiggsAnalysis/CombinedLimit/test/diffNuisances.py cmb/mlfit.root -A -a --stol 0.99 --stol 0.99 --vtol 99. --vtol2 99. -f text --poi r_ggH --histogram nuisance_tests.root &> '+basedir+'/log_np.txt'
    pcall='python '+CMSSW_BASE+'/src/HiggsAnalysis/CombinedLimit/test/diffNuisances.py cmb/mlfit.root -a --stol 0.99 --stol 0.99 --vtol 99. --vtol2 99. -f text --poi r_ggH --histogram nuisance_tests.root &> '+basedir+'/log_np.txt'
    make_pcall(pcall,'Make NP texts... in dir: '+basedir)

    exvar=' --exclude `cat ../combined.txt.cmb | awk {\'print $1\'} | grep _bin_ | head -c -1 | tr \'\\n\' \',\' `'
    idir=basedir+'/cmb/impacts'
    make_dir(idir)
    os.chdir(idir)
    make_print( '### Make NP plots... in dir: '+idir)
    pcall4=[ 
      'combineTool.py -t -1 -M Impacts -d ../ws.root -m '+str(smass)+' --setPhysicsModelParameters r_bbH=0,r_ggH=0 --setPhysicsModelParameterRanges r_ggH=-1.0,1.0 --doInitialFit --robustFit 1 --minimizerAlgoForMinos Minuit2,Migrad --redefineSignalPOIs r_ggH --freezeNuisances r_bbH'+exvar+' &>log1.txt',
      'combineTool.py -t -1 -M Impacts -d ../ws.root -m '+str(smass)+' --setPhysicsModelParameters r_bbH=0,r_ggH=0 --setPhysicsModelParameterRanges r_ggH=-1.0,1.0 --robustFit 1 --doFits --minimizerAlgoForMinos Minuit2,Migrad  --redefineSignalPOIs r_ggH --freezeNuisances r_bbH --allPars --parallel 8'+exvar+' &>log2.txt',
      'combineTool.py -M Impacts -d ../ws.root --allPars --redefineSignalPOIs r_ggH --exclude r_bbH -m '+str(smass)+' -o impacts.json'+exvar+' &>log3.txt',
      'plotImpacts.py -i impacts.json -o impacts --transparent &>log4.txt',
      'cp -p impacts.pdf ../',
      ]
    ll=[1,1,1,1,2]
    for j,p4 in enumerate(pcall4):
      make_pcall(p4,'',ll[j])

    os.chdir(rundir)

  ############################################## NP


#def create_output_dir(webdir):
def create_output_dir():
    if not dryrun: 
        os.system('mkdir -p '+physdir)
        if os.path.islink(basedir.rstrip('/')): os.remove(basedir.rstrip('/'))
        os.symlink(mdir,basedir.rstrip('/')) #symdir
        make_print( '### output dir '+physdir+' and symlink created.' , 0)

        print 'XXXX',physdir,mdir,basedir.rstrip('/')

#        make_dir(webdir.replace(symdir.rstrip('/'),mdir))
#        if os.path.islink(webdir): 
#            os.remove(webdir)
#        os.symlink(mdir,webdir)

def make_dir(d,msg=''):
    if not msg=='':
        make_print( '### '+msg )

    if not os.path.exists(d):
        make_print( ' >> mkdir -p '+d )
        os.makedirs(d)

def make_print(msg,level=1):
    global logf
    if not 'logf' in globals():
        logf = open(logfile, 'a')

    if level <= loglevel:
        print msg

    logf.write(msg+'\n')

def print_file(text,fname,mode='w'):
    f = open(fname, mode)
    f.write(text)
    f.close()

def make_pcall(pcall,msg='',level=1,rep=0):
    if rep==0 and not msg=='': 
        make_print( '### '+msg )
    make_print( ' >> '+pcall.replace(basedir,'') , level )

    if not dryrun: os.system(pcall)

if __name__ == '__main__':
  main(sys.argv[1:])




#combineTool.py -M T2W -o "ws.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO '"map=^.*/ggH.?$:r_ggH[0,0,200]"' --PO '"map=^.*/bbH$:r_bbH[0,0,200]"' -i output/mssm_201017_scale-bbb/* --X-nuisance-function 'CMS_htt_.*bin_[0-9]+' '"expr::lumisyst(\"1/sqrt(@0)\",lumiscale[1])"' &> output/mssm_201017_scale-bbb/log_ws.txt
#combineTool.py -M T2W -o "ws.root" -P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel --PO '"map=^.*/ggH.?$:r_ggH[0,0,200]"' --PO '"map=^.*/bbH$:r_bbH[0,0,200]"' -i output/mssm_201017_scale-all/* --X-nuisance-function 'CMS_+' '"expr::lumisyst(\"1/sqrt(@0)\",lumiscale[1])"' --X-nuisance-function 'lumi_+' '"expr::lumisyst(\"1/sqrt(@0)\",lumiscale[1])"' &> output/mssm_201017_scale-all/log_ws.txt