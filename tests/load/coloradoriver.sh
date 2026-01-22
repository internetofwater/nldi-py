#!/bin/bash 
#
START_COMID=21412883  ## This comid selected from https://reference.geoconnex.us/collections/mainstems/items/29559 
                      ## as the outlet/mouth of the Colorado River

N=100                 ## Number of jobs in a batch.  These jobs run serially.
PARALLELISM=20        ## How many batches to launch.  Batches run in parallel... the jobs within are serial.

BASE_URL="https://labs-beta.waterdata.usgs.gov/api/nldi"  # Use for QA
#BASE_URL="https://nhgf.dev-wma.chs.usgs.gov/api/nldi-py"  # Use for internal dev
echo  "Fetching a bunch of COMIDs to work on...  "
#echo "${BASE_URL}/linked-data/comid/${START_COMID}/navigation/UM/flowlines?distance=1000&f=json&excludeGeometry=true" 
#curl -s "${BASE_URL}/linked-data/comid/${START_COMID}/navigation/UM/flowlines?distance=1000&f=json&excludeGeometry=true" | jq '.features.[].properties.nhdplus_comid' > /tmp/worklist.txt
echo "DONE."


TRACEFILE="outfile_$$.txt"
for LOOP in `seq 1 $PARALLELISM`
do
    echo -n ">  Launching batch $LOOP of $N requests in the background... " 
    echo "Batch $LOOP of $N requests START at `date`" >> $TRACEFILE
    mkdir -p ./${LOOP}
    cat ./worklist.txt | shuf -n $N | while read COMID
    do
        curl -s "${BASE_URL}/linked-data/comid/${COMID}/navigation/DM/flowlines?distance=50&f=json&excludeGeometry=true" > ./${LOOP}/${COMID}.json
    done  &
    echo " ... launched"
    sleep 1
done
#rm /tmp/worklist_$$.txt

