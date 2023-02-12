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

DOCUMENT_FILTER_MAPPING = {
}

DOCUMENT_DEFAULT = {
    #'id':'',
    'title':''
}

class DBtable_documents(DBtable):
    def __init__(self, whichServer='default'):
        DBtable.__init__(self, 'SEEK', 'seek_development')
        self.tablename = 'documents'
        self.tablemodel = Documents
        self.fulltablename = self.tablemodel
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
        
        self.uniqueFields = ['title']
        self.primaryField = "id"
        self.fieldMapping = DOCUMENT_FILTER_MAPPING
        self.excludeFields = []
        
    def getOptionsDocuments(self, id, keyword):
        queryset = self.tablemodel.objects.all()
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
    
        return simplejson.dumps(options)

    def __getInfo(self, document_id, server, username, password):
        from .seekdb import SeekDB
        seekdb = SeekDB(server, username, password)
        return seekdb.getInfoObject("/documents/", document_id)
        
        
    def getDownloadURL(self, document_id, server, username, password):
        infodata = self.__getInfo(document_id, server, username, password)
        if infodata is None or document_id==0:
            docurl = ''
            msg = 'Error: the data for the document is not available at ID=' + str(document_id)
            return None, None
        
        attributes = infodata["attributes"]
        content_blobs = attributes["content_blobs"]
        docurl = infodata["attributes"]["content_blobs"][0]["link"]
        docurl = docurl + "/download"
        
        filename = infodata["attributes"]["content_blobs"][0]["original_filename"]
        return docurl, filename
        
        
        