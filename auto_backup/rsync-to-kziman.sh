#If you are using a lab computer that has multiple users, but want to 
#do auto-backups (which require password-free access to your 
#Dsicovery account), you should create a separate username on that 
#computer which only you have the password for. You will then transfer 
#the data twice; once from the public user account to your private user 
#account, then from your private user account to Discovery. Thus, only 
#your private user account will have access to your Discovery account.


#This script is for the first of those two transfers

#to implement:
#change email and username accordingly
#set in terminal to run once per desired time interval


echo "now syncing audio folder"
rsync -av /Users/Student/Documents/BitBucket/efficient-learning-code/audio /Users/kziman/files_to_sync_el/ > logfile

echo "now syncing db"
rsync -av /Users/Student/Documents/BitBucket/efficient-learning-code/participants.db /Users/kziman/files_to_sync_el/ >> logfile
tail -20 logfile | mail -s "rsync-log" kirsten.k.ziman@dartmouth.edu

#echo "now syncing error log file"
#rsync -av /Users/Student/Documents/BitBucket/efficient-learning-code/<logfile> /Users/kziman/files_to_sync_el/
