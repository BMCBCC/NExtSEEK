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

from subprocess import call
import logging
logger = logging.getLogger(__name__)

from .seekdb import SeekDB
from .models import Data_files
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
DATA_FILES_FILTER_MAPPING = {
}

# Default values for Sample table
DATA_FILES_DEFAULT = {
    #'id':'',
    'contributor_id':0,
    'title':'',
    'description':'',
    'template_id':None,
    'last_used_at':'',
    'created_at':'',
    'updated_at':'',
    'version':1,
    'first_letter':'',
    'other_creators':'',
    'uuid':'',
    'policy_id':'',
    'doi':None,
    'license':'CC-BY-4.0',
    'simulation_data':0,
    'deleted_contributor':None         # use DB default null
}

# A DF UID such as "D.FLOW-200406WHI-1_dataoutput.txt", consists of sample_uid, such as "D.FLOW-200406WHI-1"
# and the file name, such as "dataoutput.txt" (space filled with "-"), delimited by DATA_FILE_UID_DELIMITER.
DATA_FILE_UID_DELIMITER = "_"


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
  
DATAFILE_ERRORCODE = {
    '001': 'Error: User not logged in.',
    '101': 'Warning: File already uploaded in Seek thus no update.',
    '201': 'Error: Data file UID not in right format: ',
    '202': 'Error: Data file uploading into datafile table failed: ',
    '203': 'Error: Data file uploading into content_blob table failed: ',
    '204': 'Warning: Data file and sample association not saved correctly into DB: ',
    '301': 'Error: Data file UID not in right format: ',
    '302': 'Error: Data file UID not found in DB: ',
    '303': 'Error: More than one data file found for the UID: ',
    '304': 'Error: User info not found in DB: ',
    '305': 'Error: File not found on server as a file: ',
    '306': 'Error: File not found on server: '
}  
  
class BatchSearchForm(forms.Form):
    keywords = forms.CharField(required=True, label='Keywords', widget=forms.Textarea )
    category = forms.ChoiceField(required=True, label="Category", initial='', choices=CATEGORY_CHOICES, widget=forms.Select())

class DBtable_data_files(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        dbdf = DBtable_data_files("DEFAULT")
        return dbdf.getDatafileUID(pid)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_data_files"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'data_files'
        self.tablemodel = Data_files
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'contributor_id',
            'title',
            'description',
            'template_id',
            'last_used_at',
            'created_at',
            'updated_at',
            'version',
            'first_letter',
            'other_creators',
            'uuid',
            'policy_id',
            'doi',
            'license',
            'simulation_data',
            'deleted_contributor'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['title']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = DATA_FILES_FILTER_MAPPING
        self.excludeFields = []
        
        # create a virtual form that is to be overrided.
        report = {}
        self.form = BatchSearchForm(report)
        self.formDefault = BATCHSEARCHFORM_DEFAULT
        self.formMapping = BATCHSEARCHFORM_MAPPING
    
    def __getUID(self, lababbv, filename, nassets=0, sample_uid=None):
        ''' Define the UID for a file uploaded from the DropZone.
        Input:
            lababbv: three letter abbreviation of a lab/institution, defined based on login user
                as user_seek['lababbv']
            
            filename, the corrected filename, in which any space has been replaced by '-'.
            nassets, how many same original filename exist in the content_blob table,
                which will be used as the increased version number for same
                original filename and type. Default is 0 sonext version is 1.
                
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.

        Output
            UID: such as DF-200413WHI-V1_filename.txt, where "DF" for data file,
                "20191213" is the date of uploading.
        '''        
        #print('getDatafileUID')
        
        uid_date = str(datetime.datetime.now().strftime("%Y%m%d"))  # such as '20200323'
        uid_date_2 = uid_date[2:]    # such as # such as '200323'
        next_version = nassets + 1
        
        #uid = 'DF' + '-' + uid_date_2 + lababbv + '-V' + str(next_version) + '_' + filename
        if sample_uid in filename:
            # this is to prevent the uid to be formed by additively adding the sample_uid to the original file name
            uid = filename
        else:
            uid = sample_uid + DATA_FILE_UID_DELIMITER + filename     # such as "D.FLOW-200406WHI-1_dataoutput.txt"
        print(uid)
        return uid

    def __defineUploadFilename(self, username, infilename, uid):
        ''' Define the data filename from the input file uploaded.
        Input:
            infilename, the input file name, such as "abcde.jpg"
        
        Output:
            outfilename, the filename defined after uploading.
            
        Notes:
            such as DF-200413WHI-V1_filename.txt, where "DF" for data file,
                "20191213" is the date of uploading.
        '''
        #outfilename = username + "_" + infilename
        #outfilename = os.path.join(upload_full_path, infilename)
        #while os.path.exists(outfilename):
        #    infilename = '_' + infilename
        #    outfilename = os.path.join(upload_full_path, infilename)
        #if uid is not None and len(uid)>0:
        #    outfilename = uid + "_" + username + "_v1_" + infilename
        #else:
        #    outfilename = username + "_v1_" + infilename
        
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
        #weblink = settings.SEEK_DATAFILE_ROOT_WEBLINK + labfolder + "/" + projectfolder + "/" + outfilename
        url = "/seek/datafile/uid=" + uid + "/"
        weburl = settings.SEEK_DATAFILE_SERVER + url
        weblink = '<a href="' + url + '" target="_blank">' + weburl + '</a>'
        #weblink = weburl
        return weblink, weburl
    
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
    
    
    def __defineUploadPath(self, user_seek, originalfilename, nassets=0, sample_uid=None):
        ''' Define the path and file name for uploading a data file.
        Input:
            projectname = user_seek['projectname'], such as 'ImpactTB'
            institutionname = user_seek['institutionname'], such as 'BENG lab'
            username = user_seek['username'], such as 'dbadmin'
            originalfilename, such as 'test.jpg'
            nassets, how many same original filename exist in the content_blob table,
                which will be used as the increased version number for same
                original filename and type. Default is 0 sonext version is 1.
            
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.

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
                'http://fairdata.mit.edu:8010/seek/datafile/uid=DF-200412WHI-V1_1234_USER_abcd.jpg/'
        
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
        #   The next primary key available in data_files table 
        #pid = self.getLatestPrimarykey()
        pid = 0
        # the UID for the current data file that will be uploaded.
        uid = self.__getUID(lababbv, infilename_corrected, nassets, sample_uid)
        # Get the destination file name, which is defined as
        # such as: UID_username_originalname
        outfilename = self.__defineUploadFilename(username, infilename_corrected, uid)
            
        # Step 3. Get the weblink to the file
        weblink, weburl = self.__getWeblink(uid)
        print('weblink:', weblink)
        
        dfrecord = {}
        dfrecord['id'] = pid
        dfrecord['uid'] = uid
        dfrecord['originalname'] = originalfilename
        #dfrecord['filetypeid'] = content_type
        dfrecord['weburl'] = weblink               # such as "<a href="">server/seek/datafile/uid=uid/</a>"
        dfrecord['fileurl'] = weburl                 # such as "server/seek/datafile/uid=uid/"
        dfrecord['notes'] = ''
        dfrecord['outfilename'] = outfilename
        dfrecord['upload_full_path'] = upload_full_path
        
        fullfilename = os.path.join(upload_full_path, outfilename)
        dfrecord['fullfilename'] = fullfilename
        return dfrecord
    
    def __getSeeklink(self, originalfilename, datafile_id):
        ''' Get the web link for downloading a SOP based on,
        
        Input:
            sop_id, the primary key in sobs table for the SOP, also the asset_id in content_blob table.
        
        Output:
            Seek link, a url for finding the file in Seek DB, such as
                http://seekserver/sops/12/
                
        '''
        seek_url = settings.SEEK_URL + "/data_files/" + str(datafile_id)
        seeklink = '<a href="' + seek_url + '" target="_blank">' + originalfilename + '</a>'
        #seeklink = '<a href="' + seek_url + '" target="_blank">' + str(datafile_id) + '</a>'
        return seeklink
    
    def __defineDatafile(self, seekdb, originalfilename, sample_uid):
        ''' Search Seek whether a data file has been uploaded previously, then
            define the record for uploading into DB.
        Input
            seekdb, SEEK DB API.
                username,  user_seek['username'] or request.session.get('username')
                userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            originalfilename: request.FILES['file'].name, the original file name from client side, which
                        may contain space in its name.
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.
        
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
        asset_id, asset_type, asset_version, nassets = dbcb.searchFile(originalfilename, 'DataFile')
        
        # the corrected file name is used then as the file name saved on the storage server.
        # copy the file to the storage server
        # assign next UID for uloading etc
        dfrecord = self.__defineUploadPath(seekdb.user_seek, originalfilename, nassets, sample_uid)
        return asset_id, asset_type, dfrecord
    
    def __searchDatafile(self, seekdb, originalfilename, sample_uid):
        ''' Search Seek whether a data file has been uploaded previously.
        Input
            seekdb, SEEK DB API.
                username,  user_seek['username'] or request.session.get('username')
                userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            originalfilename: request.FILES['file'].name, the original file name from client side, which
                may contain space in its name.
                infile: = request.FILES['file'], the data file to be uploaded and searched.
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.

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
        #originalfilename = infile.name
        infilename_corrected = correctFileName(originalfilename)
        
        # search thr file name in content_blob table
        asset_id, asset_type, dfrecord = self.__defineDatafile(seekdb, originalfilename, sample_uid)
        if asset_id is not None and asset_type=='DataFile':
            # data file found in content_blobs table
            # however, there are a few possible scenario:
            #   (a)the original file name has already been uploaded into the system by same user.
            #      In this case, asking for whether the second version is to be uploaded.
            #   (b)the original file name is found in content_blob table but not in data_file table,
            #      whcih indicates the data file has been uploaded previously but deleted manually in Seek afterwards.   
            #      Due to the bug in Seek, the entry for the data file is deleted from data_file but not from content_blob table.
            #      In this case, the current data file is regarded as a new file to upload.
            #   (c)the original data file is not found anywhere. In this case, the file is regarded as new file for upload.
            
            record = self.getOneRecord(asset_id)
            print('Data file record:', record)
            #contributor_id = self.retrieveFieldValue(asset_id, 'contributor_id')
            contributor_id = None
            if 'contributor_id' in record:
                contributor_id = record['contributor_id']
            print("contributor_id:", contributor_id, seekdb.user_seek['user_id'])
            if contributor_id is not None and int(contributor_id)==seekdb.user_seek['user_id']:
                # same user has same data file in Seek, return the datafile id
                dfrecord['id'] = asset_id
                dfrecord['uid'] = record['title']
                dfrecord['originalname'] = originalfilename
                dfrecord['originalname_url'] = self.__getSeeklink(originalfilename, asset_id)
                
                dfrecord['notes'] = 'Warning: already uploaded, no update enforced.'
                #dfrecord['fileurl'] = settings.SEEK_URL + "/data_files/" + str(asset_id)
                weblink, weburl = self.__getWeblink(record['title'])
                dfrecord['weburl'] = weblink
                dfrecord['fileurl'] = weburl                 # such as "server/seek/datafile/uid=uid/"
                # if we want to enforce the update of the data file,
                # the version should be next version, such as "user_v1_originalfilename"
                #   outfilename = dfrecord['outfilename']
                #   nextversion = '_' + str(int(asset_version) + 1) + '_'
                #   dfrecord['outfilename'] = outfilename.replace('_v1_', nextversion)
                return asset_id, dfrecord
    
        # Step 2. Query whether the same user has same data file available on server
        # For example, the data file size might exceed the size limit of Seek thus not uploaded in Seek, but available on server.
        return None, dfrecord
    
    
    def uploadFileLink_intoSeek(self, seekdb, infile, sample_uid):
        ''' Upload a web link to a data file into Seek system by using Seek API.
        Input:
            seekdb, SEEK DB API.
            infile: = request.FILES['file']
        
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])

            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.
            
        Output:
            report={}, a report with the following,
            report['msg'] = msg
            report['status'] = status
            report['df_info'] = df_info, the output from the API query "/data_files/id/", such as,
            report['newrow'] = dfrecord, a record for shown in the table on the DropZone page, which includes
                dfrecord['id'] = pid
                dfrecord['uid'] = uid
                dfrecord['originalname'] = infilename
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
        if seekdb.user_seek is None:
            report['msg'] = 'Error: user not loged in.'
            report['status'] = 0
            return report
        
        # Step 1. Define output file name etc,  and verify whether the  data file has been uploaded before.
        df_id, dfrecord = self.__searchDatafile(seekdb, infile.name, sample_uid)
        if df_id>0:
            report['msg'] = 'Warning: file already uploaded in Seek, no update: ' + infile.name
            print report['msg']
            report['status'] = 0
            report['newrow'] = dfrecord
            return report
        
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
        self.handle_uploaded_file(infile, fullfilename)
                
        # Step 3. Store datafile into into Seek system by using Seek API
        userid = seekdb.user_seek['user_id']
        project_id = seekdb.user_seek['projectid']
        assay_id = None
        #tags = []
        #tags.append("")
        #tags.append("")
        tags = None
        
        content_type = infile.content_type
        #print('content_type:', content_type)
        dfrecord['content_type'] = content_type
    
        # use API to upload file into Seek
        #datatitle = request.POST.get('datatitle')
        datatitle = dfrecord['outfilename']
        #description = request.POST.get('description')
        description = 'File uploaded from DropZone'
        msg, status, df_info, datafile_url = seekdb.seekupload(
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
            df_id, dfrecord = self.__searchDatafile(seekdb, infile.name, sample_uid)
            if df_id>0:
                dfrecord['notes'] = 'Successful'
            else:
                dfrecord['notes'] = 'Error: failed in uploading file into Seek.'
        else:
            dfrecord['id'] = ''
            dfrecord['uid'] = ''
            dfrecord['notes'] = 'Error: failed in uploading file into Seek.'
    
        # Step 4. If we don't want to keep two copies of the data file on server,
        # remove temp folder and file
        #call(["rm", "-r", outfilename])
        #call(["rm", "-r", upload_full_path])
        
        report['msg'] = msg
        report['status'] = status
        report['df_info'] = df_info
        report['newrow'] = dfrecord
        return report
        
    def uploadDF_toStorage(self, seekdb, infile, sample_uid, md5In):
        ''' Upload a data file into the storage server, which will be further uploaded into Seek.
            Refer to dbtable_sop.uploadSOP_toStorage()
        
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
            
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.
            
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
            1. Search for the filename in sample table to determine whether or not the data file belongs to a data-sample metadata.
            2. If yes, search for the sample type and the UID of the sample meta information,
               in which the data file is quoted. Use the sample UID to form the UID of the data
               file for uploading the file to the data lake on server;
            3. If no, the data file is rejected from further processing into Seek.
            4. A web-url link to the file is generated and returned;
            5. The information about the data file together with its web-link is stored into the Seek system.
        '''
        print("uploadDF_toStorage")
        originalfilename = infile.name
        report = {}
        if seekdb.user_seek is None:
            report['msg'] = DATAFILE_ERRORCODE['001']
            report['status'] = 0
            dfrecord = {}
            dfrecord['uid'] = ''
            dfrecord['originalname'] = originalfilename
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        content_type = infile.content_type
        ''' No limit on the type of a data file
        if content_type not in FILETYPES_SOP_SUPPORTED:
            report['msg'] = 'Warning: not one of supported pdf, Word, Excel or txt files: ' + content_type
            print report['msg']
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
        '''
        
        # Step 1. Define output file name etc,  and verify whether the  data file has been uploaded before.        
        df_id, dfrecord = self.__searchDatafile(seekdb, originalfilename, sample_uid)
        print('df_id:', df_id, dfrecord)
        dfrecord['content_type'] = content_type
        
        # Step 2. Upload file to the designated server folder, regardles whether the file is already on server and in Seek.
        fullfilename = dfrecord['fullfilename']
        #handle_uploaded_file(infile, fullfilename)
        if df_id>0:
            #report['msg'] = 'Warning: File already uploaded in Seek: ' + infile.name
            report['msg'] = DATAFILE_ERRORCODE['101']
            print report['msg']
            report['status'] = -1
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        handle_uploaded_file(infile, fullfilename)
        
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
    

        
        
    def uploadDF_storageToSeek(self, seekdb, originalfilename, content_type, df_uid, weburl, istest=False):
        ''' Upload a data file from the storage server into Seek system by using Seek API.
        
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
            
            df_uid, such as "D.FLOW-200406WHI-1_dataoutput.txt", the data file UID, defined in the
                first step of DF uploading from client side to the storage server (data lake).
                It consists of sample_uid, such as "D.FLOW-200406WHI-1" and the file name,
                such as "dataoutput.txt" (space filled with "-"), delimited by "_".
            
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
        print("uploadDF_storageToSeek")
        report = {}
        if DATA_FILE_UID_DELIMITER not in df_uid:
            msg = DATAFILE_ERRORCODE['201'] + df_uid
            report['msg'] = msg
            report['status'] = status
            report['df_info'] = df_info
            report['newrow'] = {'notes':msg}
            return report
        
        terms = df_uid.split(DATA_FILE_UID_DELIMITER)
        sample_uid = terms[0]

        '''
        df_id, asset_type, dfrecord = self.__defineDatafile(seekdb, originalfilename, sample_uid)
        if df_id>0:
            report['msg'] = 'Warning: file already uploaded in Seek, forced update: ' + originalfilename
            print report['msg']
            report['status'] = 0
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            
            # Same original filename exists in DB,
            # however, forced upload is allowed according to user side confirmation.
            #return report
        '''
        dfrecord = self.__defineUploadPath(seekdb.user_seek, originalfilename, 0, sample_uid)
        
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
        
        if istest:
            print('sample_uid: %s'%sample_uid)
            print('userid: %s'%userid)
            print('project_id: %s'%project_id)
            print('content_type: %s'%content_type)
            print('datatitle: %s'%datatitle)
            
            #report['msg'] = 'Just a test for uploadDF_storageToSeek'
            #report['status'] = 0
            #return report                   
        
        
        #msg, status, df_info, datafile_url = seekdb.seekupload(
        msg, status, df_info, datafile_url = seekdb.seekupload_dfurl(
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
            tags,
            weburl
        )
        if status==1:
            # update content_blob for this data file with the weburl
            record_cb = df_info["attributes"]["content_blobs"][0]
            record_cb['url'] = weburl
            #record_cb['md5sum'] = self.getmd5sum(df)
            #record_cb['sha1sum'] = self.getsha1sum(df)
            #record_cb['size'] = self.getsize(df)
            record_cb['is_webpage'] = 1
            record_cb['external_link'] = 1
            dbcb = DBtable_content_blobs("DEFAULT")
            msg, status, cb_id = dbcb.storeOneRecord(seekdb.user_seek['username'], record_cb)
            if status:
                df_link = df_info["attributes"]["versions"][0]['url']
                dfrecord = {}
                dfrecord['id'] = df_info['id']
                dfrecord['uid'] = df_uid
                dfrecord['originalname'] = originalfilename
                #dfrecord['filetypeid'] = content_type
                dfrecord['fileurl'] = weburl
                
                dfrecord['notes'] = df_link
                #dfrecord['notes'] = datafile_url
                
                #dfrecord['outfilename'] = fullfilename
                #dfrecord['upload_full_path'] = upload_full_path
                dfrecord['fullfilename'] = fullfilename
                
                if istest:
                    print('Skip sample update in a test run.')
                else:
                    from dbtable_sample import DBtable_sample
                    dbsample = DBtable_sample()
                    msg, status = dbsample.updateSampleDFurl(seekdb.user_seek['username'], sample_uid, originalfilename, df_link)
                    if not status:
                        msg = DATAFILE_ERRORCODE['204'] + msg
            else:
                msg = DATAFILE_ERRORCODE['203'] + msg
                dfrecord['notes'] = msg
            
            '''
            df_id, dfrecord = self.__searchDatafile(seekdb, originalfilename, sample_uid)
            #df_id = self.__getIDfromUID(datatitle)
            if df_id>0:
                dfrecord['originalname'] = originalfilename
                #dfrecord['originalname_url'] = self.__getSeeklink(originalfilename, df_id)
                dfrecord['id'] = self.__getSeeklink(originalfilename, df_id)
                dfrecord['notes'] = 'Successful'
            else:
                dfrecord['notes'] = 'Error: failed in uploading file into Seek.'
            '''
        else:
            dfrecord['id'] = ''
            dfrecord['uid'] = ''
            msg = DATAFILE_ERRORCODE['202'] + msg
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
        
    def uploadDFs_storageToSeek(self, seekdb, diclist):
        ''' Upload multiple data files from the storage server into Seek system by using Seek API
            in a sequential order.
            
            diclist: from datafile_table_embed.html
        '''
        report = {}
        report['msg'] = 'test uploadDF_storageToSeek()'
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
            df_uid = dici['uid']
            weburl = dici['fileurl']
            reporti = self.uploadDF_storageToSeek(seekdb, originalfilename, content_type, df_uid, weburl)
            newrows.append(reporti['newrow'])
            if reporti['status']==0:
                status = 0
                msg += reporti['msg'] + '\n'
        
        report['msg'] = msg
        report['status'] = status
        report['df_info'] = ''
        report['newrows'] = newrows
        return report     
        
    def downloadDF_fromStorage(self, user_seek, uid):
        ''' Download a data file from the storage server.
                
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
        
        if DATA_FILE_UID_DELIMITER not in uid:
            msg = DATAFILE_ERRORCODE['301'] + uid
            return msg, status, weblink
        
        constraint = {"title":uid}
        diclist = self.queryRecordsByConstraint(constraint)
        if diclist is None or len(diclist)==0:
            msg = DATAFILE_ERRORCODE['302'] + uid
            return msg, status, weblink
        elif len(diclist)>1:
            msg = DATAFILE_ERRORCODE['303'] + uid
            return msg, status, weblink
        
        record = diclist[0]
        #print('Data file record:', record)
        #contributor_id = self.retrieveFieldValue(asset_id, 'contributor_id')
        contributor_id = record['contributor_id']
        print("contributor_id:", contributor_id)
        
        
        seekdb = SeekDB(user_seek['server'], user_seek['username'], user_seek['password'])
        userInfo, status, msg = seekdb.getUserInfo(contributor_id)
        if not status:
            msg = DATAFILE_ERRORCODE['304'] + msg
            return msg, status, weblink
        
        #username = user_seek['username']
        #lababbv, upload_full_path = self.__getUploadPath(user_seek)
        lababbv, upload_full_path = self.__getUploadPath(userInfo)
        outfilename = uid
        
        fullfilename = os.path.join(upload_full_path, outfilename)
        weblink = fullfilename
        weblink = weblink.replace(settings.SEEK_DATAFILE_ROOT, settings.SEEK_DATAFILE_ROOT_WEBLINK)
        print('weblink:', weblink)
        
        if not os.path.isfile(fullfilename):
            msg = DATAFILE_ERRORCODE['305'] + fullfilename
            print(msg)
            return msg, status, weblink
 
        if not os.path.exists(fullfilename):
            msg = DATAFILE_ERRORCODE['306'] + fullfilename
            print(msg)
            return msg, status, weblink
        
        status = 1
        return msg, status, weblink

###################  below are also in dbtable_sops.py
        
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
        print allFiles
        diclist = []
        index = 0
        for filename in allFiles:
            index += 1
            dici = self.__defineUploadPath(seekdb.user_seek, filename)
            diclist.append(dici)
    
        print(diclist)
    
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
    
        # such as "http://server:port/data_files/"
        dfurl_prefix = settings.SEEK_URL + "/data_files/"
    
        # Step 1. Check whether the string in the URI column matchs the prefix for the Seek fileStore or the Seek storage server,
        # such as "http://dmac.mit.edu:8010/themes/SmartAdmin/static/media/uploads"
        rooturl = settings.SEEK_DATAFILE_ROOT_WEBLINK
        
        if dfurl is None or len(dfurl)==0:
            msg = 'Warning: Data file url not available in Seek system thus ignored: ' + dfurl
            print msg
            status = 0
            return msg, status
        elif dfurl_prefix in dfurl:
            # such as dfurl="http://server:port/data_files/23"
            if dfurl[-1]=="/":
                # remove the last "/'
                dfurl = dfurl[:-1]
            terms = dfurl.split("/")
            # such as ['http:','', 'server:port', 'data_files', '23']
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
        fdata = dbcb.retrieveFileList('', "DataFile")
        #print(fdata)
        fdatadic = {}
        for fi in fdata['rows']:
            #print(fi)
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
            weblink, weburl = self.__getWeblink(data['title'])
            datadic['fileurl'] = weblink
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
    
    
    def moveDF_toStorage(self, seekdb, pathtofile, filename, sample_uid, istest=False):
        ''' Move a data file from a queue on the server into the storage server, which will be further uploaded into Seek.
            Modified from self.uploadDF_toStorage()
        
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
            
            sample_uid = sampleRecord['uuid'],the sample UID, by which a data file is binded to.
                sampleRecord, the dictionary of sample record plus the dic from json_metadata, to which this data file is referred.
            
            istest, if True, only run a test but not actually move the file
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
            1. Search for the filename in sample table to determine whether or not the data file belongs to a data-sample metadata.
            2. If yes, search for the sample type and the UID of the sample meta information,
               in which the data file is quoted. Use the sample UID to form the UID of the data
               file for uploading the file to the data lake on server;
            3. If no, the data file is rejected from further processing into Seek.
            4. A web-url link to the file is generated and returned;
            5. The information about the data file together with its web-link is stored into the Seek system.
        '''
        print("moveDF_toStorage")
        originalfilename = filename
        report = {}
        if seekdb.user_seek is None:
            report['msg'] = 'Error: user not loged in.'
            report['status'] = 0
            dfrecord = {}
            dfrecord['uid'] = ''
            dfrecord['originalname'] = originalfilename
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        content_type = 'To be defined'
        ''' No limit on the type of a data file
        if content_type not in FILETYPES_SOP_SUPPORTED:
            report['msg'] = 'Warning: not one of supported pdf, Word, Excel or txt files: ' + content_type
            print report['msg']
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
        '''
        # Step 1. Define output file name etc,  and verify whether the  data file has been uploaded before.        
        df_id, dfrecord = self.__searchDatafile(seekdb, originalfilename, sample_uid)
        print('df_id:', df_id, dfrecord)
        dfrecord['content_type'] = content_type
        
        # Step 2. Upload file to the designated server folder, regardles whether the file is already on server and in Seek.
        fullfilename = dfrecord['fullfilename']
        #handle_uploaded_file(infile, fullfilename)
        if df_id>0:
            #report['msg'] = 'Warning: File already uploaded in Seek: ' + infile.name
            report['msg'] = 'Warning: Data file already uploaded in Seek by same user'
            print report['msg']
            report['status'] = -1
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return report
        
        # move file from queue to storage server
        filename_inqueue = os.path.join(pathtofile, filename)
        print('filename_inqueue: %s'%filename_inqueue)
        
        md5pre = None
        if istest:
            print('Skip calculation of MD5 checksum.')
        #else:
            print('Calculate MD5 checksum.')
            md5pre = getFileChecksum(filename_inqueue, 'MD5')
            print('File MD5 checksum: %s'%md5pre)
        
        #handle_uploaded_file(filename_inqueue, fullfilename)
        #cmd = "mv " + filename_inqueue + " " + fullfilename
        cmdline = "cp " + filename_inqueue + " " + fullfilename
        print(cmdline)
                
        #seekapi = SeekAPI(None, None, None)
        #exitcode, out, err = seekapi.callCmdline(cmdline)
        try:
            call([cmdline], shell=True)
            status = True
        except:
            msg = "Error: " + cmdline
            status = False
        
        md5Now = None
        if istest:
            print('Skip verification of MD5 checksum.')
        #else:
            md5Now = getFileChecksum(fullfilename, 'MD5')
            print('Verification of MD5 checksum: %s'%md5Now)
            if md5Now!=md5pre:
                msg = 'Error: File MD5 checksum not match: ' + md5Now
                status = 0
            else:
                msg = 'File uploaded to storage server'
                status = 1
        
        if istest:
            #print('Skip deletion of file in queue.')
        #elif status:
            print('Deletion of file in queue: %s'%filename_inqueue)
            cmdline = "rm " + filename_inqueue
            print(cmdline)
            try:
                call([cmdline], shell=True)
                status = True
            except:
                status = False
                msg = "Error: " + cmdline
                print(msg)
        
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
        if status:
            report['msg'] = 'File uploaded to storage server'
            report['status'] = 1
        else:
            report['msg'] = msg
            report['status'] = 0
        dfrecord['notes'] = report['msg']
        report['newrow'] = dfrecord
        return report
    
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
        status = 1
        link = " "
        
        datenow = str(datetime.datetime.now().strftime("%Y-%m-%d_%H"))
        filename = 'datafiles-' + datenow + '.zip'
        print "generate zipped file", filename
        zipfilename = DOWNLOAD_DIRECTORY + filename
        link = DOWNLOAD_DIRECTORY_LINK + filename
        
        zf = zipfile.ZipFile(zipfilename, mode='w')
        msg = "Start generating zip file"
        try:
            msg = 'Error: '
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
    
    def publishDFs(self, user_seek, sdb, user, df_ids, assay_id, project_id):
        ''' Publish data files from local Seek system to the remote Seek server.
        Input:
            user_seek, local user info.
            sdb, remote Seek server API class.
            user, remote Seek user.
            df_ids, data file ids in local Seek system.
            assay_id, assay id in the remote Seek system.
            project_id, project id in the remote Seek system.
        
        Output:
            
        
        '''
        status = 1
        msg = ''
        headers = None
        diclist = []
        for df_id in df_ids:
            record_cb = {}
            record_cb['id'] = df_id
            record_cb['assay_id'] = assay_id
            record_cb['project_id'] = project_id
            record_cb['title'] = 'undefined'
            
            dfrecord = self.getOneRecord(df_id)
            if dfrecord is None:
                status = 0
                record_cb['status'] = 0
                record_cb['msg'] = 'Data file not found'
                msg += record_cb['msg'] + '<br/>'
                diclist.append(record_cb)
                continue
            
            record_cb['title'] = dfrecord['title']
            
            fullfilename, filename, statusi, msgi = self.getFile(user_seek, df_id)
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
            diclist_blobs = dbcb.getRecord(df_id, 'DataFile')
            if diclist_blobs is not None:
                content_type = diclist_blobs[0]['content_type']
            record_cb['content_type'] = content_type
            #record_cb['msg'] = content_type
            
            userid = user['user_id']
            description = 'File published through API'
            tags = None
            
            msgi, statusi, df_info, datafile_url = sdb.seekupload(
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
                record_blob = df_info["attributes"]["content_blobs"][0]
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
        data['ptype'] = 'Datafile'
        data['diclist'] = diclist
        reportData = simplejson.dumps(data)
        return reportData
        
        
        