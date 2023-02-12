#!/usr/bin/env python
import os
import sys
import time
import datetime
import simplejson
import json
import logging
import xlwt
logger = logging.getLogger(__name__)

import zipfile
from django.conf import settings
from django.db.models import Q

from .models import Samples, Projects_samples, People, Assets_creators, Projects
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile, load_excelfile_asdic, saveExcelDiclist, modifyExcelCell, reviseExcelDiclist
from dmac.conversion import getDefaultDate, toString, cleanString, getDefaultDate, getDefaultDateTime, convertDateListToString, toInt, verifyValueType
from dmac.iocsv import saveDiclistIntoExcel, filterDiclist, saveTwoDiclistsIntoExcel, getConstantRows, removeDiclistDuplicates

from dbtable_sampleattribute import DBtable_sampleattribute
from dbtable_sampletype import DBtable_sampletype
from dbtable_assay_assets import DBtable_assay_assets

from dbtable_data_files import DBtable_data_files
from dbtable_sops import DBtable_sops
from dbtable_policies import DBtable_policies

from dbtable_ontology import DBtable_ontology

SEEK_DATABASE = settings.SEEK_DATABASE
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + 'download/'

SAMPLE_FILTER_MAPPING = {
    "id":"A.id",
    "title":"A.title",
    "sample_type_id":"A.sample_type_id",
    "sample_type":"B.title",
    "uid":"A.uuid",
    "contributor_id":"A.contributor_id",
    "first_name":"C.first_name",
    "created_at":"A.created_at",
    "json_metadata":"A.json_metadata",
    "assay_id":"D.assay_id",
    "assayname":"E.assayname",
    "work_group_id":"F.work_group_id",
    "project_id":"G.project_id",
    "institution_id":"G.institution_id",
    "projectname":"H.title",
    "institution":"I.title"
}
SAMPLE_HEADERS = [
    "id",
    "title",
    "sample_type_id",
    "sample_type",
    "uid",
    "contributor_id",
    "first_name",
    "created_at",
    "json_metadata",
    "assays"
    #"assay_id",
    #"assayname",
    #"work_group_id",
    #"project_id",
    #"institution_id",
    #"projectname",
    #"institution"
]

SAMPLE_DEFAULT = {
    #'id':'',
    'title':'',
    'sampleType_id':0,
    'json_metadata':'',
    'uuid':'',
    'contributor_id':0,
    'policy_id':'',
    'created_at':'',
    'updated_at':'',
    'first_letter':'',
    'other_creators':'',
    'originating_data_file_id':None,  
    'deleted_contributor':None         
}

SAMPLE_SHEET_NAMES = ["INSTRUCTIONS", "SAMPLES", "ASSAY", "ONTOLOGY"]

ATTRIBUTETYPE_ID_WEBLINK = 5
ATTRIBUTETYPE_ID_URI = 19

SAMPLE_PARENT_ATTRIBUTOR = "CreatedFromSample"
SAMPLE_PARENT_ACCESSOR_NAME = "parent"
SAMPLE_PROTOCOL_ACCESSOR_NAME = "protocol"
SAMPLE_FILE_ACCESSOR_NAME = "file_"         
SAMPLE_LINK_ACCESSOR_NAME = "link_"        
SAMPLE_CONTRIBUTOR_ACCESSOR_NAME = "Scientist"

SAMPLE_ERRORCODE = {
    '101': 'Error S101: Sample excel file not in the right xlsx format.',
    '102': 'Error S102: Sample excel file does not contain required sheet:',
    '103': 'Error S103: Sample excel file contains invalid "Instruction" sheet.',
    '104': 'Error S104: Sample excel file contains invalid "Samples" sheet.',
    '105': 'Error S105: Sample excel file contains invalid "Samples" sheet with no data on the sample type: ',
    '106': 'Error S106: Sample excel file not loaded correctly: ',
    '201': 'Error S201: Sample type not uniquely defined in database: ',
    '202': 'Error S202: Sample type has no attribute defined: ',
    '301': 'Error S301: Sample has a Parent UID with error. ',
    '302': 'Error S302: Sample has neither "Name" nor "File_PrimaryData" attribute: ',
    '303': 'Error S303: Sample has invalid "Name" or "File_PrimaryData" attribute. ',
    '401': 'Error S401: Revise sample name or use the UID to update this sample, whose name already in DB with the UID: ',
    '402': 'Error S402: Sample UID not consistent with the UID in DB for same sample name: ',
    '403': 'Error S403: Ask Admin for help because the sample name corresponds to more than one record in DB.',
    '501': 'Error S501: Sample information empty for uploading.',
    '502': 'Error S502: Sample required values not provided: ',
    '503': 'Error S503: Sample does not have an "UID" field for saving into DB. ',
    '504': 'Error S504: Sample not saved into DB: ',
    '601': 'Warning S601: Sample asset not saved into DB: ',
    '602': 'Warning S602: Sample and data file association not saved correctly into DB: '
}

SAMPLE_ERRORCODE = {
    '101': 'Error: Excel file in incorrect format.',
    '102': 'Error: Assay sheet does not contain required sheet - ',
    '103': 'Error: Assay sheet does not contain valid "Instruction" sheet.',
    '104': 'Error: Assay sheet does not contain valid "Samples" sheet.',
    '105': 'Error: Sample type not identified in assay sheet - ',
    '106': 'Error: Excel file failed to load - ',
    '201': 'Error: Sample type not uniquely defined in database - ',
    '202': 'Error: Unknown attribute in assay sheet - ',
    '301': 'Error: Sample has an invalid Parent UID. ',
    '302': 'Error: Sample is missing data for either the "Name" or "File_PrimaryData" attribute - ',
    '303': 'Error: Sample has invalid entry for either the "Name" or "File_PrimaryData" attribute. ',
    '304': 'Error: Sample has no entry for the required "Scientist" attribute',
    '305': 'Error: "Scientist" name for the sample not registered in Seek: ',
    '401': 'Error: User has already uploaded a sample with this name to the database; please include the UID in order to update the sample metadata - ',
    '402': 'Error: Sample UID does not match sample name in the SEEK database - ',
    '403': 'Error: Sample name corresponds to more than one record in the database; please ask an admin for help.',
    '501': 'Error: No information provided for sample.',
    '502': 'Error: Required data is missing - ',
    '503': 'Error: Assay sheet is missing the "UID" attribute. ',
    '504': 'Error: Sample not saved into DB - ',
    '601': 'Warning: Sample not saved to the SEEK database - ',
    '602': 'Warning: Data file not associated with a sample in the SEEK database - ',
    
    '701': 'Warning: Assay sheet does not contain valid "Update_assay" sheet.',
    
}

DELIMITER_DBFIELD = "::"
SAMPLE_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/SAMPLE_TEMPLATE.xlsx"
IMMPORT_TEMPLATE_FILE_PREFIX = settings.MEDIA_ROOT + "/reserved/IMMPORT_TEMPLATE-"
IMMPORT_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/IMMPORT_TEMPLATE-MAPPING.xlsx"
IMMPORT_TEMPLATES = {'protocols':'protocols',
    'subjectanimals':'subjectanimals',
    'biosamples':'biosamples',
    'experiments':'experiments',
    'experimentsamples':'mass_spec_proteomics'   
}
IMMPORT_TEMPLATES_VERSION = 'Schema Version 3.32'
PUBLISH_SERVER = settings.PUBLISH_URL
RESERVED_REMOVE_VALUE_FOR_UPDATE = "-null"
RESERVED_DEFAULT_VALUE_FOR_UPDATE = "-none"

    
from joblib import Parallel, delayed
import multiprocessing

def unwrap_self_createMultiParentTreeParallel_i(arg, **kwarg):    
    return DBtable_sample.createMultiParentTreeParallel_i(*arg, **kwarg)

def unwrap_self_createSampleChildrenTreeParallel_i(arg, **kwarg):
    return DBtable_sample.createSampleChildrenTreeParallel_i(*arg, **kwarg)

class DBtable_sample(DBtable):
    def __init__(self, whichServer='default'):
        DBtable.__init__(self, 'SEEK', 'seek_development')
        self.tablename = 'samples'
        self.tablemodel = Samples
        self.fulltablename = self.tablemodel
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'title',
            'sample_type_id',
            'json_metadata',
            'uuid',
            'contributor_id',
            'policy_id',
            'created_at',
            'updated_at',
            'first_letter',
            'other_creators',
            'originating_data_file_id',
            'deleted_contributor'
        ]
        self.uniqueFields = ['uuid']
        self.primaryField = "id"
        self.fieldMapping = SAMPLE_FILTER_MAPPING
        self.excludeFields = []
        
    def __notEmptyLine(self, csvdic):
        notEmpty = True
        if len(csvdic)==0:
            notEmpty = False
            return notEmpty
            
        allNone = True
        for key, value in csvdic.items():
            if value is None:
                okay = 1
            else:
                allNone = False
            
        if allNone:    
            notEmpty = False
            
        return notEmpty
        
    def getSampleUIDIndex(self, sampleUIDPrefix):
        records = self.db.retrieveRecords(self.tablemodel, 'uuid', sampleUIDPrefix)
        prefix = sampleUIDPrefix + '-'          
        indexes = []
        maxindex = 0
        for record in records:
            uid = record['uuid']               
            if prefix in uid:
                index = uid.replace(prefix, '') 
                index = toInt(index)
                if index>maxindex:
                    maxindex = index
            
        nextIndex = maxindex + 1    
        return nextIndex
    
    def __defineUID(self, user_seek, record, attributeInfo):
        sampletype = attributeInfo['sampletype']
        typetitle = sampletype['title']
        uid_prefix = typetitle
        if '_' in typetitle:
            terms = typetitle.split('_')
            uid_prefix = terms[0]
            
        uid_date = str(datetime.datetime.now().strftime("%Y%m%d"))
        lab = user_seek['lababbv']
        prefix = uid_prefix + '-' + uid_date[2:] + lab
        nextIndex = str(self.getSampleUIDIndex(prefix))
        uid = prefix + '-' + nextIndex
        return uid
    
    def __getRecordToJson(self, record, attributeInfo):
        headers = attributeInfo['headers']
        record_new = {}
        for header in headers:
            field = header.lower()
            if header in record:
                record_new[field] = toString(record[header])
            else:
                record_new[field] = ''
        
        record_json = simplejson.dumps(record_new, default=str)
        return record_json
        
    def __getRecordFromJson(self, record_json):
        record = json.loads(record_json)
        return record
        
    def __updateSampleMetadata(self, metadata_db, metadata_in, attributes=None):
        metadata_in2 = {}
        for key, value in metadata_in.items():
            lowkey = key.lower()
            metadata_in2[lowkey] = value
        metadata_in = metadata_in2
        
        if metadata_db['uid']!=metadata_in['uid']:
            return metadata_in
        
        if attributes is not None:
            metadata_db2 = {}
            for key, value in metadata_db.items():
                lowkey = key.lower()
                if lowkey in attributes:
                    metadata_db2[lowkey] = value
            metadata_db = metadata_db2
        
        metadata_out = {}
        for key, value in metadata_db.items():
            if key in metadata_in:
                value_in = metadata_in[key]
                if value_in is None:
                    metadata_out[key] = value
                    continue
                
                elif value_in==RESERVED_REMOVE_VALUE_FOR_UPDATE:
                    continue
                
                elif value_in==RESERVED_DEFAULT_VALUE_FOR_UPDATE:
                    metadata_out[key] = ''
                    continue
                
                try:
                    value_str = str(value_in)
                    if len(value_str)>0:
                        metadata_out[key] = value_in
                except:
                    metadata_out[key] = value_in
            else:
                metadata_out[key] = value
                
        for key, value in metadata_in.items():
            if key not in metadata_out:
                if value==RESERVED_DEFAULT_VALUE_FOR_UPDATE:
                    metadata_out[key] = ''
                else:
                    metadata_out[key] = value
        
        return metadata_out
        
    def __getRecord(self, user_seek, record, attributeInfo, contributor_id):
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        record_new = {}
        for field in self.fields:
            value = ''
            if field in SAMPLE_DEFAULT:
                value = SAMPLE_DEFAULT[field]
            record_new[field] = value
            
        uid = record['UID']
        newSample = False
        if uid is None or len(uid.strip())==0:
            uid = self.__defineUID(user_seek, record, attributeInfo)
            record['UID'] = uid
            newSample = True
            
        if 'Name' in record:
            samplename = str(record['Name'])
        elif 'File_PrimaryData' in record:
            samplename = str(record['File_PrimaryData'])
        elif 'File_PrimaryData_Forward' in record:
            samplename = str(record['File_PrimaryData_Forward'])
        elif 'File_PrimaryData_Reverse' in record:
            samplename = str(record['File_PrimaryData_Reverse'])
        else:
            samplename = 'Undefined'
        
        record_new['title'] = samplename
        record_new['sample_type_id'] = attributeInfo['sampleType_id']
        record_new['json_metadata'] = self.__getRecordToJson(record, attributeInfo)
        record_new['uuid'] = uid
        record_new['contributor_id'] = contributor_id
        
        policy = DBtable_policies("DEFAULT")
        record_db = self.__retrieveSampleByUID(uid)
        if record_db is None:
            msg, status, policy_id = policy.createDefaultPolicy(username, contributor_id, project_id)
        else:
            policy_id = record_db['policy_id']
            contributor_id = record_db['contributor_id']
            record_new['contributor_id'] = contributor_id
            
            metadata_db = self.__getRecordFromJson(record_db['json_metadata'])
            metadata_in = self.__getRecordFromJson(record_new['json_metadata'])
            metadata_out = self.__updateSampleMetadata(metadata_db, metadata_in)
            record_new['json_metadata'] = simplejson.dumps(metadata_out, default=str)
            
            other_creators = record_db['other_creators']
            if other_creators is None:
                record_new['other_creators'] = username
            else:
                record_new['other_creators'] = other_creators + ';' + username
            
        record_new['policy_id'] = policy_id
        record_new['created_at'] = getDefaultDateTime()
        record_new['updated_at'] = getDefaultDateTime()
        record_new['first_letter'] = samplename[0]
        return record_new, newSample
        
    def __updateSampleProject(self, user_seek, sample_id):
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        record = {}
        record['sample_id'] = sample_id
        record['project_id'] = project_id
        record = Projects_samples(project_id=project_id, sample_id=sample_id)
        record.save()
        return
        
        
    def __updateSampleAssetsCreators(self, sample_id, creator_id):
        records = Assets_creators.objects.filter(asset_id=sample_id, creator_id=creator_id, asset_type='Sample')
        if len(records)==1:
            return
        
        if len(records)>1:
            Assets_creators.objects.filter(asset_id=sample_id, creator_id=creator_id, asset_type='Sample').delete()
        
        timenow = getDefaultDateTime()
        record = Assets_creators(asset_id=sample_id, creator_id=creator_id, asset_type='Sample', created_at=timenow, updated_at=timenow)
        record.save()
        return
        
    def __verifyOntology(self, record):
        msg = "Warning: verifying ontology of a sample info is to be implemented"
        logger.debug(msg)
        
    def __verifyRequiredFields(self, record, fields_required):
        if 'UID' not in record.keys():
            msg = SAMPLE_ERRORCODE['503']
            meetRequired = False
            return msg, meetRequired
        
        uid = record['UID']
        if uid is None or len(uid.strip())==0:
            newSample = True
        else:
            newSample = False
            meetRequired = True
            msg = 'Other required fields are not necessary when the UID is available for updating the sample Info.'
            return msg, meetRequired
        
        if 'UID' in fields_required:
            fields_required.remove('UID')
        
        meetRequired = True
        msg_required = 'Following fields are required: '
        for field in fields_required:
            if field in record:
                value = record[field]
                if value is None:
                    meetRequired = False
                    msg_required += field + ";"
                else:
                    valuestr = str(value)
                    if len(valuestr.strip())==0:
                        meetRequired = False
                        msg_required += field + ";"
            else:
                meetRequired = False
                msg_required += field + ";"
                
        if meetRequired:
            msg_required = 'All fields required are available'
        return msg_required, meetRequired
        
    
    def __loadSampleTypes(self, diclist_instruction):
        sampleTypes = {}      
        sampleTypes_order = []
        for dici in diclist_instruction:
            if "Field" not in dici or "Database Field" not in dici:
                msg = "Error: Instruction sheet should contain 'Field' or 'Database Field' columns."
                return {}, []
                
            tbheader = dici["Field"]
            if tbheader is not None:
                header = str(tbheader)
                if len(header.strip())==0:
                    continue
            else:
                continue
            
            dbfield = dici["Database Field"]
            if DELIMITER_DBFIELD not in dbfield:
                msg = "Error: 'Database Field' column should follow the format 'tableName::attributeName."
                return {}, []
                
            terms = dbfield.split(DELIMITER_DBFIELD)     
            sampleType = terms[0]         
            attribute = terms[1]            
            if sampleType in sampleTypes:
                attributeMapping = sampleTypes[sampleType]
            else:
                attributeMapping = {}
                                
            attributeMapping[tbheader] = attribute
            sampleTypes[sampleType] = attributeMapping
            
            if sampleType not in sampleTypes_order:
                sampleTypes_order.append(sampleType)
            
        return sampleTypes, sampleTypes_order
        
    def __splitSampleTypes(self, sampleTypes, diclist_samples):
        sample_sheets = {}
        for sampleType in sampleTypes:
            sample_sheets[sampleType] = []
            
        unique_samples = {}
        for dici_meta in diclist_samples:
            for sampleType, attributeMapping in sampleTypes.items():
                diclist = sample_sheets[sampleType]
                
                dici_sample = {}
                samplename = None
                for header, value in dici_meta.items():
                    if header in attributeMapping:
                        attribute = attributeMapping[header]
                        dici_sample[attribute] =  value
                        
                        if attribute.lower()=='name':
                            samplename = value
                        elif attribute.lower()=='file_primarydata':
                            samplename = value
                        elif attribute.lower()=='file_primarydata_forward':
                            samplename = value
                        elif attribute.lower()=='file_primarydata_reverse':
                            samplename = value
                            
                if samplename is None:
                    msg = 'Error: one sample does not have an unique identifier, which will be captured later on in __getRecord()'
                elif samplename in unique_samples:
                    dici_sample = unique_samples[samplename]
                else:
                    unique_samples[samplename] = dici_sample
                        
                diclist.append(dici_sample)
                sample_sheets[sampleType] = diclist
        return sample_sheets
    
    
    def __setSampleDatafileAssociation(self, user_seek, sampleType, record, attributeInfo, diclist_assay):   
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        msg = ''
        status = 1
        
        attributeTypes = attributeInfo['attributeTypes']
        dbdf = DBtable_data_files("DEFAULT")
        for attribute, dfurl in record.items():
            if attribute not in attributeTypes:
                continue
            
            attributeType_id = attributeTypes[attribute]
            if attributeType_id!=ATTRIBUTETYPE_ID_WEBLINK and attributeType_id!=ATTRIBUTETYPE_ID_URI:
                continue
            
            msgi, statusi = dbdf.processSampleDatafile(user_seek, sampleType, dfurl, diclist_assay)
            if not statusi:
                status = 0
                msg += msgi + ';'
                
        return msg, status
    
    
    def __verifyUID(self, uidIn, attributeInfo):
        isValid = True
        msg = ''
        sampletype = attributeInfo['sampletype']
        typetitle = sampletype['title']
        uid_prefix = typetitle
        if '_' in typetitle:
            terms = typetitle.split('_')
            uid_prefix = terms[0]
            
        uidIn_prefix = uidIn
        if '-' in uidIn:
            terms = uidIn.split('-')
            uidIn_prefix = terms[0]
        
        if uid_prefix.strip()!=uidIn_prefix.strip():
            msg = "Error: Sample UID " + uidIn + " does not match sample type: " + typetitle
            isValid = False
            return isValid, msg
        
        record = self.__retrieveSampleByUID(uidIn)
        if record is None:
            msg = "Error: Sample UID " + uidIn + " does not exist in DB for update "
            isValid = False
            return isValid, msg
        
        return isValid, msg

            
    def __storeSample(self, user_seek, sampleType, record, attributeInfo, diclist_assay, creator):
        username = user_seek['username']
        contributor_id = user_seek['user_id']
        
        creator_id = creator['user_id']
        project_id = creator['projectid']
        
        if not self.__notEmptyLine(record):
            msg = SAMPLE_ERRORCODE['501']
            return msg, 0, None
        
        headers_required = attributeInfo['headers_required']
        
        msg_required, meetRequired = self.__verifyRequiredFields(record, headers_required)
        if not meetRequired:
            msg = SAMPLE_ERRORCODE['502'] + msg_required
            return msg, 0, None
                
        if 'UID' not in record.keys():
            msg = SAMPLE_ERRORCODE['503']
            return msg, 0, None
        
        record_new, newSample = self.__getRecord(creator, record, attributeInfo, contributor_id)
        uid = record_new['uuid']
        msg, status, sample_id = self.storeOneRecord(username, record_new)
        if status:
            if newSample:
                self.__updateSampleProject(creator, sample_id)
                self.__updateSampleAssetsCreators(sample_id, creator_id)
                if len(diclist_assay)>0:
                    msgj, statusj = self.__storeSample_assay_asset(creator, sampleType, sample_id, diclist_assay)
                    if statusj==0:
                        msgj = SAMPLE_ERRORCODE['601'] + msgj
                        msg += ';' + msgj
                else:
                    msg = 'Info: Assay info not available for updating array-sample relationship for sample id: ' + str(sample_id)
            else:
                msg = 'Info: No update on array-sample relationship for old sample id: ' + str(sample_id)
                    
            msgdf, statusdf = self.__setSampleDatafileAssociation(creator, sampleType, record, attributeInfo, diclist_assay)
            if not statusdf:
                msgdf = SAMPLE_ERRORCODE['602'] + msgdf
                msg += ';' + msgdf
        else:
            msg = SAMPLE_ERRORCODE['504'] + msg
        
        return msg, status, uid
    
    def __storeSample_assay_asset(self, user_seek, sampleType, sample_id, diclist_assay):
        username = user_seek['username']
        assay_assets = DBtable_assay_assets("DEFAULT")
        return assay_assets.storeSample_assay_asset(user_seek, sampleType, sample_id, diclist_assay)
        
    def __searchUniqueSample(self, samplename, scientist, sample_type_id):
        query = {}
        query['sample_type_id__exact'] = sample_type_id
        qset = Q(**query)
        
        query = {}
        query['json_metadata__icontains'] = scientist
        qset = qset & Q(**query)
        
        query = {}
        query['title__iexact'] = samplename
        qset = qset & Q(**query)
            
        records = self.queryRecordsCustom(qset)
        return records
        
    def __verifySampleUID(self, samplename, creator_id, uidIn, sample_type_id, scientist):
        samplename = str(samplename)
        records = self.__searchUniqueSample(samplename, scientist, sample_type_id)
        
        nr = len(records)
        status = 1
        msg = ''
        if nr==0:
            if uidIn is None or len(uidIn.strip())==0:
                status = 1
                msg = 'Okay: ready for store a new sample without predefined UID'
            else:
                status = 1
                msg = 'Okay: ready for store a new sample with predefined UID: ' + uidIn
        elif nr==1:
            record = records[0]
            uid_verified = record['uuid'] # we always use 'uuid' to store UID for a sample.
            if uidIn is None or len(uidIn.strip())==0:
                status = 0
                msg = SAMPLE_ERRORCODE['401'] + uid_verified
            elif uid_verified==uidIn:
                status = 1
                msg = 'Okay: Unique record exists based on ' + samplename
                msg += ', which is consistent with the UID ' + uidIn
            else:
                status = 0
                msg = SAMPLE_ERRORCODE['402'] + uidIn + ' ' + uid_verified
        else:
            status = 0
            msg = SAMPLE_ERRORCODE['403']
        return msg, status
    
    def __updateSampleErrorMsg(self, sampledic_feeback, primaryField, msg, sampleType):
        header = sampleType + "::UID"
        sampledic_feeback[header] = msg
        
        if primaryField in sampledic_feeback:
            value = sampledic_feeback[primaryField]
            if value is None or len(str(value))==0:
                sampledic_feeback[primaryField] = msg
            else:
                sampledic_feeback[primaryField] = value + ":" + msg
        else:
            sampledic_feeback[primaryField] = msg
            
        return sampledic_feeback
        
    def __queryContributorID(self, user_seek, contributor_fullname):
        seekdb = SeekDB(user_seek['server'], user_seek['username'], user_seek['password'])
        contributor_id = seekdb.getUserid(contributor_fullname)
        if contributor_id is None:
            return -1
        
        return contributor_id
        
        
    def __batchUploadTest(self, seekdb, sampleType, diclist, diclist_feedback, attributeInfo, attributeMapping, diclist_assay, uploadEnforced=False):
        user_seek = seekdb.user_seek
        username = user_seek['username']
        user_id = user_seek['user_id']
        contributor_id = user_id
        creator = seekdb.creator
        creator_id = creator['user_id']
        msg0 = '<br/>'
        nright = 0
        nrow = 0
        statusTest = True
        diclist_new = []
        ndici = len(diclist)
        uids_predefined = {}
        
        for index in range(ndici):
            dici = diclist[index]
            if len(diclist_feedback)>0:
                dici_feedback = diclist_feedback[index]
                
                findParentUID = True
                for field, attribute in attributeMapping.items():
                    if DELIMITER_DBFIELD in field and field in dici_feedback:
                        uid_from = dici_feedback[field]
                        if "Error" in uid_from:
                            findParentUID = False
                        else:
                            dici[attribute] = uid_from
                if not findParentUID:
                    msgi = SAMPLE_ERRORCODE['301']
                    statusTest = False
                    msg0 += msgi +  '<br/>'
                
                    header = sampleType + "::UID"
                    dici_feedback[header] = msgi
                    diclist_new.append(dici_feedback)
                    continue
            else:
                dici_feedback = {}
                
            primaryField = sampleType + "::UID" 
            for header, attribute in attributeMapping.items():
                if attribute in dici:
                    dici_feedback[header] = dici[attribute]
                else:
                    dici_feedback[header] = ''
                    
                if attribute=='UID':
                    primaryField = header
                    
            if 'Name' in dici:
                samplename = str(dici['Name'])
            elif 'File_PrimaryData' in dici:
                samplename = str(dici['File_PrimaryData'])
            elif 'File_PrimaryData_Forward' in dici:
                samplename = str(dici['File_PrimaryData_Forward'])
            elif 'File_PrimaryData_Reverse' in dici:
                samplename = str(dici['File_PrimaryData_Reverse'])
            else:
                msgi = SAMPLE_ERRORCODE['302'] + sampleType + " " + str(index)
                statusTest = False
                msg0 += msgi +  '<br/>'
                
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            
            if samplename is None:
                cleanname = ''
            else:
                cleanname = str(samplename)
            cleanname = cleanname.strip()
            if len(cleanname)==0:
                msgi = SAMPLE_ERRORCODE['303']
                statusTest = False
                msg0 += msgi +  '<br/>'
                
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            
            if SAMPLE_CONTRIBUTOR_ACCESSOR_NAME in dici:
                scientist = str(dici[SAMPLE_CONTRIBUTOR_ACCESSOR_NAME])
            elif SAMPLE_CONTRIBUTOR_ACCESSOR_NAME.lower() in dici:
                scientist = str(dici[SAMPLE_CONTRIBUTOR_ACCESSOR_NAME.lower()])
            else:
                msgi = SAMPLE_ERRORCODE['304']
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            
            if contributor_id<=0:
                msgi = SAMPLE_ERRORCODE['305'] + contributor
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            

            if samplename in uids_predefined:
                dici['UID'] = uids_predefined[samplename]
            else:
                sample_type_id = attributeInfo['sampleType_id']
                uidIn = None
                if 'UID' in dici:
                    uidIn = dici['UID']
                msgi, statusi = self.__verifySampleUID(samplename, creator_id, uidIn, sample_type_id, scientist)
                if statusi==0:
                    statusTest = False
                    msg0 += msgi +  '<br/>'
                    dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                    diclist_new.append(dici_feedback)
                    continue
                
                if uidIn is not None and len(uidIn.strip())>0:
                    isValid, msgi = self.__verifyUID(uidIn, attributeInfo)
                    if not isValid:
                        statusTest = False
                        msg0 += msgi +  '<br/>'
                        dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                        diclist_new.append(dici_feedback)
                        continue
            
            msgi, statusi, uid = self.__storeSample(user_seek, sampleType, dici, attributeInfo, diclist_assay, creator)
                
            nrow += 1
            if statusi:
                msg0 += str(samplename) + ": " + msgi +  '<br/>'
                nright += 1
                if samplename not in uids_predefined:
                    uids_predefined[samplename] = uid
            else:
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                
            header = sampleType + "::UID"
            if statusi:
                dici_feedback[header] = uid
                dici_feedback[primaryField] = uid
            else:
                dici_feedback[header] = msgi
            diclist_new.append(dici_feedback)
                
        msg = 'The number of samples uploaded for ' + sampleType + ': ' + str(nright) + ' out of in total ' + str(ndici) + ' samples.'
        if not statusTest:
            msg = msg + '<br/>' + msg0
        else:
            msg = msg + '<br/>' + msg0
        
        return msg, statusTest, diclist_new
    
    def __batchUploadSampleTest(self, seekdb, sampleType, diclist_sample, diclist_feedback, attributeMapping, diclist_assay, uploadEnforced=False):
        user_seek = seekdb.user_seek
        username = user_seek['username']
        stype = DBtable_sampletype()
        sampletype_id = stype.getSampleTypeID(sampleType)
        if sampletype_id<=0:
            msg = SAMPLE_ERRORCODE['201'] + sampleType + " id: " + str(sampletype_id)
            return msg, 0, diclist_feedback
    
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        if len(attributeInfo['headers'])==0:
            msg = SAMPLE_ERRORCODE['202'] + sampleType
            status = 0
            return msg, status,diclist_feedback
        
        msg, status, diclist_feedback = self.__batchUploadTest(seekdb, sampleType, diclist_sample, diclist_feedback, attributeInfo, attributeMapping, diclist_assay, uploadEnforced)
        return msg, status, diclist_feedback


    def __outputUploadFeedback(self, diclist_feedback, headers, feedbackfile):
        book = xlwt.Workbook(encoding="utf-8")
        sheet1 = book.add_sheet("Samples")
        row = 0
        for index, header in enumerate(headers):
            try:
                newitem = toString(header)
            except:
                newitem = cleanString(header)
            sheet1.write(row, index, newitem)
        
        for dici in diclist_feedback:
            row += 1
            for index, header in enumerate(headers):
                if header in dici:
                    newitem = dici[header]
                else:
                    newitem = "N/A"
                
                try:
                    newitem = str(newitem)
                except:
                    newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
                
        book.save(feedbackfile)
        
    def __outputUploadFeedback_V2(self, diclist, diclist_feedback, headers, feedbackfile):
        book = xlwt.Workbook(encoding="utf-8")
        sheet1 = book.add_sheet("Samples")
        row = 0
        for index, header in enumerate(headers):
            try:
                newitem = toString(header)
            except:
                newitem = cleanString(header)
            sheet1.write(row, index, newitem)
        
        style = xlwt.easyxf('pattern: pattern solid, fore_colour red;')
        style0 = xlwt.Style.easyxf('pattern: pattern solid, fore_colour white;')
        i = 0
        for dici in diclist:
            dici_feedback = diclist_feedback[i]
            row += 1
            for index, header in enumerate(headers):
                if header in dici:
                    newitem = dici[header]
                else:
                    newitem = ""
                
                try:
                    newitem = str(newitem)
                except:
                    newitem = toString(newitem)
                
                if header in dici_feedback:
                    feedback = dici_feedback[header]
                    if feedback is None:
                        sheet1.write(row, index, newitem)
                    elif 'Error' in toString(feedback):
                        feedback = feedback + ":" + newitem
                        sheet1.write(row, index, feedback, style)
                    elif 'Warning' in toString(feedback):
                        feedback = feedback + ":" + newitem
                        sheet1.write(row, index, feedback, style)
                    elif 'UID' in header:
                        sheet1.write(row, index, feedback)
                    else:
                        sheet1.write(row, index, newitem)
                else:
                    sheet1.write(row, index, newitem)
                
            i += 1 
        book.save(feedbackfile)        
        
    def __verifyUpdateSample(self, sheetData, feedbackfile):
        status = 1
        msg = "Okay"
        headers = sheetData['headers']
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['104']
            status = 0
            return msg, status, None
        
        if 'UID' not in headers and 'uid' not in headers:
            msg = 'UID column not available in the sheet for update'
            status = 0
            return msg, status, None
        
        sampleTypes_order = []
        for dici in diclist:
            if 'UID' in dici:
                uid = dici['UID']
            else:
                uid = dici['uid']
            terms = uid.split('-')
            sampleType = terms[0]
            if sampleType not in sampleTypes_order:
                sampleTypes_order.append(sampleType)
            
        if len(sampleTypes_order)==0:
            msg = 'Sample type not available in the sheet for update'
            status = 0
            return msg, status, None
        
        if len(sampleTypes_order)>1:
            msg = 'Only one sample type should be included in the sheet for update'
            status = 0
            return msg, status, None
        
        sampleType = sampleTypes_order[0]
        stype = DBtable_sampletype()
        sampletype_id = stype.getSampleTypeID(sampleType)
        if sampletype_id<=0:
            msg = SAMPLE_ERRORCODE['201'] + sampleType + " id: " + str(sampletype_id)
            return msg, 0, None
    
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        if len(attributeInfo['headers'])==0:
            msg = SAMPLE_ERRORCODE['202'] + sampleType
            status = 0
            return msg, status, None
        
        attributes = [x.lower() for x in attributeInfo['headers']]
        msg = 'The following column(s) are not in sample attributes thus must be removed from the sheet before further processing:<br/><br/>'
        headers_error = []
        for header in headers:
            if header.lower() not in attributes:
                msg += header +  '<br/>'
                headers_error.append(header)
                status = 0
        
        if status==0:
            diclist_sanity = []
            for dici in diclist:
                for header in headers_error:
                    dici[header] = 'Error:' + dici[header]
                diclist_sanity.append(dici)
            self.__outputUploadFeedback_V2(diclist, diclist_sanity, headers, feedbackfile)
        
        return msg, status, attributes
        
    def __batchUpdateSample(self, sheetData, feedbackfile, user_seek):
        username = user_seek['username']
        msg = "batchUpdate"
        status = 0
        
        headers = sheetData['headers']
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['104']
            status = 0
            return msg, status
        
        msg, status, attributes = self.__verifyUpdateSample(sheetData, feedbackfile)
        if status==0:
            return msg, status
        
        headers.append('feedback')
        username = user_seek['username']
        user_id = user_seek['user_id']

        msg0 = '<br/>'
        nright = 0
        nrow = 0
        statusTest = True
        ndici = len(diclist)
        diclist_feedback = []
        for index in range(ndici):
            dici = diclist[index]
            dici_feedback = {}
            
            for key, elem in dici.items():
                dici_feedback[key] = elem
                
            msgi, statusi = self.updateSingleSample(dici, username, attributes)
            nrow += 1
            if statusi:
                msg0 += str(nrow) + ": " + msgi +  '<br/>'
                nright += 1
                dici_feedback['feedback'] = 'successful'
            else:
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['feedback'] = msgi

            diclist_feedback.append(dici_feedback)
                
        msg = 'The number of samples updated: ' + str(nright) + ' out of in total ' + str(ndici) + ' samples.'
        if not statusTest:
            msg = msg + '<br/>' + msg0
            status = 0
        else:
            msg = msg + '<br/>' + msg0
            status = 1
                
        self.__outputUploadFeedback_V2(diclist, diclist_feedback, headers, feedbackfile)
        return msg, status
    
    
    def __batchUpdateSampleAssociation(self, sheetData, feedbackfile, user_seek):
        username = user_seek['username']
        msg = "batchUpdate sample-assay association"
        status = 0
        
        headers = sheetData['headers']
        headers_required = ["Sample UID","Current Assay ID","Current Assay Direction","New Assay ID","New Assay Direction"]
        missing = False
        missed = ''
        for header in headers_required:
            if header not in headers:
                missing = True
                missed += header + ' '
        if missing:
            msg = SAMPLE_ERRORCODE['701'] + ' with missing columns ' + missed
            status = 0
            return msg, status
        
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['701'] + ' with no content'
            status = 0
            return msg, status
        
        headers.append('Feedback')
        username = user_seek['username']
        user_id = user_seek['user_id']
        assay_assets = DBtable_assay_assets("DEFAULT")

        msg0 = '<br/>'
        nright = 0
        nrow = 0
        statusTest = True
        ndici = len(diclist)
        diclist_feedback = []
        for index in range(ndici):
            dici = diclist[index]
            dici_feedback = {}
            
            for key, elem in dici.items():
                dici_feedback[key] = elem
                
            uid = dici['Sample UID']
            sample_id = self.getSampleID(uid)
            if sample_id>0:
                msgi, statusi = assay_assets.updateSample_assay_asset(user_seek, sample_id, dici)
            else:
                msgi ='Warning: Sample UID not found: ' + uid
                statusi = 0
            nrow += 1
            if statusi:
                msg0 += uid + ": " + msgi +  '<br/>'
                nright += 1
                dici_feedback['Feedback'] = 'successful: ' + msgi
            else:
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['Feedback'] = msgi

            diclist_feedback.append(dici_feedback)
                
        msg = 'The number of samples updated: ' + str(nright) + ' out of in total ' + str(ndici) + ' samples.'
        if not statusTest:
            msg = msg + '<br/>' + msg0
            status = 0
        else:
            msg = msg + '<br/>' + msg0
            status = 1
                
        self.__outputUploadFeedback_V2(diclist, diclist_feedback, headers, feedbackfile)
        return msg, status
    
    
    def __runSanityCheck(self, diclist, diclist_ins, diclist_ont):
        status = 1
        msg = ''
        diclist_sanity = []
        headermapping = {}
        for dici in diclist_ins:
            if 'Field' not in dici:
                msg += 'Error: Instructions sheet must have a "Field" column \n'
                status = 0
            
            if 'Field Type' not in dici:
                msg += 'Error: Instruction sheet must have a "Field Type" column \n'
                status = 0
                
            if status==0:
                return msg, status, diclist_sanity
            
            header = dici['Field']
            fieldtype = dici['Field Type']
            headermapping[header] = fieldtype
        
        for dici in diclist:
            sanity_error = {}
            for header, value in dici.items():
                if header not in headermapping:
                    msgi = "Warning: header not defined in the Instructions sheet: " + header
                    sanity_error[header] = msgi
                    msg += msgi + '\n'
                else:
                    valuetype = headermapping[header]
                    isRightType = verifyValueType(valuetype, value)
                    if isRightType:
                        sanity_error[header] = value
                    else:
                        valueStr = toString(value)
                        valueStr = valueStr.strip().upper()
                        if len(valueStr)==0:
                            # allow empty value 
                            sanity_error[header] = value    
                        else:
                            status = 0
                            msgi = "Error: value not in the expected " + valuetype + " type: " + toString(value)
                            msg += msgi + '\n'
                            sanity_error[header] = msgi
                                
            diclist_sanity.append(sanity_error)
        return msg, status, diclist_sanity
        
        
    def batchUpload(self, infile, feedbackfile, seekdb):
        user_seek = seekdb.user_seek
        username = user_seek['username']
        msg = "batchUpload"
        status = 0
        try:
            filedata = load_excelfile_asdic(infile)
        except:
            msg = SAMPLE_ERRORCODE['101']
            status = 0
            return msg, status
        
        status = filedata['status']
        msg = filedata['msg']
        if status==0:
            msg = SAMPLE_ERRORCODE['106'] + msg
            return msg, status
        
        if 'UPDATE' in filedata['sheetnames'] and 'UPDATE' in filedata:
            sheetData = filedata['UPDATE']
            if "ONTOLOGY" not in filedata or "INSTRUCTIONS" not in filedata:
                return self.__batchUpdateSample(sheetData, feedbackfile, user_seek)
            
            sheetData_ont = filedata["ONTOLOGY"]
            diclist_ont = sheetData_ont['diclist']
            
            sheetData_ins = filedata["INSTRUCTIONS"]
            diclist_ins = sheetData_ins['diclist']
            
            diclist_up = sheetData['diclist']
            headers = sheetData['headers']
            ontology = DBtable_ontology()
            msg, status, ontology_feedback = ontology.evaluateOntology(diclist_up, diclist_ins, diclist_ont)
            if status==0:
                if len(ontology_feedback)==0:
                    return msg, status
                else:
                    msg = 'Error: Refer to the feedback excel file for vialation in controlled Ontology terms.'
                    ontology.outputOntologyFeedback(diclist_up, headers, feedbackfile, ontology_feedback)     
                    return msg, status
            
            return self.__batchUpdateSample(sheetData, feedbackfile, user_seek)
        
        elif 'UPDATE_ASSAY' in filedata['sheetnames'] and 'UPDATE_ASSAY' in filedata:
            sheetData = filedata['UPDATE_ASSAY']
            return self.__batchUpdateSampleAssociation(sheetData, feedbackfile, user_seek)
        
        status = 1
        for sheetname in SAMPLE_SHEET_NAMES:
            msg = SAMPLE_ERRORCODE['102']
            if sheetname not in filedata['sheetnames'] or sheetname not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                return msg, status
        
        sheetData_ins = filedata["INSTRUCTIONS"]
        diclist_ins = sheetData_ins['diclist']
        sampleTypes, sampleTypes_order = self.__loadSampleTypes(diclist_ins)
        if len(sampleTypes.keys())==0:
            msg = SAMPLE_ERRORCODE['103']
            status = 0
            return msg, status
        
        sheetData_assay = filedata["ASSAY"]
        diclist_assay = sheetData_assay['diclist']
        sheetData = filedata["SAMPLES"]
        headers = sheetData['headers']
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['104']
            status = 0
            return msg, status
        
        sheetData_ont = filedata["ONTOLOGY"]
        diclist_ont = sheetData_ont['diclist']
        
        ontology = DBtable_ontology()
        msg, status, ontology_feedback = ontology.evaluateOntology(diclist, diclist_ins, diclist_ont)
        if status==0:
            if len(ontology_feedback)==0:
                return msg, status
            else:
                msg = 'Error: Refer to the feedback excel file for violation in controlled Ontology terms.'
                ontology.outputOntologyFeedback(diclist, headers, feedbackfile, ontology_feedback)     
                return msg, status
        
        
        msg, status, diclist_sanity = self.__runSanityCheck(diclist, diclist_ins, diclist_ont)
        if status==0:
            msg = 'Error: Refer to the feedback excel file for any error.'
            self.__outputUploadFeedback_V2(diclist, diclist_sanity, headers, feedbackfile)
            return msg, status
        
        sample_sheets = self.__splitSampleTypes(sampleTypes, diclist)
        
        msg = ""
        diclist_feedback = []
        for sampleType in sampleTypes_order:
            if sampleType in sample_sheets:
                diclist_sample = sample_sheets[sampleType]
                attributeMapping = sampleTypes[sampleType]

                msgi, statusi, diclist_feedback = self.__batchUploadSampleTest(seekdb, sampleType, diclist_sample, diclist_feedback, attributeMapping, diclist_assay)                
                msg += msgi + "<br/>"
                if not statusi:
                    status = 0
            else:
                msgi = SAMPLE_ERRORCODE['105'] + sampleType
                status = 0
                msg += msgi + "<br/>"
                
        self.__outputUploadFeedback_V2(diclist, diclist_feedback, headers, feedbackfile)
        return msg, status
    
    def __getSampleUrl(self, id):
        url = "<a href='/seek/sample/id=" + str(id) + "/'  target='_blank'>" + str(id) + "</a>"
        return url
    
    def search(self, uids, orderby, limit):
        total = len(uids)
        rdata = []
        if total==0:
            data = {'total':total,'rows':rdata}
            sdata = simplejson.dumps(data, default=str)
            return sdata
        
        qset = Q(uuid__in=uids)
        rdata = self.db.retrieveJoint(self.tablemodel, '', qset, orderby, limit)
        rdata = convertDateListToString('created_at', rdata)
        rdata = convertDateListToString('updated_at', rdata)
        
        for datai in rdata:
            id = datai['id']
            datai['id'] = self.__getSampleUrl(id)
        
        total = len(rdata)
        data = {'total':total,'rows':rdata}
        sdata = simplejson.dumps(data, default=str)
        return sdata
    
    def childTube(relation):
        child = {}
        child["name"] = "bcdf"

        name = str(relation['child_tube2dtype']) + ': ' + str(relation['child_tube2dcode'])
        child["name"] = name
        next_children = []
    
        next_child_2dtube_id = relation['child_2dtube_id']
    
        if next_child_2dtube_id is None:
            msg = "No next child is found"
        else:
            next_relations = derive2DTubes(next_child_2dtube_id)
            for next_relation in next_relations:
                next_child_2dtube_id = next_relation['child_2dtube_id']
                if next_child_2dtube_id is None:
                    msg = 'No child is found'
                else:
                    next_child = childTube(next_relation)
                    next_children.append(next_child)
        
        child["children"] = next_children   
        return child
    
    def createSampleTree(self, sample_id):
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        uids =  self.__getParentUIDs(dici)
        parentinfo, treeData = self.__trackParent(childuid, uids)
        return treeData
        

    def __retrieveSampleByUID(self, uid):
        record = None
        if uid is None or len(uid.strip())==0:
            msg = 'No record is found based on the input UID: ' + uid
            return None
        
        constraint = {'uuid':uid}
        records = self.queryRecordsByConstraint(constraint)
        if len(records)==1:
            record = records[0]
        
        return record
    
    def getSampleID(self, uid):
        sample_id = None
        record = self.__retrieveSampleByUID(uid)
        if record is not None:
            sample_id = record['id']
            
        return sample_id
        
 
    def __retrieveSampleByID(self, idIn):
        record = None
        try:
            id = int(idIn)
        except:
            msg = 'No record is found based on the input ID: ' + idIn
            return None
        
        if id<=0:
            msg = 'No record is found based on the input ID: ' + idIn
            return None
        
        constraint = {'id':id}
        records = self.queryRecordsByConstraint(constraint)
        if len(records)==1:
            record = records[0]
        
        return record           
        
    def __getSeeklink(self, seek_type, id):
        seek_url = settings.SEEK_URL + "/" + seek_type + "/" + str(id) + "/"
        seeklink = '<a href="' + seek_url + '" target="_blank">' + str(id) + '</a>'
        return seeklink
        
    def __getSamplelink(self, sample_uid, sample_id):
        sample_url = "/seek/sample/id=" + str(sample_id) + "/"
        samplelink = '<a href="' + sample_url + '" target="_blank">' + str(sample_uid) + '</a>'
        return samplelink
    
        
    def reformatDataForClient(self, jdata):
        jdata_new = []
        for data in jdata:
            datadic = {}
            datadic['idlink'] = self.__getSeeklink('samples', data['id'])
            datadic['idurl'] = self.__getSamplelink(data['id'], data['id'])
            datadic['id'] = data['id']
            datadic['title'] = data['title']
            datadic['uuid'] = data['uid']
            datadic['uid'] = self.__getSamplelink(data['uid'], data['id'])
            datadic['sample_type_id'] = data['sample_type_id']
            datadic['contributor_id'] = data['contributor_id']
            datadic['created_at'] = str(data['created_at'])
            datadic['json_metadata'] = str(data['json_metadata'])
            datadic['sample_type'] = data['sample_type']
            datadic['first_name'] = data['first_name']
            datadic['assays'] = data['assays']
            
            jdata_new.append(datadic)
        
        return jdata_new
    
    def retrieveRecords(self, user_seek, filtersdic):
        return self.retrieveRecords_joint(user_seek, filtersdic)
    
    def __sqlQuery_select_records_filters(self, filtersdic):
        filterRules = filtersdic['filterRules']
        sqlquery_filter = ""
        n = 0
        for rule in filterRules:
            tablefield = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if tablefield in SAMPLE_FILTER_MAPPING:
                field = SAMPLE_FILTER_MAPPING[tablefield]
            
                if n==0:
                    sqlquery_filter += " WHERE " + field
                else:
                    sqlquery_filter += " AND " + field
                if op=="contains":
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
                elif op=="equal":
                    sqlquery_filter += "='" + str(value) + "' "
                else:
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
            n += 1
        
        return sqlquery_filter
    
    def __sqlQuery_select_records_select(self):
        sqlquery_select =  " SELECT "
        sqlquery_select +=  "A.id as id,"
        sqlquery_select +=  "A.title as title,"
        sqlquery_select +=  "A.sample_type_id as sample_type_id,"
        sqlquery_select +=  "B.title as sample_type,"
        sqlquery_select +=  "A.uuid as uid,"
        sqlquery_select +=  "A.contributor_id as contributor_id,"
        sqlquery_select +=  "C.first_name as first_name,"
        sqlquery_select +=  "A.created_at as created_at,"
        sqlquery_select +=  "A.json_metadata as json_metadata,"
        
        sqlquery_select +=  "("
        sqlquery_select +=  "SELECT GROUP_CONCAT(E.title) as assays "
        sqlquery_select +=  "FROM assay_assets D "
        sqlquery_select +=  "left join assays E on E.id=D.assay_id "
        sqlquery_select +=  "WHERE A.id=D.asset_id AND D.asset_type='Sample' "
        sqlquery_select +=  ") "
        return sqlquery_select
    
    def __sqlQuery_select_records_from(self, projectID=None):
        sqlquery_from =  " FROM "   
        sqlquery_from +=  "samples A "
        sqlquery_from +=  "left join sample_types B on A.sample_type_id=B.id "
        sqlquery_from +=  "left join people C on A.contributor_id=C.id "
        if projectID is not None and projectID!=0:
            sqlquery_from +=  "left join projects_samples D on D.sample_id=A.id "
        
        return sqlquery_from     
    
    def __sqlQuery_select_records(self, filtersdic, withLimit=True):
        sqlquery_select = self.__sqlQuery_select_records_select()
        sqlquery_from = self.__sqlQuery_select_records_from()
        orderby = filtersdic['orderby'] 
        startNo = filtersdic['startNo'] 
        endNo = filtersdic['endNo']     
        sqlquery_where = self.__sqlQuery_select_records_filters(filtersdic)
        sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where
        
        if len(orderby)==0:
            orderby = " ORDER BY A.id desc"
        
        if withLimit:
            sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where + orderby
        else:
            sqlqueryMega = " SELECT count(A.id) " + sqlquery_from
        
        return sqlqueryMega
    
    def retrieveRecords_joint(self, user_seek, filtersdic):
        sqlquery = self.__sqlQuery_select_records(filtersdic)
        headers = SAMPLE_HEADERS
        db_alias = settings.SEEK_DATABASE
        jdata = self.db.queryToListDics(sqlquery, headers, db_alias)
        sqlquery = self.__sqlQuery_select_records(filtersdic, False)
        total = self.db.getQueryValue(sqlquery, db_alias)
        if total is None:
            total = 0
        else:
            total = int(total)
    
        jdata_new = self.reformatDataForClient(jdata)
        footer = []
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data

    def __getParentUIDs(self, sampleDic):
        uids = []
        for key, value in sampleDic.iteritems():
            if SAMPLE_PARENT_ACCESSOR_NAME in key:
                if value is None:
                    continue
                else:
                    if ";" in value:
                        vis = value.split(";")
                        for vi in vis:
                            vi = vi.strip()
                            if len(vi)>0:
                                uids.append(vi)
                    else:
                        value = value.strip()
                        if len(value)>0:
                            uids.append(value)
                
        return uids
    
    def __getParents(self, childuid):
        record_db = self.__retrieveSampleByUID(childuid)
        if record_db is None:
            return []
            
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        uids = self.__getParentUIDs(sampleDic)
        return uids

    def __getParentLoop(self, childuid):
        parent = {}
        parent["name"] = str(childuid)
        parent["id"] = str(childuid)
        parent_uids = self.__getParents(childuid)
        next_parents = []
        for uid in parent_uids:
            next_parent = self.__getParentLoop(uid)
            next_parents.append(next_parent)
        
        if len(next_parents)>0:
            parent["children"] = next_parents
        return parent

    def __trackParent(self, childuid, parent_uids):
        treeData = {}
        treeData["name"] = str(childuid)
        treeData["id"] = str(childuid)
        
        parents = []
        parentinfo = ''
        for uid in parent_uids:
            parent = self.__getParentLoop(uid)
            parents.append(parent)
            
            parentinfo += uid + ';'
            
        parentinfo = parentinfo[:-1]

        if len(parents)>0:
            treeData["children"] = parents
        return parentinfo, treeData
        

    def __filterSamples(self, jdata, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        if filter_rule=='No Filter':
            return jdata
        
        accessor_name = attribute.lower().strip()
        
        values = []     
        parentUIDs = []    
        n = 0
        for data in jdata:
            json_metadata = data['json_metadata']
            dici = self.__getRecordFromJson(json_metadata)
            
            if accessor_name not in dici:
                value = None
            else:
                value = dici[accessor_name]
            values.append(value)
            
            uids = self.__getParentUIDs(dici)
            parentUIDs.append(uids)
            
            n += 1
            
        sattr = DBtable_sampleattribute()
        passvalues = sattr.filterValues(values, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
        
        jdata_new = []
        parentUIDs_new = [] 
        index = 0
        ni = 0
        for data in jdata:
            passit = passvalues[index]
            if passit:
                childuid = data['uid']
                uids = parentUIDs[index]
                parentinfo, treeData = self.__trackParent(childuid, uids)
                data['parent_uids'] = ';'.join(uids)
                jdata_new.append(data)
                ni += 1
            index += 1
        
        return jdata_new
    
    def searchSamples(self, user_seek, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            if status==0:
                data = {'msg':msg, 'status': status}
                reportData = simplejson.dumps(data, default=str)
                return reportData
        
        filtersdic = {}
        filtersdic['orderby'] = " ";
        filtersdic['limit'] = " ";
        filtersdic['suffix'] = " ";
        filtersdic['startNo'] = " "
        filtersdic['endNo'] = " "
        filtersdic['sqlquery_filter'] = " "
        filterRules = [{
            "field":"sample_type_id",
            "op":"equal",
            "value":sampletype_id
        }]
        filtersdic['filterRules'] = filterRules
        data = self.retrieveRecords_joint(user_seek, filtersdic)
        if attribute=='none':
            msg = 'ignore filtering'
        else:
            rows = self.__filterSamples(data['rows'], sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo) 
            data['rows'] = rows
            data['total'] = len(rows)
        data['msg'] = 'okay'
        data['status'] = 1
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def __getChildrenUIDs(self, currentuid):
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', currentuid)
        uids = []
        for record in records:
            uid = record['uuid']
            metadata = record['json_metadata']
            sampleDic = self.__getRecordFromJson(metadata)
            parent_uids = self.__getParentUIDs(sampleDic)
            if currentuid in parent_uids:
                uids.append(uid)
            
        return uids
    
    def __getChildLoop(self, parentuid):
        child = {}
        child["name"] = str(parentuid)
        child["id"] = str(parentuid)
        child_uids = self.__getChildrenUIDs(parentuid)
        if len(child_uids)==0:
            return child
        
        next_children = []
        for uid in child_uids:
            next_child = self.__getChildLoop(uid)
            next_children.append(next_child)
        
        if len(next_children)>0:
            child["children"] = next_children
        return child
    
    def createSampleChildrenTree(self, sample_id):
        return self.createSampleChildrenTreeParallel(sample_id)
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        currentuid = record['uuid']
        children_uids =  self.__getChildrenUIDs(currentuid)
        
        treeData = {}
        treeData["name"] = str(currentuid)
        treeData["id"] = str(currentuid)

        children = []
        for uid in children_uids:
            child = self.__getChildLoop(uid)
            children.append(child)

        if len(children)>0:
            treeData["children"] = children
        return treeData
    
    def createSampleChildrenTreeParallel_i(self, uid):
        child = self.__getChildLoop(uid)
        return child
    
    def createSampleChildrenTreeParallel(self, sample_id):
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        currentuid = record['uuid']
        children_uids =  self.__getChildrenUIDs(currentuid)
        
        treeData = {}
        treeData["name"] = str(currentuid)
        treeData["id"] = str(currentuid)
        
        children = []
        num_cores = multiprocessing.cpu_count()
        n = len(children_uids)
        childs = Parallel(n_jobs=-2, backend="threading")\
            (delayed(unwrap_self_createSampleChildrenTreeParallel_i)(i) for i in zip([self]*n, children_uids))

        for child in childs:
            children.append(child)

        if len(children)>0:
            treeData["children"] = children
        return treeData
    
    
    def __getParentTreeListLoop(self, childNode):
        upTreeList = []
        childuid = childNode['id']
        parent_uids = self.__getParents(childuid)
        if parent_uids is None or len(parent_uids)==0:
            upTreeList.append(childNode)
            return upTreeList
        
        for uid in parent_uids:
            uid = str(uid)
            node = {'id':uid, 'name':uid, 'children':[childNode]}
            parentTreeList = self.__getParentTreeListLoop(node)
            upTreeList += parentTreeList
            
        return upTreeList
    
    def __trackParentTreeList(self, childuid, parent_uids):
        upTreeList = []
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        if len(parent_uids)==0:
            upTreeList.append(child)
            return upTreeList
        
        for uid in parent_uids:
            uid = str(uid)
            childNode = {'id':uid, 'name':uid, 'children':[child]}
            parentTreeList = self.__getParentTreeListLoop(childNode)
            upTreeList += parentTreeList
            
        return upTreeList
    
    def __createMultiParentTree(self, sample_id, includeChilren, childrenTreeIn=None):
        return self.__createMultiParentTreeParallel(sample_id, includeChilren, childrenTreeIn)
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        parent_uids =  self.__getParentUIDs(dici)
        
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        
        if includeChilren:
            child = self.createSampleChildrenTree(sample_id)
        
        upTreeList = []
        if len(parent_uids)==0:
            upTreeList.append(child)
        else:
            for uid in parent_uids:
                uid = str(uid)
                childNode = {'id':uid, 'name':uid, 'children':[child]}
                parentTreeList = self.__getParentTreeListLoop(childNode)
                upTreeList += parentTreeList
        
        return upTreeList
    
    def createMultiParentTreeParallel_i(self, uid, child):
        uid = str(uid)
        childNode = {'id':uid, 'name':uid, 'children':[child]}
        parentTreeList = self.__getParentTreeListLoop(childNode)
        return parentTreeList
    
    def __createMultiParentTreeParallel(self, sample_id, includeChilren, childrenTreeIn=None):
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        parent_uids =  self.__getParentUIDs(dici)
        
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        if includeChilren:
            if childrenTreeIn is None:
                child = self.createSampleChildrenTree(sample_id)
            else:
                child = childrenTreeIn
        
        upTreeList = []
        if len(parent_uids)==0:
            upTreeList.append(child)
        else:
            num_cores = multiprocessing.cpu_count()
            n = len(parent_uids)
            parentTreeLists = Parallel(n_jobs=-2, backend="threading")\
                (delayed(unwrap_self_createMultiParentTreeParallel_i)(i) for i in zip([self]*n, parent_uids, [child]*n))
            
            for parentTreeList in parentTreeLists:
                upTreeList += parentTreeList
        
        return upTreeList
    
    def __getChildrenListLoop(self, parentTreeData):
        listlists = []
        for node in parentTreeData:
            if 'children' in node:
                children = node['children']
                sublists = self.__getChildrenListLoop(children)
            else:
                sublists = [[]]
            
            uid = node['id']
            for listi in sublists:
                newlist = [uid] + listi
                listlists.append(newlist)
        
        return listlists
        
    
    def createSampleMultiParentTree(self, sample_id):
        includeChilren = True
        fullTreeList = self.__createMultiParentTree(sample_id, includeChilren)
        
        if fullTreeList is None:
            multi_parents_treeData = {
                'name': "Sample Tree",
                'id': "cert-root"
            }
        else:
            multi_parents_treeData = {
                'name': "Sample Tree",
                'id': "cert-root",
                'children': fullTreeList
            }
        
        return multi_parents_treeData
    
    def __convertListlistsIntoDiclist_toberemoved(self, parentList):
        n0 = 0
        list0 = None
        for listi in parentList:
            ni = len(listi)
            if ni>n0:
                n0 = ni
                list0 = listi
                
        sampleTypes = []
        for uid in list0:
            if "-" in uid:
                terms = uid.split('-')
                sampleType = terms[0]
            else:
                sampleType = uid
            sampleTypes.append(sampleType)
            
        diclist = []
        for listi in parentList:
            dici = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                dici[sampleType] = uid
                
            diclist.append(dici)
            
        return sampleTypes, diclist
    
    def __getSampleTypeAttributes(self, parentList):
        sampleTypes = []       
        sampleTypeCount = {}
        for listi in parentList:
            sampleTypeCount_i = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                    
                if sampleType not in sampleTypes:
                    sampleTypes.append(sampleType)
                    
                if sampleType not in sampleTypeCount_i:    
                    sampleTypeCount_i[sampleType] = 1
                else:
                    sampleTypeCount_i[sampleType] = sampleTypeCount_i[sampleType] + 1
                    
            for sampleType_i, count_i in sampleTypeCount_i.iteritems():
                if sampleType_i not in sampleTypeCount:
                    sampleTypeCount[sampleType_i] = count_i
                else:
                    if count_i>sampleTypeCount[sampleType_i]:
                        sampleTypeCount[sampleType_i] = count_i
                
        stype = DBtable_sampletype("DEFAULT")
        attributes = stype.retrieveAttributes(sampleTypes)
        headers = []
        headersMapping = {} 
        for attr in attributes:
            for sampleType, attrInfo in attr.iteritems():
                count = sampleTypeCount[sampleType]
                for i in range(count):
                    if count>1:
                        suffix = "_" + str(i+1)
                        prefix = sampleType + suffix + ':'      
                    else:
                        prefix = sampleType + ':'
                
                    if attrInfo is not None and 'headers' in attrInfo:
                        headers_i = attrInfo['headers']
                        for header in headers_i:
                            title = prefix + header
                            newheader = prefix + header.lower()
                            headers.append(newheader)
                            headersMapping[newheader] = title

        return sampleTypes, sampleTypeCount, headers, headersMapping
    
    def __retrieveSampleJsonData(self, uid):
        record_db = self.__retrieveSampleByUID(uid)
        if record_db is None:
            return None
            
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        return sampleDic
        
    def __saveSampleList_toberemoved(self, sampleTypes, diclist, excelfile):
        stype = DBtable_sampletype("DEFAULT")
        attributes = stype.retrieveAttributes(sampleTypes)
        uids = {}
        for dici in diclist:
            for sampletype, uid in dici.iteritems():
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        for dici in diclist:
            dici_new = {}
            for sampletype, uid in dici.iteritems():
                if uid in uids:
                    sampleDic = uids[uid]
                    if sampleDic is not None and sampleDic is not []:
                        for key, value in sampleDic.iteritems():
                            newkey = sampletype + ':' + key
                            dici_new[newkey] = value
            diclist_new.append(dici_new)
            
        headers = []
        for attr in attributes:
            for sampletype, attrInfo in attr.iteritems():
                if attrInfo is not None and 'headers' in attrInfo:
                    headers_i = attrInfo['headers']
                    for header in headers_i:
                        newheader = sampletype + ":" + header.lower()
                        headers.append(newheader)
                        
        saveDiclistIntoExcel(diclist_new, excelfile, headers, 'samples')
        nsamples = len(diclist_new)
        return nsamples
        
    def __convertSampleTreeToList(self, parentList, sampleTypes, sampleTypeCount, headers):
        uids = {}
        for listi in parentList:
            for uid in listi:
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        diclist_new = []
        for listi in parentList:
            dici_new = {}
            sampleTypeCount_now = {}        
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    sampleTypeCount_now[sampleType] = 1
                else:
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                count = sampleTypeCount[sampleType]
                if count==1:
                    prefix = sampleType + ':'     
                else:
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix + ':'       # such as "DNA_2:"
                
                sampleDic = uids[uid]
                if sampleDic is not None and sampleDic is not []:
                    for key, value in sampleDic.iteritems():
                        newkey = prefix + key
                        dici_new[newkey] = value        
            diclist_new.append(dici_new)
        
        headers_new = filterDiclist(headers, diclist_new)
        return headers_new, diclist_new
    
    def __saveSampleList(self, headers_new, diclist_new, excelfile, attributeFilter=None):
        headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
        if attributeFilter is not None and len(attributeFilter)>0:
            headersFiltered = []
            if ',' in attributeFilter:
                headersFiltered = attributeFilter.split(',')
            
            headers_noneConstant_new = []
            for header in headers_noneConstant:
                if header in headersFiltered:
                    headers_noneConstant_new.append(header)
            headers_noneConstant = headers_noneConstant_new
            
            diclist_constant_new = []
            for dici in diclist_constant:
                header = dici[headers_constant[0]]
                if header in headersFiltered:
                    diclist_constant_new.append(dici)
            diclist_constant = diclist_constant_new
        
        saveTwoDiclistsIntoExcel(excelfile, diclist_new, headers_noneConstant, 'samples', diclist_constant, headers_constant, 'constants')
        nsamples = len(diclist_new)
        return nsamples


    def __createSampleTreeToList(self, sample_id, xlsfile='test.xls'):
        includeChilren = False
        upTreeList = self.__createMultiParentTree(sample_id, includeChilren)
        parentList = self.__getChildrenListLoop(upTreeList)
        sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(parentList)
          
        headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)        
        nsamplesOutput = self.__saveSampleList(headers_new, diclist_new, xlsfile)
        return parentList


    def __createSampleTree(self, sample_ids):
        includeChilren = False
        parentList = []
        for sample_id in sample_ids:
            upTreeList = self.__createMultiParentTree(sample_id, includeChilren)
            parentList_i = self.__getChildrenListLoop(upTreeList)
            parentList += parentList_i
        
        sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(parentList)       
        headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)       
        return headers_new, diclist_new, headersMapping

    def __createSampleTreeToList_new(self, sample_ids, xlsfile='test.xls', attributeFilter=None):
        headers_new, diclist_new, headersMapping = self.__createSampleTreeFromDB(sample_ids)
        nsamplesOutput = self.__saveSampleList(headers_new, diclist_new, xlsfile, attributeFilter)
        return nsamplesOutput


    def __exportParentList(self, parentList, xlsfile):
        sampleTypes = []       
        sampleTypeCount = {}   
        for listi in parentList:
            sampleTypeCount_i = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                    
                if sampleType not in sampleTypes:
                    sampleTypes.append(sampleType)
                    
                if sampleType not in sampleTypeCount_i:    
                    sampleTypeCount_i[sampleType] = 1
                else:
                    sampleTypeCount_i[sampleType] = sampleTypeCount_i[sampleType] + 1
                    
            for sampleType_i, count_i in sampleTypeCount_i.iteritems():
                if sampleType_i not in sampleTypeCount:
                    sampleTypeCount[sampleType_i] = count_i
                else:
                    if count_i>sampleTypeCount[sampleType_i]:
                        sampleTypeCount[sampleType_i] = count_i
                
        headers = []
        for sampleType in sampleTypes:
            count = sampleTypeCount[sampleType]
            for i in range(count):
                if count>1:
                    suffix = "_" + str(i+1)
                    prefix = sampleType + suffix 
                else:
                    prefix = sampleType
                
                headers.append(prefix)
        
        diclist = []
        for listi in parentList:
            dici = {}
            sampleTypeCount_now = {}        
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    sampleTypeCount_now[sampleType] = 1
                else:
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                count = sampleTypeCount[sampleType]
                if count==1:
                    prefix = sampleType
                else:
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix
                
                dici[prefix] = uid
                    
            diclist.append(dici)
        saveDiclistIntoExcel(diclist, xlsfile, headers, 'uids')  

    def __formatHttpLink(self, stritem):
        if stritem is None:
            return stritem
        
        newstr = 'HYPERLINK(' + stritem + ')'
        newitem = xlwt.Formula(newstr)
        return newitem
    
    
    def __saveSamples(self, xlsfile, diclist, headers, sheetname_2=None, diclist_2=None, headers_2=None):
        book = xlwt.Workbook(encoding="utf-8")
        sheet1 = book.add_sheet("Samples")
        row = 0
        for index, header in enumerate(headers):
            try:
                newitem = toString(header)
            except:
                newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
        
        for dici in diclist:
            row += 1
            for index, header in enumerate(headers):
                if header in dici:
                    newitem = dici[header]
                else:
                    newitem = "N/A"
                
                try:
                    newitem = str(newitem)
                    if 'http' in newitem:
                        newitem = self.__formatHttpLink(newitem)
                except:
                    newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
        
        if sheetname_2 is None:
            book.save(xlsfile)
            return
        
        sheet2 = book.add_sheet(sheetname_2)        
        row = 0
        for index, header in enumerate(headers_2):
            try:
                newitem = toString(header)
            except:
                newitem = cleanString(newitem)
            sheet2.write(row, index, newitem)
        
        for dici in diclist_2:
            row += 1
            for index, header in enumerate(headers_2):
                if header in dici:
                    newitem = dici[header]
                else:
                    newitem = "N/A"
                
                try:
                    newitem = str(newitem)
                    if 'http' in newitem:
                        newitem = self.__formatHttpLink(newitem)
                except:
                    newitem = cleanString(newitem)
                sheet2.write(row, index, newitem)
                
        book.save(xlsfile)
        
    def __formatSampleDownload(self, sampletype_id, diclist):
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        headers = attributeInfo['headers']
        metadata = []
        for dici in diclist:
            json_metadata = dici['json_metadata']
            record = self.__getRecordFromJson(json_metadata)
            metadata.append(record)
        
        newheaders = []
        for header in headers:
            newheaders.append(header.lower())
        return newheaders, metadata
        
    def downloadSamples(self, user_seek, xlsfile, link, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            if status==0:
                data = {'msg':msg, 'status': status, 'link':''}
                reportData = simplejson.dumps(data, default=str)
                return reportData
        
        filtersdic = {}
        filtersdic['orderby'] = " ";
        filtersdic['limit'] = " ";
        filtersdic['suffix'] = " ";
        filtersdic['startNo'] = " "
        filtersdic['endNo'] = " "
        filtersdic['sqlquery_filter'] = " "
        filterRules = [{
            "field":"sample_type_id",
            "op":"equal",
            "value":sampletype_id
        }]
        filtersdic['filterRules'] = filterRules
        data = self.retrieveRecords_joint(user_seek, filtersdic)
        if attribute=='none':
            msg = 'ignore filtering'
            rows = data['rows']
        else:
            rows = self.__filterSamples(data['rows'], sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
        
        sample_ids = []
        for row in rows:
            uid = row['uid']
            sample_id = str(row['pid'])
            sample_ids.append(sample_id)
        self.__createSampleTreeToList_new(sample_ids, xlsfile) 
        data['msg'] = 'okay'
        data['status'] = 1
        data['link'] = link
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    
    def downloadSamples_new(self, user_seek, xlsfile, link, sample_ids, includeSampleTree=1, attributeFilter=None):
        if includeSampleTree==1:
            nsamplesOutput = self.__createSampleTreeToList_new(sample_ids, xlsfile, attributeFilter)
        else:
            isNewSheet = True
            msg, status, nsamplesOutput = self.__downloadSampleList(sample_ids, xlsfile, isNewSheet)
        
        data = {}
        data['link'] = link
        if nsamplesOutput>=len(sample_ids):
            data['msg'] = 'okay'
            data['status'] = 1
        else:
            data['msg'] = 'Warning: Number of samples output: ' + str(nsamplesOutput) + ' is less than the number selected: ' + str(len(sample_ids))
            data['status'] = 0
            
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def __exportImmportSheetInfo(self, headersMapping, diclist_new, templatedata, sheetName, excelfile):
        nameup = sheetName.upper()
        sheetData = templatedata[nameup]
        diclist = sheetData['diclist']
        
        headers = []
        mapping = {}
        for dici in diclist:
            header = dici['ImmPort']
            attribute = dici['FairData']
            if attribute is not None:
                headers.append(header)
                mapping[header] = attribute
                
        diclistOut = []
        for dici in diclist_new:
            diciOut = {}
            for header in headers:
                attribute = mapping[header]
                if ":" in attribute:
                    terms = attribute.split(":")
                    attribute = terms[0] + ":" + terms[1].lower()
                
                if attribute in dici:
                    diciOut[header] = dici[attribute]
                else:
                    if ":" in attribute:
                        diciOut[header] = ''
                    else:
                        diciOut[header] = attribute
            
            diclistOut.append(diciOut)
            diclistOut = removeDiclistDuplicates(diclistOut)
        
        reviseExcelDiclist(excelfile, headers, diclistOut, sheetName)
        return
    
    def __exportImportProtocls(self, user_seek, diclist, zf):
        dbsop = DBtable_sops("DEFAULT")
        diclist_new = []
        for dici in diclist:
            if "File Name" in dici:
                sop_link = dici["File Name"] 
                terms = sop_link.split('/')
                if sop_link[-1]=='/':
                    uidterm = terms[-2]
                else:
                    uidterm = terms[-1]
                    
                if "=" in uidterm:  
                    terms = uidterm.split("=")
                    sop_uid = terms[-1]
                    fullfilename, status, link = dbsop.downloadSOP_fromStorage(user_seek, sop_uid)
                    if status==1:
                        dici['User Defined ID'] = sop_uid
                        terms = fullfilename.split('/')
                        originalName = terms[-1]
                        dici['Name'] = originalName
                        
                        if os.path.isfile(fullfilename):
                            zf.write(fullfilename, originalName)
            
            diclist_new.append(dici)
        return diclist_new
        
    
    def __exportImmportSheetInfoZip(self, user_seek, headersMapping, diclist_new, templatedata, sheetName, txtfile, fileLabel, zf):
        nameup = sheetName.upper()
        sheetData = templatedata[nameup]
        diclist = sheetData['diclist']
        
        headers = []
        mapping = {}
        for dici in diclist:
            header = dici['ImmPort']
            attribute = dici['FairData']
            if attribute is not None:
                headers.append(header)
                mapping[header] = attribute
                
        diclistOut = []
        for dici in diclist_new:
            diciOut = {}
            for header in headers:
                attribute = mapping[header]
                if ":" in attribute:
                    terms = attribute.split(":")
                    attribute = terms[0] + ":" + terms[1].lower()
                
                if attribute in dici:
                    diciOut[header] = dici[attribute]
                else:
                    if ":" in attribute:
                        diciOut[header] = ''
                    else:
                        diciOut[header] = attribute
            
            diclistOut.append(diciOut)
            diclistOut = removeDiclistDuplicates(diclistOut)
        
        if sheetName=='protocols':
            diclistOut = self.__exportImportProtocls(user_seek, diclistOut, zf)
        
        fo = open(txtfile,"w")
        
        delimit = '\t'
        line = fileLabel + delimit + IMMPORT_TEMPLATES_VERSION + '\n'
        fo.write(line)
        line = "Please do not delete or edit this column"  + '\n'
        fo.write(line)
        
        line = delimit.join(headers) + '\n'
        fo.write(line)
        for dici in diclistOut:
            line = ""
            for index, header in enumerate(headers):
                if header in dici:
                    item = dici[header]
                    newitem = toString(item)
                else:
                    newitem = ""
                
                line += newitem + delimit
        
            line = line[:-1] + '\n'
            fo.write(line)
        fo.close()    
        return           
            
    def __exportImmportSampleListZip(self, user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping):
        if 'xlsx' in downloadfile:
            return self.__exportImmportSampleList(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
            
        excelfile = downloadfile.replace('zip', 'xlsx')
        templatefile = IMMPORT_TEMPLATE_FILE
        cmd = 'cp ' + templatefile + ' ' + excelfile
        os.system(cmd)
        
        msg = "Load Immport template file"
        status = 0
        
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: Immport template file not loaded: " + excelfile
            status = 0
            return msg, status

        status = 1
        for sheetname in IMMPORT_TEMPLATES:
            msg = "Error: the following sheet is missing: "
            nameup = sheetname.upper()
            if nameup not in filedata['sheetnames'] or nameup not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                return msg, status
        
        zf = zipfile.ZipFile(downloadfile, mode='w')
        status = 0
        msg = "Start generating zip file"
        for sheetname in IMMPORT_TEMPLATES:
            filename = sheetname + '.txt'
            sheetfile = DOWNLOAD_DIRECTORY + filename
            fileLabel = IMMPORT_TEMPLATES[sheetname]
            self.__exportImmportSheetInfoZip(user_seek, headersMapping, diclist_new, filedata, sheetname, sheetfile, fileLabel, zf)
            zf.write(sheetfile, filename)
        
        zf.close()
        return "Okay", 1
    
    def __exportImmportSampleList(self, user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping):
        if 'zip' in downloadfile:
            return self.__exportImmportSampleListZip(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
            
        excelfile = downloadfile
        templatefile = IMMPORT_TEMPLATE_FILE
        cmd = 'cp ' + templatefile + ' ' + excelfile
        os.system(cmd)
        
        msg = "Load Immport template file"
        status = 0
        
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: Immport template file not loaded: " + excelfile
            status = 0
            return msg, status

        status = 1
        for sheetname in IMMPORT_TEMPLATES:
            msg = "Error: the following sheet is missing: "
            nameup = sheetname.upper()
            if nameup not in filedata['sheetnames'] or nameup not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                return msg, status
        
        for sheetname in IMMPORT_TEMPLATES:
            self.__exportImmportSheetInfo(headersMapping, diclist_new, filedata, sheetname, downloadfile)
            
        return "Okay", 1
    
    
    def __exportImmportCreateSampleTreeToList(self, user_seek, sample_ids, downloadfile, sampletypeName):
        headers_new, diclist_new, headersMapping = self.__createSampleTree(sample_ids)
        msg, status = self.__exportImmportSampleList(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
        return msg
    
    
    def exportSamples(self, user_seek, xlsfile, link, sample_ids, sampletype_id):
        stype = DBtable_sampletype()
        sampletypeName = stype.retrieveFieldValue(sampletype_id, 'title')
        return self.__exportSamples0(user_seek, xlsfile, link, sample_ids, sampletypeName)

    def __exportSamples0(self, user_seek, downloadfile, link, sample_ids, sampletypeName):
        sampletypeName = 'D.MSP'
        nsamplesOutput = self.__exportImmportCreateSampleTreeToList(user_seek, sample_ids, downloadfile, sampletypeName)
        msg = 'Okay'
        data = {}
        data['link'] = link
        if nsamplesOutput>=len(sample_ids):
            data['msg'] = 'okay'
            data['status'] = 1
        else:
            data['msg'] = msg
            data['status'] = 0
            
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def __verifyFileInRecord(self, sampleRecord, originalfilename, filetype):
        if 'json_metadata' not in sampleRecord:
            return false
        
        fileInRecord = False
        json_metadata = sampleRecord['json_metadata']
        sampledic = self.__getRecordFromJson(json_metadata)
        for key, value in sampledic.iteritems():
            if filetype=="SOP":
                if SAMPLE_PROTOCOL_ACCESSOR_NAME in key.lower():
                    if value==originalfilename:
                        fileInRecord = True
            
            if filetype=="DATAFILE":
                if SAMPLE_FILE_ACCESSOR_NAME in key.lower():
                    if value==originalfilename:
                        fileInRecord = True
        return fileInRecord, sampledic
    
    def searchFileInSample(self, creator, originalfilename, filetype):
        creator_id = creator['user_id']
        if filetype!="SOP" and filetype!="DATAFILE":
            msg = 'Error: file type not supported for uploading file.'
            return None, msg
        
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', originalfilename)
        if records is None:
            msg = 'Warning: File not associated with any sample that has been uploaded first'
            return None, msg
        
        nrecords = len(records)
        if nrecords<=0:
            msg = 'Warning: File not associated with any sample that has been uploaded first'
            return None, msg
        
        msg = "Number of samples for the file: " + str(nrecords)
        creator_lab = creator['lababbv']
        records_now = []
        for record in records:
            contributor_id = record['contributor_id']
            sample_uid = record['uuid']
            msg += "Creator lab " + creator_lab + " sample UID: " + sample_uid
            if sample_uid is not None and creator_lab in sample_uid:
                fileInRecord, sampledic = self.__verifyFileInRecord(record, originalfilename, filetype)
                if fileInRecord:
                    record_now = record.update(sampledic)
                    records_now.append(record)
        
        nnow = len(records_now)
        if nnow==1:
            sampleRecord = records_now[0]
            msg = 'okay'
        elif nnow>1:
            if filetype=="SOP":
                msg = 'okay'
                sampleRecord = records_now[0]
            else:
                msg += 'Error: File associated with more than one sample that has been uploaded'
                sampleRecord = None
        else:
            sampleRecord = None
            msg += 'Error: No sample is defined for the file from same user'
        
        return sampleRecord, msg
    
    
    def updateSampleDFurl(self, username, sample_uid, originalfilename, df_link):
        msg = ''
        status = 0
        record_db = self.__retrieveSampleByUID(sample_uid)
        if record_db is None:
            msg = 'Error: sample not found: ' + sample_uid
            return msg, status
        
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        
        suffix = None
        for key, value in sampleDic.iteritems():
            if SAMPLE_FILE_ACCESSOR_NAME in key:
                if value==originalfilename:
                    suffix = key.replace(SAMPLE_FILE_ACCESSOR_NAME, '')     # such as "qc"
        
        for key, value in sampleDic.iteritems():
            if SAMPLE_LINK_ACCESSOR_NAME in key:
                suffixi = key.replace(SAMPLE_LINK_ACCESSOR_NAME, '')        # such as 'qc'
                if suffix is not None and suffixi==suffix:
                    sampleDic[key] = df_link
        
        record_db['json_metadata'] = simplejson.dumps(sampleDic, default=str)
        msg, status, sample_id = self.storeOneRecord(username, record_db)
        return msg, status
    
    
    def __deleteOneSample(self, sample_id, policy_id):
        sqlqueries = []
        sqlquery = "DELETE FROM projects_samples where sample_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM sample_resource_links where sample_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM sample_auth_lookup where asset_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM assay_assets where asset_id=" + str(sample_id) + " AND asset_type='Sample';"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM assets_creators where asset_id=" + str(sample_id) + " AND asset_type='Sample';"
        sqlqueries.append(sqlquery)
        sqlquery = "delete FROM samples where id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM permissions where policy_id=" + str(policy_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "delete FROM policies where id=" + str(policy_id) + ";"
        sqlqueries.append(sqlquery)
        db_alias = SEEK_DATABASE
        status = self.db.run_custom_transaction(sqlqueries, db_alias)
        if status:
            msg = "Trandsaction successful"
        else:
            msg = "Error: The trandsaction of deletion failed. Delete this sample manually"
        
        return msg, status
    
    def __getSampleChildren(self, currentuid):
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', currentuid)
        childrenList = []
        for record in records:
            uid = record['uuid']
            metadata = record['json_metadata']
            sampleDic = self.__getRecordFromJson(metadata)
            parent_uids = self.__getParentUIDs(sampleDic)
            if currentuid in parent_uids:
                sid = record['id']
                dici = {'id':sid, 'uid':uid}
                childrenList.append(dici)
            
        return childrenList
    
    def __deleteSampleList(self, user_seek, sample_ids, xlsfile):
        user_id = user_seek['user_id']
        roles_mask = self.db.retrieveFieldValue(People, user_id, 'roles_mask')
    
        status = 1
        msg = ''
        diclist = []
        for sample_id in sample_ids:
            dici = {}
            dici['id'] = sample_id
            record = self.__retrieveSampleByID(sample_id)
            if record is None:
                msgi = 'Error: Sample ' + str(sample_id) +  ' not found in DB '
                status = 0
                dici['json_metadata'] = msgi
                msg += msgi + '<br/>'
                diclist.append(dici)
                continue
            
            contributor_id = record['contributor_id']
            policy_id = record['policy_id']
            currentuid = record['uuid']
            
            dici['uid'] = currentuid
            childrenList =  self.__getSampleChildren(currentuid)
            if user_id==contributor_id or roles_mask>0:
                if len(childrenList)==0:
                    msgi, statusi = self.__deleteOneSample(sample_id, policy_id)
                    if statusi:
                        dici['statusi'] = 'DELETED'
                    else:
                        dici['statusi'] = msgi
                else:
                    msgi = 'Warning: Sample has child sample thus has to be deleted manually.'
                    msg += msgi + '<br/>'
                    status = 0
                    dici['statusi'] = msgi
            else:
                msgi = 'Error: Only admin or owner is allowed to delete sample.'
                msg += msgi + '<br/>'
                status = 0
                dici['statusi'] = msgi
            dici['json_metadata'] = msgi
            diclist.append(dici)
        
        headers = ['id', 'uid', 'sample_type', 'first_name', 'created_at', 'json_metadata', 'statusi']
        saveDiclistIntoExcel(diclist, xlsfile, headers, 'samples')
        return diclist, msg, status 
    
    def deleteSamples(self, user_seek, xlsfile, link, sample_ids):
        diclist, msg, status = self.__deleteSampleList(user_seek, sample_ids, xlsfile)
        data = {}
        data['msg'] = msg
        data['status'] = status
        data['link'] = link
        data['diclist'] = diclist
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    
    def __formatSampleUIDLink(self, sample_uid):
        url = "/seek/sampletree/uid=" + sample_uid + "/";
        weblink = '<a href="' + url + '" target="_blank">' + str(sample_uid) + '</a>'
        return weblink

    def __formatSopUIDLink(self, sop_uid):
        url = "/seek/sop/uid=" + sop_uid + "/";
        weblink = '<a href="' + url + '" target="_blank">' + str(sop_uid) + '</a>'
        return weblink
    
    def __formatLinkUrl(self, attrname, attrvalue):
        weblink = attrvalue
        value = attrvalue
        
        if SAMPLE_PARENT_ACCESSOR_NAME in attrname:
            if attrvalue is None:
                return weblink
            
            if ";" in value:
                weblink = ''
                vis = value.split(";")
                i = 0
                for vi in vis:
                    vi = vi.strip()
                    if len(vi)>0:
                        if i>0:
                            weblink += ","
                            
                        weblink += self.__formatSampleUIDLink(vi)
                        i += 1
            else:
                value = value.strip()
                if len(value)>0:
                    weblink = self.__formatSampleUIDLink(value)
        
        elif SAMPLE_PROTOCOL_ACCESSOR_NAME in attrname:
            if attrvalue is None:
                return weblink
            
            if ";" in value:
                weblink = ''
                vis = value.split(";")
                i = 0
                for vi in vis:
                    vi = vi.strip()
                    if len(vi)>0:
                        if i>0:
                            weblink += ","
                            
                        weblink += self.__formatSopUIDLink(vi)
                        i += 1
            else:
                value = value.strip()
                if len(value)>0:
                    weblink = self.__formatSopUIDLink(value)
        
        elif SAMPLE_LINK_ACCESSOR_NAME in attrname:
            if attrvalue is None:
                return weblink
        
        return weblink
    
    
    def getSampleInfo(self, sample_id):
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None, None
        
        sampletype_id = record['sample_type_id']
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        headers = attributeInfo['headers']
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        
        diclist = []
        for header in headers:
            headerlower = header.lower()
            attrdici = {}
            attrdici['attrname'] = header
            if headerlower in dici:
                value = dici[headerlower]
                if value is not None:
                    try:
                        valuestr = str(value)
                        if len(valuestr.strip())>0:
                            attrdici['attrvalue'] = self.__formatLinkUrl(headerlower, valuestr)
                            diclist.append(attrdici)
                    except:
                        attrdici['attrvalue'] = value
                        diclist.append(attrdici)
            
        return dici, diclist
    
    def __exportSampleSheet(self, parentList, sampleTypes, sampleTypeCount, headers, excelfile):
        uids = {}
        for listi in parentList:
            for uid in listi:
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        diclist_new = []
        for listi in parentList:
            dici_new = {}
            sampleTypeCount_now = {}        
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                else:
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    sampleTypeCount_now[sampleType] = 1
                else:
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                count = sampleTypeCount[sampleType]
                if count==1:
                    prefix = sampleType + ':'       # such as "TIS:"
                else:
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix + ':'       # such as "DNA_2:"
                
                sampleDic = uids[uid]
                if sampleDic is not None and sampleDic is not []:
                    for key, value in sampleDic.iteritems():
                        newkey = prefix + key
                        dici_new[newkey] = value        
            diclist_new.append(dici_new)
        
        headers_new = filterDiclist(headers, diclist_new)
        headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
        saveTwoDiclistsIntoExcel(excelfile, diclist_new, headers_noneConstant, 'samples', diclist_constant, headers_constant, 'constants')
        nsamples = len(diclist_new)
        return nsamples
        
    def __publishSampleList(self, user_seek, sample_ids, xlsfile, assay_id=None, project_id=None):
        isNewSheet = False
        excelfile = xlsfile
        msg, status, nsamplesOutput = self.__downloadSampleList(sample_ids, xlsfile, isNewSheet)
        
        filename = excelfile
        if "/" in filename:
            terms = filename.split('/')
            filename = terms[-1]
        modifyExcelCell(excelfile, 4, 3, filename, "Metadata")
        modifyExcelCell(excelfile, 5, 3, 'Batch sample publishing', "Metadata")
        if assay_id is not None:
            assay_url = PUBLISH_SERVER + '/assays/' + str(assay_id)
            modifyExcelCell(excelfile, 10, 3, assay_url, "Metadata")
            
        if project_id is not None:
            project_url = PUBLISH_SERVER + '/projects/' + str(project_id)
            modifyExcelCell(excelfile, 6, 3, project_url, "Metadata")
            
        return msg, status
        
    def publishSamples(self, user_seek, xlsfile, link, sample_ids, assay_id=None, project_id=None):
        msg, status = self.__publishSampleList(user_seek, sample_ids, xlsfile, assay_id, project_id)
        
        data = {}
        data['msg'] = msg
        data['status'] = status
        data['link'] = link
        data['ptype'] = 'Sample'
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    
    def __loadPublishedSampleSheet(self, excelfile):
        msg = "loadPublishedSampleSheet"
        status = 0
        sampletype = ''
        uids = []
        
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: sample excel file can't be loaded."
            status = 0
            return msg, status, sampletype, uids
        
        status = filedata['status']
        msg = filedata['msg']
        if status==0:
            return msg, status, sampletype, uids
        
        if 'SAMPLES' not in filedata['sheetnames'] or 'SAMPLES' not in filedata:
            msg = "Error: Samples sheet not in the excel."
            status = 0
            return msg, status, sampletype, uids
        
        sheetData = filedata["SAMPLES"]
        diclist = sheetData['diclist']
        sampletypes = {}
        for dici in diclist:
            uid = dici['UID']               # such as TIS-200901ENG-8
            terms = uid.split('-')
            sampletype = uid[0]             # such as TIS
            
            if sampletype in sampletypes:
                uids = sampletypes[sampletype]
            else:
                uids = []
            if uid not in uids:
                uids.append(uid)
                
            sampletypes[sampletype] = uids
        
        n = 0
        for sampletype in sampletypes:
            uids = sampletypes[sampletype]
            if n==0:
                msg = 'okay'
                status = 1
                return msg, status, sampletype, uids
            else:
                msg = "Error: More than one sample type in the excel."
                status = 0
                return msg, status, sampletype, uids
            n += 1
        
        return msg, status, sampletype, uids
        
    
    def findSamplesForExport(self, user_seek, downloadfile, link, excelfile):
        username = user_seek['username']
        
        msg, status, sampletype, uids = self.__loadPublishedSampleSheet(excelfile)
        if status==0:
            data = {}
            data['link'] = link
            data['msg'] = msg
            data['status'] = 0
            reportData = simplejson.dumps(data, default=str)
            return reportData
        
        sample_ids = []
        for uid in uids:
            sample_id = self.getSampleID(uid)
            sample_ids.append(sample_id)
            
        sdata = self.__exportSamples0(user_seek, downloadfile, link, sample_ids, sampletype)
        return sdata
        
    def getSampleType(self, user_seek, sampletype_id, attribute):
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            if status==0:
                data = {'msg':msg, 'status': status}
                reportData = simplejson.dumps(data, default=str)
                return reportData
        
        filtersdic = {}
        filtersdic['orderby'] = " ";
        filtersdic['limit'] = " ";
        filtersdic['suffix'] = " ";
        filtersdic['startNo'] = " "
        filtersdic['endNo'] = " "
        filtersdic['sqlquery_filter'] = " "
        filterRules = [{
            "field":"sample_type_id",
            "op":"equal",
            "value":sampletype_id
        }]
        filtersdic['filterRules'] = filterRules
        data = self.retrieveRecords_joint(user_seek, filtersdic)
        if attribute=='none':
            msg = 'ignore filtering'
        else:
            rows = self.__filterSamples(data['rows'], sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo) 
            data['rows'] = rows
            data['total'] = len(rows)
        data['msg'] = 'okay'
        data['status'] = 1
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def __updateSampleMeta(self, metadata_db, diclist_attributes, attri_renamed):
        metadata_out = {}
        
        for dici in diclist_attributes:
            accessor_name = dici['title']
            accessor_name = accessor_name.lower()
            
            if accessor_name in metadata_db:
                metadata_out[accessor_name] = metadata_db[accessor_name]
            elif accessor_name in attri_renamed:
                accessor_name_old = attri_renamed[accessor_name]
                if accessor_name_old in metadata_db:
                    metadata_out[accessor_name] = metadata_db[accessor_name_old]
                else:
                    metadata_out[accessor_name] = ''
            else:
                metadata_out[accessor_name] = ''
        
        return metadata_out
        
    
    def __updateSamplesMeta(self, user_seek, samples, sampletype_id, attri_renamed):
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        diclist_attributes = attributeInfo['diclist']
        username = user_seek['username']
        
        n = 0
        nright = 0
        msg = ''
        status = 1
        for record in samples:
            json_metadata = record['json_metadata']
            metadata_db = self.__getRecordFromJson(json_metadata)
            
            metadata_out = self.__updateSampleMeta(metadata_db, diclist_attributes, attri_renamed)
            
            record['json_metadata'] = simplejson.dumps(metadata_out, default=str)
            record['updated_at'] = getDefaultDateTime()

            msgi, statusi, sample_id = self.storeOneRecord(username, record)
            if statusi:
                nright += 1
            else:
                status = 0
                msg += msgi +  '<br/>'
            
            n += 1
            
        return msg, status
    
    
    def updateSampleType(self, user_seek, sampletype_id, attri_renamed):
        filtersdic = {}
        filtersdic['orderby'] = " ";
        filtersdic['limit'] = " ";
        filtersdic['suffix'] = " ";
        filtersdic['startNo'] = " "
        filtersdic['endNo'] = " "
        filtersdic['sqlquery_filter'] = " "
        filterRules = [{
            "field":"sample_type_id",
            "op":"equal",
            "value":sampletype_id
        }]
        filtersdic['filterRules'] = filterRules
        data = self.retrieveRecords_joint(user_seek, filtersdic)
        
        msg, status = self.__updateSamplesMeta(user_seek, data['rows'], sampletype_id, attri_renamed)
        data['msg'] = msg
        data['status'] = status
        data['link'] = ''
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def updateSingleSample(self, dici, username=None, attributes=None):
        msg = "updateSingleSample"
        status = 0
                
        if 'UID' not in dici and 'uid' not in dici:
            msg = 'UID not available for update'
            status = False
            return msg, status
            
        if 'UID' in dici:
            uidIn = dici['UID']
        else:
            uidIn = dici['uid']
            
        if uidIn is None or len(uidIn.strip())==0:
            msg = 'UID not available for update'
            status = False
            return msg, status
                
        record = self.__retrieveSampleByUID(uidIn)
        if record is None:
            msg = "Error: Sample UID " + uidIn + " does not exist in DB for update "
            status = False
            return msg, status
            
        json_metadata = record['json_metadata']
        dici_json = self.__getRecordFromJson(json_metadata)
        
        metadata_db = dici_json
        metadata_in = dici
        metadata_out = self.__updateSampleMetadata(metadata_db, metadata_in, attributes)
        dici_json = metadata_out
                
        json_metadata_updated = simplejson.dumps(dici_json, default=str)
        record['json_metadata'] = json_metadata_updated
        
        other_creators = record['other_creators']
        if username is not None:
            if other_creators is None:
                record['other_creators'] = username
            elif username not in other_creators:
                record['other_creators'] = other_creators + ';' + username

        record['updated_at'] = getDefaultDateTime()
        msg, status, sample_id = self.storeOneRecord(username, record)
        return msg, status
    
    
    def __getSampleTypeInfo(self, sampleType):
        stype = DBtable_sampletype()
        sampletype_id = stype.getSampleTypeID(sampleType)
        if sampletype_id<=0:
            msg = SAMPLE_ERRORCODE['201'] + sampleType + " id: " + str(sampletype_id)
            return msg, 0, {}
        
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        attributeInfo['sampleType'] = sampleType
        attributeInfo['sampletype_id'] = sampletype_id
        if len(attributeInfo['headers'])==0:
            msg = SAMPLE_ERRORCODE['202'] + sampleType
            return msg, 0, attributeInfo
        
        msg = 'Sample type info retrieved'
        status = 1
        return msg, status, attributeInfo
        
    
    def __verifySampleAttributes(self, record, headers_required):
        msg_required, meetRequired = self.__verifyRequiredFields(record, headers_required)
        if not meetRequired:
            msg = SAMPLE_ERRORCODE['502'] + msg_required
            return msg, 0, '', ''
    
        if 'Name' in record:
            samplename = str(record['Name'])
        elif 'File_PrimaryData' in record:
            samplename = str(record['File_PrimaryData'])
        elif 'File_PrimaryData_Forward' in record:
            samplename = str(record['File_PrimaryData_Forward'])
        elif 'File_PrimaryData_Reverse' in record:
            samplename = str(record['File_PrimaryData_Reverse'])
        else:
            msg = SAMPLE_ERRORCODE['302']
            return msg, 0, '', ''
            
        if samplename is None:
            cleanname = ''
        else:
            cleanname = str(samplename)
        cleanname = cleanname.strip()
        if len(cleanname)==0:
            msg = SAMPLE_ERRORCODE['303']
            return msg, 0, '', ''
            
        if SAMPLE_CONTRIBUTOR_ACCESSOR_NAME in record:
            scientist = str(record[SAMPLE_CONTRIBUTOR_ACCESSOR_NAME])
        elif SAMPLE_CONTRIBUTOR_ACCESSOR_NAME.lower() in record:
            scientist = str(record[SAMPLE_CONTRIBUTOR_ACCESSOR_NAME.lower()])
        else:
            msg = SAMPLE_ERRORCODE['304']
            return msg, 0, '', ''
        
        msg = "Pass verification on all required and mandetroy attributes"
        return msg, 1, cleanname, scientist
    
    def apiInsertSample(self, dici, sampleType, user_seek, diclist_assay):
        msg = "insertSingleSample"
        status = 0
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        if not self.__notEmptyLine(dici):
            msg = SAMPLE_ERRORCODE['501']
            return msg, 0, None
        
        msg, status, attributeInfo = self.__getSampleTypeInfo(sampleType)
        if status==0:
            return msg, status, None
        sampletype_id = attributeInfo['sampletype_id']
        headers_required = attributeInfo['headers_required']
        headers = attributeInfo['headers']
        
        record = {}
        for header in headers:
            if header in dici:
                record[header] = dici[header]
            elif header.lower() in dici:
                record[header] = dici[header.lower()]
        
        msg, status, samplename, scientist = self.__verifySampleAttributes(record, headers_required)
        if status==0:
            return msg, status, None
            
        contributor_id = user_id
        if contributor_id<=0:
            msg = SAMPLE_ERRORCODE['305'] + contributor
            return msg, status, None
               
        uidIn = None
        if 'uid' in dici:
            uidIn = dici['uid']
        elif 'UID' in dici:
            uidIn = dici['UID']
        
        msg, status = self.__verifySampleUID(samplename, contributor_id, uidIn, sampletype_id, scientist)
        if status==0:
            status = 0
            return msg, status, None
                
        if uidIn is not None and len(uidIn.strip())>0:
            isValid, msg = self.__verifyUID(uidIn, attributeInfo)
            if not isValid:
                return msg, 0, None
        
        record_new, newSample = self.__getRecord(user_seek, record, attributeInfo, contributor_id)
        uid = record_new['uuid']
        
        msg, status, sample_id = self.storeOneRecord(username, record_new)
        if status:
            if newSample:
                self.__updateSampleProject(user_seek, sample_id)
                self.__updateSampleAssetsCreators(sample_id, contributor_id)
                if len(diclist_assay)>0:
                    msgj, statusj = self.__storeSample_assay_asset(user_seek, sampleType, sample_id, diclist_assay)
                    if statusj==0:
                        msgj = SAMPLE_ERRORCODE['601'] + msgj
                        msg += ';' + msgj
                else:
                    msg = 'Info: Assay info not available for updating array-sample relationship for sample id: ' + str(sample_id)
                    
            else:
                msg = 'Info: No update on array-sample relationship for old sample id: ' + str(sample_id)
                
            msgdf, statusdf = self.__setSampleDatafileAssociation(user_seek, sampleType, dici, attributeInfo, diclist_assay)
            if not statusdf:
                msgdf = SAMPLE_ERRORCODE['602'] + msgdf
                msg += ';' + msgdf
        else:
            msg = SAMPLE_ERRORCODE['504'] + msg
        
        return msg, status, uid
    
    def apiUploadSamples(self, data, user_seek):
        if 'UID' in data or 'uid' in data:
            msg, status = self.updateSingleSample(data)
            if 'UID' in data:
                uid = data['UID']
            else:
                uid = data['uid']
            
            return msg, status, uid
        
        if 'User' not in data:
            msg = "Error: 'User' info not provided in the input json dictionary"
            return msg, 0, None
        submitter = data['User']
        user_seek['lababbv'] = submitter['lababbv']
        user_seek['projectid'] = submitter['projectid']
        if 'Sample type' not in data:
            msg = "Error: 'Sample type' info not provided in the input json dictionary"
            return msg, 0, None
        sampleType = data['Sample type']
        
        if 'Samples' not in data:
            msg = "Error: 'Samples' info not provided in the input json dictionary"
            return msg, 0, None
        samples = data['Samples']
        
        if 'Assay' in data:
            diclist_assay = data['Assay']
        else:
            diclist_assay = []
        
        msg, status, uid = self.apiInsertSample(samples, sampleType, user_seek, diclist_assay)
        if uid is None:
            uid = ''
        return msg, status, uid


    def getSampleUIDInfo(self, sample_uid):
        sinfo = {}
        sinfo['sample_uid'] = sample_uid
        if '-' not in sample_uid:
            return sinfo
        
        record = self.__retrieveSampleByUID(sample_uid)
        if record is None:
            return sinfo
        
        sinfo['record'] = record
        terms = sample_uid.split("-")
        sampletype = terms[0]   
        sinfo['sample type'] = sampletype
        
        dateabbr = terms[1]     
        if len(dateabbr)!=9:
            return sinfo
        
        lababbv = dateabbr[-3:] 
        sinfo['lababbv'] = lababbv
        
        sid = record['id']
        sqlquery = 'SELECT * FROM projects A '
        sqlquery += 'LEFT JOIN projects_samples B '
        sqlquery += 'ON A.id=B.project_id '
        sqlquery += 'where B.sample_id=' + str(sid)
        sqlquery = 'SELECT * FROM projects_samples where sample_id=' + str(sid) + ';'
        project_id = None
        for p in Projects_samples.objects.raw(sqlquery):
            project_id = p.project_id
        
        sinfo['project_id'] = project_id
        sinfo['projectname'] = None
        if project_id is not None:
            project = Projects.objects.get(pk=project_id)
            sinfo['projectname'] = project.title
        
        return sinfo
        
        
    def __downloadSampleList(self, sample_ids, xlsfile, isNewSheet=True):
        status = 1
        msg = ''
        sample_type_id = None
        sattr = DBtable_sampleattribute()
        sattrInfo = {}
        headers = None
        diclist = []
        nsamplesOutput = 0
        for sample_id in sample_ids:
            record = self.__retrieveSampleByID(sample_id)
            if record is None:
                msgi = 'Error: Sample id ' + str(sample_id) +  ' not found in DB '
                status = 0
                msg += msgi + '<br/>'
                continue
            
            if sample_type_id is None:
                sample_type_id = record['sample_type_id']
                if sample_type_id in sattrInfo:
                    attributeInfo = sattrInfo[sample_type_id]
                else:
                    attributeInfo = sattr.getAttributeInfo(sample_type_id)
                    sattrInfo[sample_type_id] = attributeInfo
                    
                headers = attributeInfo['headers']
            else:
                if sample_type_id!=record['sample_type_id']:
                    msgi = 'Error: Sample id ' + str(sample_id) +  ' is not in the sample type with other sample'
                    status = 0
                    msg += msgi + '<br/>'
                    continue
            
            json_metadata = record['json_metadata']
            dici = self.__getRecordFromJson(json_metadata)
            dici_rev = {}
            for header in headers:
                hi = header.lower().strip()
                if hi in dici:
                    dici_rev[header] = dici[hi]
                else:
                    dici_rev[header] = ''
            
            diclist.append(dici_rev)
            nsamplesOutput += 1
        
        saveExcelDiclist(xlsfile, headers, diclist, 'Samples', isNewSheet)
        return msg, status, nsamplesOutput
    
    
    def searchAdvanced(self, user_seek, filters, searchType, project_id=0):
        filtersdic = {}
        filtersdic['orderby'] = " "
        filtersdic['limit'] = " "
        filtersdic['suffix'] = " "
        filtersdic['startNo'] = " "
        filtersdic['endNo'] = " "
        filtersdic['sqlquery_filter'] = " "
        filtersdic['project_id'] = project_id
        filterRules = []
        if searchType == "UIDs":
            filter_searchText = filters['filter_searchUIDs']
        elif searchType=="Advanced":
            sampletype_id = filters['sampletype_id']
            attribute = filters['attribute']
            filter_logic = filters['filter_logic']
            filter_searchValue = filters['filter_searchValue']
            filter_searchText = filters['filter_searchText']
            filter_matchType = filters['filter_matchType']
            filterRules = [{
                "field":"sample_type_id",
                "op":"equal",
                "value":sampletype_id
            }]
            filtersdic['sampletype_id'] = sampletype_id
            filtersdic['attribute'] = attribute
            filtersdic['matchType'] = filter_matchType 
        else:
            filter_searchText = None
            
        filtersdic['filterRules'] = filterRules
        filtersdic['searchText'] = filter_searchText
        filtersdic['searchType'] = searchType
        
        attribute = 'none'
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            if status==0:
                data = {'msg':msg, 'status': status}
                reportData = simplejson.dumps(data, default=str)
                return reportData
        
        data = self.retrieveRecords_advanced(user_seek, filtersdic)
        
        if searchType == "UIDs":
            msg = 'ignore filtering'
            data['tree'] = self.__getAttributeTree(data['rows'])
        else:
            rows = self.__filterSamples_advanced(data['rows'], filtersdic) 
            data['rows'] = rows
            data['total'] = len(rows)
            
            sampleTypes = []
            for row in rows:
                sampleType = row['sample_type']
                if sampleType not in sampleTypes:
                    sampleTypes.append(sampleType)
            data['sampleTypes'] = sampleTypes
            data['noSampleTypes'] = len(sampleTypes)
            
        data['msg'] = 'okay'
        data['status'] = 1
        
        reportData = simplejson.dumps(data, default=str)
        return reportData
    
    def retrieveRecords_advanced(self, user_seek, filtersdic):
        sqlquery = self.__sqlQuery_select_records_advanced(filtersdic)
        headers = SAMPLE_HEADERS
        db_alias = settings.SEEK_DATABASE
        jdata = self.db.queryToListDics(sqlquery, headers, db_alias)
        total = len(jdata)
        if total is None:
            total = 0
        else:
            total = int(total)
    
        jdata_new = self.reformatDataForClient(jdata)
        footer = []
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data
        
        
    def __sqlQuery_select_records_advanced(self, filtersdic, withLimit=True): 
        sqlquery_select = self.__sqlQuery_select_records_select()
        
        project_id = filtersdic['project_id']
        sqlquery_from = self.__sqlQuery_select_records_from(project_id)
        orderby = filtersdic['orderby'] 
        startNo = filtersdic['startNo'] 
        endNo = filtersdic['endNo']   
        sqlquery_where = self.__sqlQuery_select_records_filters_advanced(filtersdic)
        sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where
        if len(orderby)==0:
            orderby = " ORDER BY A.id desc"
        
        if withLimit:
            sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where + orderby
        else:
            sqlqueryMega = " SELECT count(A.id) " + sqlquery_from
        
        return sqlqueryMega
    
    
    def __getSearchTerms(self, searchText):
        terms = []
        if searchText is None:
            return terms
        
        # split accoring to new line
        if '\n' in searchText:
            lines = searchText.split('\n')
        elif '\n\r' in searchText:
            lines = searchText.split('\n\r')
        else:
            lines = [searchText]
            
        for line in lines:
            line = line.strip()
            for delimiter in (',', ';', ' ', '\t'):
                if delimiter in line:
                    termi = line.split(delimiter)
                    for term in termi:
                        term = term.strip()
                        if len(term)>0 and term not in terms:
                            terms.append(term)
            
            if len(line)>0 and line not in terms:
                terms.append(line)
                
        if len(terms)==0:
            terms.append(searchText.strip())
        return terms
        
    def __sqlQuery_select_records_filters_uids(self, uids):
        if len(uids)>0:
            tarray = "('" + "','".join(uids) + "')"
            tablefield = 'uid'
            field = SAMPLE_FILTER_MAPPING[tablefield]
            sqlquery_filter = " WHERE " + field + " in " + tarray + ";"
        else:
            sqlquery_filter = " "
        
        return sqlquery_filter
    
    def __sqlQuery_select_records_filters_keywords(self, terms):
        query = {}
        multi_match = True
        for term in terms:
            if '&' in term:
                multi_match = False
                
        if multi_match:
            query["multi_match"] = terms  
        
        if len(terms)==1:
            term = terms[0]
            if '&' in term:
                termi = term.split('&')
                query["match_all"] = termi
        
        tablefield = "json_metadata"
        field = SAMPLE_FILTER_MAPPING[tablefield]
        if "match_all" in query:
            keywords = query["match_all"]
            sqlquery_filter = ""
            n = 0
            for keyword in keywords:
                if ":" in keyword:
                    keyword = self.__getCleanKeyword(keyword)
                
                if n==0:
                    sqlquery_filter += " WHERE " + field
                else:
                    sqlquery_filter += " AND " + field
                sqlquery_filter += " LIKE '%" + str(keyword) + "%' "
                n += 1
        elif "multi_match" in query:
            keywords = query["multi_match"]
            sqlquery_filter = ""
            n = 0
            for keyword in keywords:
                if ":" in keyword:
                    keyword = self.__getCleanKeyword(keyword)
                
                if n==0:
                    sqlquery_filter += " WHERE " + field
                else:
                    sqlquery_filter += " OR " + field
                sqlquery_filter += " LIKE '%" + str(keyword) + "%' "
                n += 1
        else:
            sqlquery_filter = ""
            n = 0
            for term in terms:
                if n==0:
                    if '&' not in term:
                        keyword = term
                        sqlquery_filter += " WHERE " + field
                        if ":" in keyword:
                                keyword = self.__getCleanKeyword(keyword)
                                
                        sqlquery_filter += " LIKE '%" + str(keyword) + "%' "
                    else:
                        keywords = term.split('&')
                        i = 0
                        for keyword in keywords:
                            if ":" in keyword:
                                keyword = self.__getCleanKeyword(keyword)
                            
                            if i==0:   
                                sqlquery_filter += " WHERE (" + field
                            else:
                                sqlquery_filter += " AND " + field
                            sqlquery_filter += " LIKE '%" + str(keyword) + "%' "
                            i += 1
                        sqlquery_filter += " )" 
                else:
                    if '&' not in term:
                        keyword = term
                        if ":" in keyword:
                            keyword = self.__getCleanKeyword(keyword)
                            
                        sqlquery_filter += " OR " + field
                        sqlquery_filter += " LIKE '%" + str(term) + "%' "
                    else:
                        keywords = term.split('&')
                        i = 0
                        for keyword in keywords:
                            if ":" in keyword:
                                keyword = self.__getCleanKeyword(keyword)
                            
                            if i==0:   
                                sqlquery_filter += " OR (" + field
                            else:
                                sqlquery_filter += " AND " + field
                            sqlquery_filter += " LIKE '%" + str(keyword) + "%' "
                            i += 1
                        sqlquery_filter += " )" 
                n += 1
                
        return sqlquery_filter 
    
    def __sqlQuery_select_records_filters_advanced(self, filtersdic):
        if 'searchText' in filtersdic: 
            searchText = filtersdic['searchText']
            searchType = filtersdic['searchType']
            
            terms = self.__getSearchTerms(searchText)
            if searchType=="UIDs":
                sqlquery_filter = self.__sqlQuery_select_records_filters_uids(terms)
            elif searchType=="Advanced":
                sqlquery_filter, keywords = self.__getSearchTermsPubmed(searchText)
            else:
                sqlquery_filter = self.__sqlQuery_select_records_filters_keywords(terms)
        
            project_id = filtersdic['project_id']
            if project_id>0:
                sqlquery_filter = sqlquery_filter + " AND D.project_id=" + str(project_id)
        
            return sqlquery_filter
        
        
        filterRules = filtersdic['filterRules'] 
        sqlquery_filter = ""
        n = 0
        for rule in filterRules:
            tablefield = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if tablefield in SAMPLE_FILTER_MAPPING:
                field = SAMPLE_FILTER_MAPPING[tablefield]
            
                if n==0:
                    sqlquery_filter += " WHERE " + field
                else:
                    sqlquery_filter += " AND " + field
                if op=="contains":
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
                elif op=="equal":
                    sqlquery_filter += "='" + str(value) + "' "
                else:
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
            n += 1
        
        return sqlquery_filter
    
    def __highlightKeyword(self, keyword, value, style=None):
        defaultStyle = "color:red;"
        if style is None:
            style = defaultStyle
        
        if keyword in value:
            newKeyword = '<span style="' + style + '">' + keyword + '</span>'
            value = value.replace(keyword, newKeyword)
        else:
            kl = keyword.lower()
            vl = value.lower()
            if kl in vl:
                pos = vl.find(kl)
                keyw = value[pos:(pos+len(keyword))]
                newKeyword = '<span style="' + style + '">' + keyw + '</span>'
                value = value.replace(keyw, newKeyword)
        return value
    
    def __filterSamples_advanced(self, jdata, filtersdic):
        filterRules = filtersdic['filterRules']
        sampletype_id = filtersdic['sampletype_id']
        attribute = filtersdic['attribute']
        matchType = filtersdic['matchType']
        searchType = filtersdic['searchType']
        
        filter_rule = None
        filter_valueFrom = None
        filter_valueTo = None
        
        searchText = filtersdic['searchText']
        query, terms = self.__getSearchTermsPubmed(searchText)
        
        sampletype_id = 0
        
        n = 0
        separator = ',   '
        jdata_new = []
        for data in jdata:
            json_metadata = data['json_metadata']
            sample_type_id = data['sample_type_id']
            dici = self.__getRecordFromJson(json_metadata)
            
            attributeValue = ''
            ki = 0
            for key, value in sorted(dici.items()):
                if value is None:
                    continue
                try:
                    value = str(value)
                except:
                    continue
                
                key = self.__highlightKeyword(key, key, "color:blue;font-weight:bold;")
                
                valuel = value.lower()
                for term in terms:
                    if matchType=='EXACT':
                        if term==value or term.upper()==value.upper():
                            if ki==0:
                                attributeValue += key + ':' + self.__highlightKeyword(term, value)
                            else:
                                attributeValue += separator + key + ':' + self.__highlightKeyword(term, value)
                            ki += 1
                        continue    
                    
                    if term in value or term.lower() in valuel:     
                        if ki==0:
                            attributeValue += key + ':' + self.__highlightKeyword(term, value)
                        else:
                            attributeValue += separator + key + ':' + self.__highlightKeyword(term, value)
                        ki += 1
                    elif "&" in term:
                        termi = term.split("&")
                        for ti in termi:
                            if ':' in ti:
                                ti = self.__getCleanKeyword(ti)
                            
                            if ti in value or ti.lower() in valuel:
                                if ki==0:
                                    attributeValue += key + ':' + self.__highlightKeyword(ti, value)
                                else:
                                    attributeValue += separator + key + ':' + self.__highlightKeyword(ti, value)
                                ki += 1
                    elif "^" in term:
                        termi = term.split("^")
                        for ti in termi:
                            if ':' in ti:
                                ti = self.__getCleanKeyword(ti)

                            if ti in value or ti.lower() in valuel:
                                if ki==0:
                                    attributeValue += key + ':' + self.__highlightKeyword(ti, value)
                                else:
                                    attributeValue += separator + key + ':' + self.__highlightKeyword(ti, value)
                                ki += 1            
                    elif ':' in term:
                        term = self.__getCleanKeyword(term)
                        if term in value or term.lower() in valuel:     
                            if ki==0:
                                attributeValue += key + ':' + str(value)
                            else:
                                attributeValue += separator + key + ':' + self.__highlightKeyword(term, value)
                            ki += 1
    
            if len(attributeValue)==0:
                continue
    
            data['attributeValue'] = attributeValue
            if sampletype_id>0:
                if sampletype_id==sample_type_id:
                    jdata_new.append(data)
                    n += 1
            else:
                jdata_new.append(data)
                n += 1

        return jdata_new
    
    def __getCleanKeyword(self, keywordIn):
        keywordOut = keywordIn
        if ':' in keywordIn:
            tii = keywordIn.split(':')
            if len(tii)==3:
                keywordOut = tii[2]
            else:
                keywordOut = tii[-1]
        
        return keywordOut
    
    def __findMatchedParentheses(self, s, leftPT='(', rightPT=')'):
        ''' Refer to: https://stackoverflow.com/questions/29991917/indices-of-matching-parentheses-in-python
        
        Examples:
            S = '((((dfdfd) OR (feefe)) AND (eeewewe)) NOT (eefefe)) NOT (hhghjhh[Author])'
            find_parens(S) = {3: 9, 14: 20, 2: 21, 27: 35, 1: 36, 42: 49, 0: 50, 56: 72}
            
            s = 'ssasas'
            find_parens(s) = {}

            s = '(ssasas'
            ab = find_parens(s)
                Traceback (most recent call last):
                  File "<stdin>", line 1, in <module>
                  File "<stdin>", line 12, in find_parens
                IndexError: No matching opening parens at: 0
        '''
        toret = {}
        pstack = []

        for i, c in enumerate(s):
            if c==leftPT:
                pstack.append(i)
            elif c==rightPT:
                if len(pstack) == 0:
                    raise IndexError("No matching closing parens at: " + str(i))
                toret[pstack.pop()] = i

        if len(pstack) > 0:
            raise IndexError("No matching opening parens at: " + str(pstack.pop()))

        return toret
    
    
    def __parseKeyword(self, keyword):
        sampleType = None
        if '[' not in keyword or ']' not in keyword:
            return keyword, sampleType
            
        try:
            pts = self.__findMatchedParentheses(keyword, '[', ']')
        except:
            logger.debug("Warning: Search text has mismatched parentheses [ or ] in : " + keyword) 
            return keyword, sampleType
            
        if pts is None or not pts:
            return keyword, sampleType
        
        sids = []
        kws = []
        for i, j in pts.items():
            term = keyword[(i+1):j] 
            termi = keyword[i:(j+1)]   
            sids.append(term)
            kw = keyword[0:i]       
            kws.append(kw)
            
        if len(sids)!=1:
            logger.debug("Warning: Search text not in the right format for sample_type_id: " + keyword) 
            return keyword, sampleType
        
        keyword = kws[0].strip()
        sampleType = sids[0].strip()
        sampleType = sampleType.upper()
        return keyword, sampleType
            
        
    
    def __designConstraint(self, field, keyword, isNOT=False):
        if isNOT:
            constraint = field + " NOT LIKE '%" + str(keyword) + "%' "
        else:
            constraint = field + " LIKE '%" + str(keyword) + "%' "
            
        keyword, sampleType = self.__parseKeyword(keyword)
        if sampleType is None:
            return constraint
            
        stype = DBtable_sampletype()
        sample_type_id = stype.getSampleTypeID(sampleType)
        try:
            sample_type_id = int(sample_type_id)
        except:
            logger.debug("Warning: Search text not in the right format for sample_type_id: " + keyword) 
            return constraint
        
        if isNOT:
            constraint = "(" + field + " NOT LIKE '%" + str(keyword) + "%' AND sample_type_id=" + str(sample_type_id) + ")"
        else:
            constraint = "(" + field + " LIKE '%" + str(keyword) + "%' AND sample_type_id=" + str(sample_type_id) + ")"            
            
        return constraint
        
    def __designDualConstraint(self, field, expression, operator, termsdic):
        query = ''
        if operator not in expression:
            return None
        
        terms = expression.split(operator)
        if len(terms)!=2:
            msg = "More than two" + operator + "operations found in: " + expression
            logger.debug(msg)
            return None
                    
        keyword1 = terms[0].strip()
        keyword2 = terms[1].strip()
        
        isNOT = False
        operator2 = operator
        if operator==' NOT ':
            isNOT = True
            operator2 = ' AND '
            
        if keyword1 not in termsdic:
            constraint1 = self.__designConstraint(field, keyword1)
            query += constraint1
            if keyword2 not in termsdic:
                constraint2 = self.__designConstraint(field, keyword2, isNOT)
                query += operator2 + constraint2
            else:
                nextExpression = termsdic[keyword2]
                subQuery = self.__designIterativeQuery(nextExpression, field, termsdic)
                if subQuery is not None:
                    query += operator2 + " (" + subQuery + ") "
                
        else:
            nextExpression = termsdic[keyword1]
            subQuery1 = self.__designIterativeQuery(nextExpression, field, termsdic)
                
            if keyword2 not in termsdic:
                constraint2 = self.__designConstraint(field, keyword2, isNOT)
                if subQuery1 is not None:
                    query += " (" + subQuery1 + ") " + operator2
                query += constraint2
                
            else:
                nextExpression = termsdic[keyword2]
                subQuery2 = self.__designIterativeQuery(nextExpression, field, termsdic)
                if subQuery1 is not None:
                    if subQuery2 is not None:
                        query += " (" + subQuery1 + ") " + operator2 + " (" + subQuery2 + ") "
                    else:
                        query += " (" + subQuery1 + ") "
                else:
                    if subQuery2 is not None:
                        query += " (" + subQuery2 + ") "
                    
        return query
        
    def __validateExpression(self, expression):
        isValid = True
        operatorFound = None
        noOperators = 0
        
        expression = expression.upper().strip()
        for operator in [' NOT ', ' AND ', ' OR ']:
            if operator in expression:
                terms = expression.split(operator)
                if len(terms)!=2:
                    isValid = False
                else:
                    operatorFound = operator
                    noOperators += 1
                
        if noOperators>1:
            isValid = False
            
        return isValid, operatorFound   
        
        
    def __designIterativeQuery(self, expression, field, termsdic):
        isValid, operatorFound = self.__validateExpression(expression)
        if not isValid:
            msg = 'Search expression not in the valid format: ' + expression
            logger.debug(msg)
            return None
            
        if operatorFound is None:
            constraint = self.__designConstraint(field, expression)
            query = constraint
        else:
            query = self.__designDualConstraint(field, expression, operatorFound, termsdic)     
            
        return query
    
    def __getDualKeywords(self, expression, operator, termsdic):
        keywords = []
        if operator not in expression:
            return keywords
        
        terms = expression.split(operator)
        if len(terms)!=2:
            msg = "More than two" + operator + "operations found in: " + expression
            logger.debug(msg)
            return keywords
                    
        keyword1 = terms[0].strip()
        keyword2 = terms[1].strip()
        
        if keyword1 not in termsdic:
            keywords.append(keyword1)
            if keyword2 not in termsdic:
                keywords.append(keyword2)
            else:
                nextExpression = termsdic[keyword2]
                keywords += self.__getKeywords(nextExpression, termsdic)
        else:
            nextExpression = termsdic[keyword1]
            keywords += self.__getKeywords(nextExpression, termsdic)
            if keyword2 not in termsdic:
                keywords.append(keyword2)
            else:
                nextExpression = termsdic[keyword2]
                keywords += self.__getKeywords(nextExpression, termsdic)
                    
        return keywords
    
    
    def __getKeywords(self, expression, termsdic):
        keywords = []
        isValid, operatorFound = self.__validateExpression(expression)
        if operatorFound is None:
            keywords.append(expression)
        else: 
            keywords += self.__getDualKeywords(expression, operatorFound, termsdic)  
        
        keywords_new = []
        for keyword in keywords:
            keyword, sampleType = self.__parseKeyword(keyword)
            keywords_new.append(keyword)
            
        return keywords_new
    
    def __getSearchTermsPubmed(self, searchText):
        query = ''
        if searchText is None:
            return query
        try:
            pts = self.__findMatchedParentheses(searchText)
        except:
            logger.debug("Warning: Search text has mismatched parentheses in : " + searchText) 
            return query
        
        searching = True
        ni = 0
        sss = searchText
        iterations = []
        termsdic = {}
        keywords = []
        while(searching):
            if pts is None or not pts:
                si = {}
                si['sss'] = sss
                si['pts'] = pts
                iterations.append(si)    
                searching = False
                
            for i, j in pts.items():
                term = sss[(i+1):j]
                termi = sss[i:(j+1)]
                if '(' not in term and ')' not in term:
                    termRep = 'term_' + str(i) + '_' + str(j+1)
                    if termRep not in termsdic:
                        termsdic[termRep] = term   
                    sss = sss.replace(termi, termRep)
            
            si = {}
            si['sss'] = sss
            si['pts'] = pts
            iterations.append(si)
            pts = self.__findMatchedParentheses(sss)
        
        query = ""
        field = 'json_metadata'
        
        si = iterations[-1]
        expression = si['sss']     
        query = self.__designIterativeQuery(expression, field, termsdic)
        if query is None:
            query = field + " LIKE '%" + str(expression) + "%' "
        
        query = 'WHERE ' + query
        logger.debug("keyword query filter: " + query)
        
        keywords = self.__getKeywords(expression, termsdic)
        return query, keywords
        
 
    def __createSampleTreeFromDB(self, sample_ids):
        from .models import Sample_tree
        
        includeChilren = True
        parentList = []
        for sample_id in sample_ids:
            id = int(sample_id)
            objs = Sample_tree.objects.filter(sample_id=id)
            total = objs.count()
            if total==1:
                obj = objs[0]
                fullTree = obj.full
                atree = json.loads(fullTree)
                fullTreeList = atree
                upTreeList = fullTreeList
            else:
                upTreeList = self.__createMultiParentTree(sample_id, includeChilren)

            parentList_i = self.__getChildrenListLoop(upTreeList)
            parentList += parentList_i
        
        sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(parentList)       
        headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)       
        return headers_new, diclist_new, headersMapping
    
    def __getAttributeTree(self, jdata):
        sample_ids = []
        for data in jdata:
            id = data['id']
            sample_ids.append(id)

        includeSampleTree = 1
        if includeSampleTree==1:
            headers_new, diclist_new, headersMapping = self.__createSampleTreeFromDB(sample_ids)
            headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
            
            headers_inConstant = []
            for dici in diclist_constant:
                header = dici[headers_constant[0]]
                headers_inConstant.append(header)
                
            headers_filter = []
            for header in headers_new:
                if header in headers_noneConstant or header in headers_inConstant:
                    headers_filter.append(header)
                
            stypes = []
            for header in headers_filter:
                if ':' not in header:
                    continue
                
                terms = header.split(':')
                stype = terms[0]
                if stype not in stypes:
                    stypes.append(stype)
            
            treeChildren = {}
            for header in headers_filter:
                if ':' not in header:
                    continue
                
                terms = header.split(':')
                stype = terms[0]
                if stype in treeChildren:
                    children = treeChildren[stype]
                else:
                    children = []
                
                attribute = terms[1]
                child = {}
                child['id'] = header
                if header in headers_noneConstant:
                    #child["text"] = attribute
                    child["text"] = '<span style="color:red;">' + attribute + '</span>'
                else:
                    #child["text"] = '<span style="color:red;">' + attribute + '</span>'
                    child["text"] = attribute
                child['checked'] = 'true'
                children.append(child)
                treeChildren[stype] = children
            
            tree = []    
            for stype in stypes:
                node = {}
                node['id'] = stype
                node['text'] = stype
                node['state'] = 'closed'
                node['checked'] = 'true'
                node['children'] = treeChildren[stype]
                tree.append(node)
            
            return tree
        else:
            return None

    def getSampleTrees(self, sample_id, childrenTreeIn=None):
        sampleTree = {}
        
        if childrenTreeIn is None:
            childrenTree = self.createSampleChildrenTree(sample_id)
        else:
            childrenTree = childrenTreeIn
        sampleTree['children'] = childrenTree
        
        includeChilren = True
        fullTreeList = self.__createMultiParentTree(sample_id, includeChilren, childrenTree)
        sampleTree['full'] = fullTreeList
        sampleTree['parents'] = ''
        return sampleTree
        
        
       
    def updateChildrenTreeDic(self, childrenTrees, uid, childrenTree):
        if uid in childrenTrees:
            return childrenTrees
    
        childrenTrees[uid] = childrenTree
        if 'children' not in childrenTree:
            return childrenTrees
    
        children = childrenTree['children']
        for child in children:
            child_uid = child['id']
            if child_uid in childrenTrees:
                continue
            else:
                childrenTrees = self.updateChildrenTreeDic(childrenTrees, child_uid, child)
    
        return childrenTrees
        
    def parseSampleIDs(self, sample_ids):
        sampleDiclist = self.retrieveRecordsByIDs(sample_ids)
        sampleTypes = {}
        for dici in sampleDiclist:
            id = dici['id']
            uid = dici['uuid']
            terms = uid.split('-')
            sampleType = terms[0]
            if sampleType in sampleTypes:
                slist = sampleTypes[sampleType]
            else:
                slist = []
            slist.append(id)
            sampleTypes[sampleType] = slist
            
        return sampleTypes
        
        
        
        
        
        
        