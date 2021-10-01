'''
Created on July 12, 2016

@author: Huiming Ding
Email: huiming@mit.edu

Description:

This script is implemented for the Documents database/table.

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

from .models import Documents
from dmac.dbtable import DBtable

# This is the mapping between the field name used in DataGrid table 
# and the field name used in the SQL query for DB retrieval 
DOCUMENT_FILTER_MAPPING = {
}

# Default values for Sample table
DOCUMENT_DEFAULT = {
    #'id':'',
    'title':''
}

class DBtable_documents(DBtable):
    ''' The class stores all the information about the table [Sample].[dbo].[Sample]
    
    Typical usage of the class
    
        documents = DBtable_documents("DEFAULT")
        return documents.retrieveTableList(request)

    '''
    def __init__(self, whichServer='default'):
        print "DBtable_documents"
        DBtable.__init__(self, 'SEEK', 'seek_development')
        
        self.tablename = 'documents'
        self.tablemodel = Documents
        self.fulltablename = self.tablemodel
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.dbname + '.' + self.tablename
        self.fields = [
            'id',
            'title',
            'description',
            'contributor_id',
            'version',
            'first_letter',
            'uuid',
            'policy_id',
            'doi',
            'license',
            'last_used_at',
            'created_at',
            'updated_at',
            'other_creators',
            'deleted_contributor'
        ]
        
        # the unique constraint to find the primary key
        self.uniqueFields = ['title']
        # The primary key name
        self.primaryField = "id"
        self.fieldMapping = DOCUMENT_FILTER_MAPPING
        self.excludeFields = []
        
    def getOptionsDocuments(self, id, keyword):
        ''' Get a list of documents from documents table in the format of options, used in
        a ComboBox.
    
        Input:
            id, the option selected, if a valid id>0;
            keyword, the keyword used for filtering the list of documents based on the title.
        
        Output:
            options, = [op1, op2,...], where
                opi = {valueField:vi, textField:txti, 'selected':True}
                For example,
                    options = [
                        {'id':0, 'title':' ', 'selected':True},
                        {'id':1, 'title':'A'},
                        {'id':2, 'title':'B'},
                        ...
                    ]
                    
        Usage:
            doc = DBtable_documents()
            sampleTemplates = doc.getOptionsDocuments(id, "Sample Sheet Template")
        '''
        queryset = self.tablemodel.objects.all()
    
        # the followinng format is for a Django form choiceField 
        #type_options = [ (qi.id, qi.title) for qi in queryset]
    
        # the following format is for an easyUI comboBox
        options = []
        if id==0:
            options.append({'id':0, 'title':'','selected':True})
        else:
            options.append({'id':0, 'title':''})

        for qi in queryset:
            if keyword in qi.title:
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

    def __getInfo(self, document_id, server, username, password):
        ''' Gets the SEEK user ID based on the login user name.

        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password
            
            document_id, the id in documents table, based on the login user name,
                retrieved from API.
        Returns:
            The profile of the document.
            
        Example,
            json_document, for example,
            {
                "data": {
                    "id": "14",
                    "type": "documents",
                    "attributes": {
                        "policy": {
                            "access": "download",
                            "permissions": [
                                {
                                    "resource_type": "projects",
                                    "resource_id": "359",
                                    "access": "edit"
                             }
                            ]
                        },
                        "title": "A Maximal Document",
                        "description": "This is the description",
                        "license": "CC-BY-4.0",
                        "latest_version": 1,
                        "tags": [
                            "tag1",
                            "tag2"
                        ],
                        "versions": [
                            {
                                "version": 1,
                                "revision_comments": null,
                                "url": "http://localhost:3000/documents/14?version=1"
                            }
                        ],
                        "version": 1,
                        "revision_comments": null,
                        "created_at": "2018-04-27T14:26:09.000Z",
                        "updated_at": "2018-04-27T14:26:09.000Z",
                        "content_blobs": [
                        {
                            "original_filename": "a_pdf_file.pdf",
                            "url": null,
                            "md5sum": null,
                            "sha1sum": null,
                            "content_type": "application/pdf",
                            "link": "http://localhost:3000/documents/14/content_blobs/48",
                            "size": null
                        }
                        ],
                        "other_creators": "John Smith, Jane Smith"
                    },
                    "relationships": {
                        "creators": {
                            "data": [
                            {
                                "id": "234",
                                "type": "people"
                            }
                            ]
                        },
                        "submitter": {
                            "data": [
                            {
                                "id": "233",
                                "type": "people"
                            }
                            ]
                        },
                        "people": {
                            "data": [
                            {
                                "id": "233",
                                "type": "people"
                            },
                            {
                                "id": "234",
                                "type": "people"
                            }
                            ]
                        },
                        "projects": {
                            "data": [
                            {
                                "id": "359",
                                "type": "projects"
                            }
                            ]
                        },
                        "investigations": {
                            "data": [
                            {
                                "id": "51",
                                "type": "investigations"
                            }
                            ]
                        },
                        "studies": {
                            "data": [
                            {
                                "id": "51",
                                "type": "studies"
                            }
                            ]
                        },
                        "assays": {
                            "data": [
                            {
                                "id": "38",
                                "type": "assays"
                            }
                            ]
                        },
                        "publications": {
                            "data": []
                        }
                    },
                    "links": {
                        "self": "/documents/14?version=1"
                    },
                    "meta": {
                        "created": "2018-04-27T14:26:09.713Z",
                        "modified": "2018-04-27T14:26:10.078Z",
                        "api_version": "0.1",
                        "uuid": "da7cb1a0-2c54-0136-ec2f-08002734982f",
                        "base_url": "http://localhost:3000"
                    }
                },
                "jsonapi": {
                    "version": "1.0"
                }
            }
        '''
        from .seekdb import SeekDB
        seekdb = SeekDB(server, username, password)
        return seekdb.getInfoObject("/documents/", document_id)
        
        
    def getDownloadURL(self, document_id, server, username, password):
        ''' Gets the SEEK user ID based on the login user name.

        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password
            
            document_id, the id in documents table, based on the login user name,
                retrieved from API.
        Returns:
            The url for downloading the document, such as
                "/documents/7/content_blobs/333/download"
            
        '''
        infodata = self.__getInfo(document_id, server, username, password)
        if infodata is None or document_id==0:
            docurl = ''
            msg = 'Error: the data for the document is not available at ID=' + str(document_id)
            print(msg)
            return None, None
        
        #print(infodata)
        #for item in infodata:
        #    print item
        attributes = infodata["attributes"]
        #for item in attributes:
        #    print item
            
        content_blobs = attributes["content_blobs"]
        docurl = infodata["attributes"]["content_blobs"][0]["link"]
        docurl = docurl + "/download"
        
        filename = infodata["attributes"]["content_blobs"][0]["original_filename"]
        print(docurl)
        return docurl, filename
        
        
        