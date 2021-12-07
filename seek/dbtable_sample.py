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
import xlwt
logger = logging.getLogger(__name__)

import zipfile


from django.conf import settings
from django.db.models import Q

from .models import Samples, Projects_samples, People, Assets_creators
from dmac.dbtable import DBtable
from dmac.csv_excel import load_file, load_excelfile, load_excelfile_asdic, saveExcelDiclist, modifyExcelCell, reviseExcelDiclist
from dmac.conversion import getDefaultDate, toString, cleanString, getDefaultDate, getDefaultDateTime, convertDateListToString, toInt
from dmac.iocsv import saveDiclistIntoExcel, filterDiclist, saveTwoDiclistsIntoExcel, getConstantRows, removeDiclistDuplicates

from dbtable_sampleattribute import DBtable_sampleattribute
from dbtable_sampletype import DBtable_sampletype
from dbtable_assay_assets import DBtable_assay_assets

from dbtable_data_files import DBtable_data_files
from dbtable_sops import DBtable_sops
from dbtable_policies import DBtable_policies

from dbtable_ontology import DBtable_ontology

SEEK_DATABASE = settings.SEEK_DATABASE

# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
# this is usually at "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY  = settings.PROJECT_ROOT + "/static/media/download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + 'download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY
# this is the symbolic link to "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY_LINK = '/static/media/download/'

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval,
# the SAMPLE_FILTER_MAPPING.keys() is the list of headers retrieved from DB
# 
# for example, self.__sqlQuery_select_records_select()
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
# SAMPLE_HEADERS = SAMPLE_FILTER_MAPPING.keys()
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

# Default values for Sample table
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
    'originating_data_file_id':None,   # use DB default null
    'deleted_contributor':None         # use DB default null
}

# Predefiinied sheet names on the meta-sample sheet
SAMPLE_SHEET_NAMES = ["INSTRUCTIONS", "SAMPLES", "ASSAY", "ONTOLOGY"]

# predefined attribute type id=5 for weblik
ATTRIBUTETYPE_ID_WEBLINK = 5
# predefined attribute type id=19 for URI
ATTRIBUTETYPE_ID_URI = 19

# If an attribute contains the following identifier,
# it value is regarded as the UID for its parent sample
# it also refer to "CreatedFromSample1", "CreatedFromSample2" etc.
# in future,we should change it to attribute_type="SEEK_Sample"
SAMPLE_PARENT_ATTRIBUTOR = "CreatedFromSample"

#SAMPLE_PARENT_ACCESSOR_NAME = "createdfromsample"
SAMPLE_PARENT_ACCESSOR_NAME = "parent"
#SAMPLE_PROTOCOL_ACCESSOR_NAME = "protocol."
#SAMPLE_FILE_ACCESSOR_NAME = "file."
SAMPLE_PROTOCOL_ACCESSOR_NAME = "protocol"
SAMPLE_FILE_ACCESSOR_NAME = "file_"         # such as 'file_qc', where the suffix 'qc' matches the suffix in 'link_qc'.
SAMPLE_LINK_ACCESSOR_NAME = "link_"         # such as 'link_qc'
SAMPLE_CONTRIBUTOR_ACCESSOR_NAME = "Scientist" # each sample type must have the attribute "Scientist", which is used as the contributor of the sample.
#LAB_ABBREV

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
    '102': 'Error: Assay sheet does not contained required sheet - ',
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
    '602': 'Warning: Data file not associated with a sample in the SEEK database - '
}

DELIMITER_DBFIELD = "::"

# the excel file used as the template for publishing samples to FairDomHub
#SAMPLE_TEMPLATE_FILE = "SAMPLE_TEMPLATE.xlsx"
SAMPLE_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/SAMPLE_TEMPLATE.xlsx"


#The expected Immport template excel file will be:
#   IMMPORT_TEMPLATE_FILE_PREFIX + sampletype + ".xlsx" 
#For example, for sample type "D.MSP", the Immport template file is: "IMMPORT_TEMPLATE-D.MSP.xlsx"
IMMPORT_TEMPLATE_FILE_PREFIX = settings.MEDIA_ROOT + "/reserved/IMMPORT_TEMPLATE-"
IMMPORT_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/IMMPORT_TEMPLATE-MAPPING.xlsx"
# A list of Immport template names: IMMPORT_TEMPLATES[txtfilename]=sheetname
IMMPORT_TEMPLATES = {'protocols':'protocols',
    'subjectanimals':'subjectanimals',
    'biosamples':'biosamples',
    'experiments':'experiments',
    'experimentsamples':'mass_spec_proteomics'   
}
IMMPORT_TEMPLATES_VERSION = 'Schema Version 3.32'

# such as: "https://fairdomhub.org"
PUBLISH_SERVER = settings.PUBLISH_URL

# If an attribute value equals to "-null", such attribute in the database will be removed from a sample's meta data. 
RESERVED_REMOVE_VALUE_FOR_UPDATE = "-null"

# If an attribute value equals to "-none", such attribute in the database will be added with default None value from a sample's meta data. 
RESERVED_DEFAULT_VALUE_FOR_UPDATE = "-none"


def hierarchyExample():
    ''' Here is a list of data used in the hierarchu tree example at 
        http://blog.pixelingene.com/2011/07/building-a-tree-diagram-in-d3-js/ 
        This example is shown in data/templates/pages/wga_cell_status.embed.html
    '''
    treeData = {
        'name': "/",
        'children': [
            {
                'name': "Applications",
                'children': [
                    { 'name': "Mail.app" },
                    { 'name': "iPhoto.app" },
                    { 'name': "Keynote.app" },
                    { 'name': "iTunes.app" },
                    { 'name': "XCode.app" },
                    { 'name': "Numbers.app" },
                    { 'name': "Pages.app" }
                ]
            },
            {
                'name': "System",
                'children': []
            },
            {
                'name': "Library",
                'children': [
                    {
                        'name': "Application Support",
                        'children': [
                            { 'name': "Adobe" },
                            { 'name': "Apple" },
                            { 'name': "Google" },
                            { 'name': "Microsoft" }
                        ]
                    },
                    {
                        'name': "Languages",
                        'children': [
                            { 'name': "Ruby" },
                            { 'name': "Python" },
                            { 'name': "Javascript" },
                            { 'name': "C#" }
                        ]
                    },
                    {
                        'name': "Developer",
                        'children': [
                            { 'name': "4.2" },
                            { 'name': "4.3" },
                            { 'name': "5.0" },
                            { 'name': "Documentation" }
                        ]
                    }
                ]
            },
            {
                'name': "opt",
                'children': []
            },
            {
                'name': "Users",
                'children': [
                    { 'name': "pavanpodila" },
                    { 'name': "admin" },
                    { 'name': "test-user" }
                ]
            }
        ]
    };
    
    treeData = {
        'name': 'A.MSP-20200225-27',
        'children': [
            {
                'name': 'D.MSP-20200225-26',
                'children': [
                    {
                        'name': 'LYS-20200225-14',
                        'children': [
                            {'name': 'CEL-20200225-2'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-15',
                        'children': [
                            {'name': 'CEL-20200225-3'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-16',
                        'children': [
                            {'name': 'CEL-20200225-4'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-18',
                        'children': [
                            {'name': 'CEL-20200225-6'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-19',
                        'children': [
                            {'name': 'CEL-20200225-7'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-20',
                        'children': [
                            {'name': 'CEL-20200225-8'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-22',
                        'children': [
                            {'name': 'CEL-20200225-10'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-23',
                        'children': [
                            {'name': 'CEL-20200225-11'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-24',
                        'children': [
                            {'name': 'CEL-20200225-12'}
                        ]
                    }
                ]
            }
        ]
    };

    treeData = {
        'name': 'A.MSP-20200225-27',
        'parents': [
            {
                'name': 'D.MSP-20200225-26',
                'parents': [
                    {
                        'name': 'LYS-20200225-14',
                        'parents': [
                            {'name': 'CEL-20200225-2'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-15',
                        'parents': [
                            {'name': 'CEL-20200225-3'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-16',
                        'parents': [
                            {'name': 'CEL-20200225-4'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-18',
                        'parents': [
                            {'name': 'CEL-20200225-6'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-19',
                        'parents': [
                            {'name': 'CEL-20200225-7'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-20',
                        'parents': [
                            {'name': 'CEL-20200225-8'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-22',
                        'parents': [
                            {'name': 'CEL-20200225-10'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-23',
                        'parents': [
                            {'name': 'CEL-20200225-11'}
                        ]
                    }, 
                    {
                        'name': 'LYS-20200225-24',
                        'parents': [
                            {'name': 'CEL-20200225-12'}
                        ]
                    }
                ]
            }
        ]
    };

    
    treeData2 = {
        'name': "MUS-20191106-335",
        'children': [
            {
                'name': "TIS-20191106-336",
                'children': [
                    { 'name': "IMG-20191106-349" }
                ]
            },
            {
                'name': "TIS-20191106-337",
                'children': []
            },
            {
                'name': "TIS-20191106-338",
                'children': [
                    {
                        'name': "IMG-20191106-350",
                        'children': [
                            { 'name': "19.05.21_19-194_LL.tif" },
                            { 'name': "19.05.21_19-194_RL.tif" }
                        ]
                    },
                    {
                        'name': "P.NDMA-Ing.Beng.001",
                        'children': [
                            { 'name': "19.05.21_19-195_LL.tif" },
                            { 'name': "19.05.21_19-195_RL.tif" },
                            { 'name': "19.05.21_19-196_LL.tif" },
                            { 'name': "19.05.21_19-196_RL.tif" }
                        ]
                    },
                    {
                        'name': "P.NDMA-Ing.Beng.001",
                        'children': [
                            {
                                'name': "P.T-Iso.Beng.001",
                                'children': [
                                    { 'name': "19.05.21_19-197_LL.tif" },
                                    { 'name': "19.05.21_19-197_RL.tif" }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    };
    return treeData    

def hierarchyExample2():
    ''' Here is a list of data used in the hierarchu tree example at 
        http://blog.pixelingene.com/2011/07/building-a-tree-diagram-in-d3-js/ 
        This example is shown in data/templates/pages/wga_cell_status.embed.html
    '''
    treeData = {
        'name': "/",
        'children': [
            {
                'name': "Applications",
                'children': [
                    { 'name': "Mail.app" },
                    { 'name': "iPhoto.app" },
                    { 'name': "Keynote.app" },
                    { 'name': "iTunes.app" },
                    { 'name': "XCode.app" },
                    { 'name': "Numbers.app" },
                    { 'name': "Pages.app" }
                ]
            },
            {
                'name': "System",
                'children': []
            },
            {
                'name': "Library",
                'children': [
                    {
                        'name': "Application Support",
                        'children': [
                            { 'name': "Adobe" },
                            { 'name': "Apple" },
                            { 'name': "Google" },
                            { 'name': "Microsoft" }
                        ]
                    },
                    {
                        'name': "Languages",
                        'children': [
                            { 'name': "Ruby" },
                            { 'name': "Python" },
                            { 'name': "Javascript" },
                            { 'name': "C#" }
                        ]
                    },
                    {
                        'name': "Developer",
                        'children': [
                            { 'name': "4.2" },
                            { 'name': "4.3" },
                            { 'name': "5.0" },
                            { 'name': "Documentation" }
                        ]
                    }
                ]
            },
            {
                'name': "opt",
                'children': []
            },
            {
                'name': "Users",
                'children': [
                    { 'name': "pavanpodila" },
                    { 'name': "admin" },
                    { 'name': "test-user" }
                ]
            }
        ]
    };
    
    treeData = {
        'name': "/",
        'children': [
            {
                'name': "Applications",
                'children': [
                    { 'name': "Mail.app" },
                    { 'name': "iPhoto.app" },
                    { 'name': "Keynote.app" },
                    { 'name': "iTunes.app" },
                    { 'name': "XCode.app" },
                    { 'name': "Numbers.app" },
                    { 'name': "Pages.app" }
                ]
            },
            {
                'name': "System",
                'children': []
            },
            {
                'name': "Library",
                'children': [
                    {
                        'name': "Application Support",
                        'children': [
                            { 'name': "Adobe" },
                            { 'name': "Apple" },
                            { 'name': "Google" },
                            { 'name': "Microsoft" }
                        ]
                    },
                    {
                        'name': "Languages",
                        'children': [
                            { 'name': "Ruby" },
                            { 'name': "Python" },
                            { 'name': "Javascript" },
                            { 'name': "C#" }
                        ]
                    },
                    {
                        'name': "Developer",
                        'children': [
                            { 'name': "4.2" },
                            { 'name': "4.3" },
                            { 'name': "5.0" },
                            { 'name': "Documentation" }
                        ]
                    }
                ]
            },
            {
                'name': "opt",
                'children': []
            },
            {
                'name': "Users",
                'children': [
                    { 'name': "pavanpodila" },
                    { 'name': "admin" },
                    { 'name': "test-user" }
                ]
            }
        ]
    };
    
    

    return treeData

def hierarchyExample3():
    data = {
            'name': "certificates",
            'id': "cert-root",
            'children': [{
                'name': "ISO",
                'id': "cert-iso",
                'children': [
                    {'id':"CO-01",
                      'name':"CO-AuditPlanning",
                        'children': [{
                            'id': "CO-01_1",
                            'name': "CO-AuditPlanning.1",
                            'children': [{
                                'id': "softlayer",
                                'name': "Soft Layter",
                                'children': [{
                                    'id': "softlayer21",
                                    'name': "Soft Layter21",
                                },
                                {
                                    'id': "softlayer22",
                                    'name': "Soft Layter22",
                                }
                                ]
                            }]
                        }]
                    },
                    {'id':"CO-06",'name':"CO-IntellectualProperty",
                        'children': [{
                            'id': "CO-06_1",
                            'name' : "CO-IntellectualProperty1",
                            'children': [{
                                'id': "Aryaka",
                                'name': "Aryaka"
                            }]
                        }
                        ]},
                    {'id':"DG-01",'name':"DG-Ownership"},
                    {'id':"SA-15",'name':"SA-MobileCode",
                        'children': [{
                            'id': "SA-15_1",
                            'name': "SA-MobileCode.1",
                            'children': [{
                                'id': "softlayer",
                                'name': "Soft Layter",
                                'children': [{
                                    'id': "softlayer21",
                                    'name': "Soft Layter21",
                                },
                                {
                                    'id': "softlayer22",
                                    'name': "Soft Layter22",
                                }
                                ]
                            }]
                        }, {
                            'id': "SA-15_2",
                            'name': "SA-MobileCode.2",
                            'children': [{
                                'id': "softlayer",
                                'name': "Soft Layter",
                            }]
                        }
                     ]
                 }]
            },
            {
                'name': "COBIT",
                'id': "cert-cobit",
                'children': [
                    {
                        'id': "CO-01",
                        'name' : "co-AuditPlanning",
                        'children': [{
                            'id': "CO-01_1",
                            'name' : "CO-AuditPlanning.1",
                            'children': [{
                                'id': "softlayer",
                                'name': "Soft Layter",
                                'children': [{
                                    'id': "softlayer21",
                                    'name': "Soft Layter21",
                                },
                                {
                                    'id': "softlayer22",
                                    'name': "Soft Layter22",
                                }
                                ]
                            },
                            {
                                'id': "Aryaka",
                                'name': "Aryaka"
                            }
                            ]
                        }
                        ]
                    }
                ]
            }
            ]
    }
    
    data2 = {
        'name': 'certificates', 
        'id': 'cert-root',
        'children': [
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-14', 'name': u'LYS-20200225-14'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-15', 'name': u'LYS-20200225-15'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-16', 'name': u'LYS-20200225-16'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-18', 'name': u'LYS-20200225-18'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-19', 'name': u'LYS-20200225-19'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-20', 'name': u'LYS-20200225-20'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-22', 'name': u'LYS-20200225-22'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-23', 'name': u'LYS-20200225-23'}, 
            {'children': [{'id': u'D.MSP-20200225-26', 'name': u'D.MSP-20200225-26'}], 'id': u'LYS-20200225-24', 'name': u'LYS-20200225-24'}
        ]
    }
    return data2

    return convertTree(data)
    return data

def convertTree(treeData):
    ''' Convert  a children tree into a multi-parents tree.
    Input:
        treeData = the tree data, such as a parent with two children:
                {
                    'id': "A_1",
                    'name': "A",
                    'children': [{
                        'id': "B_1",
                        'name': "B",
                        },
                        {
                        'id': "C_1",
                        'name': "C",
                    }]
                }
        such as,       ________
                      /         B
                A____|
                      \_________C
                      
    Output:
        reversed treeData, such as two parents with one child,
            multi-parents-tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
    References:
        1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
        2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
    
    '''
    data1 = {
        'id': "A_1",
            'name': "A",
            'children': [{
                'id': "B_1",
                'name': "B",
            },
            {
                'id': "C_1",
                'name': "C",
            }]
        }
    
    data2 = {
        'name': "certificates",
        'id': "cert-root",
        'children': [
            {
                'id': "B_1",
                'name': "B",
                'children': [{
                    'id': "A_1",
                    'name': "A",
                }]
            },
            {
                'id': "C_1",
                'name': "C",
                'children': [{
                    'id': "A_1",
                    'name': "A",
                }]
            }
        ]
    }
    
    actualTree = {}
    
    treeData = {
        'name': "certificates",
        'id': "cert-root",
        'children': [actualTree]
    }
    
    return data2
    
from joblib import Parallel, delayed
import multiprocessing

    
# refer to:http://www.visualseq.net/dokuwiki/doku.php?id=computer:software:python:python-multithreading#parallel_loop
def unwrap_self_createMultiParentTreeParallel_i(arg, **kwarg):    
    return DBtable_sample.createMultiParentTreeParallel_i(*arg, **kwarg)

def unwrap_self_createSampleChildrenTreeParallel_i(arg, **kwarg):
    return DBtable_sample.createSampleChildrenTreeParallel_i(*arg, **kwarg)

class DBtable_sample(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        sample = DBtable_sample("DEFAULT")
        return sample.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_sample"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'samples'
        self.tablemodel = Samples
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
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
        
        # the unique constraint to find the primary key
        #self.uniqueFields = ['title']
        # The unique constraint for a sample is identified by the sample name (stored as title) and the user id,
        # which is equavilent to the sample UID/uuid, where UID=uuid.
        #self.uniqueFields = ['title', 'contributor_id', 'sample_type_id']
        self.uniqueFields = ['uuid']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = SAMPLE_FILTER_MAPPING
        self.excludeFields = []
        
    def __notEmptyLine(self, csvdic):
        ''' Check whether a csv line is empty
        '''
        #print csvdic
        
        notEmpty = True
        if len(csvdic)==0:
            notEmpty = False
            return notEmpty
            
        allNone = True
        for key, value in csvdic.items():
            if value is None:
                okay = 1
                #print "__notEmptyLine: key, value: None", key, value
            else:
                allNone = False
            
        if allNone:    
            #print "__notEmptyLine: key, value: not None: ", key, value
            notEmpty = False
            
        #print "__notEmptyLine: ", notEmpty
        return notEmpty
        
    def getSampleUIDIndex(self, sampleUIDPrefix):
        ''' Find the index for a sample uid, given,
        Input:
            sampleUIDPrefix, such as "X.SAM-200413-UMS", where
                X.SAM: is the sampletype name;
                200413=YYMMDD: two digits for year.
                UMS: three letter abbreviation of the DESCRIPTION in INSTITUES table. Refer to: "/dokuwiki/doku.php?id=computer:websites:dmac:user#user_module_in_seek"
        Output:
            index, which is the next integer to be used as the suffix of the sample uid, such as
                15: is the incremental index in a day for the sample from same lab,
                so the uid = "X.SAM-200413-UMS-15"

        Notes:
            the index must be the next integer available to use. Therefore, the logic is,
                1. Search for the number N of uids with the same prefix ""X.SAM-200413-UMS";
                2. an easy way to define the next one is N+1, However, it would be an error
                   if some samples were deleted before. Therefore, a robust way is to find the maximum number then plus 1.
        '''
        records = self.db.retrieveRecords(self.tablemodel, 'uuid', sampleUIDPrefix)
        
        prefix = sampleUIDPrefix + '-'          # such as "X.SAM-200413-UMS-"
        indexes = []
        maxindex = 0
        for record in records:
            uid = record['uuid']                # such as "X.SAM-200413-UMS-15"
            if prefix in uid:
                index = uid.replace(prefix, '') # such as "15"
                index = toInt(index)
                if index>maxindex:
                    maxindex = index
            
        nextIndex = maxindex + 1    
        return nextIndex
    
    def __defineUID(self, user_seek, record, attributeInfo):
        ''' Define the UID for a new sample.
        Input:
            record,
            attributeInfo
            
        Output:
            uid, which is unique in the sample table.
            
        Notes:
            The sample UID is defined as
                sampletype-YYMMDD-LAB-INDEX
            for example,
                X.SAM-200419-UMS-15
            where
                X.SAM: is the sampletype name;
                YYMMDD: two digits for year.
                UMS: three letter abbreviation of the DESCRIPTION in INSTITUES table. Refer to: "/dokuwiki/doku.php?id=computer:websites:dmac:user#user_module_in_seek"
                15: is the incremental index in a day for the sample from same lab.
        '''
        #print '__defineUID'
        
        sampletype = attributeInfo['sampletype']
        #print(sampletype)
        
        # such as MUS_190930, where MUS is the sample type name and 190930 is the date of creation.
        typetitle = sampletype['title']
        uid_prefix = typetitle
        if '_' in typetitle:
            terms = typetitle.split('_')
            uid_prefix = terms[0]
            
        uid_date = str(datetime.datetime.now().strftime("%Y%m%d"))
        # lab abbreviation
        lab = user_seek['lababbv']
        
        prefix = uid_prefix + '-' + uid_date[2:] + lab
        
        #nextIndex = str(self.getLatestPrimarykey())

        nextIndex = str(self.getSampleUIDIndex(prefix))
        
        uid = prefix + '-' + nextIndex
        return uid
    
    def __getRecordToJson(self, record, attributeInfo):
        ''' Convert a sample record into json format for storing into DB table.
        Input
            record, a dictionary from sample sheet uploaded;
            attributeInfo, the definition of the sample type.
        
        Output
            a json string, such as 
        '''
        # convert record from sample sheet into the required format defined:
        headers = attributeInfo['headers']
        record_new = {}
        for header in headers:
            field = header.lower()
            if header in record:
                record_new[field] = toString(record[header])
            else:
                record_new[field] = ''
        
        #print(record_new)
        record_json = simplejson.dumps(record_new)
        #print(record_json)
        
        # Verify json conversion
        #record_verify = self.__getRecordFromJson(record_json)
        #print(record_verify)
        #for header in headers:
        #    print(record_new[header], record_verify[header])
        
        return record_json
        
    def __getRecordFromJson(self, record_json):
        ''' Convert a sample record from json format in DB into a dictionary.
        Input
            a json string, such as 
        Output
            record, a dictionary from sample sheet uploaded;
            attributeInfo, the definition of the sample type.
        '''
        record = json.loads(record_json)
        return record
        
    def __updateSampleMetadata(self, metadata_db, metadata_in):
        ''' Update the metadata for an existing sample in DB with the following logic:
                Keep existing metadata unchanged, unless there is new change in the input metadata.
                
        Input:
            metadata_db, a dictionary of the metadata from DB for a sample;
            metadata_in, a dictionary of the metadata for a sample from the input, such as from the assay sheet uploading.
        
        Output:
            metadata_out, a dictionary of the metadata, which combines both metadata_db and metadata_in so that only attribute from input is updated,
                while rest of attributes remain the same. 
        
        Notes:
            This is the function to keep metadata_db unchanged and update only those attributes in the metatdata_in,
        
        Requirement:
            The new value must not be None or empty.
        '''
        print("__updateSampleMetadata")
        
        print("metadata_db:", metadata_db)
        print("metadata_in:", metadata_in)
        
        # change all keys to lower case
        metadata_in2 = {}
        for key, value in metadata_in.items():
            lowkey = key.lower()
            metadata_in2[lowkey] = value
        metadata_in = metadata_in2
        
        if metadata_db['uid']!=metadata_in['uid']:
            #Both UIDs must match. Otherwise, keep input metadata untouched.
            return metadata_in
        
        # Step 1: update attributes that are already in DB
        metadata_out = {}
        for key, value in metadata_db.items():
            
            if key in metadata_in:
                value_in = metadata_in[key]
                if value_in is None:
                    # do not update None value
                    metadata_out[key] = value
                    continue
                
                elif value_in==RESERVED_REMOVE_VALUE_FOR_UPDATE:
                    # remove attribute value from DB if input value is the reserved word, such as "-null"
                    continue
                
                elif value_in==RESERVED_DEFAULT_VALUE_FOR_UPDATE:
                    # If an attribute value equals to "-none", such attribute in the database will be added with default None value from a sample's meta data. 
                    metadata_out[key] = ''
                    continue
                
                try:
                    # do not update empty value/string
                    value_str = str(value_in)
                    if len(value_str)>0:
                        metadata_out[key] = value_in
                except:
                    # update any value that is exceptional
                    metadata_out[key] = value_in
            else:
                metadata_out[key] = value
        
        # Step 2: add new attributes that are not in DB yet
        for key, value in metadata_in.items():
            if key not in metadata_out:
                if value==RESERVED_DEFAULT_VALUE_FOR_UPDATE:
                    # If an attribute value equals to "-none", such attribute in the database will be added with default None value from a sample's meta data. 
                    metadata_out[key] = ''
                else:
                    metadata_out[key] = value
        
        print("metadata_out:", metadata_out)
        return metadata_out
        
    def __getRecord(self, user_seek, record, attributeInfo, contributor_id):
        ''' Prepare a sample record for stroing into Samples table.
        Input
            username, login user name
            record, a dictionary from sample sheet for uploading.
            attributeInfo, the list of sample attributes defined in Seek system for this sample type.

        Output
            a dictionary, ready for storing into Samples table.
            newSample, whether it is a new sample thus the UID is automatically generated.
        '''
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        record_new = {}
        # Set initial values
        for field in self.fields:
            value = ''
            if field in SAMPLE_DEFAULT:
                value = SAMPLE_DEFAULT[field]
            record_new[field] = value
            
        uid = record['UID']
        newSample = False
        if uid is None or len(uid.strip())==0:
            # Assume a new sample for uploading, define the default UID
            uid = self.__defineUID(user_seek, record, attributeInfo)
            record['UID'] = uid
            newSample = True
        #else:
        # moved to __batchUploadTest()
        #    # verify if the UID provided is valid, such as
        #    # the UID does not exist in the database so the sample record should be rejected
        #    # or even though the UID exists in the database, but it does not match the sample type
        #    newSample = False
        #    isValid, msg = self.__verifyUID(uid, attributeInfo)
        
        #record_new['id'] = None
        
        #record_new['title'] = uid
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
        #record_new['contributor_id'] = user_id
        record_new['contributor_id'] = contributor_id
        
        policy = DBtable_policies("DEFAULT")
        # run uploading
        # get the policy from DB for existing sample
        record_db = self.__retrieveSampleByUID(uid)
        if record_db is None:
            # new sample
            #msg, status, policy_id = policy.createDefaultPolicy(username, user_id, project_id)
            msg, status, policy_id = policy.createDefaultPolicy(username, contributor_id, project_id)
        else:
            policy_id = record_db['policy_id']
            contributor_id = record_db['contributor_id']
            record_new['contributor_id'] = contributor_id
            
            metadata_db = self.__getRecordFromJson(record_db['json_metadata'])
            metadata_in = self.__getRecordFromJson(record_new['json_metadata'])
            metadata_out = self.__updateSampleMetadata(metadata_db, metadata_in)
            record_new['json_metadata'] = simplejson.dumps(metadata_out)
            
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
        ''' Update sample-project relationship in projects_samples table.
        
        '''
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        record = {}
        record['sample_id'] = sample_id
        record['project_id'] = project_id
        # check whether insert or update record into projects_samples table
        
        record = Projects_samples(project_id=project_id, sample_id=sample_id)
        record.save()
        return
        
        sqlquery = 'SELECT * FROM projects_samples;'
        print(sqlquery)
        for p in Projects_samples.objects.raw(sqlquery):
            print(p)
        
        sqlquery = 'insert into projects_samples VALUES (' + str(project_id) + ',' + str(sample_id) + ');'
        #self.db.run_custom_sql(sqlquery)
        # refer to:
        print(sqlquery)
        # refer to: https://docs.djangoproject.com/en/3.0/topics/db/sql/
        # it does not work
        Projects_samples.objects.raw(sqlquery)
        
    def __updateSampleAssetsCreators(self, user_seek, sample_id, contributor_id):
        ''' Insert a new record into assets_creators table to define the creator of Sample asset.
        Input
            
        Output
            
        '''
        print("updateSampleAssetsCreators")
        #creator_id = user_seek['user_id']
        creator_id = contributor_id
        
        timenow = getDefaultDateTime()
        record = Assets_creators(asset_id=sample_id, creator_id=creator_id, asset_type='Sample', created_at=timenow, updated_at=timenow)
        record.save()
        return
        
    def __verifyOntology(self, record):
        ''' Verify whether the value for a field in a table satisfies the ontology for
        that field.
        
        To be implemented.
        
        '''
        msg = "Warning: verifying ontology of a sample info is to be implemented"
        print(msg)
        
    def __verifyRequiredFields(self, record, fields_required):
        ''' Verify whether the record for uploading has all required fields, given
        Input:
            record, a dictionary from sample sheet for uploading.
            fields_required, a list of fields required for uploading.
        Output:
            msg, any message
            status, True, if all reuired fields are available in Record, or
                    False, if not all reuired fields are available in Record
        '''
        # 'UID' may be a required field defined in DB table for this sample
        # However, we exclude it from the check on other required fields
        if 'UID' not in record.keys():
            msg = SAMPLE_ERRORCODE['503']
            print(msg)
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
                # required field not in record
                meetRequired = False
                msg_required += field + ";"
                
        if meetRequired:
            msg_required = 'All fields required are available'
        return msg_required, meetRequired
        
    
    def __loadSampleTypes(self, diclist_instruction):
        ''' Load the list of attribute name and sample type in the Instructions sheet, given
        Input:
            diclist_instruction, the diclist from the Instructions sheet, in the following format,
                Field	                        Database Field
                Mouse UID	                    MUS::UID
                Mouse Name	                    MUS::Name
                Lab	                            MUS::StorageLocation
                Storage Site	                MUS::StorageSite
                Storage Condition	            MUS::StorageType
                Created By User	                MUS::CreatedByUser
                SEEK Submission Date	        MUS::CreatedByDate
                Strain	                        MUS::Strain
                Strain Reference (NCBI #, etc)	MUS::StrainReference
                ...
                MUS::UID                        TIS::SourceSample
            
        Output:
            sampleTypes = {name1:attributeMapping1, name2;attributeMapping2,...}, where,
                name, the name of a sample type, such as "MUS"
                attributeMapping = {header1:attribute1, header2:attribute2,...}, a dictionary with the mapping between the header name in the sample sheet and the attribute name in sample table.
                    For example,
                    attr = {
                        "Mouse UID":"UID",
                        ...
                        "Strain":"Strain",
                    }
                    where prefix "MUS::" has been removed from the attribute.
            sampleTypes_order = [], such as ['MUS', 'TIS', 'IMG'], the order of samples to follow in uploading samples.
                One important thing is the hierarchical relationship among samples, which is defined as the following,
                    MUS::UID                        TIS::SourceSample
                where in TIS sample, the parent "SourceSample" is the UID from the MUS sample. Therefore, during batch
                uploading, we must upload 'MUS' sample first and return its UID, which will be used as the 'SourceSample'
                attribute in 'TIS' sample for uploaidinig next. 
            
            attributesControlled = {'Stimulant':[], 'Instrument':[], 'Gender':[],...}, a dictionary with a list of attributes
                that are controlled ontology/vocabulary. The list of terms in each of vocabularies is to be loaded from
                the Ontology sheet or from the database.
        Notes:    
            Requirement for how to prepare the Intruction sheet:
                The list of attributes in the Instruction sheet should follow the order that attributes for parent sample
                are always in front of attributes for child sample.
                
        '''
        sampleTypes = {}      
        sampleTypes_order = []
        for dici in diclist_instruction:
            if "Field" not in dici or "Database Field" not in dici:
                print dici
                # the instruction sheet must have "Field","Database Field" as the first two columns.
                msg = "Error: Instruction sheet should contain 'Field' or 'Database Field' columns."
                print(msg)
                return {}, []
                
            # header in Samplae sheet
            tbheader = dici["Field"]
            if tbheader is not None:
                header = str(tbheader)
                if len(header.strip())==0:
                    continue
            else:
                continue
            
            # attribute name in Sample hash
            dbfield = dici["Database Field"]
            if DELIMITER_DBFIELD not in dbfield:
                print("Database Field: ", dbfield)
                # return any error without proceeding
                msg = "Error: 'Database Field' column should follow the format 'tableName::attributeName."
                print(msg)
                return {}, []
                
            terms = dbfield.split(DELIMITER_DBFIELD)     # dbfield, such as MUS::Strain, TIS::SourceSample
            sampleType = terms[0]          # such as MUS
            attribute = terms[1]            # such as SourceSample
            if sampleType in sampleTypes:
                attributeMapping = sampleTypes[sampleType]
            else:
                attributeMapping = {}
                                
            # such as   attributeMapping['Strain'] = 'Strain'
            #           attributeMapping['MUS::UID'] = 'SourceSample'
            attributeMapping[tbheader] = attribute
            sampleTypes[sampleType] = attributeMapping
            
            # Requirement for how to prepare the Intruction sheet:
            # The list of attributeMapping in the Instruction sheet should follow the order that attributeMapping for parent sample
            # are always in front of attributeMapping for child sample.
            # Therefore, the order of samples in batch uploading depends on which sampleType appears first. 
            if sampleType not in sampleTypes_order:
                sampleTypes_order.append(sampleType)
            
        #print sampleTypes
        #msg = ""
        #for sampletype in sampleTypes:
        #    ats = sampleTypes[sampletype]
        #    for att in ats:
        #        msg += sampletype + '\t' + att + "\t" + ats[att] + '<br/>'
                
        return sampleTypes, sampleTypes_order
        
    def __splitSampleTypes(self, sampleTypes, diclist_samples):
        ''' Split a meta-sample sheet into a list of sample sheets for each of sample types, given
        Input
            sampleTypes = {name1:attrMapping1, name2;attrMapping2,...}, where,
                name, the name of a sample type, such as "MUS"
                attrMapping = {header1:attribute1, header2:attribute2,...}, a dictionary with the mapping between the header name in the sample sheet and the attribute name in sample table.
                    For example,
                    attrMapping = {
                        "Mouse UID":"UID",
                        ...
                        "Strain":"Strain",
                        "MUS::UID":"SourceSample"
                    }
                    where prefix "MUS::" has been removed from the attribute, and
                    the "SourceSample" should come from the UID in MUS sample.
        
            diclist_samples, a list of dictionaries, loaded from the Sample sheet.
        Output
            sample_sheets = {name1:diclist1, name2:diclist2,...}, where
                name: the name of the sample type, such as "MUS"
                dislist: the list of dictioaries, in which headers are replaced by attibutes for a sample type.
        
        Usage:
            Assume we have mouse and tisse samples as the following:
            
                mouse1 weight1  tissue1  volume1
                mouse1 weight1  tissue2  volume2
                mouse2 weight2  tissue3  volume3
                
            The output will be:
            
                sample_sheets = {'mouse':[mouse1, mouse1, mouse2], 'tissue':[tissue1, tissue2, tissue3]}
                
        This is the original function to split meta-samples, where each row is processed independently so that
        mouse1 in the first row and mouse1 in the second row are processed independently. If in the second row,
        the weight of mouse1 becomes 0, 0 will replace weight1 to update the mouse1 info.
        '''
        return self.__splitSampleTypes_new(sampleTypes, diclist_samples)
        
        sample_sheets = {}
        for sampleType in sampleTypes:
            sample_sheets[sampleType] = []
            
        for dici_meta in diclist_samples:
            for sampleType, attributeMapping in sampleTypes.items():
                diclist = sample_sheets[sampleType]
                dici_sample = {}
                for header, value in dici_meta.items():
                    if header in attributeMapping:
                        attribute = attributeMapping[header]
                        dici_sample[attribute] =  value
                        
                diclist.append(dici_sample)
                sample_sheets[sampleType] = diclist
                #if sampleType=='IMG':
                #    print('dici_sample', dici_sample)
                #    print(attributeMapping)
                #    print(dici_meta)
        #for sampleType, diclist_sample in sample_sheets.items():
        #    for dici in diclist_sample:
        #        print sampleType, dici
        #print('dici_sample', dici_sample)
        return sample_sheets
            
    def __splitSampleTypes_new(self, sampleTypes, diclist_samples):
        ''' Split a meta-sample sheet into a list of sample sheets for each of sample types, given
        Input
            sampleTypes = {name1:attrMapping1, name2;attrMapping2,...}, where,
                name, the name of a sample type, such as "MUS"
                attrMapping = {header1:attribute1, header2:attribute2,...}, a dictionary with the mapping between the header name in the sample sheet and the attribute name in sample table.
                    For example,
                    attrMapping = {
                        "Mouse UID":"UID",
                        ...
                        "Strain":"Strain",
                        "MUS::UID":"SourceSample"
                    }
                    where prefix "MUS::" has been removed from the attribute, and
                    the "SourceSample" should come from the UID in MUS sample.
        
            diclist_samples, a list of dictionaries, loaded from the Sample sheet.
        Output
            sample_sheets = {name1:diclist1, name2:diclist2,...}, where
                name: the name of the sample type, such as "MUS"
                dislist: the list of dictioaries, in which headers are replaced by attibutes for a sample type.
        
        Usage:
            This is a revision of __splitSampleTypes() above.
            Assume we have mouse and tisse samples as the following:
            
                mouse1 weight1  tissue1  volume1
                mouse1          tissue2  volume2
                mouse2 weight2  tissue3  volume3
                
            where in the seconf row, the weight value for mouse1 is not provided, we will use the info weight1
            from first row instead.
            The rule for revising the logic in the script is as the following:
                If a mouse name, such as mouse1, appears the first time in loading the file,
                all attribute values in the same row will be regarded as the valid record of this mouse sample,
                any subsequent appearance of the same mouse name in other rows will be ignored.
            
            The output will be:
            
                sample_sheets = {'mouse':[mouse1, mouse1, mouse2], 'tissue':[tissue1, tissue2, tissue3]}
            
            where mouse1 and mouse1 are identical.    
        '''
        sample_sheets = {}
        for sampleType in sampleTypes:
            sample_sheets[sampleType] = []
            
        # this is used to store each uqniue sample when each type of sample appears the first time
        unique_samples = {}
            
        for dici_meta in diclist_samples:
            for sampleType, attributeMapping in sampleTypes.items():
                diclist = sample_sheets[sampleType]
                
                # dictionary for each sample type
                dici_sample = {}
                samplename = None
                for header, value in dici_meta.items():
                    if header in attributeMapping:
                        attribute = attributeMapping[header]
                        dici_sample[attribute] =  value
                        
                        if attribute.lower()=='name':
                            # unique identifier for experimental sample type
                            samplename = value
                        elif attribute.lower()=='file_primarydata':
                            # unique identifier for A. and D. sample type
                            samplename = value
                        elif attribute.lower()=='file_primarydata_forward':
                            # unique identifier for A. and D. sample type
                            samplename = value
                        elif attribute.lower()=='file_primarydata_reverse':
                            # unique identifier for A. and D. sample type
                            samplename = value
                            
                if samplename is None:
                    msg = 'Error: one sample does not have an unique identifier, which will be captured later on in __getRecord()'
                    print(msg)
                elif samplename in unique_samples:
                    # this is not the first time appearance of this sample, ignore its current value and replace it with the one in queue.
                    dici_sample = unique_samples[samplename]
                else:
                    # this is the first time appearance of this sample, save it in the queue.
                    unique_samples[samplename] = dici_sample
                        
                diclist.append(dici_sample)
                sample_sheets[sampleType] = diclist
                #if sampleType=='IMG':
                #    print('dici_sample', dici_sample)
                #    print(attributeMapping)
                #    print(dici_meta)
        #for sampleType, diclist_sample in sample_sheets.items():
        #    for dici in diclist_sample:
        #        print sampleType, dici
        #print('dici_sample', dici_sample)
        return sample_sheets
    
    
    def __setSampleDatafileAssociation(self, user_seek, sampleType, record, attributeInfo, diclist_assay):    
        #def __testSampleDatafiles(self, record, attributeInfo):
        ''' Test and process data files listed iin the sample sheet.
        Input:
            sampleType, for which sample type the data file shold be associated, such as 'D.FLOW', 'MUS', 'TIS' etc        
            record, a dictionary from sample sheet for uploading.
            attributeInfo, the list of sample attributes defined in Seek system for this sample type.
                attributeInfo['headers'], the list of attributeInfo (fields) for the sample;
                attributeInfo['headers_required'], a list of attributeInfo required;
                attributeInfo['sampletype'] = {}
            
            diclist_assay, 
            
        Output:
            msg, any message
            status, whether or nor the test passes.
             
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
        print('updateSampleDatafileAssociation')
        username = user_seek['username']
        user_id = user_seek['user_id']
        project_id = user_seek['projectid']
        
        msg = ''
        status = 1
        
        attributeTypes = attributeInfo['attributeTypes']
        
        dbdf = DBtable_data_files("DEFAULT")
        for attribute, dfurl in record.items():
            if attribute not in attributeTypes:
                #print "attribute not in attributeTypes:", attribute, dfurl
                continue
            
            attributeType_id = attributeTypes[attribute]
            #if attributeType!='URI' and attributeType!='Web link':
            # attributeType=5='Web link' and attributeType=19='URI' in sample_attribute_types table
            if attributeType_id!=ATTRIBUTETYPE_ID_WEBLINK and attributeType_id!=ATTRIBUTETYPE_ID_URI:
                #print "attributeType not URI or Web link:", attributeType_id
                continue
            
            msgi, statusi = dbdf.processSampleDatafile(user_seek, sampleType, dfurl, diclist_assay)
            if not statusi:
                status = 0
                msg += msgi + ';'
                print(msg)
                
        return msg, status
    
    
    def __verifyUID(self, uidIn, attributeInfo):
        ''' Verify if the UID provided is valid, such as,
                a. the UID does not exist in the database so the sample record should be rejected
                b. or even though the UID exists in the database, but it does not match the sample type

        Input:
            uidIn, the UID for an sample to be checked.
            attributeInfo, the list of sample attributes defined in Seek system for this sample type.

        
        Output:
            isValid, true, an valid UID for update;
                    or false, an invalid UID that should be rejected.
            msg, the error message
        '''
        isValid = True
        msg = ''
        # Step 1. Check even though the UID exists in the database, but it does not match the sample type
        sampletype = attributeInfo['sampletype']
        typetitle = sampletype['title']
        uid_prefix = typetitle
        if '_' in typetitle:
            terms = typetitle.split('_')
            uid_prefix = terms[0]
            # such as "PAV"
            
        uidIn_prefix = uidIn
        if '-' in uidIn:
            terms = uidIn.split('-')
            uidIn_prefix = terms[0]
            # such as "PAT"
        
        if uid_prefix.strip()!=uidIn_prefix.strip():
            # such as "PAV" vs "PAT"
            msg = "Error: Sample UID " + uidIn + " does not match sample type: " + typetitle
            isValid = False
            return isValid, msg
        
        # Step 2. check whether the UID does not exist in the database so the sample record should be rejected
        record = self.__retrieveSampleByUID(uidIn)
        if record is None:
            # customized UID is not found in DB, reject it
            # Notes that this UID is not the one generated automatically in __getRecord()
            msg = "Error: Sample UID " + uidIn + " does not exist in DB for update "
            isValid = False
            return isValid, msg
        
        return isValid, msg

            
    def __storeSample(self, user_seek, sampleType, record, attributeInfo, diclist_assay, contributor_id):
        ''' Store one record from input excel file for batch uploading.
        
        Input
            record, a dictionary from sample sheet for uploading.
            attributeInfo, the list of sample attributes defined in Seek system for this sample type.
            uploadEnforced, if False, only run test; if True, forcefully upload the rcord into DB.
        
        Output
            msg, any message
            status, whether or nor the test passes.
            uid, UID for the sample
        '''
        username = user_seek['username']
        if not self.__notEmptyLine(record):
            msg = SAMPLE_ERRORCODE['501']
            print(msg)
            return msg, 0, None
        
        # prepare requuired fields for the sample
        headers_required = attributeInfo['headers_required']
        
        # Verify whether the record for uploading has all required fields
        msg_required, meetRequired = self.__verifyRequiredFields(record, headers_required)
        if not meetRequired:
            msg = SAMPLE_ERRORCODE['502'] + msg_required
            print(msg)
            return msg, 0, None
                
        #keysup = [x.upper() for x in record.keys()]
        if 'UID' not in record.keys():
            msg = SAMPLE_ERRORCODE['503']
            print(msg)
            return msg, 0, None
        
        record_new, newSample = self.__getRecord(user_seek, record, attributeInfo, contributor_id)
        uid = record_new['uuid']
        
        # for test only
        # return 'test', 1, uid

        #print(record_new)
        #return 'Upload to be enforced', 1, uid   
        msg, status, sample_id = self.storeOneRecord(username, record_new)
        if status:
            if newSample:
                # only for new sample
                # create a record in project_sample table
                self.__updateSampleProject(user_seek, sample_id)
                self.__updateSampleAssetsCreators(user_seek, sample_id, contributor_id)
                if len(diclist_assay)>0:
                    msgj, statusj = self.__storeSample_assay_asset(user_seek, sampleType, sample_id, diclist_assay)
                    if statusj==0:
                        msgj = SAMPLE_ERRORCODE['601'] + msgj
                        print(msgj)
                        msg += ';' + msgj
                else:
                    msg = 'Info: Assay info not available for updating array-sample relationship for sample id: ' + str(sample_id)
                    print(msg)
            else:
                msg = 'Info: No update on array-sample relationship for old sample id: ' + str(sample_id)
                print(msg)
                    
            # Create datafile-sample-assay association, for existing or new sample
            msgdf, statusdf = self.__setSampleDatafileAssociation(user_seek, sampleType, record, attributeInfo, diclist_assay)
            if not statusdf:
                msgdf = SAMPLE_ERRORCODE['602'] + msgdf
                print(msgdf)
                msg += ';' + msgdf
        else:
            msg = SAMPLE_ERRORCODE['504'] + msg
        
        #print(msg, status, uid)
        return msg, status, uid
    
    def __storeSample_assay_asset(self, user_seek, sampleType, sample_id, diclist_assay):
        
        username = user_seek['username']
        assay_assets = DBtable_assay_assets("DEFAULT")
        return assay_assets.storeSample_assay_asset(user_seek, sampleType, sample_id, diclist_assay)
        
    def __searchUniqueSample(self, samplename, scientist, sample_type_id):
        # to partial match of (samplename, json_metadata, sample_type_id)
        #constraint = {'title':samplename, 'json_metadata':scientist, 'sample_type_id':sample_type_id}
        #records = self.retrieveContainedRecords(constraint)
        
        query = {}
        query['sample_type_id__exact'] = sample_type_id
        qset = Q(**query)
        
        query = {}
        #Case-insensitive containment of scietist name in json_metadata
        query['json_metadata__icontains'] = scientist
        qset = qset & Q(**query)
        
        query = {}
        # case insensitive match of sample name
        query['title__iexact'] = samplename
        qset = qset & Q(**query)
            
        records = self.queryRecordsCustom(qset)
        
        #print("__searchUniqueSample:")
        #print(records)
        
        return records
        
    def __verifySampleUID(self, samplename, userid, uidIn, sample_type_id, scientist):
        ''' Verify the consistency between a sample UID and the unique constraint for a sample
        by (samplename, user_id), where samplename is stored as title in the samples table.
        
        Input:
            samplename, the required sample name from dici['Name'], which is 'title' in the samples table;
            userid, the login user id, 'contributor_id' in the samples table;
            uidIn, the uid from the sample sheet, which could be anything.
        
        Output:
            msg, any message
            status, 1 no conflict
                    0 for any error
        '''
        samplename = str(samplename)
        
        # we revise the unique constraint from exact match of (samplename, contributor_id, sample_type_id)
        #constraint = {'title':samplename, 'contributor_id':userid, 'sample_type_id':sample_type_id}
        #records = self.queryRecordsByConstraint(constraint)
        
        records = self.__searchUniqueSample(samplename, scientist, sample_type_id)
        
        nr = len(records)
        status = 1
        msg = ''
        if nr==0:
            # no record is found in Samples table
            if uidIn is None or len(uidIn.strip())==0:
                # Unique sample is found in DB, therefore only update operation is allowed
                status = 1
                msg = 'Okay: ready for store a new sample without predefined UID'
            else:
                status = 1
                msg = 'Okay: ready for store a new sample with predefined UID: ' + uidIn
        elif nr==1:
            # one record is found in Samples table
            record = records[0]
            uid_verified = record['uuid'] # we always use 'uuid' to store UID for a sample.
            if uidIn is None or len(uidIn.strip())==0:
                # Unique sample is found in DB, therefore only update operation is allowed
                status = 0
                #msg = 'Error: Sample name ' + samplename + ' with UID ' + uid_verified + ' already in DB.'
                #msg += ' Add this UID in the sample sheet for update.'
                msg = SAMPLE_ERRORCODE['401'] + uid_verified
            elif uid_verified==uidIn:
                status = 1
                msg = 'Okay: Unique record exists based on ' + samplename
                msg += ', which is consistent with the UID ' + uidIn
            else:
                status = 0
                #msg = 'Error: Sample name ' + samplename + ' with UID ' + uid_verified + ' already in DB,'
                #msg +='which does not match with the UID provided ' + uidIn
                msg = SAMPLE_ERRORCODE['402'] + uidIn + ' ' + uid_verified
        else:
            status = 0
            #msg = 'Error: Sample name ' + samplename + ' has duplicated records in DB, ask Administrator for help!'
            msg = SAMPLE_ERRORCODE['403']
        return msg, status
    
    def __updateSampleErrorMsg(self, sampledic_feeback, primaryField, msg, sampleType):
        ''' Update the error message to the UID field of a sample, given,
        Input:
            sampledic_feeback, the sample dictionary for a sample type specific, whose keys are headers of the sample sheet,
                    i.e., the first column in the Instruction sheet, which are different from the attribute names in DB table.
                    
            primaryField, the header corrresponding to the 'UID' attribute for the sample, for example,
                'Cell UID' for the 'UID' attribute in CEL sample, or
                'Lysate UID' for the 'UID' attribute in LYS sample, etc.
            msg, the error message
            
            sampleType, the sample type
        
        Output:
            sampledic_feeback
        '''
        header = sampleType + "::UID"
        sampledic_feeback[header] = msg
        
        # put the error message in the UID field
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
        ''' Query contributor ID based on the fullname.
        Input:
            user_seek,
            contributor_fullname, Full name of the user in SEEK, i.e.,
                fullname = firstname = ' ' + lastname
        
        Output:
            The person ID based on the full name of the user or -1.
        '''
        seekdb = SeekDB(user_seek['server'], user_seek['username'], user_seek['password'])
        contributor_id = seekdb.getUserid(contributor_fullname)
        if contributor_id is None:
            return -1
        
        return contributor_id
        
        
    def __batchUploadTest(self, user_seek, sampleType, diclist, diclist_feedback, attributeInfo, attributeMapping, diclist_assay, uploadEnforced=False):
        ''' infile, posted in http for uploading, which could be either a csv or excel file.
        
        Input
            username, the login user name.
            sampleType, such as 'MUS', 'TIS', the name of a sample type.
            diclist, a list of dictionaries for batch uploading.
            diclist_feedback, a list of dictionaries for feedback, which includes source sample info and the current sample UID etc.
            attributeInfo, the list of sample attributeMapping defined in Seek system for this sample type.
            attributeMapping, the mapping between headers in Sample sheet and dbfields in sample hash, for the sample type specified.
            uploadEnforced, if False, only run test; if True, forcefully upload the rcord into DB.
        
        Output
            msg, any message
            status, whether or nor the test passes.
        
        '''
        username = user_seek['username']
        #print "__batchUploadTest", attributeInfo
        user_id = user_seek['user_id']
        
        print("sampleType: ", sampleType)
        #print "attributeMapping: ", attributeMapping

        msg0 = '<br/>'
        nright = 0
        nrow = 0
        statusTest = True
        diclist_new = []
        ndici = len(diclist)
        
        # in the meta-sample sheet, some samaples may have the same name, for example,
        # several tissues from same mouse, therefore, the MUS name is the same for several
        # rows of samples. Once a name is associated with a UID, such UID will be available
        # for next sample.
        # The format of uid_predefined
        uids_predefined = {}
        
        for index in range(ndici):
            dici = diclist[index]
            #print(dici)
            # Step A: add source UID into the child sample, if any
            if len(diclist_feedback)>0:
                # not the first sample for uploading thus diclist_feedback should not be empty
                dici_feedback = diclist_feedback[index]
                
                # add source sample UID into current sample record
                findParentUID = True
                for field, attribute in attributeMapping.items():
                    # such as
                    #   field = 'MUS::UID'
                    #   attribute = 'SourceSample'
                    if DELIMITER_DBFIELD in field and field in dici_feedback:
                        # such as field = 'MUS::UID'
                        # this is a foreign key
                        uid_from = dici_feedback[field]
                        if "Error" in uid_from:
                            findParentUID = False
                        else:
                            dici[attribute] = uid_from
                if not findParentUID:
                    # parent UID contains error beforehand thus do not continue uploading the current sample
                    msgi = SAMPLE_ERRORCODE['301']
                    #print(msgi)
                    #print('dici in error', dici)
                    statusTest = False
                    msg0 += msgi +  '<br/>'
                
                    header = sampleType + "::UID"
                    dici_feedback[header] = msgi
                    diclist_new.append(dici_feedback)
                    continue
            else:
                dici_feedback = {}
                
            # Step C: Add the current sample into the feedback list
            #dici_feedback += dici
            primaryField = sampleType + "::UID" # such as 'Cell UID', 'Lysate UID' etc, the UID field for a sample as a unique identifier.
            for header, attribute in attributeMapping.items():
                if attribute in dici:
                    dici_feedback[header] = dici[attribute]
                    # set empty for no error yet
                    #dici_feedback[header] = ''
                else:
                    #dici_feedback[header] = 'NA'
                    dici_feedback[header] = ''
                    
                if attribute=='UID':
                    primaryField = header   # such as 'Cell UID', 'Lysate UID' etc, which corresponds to the 'UID' field for a sample as a unique identifier.
            
            # Step B: Try to upload the current sample
            #print(dici)
            if 'Name' in dici:
                samplename = str(dici['Name'])
            elif 'File_PrimaryData' in dici:
                samplename = str(dici['File_PrimaryData'])
            elif 'File_PrimaryData_Forward' in dici:
                samplename = str(dici['File_PrimaryData_Forward'])
            elif 'File_PrimaryData_Reverse' in dici:
                samplename = str(dici['File_PrimaryData_Reverse'])
            else:
                #msgi = "Error: " + sampleType + " sample " + str(index) + " does not have either 'Name' or 'File_PrimaryData' attribute."
                msgi = SAMPLE_ERRORCODE['302'] + sampleType + " " + str(index)
                #print(msgi)
                #print('dici in error', dici)
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
                #msgi = "Error: " + sampleType + " sample " + str(index) + " has an empty name."
                msgi = SAMPLE_ERRORCODE['303']
                #print(msgi)
                #print('dici in error', dici)
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
                #msgi = "Error: " + sampleType + " sample " + str(index) + " has an empty name."
                msgi = SAMPLE_ERRORCODE['304']
                #print(msgi)
                #print('dici in error', dici)
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            
            #contributor_id = self.__queryContributorID(user_seek, scientist)
            contributor_id = user_id
            if contributor_id<=0:
                #msgi = "Error: " + sampleType + " sample " + str(index) + " has an empty name."
                msgi = SAMPLE_ERRORCODE['305'] + contributor
                #print(msgi)
                #print('dici in error', dici)
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                diclist_new.append(dici_feedback)
                continue
            
            if samplename in uids_predefined:
                # the sample name has been used for previous sample uploading thus the UID is already generated
                # therefore, for the same sample name by the same user, the UID should be the same too.
                dici['UID'] = uids_predefined[samplename]
            else:
                # Verify either UID is already defined and match the unique constraint
                sample_type_id = attributeInfo['sampleType_id']
                
                #msgi, statusi = self.__verifySampleUID(samplename, user_id, dici['UID'], sample_type_id)
                msgi, statusi = self.__verifySampleUID(samplename, contributor_id, dici['UID'], sample_type_id, scientist)
                if statusi==0:
                    statusTest = False
                    msg0 += msgi +  '<br/>'
                    dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                    diclist_new.append(dici_feedback)
                    print(msgi)
                    continue
                
                uidIn = dici['UID']
                if uidIn is not None and len(uidIn.strip())>0:
                    # Verify if the UID provided is valid,
                    #   a. the UID does not exist in the database so the sample record should be rejected
                    #   b. or even though the UID exists in the database, but it does not match the sample type
                    isValid, msgi = self.__verifyUID(uidIn, attributeInfo)
                    if not isValid:
                        # uidIn provided is invalid, return the error message
                        statusTest = False
                        msg0 += msgi +  '<br/>'
                        dici_feedback = self.__updateSampleErrorMsg(dici_feedback, primaryField, msgi, sampleType)
                        diclist_new.append(dici_feedback)
                        continue
            
            msgi, statusi, uid = self.__storeSample(user_seek, sampleType, dici, attributeInfo, diclist_assay, contributor_id)
                
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
                
            # such as 'MUS::UID' so it can be used for child sample    
            header = sampleType + "::UID"
            if statusi:
                dici_feedback[header] = uid
                dici_feedback[primaryField] = uid
            else:
                dici_feedback[header] = msgi
            diclist_new.append(dici_feedback)
                
        #print(dici)
        #print(dici_feedback)
        msg = 'The number of samples uploaded for ' + sampleType + ': ' + str(nright) + ' out of in total ' + str(ndici) + ' samples.'
        if not statusTest:
            msg = msg + '<br/>' + msg0
        else:
            msg = msg + '<br/>' + msg0
        
        return msg, statusTest, diclist_new
    
    def __batchUploadSampleTest(self, user_seek, sampleType, diclist_sample, diclist_feedback, attributeMapping, diclist_assay, uploadEnforced=False):
        ''' Upload a list of samples into one sample type table, given,
        Input
            username, the login user name.
            sampletype, the valid sample type title;
            diclist_sample, a list of dictionaries, whose keys should match attributeMapping of the sample type;
            diclist_feedback, with the source sample info, such as source sample UID etc.
            attributeMapping, the mapping between headers in Sample sheet and dbfields in sample hash, for the sample type specified.
        Output
            msg,
            status,
            diclist_feedback, with returned Valid UID for samples.
        '''
        username = user_seek['username']
        
        # Step 1. Get the sample type id, given sample type title/name:
        stype = DBtable_sampletype()
        sampletype_id = stype.getSampleTypeID(sampleType)
        if sampletype_id<=0:
            msg = SAMPLE_ERRORCODE['201'] + sampleType + " id: " + str(sampletype_id)
            print(msg)
            return msg, 0, diclist_feedback
    
        # Step 2. Get the list of pre-defined attributeMapping for a sample type.
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        if len(attributeInfo['headers'])==0:
            msg = SAMPLE_ERRORCODE['202'] + sampleType
            status = 0
            print(msg)
            return msg, status,diclist_feedback
        
        # Step 3. Verify the list of samples for uploading
        msg, status, diclist_feedback = self.__batchUploadTest(user_seek, sampleType, diclist_sample, diclist_feedback, attributeInfo, attributeMapping, diclist_assay, uploadEnforced)
        return msg, status, diclist_feedback


    def __outputUploadFeedback(self, diclist_feedback, headers, feedbackfile):
        ''' Output feedback from the batch upload of samples.
        Input:
            diclist_feedback, the list of dictionaries with everything in the Sample sheet
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
        
        for dici in diclist_feedback:
            row += 1
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
                sheet1.write(row, index, newitem)
                
        book.save(feedbackfile)
        
    def __outputUploadFeedback_V2(self, diclist, diclist_feedback, headers, feedbackfile):
        ''' Output feedback from the batch upload of samples.
        Input:
            diclist_feedback, the list of dictionaries with everything in the Sample sheet
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
        
        style = xlwt.easyxf('pattern: pattern solid, fore_colour red;')
        style0 = xlwt.Style.easyxf('pattern: pattern solid, fore_colour white;')
        #sheet.row(0).write(0, value, style0)
 
        i = 0
        #for dici in diclist_feedback:
        for dici in diclist:
            dici_feedback = diclist_feedback[i]
            row += 1
            for index, header in enumerate(headers):
                if header in dici:
                    newitem = dici[header]
                    #if 'http' in newitem:
                    #    newitem = self.__formatHttpLink(newitem)
                else:
                    #newitem = "N/A"
                    newitem = ""
                
                try:
                    newitem = str(newitem)
                except:
                    #newitem = cleanString(newitem)
                    newitem = toString(newitem)
                
                if header in dici_feedback:
                    feedback = dici_feedback[header]
                    if feedback is None:
                        sheet1.write(row, index, newitem)
                    elif 'Error' in toString(feedback):
                        feedback = feedback + ":" + newitem
                        sheet1.write(row, index, feedback, style)
                    elif 'UID' in header:
                        #term = newitem + ":" + feedback
                        #sheet1.write(row, index, term)
                        sheet1.write(row, index, feedback)
                    else:
                        sheet1.write(row, index, newitem)
                else:
                    sheet1.write(row, index, newitem)
                
            i += 1 
        book.save(feedbackfile)        
        
    def __batchUpdateSample(self, sheetData, feedbackfile, user_seek):
        ''' Batch update sample information
        Input:
            sheetData, the sample sheet with UID as the first column for updating sample info.
            user_seek, a dictionary with the login user info, such as,
                user_seek['server'],
                user_seek['storage'],
                user_seek['storagetype'],
                user_seek['username'],
                user_seek['password'],
                user_seek['noexpire'],
                user_seek['user_id'],
                user_seek['userdata'],
                user_seek['status'],
                user_seek['err']
                user_seek['projectid'], 0 or the first default project id, 
            

        '''
        username = user_seek['username']
        
        msg = "batchUpdate"
        status = 0
        
        # the list of samples for upload
        #sheetData = filedata['PUBLISH']
        headers = sheetData['headers']
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['104']
            status = 0
            print(msg)
            return msg, status
        
        headers.append('feedback')
        
        # Try to update the current samples
        username = user_seek['username']
        #print "__batchUploadTest", attributeInfo
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
                
            if 'UID' not in dici:
                msgi = 'UID not available for update'
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['feedback'] = msgi
                diclist_feedback.append(dici_feedback)
                continue
            
            uidIn = dici['UID']
            if uidIn is None or len(uidIn.strip())==0:
                msgi = 'UID not available for update'
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['feedback'] = msgi
                diclist_feedback.append(dici_feedback)
                continue
                
                
            # Verify if the UID provided is valid,
            #   a. the UID does not exist in the database so the sample record should be rejected
            #   b. or even though the UID exists in the database, but it does not match the sample type
            record = self.__retrieveSampleByUID(uidIn)
            if record is None:
                # customized UID is not found in DB, reject it
                # Notes that this UID is not the one generated automatically in __getRecord()
                msgi = "Error: Sample UID " + uidIn + " does not exist in DB for update "
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['feedback'] = msgi
                diclist_feedback.append(dici_feedback)
                continue
                       
            username = user_seek['username']
            user_id = user_seek['user_id']
            
            json_metadata = record['json_metadata']
            dici_json = self.__getRecordFromJson(json_metadata)
            
            # update the json 
            #for key, elem in dici.items():
            #    keynow = key.lower()
            #    dici_json[keynow] = elem
            
            metadata_db = dici_json
            metadata_in = dici
            metadata_out = self.__updateSampleMetadata(metadata_db, metadata_in)
            dici_json = metadata_out
                
            #Convert dictionary back to json
            json_metadata_updated = simplejson.dumps(dici_json)
            record['json_metadata'] = json_metadata_updated
        
            other_creators = record['other_creators']
            if other_creators is None:
                record['other_creators'] = username
            else:
                record['other_creators'] = other_creators + ';' + username

            record['updated_at'] = getDefaultDateTime()

            #print(record_new)
            #return 'Upload to be enforced', 1, uid   
            msgi, statusi, sample_id = self.storeOneRecord(username, record)
            nrow += 1
            if statusi:
                msg0 += uidIn + ": " + msgi +  '<br/>'
                nright += 1
                dici_feedback['feedback'] = 'successful'
            else:
                statusTest = False
                msg0 += msgi +  '<br/>'
                dici_feedback['feedback'] = msgi

            diclist_feedback.append(dici_feedback)
                
        #print(dici)
        #print(dici_feedback)
        msg = 'The number of samples updated: ' + str(nright) + ' out of in total ' + str(ndici) + ' samples.'
        if not statusTest:
            msg = msg + '<br/>' + msg0
            status = 0
        else:
            msg = msg + '<br/>' + msg0
            status = 1
                
        #self.__outputUploadFeedback(diclist_feedback, headers, feedbackfile)
        self.__outputUploadFeedback_V2(diclist, diclist_feedback, headers, feedbackfile)
        return msg, status
        
        
    def batchUpload(self, infile, feedbackfile, user_seek):
        '''
        Input:
            infile, posted in http for uploading, which could be either a csv or excel file. 
            user_seek, a dictionary with the login user info, such as,
                user_seek['server'],
                user_seek['storage'],
                user_seek['storagetype'],
                user_seek['username'],
                user_seek['password'],
                user_seek['noexpire'],
                user_seek['user_id'],
                user_seek['userdata'],
                user_seek['status'],
                user_seek['err']
                user_seek['projectid'], 0 or the first default project id, 
            

        '''
        username = user_seek['username']
        
        msg = "batchUpload"
        status = 0
        
        # Step 1. Load the input excel file
        try:
            filedata = load_excelfile_asdic(infile)
        except:
            msg = SAMPLE_ERRORCODE['101']
            status = 0
            print(msg)
            return msg, status
        
        # Step 2. Verify the input Sample sheet
        status = filedata['status']
        msg = filedata['msg']
        if status==0:
            msg = SAMPLE_ERRORCODE['106'] + msg
            print(msg)
            return msg, status
        
        print(filedata['sheetnames'])
        
        if 'UPDATE' in filedata['sheetnames'] and 'UPDATE' in filedata:
            sheetData = filedata['UPDATE']
            if "ONTOLOGY" not in filedata or "INSTRUCTIONS" not in filedata:
                # no Ontology check available, ignore Ontology check
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
                    print(msg)
                    return msg, status
                else:
                    msg = 'Error: Refer to the feedback excel file for vialation in controlled Ontology terms.'
                    ontology.outputOntologyFeedback(diclist_up, headers, feedbackfile, ontology_feedback)     
                    return msg, status
            
            return self.__batchUpdateSample(sheetData, feedbackfile, user_seek)
        
        status = 1
        for sheetname in SAMPLE_SHEET_NAMES:
            msg = SAMPLE_ERRORCODE['102']
            if sheetname not in filedata['sheetnames'] or sheetname not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                print(msg)
                return msg, status
        
        print "Step 3. Load intruction sheet"
        sheetData_ins = filedata["INSTRUCTIONS"]
        diclist_ins = sheetData_ins['diclist']
        sampleTypes, sampleTypes_order = self.__loadSampleTypes(diclist_ins)
        if len(sampleTypes.keys())==0:
            msg = SAMPLE_ERRORCODE['103']
            status = 0
            print(msg)
            return msg, status
        
        # Assay sheet
        sheetData_assay = filedata["ASSAY"]
        diclist_assay = sheetData_assay['diclist']
        
        # the list of samples for upload
        sheetData = filedata["SAMPLES"]
        headers = sheetData['headers']
        diclist = sheetData['diclist']
        if len(diclist)<1:
            msg = SAMPLE_ERRORCODE['104']
            status = 0
            print(msg)
            return msg, status
        
        print "Load Ontology sheet"
        sheetData_ont = filedata["ONTOLOGY"]
        diclist_ont = sheetData_ont['diclist']
        
        ontology = DBtable_ontology()
        msg, status, ontology_feedback = ontology.evaluateOntology(diclist, diclist_ins, diclist_ont)
        if status==0:
            if len(ontology_feedback)==0:
                print(msg)
                return msg, status
            else:
                msg = 'Error: Refer to the feedback excel file for vialation in controlled Ontology terms.'
                ontology.outputOntologyFeedback(diclist, headers, feedbackfile, ontology_feedback)     
                return msg, status
        
        # Step 4. Split meta-sample sheet into individual single sample sheets
        sample_sheets = self.__splitSampleTypes(sampleTypes, diclist)
        # Step 5. Upload individual single sample sheet
        
        msg = ""
        diclist_feedback = []
        for sampleType in sampleTypes_order:
            if sampleType in sample_sheets:
                diclist_sample = sample_sheets[sampleType]
                attributeMapping = sampleTypes[sampleType]

                # Try to upload the current sample
                msgi, statusi, diclist_feedback = self.__batchUploadSampleTest(user_seek, sampleType, diclist_sample, diclist_feedback, attributeMapping, diclist_assay)                
                msg += msgi + "<br/>"
                if not statusi:
                    status = 0
            else:
                msgi = SAMPLE_ERRORCODE['105'] + sampleType
                status = 0
                #print msg
                msg += msgi + "<br/>"
                #return msg, status
                
        #self.__outputUploadFeedback(diclist_feedback, headers, feedbackfile)
        self.__outputUploadFeedback_V2(diclist, diclist_feedback, headers, feedbackfile)
        return msg, status
    
    def __getSampleUrl(self, id):
        url = "<a href='/seek/sample/id=" + str(id) + "/'  target='_blank'>" + str(id) + "</a>"
        return url
    
    def search(self, uids, orderby, limit):
        #Wga_cell, Wga_cell_status, Wga_cell_ulp
        print "search"
        
        total = len(uids)
        rdata = []
        if total==0:
            data = {'total':total,'rows':rdata}
            sdata = simplejson.dumps(data)
            return sdata
        
        qset = Q(uuid__in=uids)
        # Step 1. Retrieve records in DB tabel
        rdata = self.db.retrieveJoint(self.tablemodel, '', qset, orderby, limit)
        rdata = convertDateListToString('created_at', rdata)
        rdata = convertDateListToString('updated_at', rdata)
        
        for datai in rdata:
            id = datai['id']
            datai['id'] = self.__getSampleUrl(id)
        
        total = len(rdata)
        
        data = {'total':total,'rows':rdata}
        sdata = simplejson.dumps(data)
        return sdata
        
        total = self.db.retrieveTotalRecords(self.tablemodel)
    
        data = {'total':total,'rows':rdata}
        cellData = simplejson.dumps(data)
        #print cellData
        msg = "DBtable_cell __retrieveCellJoint:return CellData"
        logger.debug(msg)
        return cellData
    
    def childTube(relation):
        ''' Infinite loop to look for the child tube.
        relation = {
            u'status': u'',
            u'run_id': u'e72dfa22843741e8a45b0676a29f3aa2',
            u'notes': u'',
            u'date': datetime.date(2015, 5, 29),
            u'child_2dtube_id': 120L,
            u'child_tube2dcode': u'FC14254823',
            u'child_cell_id': 0L
            u'child_cell_id_inherited': 790L,
            u'child_celltype': u'CTC',
            u'child_tube2dtype': None,
            u'child_date': datetime.date(2015, 5, 29),
            u'child_notes': u'',
            u'child_status': u'',
            u'child_concentration': 5.8,
            u'child_volume': 0.0,
        }
        '''
        child = {}
        child["name"] = "bcdf"

        #name = str(relation['notes']) + ': ' + str(relation['child_tube2dcode'])
        name = str(relation['child_tube2dtype']) + ': ' + str(relation['child_tube2dcode'])
        #name += ',' + str(relation['date']) 
        child["name"] = name
        next_children = []
    
        next_child_2dtube_id = relation['child_2dtube_id']
    
        if next_child_2dtube_id is None:
            print " No next child is found"
        else:
            next_relations = derive2DTubes(next_child_2dtube_id)
            for next_relation in next_relations:
                #print next_relation
                next_child_2dtube_id = next_relation['child_2dtube_id']
                if next_child_2dtube_id is None:
                    print 'No child is found'
                else:
                    #child={"name":name, "children":children}
                    next_child = childTube(next_relation)
                    next_children.append(next_child)
        
        child["children"] = next_children   
        return child
    
    
    
    def createSampleTree(self, sample_id):
        ''' Create a hierarchical tree of samples, given
        Input:
            sample_id, the id of a sample.
            
        Output
            tree, in the following format,
        
        
        '''
        #return self.createSampleChildrenTree(sample_id)
        
        #return hierarchyExample3()
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        #print('record:',record)
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        uids =  self.__getParentUIDs(dici)
        parentinfo, treeData = self.__trackParent(childuid, uids)
        return treeData
        
        
        
        name =  celldic['cellcode']
        if celldic['tube2dtype'] is not None:
            name += ": " + celldic['tube2dtype']
        if celldic['tube2dcode'] is not None:
            name += ": " + celldic['tube2dcode']

        treeData = {}
        treeData["name"] = str(name)
        treeData["info"] = str(celldic['tube2ddate'])
        treeData["level"] = "red"
    
        tube2did = celldic['tube2did']
        children = []
        if tube2did is None:
            # just for fun
            #children = [
            #    {"name" : "A311" },
            #    {"name" : "A312" }
            #]
            children = []
        else:
            relations = derive2DTubes(tube2did)
            for relation in relations:
                #print relation
                child_2dtube_id = relation['child_2dtube_id']
                if child_2dtube_id is None:
                    print 'No child is found'
                else:
                    #child={"name":name, "children":children}
                    child = childTube(relation)
                    children.append(child)
        
        treeData["children"] = children 
        #treeData = sampledata()
        return treeData
        

    def __retrieveSampleByUID(self, uid):
        ''' Given a UID for a sample, retrieve the record from DB.
        Input:
            uid, the UID for a sample
        
        Output:
            record, from Samples table, plus the sample meta info.     
        
        '''
        record = None
        if uid is None or len(uid.strip())==0:
            msg = 'No record is found based on the input UID: ' + uid
            print(msg)
            return None
        
        constraint = {'uuid':uid}
        records = self.queryRecordsByConstraint(constraint)
        if len(records)==1:
            record = records[0]
        
        return record
    
    def getSampleID(self, uid):
        ''' Given a UID for a sample, retrieve the sample id from DB.
        Input:
            uid, the UID for a sample
        
        Output:
            sample_id    
        '''
        sample_id = None
        record = self.__retrieveSampleByUID(uid)
        if record is not None:
            sample_id = record['id']
            
        return sample_id
        
 
    def __retrieveSampleByID(self, idIn):
        ''' Given a ID for a sample, retrieve the record from DB.
        Input:
            uid, the ID for a sample
        
        Output:
            record, from Samples table, plus the sample meta info.     
        
        '''
        record = None
        try:
            id = int(idIn)
        except:
            msg = 'No record is found based on the input ID: ' + idIn
            print(msg)
            return None
        
        #if id is None or len(id.strip())==0:
        if id<=0:
            msg = 'No record is found based on the input ID: ' + idIn
            print(msg)
            return None
        
        constraint = {'id':id}
        records = self.queryRecordsByConstraint(constraint)
        if len(records)==1:
            record = records[0]
        
        return record           
        
    def __getSeeklink(self, seek_type, id):
        ''' Get the web link for downloading a SOP based on,
        
        Input:
            seek_type, ='samples', 'sops' etc
            id, the primary key in sobs table for the SOP, also the asset_id in content_blob table.
        
        Output:
            Seek link, a url for finding the file in Seek DB, such as
                http://seekserver/sops/12/
                
        '''
        seek_url = settings.SEEK_URL + "/" + seek_type + "/" + str(id) + "/"
        #seeklink = '<a href="' + seek_url + '" target="_blank">' + originalfilename + '</a>'
        seeklink = '<a href="' + seek_url + '" target="_blank">' + str(id) + '</a>'
        return seeklink
        
    def __getSamplelink(self, sample_uid, sample_id):
        ''' Get the web link for downloading a SOP based on,
        
        Input:
            sample_uid, sample UID, such as 'A.MSP-20200225-27'.
            sample_id, the primary key in sobs table for the SOP, also the asset_id in content_blob table.
        
        Output:
            sample link, a url for finding the sample in DMAC, such as
                http://dmacserver/seek/sample/id=27/
                
        '''
        sample_url = "/seek/sample/id=" + str(sample_id) + "/"
        samplelink = '<a href="' + sample_url + '" target="_blank">' + str(sample_uid) + '</a>'
        return samplelink
    
        
    def reformatDataForClient(self, jdata):
        ''' Reformat the list of records for shown on dataGrid Table.
        Input
            jdata=[record1, record2,...], a list of records
            
        Output
            jdata_new, a revised list of records.
            
        Notes
            This is a virtual method provided for overridinng in the child class, for example,
        '''
        jdata_new = []
        for data in jdata:
            #print(data)
            #datadicc = data
            
            datadic = {}
            datadic['idlink'] = self.__getSeeklink('samples', data['id'])
            datadic['id'] = data['id']
            datadic['title'] = data['title']
            datadic['uuid'] = data['uid']
            datadic['uid'] = self.__getSamplelink(data['uid'], data['id'])
            datadic['sample_type_id'] = data['sample_type_id']
            datadic['contributor_id'] = data['contributor_id']
            datadic['created_at'] = str(data['created_at'])
            datadic['json_metadata'] = str(data['json_metadata'])
            #datadic['fileurl'] = self.__getWeblink(data['title'])
            #datadic['id'] = self.__getSeeklink('', data['id'])
            
            # the following are from joint query
            datadic['sample_type'] = data['sample_type']
            datadic['first_name'] = data['first_name']
            datadic['assays'] = data['assays']
            
            jdata_new.append(datadic)
        
        #jdata_new = jdata
        return jdata_new
    
    def retrieveRecords(self, user_seek, filtersdic):
        ''' Retrieve a list of records and show is in a dataGrid on the front page,
            from a single Django model/table.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            filtersdic, filter parameters from the dataGrid.
            
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
       
        '''
        return self.retrieveRecords_joint(user_seek, filtersdic)
        
        jdata, footer, total = self.db.retrieve_table_list(self.tablemodel, self.primaryField, filtersdic, self.fieldMapping)
        print('total:', total)
        jdata_new = self.reformatDataForClient(jdata)
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data
    
    def __sqlQuery_select_records_filters(self, filtersdic):
        ''' Generate SQL query filters basedon the parameters from DataGrid on front GUI.
        Input
            where_clause = " WHERE " or " WHERE a=b AND "
        
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        Output
            sqlquery_filters = " WHERE xxxx=yyy..."
            
        Examples:
            sqlquery_filter = "" if filterRules={};
            sqlquery_filter = " WHERE a=b AND ..." if filterRules!={};
        '''
        filterRules = filtersdic['filterRules']     # such as [{"field":"unit","op":"contains","value":"Amon"}]
        sqlquery_filter = ""
        n = 0
        for rule in filterRules:
            #print rule
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
        
        #sqlquery_select +=  "D.assay_id as assay_id,"
        #sqlquery_select +=  "E.title as assayname,"
        #sqlquery_select +=  "F.work_group_id as work_group_id,"
        #sqlquery_select +=  "G.project_id as project_id,"
        #sqlquery_select +=  "G.institution_id as institution_id,"
        #sqlquery_select +=  "H.title as projectname,"
        #sqlquery_select +=  "I.title as institution"
        
        return sqlquery_select
    
    def __sqlQuery_select_records_from(self):
        '''
        sqlquery_from =  " FROM "   
        sqlquery_from +=  "seek_production.samples A "
        sqlquery_from +=  "left join seek_production.sample_types B on A.sample_type_id=B.id "
        sqlquery_from +=  "left join seek_production.people C on A.contributor_id=C.id "
        sqlquery_from +=  "left join seek_production.assay_assets D on A.id=D.asset_id "
        sqlquery_from +=  "left join seek_production.assays E on E.id=D.assay_id "
        
        sqlquery_from +=  "left join seek_production.group_memberships F on C.id=F.person_id "
        sqlquery_from +=  "left join seek_production.work_groups G on G.id=F.work_group_id "
        sqlquery_from +=  "left join seek_production.projects H on H.id=G.project_id "
        sqlquery_from +=  "left join seek_production.institutions I on I.id=G.institution_id "
        '''
        sqlquery_from =  " FROM "   
        sqlquery_from +=  "samples A "
        sqlquery_from +=  "left join sample_types B on A.sample_type_id=B.id "
        sqlquery_from +=  "left join people C on A.contributor_id=C.id "
        
        #sqlquery_from +=  "left join assay_assets D on A.id=D.asset_id "
        #sqlquery_from +=  "left join assays E on E.id=D.assay_id "
        #sqlquery_from +=  "left join group_memberships F on C.id=F.person_id "
        #sqlquery_from +=  "left join work_groups G on G.id=F.work_group_id "
        #sqlquery_from +=  "left join projects H on H.id=G.project_id "
        #sqlquery_from +=  "left join institutions I on I.id=G.institution_id "
        return sqlquery_from     
    
    def __sqlQuery_select_records(self, filtersdic, withLimit=True): 
        '''
        Refer to: http://stackoverflow.com/questions/603724/how-to-implement-limit-with-microsoft-sql-server
        Valid in MySQL only for limit=' LIMIT 1000,50 ', where 1000 is offset and 50 is the number of rows next to pull.

            SELECT t1.*
            FROM (
                SELECT ROW_NUMBER OVER(ORDER BY id) AS row, t1.*
                FROM ( ...original SQL query... ) t1
            ) t2
            WHERE t2.row BETWEEN @offset+1 AND @offset+@count;
        
        Retrieve all active grants.
            Input
                filtersdic, all filtering parameters
                withLimit, true, put a limit on the SQL query with start and end number;
                           false, put no limit on the SQL query, so without start and end number;
            Output
                A SQL query used for retrieving records.
                
            SELECT *
            FROM [FacultyGrantSupport].[dbo].[view_GrantComponent]
            where GrantComponentStatusPK='02'
            order by [GrantPK]
        '''
        # The original SQL query        
        sqlquery_select = self.__sqlQuery_select_records_select()
        
        sqlquery_from = self.__sqlQuery_select_records_from()
        
        orderby = filtersdic['orderby'] # such as " ORDER BY id asc " or " ";
        startNo = filtersdic['startNo'] # such as 1000;
        endNo = filtersdic['endNo']     # such as 1050;
        sqlquery_where = self.__sqlQuery_select_records_filters(filtersdic)
        #if len(sqlquery_where)==0:
        #    sqlquery_where = " WHERE D.asset_type='Sample' "
        #else:
        #    sqlquery_where += " AND D.asset_type='Sample' "
        
        sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where
        
        if len(orderby)==0:
            orderby = " ORDER BY A.id desc"
        
        if withLimit:
            #sqlqueryMega = self.dbconn.sqlQuery_select_limit(sqlquery_select, sqlquery_from, orderby, startNo, endNo)
            sqlqueryMega = sqlquery_select + sqlquery_from + sqlquery_where + orderby
        else:
            #sqlqueryMega = self.dbconn.sqlQuery_select_limit(sqlquery_select, sqlquery_from, orderby, 0, 0)
            #sqlqueryMega = " SELECT count(c.GrantComponentPK) " + sqlquery_from
            sqlqueryMega = " SELECT count(A.id) " + sqlquery_from
        
        print sqlqueryMega
        return sqlqueryMega
    
    def retrieveRecords_joint(self, user_seek, filtersdic):
        ''' Retrieve a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            filtersdic, filter parameters from the dataGrid.
            
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        #sqlquery = self.__sqlQuery_select_allgrants_limit(orderby, startNo, endNo)
        print('filterRules:', filtersdic['filterRules'])
        
        sqlquery = self.__sqlQuery_select_records(filtersdic)
        headers = SAMPLE_HEADERS
        # retrieve records from SEEK DB, rather than the default DB
        db_alias = settings.SEEK_DATABASE
        jdata = self.db.queryToListDics(sqlquery, headers, db_alias)
        #datalist = self.dbconn.retrieveAllRecords(sqlquery)
        #print datalist[0]
        
        sqlquery = self.__sqlQuery_select_records(filtersdic, False)
        total = self.db.getQueryValue(sqlquery, db_alias)
        print("Total number of records retrieved: ", total)
        if total is None:
            total = 0
        else:
            total = int(total)
    
        #jdata, footer, total = self.db.retrieve_table_list(self.tablemodel, self.primaryField, filtersdic, self.fieldMapping)
        #print('total:', total)
        jdata_new = self.reformatDataForClient(jdata)
        footer = []
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data

    def __getParentUIDs(self, sampleDic):
        ''' Get a list of parent sample UIDs, given
        Input:
            sampleDic, the dictionary of a sample, such as
             {
                'title':'12',
                'CreatedFromSample':'2345678',
                'uuid':'123456',
                'contributor_id':0,
                'created_at':''
            }
            
        Output:
            uids = [], a list of parent sample UIDs.
            
        Requirement:
            In this fucntion, the approach in identifying a parent sample is based the keyword:
                SAMPLE_PARENT_IDENTIFIER="CreatedFromSample"
            which requires the attribute name predefined for the parent UID. Obviously, this requirement
            is not an ideal solution.
            
            An ideal solution should be based on the attribute type as "SEEK Strain" or "SEEK Sample",
            regardless the name used for an attribute.
        
        '''
        #print("__getParentUIDs:", sampleDic)
        uids = []
        for key, value in sampleDic.iteritems():
            if SAMPLE_PARENT_ACCESSOR_NAME in key:
                if value is None:
                    continue
                else:
                    if ";" in value:
                        #parent uids could be ";" delimited string
                        vis = value.split(";")
                        for vi in vis:
                            vi = vi.strip()
                            if len(vi)>0:
                                uids.append(vi)
                    else:
                        #print('value.strip():', key, value)
                        value = value.strip()
                        if len(value)>0:
                            uids.append(value)
                
        return uids
    
    def __getParents(self, childuid):
        ''' Retrieve parent samples, given
        Input:
            childuid, the uid for a child sample
            
        Output
            parent_uids=[uid1, uid2, ...], a list of parent uids.
        
        '''
        record_db = self.__retrieveSampleByUID(childuid)
        if record_db is None:
            return []
            
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        uids = self.__getParentUIDs(sampleDic)
        return uids

    def __getParentLoop(self, childuid):
        ''' Get all parent uids, given
        Input:
            childuid, the uid for a child sample.
            
        Output:
            a hierarchy of the all parent samples.
        '''
        print('__getParents:' , childuid)
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
        ''' Track the information of parent samples, back to the original sample, geven
        Input:
            childuid, the uid for the current sample, i.e., the child sample, for which all ancestor samples are to be tracked.
            parent_uids = [uid1, uid2,...], a list of parent uids for the current child sample.
            
        Output:
            The reverse hierachical tree of the parent samples, from the current child sample, back to all the ancestor parent samples.
            
            A string, such as uid1:uid2:uid3:..., a sequential UIDs back to the original very first sample.
        '''
        print("__trackParent", childuid, parent_uids)
        
        # this is not a children tree but actually a parents tree.
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
        print("treeData:", treeData)
        #return treeData
        return parentinfo, treeData
        

    def __filterSamples(self, jdata, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Filter a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        if filter_rule=='No Filter':
            return jdata
        
        # this is the key used in the json_metadata
        accessor_name = attribute.lower().strip()
        
        # Step 1. get the list of values used for filtering
        values = []     # the list of attribute used for filtering
        parentUIDs = []    # the list of attribute used for finding parent samples
        n = 0
        for data in jdata:
            json_metadata = data['json_metadata']
            dici = self.__getRecordFromJson(json_metadata)
            
            # get the value for filtering
            if accessor_name not in dici:
                value = None
            else:
                value = dici[accessor_name]
            values.append(value)
            
            # get the parent sample UIDs
            uids = self.__getParentUIDs(dici)
            parentUIDs.append(uids)
            
            n += 1
        print("Number of samples before filtering: ", n, values)
        
        # Step 2. Filter the list of values 
        sattr = DBtable_sampleattribute()
        passvalues = sattr.filterValues(values, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
        
        # Step 3. Output those samples that pass the filter
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
                #data['parent_uids'] = parentinfo
                data['parent_uids'] = ';'.join(uids)
                print('parent_uids: ', data['parent_uids'])
                jdata_new.append(data)
                ni += 1
            #elif passit is None:
            #    jdata_new.append(data)
            index += 1
        
        print("Number of samples after filtering: ", ni)
        return jdata_new
    
    def searchSamples(self, user_seek, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
            
            filtersdic, filter parameters from the dataGrid.
            
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            print("validateFilters:", msg)
            if status==0:
                data = {'msg':msg, 'status': status}
                reportData = simplejson.dumps(data)
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
        
        reportData = simplejson.dumps(data)
        return reportData
    
    def __getChildrenUIDs(self, currentuid):
        ''' Get children UIDs, given
        Input:
            currentuid, the uid for the current sample.
            
        Output:
            a list of sample UIDs, who are created from the current sample.
            
        How to implement?
        
        A parent sample is defined in the json_metadata of a child sample.
        However, when we search for the parent sample UID, i.e., the currentid, such as "CEL-200225WHI-1",
        the Django query self.db.retrieveRecords() returns a list of records, whose json_metadata
        contains the the currentid, such as "CEL-200225WHI-1", or
            "CEL-200225WHI-13",
            "CEL-200225WHI-134"
            "CEL-200225WHI-1;CEL-200225WHI-13",
            "CEL-200225WHI-2;CEL-200225WHI-1",
            "CEL-200225WHI-2;CEL-200225WHI-1;CEL-200225WHI-3",
            
        therefore, we have to find all those uids and exclude those samples whose parent sample UID is not the currentid.
        
        Usage:
            Also refer to self.__getSampleChildren(currentuid), which return a list of children IDs and UIDs.
        '''
        print("__getChildrenUIDs:", currentuid)
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', currentuid)
        uids = []
        for record in records:
            uid = record['uuid']
            #if uid!=currentuid:        # this causes error because this record might contain "CEL-200225WHI-13", as the parent sample, rather than "CEL-200225WHI-1",
            #    uids.append(uid)
            
            metadata = record['json_metadata']
            sampleDic = self.__getRecordFromJson(metadata)
            parent_uids = self.__getParentUIDs(sampleDic)
            if currentuid in parent_uids:
                uids.append(uid)
            
        return uids
    
    def __getChildLoop(self, parentuid):
        ''' Get all parent uids, given
        Input:
            parentuid, the uid for a child sample.
            
        Output:
            a hierarchy of the all parent samples.
        '''
        print('getChildLoop:' , parentuid)
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
        ''' Create a hierarchical tree of samples, given
        Input:
            sample_id, the id of a sample.
            
        Output
            tree, in the following format,
        '''
        return self.createSampleChildrenTreeParallel(sample_id)
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        #print('record:',record)
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
        print("treeData:", treeData)
        #return treeData
        return treeData
    
    def createSampleChildrenTreeParallel_i(self, uid):
        child = self.__getChildLoop(uid)
        return child
    
    def createSampleChildrenTreeParallel(self, sample_id):
        ''' The parallel version of self.createSampleChildrenTree()
        
        Create a hierarchical tree of samples, given
        Input:
            sample_id, the id of a sample.
            
        Output
            tree, in the following format,
        '''
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        #print('record:',record)
        currentuid = record['uuid']
        children_uids =  self.__getChildrenUIDs(currentuid)
        
        treeData = {}
        treeData["name"] = str(currentuid)
        treeData["id"] = str(currentuid)
        
        children = []
        #for uid in children_uids:
        #    child = self.__getChildLoop(uid)
        #    children.append(child)
            
        num_cores = multiprocessing.cpu_count()
        n = len(children_uids)
        #childs = Parallel(n_jobs=num_cores)(delayed(unwrap_self_createSampleChildrenTreeParallel_i)(i) for i in zip([self]*n, children_uids))
        childs = Parallel(n_jobs=-2, backend="threading")\
            (delayed(unwrap_self_createSampleChildrenTreeParallel_i)(i) for i in zip([self]*n, children_uids))

        for child in childs:
            children.append(child)

        if len(children)>0:
            treeData["children"] = children
        print("treeData:", treeData)
        #return treeData
        return treeData
    
    
    def __getParentTreeListLoop(self, childNode):
        ''' Reconstructe parent tree recursively, given
        Input:
            childNode, = {'id':uid, 'name':uid, 'children':child}, a cild node
            
        Output:
            upTreeList, = [{'id':uid, 'name':uid, 'children':children},{},...], a parent tree.
        '''
        upTreeList = []
        
        childuid = childNode['id']
        
        # for test on the first layer, stop here
        #upTreeList.append(childNode)
        #return upTreeList
        
        parent_uids = self.__getParents(childuid)
        if parent_uids is None or len(parent_uids)==0:
            # no more parent node, return the current one as the top prent
            upTreeList.append(childNode)
            return upTreeList
        
        #Otherwise, build the parent tree
        for uid in parent_uids:
            uid = str(uid)
            node = {'id':uid, 'name':uid, 'children':[childNode]}
            parentTreeList = self.__getParentTreeListLoop(node)
            upTreeList += parentTreeList
            
        # it's not working yet
        return upTreeList
    
    def __trackParentTreeList(self, childuid, parent_uids):
        ''' Track the information of parent samples, back to the original sample, geven
        Input:
            childuid, the uid for the current sample, i.e., the child sample, for which all ancestor samples are to be tracked.
            parent_uids = [uid1, uid2,...], a list of parent uids for the current child sample.
            
        Output:
            upTreeList = [
                parentTree_1,
                parentTree_2,
                ...
            ],
            where
                parentTree_i = {'name':name, 'id', id, 'children':[]}
        '''
        #print("__trackParent", childuid, parent_uids)
        
        upTreeList = []
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        if len(parent_uids)==0:
            upTreeList.append(child)
            return upTreeList
        
        # this is not a children tree but actually a parents tree.
        for uid in parent_uids:
            uid = str(uid)
            childNode = {'id':uid, 'name':uid, 'children':[child]}
            parentTreeList = self.__getParentTreeListLoop(childNode)
            upTreeList += parentTreeList
            
        # it's not working yet
        return upTreeList
    
    def __createMultiParentTree(self, sample_id, includeChilren):
        ''' Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_id, the id of a sample.
            includeChilren, True, children from the current sample are also included in the tree;
                            False, no child is included in the tree.
            
        Output
            actualTreeList, a list of top parent nodes with recursive children nodes, such as
                =[{
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }]
        
                which looks like,
                     ________
                    B         \
                              |_______A
                    C________/
        
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        '''
        return self.__createMultiParentTreeParallel(sample_id, includeChilren)
        
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        # Step 1. Get all parent uids for the current sample
        #print('record:',record)
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        parent_uids =  self.__getParentUIDs(dici)
        
        # get the current node, if we don't want to include children tree
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        
        # Step 2. get the children tree from the current sample
        # such as {'name':name, 'id':id, 'children':children}
        if includeChilren:
            child = self.createSampleChildrenTree(sample_id)
        
        # Step 3. get the parents tree
        upTreeList = []
        if len(parent_uids)==0:
            upTreeList.append(child)
        else:
            # this is not a children tree but actually a parents tree.
            for uid in parent_uids:
                uid = str(uid)
                childNode = {'id':uid, 'name':uid, 'children':[child]}
                parentTreeList = self.__getParentTreeListLoop(childNode)
                upTreeList += parentTreeList
        
        return upTreeList
    
    def createMultiParentTreeParallel_i(self, uid, child):
        '''Used in the parallel version of self.__createMultiParentTree().

        '''
        #print("createMultiParentTreeParallel_i:", uid)
        
        uid = str(uid)
        childNode = {'id':uid, 'name':uid, 'children':[child]}
        parentTreeList = self.__getParentTreeListLoop(childNode)
        return parentTreeList
    
    def __createMultiParentTreeParallel(self, sample_id, includeChilren):
        '''The parallel version of self.__createMultiParentTree()
        
        Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_id, the id of a sample.
            includeChilren, True, children from the current sample are also included in the tree;
                            False, no child is included in the tree.
            
        Output
            actualTreeList, a list of top parent nodes with recursive children nodes, such as
                =[{
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }]
        
                which looks like,
                     ________
                    B         \
                              |_______A
                    C________/
        
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        '''
        
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        # Step 1. Get all parent uids for the current sample
        #print('record:',record)
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        parent_uids =  self.__getParentUIDs(dici)
        
        # get the current node, if we don't want to include children tree
        childuid = str(childuid)
        child = {'id':childuid, 'name':childuid}
        
        # Step 2. get the children tree from the current sample
        # such as {'name':name, 'id':id, 'children':children}
        if includeChilren:
            child = self.createSampleChildrenTree(sample_id)
        
        # Step 3. get the parents tree
        
        upTreeList = []
        if len(parent_uids)==0:
            upTreeList.append(child)
        else:
            #for uid in parent_uids:
            #    uid = str(uid)
            #    childNode = {'id':uid, 'name':uid, 'children':[child]}
            #    parentTreeList = self.__getParentTreeListLoop(childNode)
            #    upTreeList += parentTreeList
            
            # this is not a children tree but actually a parents tree.
            num_cores = multiprocessing.cpu_count()
            n = len(parent_uids)
            
            #print(parent_uids)
            #for i in zip([self]*n, parent_uids, [child]*n):
            #    print(i)
            #parentTreeLists = Parallel(n_jobs=num_cores)(delayed(unwrap_self_createMultiParentTreeParallel_i)(i) for i in zip([self]*n, parent_uids, [child]*n))
            parentTreeLists = Parallel(n_jobs=-2, backend="threading")\
                (delayed(unwrap_self_createMultiParentTreeParallel_i)(i) for i in zip([self]*n, parent_uids, [child]*n))
            
            # if don't use parallel
            #parentTreeLists = [unwrap_self_createMultiParentTreeParallel_i(i) for i in zip([self]*n, parent_uids, [child]*n)]

            for parentTreeList in parentTreeLists:
                upTreeList += parentTreeList
        
        return upTreeList
    
    def __getChildrenListLoop(self, parentTreeData):
        ''' Convert a parent tree data into a list for saving into a csv file.
        
        Input:
            parentTreeData, a list of top parent nodes with recursive children nodes, such as
                =[{
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }]
        
                which looks like,
                     ________
                    B         \
                              |_______A
                    C________/
            
        Output:
            listlists, a list of lists, good for csv export, which covers all possible combinations of parent-child relationships.
            
        Examples:
            Given, treeData,
                     ________
                    B         \
                              |_______A
                    C________/
            
            Output =[
                {B,A},
                {C,A}
            ]
            
            
            Given, treeData,
                     ________
                    B         \     ________E___
                               D---/            \_____________A
                                   \________F___/
                                               /
                                              /
                    C________________________/
            
            Output =[
                [B,D,E,A],
                [B,D,F,A],
                [C,    A]
            ]
        '''
        
        listlists = []
        for node in parentTreeData:
            if 'children' in node:
                children = node['children']
            
                # such as [
                #    [E,A],
                #    [F,A]
                #]
                sublists = self.__getChildrenListLoop(children)
            else:
                sublists = [[]]
            
            uid = node['id']
            # now make it this way,
            # such as [
            #    [D, E, A],
            #    [D, F, A]
            #]
            for listi in sublists:
                newlist = [uid] + listi
                listlists.append(newlist)
        
        return listlists
        
    
    def createSampleMultiParentTree(self, sample_id):
        ''' Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_id, the id of a sample.
            
        Output
        reversed treeData, such as two parents with one child,
            multi_parents_tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        '''
        #return hierarchyExample3()
        
        includeChilren = True
        fullTreeList = self.__createMultiParentTree(sample_id, includeChilren)
        
        if fullTreeList is None:
            multi_parents_treeData = {
                #'name': "certificates",
                'name': "Sample Tree",
                'id': "cert-root"
            }
        else:
            multi_parents_treeData = {
                #'name': "certificates",
                'name': "Sample Tree",
                'id': "cert-root",
                'children': fullTreeList
            }
        print("multi_parents_treeData:", multi_parents_treeData)
        
        # run test
        self.__createSampleTreeToList(sample_id)
        
        return multi_parents_treeData
    
    def __convertListlistsIntoDiclist_toberemoved(self, parentList):
        ''' Convert a list of lists into a list of dictionaries.
        Input:
            parentList, a list of lists, such as
                [
                    ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-3', 'LYS-200225WHI-3', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-5', 'LYS-200225WHI-5', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-6', 'LYS-200225WHI-6', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-7', 'LYS-200225WHI-7', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-9', 'LYS-200225WHI-9', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-10', 'LYS-200225WHI-10', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-11', 'LYS-200225WHI-11', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                ]
                or
                [
                    ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
                ],
                where two DNA samples are either the parent or child sample.
        
        Output:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
            
        Notes: This subroutine does not work on ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
        '''
        # Step 3. Find the sub-list which is longest
        # Notes: There are two scenario:
        #   1. all sub-lists are equal length and contain sample hierarchy of samples.
        #   2. not all sub-lists are equal, 
        n0 = 0
        list0 = None
        for listi in parentList:
            print(listi)
            ni = len(listi)
            if ni>n0:
                n0 = ni
                list0 = listi
                
        sampleTypes = []
        for uid in list0:
            # such as 'CEL-200225WHI-1'
            if "-" in uid:
                terms = uid.split('-')
                sampleType = terms[0]
                # such as "CEL"
            else:
                # just in case for old uid
                sampleType = uid
            sampleTypes.append(sampleType)
        # such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        # or ['TIS', 'DNA', 'DNA', 'D.SEQ']
        
        # Step 4. Reformat the list of lists into a list of dictionaries.
        diclist = []
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            dici = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                dici[sampleType] = uid
                
            # such as dici = {'TIS':'TIS-200721BMC-1', 'DNA':'DNA-200721BMC-1', 'DNA':'DNA-200721BMC-2', 'D.SEQ':'D.SEQ-200721BMC-1'}
            diclist.append(dici)
            
        # such as 
        return sampleTypes, diclist
    
    def __getSampleTypeAttributes(self, parentList):
        ''' Get a list of unique sample types and their corresponding attributes.
        Input:
            parentList, a list of lists, such as
                [
                    ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-3', 'LYS-200225WHI-3', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-5', 'LYS-200225WHI-5', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-6', 'LYS-200225WHI-6', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-7', 'LYS-200225WHI-7', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-9', 'LYS-200225WHI-9', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-10', 'LYS-200225WHI-10', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                    ['CEL-200225WHI-11', 'LYS-200225WHI-11', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                ]
                or
                [
                    ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
                ],
                where two DNA samples are either the parent or child sample.
        
        Output:
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
            attributes,  = [{'CEL':attributeInfo1}, ... ], a list of dictionaries, with the attribute info for each of sample types.
            sampleTypeCount, = {'TIS':1, 'DNA':2, 'D.SEQ':1}
        Notes: This subroutine is to address the issue on ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
    
        '''
        # Step 1. Get an unique list of sample types
        sampleTypes = []       # this is an order list of sample types, sorted according to its appearance 
        sampleTypeCount = {}   # this is the count of the sample type apperance, 
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   in which each sample type appears once;
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            #   in which DNA sample type appears twice.
            sampleTypeCount_i = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                    
                if sampleType not in sampleTypes:
                    sampleTypes.append(sampleType)
                    
                if sampleType not in sampleTypeCount_i:    
                    sampleTypeCount_i[sampleType] = 1
                else:
                    sampleTypeCount_i[sampleType] = sampleTypeCount_i[sampleType] + 1
                    
            # update the count of sample types in a list
            for sampleType_i, count_i in sampleTypeCount_i.iteritems():
                if sampleType_i not in sampleTypeCount:
                    sampleTypeCount[sampleType_i] = count_i
                else:
                    if count_i>sampleTypeCount[sampleType_i]:
                        sampleTypeCount[sampleType_i] = count_i
                
        # such as
        #   sampleTypes = ['CEL', 'LYS', 'D.MSP', 'A.MSP'], or
        #   sampleTypes = ['TIS', 'DNA', 'D.SEQ'], where no duplicates exist.
        print("sampleTypes:", sampleTypes)
                
        # Step 2. Get the list of sample attributes
        stype = DBtable_sampletype("DEFAULT")
        attributes = stype.retrieveAttributes(sampleTypes)
        print("attributes:", attributes)
        # attributes = [
        #     {'CEL':attributeInfo1}, ...    
        # ] 

        # Step 3. Prepare headers for export
        # now we have the diclist for export, we needs to organize all columns in an order
        # defined from parent-child relationship, from left to right
        headers = []
        headersMapping = {} # headersMapping['MUS:UID'] = 'MUS:uid', where the key is the title of the attribute while the value is the lower case of an attribute name.
        for attr in attributes:
            for sampleType, attrInfo in attr.iteritems():
                #print(sampleType, attrInfo)
                count = sampleTypeCount[sampleType]
                for i in range(count):
                    if count>1:
                        suffix = "_" + str(i+1)
                        prefix = sampleType + suffix + ':'       # such as "TIS:"
                    else:
                        prefix = sampleType + ':'
                
                    if attrInfo is not None and 'headers' in attrInfo:
                        headers_i = attrInfo['headers']
                        for header in headers_i:
                            title = prefix + header
                            
                            newheader = prefix + header.lower()
                            headers.append(newheader)
                            
                            headersMapping[newheader] = title
                            
        #print(headers) 

        return sampleTypes, sampleTypeCount, headers, headersMapping
    
    def __retrieveSampleJsonData(self, uid):
        ''' Retrieve the sample json_meta data into a dicionary, given
        Input:
            uid, the uid for a sample, such as 'CEL-200225WHI-1'
            
        Output:
            dici = {}, the dictionary of the json_meta field in sample table.
        '''
        record_db = self.__retrieveSampleByUID(uid)
        if record_db is None:
            return None
            
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        return sampleDic
        
    def __saveSampleList_toberemoved(self, sampleTypes, diclist, excelfile):
        ''' Convert a list of lists into a list of dictionaries.
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            into an excel file
        '''
        #print("__saveSampleList")
        
        # Step 1. Get the list of sample attributes
        stype = DBtable_sampletype("DEFAULT")
        attributes = stype.retrieveAttributes(sampleTypes)
        # attributes = [
        #     {'CEL':attributeInfo1}, ...    
        # ] 
        
        # Step 2. Get the list of samples based on their uids
        uids = {}
        for dici in diclist:
            #such as {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
            for sampletype, uid in dici.iteritems():
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        # Step 3. Convert the diclist of sample uids into the diclist of sample values 
        diclist_new = []
        for dici in diclist:
            #such as {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
            dici_new = {}
            for sampletype, uid in dici.iteritems():
                if uid in uids:
                    sampleDic = uids[uid]
                    if sampleDic is not None and sampleDic is not []:
                        for key, value in sampleDic.iteritems():
                            newkey = sampletype + ':' + key
                            dici_new[newkey] = value
            #print(dici_new)
            diclist_new.append(dici_new)
        # diclist_new = [
        #   {'CEL:attr1':value1, 'CEL:attr2':value2, ...,  'A.MSP:attrN':valueN}
        # ]
        
        # Step 4. Prepare headers for export
        # now we have the diclist for export, we needs to organize all columns in an order
        # defined from parent-child relationship, from left to right
        headers = []
        for attr in attributes:
            for sampletype, attrInfo in attr.iteritems():
                print(sampletype, attrInfo)
                if attrInfo is not None and 'headers' in attrInfo:
                    headers_i = attrInfo['headers']
                    for header in headers_i:
                        newheader = sampletype + ":" + header.lower()
                        headers.append(newheader)
        print(headers) 
        
        # Step 5. Output the list of samples into the excel file.
        #
        #saveExcelDiclist(excelfile, headers, diclist_new, 'samples')
        saveDiclistIntoExcel(diclist_new, excelfile, headers, 'samples')
        
        nsamples = len(diclist_new)
        return nsamples
        
    def __convertSampleTreeToList(self, parentList, sampleTypes, sampleTypeCount, headers):
        ''' Convert a list of lists for a sample tree into a list of dictionaries.
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            into an excel file
        '''
        #print("__saveSampleList")
        
        # Step 2. Get the list of samples based on their uids
        uids = {}
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            for uid in listi:
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        # Step 3. Convert the diclist of sample uids into the diclist of sample values 
        diclist_new = []
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            dici_new = {}
            sampleTypeCount_now = {}        # the count of a sample type in the current list
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    # such as 'DNA-200721BMC-1', the first DNA sample uid
                    sampleTypeCount_now[sampleType] = 1
                else:
                    # such as 'DNA-200721BMC-2', which is the second DNA sample type
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                # the total count of apperance of a sample type in any individual list of parentList
                count = sampleTypeCount[sampleType]
                if count==1:
                    #this sample type appears only once in any individual list of parentList,
                    # no suffix is neccessary
                    prefix = sampleType + ':'       # such as "TIS:"
                else:
                    #this sample type appears more than once in any individual list of parentList,
                    # add a suffix with the current count
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix + ':'       # such as "DNA_2:"
                
                sampleDic = uids[uid]
                if sampleDic is not None and sampleDic is not []:
                    for key, value in sampleDic.iteritems():
                        newkey = prefix + key
                        dici_new[newkey] = value        
            diclist_new.append(dici_new)
        
        # Step 5. Output the list of samples into the excel file.
        #
        #saveExcelDiclist(excelfile, headers, diclist_new, 'samples')
        
        # remove any header that does not have any value in the diclist
        headers_new = filterDiclist(headers, diclist_new)
        #print("headers:", headers)
        #print("headers_new:", headers_new)
         
        return headers_new, diclist_new
        
        
        # only save sample sheet
        #saveDiclistIntoExcel(diclist_new, excelfile, headers_new, 'samples')
        
        # get a list of headers that contain variable values, and
        # a list of headers that contain constant values
        headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
        #print("headers_noneConstant:", headers_noneConstant)
        #print("headers_constant:", headers_constant)
        
        # save two diclists into an excel file with "samples" tab and "constants" tab
        saveTwoDiclistsIntoExcel(excelfile, diclist_new, headers_noneConstant, 'samples', diclist_constant, headers_constant, 'constants')

        nsamples = len(diclist_new)
        return nsamples

    #def __saveSampleList(self, parentList, sampleTypes, sampleTypeCount, headers, excelfile):
    def __saveSampleList(self, headers_new, diclist_new, excelfile):
        ''' Convert a list of lists into a list of dictionaries.
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            into an excel file
        '''
        #headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)
        
        # only save sample sheet
        #saveDiclistIntoExcel(diclist_new, excelfile, headers_new, 'samples')
        
        # get a list of headers that contain variable values, and
        # a list of headers that contain constant values
        headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
        #print("headers_noneConstant:", headers_noneConstant)
        #print("headers_constant:", headers_constant)
        
        # save two diclists into an excel file with "samples" tab and "constants" tab
        saveTwoDiclistsIntoExcel(excelfile, diclist_new, headers_noneConstant, 'samples', diclist_constant, headers_constant, 'constants')

        nsamples = len(diclist_new)
        return nsamples


    def __createSampleTreeToList(self, sample_id, xlsfile='/home/huiming/myhome/websites/dmac/test.xls'):
        ''' Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_id, the id of a sample.
            
        Output
        reversed treeData, such as two parents with one child,
            multi_parents_tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        
        Example
            Given, treeData,
                    B ________
                              \     ________E___
                               D---/            \_____________A
                                   \________F___/
                                               /
                                              /
                    C________________________/
            
            Output =[
                [B,D,E,A],
                [B,D,F,A],
                [C,    A]
            ]
        
        
        '''
        
        # Step 1. get only the parent tree, for example
        #   upTreeList = 
        #            B ________
        #                      \     ________E___
        #                       D---/            \_____________A
        #                           \________F___/
        #                                       /
        #                                      /
        #            C________________________/
        #
        includeChilren = False
        upTreeList = self.__createMultiParentTree(sample_id, includeChilren)
        
        # Step 2. Convert the parent tree into a list of lists, for example
        #    parentList =[
        #        [B,D,E,A],
        #        [B,D,F,A],
        #        [C,    A]
        #    ]
        parentList = self.__getChildrenListLoop(upTreeList)
        # For example:
        # [
        #   ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-3', 'LYS-200225WHI-3', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-5', 'LYS-200225WHI-5', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-6', 'LYS-200225WHI-6', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-7', 'LYS-200225WHI-7', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-9', 'LYS-200225WHI-9', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-10', 'LYS-200225WHI-10', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        #   ['CEL-200225WHI-11', 'LYS-200225WHI-11', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
        # ]
        
        # Step 3. Convert the list of lists into a list of dictionaries and an ordered list of sample types for export
        #sampleTypes, diclist = self.__convertListlistsIntoDiclist_toberemoved(parentList)
        #self.__saveSampleList_toberemoved(sampleTypes, diclist, xlsfile)
        
        
        sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(parentList)
        
        #self.__saveSampleList(parentList, sampleTypes, sampleTypeCount, headers, xlsfile)      
        headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)        
        nsamplesOutput = self.__saveSampleList(headers_new, diclist_new, xlsfile)
        return parentList


    def __createSampleTree(self, sample_ids):
        ''' Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_ids, the list of sample ids.
            
        Output
        reversed treeData, such as two parents with one child,
            multi_parents_tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        
        Example
            Given, treeData,
                    B ________
                              \     ________E___
                               D---/            \_____________A
                                   \________F___/
                                               /
                                              /
                    C________________________/
            
            Output =[
                [B,D,E,A],
                [B,D,F,A],
                [C,    A]
            ]
        
        
        '''
        
        # Step 1. get only the parent tree, for example
        #   upTreeList = 
        #            B ________
        #                      \     ________E___
        #                       D---/            \_____________A
        #                           \________F___/
        #                                       /
        #                                      /
        #            C________________________/
        #
        includeChilren = False
        parentList = []
        for sample_id in sample_ids:
            upTreeList = self.__createMultiParentTree(sample_id, includeChilren)
        
            # Step 2. Convert the parent tree into a list of lists, for example
            #    parentList =[
            #        [B,D,E,A],
            #        [B,D,F,A],
            #        [C,    A]
            #    ]
            parentList_i = self.__getChildrenListLoop(upTreeList)
            # For example:
            # [
            #   ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-3', 'LYS-200225WHI-3', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-5', 'LYS-200225WHI-5', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-6', 'LYS-200225WHI-6', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-7', 'LYS-200225WHI-7', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-9', 'LYS-200225WHI-9', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-10', 'LYS-200225WHI-10', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   ['CEL-200225WHI-11', 'LYS-200225WHI-11', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # ]
            #print(sample_id, parentList_i)
            parentList += parentList_i
        
        print("Number of samples for download: " + str(len(sample_ids)) + ", retrieved: " + str(len(parentList)))
        
        
        # Step 3. Convert the list of lists into a list of dictionaries and an ordered list of sample types for export
        #sampleTypes, diclist = self.__convertListlistsIntoDiclist_toberemoved(parentList)
        #self.__saveSampleList_toberemoved(sampleTypes, diclist, xlsfile)
        
        # For test purpose: export parent list into excel file
        #self.__exportParentList(parentList, xlsfile)
        #return parentList    
        
        # For production
        sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(parentList)       
        headers_new, diclist_new = self.__convertSampleTreeToList(parentList, sampleTypes, sampleTypeCount, headers)       
        return headers_new, diclist_new, headersMapping

    def __createSampleTreeToList_new(self, sample_ids, xlsfile='/home/huiming/myhome/websites/dmac/test.xls'):
        ''' Create a hierarchical tree of all parents, starting from the current child samples, given
        Input:
            sample_ids, the list of sample ids.
            
        Output
        reversed treeData, such as two parents with one child,
            multi_parents_tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        
        Example
            Given, treeData,
                    B ________
                              \     ________E___
                               D---/            \_____________A
                                   \________F___/
                                               /
                                              /
                    C________________________/
            
            Output =[
                [B,D,E,A],
                [B,D,F,A],
                [C,    A]
            ]
        
        
        '''
        headers_new, diclist_new, headersMapping = self.__createSampleTree(sample_ids)
        nsamplesOutput = self.__saveSampleList(headers_new, diclist_new, xlsfile)
        
        #return parentList
        return nsamplesOutput


    def __exportParentList(self, parentList, xlsfile):
        ''' Convert a list of lists into a list of dictionary for excel output.
        Input:
            parentList, a list of lists, such as,
                # [
                #   ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1'],
                #   ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                # ]
        Output
            headers, a lis of unique items in the parentList.
            diclist, a list of dictionary, such as,
                # [
                #   {'CEL-200225WHI-1':1, 'LYS-200225WHI-1':1, 'D.MSP-200225WHI-1':1, 'A.MSP-200225WHI-1':1},
                #   {'CEL-200225WHI-2':1, 'LYS-200225WHI-2':1, 'D.MSP-200225WHI-1':1, 'A.MSP-200225WHI-1':1}
                # ]
        '''
        return self.__exportParentList_V2(parentList, xlsfile)
        
        headers = []
        diclist = []
        for listi in parentList:
            dici = {}
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   in which each sample type appears once;
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            #   in which DNA sample type appears twice.
            for uid in listi:
                dici[uid] = 1
                if uid not in headers:
                    headers.append(uid)
                    
            diclist.append(dici)
        saveDiclistIntoExcel(diclist, xlsfile, headers, 'uids')    

    def __exportParentList_V2(self, parentList, xlsfile):
        ''' Convert a list of lists into a list of dictionary for excel output.
        Input:
            parentList, a list of lists, such as,
                # [
                #   ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1'],
                #   ['CEL-200225WHI-2', 'LYS-200225WHI-2', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
                # ]
        Output
            headers, a lis of unique sample types in the parentList, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
            diclist, a list of dictionary, such as,
                # [
                #   {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'},
                #   {'CEL':'CEL-200225WHI-2', 'LYS':'LYS-200225WHI-2', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                # ]
        '''
                # Step 1. Get an unique list of sample types
        sampleTypes = []       # this is an order list of sample types, sorted according to its appearance 
        sampleTypeCount = {}   # this is the count of the sample type apperance, 
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   in which each sample type appears once;
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            #   in which DNA sample type appears twice.
            sampleTypeCount_i = {}
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                    
                if sampleType not in sampleTypes:
                    sampleTypes.append(sampleType)
                    
                if sampleType not in sampleTypeCount_i:    
                    sampleTypeCount_i[sampleType] = 1
                else:
                    sampleTypeCount_i[sampleType] = sampleTypeCount_i[sampleType] + 1
                    
            # update the count of sample types in a list
            for sampleType_i, count_i in sampleTypeCount_i.iteritems():
                if sampleType_i not in sampleTypeCount:
                    sampleTypeCount[sampleType_i] = count_i
                else:
                    if count_i>sampleTypeCount[sampleType_i]:
                        sampleTypeCount[sampleType_i] = count_i
                
        # such as
        #   sampleTypes = ['CEL', 'LYS', 'D.MSP', 'A.MSP'], or
        #   sampleTypes = ['TIS', 'DNA', 'D.SEQ'], where no duplicates exist.

        # Step 3. Prepare headers for export
        # now we have the diclist for export, we needs to organize all columns in an order
        # defined from parent-child relationship, from left to right
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
        #print(headers) 
        
        diclist = []
        for listi in parentList:
            dici = {}
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            #   in which each sample type appears once;
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            #   in which DNA sample type appears twice.
            sampleTypeCount_now = {}        # the count of a sample type in the current list
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    # such as 'DNA-200721BMC-1', the first DNA sample uid
                    sampleTypeCount_now[sampleType] = 1
                else:
                    # such as 'DNA-200721BMC-2', which is the second DNA sample type
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                # the total count of apperance of a sample type in any individual list of parentList
                count = sampleTypeCount[sampleType]
                if count==1:
                    #this sample type appears only once in any individual list of parentList,
                    # no suffix is neccessary
                    prefix = sampleType
                else:
                    #this sample type appears more than once in any individual list of parentList,
                    # add a suffix with the current count
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix
                
                dici[prefix] = uid
                    
            diclist.append(dici)
        saveDiclistIntoExcel(diclist, xlsfile, headers, 'uids')  

    def __formatHttpLink(self, stritem):
        ''' Format a string into a hyperlink, given
        Input:
            stritem, a string, if 'http' is in it, convert it into a hyper link.
        Output:
            a string with the hyper link, formated by using xlwt.
            
        Refer to:
            https://xlsxwriter.readthedocs.io/example_hyperlink.html
            https://stackoverflow.com/questions/24960916/adding-hyperlink-to-cell-with-text-using-xlwt
        '''
        if stritem is None:
            return stritem
        
        newstr = 'HYPERLINK(' + stritem + ')'
        newitem = xlwt.Formula(newstr)
        #newitem = xlwt.Formula('"test " & HYPERLINK("http://google.com")')
        print(stritem, newitem)
        return newitem
    
    
    def __saveSamples(self, xlsfile, diclist, headers, sheetname_2=None, diclist_2=None, headers_2=None):
        ''' Save a list of samples into a csv file.
        Input:
            diclist, a dic list for saving.
            csvfile, a csv file name with the path to the server for download.
        
        Output:
            csv file for saving.
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
            #print(index, header)
            try:
                newitem = toString(header)
                #print(row, index, newitem)
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
        ''' Reformat the list of samples for download, given
        Input:
            sampletype_id, the id for the sample type, 
            diclist, a list of samples in the same dample type from the samples table.
        
        Output:
            headers, a sorted list of headers in the json_metadata of samples.
            metadata, a diclist of json_metadata of samples. 
        '''
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        #sampletype = attributeInfo['sampletype']
        #sampletype_name = sampletype['title']
        headers = attributeInfo['headers']
        metadata = []
        for dici in diclist:
            json_metadata = dici['json_metadata']
            #print('json_metadata:', json_metadata)
            record = self.__getRecordFromJson(json_metadata)
            #print('record:', record)
            metadata.append(record)
        
        newheaders = []
        for header in headers:
            newheaders.append(header.lower())
        return newheaders, metadata
        
    def downloadSamples(self, user_seek, xlsfile, link, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo):
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;
            filter_rule, an operator defined in DBtable_sampleattribute().getOperators(sampletype_id, attribute)
            filter_valueFrom, a start value for the filtering;
            filter_valueTo, a end value for the filtering;
            
            filtersdic, filter parameters from the dataGrid.
            
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            print("validateFilters:", msg)
            if status==0:
                data = {'msg':msg, 'status': status, 'link':''}
                reportData = simplejson.dumps(data)
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
        
        #dic0 = rows[0]
        #print(dic0)
        #uid = dic0['uid']
        #sample_id = str(dic0['pid'])
        #self.__createSampleTreeToList(sample_id, xlsfile)
        
        sample_ids = []
        for row in rows:
            uid = row['uid']
            sample_id = str(row['pid'])
            sample_ids.append(sample_id)
        self.__createSampleTreeToList_new(sample_ids, xlsfile) 
        
        #headers, metadata = self.__formatSampleDownload(sampletype_id, rows)
        #headers_2 = ['pid', 'uuid', 'parent_uids', 'sample_type', 'assays', 'first_name', 'created_at']
        #self.__saveSamples(xlsfile, metadata, headers, 'Metadata', rows, headers_2)
        
        #self.__saveSamples(rows, xlsfile, headers)
        #data['rows'] = rows
        data['msg'] = 'okay'
        data['status'] = 1
        data['link'] = link
        
        reportData = simplejson.dumps(data)
        return reportData
    
    
    def downloadSamples_new(self, user_seek, xlsfile, link, sample_ids):
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sample_ids, a list of sample ids
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        nsamplesOutput = self.__createSampleTreeToList_new(sample_ids, xlsfile)
        
        
        #headers, metadata = self.__formatSampleDownload(sampletype_id, rows)
        #headers_2 = ['pid', 'uuid', 'parent_uids', 'sample_type', 'assays', 'first_name', 'created_at']
        #self.__saveSamples(xlsfile, metadata, headers, 'Metadata', rows, headers_2)
        
        #self.__saveSamples(rows, xlsfile, headers)
        #data['rows'] = rows
        data = {}
        data['link'] = link
        if nsamplesOutput>=len(sample_ids):
            data['msg'] = 'okay'
            data['status'] = 1
        else:
            data['msg'] = 'Warning: Number of samples output: ' + str(nsamplesOutput) + ' is less than the number selected: ' + str(len(sample_ids))
            print(data['msg'])
            data['status'] = 0
            
        reportData = simplejson.dumps(data)
        return reportData
    
    def __exportImmportSheetInfo(self, headersMapping, diclist_new, templatedata, sheetName, excelfile):
        '''
        Input:
            headersMapping,  headersMapping['MUS:UID'] = 'MUS:uid', where the key is the title of the attribute while the value is the lower case of an attribute name.
        
        '''
        nameup = sheetName.upper()
        
        sheetData = templatedata[nameup]
        diclist = sheetData['diclist']
        
        headers = []
        mapping = {}
        for dici in diclist:
            print(dici)
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
                
                #if attribute in headersMapping:
                    # such as attribute = "MUS:uid"
                    # becomes "MUS:UID"
                #    attribute = headersMapping[attribute]
                    
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
            
            print(diciOut)
            diclistOut.append(diciOut)
            
            # remove any header that does not have any value in the diclist
            #headers_new = filterDiclist(headers, diclistOut)
            
            # remove duplicated rows
            diclistOut = removeDiclistDuplicates(diclistOut)
        
        reviseExcelDiclist(excelfile, headers, diclistOut, sheetName)
        return
    
    def __exportImportProtocls(self, user_seek, diclist, zf):
        ''' Update the Immport sheet 'protocols'.
        Input:
            diclist, a list f dictionaries, each of which is a row in the 'protocols' sheet.
            zf, the zip file handler for saving protocol files in a zip file.
        
        Output:
        
        
        '''
        print("__exportImportProtocls")
        dbsop = DBtable_sops("DEFAULT")
        diclist_new = []
        for dici in diclist:
            if "File Name" in dici:
                sop_link = dici["File Name"] # such as 'http://server/seek/sop/uid=sopfile/'
                terms = sop_link.split('/')
                if sop_link[-1]=='/':
                    uidterm = terms[-2]
                else:
                    uidterm = terms[-1]
                    
                if "=" in uidterm:  # such as "uid=sopfile"
                    terms = uidterm.split("=")
                    sop_uid = terms[-1]
                    fullfilename, status, link = dbsop.downloadSOP_fromStorage(user_seek, sop_uid)
                    if status==1:
                        dici['User Defined ID'] = sop_uid
                        terms = fullfilename.split('/')
                        originalName = terms[-1]
                        dici['Name'] = originalName
                        
                        if os.path.isfile(fullfilename):
                            # this will only works on the production server
                            zf.write(fullfilename, originalName)
            
            diclist_new.append(dici)
        return diclist_new
        
    
    def __exportImmportSheetInfoZip(self, user_seek, headersMapping, diclist_new, templatedata, sheetName, txtfile, fileLabel, zf):
        '''
        Input:
            headersMapping,  headersMapping['MUS:UID'] = 'MUS:uid', where the key is the title of the attribute while the value is the lower case of an attribute name.
            diclist_new, sample list of dictionaries.
            templatedata, mapping between Seek sample dictionary and Immport template sheet
            sheetName, such as "experimentsamples"
            txtfile, such as "/media_path/experimentsamples.txt"
            fileLabel, such as "mass_spec_proteomics".
            zf, zf = zipfile.ZipFile(downloadfile, mode='w'), used to save protocol files.
        
        Output:
            The Immport tab-delimit txt  file.
        '''
        nameup = sheetName.upper()
        sheetData = templatedata[nameup]
        diclist = sheetData['diclist']
        
        headers = []
        mapping = {}
        for dici in diclist:
            print(dici)
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
                
                #if attribute in headersMapping:
                    # such as attribute = "MUS:uid"
                    # becomes "MUS:UID"
                #    attribute = headersMapping[attribute]
                    
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
            
            print(diciOut)
            diclistOut.append(diciOut)
            
            # remove any header that does not have any value in the diclist
            #headers_new = filterDiclist(headers, diclistOut)
            
            # remove duplicated rows
            diclistOut = removeDiclistDuplicates(diclistOut)
        
        if sheetName=='protocols':
            print('Revise protocol output and save protocol files in the zip file')
            diclistOut = self.__exportImportProtocls(user_seek, diclistOut, zf)
        
        #reviseExcelDiclist(excelfile, headers, diclistOut, sheetName)
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
        ''' Convert a list of lists into a list of dictionaries.
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            downloadfile, file name for exporting samples, in excel or zip format.
            
        '''
        if 'xlsx' in downloadfile:
            return self.__exportImmportSampleList(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
            
        excelfile = downloadfile.replace('zip', 'xlsx')
        
        # copy template file as the file for export
        #templatefile = IMMPORT_TEMPLATE_FILE_PREFIX + sampletypeName + ".xlsx"
        templatefile = IMMPORT_TEMPLATE_FILE
        print(templatefile)
        print(excelfile)
        #handle_uploaded_file(templatefile, downloadfile)
        cmd = 'cp ' + templatefile + ' ' + excelfile
        os.system(cmd)
        
        msg = "Load Immport template file"
        status = 0
        
        # Step 1. Load the input excel file
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: Immport template file not loaded: " + excelfile
            status = 0
            print(msg)
            return msg, status

        print(filedata['sheetnames'])
        status = 1
        #for sheetname in ['ExpSample', 'AnimalSubject', 'BioSamples']:
        #for sheetname in ['EXPSAMPLE']:
        for sheetname in IMMPORT_TEMPLATES:
            msg = "Error: the following sheet is missing: "
            nameup = sheetname.upper()
            if nameup not in filedata['sheetnames'] or nameup not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                print(msg)
                return msg, status
        
        zf = zipfile.ZipFile(downloadfile, mode='w')
        status = 0
        msg = "Start generating zip file"
        #for sheetname in ['AnimalSubject', 'BioSamples', 'ExpSample', 'Protocol', 'Experiment']:
        for sheetname in IMMPORT_TEMPLATES:
            filename = sheetname + '.txt'
            sheetfile = DOWNLOAD_DIRECTORY + filename
            fileLabel = IMMPORT_TEMPLATES[sheetname]
            self.__exportImmportSheetInfoZip(user_seek, headersMapping, diclist_new, filedata, sheetname, sheetfile, fileLabel, zf)
            zf.write(sheetfile, filename)
        
        zf.close()
            
        return "Okay", 1
    
    def __exportImmportSampleList(self, user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping):
        ''' Convert a list of lists into a list of dictionaries.
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            downloadfile, file name for exporting samples, in excel or zip format.
            
        '''
        if 'zip' in downloadfile:
            return self.__exportImmportSampleListZip(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
            
        excelfile = downloadfile
        
        # copy template file as the file for export
        #templatefile = IMMPORT_TEMPLATE_FILE_PREFIX + sampletypeName + ".xlsx"
        templatefile = IMMPORT_TEMPLATE_FILE
        print(templatefile)
        print(excelfile)
        #handle_uploaded_file(templatefile, downloadfile)
        cmd = 'cp ' + templatefile + ' ' + excelfile
        os.system(cmd)
        
        msg = "Load Immport template file"
        status = 0
        
        # Step 1. Load the input excel file
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: Immport template file not loaded: " + excelfile
            status = 0
            print(msg)
            return msg, status

        print(filedata['sheetnames'])
        status = 1
        #for sheetname in ['ExpSample', 'AnimalSubject', 'BioSamples']:
        #for sheetname in ['EXPSAMPLE']:
        for sheetname in IMMPORT_TEMPLATES:
            msg = "Error: the following sheet is missing: "
            nameup = sheetname.upper()
            if nameup not in filedata['sheetnames'] or nameup not in filedata:
                status = 0
                msg += sheetname + ';'
            
            if status==0:
                print(msg)
                return msg, status
        
        #for sheetname in ['AnimalSubject', 'BioSamples', 'ExpSample', 'Protocol', 'Experiment']:
        for sheetname in IMMPORT_TEMPLATES:
            self.__exportImmportSheetInfo(headersMapping, diclist_new, filedata, sheetname, downloadfile)
            
        return "Okay", 1
    
    
    def __exportImmportCreateSampleTreeToList(self, user_seek, sample_ids, downloadfile, sampletypeName):
        ''' Create a hierarchical tree of all parents, starting from the current child samples,
            given alist of samle ids. Then convert the output of sample list according to the Immport template.
        Input:
            sample_ids, the list of sample ids.
            sampletypeName: which Immport template to use for export.
            
        Output
        
        downloadfile, file name for exporting samples, in excel or zip format.
        reversed treeData, such as two parents with one child,
            multi_parents_tree = {
                'name': "certificates",
                'id': "cert-root",
                'children': [actualTree]
            }
            
        where
            'name':"certificates", where "certificates" is a reserved name so that the jscript will not show this node with this name as well as not show the edge from this node to any child node;
            'id':"cert-root", where "cert-root" is also reserved for the same purpose;
            actualTree={
                    'id': "B_1",
                    'name': "B",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                },
                {
                    'id': "C_1",
                    'name': "C",
                    'children': [{
                        'id': "A_1",
                        'name': "A",
                    }]
                }
        such as,     ________
                    B         \
                              |_______A
                    C________/
        
                
        References:
            1. https://angularscript.com/angular-directive-to-generate-multi-parent-d3-graph/;
            2. '/dokuwiki/doku.php?id=computer:software:d3:d3-tree#step_2_prepare_the_tree_data_on_client_side'
        
        Example
            Given, treeData,
                    B ________
                              \     ________E___
                               D---/            \_____________A
                                   \________F___/
                                               /
                                              /
                    C________________________/
            
            Output =[
                [B,D,E,A],
                [B,D,F,A],
                [C,    A]
            ]
        
        
        '''
        
        headers_new, diclist_new, headersMapping = self.__createSampleTree(sample_ids)
        
        msg, status = self.__exportImmportSampleList(user_seek, headers_new, diclist_new, downloadfile, sampletypeName, headersMapping)
 
        return msg
    
    
    def exportSamples(self, user_seek, xlsfile, link, sample_ids, sampletype_id):
        ''' Similar to downloadSamples_new(), download the list of samples into an Immport template file, in which columns are Immport headers
            mapped from sample attribute names.
         
        Input:
            user_seek,
            sample_ids, a list of sample ids that will be exported;
            sampletype_id, such as MSP etc, which Immport template to use.
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        stype = DBtable_sampletype()
        sampletypeName = stype.retrieveFieldValue(sampletype_id, 'title')
        return self.__exportSamples0(user_seek, xlsfile, link, sample_ids, sampletypeName)

    def __exportSamples0(self, user_seek, downloadfile, link, sample_ids, sampletypeName):
        ''' Similar to downloadSamples_new(), download the list of samples into an Immport template file, in which columns are Immport headers
            mapped from sample attribute names.
         
        Input:
            user_seek,
            sample_ids, a list of sample ids that will be exported;
            sampletype_id, such as MSP etc, which Immport template to use.
        
        Output
            downloadfile, file name for exporting samples, in excel or zip format.
        
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        #if sampletypeName!='D.MSP':
        #    nsamplesOutput = 0
        #    msg = "Error: Only D.MSP sample type is supported for exporting samples."
        #else:
        sampletypeName = 'D.MSP'
        nsamplesOutput = self.__exportImmportCreateSampleTreeToList(user_seek, sample_ids, downloadfile, sampletypeName)
        msg = 'Okay'
                
        #headers, metadata = self.__formatSampleDownload(sampletype_id, rows)
        #headers_2 = ['pid', 'uuid', 'parent_uids', 'sample_type', 'assays', 'first_name', 'created_at']
        #self.__saveSamples(xlsfile, metadata, headers, 'Metadata', rows, headers_2)
        
        #self.__saveSamples(rows, xlsfile, headers)
        #data['rows'] = rows
        data = {}
        data['link'] = link
        if nsamplesOutput>=len(sample_ids):
            data['msg'] = 'okay'
            data['status'] = 1
        else:
            #data['msg'] = 'Warning: Number of samples output: ' + str(nsamplesOutput) + ' is less than the number selected: ' + str(len(sample_ids))
            data['msg'] = msg
            print(data['msg'])
            data['status'] = 0
            
        reportData = simplejson.dumps(data)
        return reportData
    
    def __verifyFileInRecord(self, sampleRecord, originalfilename, filetype):
        ''' Verify whether or not the sample json_metadata really contains the originalfilename.
        Input:
            sampleRecord, the record from samples table for a a
            originalfilename,request.FILES['file'].name, the original file name from client side, which
                may contain space in its name.
                infile: = request.FILES['file'], the data file to be uploaded and searched.
            filetype, 
                "DATAFILE", one data file is allowed by design uniquely only in one sample;
                "SOP", one SOP file could be quoted in any number of samples.
        Output:
            fileInRecord = false, originalfilename is not uniquely present in a sample record.
                           true, originalfilename is not uniquely present in a sample record.
        '''
        #print("__verifyFileInRecord")
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
                #print(key, value)
                if SAMPLE_FILE_ACCESSOR_NAME in key.lower():
                    if value==originalfilename:
                        fileInRecord = True
        return fileInRecord, sampledic
    
    def searchFileInSample(self, seekdb, originalfilename, filetype):
        ''' Search Seek whether a file has been quoted previously in any sample sheet.
        Input
            seekdb, SEEK DB API.
                username,  user_seek['username'] or request.session.get('username')
                userid, user_seek['user_id'] or self.__getSeekUserID(user_seek['username'])
            originalfilename: request.FILES['file'].name, the original file name from client side, which
                may contain space in its name.
                infile: = request.FILES['file'], the data file to be uploaded and searched.
            filetype:
                "DATAFILE", one data file is allowed by design uniquely only in one sample;
                "SOP", one SOP file could be quoted in any number of samples.
                or others, not supported yet.
        Output
            sampleRecord, = the record in sample table that contains the data file name,plus the dictionary in json_metadata,
                which should be unique.
            
                sample_id=sampleRecord['id'], >0, exists in sample sheet
                   =0, not exist in any sample sheet.
                   <0, does not exist anywhere in Seek or on storage server.
                sample_uid=sampleRecord['uuid'].
                
                
        Criteria
            Only the following first two criteria are applied in the implementation of the script.
            
                1. same file name, applied;
                2. same login user, applied;
                3. file checksum, not applied;
                4. file time stamp, not applied;
                5. file size, not applied.
        '''
        if filetype!="SOP" and filetype!="DATAFILE":
            msg = 'Error: file type not supported for uploading file.'
            return None, msg
        
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', originalfilename)
        if records is None:
            # no record is found
            msg = 'Warning: File not associated with any sample that must be uploaded first'
            return None, msg
        
        # If the data file name is for SOP, the number of 
        nrecords = len(records)
        if nrecords<=0:
            # no record is found
            msg = 'Warning: File not associated with any sample that must be uploaded first'
            return None, msg
        
        msg = "Number of samples for the file: " + str(nrecords)
        # nrecords>=0 and filetype=="DATAFILE" now
        # Should the same file name belong to same user, same lab or same project?
        # exclude any sample whose user is not the current login user:
        records_now = []
        for record in records:
            contributor_id = record['contributor_id']
            print("Login user id and sample contributor id:", seekdb.user_seek['user_id'], contributor_id)
            if contributor_id is not None and int(contributor_id)==seekdb.user_seek['user_id']:
                # same user defined the originalfilename in the sample json_metadata
                fileInRecord, sampledic = self.__verifyFileInRecord(record, originalfilename, filetype)
                if fileInRecord:
                    # the originalfilename is really and exactly in the "SOP" or "DATAFILE" field
                    record_now = record.update(sampledic)
                    records_now.append(record)
        
        nnow = len(records_now)
        if nnow==1:
            sampleRecord = records_now[0]
            msg = 'okay'
        elif nnow>1:
            #sampleRecord = records_now[0]
            if filetype=="SOP":
                # if file type is SOP, it could be quoted in any sample, just return any one
                msg = 'okay'
                sampleRecord = records_now[0]
            else:
                msg = 'Error: File associated with more than one sample that has been uploaded'
                sampleRecord = None
        else:
            sampleRecord = None
            msg = 'Error: No sample is defined for the file from same user'
        
        print(msg)
        return sampleRecord, msg
    
    
    def updateSampleDFurl(self, username, sample_uid, originalfilename, df_link):
        ''' After a DF is uploaded, update the DF link in its original sample table.
        Input:
             sample_uid, UID in sample table
             originalfilename, the original name
             df_link, the link to this DF in Seek
        
        Output:
            msg
            status
        '''
        msg = ''
        status = 0
        record_db = self.__retrieveSampleByUID(sample_uid)
        if record_db is None:
            msg = 'Error: sample not found: ' + sample_uid
            return msg, status
        
        metadata = record_db['json_metadata']
        sampleDic = self.__getRecordFromJson(metadata)
        #print('before modification:', sampleDic)
        
        suffix = None
        for key, value in sampleDic.iteritems():
            if SAMPLE_FILE_ACCESSOR_NAME in key:
                # such as key='file_qc'
                if value==originalfilename:
                    suffix = key.replace(SAMPLE_FILE_ACCESSOR_NAME, '')     # such as "qc"
        
        for key, value in sampleDic.iteritems():
            if SAMPLE_LINK_ACCESSOR_NAME in key:
                # such as 'link_qc'
                suffixi = key.replace(SAMPLE_LINK_ACCESSOR_NAME, '')        # such as 'qc'
                if suffix is not None and suffixi==suffix:
                    sampleDic[key] = df_link
                    
        #print('After modification:', sampleDic)
        #json_metadata = simplejson.dumps(sampleDic)
        #print('json_metadata renewed:', json_metadata)
        
        record_db['json_metadata'] = simplejson.dumps(sampleDic)
        #print(record_db)
        msg, status, sample_id = self.storeOneRecord(username, record_db)
        return msg, status
    
    
    def __deleteOneSample(self, sample_id, policy_id):
        #def __deleteOneSample(self, user_seek, sample_id):        
        ''' Delete one sample, given a sample id, regardless the parent-child samples.
        Input:
            user_seek,
            sample_id, a sample id
        
        Output
            status, 1, successful in deletion.
                    0, failed, and rolled back.
        
        '''
        #record = self.__retrieveSampleByID(sample_id)
        #if record is None:
        #    return 0
        #contributor_id = record['contributor_id']
        #policy_id = record['policy_id']
        
        
        sqlqueries = []
        
        # this call is moved into self.db.run_custom_transaction()
        #sqlquery = "START TRANSACTION;"
        #sqlqueries.append(sqlquery)
        
        #sqlquery = "delete from studies where id=10;"
        #sqlqueries.append(sqlquery)
        #sqlquery = "delete from study_auth_lookup where asset_id=10;"
        #sqlqueries.append(sqlquery)
        #sqlquery = "delete FROM policies where id=165;"
        #sqlqueries.append(sqlquery)
        #sqlquery = "DELETE FROM permissionss where policy_id=165;"
        #sqlqueries.append(sqlquery)
        
        sqlquery = "DELETE FROM projects_samples where sample_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM sample_resource_links where sample_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM sample_auth_lookup where asset_id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM assay_assets where asset_id=" + str(sample_id) + " AND asset_type='Sample';"
        sqlqueries.append(sqlquery)
        sqlquery = "delete FROM samples where id=" + str(sample_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "DELETE FROM permissions where policy_id=" + str(policy_id) + ";"
        sqlqueries.append(sqlquery)
        sqlquery = "delete FROM policies where id=" + str(policy_id) + ";"
        sqlqueries.append(sqlquery)
        
        print(sqlqueries)
        
        # this call is moved into self.db.run_custom_transaction()
        #sqlquery = "COMMIT;"
        #sqlqueries.append(sqlquery)
        
        db_alias = SEEK_DATABASE
        status = self.db.run_custom_transaction(sqlqueries, db_alias)
        if status:
            msg = "Trandsaction successful"
        else:
            msg = "Error: The trandsaction of deletion failed. Delete this sample manually"
        
        print(msg)
        return msg, status
    
    def __getSampleChildren(self, currentuid):
        ''' Get children sample IDs and UIDs, given
        Input:
            currentuid, the uid for the current sample.
            
        Output:
            childrenList = [{'id':id1, 'uid':uid1}, {...}], a list of sample IDs and UIDs, who are created from the current sample.
            
        How to implement?
        
        A parent sample is defined in the json_metadata of a child sample.
        However, when we search for the parent sample UID, i.e., the currentid, such as "CEL-200225WHI-1",
        the Django query self.db.retrieveRecords() returns a list of records, whose json_metadata
        contains the the currentid, such as "CEL-200225WHI-1", or
            "CEL-200225WHI-13",
            "CEL-200225WHI-134"
            "CEL-200225WHI-1;CEL-200225WHI-13",
            "CEL-200225WHI-2;CEL-200225WHI-1",
            "CEL-200225WHI-2;CEL-200225WHI-1;CEL-200225WHI-3",
            
        therefore, we have to find all those uids and exclude those samples whose parent sample UID is not the currentid.
        
        Usage:
            Also refer to self.__getChildrenUIDs(currentuid), which return a list of children UIDs.
        
        '''
        print("__getChildrenUIDs:", currentuid)
        records = self.db.retrieveRecords(self.tablemodel, 'json_metadata', currentuid)
        childrenList = []
        for record in records:
            uid = record['uuid']
            #if uid!=currentuid:        # this causes error because this record might contain "CEL-200225WHI-13", as the parent sample, rather than "CEL-200225WHI-1",
            #    uids.append(uid)
            
            metadata = record['json_metadata']
            sampleDic = self.__getRecordFromJson(metadata)
            parent_uids = self.__getParentUIDs(sampleDic)
            if currentuid in parent_uids:
                sid = record['id']
                dici = {'id':sid, 'uid':uid}
                childrenList.append(dici)
            
        return childrenList
    
    def __deleteSampleList(self, user_seek, sample_ids, xlsfile):
        ''' Delete a list of samples, check whether the sample in deletion has any child sample, given
        Input:
            sample_ids, the list of sample ids.
            
        Output

        '''
        user_id = user_seek['user_id']
        #records_user = self.db.retrieveRecords(People, 'id', user_id)
        roles_mask = self.db.retrieveFieldValue(People, user_id, 'roles_mask')
    
        status = 1
        msg = ''
        diclist = []
        for sample_id in sample_ids:
            dici = {}
            dici['id'] = sample_id
            record = self.__retrieveSampleByID(sample_id)
            contributor_id = record['contributor_id']
            policy_id = record['policy_id']
            currentuid = record['uuid']
            #print(record)
            if record is None:
                msgi = 'Error: Sample ' + currentuid +  ' not found in DB '
                status = 0
                dici['json_metadata'] = msgi
                
                msg += msgi + '<br/>'
                diclist.append(dici)
                continue
            
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
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sample_ids, a list of sample ids
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        diclist, msg, status = self.__deleteSampleList(user_seek, sample_ids, xlsfile)
        
        #self.__saveSamples(rows, xlsfile, headers)
        #data['rows'] = rows
        data = {}
        data['msg'] = msg
        data['status'] = status
        data['link'] = link
        data['diclist'] = diclist
        
        reportData = simplejson.dumps(data)
        return reportData
    
    
    def __formatSampleUIDLink(self, sample_uid):
        ''' Get the weblink for a sample uid.
        Input:
            sample_uid,
        Output:
            weblink
        '''
        url = "/seek/sampletree/uid=" + sample_uid + "/";
        weblink = '<a href="' + url + '" target="_blank">' + str(sample_uid) + '</a>'
        return weblink

    def __formatSopUIDLink(self, sop_uid):
        ''' Get the weblink for a sop uid.
        Input:
            sop_uid,
        Output:
            weblink
        '''
        url = "/seek/sop/uid=" + sop_uid + "/";
        weblink = '<a href="' + url + '" target="_blank">' + str(sop_uid) + '</a>'
        return weblink
    
    def __formatLinkUrl(self, attrname, attrvalue):
        ''' Format the sample value as a web link url, given,
        Input:
            attrname, the sample attribute name, in lower case.
            attrvalue, the value for the attribute
            
        Output:
            weblink, the weblink for the attribute.
            
        How it works:
            If an attribute is a parent uid, a protocol link etc, return the weblink for
            the attribute.
        '''
        weblink = attrvalue
        value = attrvalue
        
        if SAMPLE_PARENT_ACCESSOR_NAME in attrname:
            # link to parent uids
            if attrvalue is None:
                return weblink
            
            if ";" in value:
                #parent uids could be ";" delimited string
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
                #print('value.strip():', key, value)
                value = value.strip()
                if len(value)>0:
                    weblink = self.__formatSampleUIDLink(value)
        
        elif SAMPLE_PROTOCOL_ACCESSOR_NAME in attrname:
            # link to protocols
            if attrvalue is None:
                return weblink
            
            if ";" in value:
                #parent uids could be ";" delimited string
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
                #print('value.strip():', key, value)
                value = value.strip()
                if len(value)>0:
                    weblink = self.__formatSopUIDLink(value)
        
        elif SAMPLE_LINK_ACCESSOR_NAME in attrname:
            # link to protocols
            if attrvalue is None:
                return weblink
        
        return weblink
    
    
    def getSampleInfo(self, sample_id):
        ''' Retrieve sample information, given
        Input:
            sample_id, the primary key of a sample.
            
        Output:
            dici, the sample info in the format of a dictionary, such as
                {'name':'aaa', 'uid':'TIS-2001', 'volume':5, ....}
            diclist, the list of dictionaires, such as,
                [{'attrname':'Name', 'attrvalue':'aaa'}, {'attrname':'Uid', 'attrvalue':'TIS-2001'}, ...]
                where sample sttributes are sorted according to their positions defined. 
        
        '''
        record = self.__retrieveSampleByID(sample_id)
        if record is None:
            return None
        
        sampletype_id = record['sample_type_id']
        
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        headers = attributeInfo['headers']
        
        # Step 1. Get all parent uids for the current sample
        #print('record:',record)
        childuid = record['uuid']
        json_metadata = record['json_metadata']
        dici = self.__getRecordFromJson(json_metadata)
        
        
        #newheaders = []
        diclist = []
        for header in headers:
            headerlower = header.lower()
            #newheaders.append(header.lower())
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
            
        #return dici
        return dici, diclist
    
    def __exportSampleSheet(self, parentList, sampleTypes, sampleTypeCount, headers, excelfile):
        ''' Export a list of samples in a sample sheet so that it can be used for uploading the list into Seek.
        
        Notes:
            The format of the excel file exported here is different from __saveSampleList(), which also includes the parent and child sample info.
        
        Input:
            diclist, a list of dictionaries, such as,
                [
                  {'CEL':'CEL-200225WHI-1', 'LYS':'LYS-200225WHI-1', 'D.MSP':'D.MSP-200225WHI-1', 'A.MSP':'A.MSP-200225WHI-1'}
                  ...
                ]
            
            sampleTypes, an ordered list of sample types, such as ['CEL', 'LYS', 'D.MSP', 'A.MSP']
        
        Output:
            into an excel file
        '''
        #print("__saveSampleList")
        
        # Step 2. Get the list of samples based on their uids
        uids = {}
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            for uid in listi:
                if uid not in uids:
                    sampleDic = self.__retrieveSampleJsonData(uid)
                    uids[uid] = sampleDic
                    
        # Step 3. Convert the diclist of sample uids into the diclist of sample values 
        diclist_new = []
        for listi in parentList:
            # such as listi = ['CEL-200225WHI-1', 'LYS-200225WHI-1', 'D.MSP-200225WHI-1', 'A.MSP-200225WHI-1']
            # or ['TIS-200721BMC-1', 'DNA-200721BMC-1', 'DNA-200721BMC-2', 'D.SEQ-200721BMC-1']
            dici_new = {}
            sampleTypeCount_now = {}        # the count of a sample type in the current list
            for uid in listi:
                if "-" in uid:
                    terms = uid.split('-')
                    sampleType = terms[0]
                    # such as "CEL"
                else:
                    # just in case for old uid
                    sampleType = uid
                
                if sampleType not in sampleTypeCount_now:
                    # such as 'DNA-200721BMC-1', the first DNA sample uid
                    sampleTypeCount_now[sampleType] = 1
                else:
                    # such as 'DNA-200721BMC-2', which is the second DNA sample type
                    sampleTypeCount_now[sampleType] = sampleTypeCount_now[sampleType] + 1

                # the total count of apperance of a sample type in any individual list of parentList
                count = sampleTypeCount[sampleType]
                if count==1:
                    #this sample type appears only once in any individual list of parentList,
                    # no suffix is neccessary
                    prefix = sampleType + ':'       # such as "TIS:"
                else:
                    #this sample type appears more than once in any individual list of parentList,
                    # add a suffix with the current count
                    suffix = "_" + str(sampleTypeCount_now[sampleType])
                    prefix = sampleType + suffix + ':'       # such as "DNA_2:"
                
                sampleDic = uids[uid]
                if sampleDic is not None and sampleDic is not []:
                    for key, value in sampleDic.iteritems():
                        newkey = prefix + key
                        dici_new[newkey] = value        
            diclist_new.append(dici_new)
        
        # Step 5. Output the list of samples into the excel file.
        #
        #saveExcelDiclist(excelfile, headers, diclist_new, 'samples')
        
        # remove any header that does not have any value in the diclist
        headers_new = filterDiclist(headers, diclist_new)
        #print("headers:", headers)
        #print("headers_new:", headers_new)
        
        # only save sample sheet
        #saveDiclistIntoExcel(diclist_new, excelfile, headers_new, 'samples')
        
        # get a list of headers that contain variable values, and
        # a list of headers that contain constant values
        headers_noneConstant, diclist_constant, headers_constant = getConstantRows(headers_new, diclist_new)
        #print("headers_noneConstant:", headers_noneConstant)
        #print("headers_constant:", headers_constant)
        
        # save two diclists into an excel file with "samples" tab and "constants" tab
        saveTwoDiclistsIntoExcel(excelfile, diclist_new, headers_noneConstant, 'samples', diclist_constant, headers_constant, 'constants')

        nsamples = len(diclist_new)
        return nsamples
        
    def __publishSampleList(self, user_seek, sample_ids, xlsfile, assay_id=None, project_id=None):
        ''' Delete a list of samples, check whether the sample in deletion has any child sample, given
        Input:
            sample_ids, the list of sample ids, which is expected to be in the sample sample type.
            
        Output

        '''
        #user_id = user_seek['user_id']
        #roles_mask = self.db.retrieveFieldValue(People, user_id, 'roles_mask')
    
        status = 1
        msg = ''
        #records = []
        sample_type_id = None
        sattr = DBtable_sampleattribute()
        headers = None
        diclist = []
        for sample_id in sample_ids:
            record = self.__retrieveSampleByID(sample_id)
            if record is None:
                msgi = 'Error: Sample id ' + str(sample_id) +  ' not found in DB '
                status = 0
                msg += msgi + '<br/>'
                continue
            
            #contributor_id = record['contributor_id']
            #policy_id = record['policy_id']
            #currentuid = record['uuid']
            #json_metadata = record['json_metadata']
            
            if sample_type_id is None:
                sample_type_id = record['sample_type_id']
                attributeInfo = sattr.getAttributeInfo(sample_type_id)
                headers = attributeInfo['headers']
            else:
                if sample_type_id!=record['sample_type_id']:
                    msgi = 'Error: Sample id ' + str(sample_id) +  ' is not in the sample sample type with other sample'
                    status = 0
                    msg += msgi + '<br/>'
                    continue
            
            #records.append(record)
            json_metadata = record['json_metadata']
            #print('json_metadata:', json_metadata)
            dici = self.__getRecordFromJson(json_metadata)
            dici_rev = {}
            for header in headers:
                hi = header.lower().strip()
                if hi in dici:
                    dici_rev[header] = dici[hi]
                else:
                    dici_rev[header] = ''
            
            #print('dici:', dici)
            diclist.append(dici_rev)
        
        #sampleTypes, sampleTypeCount, headers, headersMapping = self.__getSampleTypeAttributes(sampleList)
        #nsamplesOutput = self.__saveSampleList(sampleList, sampleTypes, sampleTypeCount, headers, xlsfile)

        
        #headers = ['id', 'uid', 'sample_type', 'first_name', 'created_at', 'json_metadata', 'statusi']
        isNewSheet = False
        #saveDiclistIntoExcel(diclist, xlsfile, headers, 'Samples', isNewSheet)
        
        # support latest excel file, rather than old xls file
        excelfile = xlsfile
        saveExcelDiclist(excelfile, headers, diclist, 'Samples', isNewSheet)
        
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
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sample_ids, a list of sample ids
        
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        msg, status = self.__publishSampleList(user_seek, sample_ids, xlsfile, assay_id, project_id)
        
        #self.__saveSamples(rows, xlsfile, headers)
        #data['rows'] = rows
        data = {}
        data['msg'] = msg
        data['status'] = status
        data['link'] = link
        data['ptype'] = 'Sample'
        #data['diclist'] = diclist
        
        reportData = simplejson.dumps(data)
        return reportData
    
    
    def __loadPublishedSampleSheet(self, excelfile):
        ''' Find samples in an excel file for batch-exporting samples
        when the url "/seek/samplefind/" is selected on publishAssets_search.embed.html.
        Input:
            excelfile, an excel file, contains a list ofsamples published at FairdomHub.
       
        Output:
            status
            msg
        
        '''
        msg = "loadPublishedSampleSheet"
        status = 0
        sampletype = ''
        uids = []
        
        # Step 1. Load the input excel file
        try:
            filedata = load_excelfile_asdic(excelfile)
        except:
            msg = "Error: sample excel file can't be loaded."
            status = 0
            print(msg)
            return msg, status, sampletype, uids
        
        # Step 2. Verify the input Sample sheet
        status = filedata['status']
        msg = filedata['msg']
        if status==0:
            print(msg)
            return msg, status, sampletype, uids
        
        print(filedata['sheetnames'])
        
        if 'SAMPLES' not in filedata['sheetnames'] or 'SAMPLES' not in filedata:
            msg = "Error: Samples sheet not in the excel."
            status = 0
            print(msg)
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
                print(msg)
                return msg, status, sampletype, uids
            n += 1
        
        return msg, status, sampletype, uids
        
    
    def findSamplesForExport(self, user_seek, downloadfile, link, excelfile):
        ''' Find samples in an excel file for batch-exporting samples
        when the url "/seek/samplefind/" is selected on publishAssets_search.embed.html.
        Input:
            excelfile, an excel file, contains a list ofsamples published at FairdomHub.
        
        Output:    
            downloadfile, file name for exporting samples, in excel or zip format.
            link, url of the file for exporting samples.
        
        '''
        username = user_seek['username']
        
        msg, status, sampletype, uids = self.__loadPublishedSampleSheet(excelfile)
        if status==0:
            data = {}
            data['link'] = link
            data['msg'] = msg
            data['status'] = 0
            reportData = simplejson.dumps(data)
            return reportData
        
        sample_ids = []
        for uid in uids:
            sample_id = self.getSampleID(uid)
            sample_ids.append(sample_id)
            
        #stype = DBtable_sampletype()
        #sampletypeName = stype.retrieveFieldValue(sampletype_id, 'title')
        
        sdata = self.__exportSamples0(user_seek, downloadfile, link, sample_ids, sampletype)
        return sdata
        
    def getSampleType(self, user_seek, sampletype_id, attribute):
        ''' Search a list of records and show is in a dataGrid on the front page,
            from customized joint query on multiple Django models/tables.
        
        The function to overload the virtual function in dbtable.py, called by
            processRecords() in dbtable.py.
         
        Input:
            user_seek,
            sampletype_id, primary key in sample_types table;
            attribute, one of attributes defined in sample_attributes table;
                    
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        if attribute=='none':
            msg = 'ignore validation'
        else:
            sattr = DBtable_sampleattribute()
            msg, status = sattr.validateFilters(sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
            print("validateFilters:", msg)
            if status==0:
                data = {'msg':msg, 'status': status}
                reportData = simplejson.dumps(data)
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
        
        reportData = simplejson.dumps(data)
        return reportData
    
    def __updateSampleMeta(self, metadata_db, diclist_attributes, attri_renamed):
        ''' Update the metadata for an existing sample in DB with the following logic:
                Keep existing metadata unchanged, unless there is new change in the input metadata.
                
        Input:
            metadata_db, a dictionary of the metadata from DB for a sample;
            metadata_in, a dictionary of the metadata for a sample from the input, such as from the assay sheet uploading.
            diclist_attributes, the list of dictionaries for each of attributes of a sample type.
            attri_renamed, a dictionary in the format:
                attri_mapping[atrribute_newName] = atrribute_oldName
        Output:
            metadata_out, a dictionary of the metadata, which combines both metadata_db and metadata_in so that only attribute from input is updated,
                while rest of attributes remain the same. 
        
        Notes:
            This is the function to keep metadata_db unchanged and update only those attributes in the metatdata_in,
        
        Requirement:
            The new value must not be None or empty.
        '''
        print("__updateSampleMeta")
        print("metadata_db:", metadata_db)
         
        # Step 1: update attributes that are already in DB
        metadata_out = {}
        
        #for key, value in metadata_db.items():
        for dici in diclist_attributes:
            #print(dici)
            #accessor_name = dici['accessor_name']
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
        
        print("metadata_out:", metadata_out)
        return metadata_out
        
    
    def __updateSamplesMeta(self, user_seek, samples, sampletype_id, attri_renamed):
        ''' Update meta data of samples, after sample attribute is revised, such as added, deleted, or renamed.
         
        Input:
            sampletype_id, primary key in sample_types table;
            samples, a list of sample records from the DB.
            attri_renamed, a dictionary in the format:
                attri_mapping[atrribute_newName] = atrribute_oldName
            
        Output
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
            
        '''
        
        # Step 1. Retrieve sample attribute information
        sattr = DBtable_sampleattribute()
        attributeInfo = sattr.getAttributeInfo(sampletype_id)
        diclist_attributes = attributeInfo['diclist']
        
        
        username = user_seek['username']
        
        # Step 1. get the list of values used for filtering
        n = 0
        nright = 0
        msg = ''
        status = 1
        for record in samples:
            
            json_metadata = record['json_metadata']
            metadata_db = self.__getRecordFromJson(json_metadata)
            
            #metadata_out = self.__updateSampleMetadata(metadata_db, metadata_in)
            metadata_out = self.__updateSampleMeta(metadata_db, diclist_attributes, attri_renamed)
            
            # revise 
            record['json_metadata'] = simplejson.dumps(metadata_out)
            record['updated_at'] = getDefaultDateTime()

            # update sample info in DB 
            msgi, statusi, sample_id = self.storeOneRecord(username, record)
            if statusi:
                nright += 1
            else:
                status = 0
                msg += msgi +  '<br/>'
            
            n += 1
            
        print("Number of samples revised: ", n)
        print("Number of samples revised correctly: ", nright)
        return msg, status
    
    
    def updateSampleType(self, user_seek, sampletype_id, attri_renamed):
        ''' Update the meta data of all samples for a sample type.
            This function is usually called after an attribute is added into or deleted from a sample type.
            Mainly for the consistency check, given the latest list of attributes defined for a sample.
                 
        Input:
            user_seek,
            sampletype_id, primary key in sample_types table;
            attri_renamed, a dictionary in the format:
                attri_mapping[atrribute_newName] = atrribute_oldName
                     
        Output
           
        '''

        # Step 1. Retrieve all samples for a sample type
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
        #data = {'total':total,'rows':jdata_new,'footer':footer}
        
        # Step 2. Revise the metadata of those samples
        msg, status = self.__updateSamplesMeta(user_seek, data['rows'], sampletype_id, attri_renamed)
        data['msg'] = msg
        data['status'] = status
        data['link'] = ''
        
        reportData = simplejson.dumps(data)
        return reportData