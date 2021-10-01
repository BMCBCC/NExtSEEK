'''
Created on July 12, 2016

@author: Huiming Ding
Email: huiming@mit.edu

Description:

This script is implemented for the Sample database/table.

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


from django.db.models import Q

from .models import Assay_assets
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile, load_excelfile_asdic
from dmac.conversion import getDefaultDate, toString, cleanString, getDefaultDate, getDefaultDateTime, convertDateListToString

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
ASSAY_ASSETS_FILTER_MAPPING = {
}

# Default values for Sample table
ASSAY_ASSETS_DEFAULT = {
    #'id':'',
    'version': 1,
    'created_at':'',
    'updated_at':'',
    'relationship_type_id':None,
    'direction':0
}


class DBtable_assay_assets(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        assay_assets = DBtable_assay_assets("DEFAULT")
        return assay_assets.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_assay_assets"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'assay_assets'
        self.tablemodel = Assay_assets
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'assay_id',
            'asset_id',
            'version',
            'created_at',
            'updated_at',
            'relationship_type_id',
            'asset_type',
            'direction'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['assay_id', 'asset_id', 'asset_type']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = ASSAY_ASSETS_FILTER_MAPPING
        self.excludeFields = []
        
    def storeSample_assay_asset(self, user_seek, sampleType, sample_id, diclist_assay):
        username = user_seek['username']
        
        print("storeSample_assay_asset")
        record_new = {}
        # Set initial values
        for field in self.fields:
            value = ''
            if field in ASSAY_ASSETS_DEFAULT:
                value = ASSAY_ASSETS_DEFAULT[field]
            record_new[field] = value
        
        record_new['asset_id'] = sample_id
        record_new['created_at'] = getDefaultDateTime()
        record_new['updated_at'] = getDefaultDateTime()
        record_new['asset_type'] = 'Sample'
        
        msg = ''
        status = 1
        for dici in diclist_assay:
            smapletypei = dici['SampleType']
            assay_id = int(dici['Assay'])
            direction = int(dici['Direction'])
            if smapletypei==sampleType:
                record_new['assay_id'] = assay_id
                record_new['direction'] = direction
                msgi, statusi, id = self.storeOneRecord(username, record_new)
                if not statusi:
                    msg += msgi + '\n'
                    status = 0
        return msg, status
        
    def storeDatafile_assay_asset(self, user_seek, datafile_id, sampleType, diclist_assay):
        '''
        Input:
            username,
            sampleType, for which sample type the data file shold be associated, such as 'D.FLOW', 'MUS', 'TIS' etc
            diclist_assay, 
        Output:
        '''
        username = user_seek['username']
        
        print("Datafile_assay_asset")
        record_new = {}
        # Set initial values
        for field in self.fields:
            value = ''
            if field in ASSAY_ASSETS_DEFAULT:
                value = ASSAY_ASSETS_DEFAULT[field]
            record_new[field] = value
        
        record_new['asset_id'] = datafile_id
        record_new['created_at'] = getDefaultDateTime()
        record_new['updated_at'] = getDefaultDateTime()
        record_new['asset_type'] = 'DataFile'
        
        msg = ''
        status = 1
        for dici in diclist_assay:
            assay_id = int(dici['Assay'])
            sampleTypeNow = dici['SampleType']
            record_new['assay_id'] = assay_id
            record_new['direction'] = 0
            if sampleTypeNow==sampleType:
                msgi, statusi, id = self.storeOneRecord(username, record_new)
                if not statusi:
                    msg += msgi + '\n'
                    print msg
                    status = 0
        return msg, status
    