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

from .models import Sample_attributes
from .dbtable_attributetype import DBtable_attributetype

from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile

from dmac.conversion import toDateClass, is_numeric, toFloat, toBinaryTinyInt, toString, getDefaultDate

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
SAMPLEATTRIBUTE_FILTER_MAPPING = {
}

# Default values for Sample table
SAMPLEATTRIBUTE_DEFAULT = {
}

class DBtable_sampleattribute(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        attribute = DBtable_sampleattribute("DEFAULT")
        return attribute.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sample"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'sample_attributes'
        self.tablemodel = Sample_attributes
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'title',
            'sample_attribute_type_id',
            'required',
            'created_at',
            'updated_at',
            'pos',
            'sample_type_id',
            'unit_id',
            'is_title',
            'template_column_index',
            'accessor_name',
            'sample_controlled_vocab_id',
            'linked_sample_type_id'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['title', 'sample_type_id']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = SAMPLEATTRIBUTE_FILTER_MAPPING
        
    
    def getAttributeInfo(self, sampleType_id):
        ''' Get the list of attributeInfo (fields) for a sample type.
        Input
            sampletype_id, the primary key for a sample type
            
        Output
            A dictionary of attributeInfo for the sample type, including
                attributeInfo['headers'], the list of attributeInfo (fields) for the sample;
                attributeInfo['headers_required'], a list of attributeInfo required;
                attributeInfo['sampletype'] = {}
                attributeInfo['attributeTypes'] = {'name':5, 'flowamount':7, 'FileReference':5, 'URI':19,...}
        '''
        attritype = DBtable_attributetype()
        attributeTypeNames = attritype.getAttributeTypes()
        #print(attributeTypeNames)
        
        
        diclist = self.db.retrieveRecords(self.tablemodel, 'sample_type_id', sampleType_id)
        print(diclist[0])
        
        from operator import itemgetter
        #newlist = sorted(diclist, key=itemgetter('template_column_index'))
        # sort attributeInfo according to 
        newlist = sorted(diclist, key=itemgetter('pos'))
        attributeInfo = {}
        headers = []    # a list of attribute names, such as 'Concentraion'
        #accessor_names = []  # a list of keys in the json_metadata, such 'concentration', which is only small cases.
        headers_required = []   # a list of attributeInfo required
        attributeTypes = {}     # such as {'name':5, 'flowamount':7, 'FileReference':5, 'URI':19,...}, where key is the sample attribute name, while nuber is the attribute type in sample_attribute_types table
        diclist_new = []
        for dici in newlist:
            #print(dici)
            field = dici['title']
            headers.append(field)
            
            isrequired = dici['required']
            if isrequired:
                headers_required.append(field)
                
            attributeTypes[field] = dici['sample_attribute_type_id']
            
            dici_new = {}
            dici_new['title'] = dici['title']
            dici_new['id'] = dici['id']
            dici_new['pos'] = dici['pos']
            atype_id = dici['sample_attribute_type_id']
            #print(atype_id)
            dici_new['sample_attribute_type_id'] = atype_id
            if atype_id in attributeTypeNames:
                dici_new['sample_attribute_type_title'] = attributeTypeNames[atype_id]
            elif int(atype_id) in attributeTypeNames:
                dici_new['sample_attribute_type_title'] = attributeTypeNames[int(atype_id)]
            else:
                dici_new['sample_attribute_type_title'] = ''
            #print(atype_id, dici_new['sample_attribute_type_title'])
            dici_new['required'] = toBinaryTinyInt(dici['required'])
            dici_new['is_title'] = toBinaryTinyInt(dici['is_title'])
            dici_new['sample_controlled_vocab_id'] = dici['sample_controlled_vocab_id']
            diclist_new.append(dici_new)
            
        #print(attributeInfo)
        attributeInfo['diclist'] = diclist_new
        attributeInfo['headers'] = headers
        attributeInfo['headers_required'] = headers_required
        
        attributeInfo['attributeTypes'] = attributeTypes
        
        from dbtable_sampletype import DBtable_sampletype
        sampletype = DBtable_sampletype("DEFAULT")
        attributeInfo['sampletype'] = sampletype.getOneRecord(sampleType_id)
        attributeInfo['sampleType_id'] = sampleType_id
        return attributeInfo
        
    def getAttributes(self, sampletype_id, valueSelected=''):
        """ Get a list of attributes for a sample_type id.
        Input:
            sampletype id.
            valueSelected, default '', the current attribute name selected.
        Output:
            attr_options = [
                {
                    'name': name1,
                    'attribute': attr1
                },
                {
                    'name': name2,
                    'attribute': attr2
                },
            ]
        """
        attributeInfo = self.getAttributeInfo(sampletype_id)
        headers = attributeInfo['headers']
        if len(headers)==0:
            msg = "Error: the sample type has no attribute defined. "
            status = 0
            options = []
        else:
            msg = "Attributes retrieved "
            status = 1
            attributeTypes = attributeInfo['attributeTypes']
            
            options = []
            # the following format is for an easyUI comboBox
            selected = False
            id = 0
            for header in headers:
                attributeType_id = attributeTypes[header]
                option = {}
                id += 1
                option['name'] = header
                #option['id'] = id
                option['attribute'] = header
                if str(attributeType_id)==str(valueSelected):
                    option['selected'] = True
                    selected = True
                
                options.append(option)
        
            # if the value selected is not on the list from DB,
            # such as id=0, which is a primary key noot available in DB table,  
            # add a default option for such value, such as set the text as '' 
            if not selected:
                # the option selected, such as id=0, is not available in DB table
                # add an option with '' and set it as the one selected
                option = {}
                option['name'] = valueSelected
                option['attribute'] = 'none'
                option['selected'] = True
            
                options = [option] + options
            
        #attrOptions = simplejson.dumps(options)
        attrOptions = options
        
        data = {'msg':msg, 'status': status, 'attrOptions':attrOptions}
        data['valueSelected'] = valueSelected
        if valueSelected=='yes':
            data['rows'] = attributeInfo['diclist']
        return data
        
    def getOperators(self, sampletype_id, attribute):
        """ Get a list of attributes for a sample_type id.
        Input:
            sampletype id.
            attribute,one of attribute names for a sample type.
        """
        print("sampletype_id:", sampletype_id)
        print("attribute:", attribute)
        
        attributeInfo = self.getAttributeInfo(sampletype_id)
        headers = attributeInfo['headers']
        if len(headers)==0:
            msg = "Error: the sample type has no attribute defined. "
            status = 0
            options = []
            data = {
                'msg':msg,
                'status': status,
                'filter_rule':options,
                'placeholder_start':'',
                'placeholder_end':'',
                'filter_type':''
            }
            return data
            
        attributeTypes = attributeInfo['attributeTypes']
        if attribute not in attributeTypes:
            msg = "Error: the sample attribute not available. "
            status = 0
            options = []
            data = {
                'msg':msg,
                'status': status,
                'filter_rule':options,
                'placeholder_start':'',
                'placeholder_end':'',
                'filter_type':''
            }
            return data    
        
        msg = "Attributes retrieved "
        status = 1    
        attributeType_id = attributeTypes[attribute]
        attributeType_id = int(attributeType_id)
        if attributeType_id==3 or attributeType_id==3:
            # float or integer
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'Equal','operator':'Equal'},
                {'name':'Not Equal','operator':'Not Equal'},
                {'name':'Less','operator':'Less'},
                {'name':'Greater','operator':'Greater'},
                {'name':'Between','operator':'Between'}
            ]
            # messages shown in the placeholders of input field for how to input start and end values.
            placeholder_start = 'numeric value'
            placeholder_end = 'numeric value'
            filter_type = 'numeric'
        elif attributeType_id in [5,6,7,8,9,10,11,12,13,14,19,20,21]:
            # string
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'Contain','operator':'Contain'},
                {'name':'Not Contain','operator':'Not Contain'}
            ]
            placeholder_start = 'string value'
            placeholder_end = 'not in use'
            filter_type = 'string'
        elif attributeType_id in [1,2]:
            # Date
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'Equal','operator':'Equal'},
                {'name':'Not Equal','operator':'Not Equal'},
                {'name':'Before','operator':'Before'},
                {'name':'After','operator':'After'},
                {'name':'Between','operator':'Between'}
            ]
            placeholder_start = 'mm/dd/year'
            placeholder_end = 'mm/dd/year'
            filter_type = 'date'
        elif attributeType_id==18:
            # controlled Voc
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'Contain','operator':'Contain'},
                {'name':'Not Contain','operator':'Not Contain'}
            ]
            placeholder_start = 'string value'
            placeholder_end = 'not in use'
            filter_type = 'string'
        elif attributeType_id==15:
            # bool
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'True','operator':'True'},
                {'name':'False','operator':'False'}
            ]
            placeholder_start = 'not in use'
            placeholder_end = 'not in use'
            filter_type = 'bool'
        else:
            # Seek strain or sample 
            options = [
                {'name':'No Filter','operator':'No Filter', 'selected':True},
                {'name':'Contain','operator':'Contain'},
                {'name':'Not Contain','operator':'Not Contain'}
            ]
            placeholder_start = 'string value'
            placeholder_end = 'not in use'
            filter_type = 'string'
            
        #attrOptions = simplejson.dumps(options)
        filter_rule = options
        data = {
            'msg':msg,
            'status': status,
            'filter_rule':filter_rule,
            'placeholder_start':placeholder_start,
            'placeholder_end':placeholder_end,
            'filter_type':filter_type
        }
        return data
    
    def filterString(self, values, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of string values based on the criteria.
         
        Input:
            values, a list of string values for filtering;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            a list of bool values whether values pass the criteria.
            
        '''
        passvalues = []
        if filter_rule=='Contain':
            for value in values:
                vi = toString(value)
                if filter_valueFrom in vi:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Not Contain':
            for value in values:
                vi = toString(value)
                if filter_valueFrom in vi:
                    passvalues.append(False)
                else:
                    passvalues.append(True)
        else:
            for value in values:
                passvalues.append(True)
        return passvalues  

    def filterBool(self, values, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of bool values based on the criteria.
         
        Input:
            values, a list of string values for filtering;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            a list of bool values whether values pass the criteria.
            
        '''
        #valueFrom = str(filter_valueFrom)
        #valueFrom = valueFrom.upper()
        #if valueFrom=='1' or valueFrom=='TRUE' or valueFrom=='YES' or valueFrom=='OK' or valueFrom=='OKAY':
        #    vf = True
        #else:
        #    vf = False
        
        passvalues = []
        if filter_rule=='True':
            for value in values:
                vi = toBinaryTinyInt(value)
                if vi==1:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='False':
            for value in values:
                vi = toBinaryTinyInt(value)
                if vi==1:
                    passvalues.append(False)
                else:
                    passvalues.append(True)
        else:
            for value in values:
                passvalues.append(True)
        return passvalues  

    def filterNumeric(self, values, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of string values based on the criteria.
         
        Input:
            values, a list of string values for filtering;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            a list of bool values whether values pass the criteria.
            
        '''
        print("filterNumeric: ", filter_rule, filter_valueFrom, filter_valueTo)
        valueFrom = toFloat(filter_valueFrom)
        passvalues = []
        if filter_rule=='Equal':
            for value in values:
                print(value, valueFrom)
                vi = toFloat(value)
                if vi==valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Not Equal':
            for value in values:
                vi = toFloat(value)
                if vi==valueFrom:
                    passvalues.append(False)
                else:
                    passvalues.append(True)
                
        elif filter_rule=='Less':
            for value in values:
                vi = toFloat(value)
                if vi<=valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Greater':
            for value in values:
                vi = toFloat(value)
                if vi>=valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Between':
            valueTo = toFloat(filter_valueTo)
            for value in values:
                vi = toFloat(value)
                if vi>=valueFrom and vi<=valueTo:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        else:
            for value in values:
                passvalues.append(True)
                
        return passvalues          

    def filterDate(self, values, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of string values based on the criteria.
         
        Input:
            values, a list of string values for filtering;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            a list of bool values whether values pass the criteria.
            
        '''
        valueFrom = toDateClass(filter_valueFrom)
        passvalues = []
        if filter_rule=='Equal':
            for value in values:
                vi = toDateClass(value)
                if vi is None:
                    passvalues.append(False)
                elif vi==valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Not Equal':
            for value in values:
                vi = toDateClass(value)
                if vi is None:
                    passvalues.append(True)
                elif vi==valueFrom:
                    passvalues.append(False)
                else:
                    passvalues.append(True)
                
        elif filter_rule=='Before':
            for value in values:
                vi = toDateClass(value)
                if vi is None:
                    passvalues.append(False)
                elif vi<=valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='After':
            for value in values:
                vi = toDateClass(value)
                if vi is None:
                    passvalues.append(False)
                elif vi>=valueFrom:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        elif filter_rule=='Between':
            valueTo = toDateClass(filter_valueTo)
            for value in values:
                vi = toDateClass(value)
                if vi is None:
                    passvalues.append(False)
                elif vi>=valueFrom and vi<=valueTo:
                    passvalues.append(True)
                else:
                    passvalues.append(False)
                    
        else:
            for value in values:
                passvalues.append(True)
                
        return passvalues    

    def filterValues(self, values, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of values based on the criteria.
         
        Input:
            values, a list of values for filtering;
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;

            filter_type, ='string', 'numeric', 'date' or 'bool'
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            a list of bool values whether values pass the criteria.
            
        '''
        attrdata = self.getOperators(sampletype_id, attribute)
        #print("attrdata: ", attrdata)
        filter_type = attrdata['filter_type']
        print("filterValues: ", attribute, filter_type, filter_rule, filter_valueFrom, filter_valueTo)
          
        if filter_type=='string':
            passvalues = self.filterString(values, filter_rule, filter_valueFrom, filter_valueTo)
        elif filter_type=='numeric':
            passvalues = self.filterNumeric(values, filter_rule, filter_valueFrom, filter_valueTo)
        elif filter_type=='date':
            passvalues = self.filterDate(values, filter_rule, filter_valueFrom, filter_valueTo)
        elif filter_type=='bool':
            passvalues = self.filterBool(values, filter_rule, filter_valueFrom, filter_valueTo)
        else:
            passvalues = self.filterString(values, filter_rule, filter_valueFrom, filter_valueTo)
            
        return passvalues
        
    def validateFilters(self, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Validate the filter rule and values for searching samples.
        Refer to getOperators(self, sampletype_id, attribute) above for how the filter is defined.
        
        Input:
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;
            filter_rule, an operator defined in self.getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            status = 1, okay
                     0, for any error
            message, any message
        '''
        if filter_rule=='No Filter':
            msg = 'okay'
            status = 1
            return msg, status
        
        attrdata = self.getOperators(sampletype_id, attribute)
        msg = attrdata['msg']
        status = attrdata['status']
        if status==0:
            return msg, status
        
        filter_type = attrdata['filter_type']
        if filter_type=='numeric':
            if not is_numeric(filter_valueFrom):
                msg = 'Warning: Not a valid numeric value: ' + str(filter_valueFrom)
                status = 0
                return msg, status
            
            if filter_rule=='Between':
                if not is_numeric(filter_valueTo):
                    msg = 'Warning: Not a valid numeric value: ' + str(filter_valueTo)
                    status = 0
                    return msg, status
            
        elif filter_type=='date':
            if toDateClass(filter_valueFrom) is None:
                msg = 'Warning: Start date not valid: ' + str(filter_valueFrom)
                status = 0
                return msg, status
            
            if filter_rule=='Between':
                if toDateClass(filter_valueTo) is None:
                    msg = 'Warning: End date not valid: ' + str(filter_valueTo)
                    status = 0
                    return msg, status
        
        msg = 'validateFilters: okay'
        status = 1
        return msg, status
        
    def reformatRecordForDB(self, login_user, record):
        ''' Given the record from either one row in an excel file or from client-side table,
            reformat it accordingly so it can be stored into the database table.
        Input
            record, the dictionary in its original format.
            login_user, the login user who submitted the request.
        Output
            record, the dictionary reformated ready for storing into database table.
            
        Notes
            This is a virtual method provided for overridinng in the child class.

        '''
        record_new = {}
        #for key, value in record.items():
        for key in self.fields:
            key_new = str(key)
            if key in record:
                value = record[key]
            elif key=="sample_attribute_type_id":
                value = record['sample_attribute_type_title']
            elif key=="created_at":
                value = getDefaultDate()
            elif key=="updated_at":
                value = getDefaultDate()
            #elif key=="unit_id":
            #    value = None
            elif key=="template_column_index":
                value = record['pos']
            elif key=="accessor_name":
                title = record['title']
                value = title.lower()
            #elif key=="sample_controlled_vocab_id":
                # ignore it and set it to default None, to be revised for future use
            #    value = None
            #elif key=="linked_sample_type_id":
            #    value = None
            else:
                #value = None
                continue
            
            if key_new=='id':
                pid = int(value)
                if pid>0:
                    record_new[key_new] = value
                #else:
                #    #ignore id for new attribute
            elif key_new=="sample_controlled_vocab_id":
                # ignore it and set it to default None, to be revised for future use
                continue
            else:
                record_new[key_new] = value
            #print(key_new, value)
            
        print(record_new)
        return record_new
        
    def getAttributesRenamed(self, sampleType_id, records_revised):
        ''' Given a list of attributes revised, get the mapping of attribute names between those renamed and stored in DB.
        Input:
            sampletype_id, the primary key for a sample type;
            records_revised, a list of dictionaries, each of which is a record in the sample_attribute format,
                with the following fields,
                    ('id', 'title', 'sample_attribute_type_id', ...)
            
        Output:
            attri_renamed, a dictionary in the format:
                attri_mapping[atrribute_newName] = atrribute_oldName
            
        Notes
            This function is used for updating sample's meta data after any attribute renaming dfor a sample type.

        '''        
        attributeInfo = self.getAttributeInfo(sampleType_id)
        attributes_db = attributeInfo['diclist']
        attributes_old = {}
        for attribute in attributes_db:
            id = attribute['id']
            attributes_old[id] = attribute
        
        attri_renamed= {}
        for record in records_revised:
            print(record)
            title_new = record['title']
            if 'id' not in record:
                #ignore any new attribute added
                continue
                
            id = int(record['id'])
            if id in attributes_old:
                attribute = attributes_old[id]
                title_old = attribute['title']
                if title_new.lower()!=title_old.lower():
                    attri_renamed[title_new.lower()] = title_old.lower()
        
        print(attri_renamed)
        return attri_renamed
        