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
from os.path import abspath, exists

SEEK_PRO = {'host': '', 'user':'', 'passwd':'', 'db':'seek_development'}
SEEK_DEV = {'host': '', 'user':'', 'passwd':'', 'db':'seek_development'}

class DBconn_mysql(object):
    ''' The class for connecting to the default database
    
    Typical usage of the class
    
        dbconn = DBconn_mysql("DJANGO")
        dbconn.conn
        dbconn.cursor

    '''
    def __init__(self):
        self.conn = None
        self.cursor = None
        mysqldb = self.__getDefaultDB()
        if mysqldb is not None:
            self.conn = MySQLdb.connect (host=mysqldb['host'], user=mysqldb['user'], passwd=mysqldb['passwd'], db=mysqldb['db'])
            self.cursor = self.conn.cursor()
        
    def __getDefaultDB(self):
        print 'getDefaultDB'
        f_path = abspath("dbconnect.txt")
        if exists(f_path):
            # this will be /.../bloodbiopsy/dbconnect.txt, which is good if it is run under shell directly.
            defaultDBFile = f_path
            print "Found in current folder:", defaultDBFile
        else:
            # this will be /.../bloodbiopsy/data/dbconnect.txt, which is good it it is run under web call.
            defaultDBFile = abspath("data/dbconnect.txt")
            print "Found in data folder:", defaultDBFile
    
        #defaultDB = SEEK_DEV
        defaultDB = self.__dbchoices("DEFAULT")
        try:
            fi = open(defaultDBFile,"r")
        except (OSError, IOError) as e:
            print 'File not found: ', defaultDBFile
            return defaultDB
    
        for line in fi:
            print line
            terms = line.strip().split(' ')
            db = terms[0]
            if db=='production':
                defaultDB = self.__dbchoices("SEEK_PRO")
            elif db=='development':
                defaultDB = self.__dbchoices("SEEK_DEV")
            else:
                print "Error: database selection not right: ", db
                print "The development DB will be used as default."
    
        print defaultDB
        fi.close()
        return defaultDB

    def __dbchoices(self, whichDB):
        print 'dbchoices'
        if whichDB=='SEEK_PRO':
            mysqldb = SEEK_PRO
        elif whichDB=='SEEK_DEV':
            mysqldb = SEEK_DEV
        else:
            mysqldb = SEEK_DEV
        
        print "DB selected: ", mysqldb
        return mysqldb

    def getPrimarykey(self, table, field, keyword):
        select_sql = "SELECT id FROM %s WHERE %s='%s';" % (table, field, keyword)
        return self.__selectPrimarykeyAny(select_sql)
    
    def __selectPrimarykeyAny(self, sqlquery): 
        rows = self.__retrieveRecords(sqlquery)
        if rows is None:
            return -1
    
        #print rows
        id = 0
        n = 0
        for row in rows:
            id = row[0]
            #print row[0]
            n += 1
    
        if n>1:
            #duplicated primary key
            return -n
    
        # either 0 or >0
        return id
            
         
    def __retrieveRecords(self, sqlquery):
        ''' Example how to process rows
        for row in rows:
            id = row[0]
            arraycode = row[1]
            striporder = row[2]
            stripcode = row[3]
            tubeindex = row[4]
            tubecode = row[5]
            numberofcells = row[6]
            cell_id = row[7]
            notes = row[8]
            #line = ','.join(row) + '\n'
            line = tubeindex + ',' + str(striporder) + ',' + str(numberofcells) + ',' + str(cell_id) + ',' + notes + ',' + tubecode + '\n'
            fo.write(line)
        fo.close()
        '''
        #print sqlquery
        try:
            # Execute the SQL command
            self.cursor.execute(sqlquery)
            # Commit your changes in the database
            self.conn.commit()
            rows = self.cursor.fetchall()
        except:
            # Rollback in case there is any error
            self.conn.rollback()
            print 'Error in running: ' +  sqlquery
            rows = None
        return rows
        
    def __is_numeric(self, s):
        try:
            i = float(s)
        except ValueError:
            # not numeric
            return False
        # numeric
        return True
            
    def retrieveFieldValue(self, table, primarykey, field):
        ''' Retrieve one record, given the primary key in a table
        '''
        sqlquery = "SELECT %s FROM %s " % (field, table)
        sqlquery += " WHERE id=" + str(primarykey) + ";"
    
        #return getOneValue(sqlquery, conn, cursor)
    
        data = []
        rows = self.__retrieveRecords(sqlquery)
        if rows is None:
            return None
    
        # expect just one record here
        n = 0
        for row in rows:
            data = row
            n += 1
    
        if n>1 or n==0:
            return None

        return data[0] 

    def __insertRecords(self, table, columns, rows):
        # Given a table name and a DB connection in cursor,
        # insert all rows into the table.
        # columns are exact table columns, for example, ['col1', 'col2',...,'colN']
        # rows are data rows in accordance with columns, for instance,
        #   [
        #       [x11,x12,...,x1N],
        #       ... 
        #       [xm1,xm2,...,xmN]
        #   ]
        #print 'insertRecords'
        index = 0
        sqlqueries = []
        for tabs in rows:
            #print tabs
            insert_row = []
            for value in tabs:
                #print value
                strValue = self.__convertSQLString(value)
                insert_row.append(strValue)
            #print insert_row
            #print ','.join(columns)
            #print ','.join(insert_row)
            insert_sql = "INSERT INTO %s (%s) VALUES (%s);" % (table, ','.join(columns), ','.join(insert_row)) 
            sqlqueries.append(insert_sql)
            #print "insert_sql", insert_sql
            index += 1
            
        return self.__runTransaction(sqlqueries)
    
    def __convertSQLString(self, value):
        ''' Given a numeric or string input value, convert it into a string used for SQL query.
        '''
        if not self.__is_numeric(value):
            strValue = '"' + MySQLdb.escape_string(value) + '"'
        else:
            strValue = str(value)
            
        return strValue

    def __insertOneRecord(self, table, record):
        ''' Input
                table, the table name in MySQL DB;
                record = {"field1":value1, "field2":value2, ...}
        '''
        columns = []
        row = []
        for key, value in record.items():
            columns.append(key)
            strValue = self.__convertSQLString(value)
            row.append(strValue)
                
        insert_sql = "INSERT INTO %s (%s) VALUES (%s);" % (table, ','.join(columns), ','.join(row))
        sqlqueries = []
        sqlqueries.append(insert_sql)
        return self.__runTransaction(sqlqueries)
        
    
    def __updateRecords(self, table, columns, rows):
        # Given a table name and a DB connection in cursor,
        # update all rows into the table.
        # columns are exact table columns, for example, ['col1', 'col2',...,'colN'],
        # the first column must be the primary key.
        # rows are data rows in accordance with columns, for instance,
        #   [
        #       [x11,x12,...,x1N],
        #       ... 
        #       [xm1,xm2,...,xmN]
        #   ]
        ''' Requirement,
                The primary key id = row[0], where row in rows
        '''
        index = 0
        sqlqueries = []
        for tabs in rows:
            update_sql = "UPDATE %s SET " % table 
            n = 0
            where = " WHERE id="
            for value in tabs:
                #print value
                if n==0:
                    where += str(value) + ";"
                else:
                    strValue = self.__convertSQLString(value)
                
                    if n<(len(columns)-1):
                        update_sql += columns[n] + "=" + strValue + ", "
                    else:
                        update_sql += columns[n] + "=" + strValue + " " + where
                n += 1
            
            #print update_sql
            sqlqueries.append(update_sql)
            
        return self.__runTransaction(sqlqueries) 
       
    def updateOneRecord(self, table, record):
        ''' Input
                table, the table name in MySQL DB;
                record = {"field1":value1, "field2":value2, ...}
        '''
        update_sql = "UPDATE %s SET " % table 
        where = " WHERE id="
        for key, value in record.items():
            if key == "id":
                where += str(value) + ";"
            else:
                strValue = self.__convertSQLString(value)
                update_sql += key + "=" + strValue + ", "
            
        update_sql = update_sql[:-1]    # remove last ","
        update_sql += " " + where
        sqlqueries = []
        sqlqueries.append(update_sql)
        return self.__runTransaction(sqlqueries)
        
       
    def __runTransaction(self, sqlqueries):
        ''' Use transaction to execute a series of sql queries.
            Refer to: http://www.zyxware.com/articles/2599/how-to-enable-transactions-with-mysql-and-python
        Input
            conn = MySQLdb.connect(host="dbhost", user="dbuser" , passwd="dbpass", db="dbname")
            sqlqueies = [query1, query2, ...]
        '''
        msg = "Run SQL transaction "
        status = 1
        
        self.conn.autocommit(False)
        try:
            for sqlquery in sqlqueries:
                self.cursor.execute(sqlquery)
            self.conn.commit()
            msg += " successfully"
            status = 1
        except:
            self.conn.rollback()
            msg += " failed"
            status = 0
 
        return msg, status
 
    def __deleteRecords(self, table, field, keyword):   
        delete_sql = "DELETE FROM %s WHERE %s='%s';" % (table, field, keyword) 
        sqlqueries = []
        sqlqueries.append(delete_sql)
        return self.__runTransaction(sqlqueries)
        
    def getLatestID(self, table):
        select_sql = "SELECT max(id) FROM %s;" % (table)
        rows = self.__retrieveRecords(select_sql)
        if rows is None:
            id = 0
        else:
            row = rows[0]
            id = row[0]
            if id==None:
                id = 0
        new_id = id + 1
        return new_id    
    
    def storeOneRecord(self, table, record):
        ''' Input
                table, the table name in MySQL DB;
                record = {"field1":value1, "field2":value2, ...}
        '''
        id = 0
        if "id" in record:
            id = record["id"]
            
        if id>0:
            msg, status = self.__updateOneRecord(table, record)
        else:
            id = self.__getLatestID(table)
            record["id"] = id
            msg, status = self.__insertOneRecord(table, record)
        
        if status:
            return id, msg
        else:
            return -1, msg
    
    def retrieveOneRecord(self, table, primarykey):
        ''' Retrieve one record, given the primary key in a table
        '''
        sqlquery = "SELECT * FROM %s " % (table)
        sqlquery += " WHERE id=" + str(primarykey) + ";"
    
        data = []
        #print sqlquery
        try:
            # Execute the SQL command
            cursor.execute(sqlquery)
            # Commit your changes in the database
            conn.commit()
            rows = cursor.fetchall()
        except:
            # Rollback in case there is any error
            conn.rollback()
            print 'Error in SELECT: ' +  sqlquery
            return data
    
        ''' Example how to process rows
        fo = open(output_csv_file,"w")
        line = 'cell_id,arraycode,striporder,stripcode,tubeindex,cellcode,numberofcells,notes\n'
        line = 'tubeindex,striporder,numberofcells,unique_cell_id, notes, tubecode\n'
        fo.write(line)
        for row in rows:
            id = row[0]
            arraycode = row[1]
            striporder = row[2]
            stripcode = row[3]
            tubeindex = row[4]
            tubecode = row[5]
            numberofcells = row[6]
            cell_id = row[7]
            notes = row[8]
            #line = ','.join(row) + '\n'
            line = tubeindex + ',' + str(striporder) + ',' + str(numberofcells) + ',' + str(cell_id) + ',' + notes + ',' + tubecode + '\n'
            fo.write(line)
        fo.close()
        '''
    
        # expect just one record here
        for row in rows:
            data = row
    
        # to be modified how to output a dictioanry instaed of a array
        #  ???????????????
        return data  
    
        
    def retrieve_custom_sql(self, sqlquery):
        ''' Retrieve a list of records and output them into a CSV file.
        Input
            sqlquery, a customized sql query, for example,
        sqlquery = "SELECT C.id as id, "
        sqlquery += " F.arraycode as arraycode, "
        sqlquery += " A.striporder as striporder, "
        sqlquery += " B.stripcode as stripcode, "
        sqlquery += " C.tubeindex as tubeindex, "
        sqlquery += " E.tubecode as tubecode, "
        sqlquery += " D.numberofcells as numberofcells, "
        sqlquery += " D.id as cell_id, "
        sqlquery += " D.notes as notes "
        sqlquery += "FROM data_wga_arraystrip A "
        sqlquery += "left join data_wga_strip B on A.wga_strip_id=B.id "
        sqlquery += "left join data_wga_stripcell C on C.wga_strip_id=B.id  "
        sqlquery += "left join data_wga_cell D on C.wga_cell_id=D.id  "
        sqlquery += "left join data_wga_tube E on D.wga_tube_id=E.id  "
        sqlquery += "left join data_wga_array F on A.wga_array_id=F.id  "
        sqlquery += "where A.wga_array_id=" + str(array_id)
        sqlquery += " order by A.striporder;"
    
        Output
            rows
        '''
        #print sqlquery
        try:
            # Execute the SQL command
            self.cursor.execute(sqlquery)
            # Commit your changes in the database
            self.conn.commit()
            rows = self.cursor.fetchall()
        except:
            # Rollback in case there is any error
            self. conn.rollback()
            print 'Error in SELECT: ' +  sqlquery
            return None
    
        ''' Example how to process rows
        fo = open(output_csv_file,"w")
        line = 'cell_id,arraycode,striporder,stripcode,tubeindex,cellcode,numberofcells,notes\n'
        line = 'tubeindex,striporder,numberofcells,unique_cell_id, notes, tubecode\n'
        fo.write(line)
        for row in rows:
            id = row[0]
            arraycode = row[1]
            striporder = row[2]
            stripcode = row[3]
            tubeindex = row[4]
            tubecode = row[5]
            numberofcells = row[6]
            cell_id = row[7]
            notes = row[8]
            #line = ','.join(row) + '\n'
            line = tubeindex + ',' + str(striporder) + ',' + str(numberofcells) + ',' + str(cell_id) + ',' + notes + ',' + tubecode + '\n'
            fo.write(line)
        fo.close()
        '''
        return rows
    
    def retrieveNumberOfRecords(self, tablename):
        ''' Modified from retrieveTotalRecords(tablename) in dbjango.py.
            Returns the total number of records in a table.
            Input
                tablename, the actual database table name (not the table model in Django).
            
            Output
                The total number of records in the table.
        '''
        sqlquery = "select count(*) as total from " + tablename + ";"
        # such as 
        #   rows = [{'total': 686L}]
        rows = self.retrieve_custom_sql(sqlquery)
        row = rows[0]   # only one record
        total = row[0]  # only one value
        return total
    