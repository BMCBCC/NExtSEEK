import simplejson
from dbconnection import DBconnection
from datagrid_custom import DataGrid
from conversion import toInt, convertBoolstrToInt
from django.conf import settings
from django import forms

import json
import logging
logger = logging.getLogger(__name__)

DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/'

FORM_MAPPING = {
    'pk':'PK',
    'barcode':'Barcode',
    'status':'Status',
    'notes':'Notes'
}
FORM_DEFAULT = {
    #'pk':'',   
    'barcode':'',
    'status':'',
    'notes':''
}
class TableForm(forms.Form):
    pk = forms.CharField(required=True, label="ID", widget=forms.TextInput(attrs={'readonly': True}))
    barcode = forms.CharField(required=True, label="Barcode", widget=forms.TextInput(attrs={'size':200}), initial=FORM_DEFAULT['barcode'])
    status = forms.BooleanField(required=False, label="Status", initial=FORM_DEFAULT['status'])
    notes = forms.CharField(required=False, label='Notes', widget=forms.Textarea(attrs={'rows': 2, 'cols': 200}), initial=FORM_DEFAULT['notes'])

class DBtable(object):
    def __init__(self, whichDB, dbname=''):
        self.dbname = dbname
        self.tablemodel = ""
        if whichDB=="DJANGO":
            self.tablemodel = None
        else:
            self.tablemodel = None
        self.tablename = ""
        self.fulltablename = self.dbname + '.' + self.tablename
        self.viewtablename = self.fulltablename
        self.fields = []
        self.default = {}
        
        self.uniqueFields = []
        self.primaryField = ""
        self.fieldMapping = {}
        self.excludeFields = []
        self.db = DBconnection(whichDB, self.dbname)
        
        report = {}
        self.form = TableForm(report)
        self.formDefault = FORM_DEFAULT
        self.formMapping = FORM_MAPPING
        
        
    def reformatDataForClient(self, jdata):
        jdata_new = jdata
        return jdata_new
        
    def reformatRecordForDB(self, login_user, record):
        record_new = {}
        for key in self.fields:
            key_new = str(key)
            if key in record:
                value = record[key]
                record_new[key_new] = value
            
        return record_new
    
    def verifyRecordForDB(self, record):
        return 1, 'Successful'
        
    def __verifyUniqueConstraint(self, record):
        if self.primaryField in record:
            primarykey = record[self.primaryField]
            primarykey = toInt(primarykey)
            if primarykey>0:
                return primarykey
        
        constraint = {}
        ic = 0
        for field in self.uniqueFields:
            if field in record:
                value = record[field]
                if value is not None:
                    constraint[field] = record[field]
                    ic += 1
        if ic==0:
            primarykey = 0
            msg = "__verifyUniqueConstraint: primarykey not found: " + str(primarykey)
            logger.debug(msg)
            return primarykey
        
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        if len(diclist)==1:
            dici = diclist[0]
            primarykey = dici[self.primaryField]
        elif len(diclist)==0:
            primarykey = 0
        else:
            primarykey = -1
        
        return primarykey

    def storeOneRecord(self, username, record):
        status = 1
        try:
            record_new = self.reformatRecordForDB(username, record)
        except Exception, e:
            status = 0
            msg = str(e)
            logger.debug(msg)
            return msg, status, -1
       
        okay, msg = self.verifyRecordForDB(record_new)
        if not okay:
            status = 0
            return msg, status, -1
        
        primarykey = self.__verifyUniqueConstraint(record_new)
        if primarykey>0:
            msg = "Updating an existing record"
            logger.debug(msg)
            record_new[self.primaryField] = str(primarykey)
            msg, primarykey = self.db.storeOneRecord(self.fulltablename, record_new, self.primaryField, str(primarykey), self.excludeFields)
        elif primarykey==0:
            msg = "Inserting a new record"
            logger.debug(msg)
            record_new[self.primaryField] = 0
            msg, primarykey = self.db.storeOneRecord(self.fulltablename, record_new, self.primaryField, str(primarykey), self.excludeFields)        
        else:
            status = 0
            msg = "Warning: Not saved, another record already has the same " + ', '.join(self.uniqueFields) + ";"
            logger.debug(msg)
            
        return msg, status, primarykey
        
    def __saveRecords(self, username, records):
        data = {}
        status = 1
        data["status"] = status
        data["msg"] = "Saving record"
        data["link"] = ""
        
        n = 0
        msg = ""
        for record in records:
            msgi, statusi, primarykey = self.storeOneRecord(username, record)
            if statusi==0:
                status = 0
                msg += msgi
            else:
                n += 1
        
        data["status"] = status
        if status:
            data["msg"] = "Saving records successfully: " + str(n)
        else:
            data["msg"] = msg
        data["link"] = ""
        return data
        
    def verifyRecordForDelete(self, record):
        msg = 'Successful'
        return 1, msg
        
    def deleteOneRecord(self, record):
        status, msg = self.verifyRecordForDelete(record)
        primarykey = 0
        if self.primaryField in record:
            primarykey = record[self.primaryField]
        else:
            primarykey = self.__verifyUniqueConstraint(record)
            
        if primarykey>0 and status:
            logger.debug("The following record will be deleted: " + str(primarykey))    
            self.db.deleteOneRecord(self.fulltablename, self.primaryField, str(primarykey))
        else:
            logger.debug("No unique record is found for deletion")    
            
        return msg, status
        
    def __deleteRecords(self, username, records):
        data = {}
        data["status"] = 0
        data["msg"] = "Deleting record"
        data["link"] = ""
        status = 1
        n = 0
        msg = "Error in deleting: "
        for record in records:
            msgi, statusi = self.deleteOneRecord(record)
            if statusi==1:
                n += 1
            else:
                status = 0
                msg += msgi + ";"
        
        data["status"] = status
        data["msg"] = msg
        data["link"] = ""
        return data    

    def deleteRecordsConstraint(self, constraint):
        return self.db.deleteRecordsConstraint(self.fulltablename, constraint)
        
    def retrieveRecords(self, username, filtersdic):
        jdata, footer, total = self.db.retrieve_table_list(self.viewtablename, self.primaryField, filtersdic, self.fieldMapping)
        jdata_new = self.reformatDataForClient(jdata)
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data
    
    def download(self, username, allids, downloadallterms):
        msg = "Error: Download not successful."
        status = 0
        link = " "
        return msg, status, link      
        
    def processRecords(self, request, username, operation):
        ret = request.GET
        dg = DataGrid(None)
        if operation=="retrieve":
            filtersdic = dg.getDatagridFilters(ret)
            data = self.retrieveRecords(username, filtersdic)
        elif operation=="delete":
            data = dg.getDataGridData(request, username)
            if 'records' in data:
                records = data['records']
                data = self.__deleteRecords(username, records)
            
        elif operation=="save":
            data = dg.getDataGridData(request, username)
            if 'records' in data:
                records = data['records']
                data = self.__saveRecords(username, records)
            
        elif operation=="upload":
            msg, status, link = self.__upload(request)
            data = {'total':total,'rows':jdata,'footer':footer, 'msg':msg, 'status': status, 'link': link}
        elif operation=="download":
            msg = "Error: Download not successful."
            status = 0
            link = " "
            if 'allids' in ret:
                allids = json.loads(ret['allids'])
                downloadallterms = json.loads(ret['downloadallterms'])
                msg, status, link = self.download(username, allids, downloadallterms)
        
            data = {'msg':msg, 'status': status, 'link': link}
        
        reportData = simplejson.dumps(data)
        return reportData
 
    def getOneRecord(self, primarykeyvalue):
        return self.db.getOneRecord(self.fulltablename, self.primaryField, str(primarykeyvalue))
     
    def getLatestPrimarykey(self):
        return self.db.getLatestPrimarykey(self.fulltablename)
     
    def getComboboxOptions(self, primarykeySelected, textField):
        valueField = self.primaryField
        return self.db.getOptions(self.fulltablename, valueField, textField, primarykeySelected)
            
    def setForm(self, report):
        self.form = TableForm(report)
        return self.form

    def getFormDate(self, primarykeyvalue):
        pk = int(primarykeyvalue)
        recordDB = self.getOneRecord(primarykeyvalue)
        record = {}
        if pk==0 or not recordDB:
            for key, value in self.formDefault.iteritems():
                record[key] = value
            if pk==0:
                record["pk"] = self.getLatestPrimarykey()
            else:
                record["pk"] = primarykeyvalue
            record['form_msg'] = 'Fill new form'
        else:
            for formfield, dbfield in self.formMapping.iteritems():
                record[formfield] = recordDB[dbfield]
            record['form_msg'] = 'Revise form'
                
        return record

    def setForm(self, record):
        self.form = TableForm(record)
        return self.form

    def formInfo(self, request, pk):
        username = str(request.user)
        report = {}
        if request.method == 'POST':
            report = self.getFormDate(pk)
            postdata = request.POST
            for key, value in postdata.iteritems():
                report[key] = value
            form = self.setForm(request.POST)
            if form.is_valid():
                try:
                    operation = ""
                    if 'save' in request.POST:
                        operation = "SAVE"
                    elif 'delete' in request.POST:
                        operation = "DELETE"
                    
                    msg, status, form = self.__processForm(username, form, pk, operation)
                    if not status:
                        form.errors['__all__'] = form.error_class([msg])
                        report['form_msg'] = msg
                    else:
                        report['form_msg'] = msg
                    report['form_status'] = status
                    
                    report['operation'] = operation
                except Exception, e:
                    error = "Form field has exception: " + str(e)
                    form.errors['__all__'] = form.error_class([error])
                    report['form_status'] = 0
                    report['form_msg'] = error
                    report['operation'] = 'none'
            else:
                message = str(form.errors)
                report['form_status'] = 0
                report['form_msg'] = message
                report['operation'] = 'none'
        else:
            report = self.getFormDate(pk)
            form = self.setForm(report)
            report['form_status'] = 1
            report['form_msg'] = "Record retrieved."
            report['operation'] = 'get'

        return form, report
    
    def getRecordFromForm(self, login_user, form):
        status = 1
        record = {}
        for dbfield, value in self.formDefault.iteritems():
            record[dbfield] = value
        
        for formfield, dbfield in self.formMapping.iteritems():
            record[dbfield] = form.cleaned_data[formfield]
        
        record['LastUpdate_KRB_Name'] = login_user
        record['LastUPdate_Date'] = time.strftime("%Y-%m-%d")
        return status, record, form
    
    def __processForm(self, login_user, form, pk, operation):
        status, record, form = self.getRecordFromForm(login_user, form)
        if status==0:
            msg = "Error on the form"
            logger.debug(msg)
            return msg, status, form
        
        if operation=="SAVE":
            msg, status = self.storeOneRecord(login_user, record)
        elif operation=="DELETE":
            msg, status = self.deleteOneRecord(record)
        else:
            msg = "Error: unknown"
            status = 0
                
        return msg, status, form  
     
    def queryRecordsByConstraint(self, constraint):
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        return diclist
    
    def retrieveContainedRecords(self, constraint):
        diclist = self.db.retrieveContainedRecords(self.fulltablename, constraint)
        return diclist
        
    def queryPrimaryKeyByConstraint(self, constraint):
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        if len(diclist)==1:
            dici = diclist[0]
            primarykey = dici[self.primaryField]
        elif len(diclist)==0:
            primarykey = 0
        else:
            primarykey = -1
        return primarykey
    
    def queryRecordsCustom(self, qset):
        diclist = self.db.queryRecordsCustom(self.fulltablename, qset)
        return diclist
     
    def retrieveFieldValue(self, primarykey, field):
        value = self.db.retrieveFieldValue(self.tablemodel, primarykey, field)
        return value
     
    def retrieveRecordsByIDs(self, ids): 
        diclist = self.db.retrieveRecordsByIDs(self.tablemodel, ids)
        return diclist


