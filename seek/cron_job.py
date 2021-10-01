import glob, os
from datetime import datetime

from django.conf import settings

DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"

# on fairdata, it is /net/bmc-pub10/data1/queue/white/ikohale
# such as dmac/themes/SmartAdmin/static/media/queue
QUEUE_DIRECTORY  = settings.MEDIA_ROOT + "/queue/"

ADMIN_USERNAME = settings.SEEK_USER
ADMIN_PWD = settings.SEEK_PWD
SEEK_SERVER = settings.SEEK_SERVER

from .seekdb import SeekDB
from .seekapi import SeekAPI
from .dbtable_sample import DBtable_sample
from .dbtable_data_files import DBtable_data_files

def uploadDF_fromQueue(pathtofile, originalfilename):
    ''' Upload a data file from queue into Seek.
    Input:
        pathtofile, 
        originalfilename, filename in the queue.
    
    
    '''
    print(pathtofile, originalfilename)
    filename_inqueue = os.path.join(pathtofile, originalfilename)
    '''
    seekdb = SeekDB(None, None, None)
    request = None
    user_seek = seekdb.getSeekLogin(request)
    '''
    
    seekdb = SeekDB(SEEK_SERVER, ADMIN_USERNAME, ADMIN_PWD)
    user_seek = seekdb.user_seek
    
    terms = pathtofile.split('/')
    username = terms[-1]
    print('Login usr name: ', username)
    seekdb.reviseOwnership(username)
    
    istest = True
    if istest:
        sample_uid = 'TIS-210517FOR-89'
        print('Run a test with the sample UID: %s'%sample_uid)
    else:
        dbsample = DBtable_sample()
        filetype = "DATAFILE"
        sampleRecord, msg = dbsample.searchFileInSample(seekdb, originalfilename, filetype)
        if sampleRecord is None or sampleRecord['id']<=0:
            msg = msg + ': ' + originalfilename
            print(msg)
            return msg, 0
        
        sample_uid = sampleRecord['uuid']
    
    dbdf = DBtable_data_files("DEFAULT")
    #report = dbdf.uploadFileLink_intoSeek(seekdb, infile)
    
    # copy file from queue to storage server with a new file name
    report = dbdf.moveDF_toStorage(seekdb, pathtofile, originalfilename, sample_uid, istest)
    status = report['status']
    if status==-1:
        # data file already uploaded into DF table, do we continue?
        msg = report['msg']
        return msg, 0
    elif status==0:
        # data file not uploaded into data lake properly, should return
        msg = report['msg']
        return msg, 0
    else:
        # data file does not exist in DF table, ready for uploading into Seek
        msg = report['msg']
 
    dici = report['newrow']
    content_type = dici['content_type']
    df_uid = dici['uid']
    weburl = dici['fileurl']
    report = dbdf.uploadDF_storageToSeek(seekdb, originalfilename, content_type, df_uid, weburl, istest)
    if report['status']==0:
        status = 0
        msg += report['msg']
    else:
        msg = weburl
        status = 1
        
    return msg, status

def my_cron_job_0():
    # your functionality goes here
    print('my_cron_job')
    outcsvfile = DOWNLOAD_DIRECTORY + 'test_cron_job.txt'
    fo = open(outcsvfile,"w")
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S") + '\n'
    print("Current Time =", current_time)
    fo.write(current_time)
    line = QUEUE_DIRECTORY + '\n'
    fo.write(line)
    
    #os.chdir(QUEUE_DIRECTORY)
    #for file in glob.glob("*.txt"):
    #for file in glob.glob("*.*"):
    #    print(file)
    #    filename = file + '\n'
    #    fo.write(filename)
        
    for root, dirs, files in os.walk(QUEUE_DIRECTORY):
        for file in files:
            #if file.endswith(".txt"):
            #    print(os.path.join(root, file))
            # such as 
            filename = os.path.join(root, file)
            print(filename)
            
            fo.write((filename+'\t'))
            #fo.write('uploadDF_fromQueue\n')
            #msg, status = uploadDF_fromQueue(root, file)
            msg = ''
            fo.write((msg+'\n'))
    
    fo.close()
    
def my_cron_job():
    print('my_cron_job')
    outcsvfile = DOWNLOAD_DIRECTORY + 'test_cron_job.txt'
    fo = open(outcsvfile,"w")
    
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S") + '\n'
    print("Current Time =", current_time)
    fo.write(current_time)
    line = QUEUE_DIRECTORY + '\n'
    fo.write(line)
    
    #os.chdir(QUEUE_DIRECTORY)
    #for file in glob.glob("*.txt"):
    #for file in glob.glob("*.*"):
    #    print(file)
    #    filename = file + '\n'
    #    fo.write(filename)
        
    for root, dirs, files in os.walk(QUEUE_DIRECTORY):
        if len(files)==0:
            continue
            
        readmefile = os.path.join(root, 'ReadMe.txt')
        #print(readmefile)
        foi = open(readmefile,"w")
        for file in files:
            #print(file)
            if file!='ReadMe.txt':
                #if file.endswith(".txt"):
                #    print(os.path.join(root, file))
                # such as 
                filename = os.path.join(root, file)
                #print(filename)
                msg, status = uploadDF_fromQueue(root, file)
                line = filename + "\t" + msg + "\n"
                fo.write(line)
                foi.write(line)
    
        foi.close()
    fo.close()