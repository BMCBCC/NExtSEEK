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

import logging
logger = logging.getLogger(__name__)

from .seekapi import SeekAPI
from .models import Sample_types
from dmac.dbtable import DBtable
from dbtable_sampleattribute import DBtable_sampleattribute

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
SAMPLETYPE_FILTER_MAPPING = {
}

# Default values for Sampletype table
SAMPLETYPE_DEFAULT = {
}

#SAMPLE_TYPES = [ (qi.id, qi.title) for qi in Sample_types.objects.all()]
#class SampletypeForm(forms.Form):
#    sampletype = forms.ChoiceField(required=True, label="Sample Type", initial='', choices=SAMPLE_TYPES, widget=forms.Select())


class DBtable_sampletype(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        sampletype = DBtable_sampletype("DEFAULT")
        return sampletype.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sampletype"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'sample_types'
        self.tablemodel = Sample_types
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = []
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = SAMPLETYPE_FILTER_MAPPING
        
    def __getSampleTypes(self, id):
        ''' This is equivalent to self.getOptions(id)
        
            Not in use. For backup purpose only.
        '''
        queryset = self.tablemodel.objects.all()
    
        # the followinng format is for a Django form choiceField 
        #type_options = [ (qi.id, qi.title) for qi in queryset]
    
        # the following format is for an easyUI comboBox
        options = []
        if id==0:
            options.append({'id':0, 'title':'','selected':True})
            options += [ {'id':qi.id, 'title':qi.title} for qi in queryset]
        else:
            options.append({'id':0, 'title':''})
            for qi in queryset:
                dici = {'id':qi.id, 'title':qi.title}
                if int(qi.id)==int(id):
                    dici['selected'] = True
                options.append(dici)
    
        #print(options)
    
        # the following format is good for returning to the client side,
        # and then being loaded into a EasyUI ComboBox as
        #   var type_options = {{ report.type_options|safe }};
        #   $('#id_cc2').combobox('reload', type_options)
        return simplejson.dumps(options)
        
    def getSamplePage(self, sampletype_id, server, username, password):
        ''' use Seek API to get the html page with sample info. 
        
        '''
        seekapi = SeekAPI(server, username, password)
        if sampletype_id>0:
            seek_url = "/sample_types/" + str(sampletype_id) + "/samples/"
            #print(seek_url)
            bodyhtml = seekapi.getPageRequests(seek_url)
        else:
            bodyhtml = '<div>Select the sample type from the ComboBox to get the innformation of samples.</div>'
        return bodyhtml
        
    def getSampleTypeID(self, sampleType_title):
        ''' Get the primary key from Sample_types table, given
        Input
            sampleType_title, the title of a sample type, such as,
                DNA, for DNA sample, or
                DNA_1, for DNA sample as parent sample
                DNA_2, for DNA sample as child sample.
                
        Output
            id, the primary key in Sample_types table
        '''
        if '_' in sampleType_title:
            # such as DNA_1, DNA_2 etc, where _1 or _2 indictes more than one same sample type in an assay sheet.
            terms = sampleType_title.split('_')
            sampleType_title = terms[0]
        
        return self.db.getPrimarykey(self.tablemodel, 'title', sampleType_title)
        
    def retrieveAttributes(self, sampleTypes):
        ''' Get the list of sample attributes.
        Input:
            sampleTypes, an ordered list of titles of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            diclist, such as [{'CEL':attributeInfo}, ...]
        '''
        #print("retrieveAttributes")
        sattr = DBtable_sampleattribute()
        
        diclist = []
        for title in sampleTypes:
            sampletype_id = self.getSampleTypeID(title)
            dici = {}
            if sampletype_id>0:
                dici[title] = sattr.getAttributeInfo(sampletype_id)
            else:
                dici[title] = None
            #print(title, dici[title])
            diclist.append(dici)
        
        return diclist
    
    def getSampleTypes(self):
        ''' Get a list of sample types.
        Output
            sampleTypes in the following format,
                [s1,s2,...], where
                    si = {"id":i, "title":'CEL", "gorup":"D"}
            
        '''
        sampletype_id = 0
        options = self.getComboboxOptions(sampletype_id, 'title')
        #print(options)
        options = json.loads(options)
        options_new = []
        for option in options:
            #print(option)
            title = option['title']
            if "A." in title:
                option['group'] = "Analysis type"
            elif "D." in title:
                option['group'] = "Data type"
            else:
                option['group'] = "Experimental type"
            options_new.append(option)
        
        #refer to: https://www.geeksforgeeks.org/ways-sort-list-dictionaries-values-python-using-lambda-function/
        #options = sorted(options_new, key = lambda i: i['title'],reverse=True)
        # sort sample type in alphabet
        options = sorted(options_new, key = lambda i: i['title'])
        
        # sort sample types in three groups
        options_new = []
        for group in ["Experimental type", "Analysis type", "Data type"]:
            for option in options:
                groupi = option['group']
                if group==groupi:
                    options_new.append(option)
        
        options = json.dumps(options_new)
        return options
        
        
        
