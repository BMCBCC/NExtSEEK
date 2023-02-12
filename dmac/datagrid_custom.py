#!/usr/bin/env python

import json
import logging
logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django import forms

from django.conf import settings

import simplejson
import json
import datetime

from csv_excel import load_file, load_excelfile

DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/' 

class DataGrid(object):
    def __init__(self, dbtable):
        self.dbtable = dbtable
        if dbtable is None:
            self.db = None
        else:
            self.db = dbtable.db
        
    def __querySuffix(self, ret):
        if 'rows' in ret:
            page = ret['page']
            rows = ret['rows']
            msg = "page: " + page + " rows: " + rows
            offset = (int(page)-1)*int(rows)     
            limit = " LIMIT " + str(offset) + "," + rows
        else:
            limit = ""
        
        msg = 'limit: ' + limit
        orderby = ""
        if 'sort' in ret:
            sort= ret['sort']
            order = 'desc'
            if 'order' in ret:
                order= ret['order']
        
            orderby = " ORDER BY " + sort + " " + order + " "
        
        suffix = orderby + limit
        return orderby, limit

    def __getStartRows(self, limit):
        strs1 = limit.strip().split(' ')       
        offset = 0
        rows = 0
        if len(strs1)>1:
            strs2 = strs1[1].split(',')        
            if len(strs2)>1:
                offset = int(strs2[0])
                rows = int(strs2[1])
          
        startNo = offset
        endNo = offset + rows
        return startNo, endNo

    def __getFilteringParameters(self, ret):
        filterRules = []
        sqlquery_filter = ""
        if 'filterRules' not in ret:
            return sqlquery_filter, filterRules
        
        filterRules = ret['filterRules']
        if filterRules is None:
            return sqlquery_filter, filterRules
        
        filterRules = json.loads(filterRules)
    
        n = 0
        for rule in filterRules:
            field = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if n==0:
                sqlquery_filter += field
            else:
                sqlquery_filter += " AND " + field
            if op=="contains":
                sqlquery_filter += " LIKE '%" + str(value) + "%' "
            else:
                sqlquery_filter += " LIKE '%" + str(value) + "%' "
            n += 1
        
        return sqlquery_filter, filterRules
    
    def getDatagridFilters(self, ret):
        filtersdic = {}
    
        orderby, limit = self.__querySuffix(ret)
        filtersdic['orderby'] = orderby
        filtersdic['limit'] = limit
    
        suffix = orderby + limit
        filtersdic['suffix'] = suffix
    
        startNo, endNo = self.__getStartRows(limit)
        filtersdic['startNo'] = startNo
        filtersdic['endNo'] = endNo
    
        sqlquery_filter, filterRules = self.__getFilteringParameters(ret)
        filtersdic['sqlquery_filter'] = sqlquery_filter
        filtersdic['filterRules'] = filterRules
    
        return filtersdic
    
    def getDataGridData(self, request, username):
        ret = request.GET
        data = {}
        data["status"] = 0
        data["msg"] = "Processing records"
        data["link"] = ""
        if 'records' not in ret:
            data["msg"] = "Warning: No data provided for processing records."
            return data
        
        if username is None:
            data["msg"] = "Error: user login required."
            return data
      
        records = ret['records']
        records = json.loads(records)
        data['records'] = records
        data["status"] = 1
        return data
    
    def sqlQuery_select_filters(self, filtersdic, fieldMapping):
        filterRules = filtersdic['filterRules']     # such as [{"field":"unit","op":"contains","value":"Amon"}]
        sqlquery_filter = ""
        n = 0
        for rule in filterRules:
            field_dg = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if field_dg in fieldMapping:
                field_db = fieldMapping[field_dg]
            
                if n==0:
                    sqlquery_filter += " WHERE " + field_db
                else:
                    sqlquery_filter += " AND " + field_db
                if op=="contains":
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
                else:
                    sqlquery_filter += " LIKE '%" + str(value) + "%' "
            n += 1
        
        return sqlquery_filter    
    
    
    def __retrieve(self):
        filterRules = self.dbtable.formatRule(self.filterRules)
        
        qset = self.db.generateQuerySet(filterRules)
        jdata = self.db.retrieveJoint(self.dbtable.tablemodel, '', qset, self.orderby, self.limit)
        jdata_new = self.dbtable.reformatData(jdata)
        
        total = self.db.retrieveTotalRecords(self.dbtable.tablemodel, qset)
        return jdata_new, total
    
    def __uploadExcelFile(self, excelfile, feedbackfile):
        msg, status, jdata, total = self.dbtable.upload(excelfile, feedbackfile)
        if status==1:
            return msg, status, jdata, total
        
        headersMapping = self.dbtable.headersMapping()
        csvdata = load_file(excelfile, headersMapping)
        status = csvdata['status']
        msg = csvdata['msg']
        
        jdata = []
        total = len(jdata)
        if status:
            msg = "excel file loaded okay"
        else:
            return msg, status, jdata, total
        
        csvdiclist = csvdata['diclist']
        n = 0
        msg0 = '\n'
        index = 0
        for csvdic in csvdiclist:
            msgn, statusn = self.dbtable.storeRecord(csvdic)
            index += 1
            if statusn:
                n += 1
            else:
                status = statusn
                msg0 += "Row " + str(index) + ". " + msgn + "\n"
            
        if status:  
            msg = 'Total number of records uploaded successfully: ' + str(n) 
        else:
            msg = msg0
        
        return msg, status, jdata, total
    
    def __upload(self, request):
        msg = 'Uploading records'
        status = 0
        link = ""
        if request.method == "POST":
            if request.FILES and request.FILES.get('excelfile_upload'):
                excelfile = request.FILES['excelfile_upload']
                if excelfile:
                    infilename = excelfile.name
                    names = infilename.split(".")
                    prefix = names[0]
                    filename = prefix + "_feedback.xls"
                    feedbackfile = DOWNLOAD_DIRECTORY + filename
                    link = DOWNLOAD_DIRECTORY_LINK + filename
                    msg, status, jdata, total = self.__uploadExcelFile(excelfile, feedbackfile)
                    
        return msg, status, link
        
    def __download(self, allids, downloadallterms):
        datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H")
        filename = self.dbtable.tablename + "-" + datenow + '.xls'
        excelfile = DOWNLOAD_DIRECTORY + filename
        link = DOWNLOAD_DIRECTORY_LINK + filename
        
        self.dbtable.downloadRecords(allids, excelfile, downloadallterms)
        msg = 'Retrieved in ' + filename
        status = 1
        
        return msg, status, link
    
    def __delete(self, ids):
        for id in ids:
            self.dbtable.delete(id)
        
        status = 1
        msg = "Deleting records successfully"
        return msg, status
    
    def __save(self, records):
        statusTest = 1
        msgTest = ""
        for record in records:
            msg, status = self.dbtable.storeOneRecord(record)
            if status==0:
                msgTest += msg
                statusTest = 0
            
        return msgTest, statusTest
        
    def process(self, request, operation):
        ret = request.GET
        self.orderby, self.limit = self.__querySuffix(ret)
        self.suffix = self.orderby + self.limit
        self.startNo, self.endNo = self.__getStartRows(self.limit)
        self.sqlquery_filter, self.filterRules = self.__getFilteringParameters(ret)
        
        msg = operation
        status = 0
        link = " "
        total = 0
        jdata = None
        footer = {}
        if operation=="retrieve":
            jdata, total = self.__retrieve()
            status = 1
            msg = "Retrieved number of records: " + str(len(jdata))
        elif operation=="upload":
            msg, status, link = self.__upload(request)
        elif operation=="download":
            if 'allids' in ret:
                allids = json.loads(ret['allids'])
                downloadallterms = json.loads(ret['downloadallterms'])
                msg, status, link = self.__download(allids, downloadallterms)
        elif operation=="delete":
            if 'ids' in ret:
                IDs = ret['ids']
                ids = json.loads(IDs)
                msg, status = self.__delete(ids)
        elif operation=="save":
            if 'records' in ret:
                records = ret['records']
                records = json.loads(records)
                msg, status = self.__save(records)
        
        data = {'total':total,'rows':jdata,'footer':footer, 'msg':msg, 'status': status, 'link': link}
        reportData = simplejson.dumps(data)
        return HttpResponse(reportData)    

    def formatRule(self, filterRules, boolfield):
        filterRules_new = []
        for rule in filterRules:
            field = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if field==boolfield:
                value_new = convertBoolstrToInt(value)
                rule["value"] = value_new
                rule["op"] = "equal"
                
            filterRules_new.append(rule)
                
        return filterRules_new