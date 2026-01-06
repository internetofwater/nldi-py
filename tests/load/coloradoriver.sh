#!/bin/bash 
#
START_COMID=21412883  ## This comid selected from https://reference.geoconnex.us/collections/mainstems/items/29559 
                      ## as the outlet/mouth of the Colorado River

N=100                 ## Number of jobs in a batch.  These jobs run serially.
PARALLELISM=10        ## How many batches to launch.  Batches run in parallel... the jobs within are serial.

echo -n "Fetching a bunch of COMIDs to work on...  "
curl -s "https://nhgf.dev-wma.chs.usgs.gov/api/nldi-py/linked-data/comid/${START_COMID}/navigation/UM/flowlines?distance=1000&f=json&excludeGeometry=true" | jq '.features.[].properties.nhdplus_comid' > /tmp/worklist_$$.txt
echo "DONE."

TRACEFILE="outfile_$$.txt"
for LOOP in `seq 1 $PARALLELISM`
do
    echo -n ">  Launching batch $LOOP of $N requests in the background... " 
    echo "Batch $LOOP of $N requests START at `date`" >> $TRACEFILE
    cat /tmp/worklist_$$.txt | shuf -n $N | while read COMID
    do
        curl -s "https://nhgf.dev-wma.chs.usgs.gov/api/nldi-py/linked-data/comid/${COMID}/navigation/DM/flowlines?distance=20&f=json&excludeGeometry=true" > /dev/null
    done && echo "Batch $LOOP FINISH at `date`" >> $TRACEFILE &
    echo " ... launched"
    sleep 1
done
rm /tmp/worklist_$$.txt

