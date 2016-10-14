#this script will copy the desired file/directory to discovery, provided you have granted access to your discovery account
#it will also auto-email a log of the backup

rsync -av audio kziman@discovery.dartmouth.edu:/idata/cdl/data/behavioral/FRFR/synced_files_from_labmac/ > logfile
rsync -av participants.db kziman@discovery.dartmouth.edu:/idata/cdl/data/behavioral/FRFR/synced_files_from_labmac/ >> logfile
tail -20 logfile | mail -s "sync-to-discovery" kirsten.k.ziman@dartmouth.edu
