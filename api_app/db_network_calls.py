#!/usr/bin/env python
import subprocess
import json
from subprocess import call

import string
import getpass
from urllib2 import urlopen, Request
import urllib2
import io
import sys; 
import argparse
from dbconn_mysql import DBconn_mysql

 
DB_FIELD_TYPES = { 
    'Text':'TEXT NOT NULL',
    'Date':'date NOT NULL',
    'Float':'FLOAT',
    'String':'char(255) NOT NULL',
    'Integer':'int(11) NOT NULL'
}

DB_FIELD_TYPES = { 
    'Text':'text',
    'Date':'date',
    'Float':'float',
    'String':'char(255)',
    'Integer':'int(11)'
}

DB_FIELD_TYPES = { 
    'Text':'text',
    'Date':'date',
    'Float':'float',
    'String':'varchar(255)',
    'Integer':'int'
}

def tableSQL1(tablename, attributes, base_types):
    sql = "CREATE TABLE '" + tablename + "' ("
    for attribute in attributes:
        attributeName = attribute[1]
        sample_attribute_type_id = attribute[2]
        base_type = base_types[sample_attribute_type_id]
        dbtype = DB_FIELD_TYPES[base_type]  
        fieldname = attributeName.strip()
        fieldname = fieldname.replace(" ", "_")
        sql += "'" + fieldname + "' " + dbtype + ","

    sql = sql[:-1]      
    sql += ") ENGINE=InnoDB"
    sql = (sql)
    return sql
    
def tableSQL(tablename, attributes, base_types, parents):
    sql = "CREATE TABLE " + tablename + " ("
    sql += "id INT AUTO_INCREMENT PRIMARY KEY,"
    
    for attribute in attributes:
        attributeName = attribute[1]
        sample_attribute_type_id = attribute[2]
        base_type = base_types[sample_attribute_type_id]
        dbtype = DB_FIELD_TYPES[base_type]          
        
        fieldname = attributeName.strip()
        fieldname = fieldname.replace(" ", "_")
        if "(" in fieldname:
            fieldname = fieldname.replace("(", "_")
        if ")" in fieldname:
            fieldname = fieldname.replace(")", "_")
        
        if fieldname.lower()!='id':
            sql += fieldname + " " + dbtype + ","
    sql_foreign = ''
    for parent_type, uids in parents.items():
        foreign_tablename = parent_type
        if "." in parent_type:
            foreign_tablename = parent_type.replace(".", "_")
            
        ni = len(uids)
        if ni>0:
            sql += foreign_tablename + "_id int,"
            
            sql_foreign += 'alter table ' + tablename + ' add foreign key (' + foreign_tablename + '_id) references ' + foreign_tablename + '(id);'

    sql = sql[:-1] 
    sql += ")"
    return sql, sql_foreign

def runSQL(table_description, tablename, dbconn_out):
    try:
        dbconn_out.cursor.execute(table_description)
        status = 1
    except:
        msg = 'Error in creating table: ' + tablename
        status = 0
    else:
        status = 1
        
    return status


def create_database(cursor):
    try:
        cursor.execute(
            "CREATE DATABASE {} DEFAULT CHARACTER SET 'utf8'".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Failed creating database: {}".format(err))
        exit(1)

    try:
        cursor.execute("USE {}".format(DB_NAME))
    except mysql.connector.Error as err:
        print("Database {} does not exists.".format(DB_NAME))
        if err.errno == errorcode.ER_BAD_DB_ERROR:
            create_database(cursor)
            print("Database {} created successfully.".format(DB_NAME))
            cnx.database = DB_NAME
        else:
            print(err)
            exit(1)
 
def getBaseTypes(dbconn_seek):
    sqlquery = "SELECT id, title, base_type FROM sample_attribute_types;"
    rows = dbconn_seek.retrieve_custom_sql(sqlquery)
    base_types = {}
    for row in rows:
        id = row[0]
        base_type = row[2]
        base_types[id] = base_type
    
    sqlquery = "SELECT id, title, sample_attribute_type_id FROM sample_attributes;"
    rows2 = dbconn_seek.retrieve_custom_sql(sqlquery)
    dbtypes = []
    for row in rows2:
        id = row[0]
        sample_attribute_type_id = row[2]
        base_type = base_types[sample_attribute_type_id]
        if base_type not in dbtypes:
            dbtypes.append(base_type)
        
    for base_type in dbtypes:
        print(base_type)
        
    return base_types
        
def createSampletypeTable(dbconn_seek, dbconn_out, sample_type, sample_type_id, base_types, parents):
    tablename = sample_type
    if "." in sample_type:
        tablename = sample_type.replace(".", "_")
 
    sqlquery = "DROP TABLE IF EXISTS " + tablename + ";"
    dbconn_out.cursor.execute(sqlquery)
    
    sqlquery = "SELECT id, title, sample_attribute_type_id FROM sample_attributes where sample_type_id=" + str(sample_type_id) + ";"
    attributes = dbconn_seek.retrieve_custom_sql(sqlquery)
           
    table_description, sql_foreign = tableSQL(tablename, attributes, base_types, parents)
    runSQL(table_description, tablename, dbconn_out)
    return tablename, sql_foreign
    
def getParentUIDs(sampleDic):
    uids = []
    
    for key, value in sampleDic.items():
        if "parent" in key:
            if value is None:
                continue
            else:
                if ";" in value:
                    vis = value.split(";")
                    for vi in vis:
                        vi = vi.strip()
                        if len(vi)>0:
                            uids.append(vi)
                else:
                    value = value.strip()
                    if len(value)>0:
                        uids.append(value)
                
    return uids    
    
def getParents(sampleDic):
    uids = getParentUIDs(sampleDic)
    
def retrieveSampleTypeInfo(dbconn_seek, sample_type_id, sample_types):
    sqlquery = "SELECT id, title, json_metadata FROM samples where sample_type_id=" + str(sample_type_id) + ";"
    samples = dbconn_seek.retrieve_custom_sql(sqlquery)
    nsamples = len(samples)
    parents = {}
    for sample in samples:
        id = sample[0]
        uid = sample[1]
        record_json = sample[2]
        sampleDic = json.loads(record_json)
        uids = getParentUIDs(sampleDic)
        for uid in uids:
            terms = uid.split('-')
            sample_type = terms[0]
            if sample_type not in sample_types:
                continue
            
            if sample_type in parents:
                parents_uids = parents[sample_type]
            else:
                parents_uids = []
            if uid not in parents_uids:
                parents_uids.append(uid)
            parents[sample_type] = parents_uids
 
    return nsamples, parents
    
def getSampleTypes(dbconn_seek):
    sqlquery = "SELECT id, title FROM sample_types;"
    rows = dbconn_seek.retrieve_custom_sql(sqlquery)
    sample_types = {}
    for row in rows:
        sample_type_id = row[0]
        sample_type = row[1]
        if "_old" not in sample_type:
            sample_types[sample_type] = sample_type_id
        
    return sample_types
 
def calSampleNetwork():
    dbconn_in = DBconn_mysql('SEEK_IN')
    sample_types = getSampleTypes(dbconn_in)
    network = []
    numbers = {}
    for sample_type, sample_type_id in sample_types.items():
        nsamples, parents = retrieveSampleTypeInfo(dbconn_in, sample_type_id, sample_types)
        numbers[sample_type] = nsamples
        for parent_type, uids in parents.items():
            link = []
            ni = len(uids)
            if ni>0:
                link.append(parent_type)   
                link.append(sample_type)
                link.append(ni)
                network.append(link)

    for sample_type, nsamples in numbers.items():
        print("%s\t%d"%(sample_type, nsamples))
    
    for link in network:
        print("%s\t%s\t%s"%(link[0], link[1], str(link[2])))
    
    return
 
def runDBTest():
    dbconn_in = DBconn_mysql('SEEK_IN')
    base_types = getBaseTypes(dbconn_in)
    
    dbconn_out = DBconn_mysql('SEEK_OUT')
    sample_types = getSampleTypes(dbconn_in)
    
    network = []
    numbers = {}
    sql_foreign_keys = ''
    for sample_type, sample_type_id in sample_types.items():
        nsamples, parents = retrieveSampleTypeInfo(dbconn_in, sample_type_id, sample_types)
        
        tablename, sql_foreign = createSampletypeTable(dbconn_in, dbconn_out, sample_type, sample_type_id, base_types, parents)
        sql_foreign_keys += sql_foreign
        
    runSQL(sql_foreign_keys, '', dbconn_out)  
    return
        
def main():
    calSampleNetwork()
    sys.exit(0)
    return

if __name__ == "__main__":
    main()
