'''
Created on July 12, 2016

@author: Huiming Ding
Email: huiming@mit.edu

Description:

This script is implemented for the Data_files database/table.

Input:  No typical input to define.
       
Output: No typical output to define.
        
Example command line:
     
Log of changes:
     
'''
#!/usr/bin/env python
import os
import sys
import time
import datetime
import simplejson
import json
import zipfile
import logging
logger = logging.getLogger(__name__)

from .models import Sops
from .seekdb import SeekDB

from dmac.dbtable import DBtable
from dmac.iocsv import saveCsvfile
from dmac.conversion import handle_uploaded_file, correctFileName, sizeof_fmt, getFileChecksum

from django.conf import settings
from django import forms

from dbtable_assay_assets import DBtable_assay_assets
from dbtable_content_blobs import DBtable_content_blobs

DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
# this is usually at "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY  = settings.PROJECT_ROOT + "/static/media/download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY
# this is the symbolic link to "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY_LINK = '/static/media/download/'

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
SOPS_FILTER_MAPPING = {
    'id':'id',
    'title':'uid'
}

# Default values for Sample table
SOPS_DEFAULT = {
    #'id':'',
    'contributor_id':0,
    'title':'',
    'description':'',
    'created_at':'',
    'updated_at':'',
    'last_used_at':'',
    'version':1,
    'first_letter':'',
    'other_creators':'',
    'uuid':'',
    'policy_id':'',
    'doi':None,
    'license':'CC-BY-4.0',
    'deleted_contributor':None         # use DB default null
}

# The following is the mapping between fields on the form and those in the DB grant table
BATCHSEARCHFORM_MAPPING = {
    'keywords':'PK',
    'status':'Status'
}
BATCHSEARCHFORM_DEFAULT = {
    #'pk':'',   # usually PK should be either 0 or a valid pk
    'keywords':'',
    'category':'ALL'
}

CATEGORY_CHOICES = (
    ("ALL", "All"),
    ("ASSAYS", "Assays"),
    ("DATAFILES", "Data files"),
    ("SAMPLES", "Samples"),
    ("SAMPLETYPES", "Sample types")
)

FILETYPES_SOP_SUPPORTED = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword"
]

SOP_ERRORCODE = {
    '001': 'Error P001: User not logged in.',
    '101': 'Warning P101: File already uploaded in Seek thus no update.',
    '102': 'Warning P102: Not one of supported pdf, Word, Excel or txt files: ',
    '201': 'Error P201: File UID not in right format: ',
    '202': 'Error P202: Failed in searching for SOP in Seek: ',
    '203': 'Error P203: File uploading into content_blob table failed: ',
    '204': 'Warning P204: File and sample association not saved correctly into DB: ',
    '205': 'Warning P205: File already uploaded in Seek, forced update: '
}  

class BatchSearchForm(forms.Form):
    keywords = forms.CharField(required=True, label='Keywords', widget=forms.Textarea )
    category = forms.ChoiceField(required=True, label="Category", initial='', choices=CATEGORY_CHOICES, widget=forms.Select())

class DBtable_sops(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        dbdf = DBtable_sops("DEFAULT")
        return dbdf.getDatafileUID(pid)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sops"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'sops'
        self.tablemodel = Sops
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'contributor_id',
            'title',
            'description',
            'created_at',
            'updated_at',
            'last_used_at',
            'version',
            'first_letter',
            'other_creators',
            'uuid',
            'policy_id',
            'doi',
            'license',
            'deleted_contributor'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['title', 'version']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = SOPS_FILTER_MAPPING
        self.excludeFields = []
        
        # create a virtual form that is to be overrided.
        report = {}
        self.form = BatchSearchForm(report)
        self.formDefault = BATCHSEARCHFORM_DEFAULT
        self.formMapping = BATCHSEARCHFORM_MAPPING
     
    def __getUID(self, lababbv, filename, nassets=0):
        ''' Define the UID for a file uploaded from the DropZone.
        Input:
            #pid: the primary key in the table sops.
            lababbv, three letter abbreviation of a lab/institution, defined based on login user
                as user_seek['lababbv']
            filename, the corrected filename, in which any space has been replaced by '-'.
            nassets, how many same original filename exist in the content_blob table,
                which will be used as the increased version number for same
                original filename and type. Default is 0 sonext version is 1.
        Output
            UID: such as P.WHI-200401-V1_filename, where "DF" for data file,
                "191213" is the date of uploading, and "123456" is the pid.
        '''
        #print('getDatafileUID')
        #uid_prefix = 'P.' + institutionname + '_' + filename
        #uid = uid_prefix
        
        uid_date = str(datetime.datetime.now().strftime("%Y%m%d"))  # such as '20200323'
        uid_date_2 = uid_date[2:]    # such as # such as '200323'
        next_version = nassets + 1
        
        # such as P.MIT-200323-V1_filename
        #uid = 'P.' + institutionname + '-' + uid_date_2 + '-V' + str(next_version) + '_' + filename
        uid = 'P.' + lababbv + '-' + uid_date_2 + '-V' + str(next_version) + '_' + filename
        return uid

    def __defineUploadFilename(self, username, infilename, uid):
        ''' Define the data filename from the input file uploaded.
        Input:
            infilename, the input file name, such as "abcde.jpg"
        
        Output:
            outfilename, the filename defined after uploading.
            
        Notes:
            The output file name is defined as the following:
                outfilename = UID
        
        '''
        #outfilename = username + "_" + infilename
        #outfilename = os.path.join(upload_full_path, infilename)
        #while os.path.exists(outfilename):
        #    infilename = '_' + infilename
        #    outfilename = os.path.join(upload_full_path, infilename)
        outfilename = uid
        return outfilename

    def __getWeblink(self, uid):
        #def __getWeblink(self, labfolder, projectfolder, uid):
        ''' Get the web link for downloading a SOP based on,
        
        Input:
            labfolder, lab name, after space replaced by '-'.
            projectfolder, the project name, after space replaced by '-'.
            uid, the UID for the SOP.
        
        Output:
            weblink, a url for downloading the file, such as
                
        '''
        #weblink = settings.SEEK_DATAFILE_ROOT_WEBLINK + labfolder + "/" + projectfolder + "/" + uid
        url = "/seek/sop/uid=" + uid + "/"
        weburl = settings.SEEK_DATAFILE_SERVER + url
        weblink = '<a href="' + url + '" target="_blank">' + weburl + '</a>'
        #weblink = weburl
        return weblink
    
    def __getUploadPath(self, user_seek):
        ''' Define the path and file name for uploading a data file.
        Input:
            projectname = user_seek['projectname'], such as 'ImpactTB'
            institutionname = user_seek['institutionname'], such as 'BENG lab'
            username = user_seek['username'], such as 'dbadmin'
            originalfilename, such as 'test.jpg'
            nassets, how many same original filename exist in the content_blob table,
                which will be used as the increased version number for same
                original filename and type. Default is 0 sonext version is 1.
        Output
            outfilename, the output file name without the absolute path,such as
                    "DF-20191210-1234_USER_abcd.jpg", which is revised to
                    "USER_v1_abcd.jpg", which supports versionning.
                To get the file with path, use:
                    filename = os.path.join(upload_full_path, outfilename)
            upload_full_path, the absolute path, such as
                "/net/bmc-pub10/data1/bmc/seek/luffenbourgLab/impactb/"
            weblink, the weblink to the file, such as
                #'http://fair.mit.edu/luffenbourgLab/impactb//DF-20191210-1234_USER_abcd.jpg'
                'http://fairdata.mit.edu:8010/seek/sop/uid=P.WHI-200412-V1_1234_USER_abcd.jpg/'
        Notes:
            The protocol for defining the path, file name and web link is as the following:
            1. The path consists of ROOT path, plus the sub-folder name by using the project name,
                in which any space is replaced by "_", and the original file name.
            2. A datafile should never be overwritten.
        '''        
        #upload_dir = (
        #    "tmp" +
        #    hashlib.md5(username.encode('utf-8')).hexdigest()
        #)
        # All data files fro dropZone will be stored under the default project and default assay,
        # until it is included in the sample sheet for actual assay association.
        projectname = user_seek['projectname']
        
        institutionname = user_seek['institutionname']
        # lab abbreviation, three letter abbreviation of a lab
        lababbv = user_seek['lababbv']
        
        # Step 1. Get full path of the uploading folder
        # Lab folder, such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab"
        labfolder = lababbv
        
        
        '''
        upload_full_path_labroot = os.path.join(settings.SEEK_DATAFILE_ROOT, labfolder)
        if not os.path.exists(upload_full_path_labroot):
            print("mkdir: ", upload_full_path_labroot)
            os.makedirs(upload_full_path_labroot)
        
        # the sub-folder name, defined by the project name, in which any space is replaced by '_'.
        projectfolder = projectname
        if " " in projectname:
            projectfolder = projectname.replace(" ", "_")
            
        # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
        upload_full_path_projectroot = os.path.join(upload_full_path_labroot, projectfolder)
        print('project_root:', upload_full_path_projectroot)
        if not os.path.exists(upload_full_path_projectroot):
            os.makedirs(upload_full_path_projectroot)
        
        # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
        upload_full_path = upload_full_path_projectroot
        '''
        
        # the sub-folder name, defined by the project name, in which any space is replaced by '_'.
        projectfolder = projectname
        if " " in projectname:
            projectfolder = projectname.replace(" ", "_")
            
        # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
        upload_full_path_projectroot = os.path.join(settings.SEEK_DATAFILE_ROOT, projectfolder)
        print('project_root:', upload_full_path_projectroot)
        if not os.path.exists(upload_full_path_projectroot):
            os.makedirs(upload_full_path_projectroot)
        
        upload_full_path_labroot = os.path.join(upload_full_path_projectroot, labfolder)
        if not os.path.exists(upload_full_path_labroot):
            print("mkdir: ", upload_full_path_labroot)
            os.makedirs(upload_full_path_labroot)
        
        
        # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
        upload_full_path = upload_full_path_labroot
        
        return lababbv, upload_full_path
    
    def __defineUploadPath(self, user_seek, originalfilename, nassets=0):
        ''' Define the path and file name for uploading a data file.
        Input:
            projectname = user_seek['projectname'], such as 'ImpactTB'
            institutionname = user_seek['institutionname'], such as 'BENG lab'
            username = user_seek['username'], such as 'dbadmin'
            originalfilename, such as 'test.jpg'
            nassets, how many same original filename exist in the content_blob table,
                which will be used as the increased version number for same
                original filename and type. Default is 0 sonext version is 1.
        Output
            outfilename, the output file name without the absolute path,such as
                    "DF-20191210-1234_USER_abcd.jpg", which is revised to
                    "USER_v1_abcd.jpg", which supports versionning.
                To get the file with path, use:
                    filename = os.path.join(upload_full_path, outfilename)
            upload_full_path, the absolute path, such as
                "/net/bmc-pub10/data1/bmc/seek/luffenbourgLab/impactb/"
            weblink, the weblink to the file, such as
                #'http://fair.mit.edu/luffenbourgLab/impactb//DF-20191210-1234_USER_abcd.jpg'
                'http://fairdata.mit.edu:8010/seek/sop/uid=P.WHI-200412-V1_1234_USER_abcd.jpg/'
        Notes:
            The protocol for defining the path, file name and web link is as the following:
            1. The path consists of ROOT path, plus the sub-folder name by using the project name,
                in which any space is replaced by "_", and the original file name.
            2. A datafile should never be overwritten.
        '''
        # Use '-' to replace any space in the original file name so that
        # such corrected name can be used as the filename saved on the storage server and as file UID.
        infilename_corrected = correctFileName(originalfilename)
        
        #upload_dir = (
        #    "tmp" +
        #    hashlib.md5(username.encode('utf-8')).hexdigest()
        #)
        username = user_seek['username']
        
        lababbv, upload_full_path = self.__getUploadPath(user_seek)
        
        
        # Step 2. Get the datafile info
        #   The next primary key available in sops table, which is not in further use.
        #pid = self.getLatestPrimarykey()
        pid = 1
        # the UID for the current data file that will be uploaded.
        uid = self.__getUID(lababbv, infilename_corrected, nassets)
        # Get the destination file name, which is defined as
        # such as: UID_username_originalname
        outfilename = self.__defineUploadFilename(username, infilename_corrected, uid)
            
        # Step 3. Get the weblink to the file
        weblink = self.__getWeblink(uid)
        print('weblink:', weblink)
        
        dfrecord = {}
        dfrecord['id'] = pid
        dfrecord['uid'] = uid
        dfrecord['originalname'] = originalfilename
        #dfrecord['filetypeid'] = content_type
        dfrecord['fileurl'] = weblink
        dfrecord['notes'] = ''
        dfrecord['outfilename'] = outfilename
        dfrecord['upload_full_path'] = upload_full_path
        
        fullfilename = os.path.join(upload_full_path, outfilename)
        dfrecord['fullfilename'] = fullfilename
        return dfrecord
        
    def __getSeeklink(self, originalfilename, sop_id):
        ''' Get the web link for downloading a SOP based on,
        
        Input:
            sop_id, the primary key in sobs table for the SOP, also the asset_id in content_blob table.
        
        Output:
            Seek link, a url for finding the file in Seek DB, such as
                http://seekserver/sops/12/
                
        '''
        seek_url = settings.SEEK_URL + "/sops/" + str(sop_id)
        seeklink = '<a href="' + seek_url + '" target="_blank">' + originalfilename + '</a>'
        #seeklink = '<a href="' + seek_url + '" target="_blank">' + str(sop_id) + '</a>'
        return seeklink

    
    def __defineSOP(self, seekdb, originalfilename):
        ''' Search Seek whether a data file has been uploaded previously, then
            define the record for uploading into DB.
        Input
            seekdb, SEEK DB API.
                username,  user_seek['username'] or request.session.get('username')
                userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            originalfilename: request.FILES['file'].name, the original file name from client side, which
                        may contain space in its name.
        
        Output
            df_id, >0, exists in Seek
                   =0, not exist in Seek but exist on storage server.
                   <0, does not exist anywhere in Seek or on storage server.
        
        Criteria
            Only the following first two criteria are applied in the implementation of the script.
            
                1. same file name, applied;
                2. same login user, applied;
                3. file checksum, not applied;
                4. file time stamp, not applied;
                5. file size, not applied.
        '''
        # Step 1. Query content_blobs table whether the data file is already uploaded,
        # based on the original file name from the client side.
        dbcb = DBtable_content_blobs("DEFAULT")
        asset_id, asset_type, asset_version, nassets = dbcb.searchFile(originalfilename, 'Sop')
        
        # the corrected file name is used then as the file name saved on the storage server.
        # copy the file to the storage server
        # assign next UID for uloading etc
        dfrecord = self.__defineUploadPath(seekdb.user_seek, originalfilename, nassets)
        return asset_id, asset_type, dfrecord
    
    
    def __searchSOP(self, seekdb, originalfilename):
        ''' Search Seek whether a data file has been uploaded previously.
        Input
            seekdb, SEEK DB API.
                username,  user_seek['username'] or request.session.get('username')
                userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            originalfilename: request.FILES['file'].name, the original file name from client side, which
                        may contain space in its name.
        
        Output
            df_id, >0, exists in Seek
                   =0, not exist in Seek but exist on storage server.
                   <0, does not exist anywhere in Seek or on storage server.
        
        Criteria
            Only the following first two criteria are applied in the implementation of the script.
            
                1. same file name, applied;
                2. same login user, applied;
                3. file checksum, not applied;
                4. file time stamp, not applied;
                5. file size, not applied.
        '''
        asset_id, asset_type, dfrecord = self.__defineSOP(seekdb, originalfilename)
        # hoowever, we must confirm for updating any existing original file name
        if asset_id is not None and asset_type=='Sop':
            # data file found in content_blobs table
            record = self.getOneRecord(asset_id)
            print('SOP record:', record)
            if record is None or 'contributor_id' not in record:
                return 0, dfrecord
            
            #contributor_id = self.retrieveFieldValue(asset_id, 'contributor_id')
            contributor_id = record['contributor_id']
            print("contributor_id:", contributor_id, seekdb.user_seek['user_id'])
            if contributor_id is not None and int(contributor_id)==seekdb.user_seek['user_id']:
                
                # same user has same data file in Seek, return the datafile id
                dfrecord['id'] = asset_id
                dfrecord['uid'] = record['title']
                dfrecord['originalname'] = originalfilename
                dfrecord['originalname_url'] = self.__getSeeklink(originalfilename, asset_id)
                
                #dfrecord['notes'] = 'Warning: already uploaded, no update enforced.'
                dfrecord['notes'] = 'Warning: File already uploaded in Seek'
                
                # url in Seek for the SOP
                #seek_url = settings.SEEK_URL + "/sops/" + str(asset_id)
                # the url for the SOP on the storage server
                #url = '<a href="' + seek_url + '">' + serverlink + '</a>'
                #dfrecord['fileurl'] = url
                dfrecord['fileurl'] = self.__getWeblink(record['title'])
                
                # if we want to enforce the update of the data file,
                # the version should be next version, such as "user_v1_originalfilename"
                #   outfilename = dfrecord['outfilename']
                #   nextversion = '_' + str(int(asset_version) + 1) + '_'
                #   dfrecord['outfilename'] = outfilename.replace('_v1_', nextversion)
                return asset_id, dfrecord
    
        # Step 2. Query whether the same user has same data file available on server
        # For example, the data file size might exceed the size limit of Seek thus not uploaded in Seek, but available on server.
        
        return 0, dfrecord
                
    def uploadSOP_toStorage(self, seekdb, infile, md5In):
        ''' Upload a SOP file into the storage server, which will be further uploaded into Seek.
        
        Notes: In the initial implementation, files are batch uploaded from the client side DropZone
                to the storage server then from storage server to Seek database. However, Seek API
                seems not happy for parallel uploading of files into Seek content_blob table, when
                seekdb.seekuploadSOP() is called below. Therefore, we split the whole process into
                two steps:
                    (a) upload the file into storage server from client side, which is the current step.
                    (b) Upload the file from storage server to the Seek system.
        
        Input:
            seekdb, SEEK DB API.
            infile: = request.FILES['file']
        
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            
        Output:
            report={}, a report with the following,
            report['msg'] = msg
            report['status'] = status
            report['df_info'] = df_info, the output from the API query "/sops/id/", such as,
            report['newrow'] = dfrecord, a record for shown in the table on the DropZone page, which includes
                dfrecord['id'] = pid
                dfrecord['uid'] = uid
                dfrecord['originalname'] = originalfilename
                #dfrecord['filetypeid'] = content_type
                dfrecord['fileurl'] = weblink
                dfrecord['outfilename'] = outfilename
                dfrecord['upload_full_path'] = upload_full_path
                dfrecord['fullfilename'] = fullfilename
        
        Notes:
            migrated from def seek(request) in MyFair project.
            
        Procedure:
            After a data file is droped into the FileZone, it takes the following procedure to upload a data file into the system:
            1. The file is copied to the storage server on bmc-pub10;
            2. A web-url link to the file is generated and returned;
            3. The information about the data file together with its web-link is stored into the Seek system.
        '''
        print("uploadSOP_toStorage")
        originalfilename = infile.name
        report = {}
        if seekdb.user_seek is None:
            report['msg'] = SOP_ERRORCODE['001']
            report['status'] = 0
            dfrecord = {}
            dfrecord['uid'] = ''
            dfrecord['originalname'] = originalfilename
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        content_type = infile.content_type
        if content_type not in FILETYPES_SOP_SUPPORTED:
            report['msg'] = SOP_ERRORCODE['102'] + content_type
            print(report['msg'])
            report['status'] = 0
            dfrecord = {}
            dfrecord['uid'] = ''
            dfrecord['originalname'] = originalfilename
            dfrecord['fileurl'] = 'Not available'
            dfrecord['notes'] = report['msg']
            dfrecord['content_type'] = content_type
            report['newrow'] = dfrecord
            print(report)
            return report
        
        # Step 1. Define output file name etc,  and verify whether the  data file has been uploaded before.        
        df_id, dfrecord = self.__searchSOP(seekdb, originalfilename)
        print('df_id:', df_id, dfrecord)
        dfrecord['content_type'] = content_type
        
        # Step 2. Upload file to the designated server folder, regardles whether the file is already on server and in Seek.
        fullfilename = dfrecord['fullfilename']
        handle_uploaded_file(infile, fullfilename)
        
        if df_id>0:
            #report['msg'] = 'Warning: File already uploaded in Seek: ' + infile.name
            report['msg'] = SOP_ERRORCODE['101']
            print(report['msg'])
            report['status'] = -1
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        md5Now = getFileChecksum(fullfilename, 'MD5')
        if md5Now!=md5In:
            msg = 'Error: File MD5 checksum not match: ' + md5Now
            status = 0
        else:
            msg = 'File uploaded to storage server'
            status = 1
        
        #elif df_id==0:
        #    report['msg'] = 'Warning: file already uploaded on server: ' + infile.name
        #    print report['msg']
        #    report['status'] = 0
        #    return report
        #else:
        #    report['msg'] = 'Okay: file ready for uploadinng: ' + infile.name
        #    print report['msg']
        #    report['status'] = 0
        #    #return report
        
        report['msg'] = msg
        report['status'] = status
        dfrecord['notes'] = report['msg']
        report['newrow'] = dfrecord
        return report

    def __getIDfromUID(self, sopUID):
        ''' Search Seek whether a data file has been uploaded previously.
        Input
            sopUID: = the UID/title for a SOP object in sops table, such as
                P.labname-date-V#_filename, for example,
                P.NDMA-200323-V1_inj.Beng.001.docx
        
        Output
        
            id in sops table, or asset_id, in content_blob table
        
        '''
        # Step 1. Query content_blobs table whether the data file is already uploaded.
        constraint = {}
        constraint['title'] = sopUID
        diclist_cb = self.queryRecordsByConstraint(constraint)
        
        nrecords = len(diclist_cb)
        if nrecords==1:
            # unqiue record found in content_blobs table
            dici = diclist_cb[0]
            id = dici['id']
        else:
            # same file not in content blob
            id = None
            
        return id

    def uploadSOP_storageToSeek(self, seekdb, originalfilename, content_type):
        ''' Upload a SOP file from the storage server into Seek system by using Seek API.
        
        Notes: In the initial implementation, files are batch uploaded from the client side DropZone
                to the storage server then from storage server to Seek database. However, Seek API
                seems not happy for parallel uploading of files into Seek content_blob table, when
                seekdb.seekuploadSOP() is called below. Therefore, we split the whole process into
                two steps:
                    (a) upload the file into storage server from client side;
                    (b) Upload the file from storage server to the Seek system, which is the current step.
        
        Input:
            seekdb, SEEK DB API.
            infile: = request.FILES['file']
        
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            
        Output:
            report={}, a report with the following,
            report['msg'] = msg
            report['status'] = status
            report['df_info'] = df_info, the output from the API query "/sops/id/", such as,
            report['newrow'] = dfrecord, a record for shown in the table on the DropZone page, which includes
                dfrecord['id'] = pid
                dfrecord['uid'] = uid
                dfrecord['originalname'] = originalfilename
                #dfrecord['filetypeid'] = content_type
                dfrecord['fileurl'] = weblink
                dfrecord['outfilename'] = outfilename
                dfrecord['upload_full_path'] = upload_full_path
                dfrecord['fullfilename'] = fullfilename
        
        Notes:
            migrated from def seek(request) in MyFair project.
            
        Procedure:
            After a data file is droped into the FileZone, it takes the following procedure to upload a data file into the system:
            1. The file is copied to the storage server on bmc-pub10;
            2. A web-url link to the file is generated and returned;
            3. The information about the data file together with its web-link is stored into the Seek system.
        '''
        report = {}
        df_id, asset_type, dfrecord = self.__defineSOP(seekdb, originalfilename)
        if df_id>0:
            report['msg'] = SOP_ERRORCODE['205'] + originalfilename
            print(report['msg'])
            report['status'] = 0
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            
            # Same original filename exists in DB,
            # however, forced upload is allowed according to user side confirmation.
            #return report
        
        # Step 3. Store datafile into Seek system by using Seek API
        userid = seekdb.user_seek['user_id']
        project_id = seekdb.user_seek['projectid']
        assay_id = None
        #tags = []
        #tags.append("")
        #tags.append("")
        tags = None
        
        #print('content_type:', content_type)
        dfrecord['content_type'] = content_type
    
        # use API to upload file into Seek
        #datatitle = fileuid
        datatitle = dfrecord['uid']
        # the filename with path on the storage server
        fullfilename = dfrecord['fullfilename']
        print(fullfilename, originalfilename)
        #description = request.POST.get('description')
        description = 'File uploaded from DropZone'
        msg, status, df_info, datafile_url = seekdb.seekuploadSOP(
            #seekupload(
            #request.session.get('username'),
            #request.session.get('password'),
            #request.session.get('storage'),
            datatitle,
            fullfilename,
            originalfilename,
            content_type,
            userid,
            project_id,
            assay_id,
            description,
            tags
        )
        if status==1:
            #df_id, dfrecord = self.__searchSOP(seekdb, originalfilename)
            df_id = self.__getIDfromUID(datatitle)
            if df_id>0:
                dfrecord['originalname'] = originalfilename
                #dfrecord['originalname_url'] = self.__getSeeklink(originalfilename, df_id)
                dfrecord['id'] = self.__getSeeklink(originalfilename, df_id)
                dfrecord['notes'] = 'Successful'
            else:
                msg = SOP_ERRORCODE['202'] + datatitle
                dfrecord['notes'] = msg
                
        else:
            dfrecord['id'] = ''
            dfrecord['uid'] = ''
            msg = SOP_ERRORCODE['203'] + msg
            dfrecord['notes'] = msg
    
        # Step 4. If we don't want to keep two copies of the data file on server,
        # remove temp folder and file
        #call(["rm", "-r", outfilename])
        #call(["rm", "-r", upload_full_path])
        
        report['msg'] = msg
        report['status'] = status
        report['df_info'] = df_info
        report['newrow'] = dfrecord
        return report                    
                
    def uploadSOPs_storageToSeek(self, seekdb, diclist):
        ''' Upload multiple SOP files from the storage server into Seek system by using Seek API
            in a sequential order.
            
            diclist: from datafile_table_embed.html
        '''
        report = {}
        report['msg'] = 'test uploadSOPs_storageToSeek()'
        report['status'] = 0
        report['df_info'] = ''
        report['newrows'] = []
        
        newrows = []
        status = 1
        msg = ''
        for dici in diclist:
            #print(dici)
            originalfilename = dici['originalname']
            content_type = dici['content_type']
            reporti = self.uploadSOP_storageToSeek(seekdb, originalfilename, content_type)
            newrows.append(reporti['newrow'])
            if reporti['status']==0:
                status = 0
                msg += reporti['msg'] + '\n'
        
        report['msg'] = msg
        report['status'] = status
        report['df_info'] = ''
        report['newrows'] = newrows
        return report 
        
    def uploadSOP_intoSeek_retired(self, seekdb, infile):
        ''' Upload a web link to a data file into Seek system by using Seek API.
        
        Notes: In the initial implementation, files are batch uploaded from the client side DropZone
                to the storage server then from storage server to Seek database. However, Seek API
                seems not happy for parallel uploading of files into Seek content_blob table, when
                seekdb.seekuploadSOP() is called below. Therefore, we split the whole process into
                two steps:
                    (a) upload the file into storage server from client side;
                    (b) Upload the file from storage server to the Seek system.
        
            This function combines two steps into one for parallel uploading of file.
        
        Input:
            seekdb, SEEK DB API.
            infile: = request.FILES['file']
        
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            
            originalfilename=None, original file name, which is a reduandent parameter with infile.
                    
            fileuid=None
            
            
        Output:
            report={}, a report with the following,
            report['msg'] = msg
            report['status'] = status
            report['df_info'] = df_info, the output from the API query "/sops/id/", such as,
            report['newrow'] = dfrecord, a record for shown in the table on the DropZone page, which includes
                dfrecord['id'] = pid
                dfrecord['uid'] = uid
                dfrecord['originalname'] = originalfilename
                #dfrecord['filetypeid'] = content_type
                dfrecord['fileurl'] = weblink
                dfrecord['outfilename'] = outfilename
                dfrecord['upload_full_path'] = upload_full_path
                dfrecord['fullfilename'] = fullfilename
        
        Notes:
            migrated from def seek(request) in MyFair project.
            
        Procedure:
            After a data file is droped into the FileZone, it takes the following procedure to upload a data file into the system:
            1. The file is copied to the storage server on bmc-pub10;
            2. A web-url link to the file is generated and returned;
            3. The information about the data file together with its web-link is stored into the Seek system.
        '''
        print("uploadSOP_intoSeek")
        originalfilename = infile.name
        content_type = infile.content_type
        
        #report = self.uploadSOP_toStorage(seekdb, infile)
        #if report['status']==0:
        #    return report
        
        report = {}
        if seekdb.user_seek is None:
            report['msg'] = 'Error: user not loged in.'
            report['status'] = 0
            dfrecord = {}
            dfrecord['originalname'] = originalfilename
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        # Step 1. Define output file name etc,  and verify whether the  data file has been uploaded before.
        
        df_id, dfrecord = self.__searchSOP(seekdb, originalfilename)
        if df_id>0:
            report['msg'] = 'Warning: file already uploaded in Seek, no update: ' + infile.name
            print report['msg']
            report['status'] = 0
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        content_type = infile.content_type
        if content_type not in FILETYPES_SOP_SUPPORTED:
            report['msg'] = 'Warning: not one of supported pdf, Word, Excel or txt files: ' + content_type
            print report['msg']
            report['status'] = 0
            dfrecord['uid'] = ''
            dfrecord['fileurl'] = 'Not available'
            dfrecord['notes'] = report['msg']
            dfrecord['filetypeid'] = content_type
            report['newrow'] = dfrecord
            print(report)
            return report

        dfrecord['filetypeid'] = content_type
        
        #elif df_id==0:
        #    report['msg'] = 'Warning: file already uploaded on server: ' + infile.name
        #    print report['msg']
        #    report['status'] = 0
        #    return report
        #else:
        #    report['msg'] = 'Okay: file ready for uploadinng: ' + infile.name
        #    print report['msg']
        #    report['status'] = 0
        #    #return report
        
        # Step 2. Upload file to the designated server folder
        fullfilename = dfrecord['fullfilename']
        handle_uploaded_file(infile, fullfilename)
                
        # report = self.uploadSOP_storageToSeek(seekdb, originalfilename, content_type):        
        # rturn report        
                
        # Step 3. Store datafile into into Seek system by using Seek API
        userid = seekdb.user_seek['user_id']
        project_id = seekdb.user_seek['projectid']
        assay_id = None
        #tags = []
        #tags.append("")
        #tags.append("")
        tags = None
        
        #print('content_type:', content_type)
        dfrecord['content_type'] = content_type
    
        # use API to upload file into Seek
        #datatitle = request.POST.get('datatitle')
        datatitle = dfrecord['outfilename']
        #description = request.POST.get('description')
        description = 'File uploaded from DropZone'
        msg, status, df_info, datafile_url = seekdb.seekuploadSOP(
            #seekupload(
            #request.session.get('username'),
            #request.session.get('password'),
            #request.session.get('storage'),
            datatitle,
            fullfilename,
            infile.name,
            content_type,
            userid,
            project_id,
            assay_id,
            description,
            tags
        )
        if status==1:
            df_id, dfrecord = self.__searchSOP(seekdb, originalfilename)
            if df_id>0:
                dfrecord['notes'] = 'Successful'
            else:
                dfrecord['notes'] = 'Error: failed in searching for SOP in Seek.'
        else:
            dfrecord['id'] = ''
            dfrecord['uid'] = ''
            dfrecord['notes'] = 'Error: failed in uploading into Seek, available on server.'
    
        # Step 4. If we don't want to keep two copies of the data file on server,
        # remove temp folder and file
        #call(["rm", "-r", outfilename])
        #call(["rm", "-r", upload_full_path])
        
        report['msg'] = msg
        report['status'] = status
        report['df_info'] = df_info
        report['newrow'] = dfrecord
        return report    
        
    def downloadSOP_fromSeek(self, user_seek, uid):
        ''' Download a SOP file from Seek by using Seek API.
                
        Input:
            seekdb, SEEK DB API.
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            
            uid, also ='title' in sops table.
            
        Output:
            web url for downloading the file, or a not found page.
        '''
        msg = 'Waening: File to be found on server: ' + uid
        status = 0
        weblink = None
        
        username = user_seek['username']
        # All data files fro dropZone will be stored under the default project and default assay,
        # until it is included in the sample sheet for actual assay association.
        projectname = user_seek['projectname']
        institutionname = user_seek['institutionname']
        # lab abbreviation, three letter abbreviation of a lab
        lababbv = user_seek['lababbv']
        
        # Step 1. Get full path of the uploading folder
        # Lab folder, such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab"
        labfolder = lababbv
            
        upload_full_path_labroot = os.path.join(settings.SEEK_DATAFILE_ROOT, labfolder)
        if not os.path.exists(upload_full_path_labroot):
            msg = 'Error: File not found on server: ' + uid
            return msg, status, weblink
        
        return msg, status, weblink        
        
        
    def downloadSOP_fromStorage(self, user_seek, uid):
        ''' Download a SOP file from the storage server.
                
        Input:
            seekdb, SEEK DB API.
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            
            uid, also ='title' in sops table.
            
        Output:
            web url for downloading the file, or a not found page.
        '''
        msg = 'Waening: File to be found on server: ' + uid
        status = 0
        weblink = None
                
        constraint = {"title":uid}
        diclist = self.queryRecordsByConstraint(constraint)
        if diclist is None or len(diclist)==0:
            msg = 'Error: SOP file UID not found in DB: ' + uid
            return msg, status, weblink
        elif len(diclist)>1:
            msg = 'Error: More than one SOP file found for the UID: ' + uid
            return msg, status, weblink
        
        record = diclist[0]
        #print('Data file record:', record)
        #contributor_id = self.retrieveFieldValue(asset_id, 'contributor_id')
        contributor_id = record['contributor_id']
        print("contributor_id:", contributor_id)
        
        seekdb = SeekDB(user_seek['server'], user_seek['username'], user_seek['password'])
        userInfo, status, msg = seekdb.getUserInfo(contributor_id)
        if not status:
            return msg, status, weblink
        
        username = user_seek['username']
        #lababbv, upload_full_path = self.__getUploadPath(user_seek)
        lababbv, upload_full_path = self.__getUploadPath(userInfo)

        outfilename = self.__defineUploadFilename(username, None, uid)
        fullfilename = os.path.join(upload_full_path, outfilename)
        weblink = fullfilename
        weblink = weblink.replace(settings.SEEK_DATAFILE_ROOT, settings.SEEK_DATAFILE_ROOT_WEBLINK)
        print('weblink:', weblink)
        
        if not os.path.isfile(fullfilename):
            msg = 'Warning: File not found on server: ' + fullfilename
            print(msg)
            return msg, status, weblink
 
        if not os.path.exists(fullfilename):
            msg = 'Warning: File not found on server: ' + fullfilename
            print(msg)
            return msg, status, weblink
        
        status = 1
        msg = fullfilename
        return msg, status, weblink


###################  below are to be modified
    
    def __getDatafileUrl(self, filename):
        ''' Return the absolute url including the server name for accessing a data file.
        For example, a relative path looks like "/themes/SmartAdmin/static/media/uploads/"
        An absolute url includes the server name in front:
            'http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads/'
            url = 'http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads/filename'
        
        On PRO server, it will be,
            url = 'http://fair.mit.edu/bmc/seek/filename'
        whose absolute path is,
            "/net/bmc-pub10/data1/bmc/seek/"
        '''
        link = settings.SEEK_DATAFILE_ROOT_WEBLINK + filename
        #url = 'http://fairdata.mit.edu:8010' + link
        url = link
        #url = "<a href='/seek/sample/id=" + str(id) + "/'  target='_blank'>" + str(id) + "</a>"
        url2 = "<a href='" + link + "'  target='_blank'>" + url + "</a>"
        return url
        
    def filesGetUIDs(self, seekdb, allFiles):
        ''' Gien a list of file names that have been uploaded through the DropZone,
        retrieve their information afterwards.
        
        Input:
            seekdb: the seekdb API for a login user.
            allFiles: the list of original file names uploaded from the dropZone.
            
        Output:
            data={}, a dictionary with information about those files.
        '''
        #variable = "Hello, world. You're at the door of filesGetUIDs."
        #print variable
        #ret = request.GET
        #allFiles = json.loads(ret['allfiles'])
        #print allFiles
        diclist = []
        index = 0
        for originalfilename in allFiles:
            index += 1
            dici = self.__defineUploadPath(seekdb.user_seek, originalfilename)
            diclist.append(dici)
    
        #print(diclist)
    
        datenow = str(datetime.datetime.now().strftime("%Y-%m-%d_%H"))
        filename = 'datafile-upload-feedback-' + datenow + '.csv'
        #filename = 'samples_upload_feedback.xls'
        feedbackfile = DOWNLOAD_DIRECTORY + filename
        link = DOWNLOAD_DIRECTORY_LINK + filename
    
        headers = ['id', 'uid', 'originalname', 'fileurl']
        saveCsvfile(feedbackfile, headers, diclist)
    
        status = 1
        msg = 'okay'
        data = {'message':msg, 'status':status, 'link':link}
        data["allrows"] = index
        data["total"] = index
        data['rows'] = diclist
        return data
        
    def storeDataFile(self, username, sampleType, record, attributeInfo, uploadEnforced=False):
        ''' Store one record from input excel file for batch uploading.
        
        Input
            record, a dictionary from sample sheet for uploading.
            attributeInfo, the list of sample attributes defined in Seek system for this sample type.
            uploadEnforced, if False, only run test; if True, forcefully upload the rcord into DB.
        
        Output
            msg, any message
            status, whether or nor the test passes.
        '''
        if not self.__notEmptyLine(record):
            #msg = 'Error: record for uploading empty in ' + sampleType
            print(msg)
            return msg, 0, None
        
        # prepare requuired fields for the sample
        headers_required = attributeInfo['headers_required']
        
        # Verify whether the record for uploading has all required fields
        msg_required, meetRequired = self.__verifyRequiredFields(record, headers_required)
        if not meetRequired:
            msg = 'Error: ' + msg_required
            print(msg)
            return msg, 0, None
                
        #keysup = [x.upper() for x in record.keys()]
        if 'UID' not in record.keys():
            msg = 'Error: Sample record does not have a UID field.'
            print(msg)
            return msg, 0, None
        
        record_new = self.__getRecord(username, record, attributeInfo)
        uid = record_new['title'] 
        #print(record_new)
        if not uploadEnforced:
            msg = 'Warning: Upload not enforced, test okay.'
            #print(msg)
            return 'Upload not enforced', 1, uid

        #print(record_new)
        #return 'Upload to be enforced', 1, uid   
        msg, status, sample_id = self.storeOneRecord(username, record_new)
        if status:
            self.__updateProject(username, sample_id)
        
        #print(msg, status, uid)
        return msg, status, uid
    
    def __getDatafilePID(self, dfurl):
        ''' Get the data files UID from a data file url.
        Input:
            dfurl, such as:
                "http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads/Default_Institution/Default_Project/DF-20200106-22_dbadmin_training-dataset.csv"
                
                where,
                    rooturl = 'http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads/'
                    labname = 'Default_Institution'
                    projectname = 'Default_Project'
                    filename = 'DF-20200106-22_dbadmin_training-dataset.csv'
        Output:
            UID = 'DF-20200106-22', which is automatically generated during data file uploading.
                where,
                    'DF' indicates the data file.
                    '20200106' is the date of uploading.
                    '22' is the primary key of the data file in Data_files table.
        '''
        terms = dfurl.split("/")
        filename = terms[-1]        #such as DF-20200106-22_dbadmin_training-dataset.csv
        
        ids = filename.split("_")   
        uid = ids[0]                #such as DF-20200106-22
        
        pids = uid.split('-')
        pid = pids[-1]              #such as 22
        
        try:
            id = int(pid)    
        except:
            id = -1
        return id
    
    def processSampleDatafile(self, user_seek, sampleType, dfurl, diclist_assay):
        ''' Test and process data files listed iin the sample sheet.
        Input:
            dfurl, such as
                "http://fairdata.mit.edu:8010/themes/SmartAdmin/static/media/uploads/" or 
                "http://fair.mit.edu/labname/projectname/filename",
                
                
                http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads/Default_Institution/Default_Project/DF-20200106-22_dbadmin_training-dataset.csv
            username,
            sampleType, for which sample type the data file shold be associated, such as 'D.FLOW', 'MUS', 'TIS' etc
            diclist_assay, 
        Output:
            
        
        For example, the following columns may be included in a sample sheet:
            Image Name              File URL
            19.05.21_19-194_LL.tif  http://fairdata.mit.edu:8010/themes/SmartAdmin/static/media/uploads/19.05.21_19-194_RL.tif
            19.05.21_19-194_RL.tit  http://fairdata.mit.edu:8010/themes/SmartAdmin/static/media/uploads/19.05.21_19-194_LL.tif

        where
            "File URL" is an link to a data file that should be defined in Seek system.
            
        The protocol for processing such association is,
            1. The attribute for the "File URL" in the table above is defined as "URI" in the sample_attribute_types table.
            2. If the string in the URI column matchs the prefix for the Seek fileStore or the Seek storage server, such as 
                "http://fairdata.mit.edu:8010/themes/SmartAdmin/static/media/uploads/" or 
                "http://fair.mit.edu/labname/projectname/filename", 
                which is predefined for each Seek system, the content of the URI will be processed as the url for a data file;
            3. The url for the data file will be evaluated in the following scenario:
                3a. the data file for the url is already uploaded to the storage server and defined into Seek system by using the File DropZone;
                3b. the data file for the url is uploaded manually to the storage server but yet not defined in the Seek system;
                3c. the data file for the url is neither uploaded nor defined in the Seek system;
                3d. the data file for the url points to an external file on external server.
        '''
        print('processSampleDatafile')
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        msg = 'To be implemented!'
        status = 0
    
        # such as "http://server:port/sops/"
        dfurl_prefix = settings.SEEK_URL + "/sops/"
    
        # Step 1. Check whether the string in the URI column matchs the prefix for the Seek fileStore or the Seek storage server,
        # such as "http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads"
        rooturl = settings.SEEK_DATAFILE_ROOT_WEBLINK
        
        if dfurl is None or len(dfurl)==0:
            msg = 'Warning: Data file url not available in Seek system thus ignored: ' + dfurl
            print msg
            status = 0
            return msg, status
        elif dfurl_prefix in dfurl:
            # such as dfurl="http://server:port/sops/23"
            if dfurl[-1]=="/":
                # remove the last "/'
                dfurl = dfurl[:-1]
            terms = dfurl.split("/")
            # such as ['http:','', 'server:port', 'sops', '23']
            id = terms[-1]
            try:
                dfid = int(id)
            except:
                dfid = None
        elif rooturl not in dfurl:
            msg = 'Warning: Data file url not available in Seek system thus ignored: ' + dfurl
            print msg
            status = 0
            return msg, status
        else:
            # data file on storage server but not in Seek
            dfid = None
            # Step 2. Get the data file id for the dfurl
            # such as 'DF-20200106-22', where '22' is the primary key of the data file in Data_files table.
            #dfid = self.__getDatafilePID(dfurl)
        
        if dfid is None or dfid<=0:
            msg = 'Warning: Data file UID not valid thus ignored: ' + dfurl
            print msg
            status = 0
            return msg, status
        
        # Step 3. Associate the data file id with the sample_id and the assay_id
        assay_assets = DBtable_assay_assets("DEFAULT")
        msg, status = assay_assets.storeDatafile_assay_asset(user_seek, dfid, sampleType, diclist_assay)                 
        return msg, status
    
    def reformatDataForClient(self, jdata):
        ''' Reformat the list of records for shown on dataGrid Table.
        Input
            jdata=[record1, record2,...], a list of records
            
        Output
            jdata_new, a revised list of records.
            
        Notes
            This is a virtual method provided for overridinng in the child class, for example,
        '''
        dbcb = DBtable_content_blobs("DEFAULT")
        fdata = dbcb.retrieveFileList('', "Sop")
        fdatadic = {}
        for fi in fdata['rows']:
            aid = fi['asset_id']
            fdatadic[aid] = fi
        
        jdata_new = []
        for data in jdata:
            #datadic = data
            datadic = {}
            #datadic['id'] = self.__getSeeklink('', data['id'])
            datadic['id'] = data['id']
            datadic['uid'] = data['title']
            datadic['title'] = data['title']
            datadic['fileurl'] = self.__getWeblink(data['title'])
            #datadic['id'] = self.__getSeeklink('', data['id'])
            if data['id'] in fdatadic:
                fi = fdatadic[data['id']]
                datadic['originalname'] = self.__getSeeklink(fi['original_filename'], data['id'])
                datadic['checksum'] = fi['md5sum']
                datadic['filesize'] = sizeof_fmt(fi['file_size'])
                
            jdata_new.append(datadic)
        
        #jdata_new = jdata
        return jdata_new
    
    def retrieveRecords(self, user_seek, filtersdic):
        ''' Retrieve a list of records and show is in a dataGrid on the front page.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            filtersdic, filter parameters from the dataGrid.
        
        '''
        jdata, footer, total = self.db.retrieve_table_list(self.tablemodel, self.primaryField, filtersdic, self.fieldMapping)
        print('total:', total)
        jdata_new = self.reformatDataForClient(jdata)
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data
    
    
    def getFile(self, user_seek, id):
        ''' Find the data file for download, given
        Input:
            id, the primary key of 'data_files' table.
        Output: 
        '''
        fullfilename = ''
        filename = ''
        status = 0
        msg = 'Error: file not found.'
        if id is None or int(id)<=0:
            return fullfilename, filename, status, msg
        
        record = self.getOneRecord(id)
        if record is None:
            return fullfilename, filename, status, msg
            
        #print('Data file record:', record)
        #contributor_id = self.retrieveFieldValue(asset_id, 'contributor_id')
        contributor_id = record['contributor_id']
        print("contributor_id:", contributor_id)
        
        seekdb = SeekDB(user_seek['server'], user_seek['username'], user_seek['password'])
        userInfo, status, msg = seekdb.getUserInfo(contributor_id)
        if not status:
            msg = "Error: " + msg
            return fullfilename, filename, status, msg
        
        #username = user_seek['username']
        #lababbv, upload_full_path = self.__getUploadPath(user_seek)
        lababbv, upload_full_path = self.__getUploadPath(userInfo)
        outfilename = record['title']
        filename = outfilename
        
        fullfilename = os.path.join(upload_full_path, outfilename)
        weblink = fullfilename
        weblink = weblink.replace(settings.SEEK_DATAFILE_ROOT, settings.SEEK_DATAFILE_ROOT_WEBLINK)
        print('weblink:', weblink)
        
        if not os.path.isfile(fullfilename):
            msg = "Error: file not found:" + fullfilename
            print(msg)
            status = 0
            return fullfilename, filename, status, msg
 
        if not os.path.exists(fullfilename):
            msg = "Error: file not found:" + fullfilename
            print(msg)
            return fullfilename, filename, status, msg
        
        status = 1
        return fullfilename, filename, status, msg
    
    def download(self, user_seek, allids, downloadallterms):
        ''' Function to overload the same one in dbtable.py.
            Batch download files.
        
        Input:
            user_seek, user info
            allids, a list of ids in 'data_files' table for batch download of files.
            downloadallterms, optional, not in use.
        
        Output:
            
        
        '''
        msg = "Error: Download not successful."
        link = " "
        status = 1
        
        datenow = str(datetime.datetime.now().strftime("%Y-%m-%d_%H"))
        filename = 'sops-' + datenow + '.zip'
        print "generate zipped file", filename
        zipfilename = DOWNLOAD_DIRECTORY + filename
        link = DOWNLOAD_DIRECTORY_LINK + filename
        
        zf = zipfile.ZipFile(zipfilename, mode='w')
        msg = "Start generating zip file"
        try:
            msg = ''
            for id in allids:
                fullfilenamei, filenamei, statusi, msgi = self.getFile(user_seek, id)
                if statusi==0:
                    msg += msgi + '\n'
                    status = 0
                else:
                    zf.write(fullfilenamei, filenamei)
                    #msg = "Generating " + filename
        finally:
            print 'closing'
            zf.close()
        
        return msg, status, link
    
    
    def publishSOPs(self, user_seek, sdb, user, sop_ids, assay_id, project_id):
        ''' Publish SOPs from local Seek system to the remote Seek server.
        Input:
            user_seek, local user info.
            sdb, remote Seek server API class.
            user, remote Seek user.
            sop_ids, SOP ids in local Seek system.
            assay_id, assay id in the remote Seek system.
            project_id, project id in the remote Seek system.
        
        Output:
            
        
        '''
        status = 1
        msg = ''
        headers = None
        diclist = []
        for sop_id in sop_ids:
            record_cb = {}
            record_cb['id'] = sop_id
            record_cb['assay_id'] = assay_id
            record_cb['project_id'] = project_id
            record_cb['title'] = 'undefined'
            
            dfrecord = self.getOneRecord(sop_id)
            if dfrecord is None:
                status = 0
                record_cb['status'] = 0
                record_cb['msg'] = 'Protocol file not found'
                msg += record_cb['msg'] + '<br/>'
                diclist.append(record_cb)
                continue
            
            record_cb['title'] = dfrecord['title']
            
            fullfilename, filename, statusi, msgi = self.getFile(user_seek, sop_id)
            record_cb['fullfilename'] = fullfilename
            record_cb['filename'] = filename
            record_cb['status'] = statusi
            record_cb['msg'] = msgi
            if not statusi:
                status = 0
                msg += msgi + '<br/>'
                diclist.append(record_cb)
                continue
        
            datatitle = dfrecord['title']
            content_type = ''
            dbcb = DBtable_content_blobs("DEFAULT")
            diclist_blobs = dbcb.getRecord(sop_id, 'Sop')
            if diclist_blobs is not None:
                content_type = diclist_blobs[0]['content_type']
            record_cb['content_type'] = content_type
            #record_cb['msg'] = content_type
            
            userid = user['user_id']
            description = 'File published through API'
            tags = None
            
            msgi, statusi, sop_info, datafile_url = sdb.seekuploadSOP(
                #seekupload(
                #request.session.get('username'),
                #request.session.get('password'),
                #request.session.get('storage'),
                datatitle,
                fullfilename,
                filename,
                content_type,
                userid,
                project_id,
                assay_id,
                description,
                tags
            )
            
            record_cb['status'] = statusi
            record_cb['msg'] = msgi
            if statusi==0:
                status = 0
                msg += msgi + '<br/>'
            else:
                # check the checksum of file
                record_blob = sop_info["attributes"]["content_blobs"][0]
                record_blob['url'] = weburl
                md5sum_published = record_blob['md5sum']
                
                import hashlib
                md5sum = hashlib.md5(open(fullfilename,'rb').read()).hexdigest()
                if md5sum_published!=md5sum:
                    status = 0
                    msgi = 'Error: File checksum on remote server ' + str(md5sum_published) + ' does not match the local record ' + md5sum
                    msg += msgi + '<br/>'
                    record_cb['status'] = 0
                    record_cb['msg'] = msgi
            
            diclist.append(record_cb)
        
        data = {}
        data['msg'] = msg
        data['status'] = status
        data['link'] = ''
        data['ptype'] = 'Sop'
        data['diclist'] = diclist
        reportData = simplejson.dumps(data)
        return reportData
        
                
        
