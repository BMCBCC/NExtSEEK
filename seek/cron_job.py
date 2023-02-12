import glob, os
from datetime import datetime
import argparse
import simplejson
import csv
from django.utils.timezone import get_current_timezone

from django.core.management.base import BaseCommand

def uploadDF_fromQueue(pathtofile, originalfilename):
    from django.conf import settings
    DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
    QUEUE_DIRECTORY  = settings.MEDIA_ROOT + "/queue/"
    ADMIN_USERNAME = settings.SEEK_USER
    ADMIN_PWD = settings.SEEK_PWD
    SEEK_SERVER = settings.SEEK_SERVER
    filename_inqueue = os.path.join(pathtofile, originalfilename)
    from .seekdb import SeekDB
    seekdb = SeekDB(SEEK_SERVER, ADMIN_USERNAME, ADMIN_PWD)
    user_seek = seekdb.user_seek
    
    terms = pathtofile.split('/')
    username = terms[-1]
    seekdb.reviseOwnership(username)
    
    from .dbtable_sample import DBtable_sample
    
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
        
    from .dbtable_data_files import DBtable_data_files
    dbdf = DBtable_data_files("DEFAULT")
    report = dbdf.moveDF_toStorage(seekdb, pathtofile, originalfilename, sample_uid, istest)
    status = report['status']
    if status==-1:
        msg = report['msg']
        return msg, 0
    elif status==0:
        msg = report['msg']
        return msg, 0
    else:
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
    from django.conf import settings
    DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
    QUEUE_DIRECTORY  = settings.MEDIA_ROOT + "/queue/"
    ADMIN_USERNAME = settings.SEEK_USER
    ADMIN_PWD = settings.SEEK_PWD
    SEEK_SERVER = settings.SEEK_SERVER
    outcsvfile = DOWNLOAD_DIRECTORY + 'test_cron_job.txt'
    fo = open(outcsvfile,"w")
    now = datetime.now(tz=get_current_timezone())
    current_time = now.strftime("%H:%M:%S") + '\n'
    print("Current Time =", current_time)
    fo.write(current_time)
    line = QUEUE_DIRECTORY + '\n'
    fo.write(line)
    for root, dirs, files in os.walk(QUEUE_DIRECTORY):
        for file in files:
            filename = os.path.join(root, file)
            print(filename)
            fo.write((filename+'\t'))
            #fo.write('uploadDF_fromQueue\n')
            #msg, status = uploadDF_fromQueue(root, file)
            msg = ''
            fo.write((msg+'\n'))
    
    fo.close()
    
def my_cron_job():
    from django.conf import settings
    DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
    QUEUE_DIRECTORY  = settings.MEDIA_ROOT + "/queue/"
    ADMIN_USERNAME = settings.SEEK_USER
    ADMIN_PWD = settings.SEEK_PWD
    SEEK_SERVER = settings.SEEK_SERVER
    outcsvfile = DOWNLOAD_DIRECTORY + 'test_cron_job.txt'
    fo = open(outcsvfile,"w")
    now = datetime.now(tz=get_current_timezone())
    current_time = now.strftime("%H:%M:%S") + '\n'
    print("Current Time =", current_time)
    fo.write(current_time)
    line = QUEUE_DIRECTORY + '\n'
    fo.write(line)
    for root, dirs, files in os.walk(QUEUE_DIRECTORY):
        if len(files)==0:
            continue
            
        readmefile = os.path.join(root, 'ReadMe.txt')
        foi = open(readmefile,"w")
        for file in files:
            #print(file)
            if file!='ReadMe.txt':
                filename = os.path.join(root, file)
                #print(filename)
                msg, status = uploadDF_fromQueue(root, file)
                line = filename + "\t" + msg + "\n"
                fo.write(line)
                foi.write(line)
    
        foi.close()
    fo.close()
    
def sample_tree_cron_job():
    print('sample_tree_cron_job')
    from .models import Sample_tree
    now = datetime.now(tz=get_current_timezone())
    current_time = now.strftime("%H:%M:%S") + '\n'
    print("Current Time =", current_time)
    exportSampleTrees()
    Sample_tree.objects.all().delete()
    from .dbtable_sample import DBtable_sample
    dbsample = DBtable_sample()
    try:
        max_id = dbsample.tablemodel.objects.latest('id').id
        print("max sample id: %d"%max_id)
    except dbsample.tablemodel.DoesNotExist:
        max_id = 0
    
    id = 1
    nf = 0
    childrenTrees = {}
    for i in range(max_id):
        sample_id = i + 1
        dici, diclist = dbsample.getSampleInfo(sample_id)
        if dici is None:
            continue
        
        uid = dici['uid']
        tree = Sample_tree()
        tree.id = id
        tree.sample_id = sample_id
        tree.uuid = uid
        
        childrenTreeIn = None
        msg = 'children tree absent'
        if uid in childrenTrees:
            childrenTreeIn = childrenTrees[uid]
            msg = 'children tree present'
        
        sampleTree = dbsample.getSampleTrees(sample_id, childrenTreeIn) 
        parents = sampleTree['parents']
        tree.parents = simplejson.dumps(parents, default=str)
        children = sampleTree['children']
        tree.children = simplejson.dumps(children, default=str)
        fullTree = sampleTree['full']
        tree.full = simplejson.dumps(fullTree, default=str)
        tree.updated = str(datetime.now(tz=get_current_timezone()))
        childrenTrees = dbsample.updateChildrenTreeDic(childrenTrees, uid, children)
        try:
            tree.save()
            id += 1
        except:
            msg = "Failed in adding record for " + uid
            nf += 1
        
    print('Number of samples with tree: %d'%(id-1))
    print('Number of samples without tree: %d'%nf)
    print('Number of samples in DMAC: %d'%(id-1+nf))
    now = datetime.now(tz=get_current_timezone())
    print(str(now))
    return

def exportSampleTrees():
    from django.conf import settings
    DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
    
    now = datetime.now(tz=get_current_timezone())
    outcsvfile = DOWNLOAD_DIRECTORY + 'sample_tree_log-' + str(now.strftime("%Y%m%d")) +'.csv'
    print("Save sample tree table into: %s"%outcsvfile)
    
    from .models import Sample_tree
    queryset = Sample_tree.objects.all()
    opts = queryset.model._meta
    field_names = [field.name for field in opts.fields]
    n = 0
    with open(outcsvfile, 'w') as csvfile: 
        writer = csv.writer(csvfile)
        writer.writerow(field_names)
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
            n += 1
        
    print("Number of sample_tree records exported: %d"%n)    


def sample_tree_generation(start_id, end_id, sample_start_id):
    from models import Sample_tree
    now = datetime.now(tz=get_current_timezone())
    current_time = now.strftime("%H:%M:%S") + '\n'
    from seek.dbtable_sample import DBtable_sample
    dbsample = DBtable_sample()
    
    id = 1
    nf = 0
    
    childrenTrees = {}
    
    ids = end_id - start_id + 1
    id = start_id
    for i in range(ids):
        sample_id = i + sample_start_id
        dici, diclist = dbsample.getSampleInfo(sample_id)
        if dici is None:
            continue
        
        uid = dici['uid']
        tree = Sample_tree()
        tree.id = id
        tree.sample_id = sample_id
        tree.uuid = uid
        
        childrenTreeIn = None
        msg = 'children tree absent'
        if uid in childrenTrees:
            childrenTreeIn = childrenTrees[uid]
            msg = 'children tree present'
        
        sampleTree = dbsample.getSampleTrees(sample_id, childrenTreeIn) 
        parents = sampleTree['parents']
        tree.parents = simplejson.dumps(parents, default=str)
        children = sampleTree['children']
        tree.children = simplejson.dumps(children, default=str)
        fullTree = sampleTree['full']
        tree.full = simplejson.dumps(fullTree, default=str)
        tree.updated = str(datetime.now(tz=get_current_timezone()))
        childrenTrees = dbsample.updateChildrenTreeDic(childrenTrees, uid, children)
        
        try:
            tree.save()
            id += 1
        except:
            msg = "Failed in adding record for " + uid
            print(msg)
            nf += 1
        
    print('Number of samples with tree: %d'%(id-1))
    print('Number of samples without tree: %d'%nf)
    print('Number of samples in DMAC: %d'%(id-1+nf))
    return

class Command(BaseCommand):
    help = 'Customized cron job commanline script'

    def add_arguments(self, parser):
        parser.add_argument('startid', nargs='+', type=int, help='start id.')
        parser.add_argument('endid', nargs='+', type=int, help='end id.')
        parser.add_argument('sampleid', nargs='+', type=int, help='sample id.')

    def handle(self, *args, **options):
        start_id = options['startid']
        end_id = options['endid']
        sample_start_id = options['sampleid']
        print("start_id: ", start_id)
        sample_tree_generation(start_id, end_id, sample_start_id)

def main():
    parser = argparse.ArgumentParser(description="Download and uverify file from Pride database.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('startid', help='start id.')
    parser.add_argument('endid', help='end id.')
    parser.add_argument('sampleid', help='sample id.')
    args = parser.parse_args()
    start_id = args.startid
    end_id = args.endid
    sample_start_id = args.sampleid
    
    sample_tree_generation(start_id, end_id, sample_start_id)


if __name__ == "__main__":
    main()