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
import simplejson
import logging
logger = logging.getLogger(__name__)

from .models import Permissions
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile
from dmac.conversion import getDefaultDateTime


# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
PERMISSIONS_FILTER_MAPPING = {
}

# Default values for Sample table
PERMISSIONS_DEFAULT = {
    #'id':'',
    'contributor_type':'Project',
    'contributor_id':None,
    'policy_id':None,
    'access_type':4,    #downloadable for anyone in the same project
    'created_at':getDefaultDateTime(),
    'updated_at':getDefaultDateTime()
}

class DBtable_permissions(DBtable):
    ''' The class abut all the information about the table sample_controlled_vocabs and sample_controlled_vocab_terms.
    
    Typical usage of the class
    
        permissions = DBtable_permissions("DEFAULT")
        return permissions.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_permissions"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'permissions'
        self.tablemodel = Permissions
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'contributor_type',
            'contributor_id',
            'policy_id',
            'access_type',    #downloadable for anyone in the same project
            'created_at',
            'updated_at'
        ]
        self.default = PERMISSIONS_DEFAULT
        # the unique constraint to find the primary key
        self.uniqueFields = []
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = PERMISSIONS_FILTER_MAPPING
        
    def createDefaultPermission(self, username, policy_id, project_id):
        ''' Add a default plicy into policies table for a sample,
        datafile etc.
        Input:
        
        Output:
        '''
        record = {}
        for key, value in self.default.items():
            record[key] = value
        
        record['contributor_id'] = project_id
        record['policy_id'] = policy_id
        
        msg, status, primarykey = self.storeOneRecord(username, record)
        return msg, status, primarykey
        
        