from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django import forms

from django.conf import settings

import simplejson
import datetime
import json

from .datagrid import querySuffix, getStartRows, getFilteringParameters
from .dbtable_alumni import DBtable_alumni

# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY


# We always use report to return variables
report = {}

class DBtable_alumni(object):
    ''' The class stores all the information about the table [KI_Directory].[dbo].[KI_Directory]
    
    Typical usage of the class
    
        dbtable = DBtable_alumni()
        row = dbtable.retrieveRecord(mitid, krebid, firstname, lastname)
        dbtable.close()

    '''
    def __init__(self, whichDB):
        #print "Dbtable_cell: __init__"
        self.db = DBconnection(whichDB)
        #print "Dbtable_cell: __init__: db okay"
        self.tablemodel = "data_alumni_alumni"
        if whichDB=="DJANGO":
            self.tablemodel = Alumni
        else:
            self.tablemodel = Alumni
        self.tablename = "data_alumni_alumni"
        
    def __formatRecord(self, record):
        ''' Given the record from either one row in an excel file or from client-side table,
            reformat it accordingly so it can be stored into the database table.
        Input
            record, the dictionary in its original format.
        Output
            record, the dictionary reformated ready for storing into database table.
            
        Notes:
        Used in save(request).
        '''
        record_new = {}
        for key, value in record.items():
            key_new = str(key)
            if key_new=='employment_cancer_related':
                if value is None:
                    value = -1
                elif value=="Yes":
                    value = 1
                elif value=="No":
                    value = 0
                else:
                    value = -1
                #print "cancer_related", value
            elif key_new=='position':
                if value is None:
                    value = 'Other'
                elif len(value)==0:
                    value = 'Other'
                elif value=="":
                    value = 'Other'
                #print "position", value
            elif key_new=='type':
                if value is None:
                    value = 'Other'
                elif len(value)==0:
                    value = 'Other'
                elif value=="":
                    value = 'Other'
                #print "type", value    
            record_new[key_new] = value
            
        #print "Save record: ", record[u'cancer_related']
        #print "Save record: ", record[u'position']
        record_new['date_uploaded'] = time.strftime("%Y-%m-%d")
        return record_new
    
    def storeOneRecord(self, record):
        ''' Given the record from either one row in an excel file or from client-side table,
            reformat it accordingly so it can be stored into the database table.
        Input
            record, the record in its original format.
        Output
            record, the record reformated ready for storing into database table.
            
        Notes:
        Used in save(request).
        '''
        record_new = self.__formatRecord(record)
        self.db.storeOneRecord(self.tablemodel, record_new)

    def __sqlQuery_select_alumni_Excel_byIDs(self, orderby, allids, downloadallterms=False):
        ''' Retrieve all records.
                Input
            
            Output
                A SQL query used for retrieving records
        
        SELECT * 
            FROM djangocms.alumni_alumni A
            order by A.last_name_ki;
        '''
        sqlquery =  " SELECT * "
        sqlquery +=  "FROM alumni_alumni A "
        if downloadallterms:
            # download all records
            sqlquery += " "
        else:
            # download only selected ids
            n = len(allids)
            # download only those records on the list
            sqlquery += " WHERE A.id in ("
            ni = 0
            for id in allids:
                sqlquery += str(id)
                ni += 1
                if ni<n:
                    sqlquery += ","
            sqlquery += ") "
        
        if len(orderby)==0:
            #sqlquery += " ORDER BY c.GrantPK "
            sqlquery += " ORDER BY A.id "
        else:
            sqlquery += orderby
        
        # refer to: http://stackoverflow.com/questions/603724/how-to-implement-limit-with-microsoft-sql-server
        # Valid in MySQL only for limit=' LIMIT 1000,50 ', where 1000 is offset and 50 is the number of rows next to pull.
        #sqlquery += limit
        
        # valid since MSSQL 2012
        #sqlquery += " OFFSET 10 ROWS "
        #sqlquery += " FETCH NEXT 10 ROWS ONLY; "
        
        print sqlquery
        return sqlquery    

    def downloadRecords(self, allids, excelfile, downloadallterms=False):
        ''' Given a list of grant ids, save the list of cell information into a csv file.
        
        Notes:
        Used in download(request).
        '''
        # copy from cells.py
        #sqlquery = self.__sqlquery_searchCells(cellids, " ")
        #columns = ["id", "celltype", "cellcode", "patient", "tubecode", "tube_date", "notes",
        #           "tube2dcode", "concentration", "volume", "cell_coeff", "cell_pf_reads", "patient_alias"]
        #self.db.saveRecordsIntoCSV(sqlquery, columns, outcsvfile)

        orderby = ' ORDER BY A.last_name_ki '
        startNo = 0
        endNo = 0
        #sqlquery = self.__sqlQuery_select_active_Excel(orderby)
        sqlquery = self.__sqlQuery_select_alumni_Excel_byIDs(orderby, allids, downloadallterms)
        
        self.db.retrieveAllRecordsIntoExcel(sqlquery, HEADERS, ALUMNUS_MAPPING, excelfile)
        
    def storeRecord(self, csvdic):
        ''' Insert a new grant/grant component combo info into DB, given no known grant info found.
        Input
            csvdic, a dictionary corresponding to a row in a input csv file.
        Output
            msg, a message
            status, 0 or 1
            
        Notes:
        Used in save(request).
    
        '''
        #print "DBtable_person: __storeAlumnusComboInfo"
        if not csvdic:
            msg = "Not a valid row format!"
            print msg
            status = 0
            return msg, status
        
        last_name = csvdic['last_name_ki']
        first_name = csvdic['first_name_ki']
        if last_name is None or first_name is None:
            msg = "Not a valid name!"
            print msg
            status = 0
            return msg, status
        
        if len(last_name)==0 or len(first_name)==0:
            msg = "Not a valid name!"
            print msg
            status = 0
            return msg, status
        
        #print csvdic
        #msg = "Not a valid row format!"
        #status = 0
        #return msg, status
        
        #msg, status = self.__verifyDates(csvdic)
        
        person_id = self.__verifyPerson(csvdic)
        msg, status = self.__storePersonComboInfo(person_id, csvdic)
        return msg, status

    def __convertBoolstrToInt(self, valueIn):
        ''' Convert "yes", "no" or "unknown" type input string to int, which can be saved in DB table.
        Input
            valueIn, a string or an int, where
                a string could be either "yes", "no" or "unknown";
                a int value could be 1, 0 or -1.
        Output
            an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
                
        '''
        if valueIn is None:
            value = -1
            return value
            
        valueStr = str(valueIn)
        valueStr = valueStr.upper()
        if valueStr=="YES":
            value = 1
        elif valueStr=="NO":
            value = 0
        elif valueStr=="1":
            value = 1
        elif valueStr=="0":
            value = 0
        else:
            value = -1
            
        return value
    
    def __convertInttoBoolstr(self, valueIn):
        ''' Convert tiny int value into either "yes", "no" or "unknown" string, which can be shown on html page.
        Input
            an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
        
        Output
            valueIn, a string , either "Yes", "No" or "?" ("Unknown").    
        '''
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
            
        return value

    def formatRule(self, filterRules):
        '''  Re-format the filtering rule for 'employment_cancer_related', which
        could be either "yes", "No" or "N/A" on GUI page but should be 1, 0 or -1 in DB search.
        
        Notes:
        Used in retrieve(request).
    
        '''
        filterRules_new = []
        for rule in filterRules:
            field = rule["field"]
            value = rule["value"]
            op = rule["op"]
            if field=='employment_cancer_related':
                value_new = self.__convertBoolstrToInt(value)
                rule["value"] = value_new
                rule["op"] = "equal"
                
            filterRules_new.append(rule)
                
        return filterRules_new
    
    def reformatData(self, jdata):
        ''' Reformat the resulted diclist so it can be submitted back to the front GUI.
        Input
            jdata, the diclist retrieved from database table.
        
        Output
            jdata_new, reformated diclist.
        
        Notes:
        Used in retrieve(request).
        '''
        jdata_new = []
        for dici in jdata:
            #print dici
            for field in ['last_name_ki', 'first_name_ki', 'employer']:
                term = dici[field]
                dici[field] = term.encode('ascii', 'ignore')
                
            value = dici['employment_cancer_related']
            dici['employment_cancer_related'] = self.__convertInttoBoolstr(value)
            dici['date_uploaded'] = ''
            jdata_new.append(dici)
            
        return jdata_new
   

def __process(request, operation):
    alumni = DBtable_alumni("DEFAULT")
    dgtable = DataGrid(alumni)
    return dgtable.process(request, operation) 
   
def retrieve(request):
    ''' Callback saving records.
    '''
    return __process(request, "retrieve") 
   
def upload(request):
    ''' Callback saving records.
    '''
    return __process(request, "upload") 
   
def download(request):
    ''' Callback saving records.
    '''
    return __process(request, "download") 
    
def save(request):
    ''' Callback saving records.
    '''
    return __process(request, "save")
    
def delete(request):
    ''' Callback saving records.
    '''
    return __process(request, "delete")