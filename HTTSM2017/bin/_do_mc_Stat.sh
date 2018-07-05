# provide the folder at the end of the command 
ls $1/*/*/*.txt | while read sample
do
   echo  '* autoMCStats 0' >> $sample 

done

