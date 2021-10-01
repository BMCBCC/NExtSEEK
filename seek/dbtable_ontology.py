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
import xlwt
import logging
logger = logging.getLogger(__name__)

#from .models import Sample_ontologys
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile
from dmac.conversion import cleanString, toString, toStringDB


# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
ONTOLOGY_FILTER_MAPPING = {
}

# Default values for Sample table
ONTOLOGY_DEFAULT = {
}

INSTRUCTION_FIELD = "Field"
INSTRUCTION_FIELDTYPE = "Field Type"
INSTRUCTION_ONTOLOGY = "Ontology"

class DBtable_ontology(DBtable):
    ''' The class abut all the information about the table sample_controlled_vocabs and sample_controlled_vocab_terms.
    
    Typical usage of the class
    
        ontology = DBtable_ontology("DEFAULT")
        return ontology.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sample"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'sample_controlled_vocab_terms'
        #self.tablemodel = Sample_ontologys
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = []
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = ONTOLOGY_FILTER_MAPPING
        
    def loadControlledVocabulary(self, diclist_instruction, diclist_ontology):
        ''' Load the terms of controlled vocabularies in a sample sheet, given
        Input:
            diclist_instruction, the diclist from the Instructions sheet, in the following format,
                Field	                        Database Field              Field Type          Ontology
                Mouse UID	                    MUS::UID
                Mouse Name	                    MUS::Name
                Lab	                            MUS::StorageLocation
                Storage Site	                MUS::StorageSite
                Storage Condition	            MUS::StorageType
                Created By User	                MUS::CreatedByUser
                SEEK Submission Date	        MUS::CreatedByDate
                Strain	                        MUS::Strain                 Controlled Ontology  strain
                Strain Reference (NCBI #, etc)	MUS::StrainReference
                ...
                MUS::UID                        TIS::SourceSample
                
                where the 4th column is the name of ontology, in this instance, called "strain", which should match the terms
                in the ontology sheet below. 
            
            diclist_ontology, the diclist from the ontology sheet, in the following format,
                strain
                strain1
                strain2
                strain3
            
        Output:
            attributesControlled = {'Strain':['strain1', 'strain2', 'strain3',...]}, a dictionary with a list of attributes
                that are controlled ontology/vocabulary. The list of terms in each of vocabularies is to be loaded from
                the Ontology sheet or from the database.
        Notes:    
        '''
        # Step 1. find which attribute is the type of 'Controlled Ontology'
        # This is a list of attributes, whose attribute type is "Controlled Vocabulary" ("Controlled Ontology")
        # defined in sample_attribute_types table in Seek.
        # such as {"strain":["s1", "s2"]}
        attributesControlled = {}
        
        # mapping between sample header, such as "strain_A", "strain_B" and the ontology name, such as "strain"
        # so {"strain_A":"strain", "strain_B":"strain"}
        ontologies = {}
        
        status = 1
        msg = ''
        for dici in diclist_instruction:
            if INSTRUCTION_FIELD not in dici or INSTRUCTION_FIELDTYPE not in dici or INSTRUCTION_ONTOLOGY not in dici:
                #print dici
                # the instruction sheet must have INSTRUCTION_FIELD,"Database Field" as the first two columns.
                msg = "Error: Instruction sheet misses one of 'Field', 'Field Type' or 'Ontology' column."
                print(msg)
                status = 0
                return attributesControlled, ontologies, status, msg
                
            # header in Samplae sheet
            tbheader = dici[INSTRUCTION_FIELD]
            
            # the attribute type, such as "Text", "Date" or "Controlled Vocabulary"/"Controlled Ontology"
            fieldType = dici[INSTRUCTION_FIELDTYPE]
            
            # the name of the ontology, which matches the header of column in the Ontology sheet
            ontologyname = dici[INSTRUCTION_ONTOLOGY]
            if fieldType is not None and fieldType.strip()=='Controlled Ontology':
                if tbheader not in ontologies:
                    ontologies[tbheader] = ontologyname
                if ontologyname not in attributesControlled:
                    attributesControlled[ontologyname] = []
        
        #print "attributesControlled: ", attributesControlled 
        
        if len(attributesControlled)==0:
            # no attribute is the type of controlled vocabulary.
            return attributesControlled, ontologies, status, msg
                    
        # Step 2. load terms of for a attribute, whose type is of 'Controlled Ontology'.
        for dici in diclist_ontology:
            for field, term in dici.items():
                if field in attributesControlled:
                    terms = attributesControlled[field]
                    if term is not None and len(term.strip())>0:
                        terms.append(term.strip())
        
        #print "attributesControlled: ", attributesControlled
        return attributesControlled, ontologies, status, msg
    
    
    def getAttributeInfo(self, sampleType_id):
        ''' Get the list of ontologyInfo (fields) for a sample type.
        Input
            sampletype_id, the primary key for a sample type
            
        Output
            A dictionary of ontologyInfo for the sample type, including
                ontologyInfo['headers'], the list of ontologyInfo (fields) for the sample;
                ontologyInfo['headers_required'], a list of ontologyInfo required;
                ontologyInfo['sampletype'] = {}
                ontologyInfo['ontologyTypes'] = {'name':5, 'flowamount':7, 'FileReference':5, 'URI':19,...}
        '''
        diclist = self.db.retrieveRecords(self.tablemodel, 'sample_type_id', sampleType_id)
        
        from operator import itemgetter
        #newlist = sorted(diclist, key=itemgetter('template_column_index'))
        # sort ontologyInfo according to 
        newlist = sorted(diclist, key=itemgetter('pos'))
        ontologyInfo = {}
        headers = []    # a list of ontologyInfo
        headers_required = []   # a list of ontologyInfo required
        ontologyTypes = {}     # such as {'name':5, 'flowamount':7, 'FileReference':5, 'URI':19,...}, where key is the sample ontology name, while nuber is the ontology type in sample_ontology_types table
        for dici in newlist:
            field = dici['title']
            headers.append(field)
            
            isrequired = dici['required']
            if isrequired:
                headers_required.append(field)
                
            ontologyTypes[field] = dici['sample_ontology_type_id']
            
        #print(ontologyInfo)
        ontologyInfo['headers'] = headers
        ontologyInfo['headers_required'] = headers_required
        
        ontologyInfo['ontologyTypes'] = ontologyTypes
        
        from dbtable_sampletype import DBtable_sampletype
        sampletype = DBtable_sampletype("DEFAULT")
        ontologyInfo['sampletype'] = sampletype.getOneRecord(sampleType_id)
        ontologyInfo['sampleType_id'] = sampleType_id
        return ontologyInfo
        
    def __verifyOntologyTerm(self, ontology, term):
        ''' Verify whether a term is in the list of controlled ontology.
        Input:
            ontology = [term1, term2, ...]
            term, one of terms to be checked.
        
        Output:
            status, 1 term is okay
                    0 term is not in the ontology
            termRevised, the standard term in the ontology, after space or capitalization is revised.
        
        How it works:
            Verify whether a term is in the list of ontology, after checking space and capitalization.
            If space or capitalization difference is found in a term from user, the standard term from
            the ontology will be revised and returned for uploading.
        '''
        status = 1
        termRevised = term
        if term in ontology:
            return status, termRevised
        
        # the term is not found in the ontology. Check space or capitalization of the term.
        ontologyDic = {}
        for termi in ontology:
            termUp = termi.strip().upper()
            ontologyDic[termUp] = termi
            
        termUp = term.strip().upper()
        if termUp in ontologyDic:
            status = 1
            termRevised = ontologyDic[termUp]
        else:
            status = 0
        
        return status, termRevised
        
        
    def evaluateOntology(self, diclist_sample, diclist_ins, diclist_ont):
        ''' Evaluate whether the sample sheet has any problem in controlled terms of ontology.
        
        
        '''
        ontology_feedback = []
        attributesControlled, ontologies, status, msg = self.loadControlledVocabulary(diclist_ins, diclist_ont)
        if status==0:
            # error in loading the ontology
            return msg, status, ontology_feedback
        
        if len(attributesControlled)==0:
            # no ontology involved
            status = 1
            return msg, status, ontology_feedback
        
        status = 1  # no ontology error
        for dici in diclist_sample:
            ontology_error = []
            for header, value in dici.items():
                if header in ontologies:
                    # controlled term
                    ontologyname = ontologies[header]
                    ontology = attributesControlled[ontologyname]
                    if value is not None:
                        #ignore None value
                        valuestr = toString(value)
                        if len(valuestr)>0:
                            # ignore empty value
                            if value not in ontology:
                                #ontology_error.append(header)
                                #status = 0
                                
                                status, valueRevised = self.__verifyOntologyTerm(ontology, value)
                                if status==1:
                                    # the value is still in the ontology after space and capitalization are checked
                                    # Also revise the standardernized term, instead of the original one.
                                    dici[header] = valueRevised
                                else:
                                    # the term is not found in ontology after space and capitalization are checked
                                    ontology_error.append(header)
                                    status = 0
                                
                                
            ontology_feedback.append(ontology_error)
        return msg, status, ontology_feedback
    
    def outputOntologyFeedback(self, dicilist_feedback, headers, feedbackfile, ontology_feedback):
        ''' Output feedback from the batch upload of samples.
        Input:
            dicilist_feedback, the list of dictionaries with everything in the Sample sheet
                plus UIDs returned, returned from the batch uploading.
            headers, the list of headers from the original Sample sheet
        
        Output:
            feedbackfile, an excel file for output.
        '''
        book = xlwt.Workbook(encoding="utf-8")
        sheet1 = book.add_sheet("Samples")
        
        # Output headers of the sample
        row = 0
        for index, header in enumerate(headers):
            #print(index, header)
            try:
                newitem = toString(header)
                #print(row, index, newitem)
            except:
                newitem = cleanString(header)
            sheet1.write(row, index, newitem)
        
        i = 0
        
        style = xlwt.easyxf('pattern: pattern solid, fore_colour red;')
        style0 = xlwt.Style.easyxf('pattern: pattern solid, fore_colour white;')
        #sheet.row(0).write(0, value, style0)
        
        for dici in dicilist_feedback:
            row += 1
            # get ontology error in the format of ['header1, header2,...]
            ontology_error = ontology_feedback[i]
            for index, header in enumerate(headers):
                if header in dici:
                    newitem = dici[header]
                    #if 'http' in newitem:
                    #    newitem = self.__formatHttpLink(newitem)
                else:
                    newitem = "N/A"
                
                try:
                    newitem = str(newitem)
                except:
                    newitem = cleanString(newitem)
                    
                if header in ontology_error:
                    sheet1.write(row, index, newitem, style)
                else:    
                    #sheet1.write(row, index, newitem, style0)
                    sheet1.write(row, index, newitem)
            i += 1    
        book.save(feedbackfile)
        
        