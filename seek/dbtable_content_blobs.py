'''
Created on July 12, 2016

@author: Huiming Ding
Email: huiming@mit.edu

Description:

This script is implemented for the Content_blobs database/table.

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
import logging
logger = logging.getLogger(__name__)

from .models import Content_blobs
from dmac.dbtable import DBtable

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
CONTENT_BLOBS_FILTER_MAPPING = {
}

# Default values for Sample table
CONTENT_BLOBS_DEFAULT = {
    #'id':'',
    'md5sum':'',
    'url':None,
    'uuid':'',
    'original_filename':'',
    'content_type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'asset_id':0,
    'asset_type':'DataFile',
    'asset_version':1,
    'is_webpage':0,
    'external_link':0,
    'sha1sum':'',
    'file_size':0,
    'created_at':'',
    'updated_at':''
}

class DBtable_content_blobs(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        content_blobs = DBtable_content_blobs("DEFAULT")
        return content_blobs.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_content_blobs"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'content_blobs'
        self.tablemodel = Content_blobs
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        #self.viewtablename = self.dbname + '.' + self.tablename
        self.viewtablename = self.tablemodel
        self.fields = [
            'id',
            'md5sum',
            'url',
            'uuid',
            'original_filename',
            'content_type',
            'asset_id',
            'asset_type',
            'asset_version',
            'is_webpage',
            'external_link',
            'sha1sum',
            'file_size',
            'created_at',
            'updated_at'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['original_filename']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = CONTENT_BLOBS_FILTER_MAPPING
        self.excludeFields = []
        
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
    
    def searchFile(self, infilename, asset_typeIn=None):
        ''' Search Seek whether a data file has been uploaded previously.
        Input
            infilename: = original file name from the client side.
        
        Output
            diclist, a list of dictionaries/records from content_blobs table.
        
            asset_id, latest asset id
            asset_type, asset type
            asset_version, asset version, default 1.
            nassets, how many assets with the same original name and asset type.
        
        Criteria
            Only the following first two criteria are applied in the implementation of the script.
            
                1. same file name, applied;
                2. same login user, applied;
                3. file checksum, not applied;
                4. file time stamp, not applied;
                5. file size, not applied.
        '''
        # Step 1. Query content_blobs table whether the data file is already uploaded.
        constraint = {}
        constraint['original_filename'] = infilename
        if asset_typeIn is not None:
            constraint['asset_type'] = asset_typeIn
        diclist_cb = self.queryRecordsByConstraint(constraint)
        
        asset_id = None
        asset_type = None
        asset_version = None
        nassets = len(diclist_cb)
        if nassets==1:
            print("unqiue record found in content_blobs table")
            dici = diclist_cb[0]
            asset_id = dici['asset_id']
            asset_type = dici['asset_type']
            asset_version = dici['asset_version']
        elif nassets>1:
            print("multiple records found, choose the one with the highest version")
            version_max = -1
            for dici in diclist_cb:
                version_i = dici['asset_version']
                if version_i is None:
                    version_i = 0
                else:
                    version_i = int(version_i)
                    
                if version_i > version_max:
                    asset_id = dici['asset_id']
                    asset_type = dici['asset_type']
                    asset_version = version_i
        else:
            print("file not found in content blob")
            asset_id = None
            asset_type = None
            asset_version = None
            
        print "asset info: ", asset_id, asset_type, asset_version, nassets
        return asset_id, asset_type, asset_version, nassets
    
    def retrieveFileList(self, username, asset_type):
        ''' Retrieve a list of records.
        
         
        Input:
            user_seek,
            asset_type, such as "Document", "SampleType", "DataFile" or, "Sop"
        
        '''
        #filtersdic = dg.getDatagridFilters(ret)
        
        filtersdic = {}
        filtersdic['orderby'] = ''
        filtersdic['limit'] = ''
        filtersdic['suffix'] = ''
        filtersdic['startNo'] = 0
        filtersdic['endNo'] = 0
    
        #sqlquery_filter, filterRules = self.__getFilteringParameters(ret)
        filterRules = [{"field":"asset_type","op":"contains","value":asset_type}]
        if asset_type in ["Document", "SampleType", "DataFile", "Sop"]:
            sqlquery_filter = " asset_type='" + asset_type + "';"
        else:
            sqlquery_filter = " "
        
        filtersdic['sqlquery_filter'] = sqlquery_filter
        filtersdic['filterRules'] = filterRules
        
        data = self.retrieveRecords(username, filtersdic)
        return data
    
    def getRecord(self, asset_id, asset_typeIn):
        ''' Search Seek whether a data file has been uploaded previously.
        Input
            asset_id: = primary key for the asset type, such as Sample, data file or SOP
            asset_typeIn, one of 'DataFile', 'Sop', 'SampleType', and 'Document'
        Output
            diclist, a list of dictionaries/records from content_blobs table.
        
            asset_id, latest asset id
            asset_type, asset type
            asset_version, asset version, default 1.
            nassets, how many assets with the same original name and asset type.
            content_type
        
        Criteria
            Only the following first two criteria are applied in the implementation of the script.
            
                1. same file name, applied;
                2. same login user, applied;
                3. file checksum, not applied;
                4. file time stamp, not applied;
                5. file size, not applied.
        '''
        # Step 1. Query content_blobs table whether the data file is already uploaded.
        constraint = {}
        constraint['asset_id'] = asset_id
        constraint['asset_type'] = asset_typeIn
        diclist_cb = self.queryRecordsByConstraint(constraint)
        return diclist_cb