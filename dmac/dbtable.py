
#from django.http import HttpResponseRedirect, HttpResponse
import simplejson
#from alumni.datagrid import getDatagridFilters, getDataGridData
from dbconnection import DBconnection
from datagrid_custom import DataGrid
from conversion import toInt, convertBoolstrToInt


### used when necessary
from django.conf import settings
from django import forms

import json


# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + '/download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY

# The following is the mapping between fields on the form and those in the DB grant table
FORM_MAPPING = {
    'pk':'PK',
    'barcode':'Barcode',
    'status':'Status',
    'notes':'Notes'
}
FORM_DEFAULT = {
    #'pk':'',   # usually PK should be either 0 or a valid pk
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
    ''' The class stores all the information about the table [KI_Directory].[dbo].[KI_Directory]
    
    Typical usage of the class
    
        dbtable = DBtable()
        row = dbtable.retrieveRecord(mitid, krebid, firstname, lastname)
        dbtable.close()

    '''
    def __init__(self, whichDB, dbname=''):
        self.dbname = dbname
        self.tablemodel = ""
        if whichDB=="DJANGO":
            self.tablemodel = None
        else:
            self.tablemodel = None
        self.tablename = ""
        self.fulltablename = self.dbname + '.' + self.tablename
        # this is the table for retrieving the list and shown in a dataGrid
        self.viewtablename = self.fulltablename
        # fields defined in the table
        self.fields = []
        # default values for all fields in a table record.
        self.default = {}
        
        # the unique constraint to find the primary key
        self.uniqueFields = []
        # The primary key name
        self.primaryField = ""
        # the mapping between field names in DB and headers for DataGrid table.
        self.fieldMapping = {}
        # a list of fields that should be excluded from updating a record in a DB table.
        self.excludeFields = []
        # the DB operator
        self.db = DBconnection(whichDB, self.dbname)
        
        # create a virtual form that is to be overrided.
        report = {}
        self.form = TableForm(report)
        self.formDefault = FORM_DEFAULT
        self.formMapping = FORM_MAPPING
        
        
    def reformatDataForClient(self, jdata):
        ''' Reformat the list of records for shown on dataGrid Table.
        Input
            jdata=[record1, record2,...], a list of records
            
        Output
            jdata_new, a revised list of records.
            
        Notes
            This is a virtual method provided for overridinng in the child class, for example,

        jdata_new = []
        for data in jdata:
            datadic = data
            datadic['sponsorUrl'] = self.__getSponsorLinkUrl(data['SPONSOR_NAME'], data['SponsorPK'])
            jdata_new.append(datadic)
        '''
        jdata_new = jdata
        return jdata_new
        
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
                
            #elif key=="LastUpdate_KRB_Name":
            #    value = login_user
            #elif key=="LastUPdate_Date":
            #    value = time.strftime("%Y-%m-%d")
            #print(key, value)
            
                record_new[key_new] = value
            
        return record_new
    
    def verifyRecordForDB(self, record):
        ''' Given the record from either one row in an excel file or from client-side table,
            verify whether it can be stored into the database table.
        Input
            record, the dictionary in its original format.
        Output
            okay, 1 or 0
            msg, any message
            
        Notes
            This is a virtual method provided for overridinng in the child class.
        '''
        return 1, 'okay'
        
    def __verifyUniqueConstraint(self, record):
        ''' Retrieve an unique record from DB, based on the unique constraint defined in
            self.uniqueFields.
        Input
            record = {field1:value1,...}, a dictionary with some keys and values;
        Output
            primarykey >0, unqiue constraint exists;
                       =0, does not exist in DB table;
                       <0, any error, such as more than one record etc.
        '''
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
            # no constrint set up
            primarykey = 0
            msg = "__verifyUniqueConstraint: primarykey not found: " + str(primarykey)
            print(msg)
            return primarykey
        
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        #print(diclist)
        if len(diclist)==1:
            dici = diclist[0]
            # unique constraint found for a new record, nor insert, neither update, refer to search for tht record to modify
            primarykey = dici[self.primaryField]
        elif len(diclist)==0:
            # unique constraint not found, a new record
            primarykey = 0
        else:
            # more than one unique constraint found, nor insert, neither update, refer to search for tht record to modify
            primarykey = -1
        
        msg = "__verifyUniqueConstraint: primarykey found: " + str(primarykey)
        print(msg)
        return primarykey

    def storeOneRecord(self, username, record):
        ''' Store a record into a table. Based on the unique identifier, if such record already exists, update the record,
            If it is a new record, insert it.
        Input
            username, the login user who submitted the request.
            record, 
                record["id"], the primary key for the record, =0 for insert, >0 for update
                record["fieldi": valuei] for i=1, ..., N, the pair of field name and its value.
                
            Notes: no unique constrain is checked in this subroutine.
        Output
            
        '''
        status = 1
        try:
            record_new = self.reformatRecordForDB(username, record)
        except Exception, e:
            status = 0
            msg = str(e)
            print(msg)
            return msg, status, -1
       
        okay, msg = self.verifyRecordForDB(record_new)
        if not okay:
            status = 0
            return msg, status, -1
        
        primarykey = self.__verifyUniqueConstraint(record_new)
        if primarykey>0:
            msg = "Updating an existing record"
            print(msg)
            record_new[self.primaryField] = str(primarykey)
            msg, primarykey = self.db.storeOneRecord(self.fulltablename, record_new, self.primaryField, str(primarykey), self.excludeFields)
        elif primarykey==0:
            msg = "Inserting a new record"
            print(msg)
            # only insert new record
            #primarykey = self.db.getLatestPrimarykey(self.fulltablename)
            #print('primarykey:', primarykey)
            #record_new[self.primaryField] = str(primarykey)
            record_new[self.primaryField] = 0
            print(record_new)
            msg, primarykey = self.db.storeOneRecord(self.fulltablename, record_new, self.primaryField, str(primarykey), self.excludeFields)        
        else:
            #primarykey<0
            status = 0
            msg = "Warning: Not saved, another record already has same " + ', '.join(self.uniqueFields) + ";"
            print(msg)
            
        return msg, status, primarykey
        
    def __saveRecords(self, username, records):
        ''' Save records when saveSelectedIntoDB() is called in the jscript on a dataGrid table.
        Arguments:
            records, a list of dictionaries.
            username, the login user in the current session or None if not loged in.
        Returns:
            data = {'status':'', 'message':'', 'link':''}
            
        Usage:
    
            username = str(request.user)
            if verifyUser(request)==0:
                username = None
    
            data = getDataGridData(request, username)
            records = data['records']
            sponsor = DBtable_sponsor("DEFAULT")
            data = sponsor.saveRecords(username, records)
        '''
        print "saveRecords"
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
        ''' Verify whether a record is ready for deleting from a DB table.
        Input
            record
            
        Output
            1 or 0
            
        Notes
            This is a virtual method provided for overridinng in the child class, for example,

        jsponsor_code = record['SPONSOR_CODE']
        if sponsor_code[0]=="T":
            msg += sponsorname + ": deleted;"
            return 1
        else:
            msg += sponsorname + ": not allowed;"
            return 0
        '''
        msg = 'okay'
        return 1, msg
        
    def deleteOneRecord(self, record):
        ''' Delete a record, given
        Input
            primaryvalue, the value for the unique constraint field, such as the primary id.
        '''
        status, msg = self.verifyRecordForDelete(record)
        primarykey = 0
        if self.primaryField in record:
            primarykey = record[self.primaryField]
        else:
            primarykey = self.__verifyUniqueConstraint(record)
            
        if primarykey>0 and status:
            print("The following record will be deleted: " + str(primarykey))    
            self.db.deleteOneRecord(self.fulltablename, self.primaryField, str(primarykey))
        else:
            print("No unique record is found for deletion")    
            
        return msg, status
        
    def __deleteRecords(self, username, records):
        ''' Delete records when deleteSelectedFromDB() is called in the jscript on a dataGrid table.
        Arguments:
            records, a list of dictionaries.
            username, the login user in the current session or None if not loged in.
        Returns:
            data = {'status':'', 'message':'', 'link':''}
            
        Usage:
    
        '''
        print("deleteRecords")
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
             #else:
            #    we don't want to update record
        
        data["status"] = status
        data["msg"] = msg
        data["link"] = ""
        return data    

    def deleteRecordsConstraint(self, constraint):
        ''' Delete all records, given
        Input
            tablename, the full name of the table, such as [dbname].[dbo].[tablename]
            constraint, {"field1":value1,"field2":valuue2,...}, where the combination of all fields forms the unqiue constraint.
            
        Output
            msg,
            status
            
        Notes:
            constraint can not be empty for deleting all records in a table.
        '''
        return self.db.deleteRecordsConstraint(self.fulltablename, constraint)
        
    def retrieveRecords(self, username, filtersdic):
        ''' Virtual function fo overload.
        Retrieve a list of records and show is in a dataGrid on the front page.
        
        '''
        jdata, footer, total = self.db.retrieve_table_list(self.viewtablename, self.primaryField, filtersdic, self.fieldMapping)
        jdata_new = self.reformatDataForClient(jdata)
        data = {'total':total,'rows':jdata_new,'footer':footer}
        return data
    
    def download(self, username, allids, downloadallterms):
        ''' Function for overload.
        '''
        msg = "Error: Download not successful."
        status = 0
        link = " "
        return msg, status, link

    def download(self, username, allids, downloadallterms):
        ''' Function for overload.
        '''
        msg = "Error: Download not successful."
        status = 0
        link = " "
        return msg, status, link        
        
    def processRecords(self, request, username, operation):
        ''' Process http request from client-side for various operations.
        Input
            request, a http request;
            username, login user or None if not login.
            operation, the name of operation through the request, such as,
                save, save record(s) into the database table, defined in dbtable;
                delete, remove record(s) from the database table, defined in dbtable;
                download, batch download of record(s) in an excel or pdf file from the database table, defined in dbtable;
                upload, batch upload of record(s) in an excel file into the database table, defined in dbtable;
                retrieve, retrieve a list of records from the database table, defined in dbtable, according to the filtering and sorting parameters.
        
        '''
        '''
        ret = request.GET
        #filtersdic = getDatagridFilters(ret)
        dg = DataGrid(None)
        data = dg.getDataGridData(request, username)
        
        
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
        '''
        
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
            # batch upload of record(s) in an excel file into the database table, defined in dbtable;
            # alumniUploadAjax(request)
            msg, status, link = self.__upload(request)
            data = {'total':total,'rows':jdata,'footer':footer, 'msg':msg, 'status': status, 'link': link}
        elif operation=="download":
            # batch download of record(s) in an excel or pdf file from the database table, defined in dbtable;
            msg = "Error: Download not successful."
            status = 0
            link = " "
            if 'allids' in ret:
                allids = json.loads(ret['allids'])
                downloadallterms = json.loads(ret['downloadallterms'])
                msg, status, link = self.download(username, allids, downloadallterms)
        
            #data = {'total':total,'rows':jdata,'footer':footer, 'msg':msg, 'status': status, 'link': link}
            data = {'msg':msg, 'status': status, 'link': link}
        
        #print data
        reportData = simplejson.dumps(data)
        #return HttpResponse(reportData)    
        return reportData
 
    def getOneRecord(self, primarykeyvalue):
        ''' get a record, given
        Input
            fulltablename, the full table name in MSSQL DB, such as [hr].[dbo].[Grant]
            primarykey, the unique constraint field, such as the primary key.
            primaryid, the value for the unique constraint field, such as the primary id.
        '''
        return self.db.getOneRecord(self.fulltablename, self.primaryField, str(primarykeyvalue))
     
    def getLatestPrimarykey(self):
        ''' Be careful in using the id from this call, because the next id available may not
        necessary to be the actual id for a new record inserted into the table. This issue is
        related to
            http://visualseq.org/dokuwiki/doku.php?id=computer:database:mysql:mysql-faqs#why_does_auto_increment_primary_leave_gaps_in_counting
            
        '''
        return self.db.getLatestPrimarykey(self.fulltablename)
     
    def getComboboxOptions(self, primarykeySelected, textField):
        ''' Get the options used in a comboBox from a DB table directly.
        Input
            tablemodel,a Django model
            valueField, a field used as the id of an option in combobox, such as 'id', which usually the primary key of a record;
            textField, a field used as the text of an option in combobox, such as 'name' of the record;
            primarykeySelected, such as 3, the value of the valueField, such that 'id'=3, is the current value selected in combobox;
        
        Output
            options, = [op1, op2,...], where opi = {valueField:vi, textField:txti, 'selected':True}
        '''
        print(primarykeySelected)
        valueField = self.primaryField
        return self.db.getOptions(self.fulltablename, valueField, textField, primarykeySelected)
            
    def setForm(self, report):
        ''' Initialize a form class, which is a virtual function for overriding.
        Input
            report: ={} a dictionary
        
        '''
        self.form = TableForm(report)
        return self.form

    def getFormDate(self, primarykeyvalue):
        ''' Retrieve record info from DB.
        Input
            primaryvalue, the primary key of a table, or 0, if it is a new record.
        
        Output
            record={}, the dictionary with returned values of a record.
        '''
        pk = int(primarykeyvalue)
        recordDB = self.getOneRecord(primarykeyvalue)
        record = {}
        if pk==0 or not recordDB:
            # add a new record
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
        ''' Initialize a form class, which overrides a virtual function in parent Dbtable class.
        Input
            record: ={} a dictionary
        
        '''
        self.form = TableForm(record)
        return self.form

    def formInfo(self, request, pk):
        ''' This is the main function to process a form, provided for overriding.
        Input
            request, http request
            pk, the primary key of the table
        Output
            form, the form class
            report={}, extra report
            
        '''
        username = str(request.user)
        report = {}
        if request.method == 'POST':
            report = self.getFormDate(pk)
            # use the form data to overwrite the DB data
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
                    # URl for redirction after deletion
                    #if operation == "DELETE" and status:
                    #    return funding(request)
                    
                except Exception, e:
                    error = "Form field has exception: " + str(e)
                    form.errors['__all__'] = form.error_class([error])
                    
                    report['form_status'] = 0
                    report['form_msg'] = error
                    report['operation'] = 'none'
            else:
                print "form is not valid", form.errors
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
            #report['formstatus'] = False

        return form, report
    
    def getRecordFromForm(self, login_user, form):
        ''' Create a record from the form, which is used for storing into DB table.
        Input
            form, the data from the Component Form
            login_user, the login user who submitted the request.
        Output
            status, whether or not the form has any error.
            form, the same form class but with more error or form message that will be returned to the Form GUI.
            record, the record rady for storing into DB table.
            
        Notes;
            This fuction could also be part of the parent DBTable class for inheritance and overriding. 
        '''
        status = 1
        record = {}
        for dbfield, value in self.formDefault.iteritems():
            record[dbfield] = value
        
        for formfield, dbfield in self.formMapping.iteritems():
            #print field, key
            record[dbfield] = form.cleaned_data[formfield]
        
        record['LastUpdate_KRB_Name'] = login_user
        record['LastUPdate_Date'] = time.strftime("%Y-%m-%d")
        return status, record, form
    
    def __processForm(self, login_user, form, pk, operation):
        ''' Save/update/delete a record in the database, given
        Input
            form, the data from the Component Form
            pk, the grant component PK
            operation="SAVE" or "DELETE"
        Output
            form, the same form class but with more error or form message that will be returned to the Form GUI.
            msg, any message
            status, False or True for the operation.
        '''
        status, record, form = self.getRecordFromForm(login_user, form)
        if status==0:
            msg = "Error on the form"
            print(msg)
            return msg, status, form
        
        if operation=="SAVE":
            print('save a record')
            msg, status = self.storeOneRecord(login_user, record)
        elif operation=="DELETE":
            print('delete a record')
            msg, status = self.deleteOneRecord(record)
        else:
            # should never reach here
            msg = "Error: unknown"
            status = 0
                
        return msg, status, form  
     
    def queryRecordsByConstraint(self, constraint):
        ''' Run SQL query to get a list of records from DB, given
        Input
            constraint = {field1:value1,...}, a dictionary with some keys and values;
        Output
            diclist, a list of dictionaries/records from DB.
            
        Notes:
            the difference between queryRecordsByConstraint() and retrieveContainedRecords() is:
                queryRecordsByConstraint() prefers exact match for field names, such as nameField='Jerry';
                retrieveContainedRecords() allows contained match for a string field that contains the query string, such as
                    nameField contains "Jerry" etc;
        '''
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        #print(diclist)
        return diclist
        '''
        if len(diclist)==1:
            dici = diclist[0]
            # unique constraint found for a new record, nor insert, neither update, refer to search for tht record to modify
            primarykey = dici[self.primaryField]
        elif len(diclist)==0:
            # unique constraint not found, a new record
            primarykey = 0
        else:
            # more than one unique constraint found, nor insert, neither update, refer to search for tht record to modify
            primarykey = -1
        '''

    #def getRecords(self, constraint):
    #    ''' Run SQL query to get a list of records from DB, given
    #    Input
    #        constraint = {field1:value1,...}, a dictionary with some keys and values;
    #    Output
    #        diclist, a list of dictionaries/records from DB.
    #    Notes:
    #        self.getRecords() is the same as self.queryRecordsByConstraint()
    #    '''
    #    diclist = self.db.getRecords(self.fulltablename, constraint)
    #    return diclist
    
    def retrieveContainedRecords(self, constraint):
        ''' Run SQL query to get a list of records from DB, given
        Input
            constraint = {field1:value1,...}, a dictionary with some keys and values;
        Output
            diclist, a list of dictionaries/records from DB.
            
        Notes:
            the difference between queryRecordsByConstraint() and retrieveContainedRecords() is:
                queryRecordsByConstraint() prefers exact match for field names, such as nameField='Jerry';
                retrieveContainedRecords() allows contained match for a string field that contains the query string, such as
                    nameField contains "Jerry" etc;
        '''
        diclist = self.db.retrieveContainedRecords(self.fulltablename, constraint)
        #print(diclist)
        return diclist
        
    def queryPrimaryKeyByConstraint(self, constraint):
        ''' Run SQL query to get a list of records from DB, given
        Input
            constraint = {field1:value1,...}, a dictionary with some keys and values;
        Output
            diclist, a list of dictionaries/records from DB.
        '''
        diclist = self.db.retrieveConstraintRecords(self.fulltablename, constraint)
        #print(diclist)
        #return diclist
        if len(diclist)==1:
            dici = diclist[0]
            # unique constraint found for a new record, nor insert, neither update, refer to search for tht record to modify
            primarykey = dici[self.primaryField]
        elif len(diclist)==0:
            # unique constraint not found, a new record
            primarykey = 0
        else:
            # more than one unique constraint found, nor insert, neither update, refer to search for tht record to modify
            primarykey = -1
        return primarykey
    
    def queryRecordsCustom(self, qset):
        ''' Run SQL query to get a list of records from DB, given
        Input
            qset, a customized query set in Django, such as,
                query = {}
                query['sample_type_id__exact'] = sample_type_id
                qset = Q(**query)
        
                query = {}
                #Case-insensitive containment of scietist name in json_metadata
                query['json_metadata__icontains'] = scientist
                qset = qset & Q(**query)
        
                query = {}
                # case insensitive match of sample name
                query['title__iexact'] = title
                qset = qset & Q(**query)
            
        Output
            diclist, a list of dictionaries/records from DB.
            
        Notes:
            the difference between queryRecordsByConstraint() and retrieveContainedRecords() is:
                queryRecordsByConstraint() prefers exact match for field names, such as nameField='Jerry';
                retrieveContainedRecords() allows contained match for a string field that contains the query string, such as
                    nameField contains "Jerry" etc;
        '''
        diclist = self.db.queryRecordsCustom(self.fulltablename, qset)
        #print(diclist)
        return diclist
     
    def retrieveFieldValue(self, primarykey, field):
        ''' Retrieve the value for a field, given the primary key in a table.
        Notes
            This subroutine will not work if the field name is a foreign key, such as "wga_tube" in Cell table.
            If the field is a foreign key, such as "wga_tube", whether using "wga_tube_id" or "wga_tube" will 
            return the model object for the foreign key, i.e., the Wga_tube object in this case. 
        Input
            table, the table name
            id, the primary key
            fieldname, the name of the field that will be retrieved.
                
        Output
            The value for that field, given the primary key.
        '''
        value = self.db.retrieveFieldValue(self.tablemodel, primarykey, field)
        #print(value)
        return value
     
     
#################### the following is to be deleted #########################        
        

    def __sqlQuery_select_Excel_byIDs(self, orderby, allids, downloadallterms=False):
        ''' Retrieve all records.
                Input
            
            Output
                A SQL query used for retrieving records
        
        SELECT * 
            FROM djangocms.alumni A
            order by A.last_name_ki;
        '''
        sqlquery =  " SELECT * "
        sqlquery +=  "FROM alumni A "
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
        sqlquery = self.__sqlQuery_select_Excel_byIDs(orderby, allids, downloadallterms)
        
        self.db.retrieveAllRecordsIntoExcel(sqlquery, HEADERS, ALUMNUS_MAPPING, excelfile)
        
    
