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
import time, json
import simplejson
import logging
logger = logging.getLogger(__name__)

from .models import Sample_attribute_types
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile

from dmac.conversion import toDateClass, is_numeric, toFloat, toBinaryTinyInt, toString, convertDicToOptions

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
SAMPLEATTRIBUTE_TYPE_MAPPING = {
}

# Default values for Sample table
ATTRIBUTETYPE_DEFAULT = {
}

class DBtable_attributetype(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        attribute = DBtable_attributetype("DEFAULT")
        return attribute.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sample"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'sample_attribute_types'
        self.tablemodel = Sample_attribute_types
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'title',
            'base_type',
            'regexp',
            'created_at',
            'updated_at',
            'placeholder',
            'description',
            'resolution'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['title']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = SAMPLEATTRIBUTE_TYPE_MAPPING
    
    def getAttributeTypes(self):
        ''' Get a list of sample types.
        Output
            sampleTypes in the following format,
                [s1,s2,...], where
                    si = {"id":i, "title":'CEL", "gorup":"D"}
            
        '''
        options = self.getComboboxOptions(0, 'title')
        #print(options)
        options = json.loads(options)
        attributeTypes = {}
        for option in options:
            #print(option)
            title = option['title']
            id = option['id']
            attributeTypes[id] = title
        
        return attributeTypes
    
    def getAttributeTypeOptions(self):
        ''' Get a list of sample attribute types, in the format of ComboBox options.
        Output
            sample attribute types in the following format,
                [s1,s2,...], where
                    si = {"id":i, "title":'CEL"},
            which is further reformated into,
                    si = {"sample_attribute_type_id":i, "sample_attribute_type_title":'CEL"}
            
        '''
        options = self.getComboboxOptions(0, 'title')
        #print(options)
        options = json.loads(options)
        options_new = []
        for option in options:
            option_new = {}
            option_new['sample_attribute_type_id'] = option['id']
            option_new['sample_attribute_type_title'] = option['title']
            options_new.append(option_new)
            
        options = json.dumps(options_new)
        return options
        
        
        

