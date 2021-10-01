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

from .models import Policies
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile
from dmac.conversion import getDefaultDateTime

from .dbtable_permissions import DBtable_permissions

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
POLICIES_FILTER_MAPPING = {
}

# Default values for Sample table
POLICIES_DEFAULT = {
    #'id':'',
    'name':'default policy',
    #'sharing_scope':None,
    'access_type':0,
    #'use_whitelist':None,
    #'use_blacklist':None,
    'created_at':getDefaultDateTime(),
    'updated_at':getDefaultDateTime()
}

class DBtable_policies(DBtable):
    ''' The class abut all the information about the table sample_controlled_vocabs and sample_controlled_vocab_terms.
    
    Typical usage of the class
    
        policies = DBtable_policies("DEFAULT")
        return policies.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_policies"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'policies'
        self.tablemodel = Policies
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'name',
            'sharing_scope',
            'access_type',
            'use_whitelist',
            'use_blacklist',
            'created_at',
            'updated_at'
        ]
        self.default = POLICIES_DEFAULT
        
        # the unique constraint to find the primary key
        self.uniqueFields = []
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = POLICIES_FILTER_MAPPING
        
    def createDefaultPolicy(self,username, user_id, project_id):
        ''' Create a default plicy into policies table for a sample,
        datafile etc.
        Input:
            user_id, the user id or contributor_id, the login user id in people table.
        Output:
            msg, any message
            status, 0 or 1
            policy_id, primary key in policies table, which should never be invalid.
        '''
        record = {}
        for key, value in self.default.items():
            record[key] = value
        
        msg, status, policy_id = self.storeOneRecord(username, record)
        if policy_id>0:
            permission = DBtable_permissions("DEFAULT")
            msg, status, permission_id = permission.createDefaultPermission(username, policy_id, project_id)
        else:
            print(msg)
            policy_id = -1
        
        return msg, status, policy_id
        
        
        
        