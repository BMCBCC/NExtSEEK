#!/bin/python
'''
Created on Aug, 2015

@author: Huiming Ding
Email: huiming@mit.edu

Description:

DB connection to different databases.

Input:  
    
Output:
        
Example command line:
    
     
Log of changes:
     
'''

import os, sys
import MySQLdb

import datetime

from os.path import abspath, exists
#from dbdjango import retrieve_custom_sql
from iocsv import saveCsvfile
from conversion import toString, cleanString


class DBconnection(object):
    ''' The class for connecting to the default database
    
    Typical usage of the class
    
        dbconn = DBconnection("DJANGO")
        dbconn.conn
        dbconn.cursor

    '''
    def __init__(self, whichDB, dbname=''):
        ''' 
            whichDB, the protocol of db connection,
                = "DJANGO"
                = "MYSQL"
                = "DEFAULT"
                = "MSSQL"
                = "SEEK"        # use django as default first
        '''
        #print "DBconnection: __init__"
        self.__dbconn = None
        self.dbtype = whichDB
        if whichDB=="DJANGO":
            #print "DBconnection: DBconn_django"
            from dbconn_django import DBconn_django
            self.__dbconn = DBconn_django()
        elif whichDB=="SEEK":
            #print "DBconnection: DBconn_django"
            from dbconn_django import DBconn_django
            self.__dbconn = DBconn_django()
        elif whichDB=="MYSQL":
            from dbconn_mysql import DBconn_mysql
            self.__dbconn = DBconn_mysql()
        else:
            # default Django
            from dbconn_django import DBconn_django
            #print "DBconnection: default DBconn_django 2"
            self.__dbconn = DBconn_django()
        
    def getPrimarykey(self, table, field, keyword):
        ''' Retrieve the primary key, given
        Input
            table, the table model, such as Wga_patient.
            field, the table column to match, such as 'name' field
            keyword, the value for the field, such as 'jack'
        
        Output
            Return the primary key if the keyword is uniquely found in the table.
            Otherwise, return -1.
    
        Usage
            id=getPrimarykey(Wga_patient, 'name', 'Jack')
        '''
        #keyword = keyword.strip()
        if self.__dbconn is not None:
            return self.__dbconn.getPrimarykey(table, field, keyword)
        else:
            return -1
    
    def getLatestID(self, tablemodel):
        return self.__dbconn.getLatestID(tablemodel)
        
    def retrieveFieldValue(self, tablemodel, primarykey, field):
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
        if self.__dbconn is not None:
            return self.__dbconn.retrieveFieldValue(tablemodel, primarykey, field)
        else:
            return None
        
    def retrieveForeignKeyId(self, tablemodel, primarykey, field):
        ''' Retrieve a foreign key, given the primary key in a table, and the name of the foreign key.
            This is a complementary to retrieveFieldValue() above, where the field can't be a foreign key name. 
        
        Input
            table, the table name, such as "Wga_cell"
            id, the primary key in the table
            fieldname, the foreign name of the field that will be retrieved, such as "wga_tube", which is a foreign in "Wga_cell" table
                
        Output
            The foreign key for that field, given the primary key.
        
        Usage
            tube_id = db_cell.db.retrieveForeignKeyId(db_cell.tablemodel, cell_id, "wga_tube")
        '''
        record = self.retrieveOneRecord(tablemodel, primarykey)
        id = 0
        if record is not None:
            #print "cell_record: ", cell_record
            if field in record:
                foreign_record = record[field]
                #print "tube_record: ", tube_record
                #print "tube_record id: ", tube_record.id
                id = foreign_record.id
        
        return id    
        
        
    def storeOneRecord(self, tablemodel, record, primarykey=None, primaryvalue=None, excludeKeys=[]):
        ''' Store a record into a table. Based on the unique identifier, if such record already exists, update the record,
            If it is a new record, insert it.
        Input
            tablemodel, the table model defined in models.py for "DJANGO" DB connection, or
                        the table name in MySQL DB for "MYSQL"  DB connection
            record, 
                record["id"], the primary key for the record, =0 for insert, >0 for update
                record["fieldi": valuei] for i=1, ..., N, the pair of field name and its value.
                
            Notes: no unique constrain is checked in this subroutine.
        Output
            
        '''
 
        id, msg = self.__dbconn.storeOneRecord(tablemodel, record)
        if id>0:
            primarykey = id
        else:
            primarykey = 0
            
        return msg, primarykey
        
    def retrieveOneRecord(self, tablemodel, id):
        return self.__dbconn.retrieveOneRecord(tablemodel, id)
        
    def __mergeStringsAdditive(self, string1, string2):
        ''' Given two strings, merge them in a proper way.
            Input
                string1, the first string
                string2, the second string
            Output
                newString = string1 + ";" + string2
        '''
        newstring = string1
        if string1 is None:
            #string1 is None
            newstring = string2
        elif len(string1)==0:
            # string1 is empty
            newstring = string2
        else:
            # string1 is not null
            if string2 is None:
                # input string is None
                newstring = string1
            elif len(string2)==0:
                # input string is empty
                newstring = string1
            else:
                # both string1 and string2 are not none
                if string2 in string1:
                    newstring = string1
                elif string1 in string2:
                    newstring = string2
                else:
                    newstring = string1 + ";" + stringIn
        
        return newstring
        
        
    def getStringValueAdditive(self, tablemodel, primarykey, field, stringIn):
        ''' Given
                tablemodel, the table model such as WGA_cell or data_wga_cell,
                primarykey, the primary key iin this table,
                field, the name for a field such as "notes"
                stringIn, this stringIn will be added to the existing string in such as way;
        
            Output
                newString = oldString + ";" + stringIn
                
            Usage
                Called in dbtable_2dtube
                
            Notes
                Old name is addStringValue
        '''
        if primarykey>0: # update it
            #print 'Already exist, update it'
            oldstring = self.retrieveFieldValue(tablemodel, primarykey, field)
            newstring = self.__mergeStringsAdditive(oldstring, stringIn)
        else:
            newstring = stringIn
        return newstring
            
    def __updateRecordViaKeyword(self, tablemodel, uniqueField, uniqueKeyword, record):
        '''
            Input
                tablemodel, which table
                uniqueField, unique filed name that can be used as unique identifier, such as tubecode;
                uniqueKeyword, the value for the uniqueField
                record, 
              
            Output
                the primary key of the record, or
                -1 if not a valid record.
            
            Usage
            Called by DBAdmin in update operation.
        '''
        id = self.getPrimarykey(tablemodel, uniqueField, uniqueKeyword)
        if id<=0:
            msg = "Warning: The primary key for the table is not valid."
            logger.debug(msg)
            return -1, msg
            
        # get the record in DB based on its id
        record_update = self.__dbconn.retrieveOneRecord(tablemodel, id)
        
        # update the record in DB
        for key, value in record.iteritems():
            if key == "id":
                if value!=id:
                    # not the same record, impossible
                    msg = "Error: The primary key not consistent."
                    logger.debug(msg)
                    return -1, msg
        
            if key in record_update:
                # update the old value in new value
                record_update[key] = value      
        
        # submit the change to DB        
        return self.storeOneRecord(tablemodel, record_update)

    def updateNotesViaKeyword(self, tablemodel, uniqueField, uniqueKeyword, notes):
        '''
            Input
                tablemodel, which table
                uniqueField, unique filed name that can be used as unique identifier, such as tubecode;
                uniqueKeyword, the value for the uniqueField
                record, 
              
            Output
                id, msg, where
                    id, the primary key of the record, or -1 if not a valid record.
                    msg, any message
            
            Usage
            Called by DBAdmin in update operation.
        '''
        id = self.getPrimarykey(tablemodel, uniqueField, uniqueKeyword)
        if id<=0:
            msg = "Warning: The primary key for the table is not valid."
            logger.debug(msg)
            return -1, msg
        
        if notes.strip()=="remove":
            # This is a particular operation for batch clearing notes, called in DB Admin.
            self.__dbconn.updateFieldValue(tablemodel, id, "notes", "")
        else:
            self.__dbconn.updateStringsAdditive(tablemodel, uniqueField, uniqueKeyword, "notes", notes)
        msg = "okay"
        return id, msg
       
    
    def run_custom_sql(self, sqlquery):
        #print sqlquery
        if self.__dbconn is not None:
            return self.__dbconn.retrieve_custom_sql(sqlquery)
        
        return None
    
    def saveRecordsIntoCSV(self, sqlquery, columns, outcsvfile):
        ''' Given the following input,
                sqlquery, a SQL "select" query;
                columns, alist of headers, such as columns=["header1", "header2", ...,"headerN"], where hearder i is in the SQL query.
        
        retrieve the list of records and save it into a csv file.
        '''
        print sqlquery
        rows = self.run_custom_sql(sqlquery)
        saveCsvfile(outcsvfile, columns, rows)
        
    def retrieveRecords(self, tablemodel, field, keyword):
        if self.__dbconn is not None:
            return self.__dbconn.retrieveRecords(tablemodel, field, keyword)
            
        return None
    
    def retrieveNumberOfRecords(self, tablename, constraint={}):
        ''' Modified from retrieveTotalRecords(tablename) in dbjango.py.
            Returns the total number of records in a table.
            Input
                tablename, the actual database table name (not the table model in Django).
                constraint = {field1:value1, ...}, default: {}, no constraint.
            Output
                The total number of records in the table.
        '''            
        if self.__dbconn is not None:
            if not constraint:
                return self.__dbconn.retrieveNumberOfRecords(tablename)
            else:
                # error: to be implemented
                return -1
        return -1
    
    def retrieveTotalRecords(self, tablemodel, qset=None):
        ''' Returns the total number of records in a table.
            Input
                tablemodel, the Django table model name such as Wga_cell etc.
            
            Output
                The total number of records in the table.
                
                
            total = tablemodel.objects.all().count()
        '''
        if self.__dbconn is not None:
            return self.__dbconn.retrieveTotalRecords(tablemodel, qset)
            
        return -1
    
    def retrieveJoint(self, tablemodel, joint_tablemodels_string, qset, orderby, limit):
        ''' Example
            # Step 1. Retrieve records in Wga_cell tabel together with Wga_cell_status and Wga_cell_ulp
            orderby, limit = querySuffix(request.GET)
            qset = Q()
            rdata = self.db.retrieveJoint(Wga_cell, 'cell_status', qset, orderby, limit)
        
            Output
                [dic1, dic2,..., dicN]
        '''
        if self.__dbconn is not None:
            return self.__dbconn.retrieveJoint(tablemodel, joint_tablemodels_string, qset, orderby, limit)
            
        return []
    

    def deleteRocords(self, tablemodel, primarykeys):
        ''' Given
                tablemodel, the table model such as WGA_cell or data_wga_cell,
                primarykeys, a list of primary keys in this table.
        
            Output
                number of records deleted from data table, or 0 if not any.
                
        '''
        if self.__dbconn is not None:
            return self.__dbconn.deleteRocords(tablemodel, primarykeys)
            
        return 0
        
    def printTest(self):
        print (self.dbtype, self.__dbconn.msg)
        
    def retrieve_table_list(self, tablename, primarykey, filtersdic, fieldMapping):
        ''' Retrieve a list of sponsors based on the filters from the dataGrid on the frant GUI.
        Input
            tablename,
            primarykey, such as 'SponsorP'
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
            jdata, the list of records in the format of a list of dictionaries.
            footer, =[{"ProjectTC": "Total","AnnualProjectDC": totalADC}], the summary of records used as the footer in a frant DataGrid table.
            total, the total number of records after removing the limit clause from the SQL query.
        
        '''
        if self.dbtype=="DJANGO" or self.dbtype=="SEEK":
            return self.__dbconn.retrieve_table_list(tablename, primarykey, filtersdic, fieldMapping)
        else:
            jdata = []
            footer = []
            total = 0
            return jdata, footer, total
        
    def getLatestPrimarykey(self, tablename):
        return self.__dbconn.getLatestID(tablename)
            
    def retrieveConstraintRecords(self, tablename, constraint):
        ''' Retrieve all records, given
        Input
            tablename, the full name of the table, such as [dbname].[dbo].[tablename]
            constraint, {"field1":value1,"field2":valuue2,...}, where the combination of all fields forms the unqiue constraint.
            
        Output
            diclist = [dic1, dic2,...], a list of dictionaries. If the unique constraint is true, only one record should be returned if it exists in DB,
                or [] if it does not exist in DB.
        
        Notes:
            the difference between retrieveConstraintRecords() and retrieveContainedRecords() is:
                retrieveConstraintRecords() prefers exact match for field names, such as nameField='Jerry';
                retrieveContainedRecords() allows contained match for a string field that contains the query string, such as
                    nameField contains "Jerry" etc;
        '''
        if self.dbtype=="DJANGO" or self.dbtype=="SEEK":
            return self.__dbconn.retrieveConstraintRecords(tablename, constraint)
        else:
            # to be implemented
            return []
            
    def retrieveContainedRecords(self, tablename, constraint):
        ''' Retrieve all records, given
        Input
            tablename, the full name of the table, such as [dbname].[dbo].[tablename]
            constraint, {"field1":value1,"field2":valuue2,...}, where the combination of all fields forms the unqiue constraint.
            
        Output
            diclist = [dic1, dic2,...], a list of dictionaries. If the unique constraint is true, only one record should be returned if it exists in DB,
                or [] if it does not exist in DB.
        
        Notes:
            the difference between retrieveConstraintRecords() and retrieveContainedRecords() is:
                retrieveConstraintRecords() prefers exact match for field names, such as nameField='Jerry';
                retrieveContainedRecords() allows contained match for a string field that contains the query string, such as
                    nameField contains "Jerry" etc;
        '''
        if self.dbtype=="DJANGO" or self.dbtype=="SEEK":
            return self.__dbconn.retrieveContainedRecords(tablename, constraint)
        else:
            # to be implemented
            return []    
            
    def deleteRecordsConstraint(self, tablename, constraint):
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
        # to be implemented
        return []
            
    def deleteOneRecord(self, fulltablename, primarykey, primaryvalue):
        ''' Delete a record, given
        Input
            fulltablename, the full table name in MSSQL DB, such as [hr].[dbo].[Grant]
            primarykey, the unique constraint field, such as the primary key.
            primaryid, the value for the unique constraint field, such as the primary id.
        '''
        if self.dbtype=="DJANGO" or self.dbtype=="SEEK":
            self.__dbconn.deleteOneRecord(fulltablename, primaryvalue)
            # to be implemented
            status = 1
            msg = "Okay"
            return msg, status
        else:
            # to be implemented
            status = 0
            msg = "To be implemented"
            return msg, status
     
    def getOneRecord(self, fulltablename, primarykey, primaryvalue):
        ''' get a record, given
        Input
            fulltablename, the full table name in MSSQL DB, such as [hr].[dbo].[Grant]
            primarykey, the unique constraint field, such as the primary key.
            primaryid, the value for the unique constraint field, such as the primary id.
        '''
        if self.dbtype=="DJANGO" or self.dbtype=="SEEK":
            return self.__dbconn.retrieveOneRecord(fulltablename, primaryvalue)
        else:
            # to be implemented
            status = 0
            msg = "To be impplemented."
            recordarray = self.__dbconn.retrieveOneRecord(fulltablename, primaryvalue)
            # need to convert from array to dic
            record = {}
            return record
        
    def queryToListDics(self, sqlquery, headers=None, db_alias=None):
        ''' Refer to: https://stackoverflow.com/questions/16519385/output-pyodbc-cursor-results-as-python-dictionary 
        Input
            sqlquery, a customized query
        
        Output
            diclist or [], a list of dictionaries.
        '''
        return self.__dbconn.retrieve_custom_sql(sqlquery, headers, db_alias)
            
    def commitSQLQuery(self, sqlquery):
        ''' Run a customized sqlquery without returning value.
        Input
            sqlquery, a customized sqlquery, such as delete or update.
            
        Output
            msg, any message
            status, 0 or 1
        '''
        # to be implemented
        return 'to be implemented', 0
        
    def compareOneRecord(self, obj, record):
        return self.__dbconn.compareOneRecord(obj, record)
        
    def retrieveValuesDictionary(self, tablemodel, filter):
        return self.__dbconn.retrieveValuesDictionary(tablemodel, filter)
        
        
    def saveOneRecord(self, datadic, tablemodel, unqiuefield, expectedfields):
        ''' Either insert or upload a record into Category table, given
        Input
            datadic = {"field1":value1, "field2":value2,...}, which has any fields
            tablemodel, such as Category, the Django model name.
            unqiuefield, such as "categoryname", the unique identifier in a table, such as an unique barcodr for a row etc.
            expectedfields, such as ["categoryname", "notes"], fields expected in a table. 
        Output
            id, msg, if id>0, it's okay. Otherwise, it's not okay.
        '''
        id = 0
        msg = "Unique identifier no found in record: " + unqiuefield
        if unqiuefield not in datadic:
            print msg
            return id, msg
        
        record = {}
        keyword = datadic[unqiuefield]
        id = self.getPrimarykey(tablemodel, unqiuefield, keyword.strip())
        if id>0:
            # the record will be updated
            record['id'] = id
       
        for field in expectedfields:
            if field in datadic:
                value = datadic[field]
                if value is not None:
                    record[field] = value
                else:
                    record[field] = ""
            else:
                record[field] = ""
        id, msg = self.storeOneRecord(tablemodel, record)
        '''
        try:
            id, msg = self.storeOneRecord(tablemodel, record)
        except:
            id = 0
            msg = "Not saved "
            print msg, record
        '''
        return id, msg
    
    def retrieveIDsUniqueField(self, tablemodel, uniqueField):
        ''' Retrieve a dictionary, {"fieldvalue1":id1, "fieldvalue2":id2,...},
            where keys are the list of the unique constraint/field,
            and values are primary keys.
        Input
            tablemodel, the DB table model;
            uniqueField, the name of the unique constraint, which has one-to-one correponse to the primary key.
        Output
            a dictionary, {"fieldvalue1":id1, "fieldvalue2":id2,...}, where keys are the list of the unique constraint/field,
            and values are primary keys.
        '''
        return self.__dbconn.retrieveIDsUniqueField(tablemodel, uniqueField)
        
        
    def getRecords(self, tablemodel, datadic):
        ''' Retrieve records based on the specification in a dictionary.
        Input
            tablemodel, the DB table model;
            datadic, a dictionary, {"field1":value1, "field2":value2,...},
        Output
            a dictionary of the query set.
            
        '''
        return self.__dbconn.getRecords(tablemodel, datadic)
        
    def retrieveAllRecordsIntoExcel(self, sqlquery, headers, headersmapping, excelfile):
        ''' Run a customized query and save results into a excel file
        Input
            sqlquery, the customized query
            headers = ["Last Name",...] , the expected headers from columns in excel file.
            headersmapping, = {header1:column1, header2:column2,...}, where header1 is the name of header used for the column1 in the excel file.
                for example, for the column of "Last Name", which is the key in headersmapping,
                we get "last_name", which is the field name, such as "last_name", from the result set of the query to get the value.
        
        Output
            excelfile
        
        '''
        return self.retrieveAllRecordsIntoExcel_V2(sqlquery, headers, headersmapping, excelfile)
        
        
        if self.__dbconn  is None:
            return None
        
        print "retrieveAllRecordsIntoExcel"
        # http://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
        book = xlwt.Workbook(encoding="utf-8")
        sheet1 = book.add_sheet("Sheet 1")
        
        # example
        #sheet1.write(0, 0, "Display")
        #sheet1.write(1, 0, "Dominance")
        #sheet1.write(2, 0, "Test")

        #sheet1.write(0, 1, x)
        #sheet1.write(1, 1, y)
        #sheet1.write(2, 1, z)
        
        #self.cursor.execute(sqlquery)
        #columns = [desc[0] for desc in self.cursor.description]
        
        row = 0
        for index, item in enumerate(headers):
            sheet1.write(row, index, item)
        
        #objdics = self.run_custom_sql(sqlquery)
        
        self.__dbconn.cursor.execute(sqlquery)
        #nc = len(columns)
        #print headers
        #rowms = self.cursor.fetchall()
        rows = self.__dbconn.cursor.fetchall()
        rowslist = list(rows)
        for columns in rowslist:
            #print columns
            row += 1
            for index, item in enumerate(columns):
                newitem = self.toString(item)
                if index in headersmapping:
                    index = headersmapping[index]
                    try:
                        sheet1.write(row, index, newitem)
                    except:
                        newitem = self.cleanString(newitem)
                        sheet1.write(row, index, newitem)
        '''
        # the following not working because diclist not returned. 
        diclist = self.__dbconn.retrieve_custom_sql(sqlquery)
        for dici in diclist:
            #print columns
            row += 1
            index = 0
            for header in headers:
                header_mapped = headersmapping[header]
                if header_mapped in dici:
                    item = dici[header_mapped]
                else:
                    item = ""
                    
                newitem = self.toString(item)
                try:
                    sheet1.write(row, index, newitem)
                except:
                    newitem = self.cleanString(newitem)
                    sheet1.write(row, index, newitem)
                index += 1
        '''
        #print "book.save"
        book.save(excelfile)       
        #print "retrieveAllRecordsIntoExcel okay"    
        
    def retrieveAllRecordsIntoExcel_V2(self, sqlquery, headers, headersmapping, excelfile):
        ''' Run a customized query and save results into a excel file.
        Input
            sqlquery, the customized query
            headers = ["Last Name",...] , the expected headers from columns in excel file.
            headersmapping, = {header1:column1, header2:column2,...}, where header1 is the name of header used for the column1 in the excel file.
                for example, for the column of "Last Name", which is the key in headersmapping,
                we get "last_name", which is the field name, such as "last_name", from the result set of the query to get the value.
        
        Output
            excelfile
        
        Notes:
            Refer to: https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
            Use openpyxl to save the result, which supports the latest xlsx format,
            whill retrieveAllRecordsIntoExcel supports the older xls format.
        '''
        
        if self.__dbconn  is None:
            return None
        
        print "retrieveAllRecordsIntoExcel_v2"
        # https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        
        # Call a Workbook() function of openpyxl  
        # to create a new blank Workbook object 
        wb = openpyxl.Workbook() 
  
        # Get workbook active sheet   
        # from the active attribute 
        sheet = wb.active
        sheet.title = "sheet 1"
  
        # example
        # Cell objects also have row, column 
        # and coordinate attributes that provide 
        # location information for the cell. 
  
        # Note: The first row or column integer 
        # is 1, not 0. Cell object is created by 
        # using sheet object's cell() method. 
        #c1 = sheet.cell(row = 1, column = 1) 
  
        # writing values to cells 
        #c1.value = "ANKIT"
  
        #c2 = sheet.cell(row= 1 , column = 2) 
        #c2.value = "RAI"
  
        # Once have a Worksheet object, one can 
        # access a cell object by its name also. 
        # A2 means column = 1 & row = 2. 
        #c3 = sheet['A2'] 
        #c3.value = "RAHUL"
  
        # B2 means column = 2 & row = 2. 
        #c4 = sheet['B2'] 
        #c4.value = "RAI"
        
        rowi = 0
        for index, item in enumerate(headers):
            ci = sheet.cell(row = (rowi+1), column = (index+1))
            ci.value = item
        
        #objdics = self.run_custom_sql(sqlquery)
        
        self.__dbconn.cursor.execute(sqlquery)
        #nc = len(columns)
        #print headers
        #rowms = self.cursor.fetchall()
        rows = self.__dbconn.cursor.fetchall()
        rowslist = list(rows)
        for columns in rowslist:
            #print columns
            rowi += 1
            for index, item in enumerate(columns):
                newitem = self.toString(item)
                if index in headersmapping:
                    index = headersmapping[index]
                    try:
                        ci = sheet.cell(row = (rowi+1), column = (index+1))
                        ci.value = newitem
                    except:
                        newitem = self.cleanString(newitem)
                        ci = sheet.cell(row = (rowi+1), column = (index+1))
                        ci.value = newitem

        # Anytime you modify the Workbook object 
        # or its sheets and cells, the spreadsheet 
        # file will not be saved until you call 
        # the save() workbook method. 
        wb.save(excelfile) 
        #print "retrieveAllRecordsIntoExcel okay"    
        
        
    def getDistinctList(self, tablemodel, fieldname):
        ''' Refer to: https://stackoverflow.com/questions/10848809/django-model-get-distinct-value-list
        Get a distinct list, for example,
            Entity.objects.order_by('foreign_key').values('foreign_key').distinct()
            
        Input
            tablemodel, the DB table model;
            fieldname, the field name used for searching records.
        '''
        return self.__dbconn.getDistinctList(tablemodel, fieldname)

    def generateQuerySet(self, filterRules):
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
            
        Now we generate the query set by usiing the same idea above.
        
        Input
            filterRules, such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
        
            queryset, such as 
        '''
        return self.__dbconn.generateQuerySet(filterRules)
        
        
    def getUniueID(self, datadic, tablemodel, unqiuefield):
        ''' Given a datadic, get the primary key of category table.
        Input
            datadic, a dictionary, whose one of keys should be self.unqiuefield = "categoryname"
            tablemodel, the Django model of a database table, such as Category;
            unqiuefield, the field of the model used as the unique identifier of the primary key, such as categoryname.
        Output
            the primary id.
        '''
        unique_id = 0
        if unqiuefield in datadic:
            fieldvalue = datadic[unqiuefield]
            #if fieldvalue in uniqueIDs:
            #    unique_id = uniqueIDs[fieldvalue]
            unique_id = self.getPrimarykey(tablemodel, unqiuefield, fieldvalue)
            print "getUniueID: ", fieldvalue, unique_id
        
        return unique_id

    def storeOneToOneRecord(self, tablemodel, record, primarykeyname):
        return self.__dbconn.storeOneToOneRecord(tablemodel, record, primarykeyname)
        
    def insertOneRecord(self, tablemodel, record):
        ''' Insert a record into a table. 
        Input
            tablemodel, the table model defined in models.py for "DJANGO" DB connection, or
                        the table name in MySQL DB for "MYSQL"  DB connection
            record, record["fieldi": valuei] for i=1, ..., N, the pair of field name and its value.
                
            Notes: no unique constrain is checked in this subroutine.
        Output
            
        '''
        return self.__dbconn.insertOneRecord(tablemodel, record)
        
    def retrieveUniqueRecord(self, tablemodel, field, keyword):
        return self.__dbconn.retrieveUniqueRecord(tablemodel, field, keyword)
        
        
    def getOptions(self, tablemodel, valueField, textField, valueSelected):
        ''' Get the options used in a comboBox from a DB table directly.
        Input
            tablemodel,a Django model
            valueField, a field used as the id of an option in combobox, such as 'id', which usually the primary key of a record;
            textField, a field used as the text of an option in combobox, such as 'name' of the record;
            valueSelected, such as 3, the value of the valueField, such that 'id'=3, is the current value selected in combobox;
        
        Output
            options, = [op1, op2,...], where opi = {valueField:vi, textField:txti, 'selected':True}
        '''
        return self.__dbconn.getOptions(tablemodel, valueField, textField, valueSelected)

    def getQueryValue(self, sqlquery, db_alias=None):
        ''' Run a query to get a value or None.
        Input
            sqlquery, a SQL query for a numberic value, such as
                "select count(id) from table"
                "select volumn from table"
                "select id from table where connnstraint"
                
            db_alias=None, use the default database. Otherwise, use the specific database defined
                in local_settings.py. For more detail, refer to https://docs.djangoproject.com/en/dev/topics/db/multi-db/.
                
                For example, db_alias="seek_dmac"
        '''
        return self.__dbconn.getQueryValue(sqlquery, db_alias)

    def run_custom_transaction(self, sqlqueries, db_alias=None):
        if self.__dbconn is not None:
            return self.__dbconn.run_custom_transaction(sqlqueries, db_alias)
        
        return None
        
    def queryRecordsCustom(self, tablemodel, qset):
        if self.__dbconn is not None:
            return self.__dbconn.queryRecordsCustom(tablemodel, qset)
        
        return []
