'''
Created on 11/07/2018

@author: Huiming Ding
Email: huiming@mit.edu

Description:

All customized server-side python scripts for EasyUI DataGrid.

Input:  No typical input to define.
       
Output: No typical output to define.
        
Example command line:
     
Log of changes:
     
'''
#!/usr/bin/env python

import json

# introduce logging 
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

# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY


class DataGrid(object):
    ''' The class processes all EasyUI dataGrid related server-side scripts.
    
    Typical usage of the class
    
        dgtable = DataGrid(dbtable)
        dgtable.process(request)
        
    '''
    def __init__(self, dbtable):
        ''' The mapping between a EasyUI dataGrid table on the client-side on a html page and the table class in the database.
        input 
            dbtable,  a class for a table or joint of tables in database. For instance,
                dbtable = DBtable_alumni("DEFAULT")
            
        Output
            Initilization of this class.
        '''
        self.dbtable = dbtable
        if dbtable is None:
            self.db = None
        else:
            self.db = dbtable.db
        
    def __querySuffix(self, ret):
        ''' Generate the piece used in a sql query that defines the number and order of records retrieved.
        Input      
            ret = request.GET, which contains the definition of 'page', 'rows', 'sort' and 'order'.
        
        Output
            For instance, when page=21, rows=50, sort='id', 'order'='asc', the output is,
                "LIMIT 1000,50 ORDER BY id asc"
        '''
        if 'rows' in ret:
            page = ret['page']
            rows = ret['rows']
            msg = "page: " + page + " rows: " + rows
            #logger.debug(msg)
            offset = (int(page)-1)*int(rows)     
            limit = " LIMIT " + str(offset) + "," + rows
        else:
            limit = ""
        
        msg = 'limit: ' + limit
        #logger.debug(msg)
    
        orderby = ""
        if 'sort' in ret:
            sort= ret['sort']
            print "sort: ", sort
    
            # The sort order, can be 'asc' or 'desc', default is 'asc'.
            order = 'desc'
            if 'order' in ret:
                order= ret['order']
                print "order: ", order
        
            orderby = " ORDER BY " + sort + " " + order + " "
        
        print "orderby: ", orderby
        suffix = orderby + limit
    
        #logger.debug(suffix)
    
        return orderby, limit

    def __getStartRows(self, limit):
        ''' Given limit from querySuffix(ret), convert offset, rows back to startNo and endNo.
        '''
        print "getStartRows"
        # example: limit = " LIMIT offset,rows"
        strs1 = limit.strip().split(' ')        # such as strs1=["LIMIT", "offset,rows"]
        #print strs1
        offset = 0
        rows = 0
        if len(strs1)>1:
            strs2 = strs1[1].split(',')         # such as strs2=["offset", "rows"]
            if len(strs2)>1:
                offset = int(strs2[0])
                rows = int(strs2[1])
        
        print "OFFSET: ", offset, "ROWS: ", rows    
        startNo = offset
        endNo = offset + rows
    
        return startNo, endNo

    def __getFilteringParameters(self, ret):
        ''' Get the filtering parameters for server-side filtering. For more detail, refer to
        dokuwiki/doku.php?id=computer:software:jscript:easyui:datagrid-filtering
    
        For example,
        
            ret = request.GET
            if 'filterRules' in ret:
                print ret['filterRules']

            [{"field":"unit","op":"contains","value":"Amon"}]
        
        each filtering parameter contains three components:

            "field":"unit", the field (column) name in the table;
            "value":"Amon", the keyword used for the filtering;
            "op":"contains", type of match, in this case, it is "contains".

        The filtering parameter in the example above can be converted into the SQL query below,

            WHERE unit LIKE '%Amon%'
        '''
        print "getFilteringParameters"
        filterRules = []
        sqlquery_filter = ""
        if 'filterRules' not in ret:
            return sqlquery_filter, filterRules
        
        filterRules = ret['filterRules']
        #print filterRules
        if filterRules is None:
            return sqlquery_filter, filterRules
        
        filterRules = json.loads(filterRules)
    
        n = 0
        for rule in filterRules:
            #print rule
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
        
        #print sqlquery_filter
        return sqlquery_filter, filterRules
    
    def getDatagridFilters(self, ret):
        ''' Given a DataGrid table on the html GUI, get all parameters used in the SQL query.
        Input
            ret, = request.GET
        Output
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        '''
        filtersdic = {}
    
        orderby, limit = self.__querySuffix(ret)
        filtersdic['orderby'] = orderby
        filtersdic['limit'] = limit
    
        suffix = orderby + limit
        print "suffix ", suffix
        filtersdic['suffix'] = suffix
    
        startNo, endNo = self.__getStartRows(limit)
        filtersdic['startNo'] = startNo
        filtersdic['endNo'] = endNo
    
        sqlquery_filter, filterRules = self.__getFilteringParameters(ret)
        filtersdic['sqlquery_filter'] = sqlquery_filter
        filtersdic['filterRules'] = filterRules
    
        return filtersdic
    
    def getDataGridData(self, request, username):
        ''' get records for saving into DB when saveSelectedIntoDB() is called in the jscript on a dataGrid table.
        Arguments:
            request, the http request from client side.
            username
        Returns:
            data = {'status':'', 'message':'', 'link':'', 'records':records},
                where records is a list of records for saving into DB. 
            
        Usage:
    
            from datagrid import saveSelectedIntoDB
            def saveRecords(request):
                username = str(request.user)
                if verifyUser(request)==0:
                    username = None
        
                data = getDataGridData(request, username)
                if 'records' in data:
                    records = data['records']
                    sponsor = DBtable_sponsor("DEFAULT")
                    data = sponsor.saveRecords(username, records)
                return HttpResponse(simplejson.dumps(data))
        '''
        #print "saveSelectedIntoDB"
        ret = request.GET
        data = {}
        data["status"] = 0
        data["msg"] = "Processing records"
        # link returns either the link url for download or redirection to window.location.href = link;
        data["link"] = ""
        if 'records' not in ret:
            data["msg"] = "Warning: No data provided for processing records."
            return data
        
        if username is None:
            data["msg"] = "Error: user login required."
            return data
      
        #print ret
        records = ret['records']
        records = json.loads(records)
        #print records
        data['records'] = records
        data["status"] = 1
        return data
    
    def sqlQuery_select_filters(self, filtersdic, fieldMapping):
        ''' Generate SQL query filters basedon the parameters from DataGrid on front GUI.
        Input
            filtersdic = {}, a dictionary with all parameters, including
            filtersdic['orderby'], such as " ORDER BY id asc " or " ";
            filtersdic['limit'], such as " LIMIT 1000,50 " or " ";
            filtersdic['suffix'], such as " LIMIT 1000,50 ORDER BY id asc " or " ";
            filtersdic['startNo'], such as 1000;
            filtersdic['endNo'], such as 1050;
            filtersdic['sqlquery_filter'], such as " lastname LIKE '%Amon%' and firstname LIKE '%John%' "
            filtersdic['filterRules'], such as [{"field":"unit","op":"contains","value":"Amon"}]
            
            fieldMapping, = {'fieldname1_dg':'fieldname1_db', ...}, where
                filename_dg is the field name used in DataGrid, such as 'ki_id';
                filename_db is the field name used in database table, such as 'KI_ID'.
        Output
            sqlquery_filters = " WHERE xxxx=yyy..."
        '''
        filterRules = filtersdic['filterRules']     # such as [{"field":"unit","op":"contains","value":"Amon"}]
        sqlquery_filter = ""
        n = 0
        for rule in filterRules:
            #print rule
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
        ''' Retrieve a list of records from the table in databased, defined by self.dbtable, according to
        dataGrid filtering, sorting and ordering.
        
        Input
            isReformat, if true, the filterRules and resulting dataset will be reformated by self.dbtable
                        if false, the filterRules and resulting dataset will not be reformated by self.dbtable
        
        Output
            A list of dictionaries, retrieved from database table.
            
            
        Requirement
            dbtable.formatRule(filterRulesIn):
                # refer to dbtable_alumni.__formatCancerRelatedrule(filterRules) for example.
                filterRules = filterRulesIn
                return filterRules
                
            dbtable.reformatData(jdata):
                # refer to dbtable_alumni.alumnilist() for example.
                jdata_new = jdata
                return jdata_new
        '''
        filterRules = self.dbtable.formatRule(self.filterRules)
        
        qset = self.db.generateQuerySet(filterRules)
        jdata = self.db.retrieveJoint(self.dbtable.tablemodel, '', qset, self.orderby, self.limit)
        '''
        jdata_new = []
        for dici in jdata:
            #print dici
            for field in ['last_name_ki', 'first_name_ki', 'employer']:
                term = dici[field]
                dici[field] = term.encode('ascii', 'ignore')
                
            value = dici['employment_cancer_related']
            if value is None:
                value = 'N/A'
                value = '?'
            elif value==1:
                value = "Yes"
            elif value==0:
                value = "No"
            else:
                value = 'N/A'
                value = '?'
            dici['employment_cancer_related'] = value
            dici['date_uploaded'] = ''
            jdata_new.append(dici)
        '''
        jdata_new = self.dbtable.reformatData(jdata)
        
        total = self.db.retrieveTotalRecords(self.dbtable.tablemodel, qset)
        return jdata_new, total
    
    def __uploadExcelFile(self, excelfile, feedbackfile):
        ''' Batch upload of record(s) in an excel file into the database table, defined in dbtable;
            # refer to dbtable_alumni.uploadAlumni(self, infile)
            
        Input
            excelfile, record(s) in an excel file
            
        Output
            msg
            status
        
        Requirements
            dbtable.headersMapping() must be available, which is the mapping between headers in the excel file
                and the headers used in the database table.
                
            dbtable.storeRecord(csvdic)
        '''
        msg, status, jdata, total = self.dbtable.upload(excelfile, feedbackfile)
        if status==1:
            return msg, status, jdata, total
        
        #csvdata = load_file(infile, ALUMNUS_MAPPING)
        headersMapping = self.dbtable.headersMapping()
        csvdata = load_file(excelfile, headersMapping)
        #csvdata = load_excelfile(infile)
        status = csvdata['status']
        msg = csvdata['msg']
        
        jdata = []
        total = len(jdata)
        #print msg, status
        if status:
            msg = "excel file loaded okay"
        else:
            print msg
            return msg, status, jdata, total
        
        #return msg, status
        
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
        ''' Batch upload of record(s) in an excel file into the database table, defined in dbtable;
            # alumniUploadAjax(request)
            
        Input
            request
            
        Output
            msg
            status
        
        Requirements
            dbtable.headersMapping() must be available, which is the mapping between headers in the excel file
                and the headers used in the database table.
                
            dbtable.storeRecord(csvdic)
        '''
        msg = 'Uploading records'
        status = 0
        link = ""
        if request.method == "POST":
            if request.FILES and request.FILES.get('excelfile_upload'):
                excelfile = request.FILES['excelfile_upload']
                if excelfile:
                    print excelfile.name
                    
                    infilename = excelfile.name
                    names = infilename.split(".")
                    #print names
                    prefix = names[0]
                    filename = prefix + "_feedback.xls"
                    feedbackfile = DOWNLOAD_DIRECTORY + filename
                    link = DOWNLOAD_DIRECTORY_LINK + filename
                    
                    #alumni = DBtable_alumni("DEFAULT")
                    #msg, status = alumni.uploadAlumni(excelfile)
                    msg, status, jdata, total = self.__uploadExcelFile(excelfile, feedbackfile)
                    
        return msg, status, link
        
    def __download(self, allids, downloadallterms):
        ''' Batch upload of record(s) in an excel file into the database table, defined in dbtable;
            # alumniUploadAjax(request)
            
        Input
            request
            
        Output
            msg
            status
            link
        Requirements
            dbtable.downloadRecords()
        '''
        datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H")
        #filename = 'grants_records' + datenow + '.csv'
        filename = self.dbtable.tablename + "-" + datenow + '.xls'
        excelfile = DOWNLOAD_DIRECTORY + filename
        link = DOWNLOAD_DIRECTORY_LINK + filename
        
        #print excelfile
        self.dbtable.downloadRecords(allids, excelfile, downloadallterms)
        msg = 'Retrieved in ' + filename
        status = 1
        
        return msg, status, link
    
    def __delete(self, ids):
        ''' remove record(s) from the database table, defined in dbtable;
            # refer to dbtable_alumni.deleteAlummae(ids)
            
        Input
            ids, a list of primary keys
            
        Output
            msg
            status
        Requirements
            
        '''
        for id in ids:
            print "delete id: ", id
            #self.db.deleteOneRecord(self.tablemodel, id)
            #b = self.dbtable.tablemodel.objects.get(pk=id)
            # This will delete the record and all of its child objects.
            #b.delete()
            self.dbtable.delete(id)
        
        status = 1
        msg = "Deleting records successfully"
        return msg, status
    
    def __save(self, records):
        ''' Save record(s) into the database table, defined in dbtable;
            # refer to dbtable_alumni.saveAlummae(records)
            
        Input
            records, a list of records to be saved into table.
            
        Output
            msg
            status
        Requirements
            Given the record from either one row in an excel file or from client-side table,
            reformat it.
            self.dbtable.formatRecord(record):
                record_new = record
                return record_new
            
        '''
        statusTest = 1
        msgTest = ""
        for record in records:
            #print record
            #record_new = self.dbtable.formatRecord(record)
            #self.db.storeOneRecord(self.dbtable.tablemodel, record_new)
            msg, status = self.dbtable.storeOneRecord(record)
            if status==0:
                msgTest += msg
                statusTest = 0
            
        print "__save:", msgTest, statusTest
        return msgTest, statusTest
        
    def process(self, request, operation):
        ''' Process http request from client-side for various operations.
        Input
            request, a http request;
            operation, the name of operation through the request, such as,
                save, save record(s) into the database table, defined in dbtable;
                delete, remove record(s) from the database table, defined in dbtable;
                download, batch download of record(s) in an excel or pdf file from the database table, defined in dbtable;
                upload, batch upload of record(s) in an excel file into the database table, defined in dbtable;
                retrieve, retrieve a list of records from the database table, defined in dbtable, according to the filtering and sorting parameters.
        
        '''
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
            # retrieve a list of records from the database table, defined in dbtable, according to the filtering and sorting parameters.
            # alumni(request)
            # jdata, total = alumni.alumnilist(orderby, limit, filterRules)
            jdata, total = self.__retrieve()
            status = 1
            msg = "Retrieved number of records: " + str(len(jdata))
        elif operation=="upload":
            # batch upload of record(s) in an excel file into the database table, defined in dbtable;
            # alumniUploadAjax(request)
            msg, status, link = self.__upload(request)
        elif operation=="download":
            # batch download of record(s) in an excel or pdf file from the database table, defined in dbtable;
            if 'allids' in ret:
                allids = json.loads(ret['allids'])
                downloadallterms = json.loads(ret['downloadallterms'])
                msg, status, link = self.__download(allids, downloadallterms)
        elif operation=="delete":
            # delete, remove record(s) from the database table, defined in dbtable;
            if 'ids' in ret:
                IDs = ret['ids']
                ids = json.loads(IDs)
                msg, status = self.__delete(ids)
        elif operation=="save":
            if 'records' in ret:
                records = ret['records']
                #print "grantIDs: ", grantIDs
                # such as ["<a href="/grant/id=1995/">1995</a>"], where it is the link to a grant
                # therefore, it will cause an error in json.loads(grantIDs) because it has four " in the link.
                records = json.loads(records)
                msg, status = self.__save(records)
        
        data = {'total':total,'rows':jdata,'footer':footer, 'msg':msg, 'status': status, 'link': link}
        #print data
        reportData = simplejson.dumps(data)
        return HttpResponse(reportData)    

    def formatRule(self, filterRules, boolfield):
        '''  Re-format the filtering rule for 'employment_cancer_related', which
        could be either "yes", "No" or "N/A" on GUI page but should be 1, 0 or -1 in DB search.
        Input
            boolfield, such as 'employment_cancer_related', in yes, no or N/A
        
        Output
            bool value, such as 1,0,-1
        Notes:
        Used in retrieve(request).
    
        '''
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