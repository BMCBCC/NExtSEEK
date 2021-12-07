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
from django.db import connection
from django.db import connections
from django.db import transaction
from django.db import IntegrityError

from iocsv import saveCsvfile, getString, getFloat
#from dbdjango import updateStringValuesAdditive

from django.forms.models import model_to_dict
from django.db.models.fields.related import OneToOneField
from django.db.models import Q

import datetime
import simplejson

from conversion import convertSQLString, is_numeric

class DBconn_django(object):
    ''' The class for connecting to the default database
    
    Typical usage of the class
    
        dbconn = DBconnection("DJANGO")
        dbconn.conn
        dbconn.cursor

    '''
    def __init__(self):
        #print "DBconn_django: __init__"
        self.conn = connection
        self.cursor = self.conn.cursor()
            
    def getPrimarykey(self, table, field, keyword):
        ''' Given a unique identifier, retrieve its primary key.
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
        if keyword is None:
            return -1
        
        uniqueKeyword = keyword.strip()
        if len(uniqueKeyword)==0 or uniqueKeyword=="NA":
            return -1
        
        query = {}
        #query['%s__contains'%field] = keyword
        query['%s__exact'%field] = keyword
        objs = table.objects.filter(**query)
        total = objs.count()
        #print total
        if total==1:
            # already exist
            obj = objs[0]
            return obj.id
        #elif total>1:
        #    return 0
        else:
            #not defined or duplicated id
            return -1    

        return -1    
            
    def retrieveFieldValue(self, table, id, fieldname):
        ''' Retrieve the value for a field, given the primary key in a table.
        Input
            table, the table name
            id, the primary key
            fieldname, the name of the field that will be retrieved.
                If the field is a foreign key, such as "wga_tube", do not use "wga_tube_id" for it.
                Use the foreign key directly, i.e., use "wga_tube"  
            
        
        Output
        The value for that field, given the primary key.
        '''
        #print "id: ", id
    
        objs = table.objects.filter(id=id)
        total = objs.count()
        #print total
        if total==1:
            # already exist
            obj = objs[0]
            #print "obj ", obj
            for f in obj._meta.fields:
                name = f.name
                #print name
                if name==fieldname:
                    #print 'f.name ', name
                    #value = unicode(getattr(o,f.name))
                    try:
                        value = getattr(obj,f.name)
                    except AttributeError:
                        value = None
                        
                    #print 'value ', type(value)
                    
                    
                    #print 'value ', unicode(value)
                
                    return unicode(value)
            
            return None
        else:
            #not defined or duplicated id
            return None    

        return None
    
    def updateFieldValue(self, tablemodel, idIn, fieldname, fieldvlue):
        try:
            tablemodel.objects.filter(id=idIn).update(fieldname=fieldvlue)
            msg = ""
        except table.DoesNotExist:
            msg = 'Error: no update on ' + fieldname
        print msg
    
    def __runTransaction(self, sqlqueries):
        ''' Use transaction to execute a series of sql queries.
            Refer to:
                http://stackoverflow.com/questions/34730385/django-rollback-save-with-transaction-atomic
                https://docs.djangoproject.com/en/1.10/topics/db/transactions/
            
        Input
            conn = MySQLdb.connect(host="dbhost", user="dbuser" , passwd="dbpass", db="dbname")
            sqlqueies = [query1, query2, ...]
        '''
        msg = "Run SQL transaction "
        status = 1
        sid = transaction.savepoint()
        
        # execute db operations here
        # run model operation
        #some_object = SomeModel(...)
        #some_object.save()
        something = 0

        if something:
            transaction.savepoint_rollback(sid)
            msg += " failed, roll back."
            status = 0
        else:
            try:
                # In worst case scenario, this might fail too
                transaction.savepoint_commit(sid)
                msg += " successfully"
                status = 1
            except IntegrityError:
                transaction.savepoint_rollback(sid)
                msg += " failed, recover."
                status = 0
        return msg, status
    
    def __insertOneRecord(self, tablemodel, record):
        ''' Input
                tablemodel, the table model defined in models.py
                record = {"field1":value1, "field2":value2, ...}
        '''
        msg = "Run SQL transaction "
        return self.__insertOneRecord_revised(tablemodel, record)
        
        status = 1
        sid = transaction.savepoint()
        try:
            # In worst case scenario, this might fail too
            tb = tablemodel(**record)
            tb.save()
            transaction.savepoint_commit(sid)
            msg += " successfully"
            status = 1
        except IntegrityError:
            transaction.savepoint_rollback(sid)
            msg += " failed."
            status = 0
            
        if status==0:
            return self.__insertOneRecord_revised(tablemodel, record)
            
        return msg, status
    
    def __insertOneRecord_revised(self, tablemodel, record):
        ''' INsert a new record into the DB table.
        Input:
            record,the record
        
        Output:
            msg, any message
            status, =0, if record['id'] is empty or None value;
                    =1, if insertion is successful
        
        Requirement:
            id=record['id']=self.getLatestID(tablemodel), should not be empty or None value, but must be 
        '''
        
        print "__insertOneRecord_revised"
        if "id" not in record:
            msg = "__insertOneRecord_revised error: no primary key in record for insert."
            print(msg)
            return msg, 0
        
        id = record['id']
        if id is None or id<=0:
            msg = "__insertOneRecord_revised error: primary key is not available."
            print(msg)
            return msg, 0
        
        #print "__insertOneRecord_revised id: ", id
        #objs = tablemodel.objects.filter(id=id)
        #obj = objs[0]
        #obj = tablemodel.objects.get(id=id)
        #obj = tablemodel.objects.get(pk=id)
        obj = tablemodel()
        #print obj
        for f in obj._meta.fields:
            name = f.name
            foreignkey = name + "_id"
            #print(name, foreignkey)
            if name in record:
                value = record[name]
                setattr(obj, name, value)
                print(name, value)
            elif foreignkey in record:
                value = record[foreignkey]
                print(foreignkey, value)
                setattr(obj, foreignkey, value)    
        
        print("run obj.sav")
        try:
            obj.save()
            status = 1
            msg = "Successful in adding record"
        except:
            status = 0
            msg = "Failed in adding record"
            
        print(msg)
        return msg, status
    
    
    def __updateOneRecord(self, tablemodel, record):
        ''' Input
                tablemodel, the table model defined in models.py
                record = {"field1":value1, "field2":value2, ...}
                
            Requirement
                In running this subroutine, the none-null values must be provided in record.
                Otherwise, tb.save() would not work and returns no value. 
        '''
        msg = "Run SQL transaction "
        
        # id required
        if "id" not in record:
            msg = "__updateOneRecord error: no primary key in record for update."
            return -1, msg
        
        status = 1
        sid = transaction.savepoint()

        # In worst case scenario, this might fail too
        #tb = tablemodel(**record)
        #tb.save()
        id = record["id"]
        record_old = self.retrieveOneRecord(tablemodel, id)
        #for k, v in record.iteritems():
        #    if k in record_old:
        #        record_old[k] = v
                    
        record_forUpdate = self.__updateRecord(record_old, record)
        try:            
            model = tablemodel()
            for k, v in record_forUpdate.iteritems():
                setattr(model, k, v)
            model.save()
            
            transaction.savepoint_commit(sid)
            msg = "Successful in updating record"
            status = 1
        except IntegrityError:
            transaction.savepoint_rollback(sid)
            print("record from DB: ", record_old)
            print("record_forUpdate: ", record_forUpdate)
            msg = "Failed in updating record"
            print(msg)
            status = 0
            
        return msg, status  
    
    def deleteOneRecord(self, tablemodel, id):
        ''' Delete one record, given the primary key.
            Input
                tablemodel, the table model defined in models.py
                id, the primary key
        '''
        b = tablemodel.objects.get(pk=id)
        # This will delete the record and all of its child objects.
        b.delete()
    
    def getLatestID(self, tablemodel):
        ''' Retrieve the next primary key available for inserting new record.
        Input
            tablemodel, the table model defined in models.py
    
        Output
            Return the primary key available 
        '''
        try:
            max_id = tablemodel.objects.latest('id').id
            #print "max_id: ", max_id
        except tablemodel.DoesNotExist:
            max_id = 0
            
        new_id = max_id + 1
        return new_id
    
    def storeOneRecord(self, tablemodel, record):
        ''' Input
                tablemodel, the table model defined in models.py
                record = {"field1":value1, "field2":value2, ...}
                
            Output
                id, msg, where
                    id is the primary key, or -1 if any error
                    msg is any message
        '''
        id = 0
        if "id" in record:
            id = record["id"]
        if id>0:
            print "update record at id: ", id
            msg, status = self.__updateOneRecord(tablemodel, record)
        else:
            id = self.getLatestID(tablemodel)
            record["id"] = id
            msg, status = self.__insertOneRecord(tablemodel, record)
            print "Insert record at id: ", id
            
        if status:
            return id, msg
        else:
            return -1, msg
            
    def __objToDic(self, obj):
        ''' Convert Django obj to a dictionary.
            Input
                obj, a model object, its fields can be accessed through value1=obj.field1.
            
            Output
                objdic, whose field can be accessed through value1=objdic[field1].
                
            Usage
                {'cellimgfile': None, 'activetubetype': u'na', 'status_nklp': -1L, 'pf_reads': None,
                'status_clinicalcancer': -1L, 'number_libraryed': 0L, u'id': 9440L, 'status_library': None,
                'status_ql': None, 'status_qc': -1L, 'activetubeid': 0L, 'status_wga': 4L, 'status_seq': None,
                'cellindex': None, 'numberofcells': None, 'status_qqn': 1L, 'wga_tube': <Wga_tube: BT00005143>,
                'hdf5file': None, 'status_recover': 3L, 'number_reracked': 0L, 'date': datetime.date(2017, 2, 28),
                'cellcode': u'FC19269516', 'number_wgarrayed': 0L, 'status_exome': -1L, 'coeff': None,
                'status_rerack': None, 'celltype': u'ctDNA'}
                
                where the foreign parent 'wga_tube' is returned as a query object : <Wga_tube: BT00005143>.
                
            Notes
                The date format will be changed to string instead of Date format.
                However, it would slowdown a little bit the processing.  
        '''
        objdic = {}
        if obj is None:
            return objdic  
          
        # Include direct parent, for example, Wga_tube in Wga_cell model.   
        for f in obj._meta.fields:
        #for f in obj._meta.concrete_fields:
        # Exclude direct parent, for example, Wga_tube in Wga_cell model.     
        #for f in obj._meta.get_fields(include_parents=False, include_hidden=False):
            #print f.name, f
            fieldValue = getattr(obj,f.name)
            objdic[f.name] = self.convertDatetimeToString(fieldValue)
        #print objdic 
        return objdic
    
    def __objToDic_2(self, obj):
        ''' Convert Django obj to a dictionary, using approach 2 discussed in
            http://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact
            Input
                obj, a model object, its fields can be accessed through value1=obj.field1.
            
            Output
                objdic, whose field can be accessed through value1=objdic[field1].
            
            Usage,
                {'cellimgfile': None, 'activetubetype': u'na', 'status_nklp': -1L, 'pf_reads': None,
                'status_clinicalcancer': -1L, 'number_libraryed': 0L, u'id': 9440L, 'status_library': None,
                'status_ql': None, 'status_qc': -1L, 'activetubeid': 0L, 'status_wga': 4L, 'status_seq': None,
                'cellindex': None, 'numberofcells': None, 'status_qqn': 1L, 'wga_tube': 5143L, 'hdf5file': None,
                'status_recover': 3L, 'number_reracked': 0L, 'date': datetime.date(2017, 2, 28),
                'cellcode': u'FC19269516', 'number_wgarrayed': 0L, 'status_exome': -1L, 'coeff': None,
                'status_rerack': None, 'celltype': u'ctDNA'} 
                In this case, the foreign parent 'wga_tube' is returned as its foreign key : 5143L.

        '''
        #objdic = model_to_dict(obj, fields=[field.name for field in obj._meta.fields])
        objdic = model_to_dict(obj)
        
        # more usage: http://stackoverflow.com/questions/12382546/how-can-i-turn-django-model-objects-into-a-dictionary-and-still-have-their-forei
        #objdic = model_to_dict(obj, fields=[], exclude=[])
        
        #print objdic 
        return  objdic
    
    def __objToDic_3(self, obj, prefix):
        ''' Convert Django obj to a dictionary.
            Input
                obj, a model object, its fields can be accessed through value1=obj.field1.
            
            Output
                objdic, whose field can be accessed through value1=objdic[field1].
                
            Usage
                {'cellimgfile': None, 'activetubetype': u'na', 'status_nklp': -1L, 'pf_reads': None,
                'status_clinicalcancer': -1L, 'number_libraryed': 0L, u'id': 9440L, 'status_library': None,
                'status_ql': None, 'status_qc': -1L, 'activetubeid': 0L, 'status_wga': 4L, 'status_seq': None,
                'cellindex': None, 'numberofcells': None, 'status_qqn': 1L, 'wga_tube': <Wga_tube: BT00005143>,
                'hdf5file': None, 'status_recover': 3L, 'number_reracked': 0L, 'date': datetime.date(2017, 2, 28),
                'cellcode': u'FC19269516', 'number_wgarrayed': 0L, 'status_exome': -1L, 'coeff': None,
                'status_rerack': None, 'celltype': u'ctDNA'}
                
                where the foreign parent 'wga_tube' is returned as a query object : <Wga_tube: BT00005143>.
                
            Notes
                The date format will be changed to string instead of Date format.
                However, it would slowdown a little bit the processing.  
        
            How to fix the error that:   AttributeError: 'tuple' object has no attribute '_meta'
            Refer to: https://stackoverflow.com/questions/39112252/restframework-tuple-object-has-no-attribute-meta
            Solution,
                class BDetail(models.Model):
                    lat = models.FloatField(blank=True, null=True)
                    lng = models.FloatField(blank=True, null=True)

                    class Meta:
                        # managed = False
                        db_table = 'b_detail'       # define how the table is called
                        fields = ('lat', 'lng')     # define which fields are available
                where the Meta has been defined.

        '''
        objdic = {}
        if obj is None:
            return objdic  
          
        # Include direct parent, for example, Wga_tube in Wga_cell model.   
        for f in obj._meta.fields:
        #for f in obj._meta.concrete_fields:
        # Exclude direct parent, for example, Wga_tube in Wga_cell model.     
        #for f in obj._meta.get_fields(include_parents=False, include_hidden=False):
            #print(f.name, f)
            if f.is_relation:
                # exclude parent foreign key
                #print f
                name = f.name
                #print(f.name, f)
            else:
                fieldValue = getattr(obj,f.name)
                name = prefix + f.name
                objdic[name] = fieldValue
        #print objdic
        
        #print(obj.id)
        #objdic['id'] = obj.id
        return objdic
    
    def convertDatetimeToString(self, fieldValue):
        ''' COnvert date format to string
        '''
        DATE_FORMAT = "%Y-%m-%d" 
        TIME_FORMAT = "%H:%M:%S"

        if isinstance(fieldValue, datetime.date):
            return fieldValue.strftime(DATE_FORMAT)
        elif isinstance(fieldValue, datetime.time):
            return fieldValue.strftime(TIME_FORMAT)
        elif isinstance(fieldValue, datetime.datetime):
            return fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
        else:
            return fieldValue
    
    def __objToDic_joint(self, obj):
        ''' Convert Django obj to a dictionary, using approach 5: Custom function, discussed in
            http://stackoverflow.com/questions/21925671/convert-django-model-object-to-dict-with-all-of-the-fields-intact
        
        Input
            obj, a model object, its fields can be accessed through value1=obj.field1.
            
        Output
            objdic, whose field can be accessed through value1=objdic[field1]. All joint child fileds are also included.
        '''
        # Gget all direct fields
        #objdic = self.__objToDic(obj)
        objdic =  model_to_dict(obj)
        
        # more usage: http://stackoverflow.com/questions/12382546/how-can-i-turn-django-model-objects-into-a-dictionary-and-still-have-their-forei
        #objdic = model_to_dict(obj, fields=[], exclude=[])
        opts = obj._meta
        #for f in opts.concrete_fields + opts.one_to_one:
        #    print "f: ", f
        #    if isinstance(f, OneToOneField):
        #        if obj.pk is None:
        #            objdic[f.name] = []
        #        else:
        #            objdic[f.name] = list(f.value_from_object(obj).values_list('pk', flat=True))
        #    else:
        #        objdic[f.name] = f.value_from_object(obj)
                
        #for f in opts.fields:
        #for f in opts.concrete_fields:
        # Refer to: https://docs.djangoproject.com/en/1.10/ref/models/meta/
        # also retrieve fields that are used to back other field's functionality. This will also include any fields that have a related_name
        
        # get all child fields in one-to-one children
        for f in opts.get_fields(include_parents=False, include_hidden=True):
            #if f.is_relation:
            #    print f
            if f.one_to_one:
                # include all one-to-one child fields
                # such as Wga_cell_status and Wga_cell_ulp
                #print "f: one to one", f.name
                obj_child = getattr(obj,f.name)
                #objdic_child = self.__objToDic(obj_child)
                objdic_child = model_to_dict(obj_child)
                # add sub-fields into main dic
                objdic.update(objdic_child)
            elif f.many_to_one:
                # such as Wga_tube, which is a parent foreign key to Wga_cell model
                #print f
                obj_child = getattr(obj,f.name)
                #print "name_child: ", name_child
                #objdic_child = self.__objToDic(obj_child)
                #objdic_child = self.__objToDic_2(obj_child)
                prefix = f.name + '.'
                objdic_child = self.__objToDic_3(obj_child, prefix)
                
                # add sub-fields into main dic
                objdic.update(objdic_child)
            #elif f.many_to_many:
            #    print f
            #elif f.one_to_many:
                # such as Wga_6mltube_cell, Wga_stripcell, Wga_rrarraycell, which are children foreign keys to Wga_cell table.
            #    print f
            #else:
            #    print f
                
        #print objdic 
        return  objdic
    
    def __objsToDicList(self, objs):
        ''' Convert Django objs to a dictionary.
        
        Input
            objs, result set from Django query.
            
        Output
            objlist, =[dic1, dic2, ..., dicn], where dic={name1:value1, name2:value2,...}
        '''
        objsdiclist = []
        for obj in objs:
            #print obj
            objdic = self.__objToDic_3(obj, '')
            #objdic = self.__objToDic_2(obj)
            #objdic = self.__objToDic_joint(obj)
            objsdiclist.append(objdic)
            
        #print objsdiclist[0]
        #print "obj.x_e: ", obj.x_e
        return objsdiclist 
            
    def retrieveOneRecord(self, tablemodel, idIn):
        ''' Retrieve one record, given the primary key in a table.
        Input
            table, the table name
            id, the primary key
        
        Output
            one record in the format of a dictionary, given the primary key.
        '''
        #print id
        objs = tablemodel.objects.filter(id=idIn)
        total = objs.count()
        #print total
        if total==1:
            # already exist
            obj = objs[0]
        else:
            #not defined or duplicated id
            obj = None    

        #return obj
        return self.__objToDic(obj)
            
    def dictfetchall(self):
        #"Returns all rows from a cursor as a dict"
        desc = self.cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in self.cursor.fetchall()
        ]    
    
    def retrieve_custom_sql(self, sqlquery, headers=None, db_alias=None):
        ''' Execute a cutomized sql query and return results into a list of dictionary.
        Input
            sqlquery, a customized sql query, such as,

                sqlquery = "SELECT C.id as id, " 
                sqlquery += " F.arraycode as arraycode, "
                sqlquery += " A.striporder as striporder, "
                sqlquery += " B.stripcode as stripcode, "
                sqlquery += " C.tubeindex as tubeindex, "
                sqlquery += " E.tubecode as cellcode, "
                sqlquery += " D.numberofcells as numberofcells, "
                sqlquery += " D.id as cell_id, "
                sqlquery += " A.wga_array_id as wga_array_id, "
                sqlquery += " D.notes as notes "
                sqlquery += "FROM data_wga_arraystrip A "
                sqlquery += "left join data_wga_strip B on A.wga_strip_id=B.id "
                sqlquery += "left join data_wga_stripcell C on C.wga_strip_id=B.id  "
                sqlquery += "left join data_wga_cell D on C.wga_cell_id=D.id  "
                sqlquery += "left join data_wga_tube E on D.wga_tube_id=E.id  "
                sqlquery += "left join data_wga_array F on A.wga_array_id=F.id  "
                sqlquery += "where A.wga_array_id=" + str(wga_array_id)
                sqlquery += " order by A.striporder;"
            
            headers, a list of headers for each of columns, such as
                    headers=['id','arraycode','striporder',...]
                which is the list of field names used in the sqlquery.
                
            db_alias=None, use the default database. Otherwise, use the specific database defined
                in local_settings.py. For more detail, refer to https://docs.djangoproject.com/en/dev/topics/db/multi-db/.
                
                For example, db_alias="seek_dmac"
            
    
        Output
            Returns a list of records, each of which is a dictionary in the following format,
                [
                    {'id':1, 'field1': aaa,...},
                    ...
                    {'id':15, 'field1': a15,...}
                ]
        '''
        #print "okay", sqlquery
        if db_alias is None:
            cursor = self.cursor
        else:
            cursor = connections[db_alias].cursor()
        
        cursor.execute(sqlquery)
        objs = cursor.fetchall()
        #for obj in objs:
        #    print obj
        
        # Usage
        rowslist = list(objs)
        rowi = 0
        diclist = []
        for listi in rowslist:
            if rowi==0:
                nlen = len(listi)
                if headers==None:
                    headers = []
                    for i in range(nlen):
                        headers.append(str(i))
                else:
                    if nlen<len(headers):
                        print "Error: Dimension of headers not match!"
                        return diclist
            
            dici = {}
            for coli, header in enumerate(headers):
                dici[header] = listi[coli]
 
            diclist.append(dici)
        return diclist
        # the following will not work because objs are not objects from Django model. 
        # return self.__objsToDicList(objs)
    
        # return such as: ((54360982L, None), (54360880L, None))
        #return cursor.fetchall()
    
        # return a list of dictionaries, such as: [{'parent_id': None, 'id': 54360982L}, {'parent_id': None, 'id': 54360880L}]
        #return self.dictfetchall()
        
    def retrieveRecords(self, tablemodel, field, keyword):
        ''' Usage,
    
            from django.db.models import Q
            qset = (
                Q(defline__icontains=keywords) | Q(locus_tag__icontains=keywords) | Q(gb_tag__icontains=keywords)     |Q(gene_name__icontains=keywords) | Q(xrefs__xref__icontains=keywords) 
            )
            mylist = Protein.objects.filter(qset).distinct().order_by('id')[:2000] # report up to 2000 proteins
    
            where,
                table = Protein
                distinct = True
                orderby = 'id'
                limit = ':2000'
                
            objdiclist = [objdic1, objdic2...]
            objdic1={field1:value1, field2:value2,...}
        '''
        query = {}
        if is_numeric(keyword):
            query['%s__exact'%field] = keyword
        else:
            # Case-sensitive
            #query['%s__contains'%field] = keyword
            # Case-insensitive 
            query['%s__icontains'%field] = keyword
            
            
        objs = tablemodel.objects.filter(**query)
        #print('retrieveRecords: ', len(objs))
        
        return self.__objsToDicList(objs)
    
    def updateStringsAdditive(self, tablemodel, field_known, value_known, field_change, string_added):
        ''' Based on the known filter, batch update a field value by adding a value to exist value.
        Input,
            tablemodel, a Django DB table model, such as Wga_tube;
            field_known, the field name used for searching records, such as wga_patient_id in Wga_tube table;
            value_known, the know value for the filed known, such as wga_patient_id=2;
            field_change, the field name that will be changed, such as "notes" in Wga_tube table. This is usually a string field.
            string_added, the string that will be added to the existing string for field_known, such as
                    notes=current_notes + ";" + value_added, where current_notes is the current value in DB for field_change.
        Usage
            updateValuesAdditive(Wga_tube, "wga_patient_id", 2, "notes", "Merged from patient xxx")
        '''
        self.__updateStringValuesAdditive(tablemodel, field_known, value_known, field_change, string_added)

    def retrieveNumberOfRecords(self, tablename):
        ''' Modified from retrieveTotalRecords(tablename) in dbjango.py.
            Returns the total number of records in a table.
            Input
                tablename, the actual database table name (not the table model in Django).
            
            Output
                The total number of records in the table.
                
                
            total = tablemodel.objects.all().count()
        '''
        sqlquery = "select count(*) as total from " + tablename + ";"
        # such as 
        #   rows = [{'total': 686L}]
        rows = self.retrieve_custom_sql(sqlquery)
        total = rows[0]['total']
        return total

    def retrieveTotalRecords(self, tablemodel, qset=None):
        ''' Returns the total number of records in a table.
            Input
                tablemodel, the Django table model name such as Wga_cell etc.
            
            Output
                The total number of records in the table.
                
                
            total = tablemodel.objects.all().count()
        '''
        if qset is None:
            total = tablemodel.objects.all().count()
        else:
            total = tablemodel.objects.filter(qset).count()
        return total

    def retrieveValuesDictionary(self, tablemodel, filter):
        ''' Refer to: http://stackoverflow.com/questions/31878137/django-one-to-one-relation-queryset
            The result is a <class 'django.db.models.query.ValuesQuerySet'>,
            which is essentially a list of dictionaries with key as the field name and value as the actual value.
            For example, 
                result = B.objects.filter(a__id=1).values('a__id', 'a__name', 'a__age', 'salary')

                qset = (
                Q(firstName__icontains=firstName) & Q(lastName__icontains=lastName) 
            )
            or
            qset = (
                Q(a__id=1) 
            )
                
            result = B.objects.filter(qset).values('a__id', 'a__name', 'a__age', 'salary')
        '''
        objsdic = tablemodel.objects.filter(filter).values()
        
        return objsdic

    def retrieveValuesList(self, tablemodel, filter):
        ''' Refer to: http://stackoverflow.com/questions/31878137/django-one-to-one-relation-queryset
            The result is a <class 'django.db.models.query.ValuesListQuerySet'>,
            and it's essentially a list of tuples.
            For example, 
                result = B.objects.filter(a__id=1).values_list('a__id', 'a__name', 'a__age', 'salary')
        '''
        objslist = tablemodel.objects.filter(filter).values_list()
        
        return objslist
    
    def retrieveJointQuery(self, tablemodel_parent, tablemodel_child, filter):
        ''' Refer to: How to do this join query in Django
            Run a joint query on two tables.
            For example,
                class Parent(models.Model):
                    name = models.CharField(max_length=40)
                    important_info = models.CharField(max_length=40)

                class Child(models.Model):
                    parent_key = models.OneToOneField(Parent)
                    extra_info = models.CharField(max_length=40)
            
            The joint query is
                
                parents = Parent.objects.filter([...]).select_related('Child')
            
            This will produce one query that fetches product ranks using a join:
                
                SELECT
                    "Parent"."id",
                    "Parent"."name",
                    "Parent"."important_info",
                    "Child"."extra_info"
                FROM "Parent"
                INNER JOIN "Child"
                ON ("Child"."parent_id" = "Parent"."id")            
        
            Input
                tablemodel_parent, such as Parent
                tablemodel_child, such as Child
                filter
        '''
        print "retrieveJointQuery"
        #objs = tablemodel_parent.objects.filter(filter).select_related(tablemodel_child)
        
    def retrieveJoint(self, tablemodel, joint_tablemodels_string, qset, orderby, limit):
        ''' Input
                tablemodel, the Django table model name such as Wga_cell etc.
                joint_tablemodels-string, such as "wga_cell_status", which is a one-to-one model to Wga_cell model.
                    In the join query above, the joint table name can't be  "Wga_cell_status" or Wga_cell_status
                    but must be "wga_cell_status", where the first character is in small case. 
                orderby, a SQL query string in the format of "ORDER BY keyword DESC" or "ORDER BY keyword ASC"
                limit, a SQL query string in the format of " LIMIT offset,rows",
                    where offset is the starting number and rows is the total number of records returned. 
                    The relationship between (startNo, endNo) and limit is,
                        offset = startNo
                        rows = endNo - startNo + 1
                        limit = " LIMIT offset,rows" = " LIMIT " + str(offset) + "," + str(rows)
  
                Both orderby and limit strings are usually created from querySuffix() in datagrid.py,
                which processes the call from an EasyUI dataGrid from the front html page.
                
                qset = Q()
                qset = Q(cell_status__xind_e__in=[1])|Q(cell_status__xind_qqn__in=[1])
                qset = (
                    Q(firstName__icontains=firstName) & Q(lastName__icontains=lastName) 
                )
                or
                qset = (
                    Q(a__id=1) 
                )
        '''
        #print "retrieveJoint"
        if qset is None:
            qset = Q()
        
        # example: limit = " LIMIT offset,rows"
        strs1 = limit.strip().split(' ')        # such as strs1=["LIMIT", "offset,rows"]
        #print strs1
        offset = 0
        #rows = tablemodel.objects.all().count()
        rows = 0
        if len(strs1)>1:
            strs2 = strs1[1].split(',')         # such as strs2=["offset", "rows"]
            if len(strs2)>1:
                offset = int(strs2[0])
                rows = int(strs2[1])
        
        #print "OFFSET: ", offset, "ROWS: ", rows
        
        startNo = offset
        endNo = offset + rows
        
        # example: "ORDER BY keyword DESC"
        strs3 = orderby.strip().split(' ')      # such as strs3=["ORDER", "BY", keyword, "DESC"]
        keyword = ' '
        if len(strs3)>2:
            keyword = strs3[2]
        
        order = 'ASC'                           # default order
        if len(strs3)>3:
            order = strs3[3]                    # such as order="DESC"
            
        #print keyword, order
        if order.upper()=='ASC':
            orderby_keyword = keyword
        elif order.upper()=='DESC':
            orderby_keyword = "-" + keyword
        else:
            orderby_keyword = keyword
            
        #print "ORDER BY: ", orderby_keyword
        
        # some examples of using "LIMIT offset,rows" in Django
        
        # This will only join any child table/model specified.
        # For example, Wga_cell.objects.select_related('wga_cell_status').order_by(orderby_keyword)[offset:rows] will
        # do a LEFT OUTER JOIN with Wga_cell_status table/modle.
        #objs = tablemodel.objects.select_related(joint_tablemodels_string).order_by(orderby_keyword)[offset:rows]
        #objs = tablemodel.objects.select_related(joint_tablemodels_string).order_by(orderby_keyword)[startNo:endNo]
        #qset = Q(cell_status__xind_e__in=[1])|Q(cell_status__xind_qqn__in=[1])
        if len(joint_tablemodels_string)==0:
            if rows==0:
                if len(orderby_keyword)<2:
                #print "A: ", qset
                    objs = tablemodel.objects.filter(qset)
                else:
                    #print len(orderby_keyword)
                    #print "B: ", qset
                    objs = tablemodel.objects.filter(qset).order_by(orderby_keyword)
            else:
                if len(orderby_keyword)<2:
                    #print "A: ", qset
                    objs = tablemodel.objects.filter(qset)[startNo:endNo]
                else:
                    #print len(orderby_keyword)
                    #print "B: ", qset
                    objs = tablemodel.objects.filter(qset).order_by(orderby_keyword)[startNo:endNo]

            #print objs.query
            #print "retrieveJoint: objs retrieved: ", len(objs)
            return self.__objsToDicList(objs)
        else:
            if rows==0:
                if len(orderby_keyword)<2:
                #print "A: ", qset
                    objs = tablemodel.objects.select_related(joint_tablemodels_string).filter(qset)
                else:
                    #print len(orderby_keyword)
                    #print "B: ", qset
                    objs = tablemodel.objects.select_related(joint_tablemodels_string).filter(qset).order_by(orderby_keyword)
            else:
                if len(orderby_keyword)<2:
                    #print "A: ", qset
                    objs = tablemodel.objects.select_related(joint_tablemodels_string).filter(qset)[startNo:endNo]
                else:
                    #print len(orderby_keyword)
                    #print "B: ", qset
                    objs = tablemodel.objects.select_related(joint_tablemodels_string).filter(qset).order_by(orderby_keyword)[startNo:endNo]
        
            #print objs.query
            #print "retrieveJoint: objs retrieved: ", len(objs)
            return self.__objsToDicList_joint(objs)
        
        # this will join all parent tables
        # For example, Wga_cell.objects.select_related().order_by(orderby_keyword)[offset:rows] will do INNER JOIN
        # with two parent models: Wga_tube and Wga_patient models automatically. 
        # objs = tablemodel.objects.select_related().order_by(orderby_keyword)[offset:rows]
        #print objs.query
        #print objs
        #print "retrieveJoint: objs retrieved: ", len(objs)
        # objs = tablemodel.objects.all()[offset:limit]
        
        # some examples of using "ORDER BY keyword DESC" in Django
        # objs = tablemodel.objects.all().filter(client=client_id).order_by('check_in')               ASC order by default  
        # objs = tablemodel.objects.all().filter(client=client_id).order_by('check_in').reverse()     DESC order
        # objs = tablemodel.objects.all().filter(client=client_id).order_by('check_in')[::-1]         DESC order
        # objs = tablemodel.objects.all().filter(client=client_id).order_by('-check_in')              DESC order
        
        #objs = self.__queryFiltering(tablemodel, qset, False, orderby_keyword, offset, rows)
        #print objs
        #return objs
        
        # return a list of dictionaries.
        return self.__objsToDicList(objs)
        
        
        
    def __queryFiltering(self, tablemodel, qset, distinct, orderby_keyword, offset, rows):
        ''' Usage,
    
            from django.db.models import Q
            qset = (
                Q(defline__icontains=keywords) | Q(locus_tag__icontains=keywords) | Q(gb_tag__icontains=keywords)     |Q(gene_name__icontains=keywords) | Q(xrefs__xref__icontains=keywords) 
            )
            mylist = Protein.objects.filter(qset).distinct().order_by('id')[:2000] # report up to 2000 proteins
    
            where,
                table = Protein
                distinct = True
                keyword = 'id'
                limit = ':2000', where offset = 0, rows = 2000
        '''
        #print "__queryFiltering"
        #print orderby_keyword, offset, rows
        if rows>0:
            if distinct:
                if len(orderby_keyword)>0:
                    mylist = tablemodel.objects.filter(qset).distinct().order_by(orderby_keyword)[offset:rows]
                else:
                    mylist = tablemodel.objects.filter(qset).distinct()[offset:rows]
            else:
                if len(orderby_keyword)>0:
                    mylist = tablemodel.objects.filter(qset).order_by(orderby_keyword)[offset:rows]
                else:
                    mylist = tablemodel.objects.filter(qset)[offset:rows]
        else:
            if distinct:
                if len(orderby_keyword)>0:
                    mylist = tablemodel.objects.filter(qset).distinct().order_by(orderby_keyword)
                else:
                    mylist = tablemodel.objects.filter(qset).distinct()
            else:
                if len(orderby_keyword)>0:
                    mylist = tablemodel.objects.filter(qset).order_by(orderby_keyword)
                else:
                    mylist = tablemodel.objects.filter(qset)
    
        #mylist = [x for x in mylist if x.numberrepeats()<5]
        return mylist

    def __queryRecords(self, tablemodel, field, keyword):
        ''' Usage,
    
            from django.db.models import Q
            qset = (
                Q(defline__icontains=keywords) | Q(locus_tag__icontains=keywords) | Q(gb_tag__icontains=keywords)     |Q(gene_name__icontains=keywords) | Q(xrefs__xref__icontains=keywords) 
            )
            mylist = Protein.objects.filter(qset).distinct().order_by('id')[:2000] # report up to 2000 proteins
    
            where,
                table = Protein
                distinct = True
                orderby = 'id'
                limit = ':2000'
        '''
        query = {}
        query['%s__contains'%field] = keyword
        #query['%s__exact'%field] = keyword
        objs = tablemodel.objects.filter(**query)
        return objs
    

    def __updateStringValuesAdditive(self, tablemodel, field_known, value_known, field_change, string_added):
        ''' Based on the known filter, batch update a field value by adding a value to exist value.
        Input,
            tablemodel, a Django DB table model, such as Wga_tube;
            field_known, the field name used for searching records, such as wga_patient_id in Wga_tube table;
            value_known, the know value for the filed known, such as wga_patient_id=2;
            field_change, the field name that will be changed, such as "notes" in Wga_tube table. This is usually a string field.
            string_added, the string that will be added to the existing string for field_known, such as
                notes=current_notes + ";" + value_added, where current_notes is the current value in DB for field_change.
        Usage
            updateValuesAdditive(Wga_tube, "wga_patient_id", 2, "notes", "Merged from patient xxx")
        '''
        #print "__updateStringValuesAdditive"
        if field_known is None:
            return
        
        field_known = field_known.strip()
        if len(field_known)==0 or field_known=="NA":
            return
        
        if value_known is None:
            return
        
        query = {}
        if is_numeric(value_known):
            query['%s__exact'%field_known] = value_known
        else:
            query['%s__contains'%field_known] = value_known
        
        objs = tablemodel.objects.filter(**query)
        #print "retrieve records"
        for obj in objs:
            for f in obj._meta.fields:
                name = f.name
                #print name
                if name==field_change:
                    #print 'f.name ', name
                    #value = unicode(getattr(o,f.name))
                    try:
                        string_old = getattr(obj,f.name)
                    except AttributeError:
                        string_old = None
                        
                    #print string_old
                    string_new = self.__mergeStringsAdditive(string_old, string_added)
                    #print string_new
                    setattr(obj, f.name, string_new)
                    obj.save()
                
                
    def __mergeStringsAdditive(self, string1, string2):
        ''' Given two strings, merge them in a proper way.
            Input
                string1, the first string, which is usually the current string in a table
                string2, the second string, which is usually a new string that will be added into the current string. 
            Output
                newString = string1 + ";" + string2
            
            Usage
                Used by dbdjango, etc
        '''
        #print "__mergeStringsAdditive"
        #print string1, string2
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
                #elif string1 in string2:
                #    newstring = string2
                else:
                    newstring = string1 + ";" + stringIn
        #print newstring
        return newstring    
    
    def deleteRocords(self, tablemodel, primarykeys):
        ''' Given
                tablemodel, the table model such as WGA_cell or data_wga_cell,
                primarykeys, a list of primary keys in this table.
        
            Output
                delete records with primark keys provided.
                
        '''
        number = 0
        try:
            objs = tablemodel.objects.filter(pk__in=primarykeys)
            #print objs
            number = len(objs)
            #print "number: ", number
            objs.delete()
        except IntegrityError:
            number = 0
        
        return number
        
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
        objs = tablemodel.objects.all()
        idsdic = {}
        if objs is None:
            return idsdic
        
        try:
            n = len(objs)
        except:
            n = -1
        
        if n<=0:
            print "retrieveIDsUniqueField: no object retrieved, ", uniqueField, n
            return idsdic
        
        diclist = self.__objsToDicList(objs)
        for dici in diclist:
            if uniqueField in dici:
                fieldvalue = dici[uniqueField]
                id = dici["id"]
                idsdic[fieldvalue] = id
        return idsdic
        
    def getRecords(self, tablemodel, datadic):
        ''' Retrieve records based on the specification in a dictionary.
        Input
            tablemodel, the DB table model;
            datadic, a dictionary, {"field1":value1, "field2":value2,...},
        Output
            a dictionary of the query set.
        Notes
            The funnction retrieveRecords(tablemodel, field, keyword) retrieves records based on keyword for just one field,
            while getRecords(tablemodel, datadic) retrieves records based on a dictionary with mulitple field values.
            It is useful when we want to find a primary key for a constraint with more than one variables. 
        Implementation
            Refer to https://stackoverflow.com/questions/16018497/django-filter-model-by-dictionary
        
        '''
        #return self.__dbconn.getRecords(tablemodel, datadic)
        #print "getRecords"
   
        objs = tablemodel.objects.filter(**datadic)
        return self.__objsToDicList(objs)
        
    def getDistinctList(self, tablemodel, fieldname):
        ''' Refer to: https://stackoverflow.com/questions/10848809/django-model-get-distinct-value-list
        Get a distinct list, for example,
            Entity.objects.order_by('foreign_key').values('foreign_key').distinct()
            
        Input
            tablemodel, the DB table model;
            fieldname, the field name used for searching records.
        '''
        dlist = []
        objs = tablemodel.objects.order_by(fieldname).values(fieldname).distinct()
        for obj in objs:
            #print obj
            term = obj[fieldname]
            dlist.append(term)
            #print term
        return dlist
            
            
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
            
        Now we generate the query set by using the same idea above.
        
        Input
            filterRules, such as [{"field":"unit","op":"contains","value":"Amon"}]
        
        Output
        
            queryset, such as 
        '''
        print "generateQuerySet"
        qset = Q()
        n = 0
        for rule in filterRules:
            print rule
            field = rule["field"]
            keyword = rule["value"]
            op = rule["op"]
            
            query = {}
            if op=="contains":
                # Case-sensitive
                #query['%s__contains'%field] = keyword
                # Case-insensitive 
                query['%s__icontains'%field] = keyword
            else:
                if is_numeric(keyword):
                    query['%s__exact'%field] = keyword
                else:
                    query['%s__icontains'%field] = keyword
            
            if n==0:
                qset = Q(**query)
            else:
                qset = qset & Q(**query)
            n += 1
            
        return qset
        
    def insertOneRecord(self, tablemodel, record):
        return self.__insertOneRecord(tablemodel, record)
        
    def __updateValue(self, value_fromDB, value_input):
        ''' Create a value that combines the information from DB and input,
            and that will be used to update the value in DB.
        Input
            value_fromDB, value retrieved from database.
            value_input, value provided from input.
        Output
            value_forUpdate, record used for updating the database.
        
        Ruls of thumb:
            The data input will overwrite the data in DB.
        '''
        value_forUpdate = value_input
        if value_input is None:
            value_forUpdate = value_fromDB
        
        return value_forUpdate
        
    def __updateRecord(self, record_fromDB, record_input):
        ''' Create a record that combines the information from DB and input,
            and that will be used to update the info in DB.
        Input
            record_fromDB, record retrieved from database.
            record_input, record provided from input.
        Output
            record_forUpdate, record used for updating the database.
        
        Ruls of thumb:
            The data input will overwrite the data in DB.
        '''
        record_forUpdate = record_fromDB
        for k, v in record_input.iteritems():
            if k in record_forUpdate:
                v_old = record_forUpdate[k]
                if v!=v_old:
                    print(k, v, v_old)
                record_forUpdate[k] = self.__updateValue(v_old, v)
                
        return record_forUpdate
        
    def __updateOneToOneRecord(self, tablemodel, record, primarykeyname):
        ''' Input
                tablemodel, the table model defined in models.py
                record = {"field1":value1, "field2":value2, ...}
                primarykeyname, the one-to-one key in the One-to-One table, such as cell_id
                
            Requirement
                In running this subroutine, the none-null values must be provided in record.
                Otherwise, tb.save() would not work and returns no value. 
        '''
        msg = "Run SQL transaction "
        
        # id required
        if primarykeyname not in record:
            msg = "__updateOneRecord error: no primary key in record for update."
            return -1, msg
        
        status = 1
        sid = transaction.savepoint()
        try:
            # In worst case scenario, this might fail too
            #tb = tablemodel(**record)
            #tb.save()
            pid = record[primarykeyname]
            #record_old = self.retrieveOneRecord(tablemodel, id)
            obj = self.retrieveUniqueObj(tablemodel, primarykeyname, pid)
            
            #query['%s='%primarykeyname] = pid
            #obj = tablemodel.objects.get(query)
            obj = tablemodel.objects.get(person_id=7)
            #print "ooooojb ", obj
            for k, v in record.iteritems():
                #print k,v
                setattr(obj, k, v)
            #print "now save", obj.last_name
            
            ###################### the following line throws an error, to be fixed ************
            obj.save()
            #######################################################################
            #print "after save"
            
            transaction.savepoint_commit(sid)
            msg += " successfully"
            status = 1
        except IntegrityError:
            transaction.savepoint_rollback(sid)
            msg += " failed."
            status = 0
            
        #print msg
        msg = ""
        return msg, status      
            
    def storeOneToOneRecord(self, tablemodel, record, primarykeyname):
        ''' Input
                tablemodel, the table model defined in models.py
                record = {"field1":value1, "field2":value2, ...}
                primarykeyname, the one-to-one key in the One-to-One table, such as cell_id
                
            Output
                id, msg, where
                    id is the primary key, or -1 if any error
                    msg is any message
        '''

        if primarykeyname not in record:
            msg = "Not right format for storing record"
            return -1, msg
        
        msg, status = self.__updateOneToOneRecord(tablemodel, record, primarykeyname)
        return status, msg
    
    def __objsToDicList_joint(self, objs):
        ''' Convert Django objs to a dictionary.
        
        Input
            objs, result set from Django query.
            
        Output
            objlist, =[dic1, dic2, ..., dicn], where dic={name1:value1, name2:value2,...}
        '''
        objsdiclist = []
        for obj in objs:
            #print obj
            objdic = self.__objToDic_joint(obj)
            objsdiclist.append(objdic)
            
        #print objsdiclist[0]
        #print "obj.x_e: ", obj.x_e
        return objsdiclist
    
    def retrieveUniqueObj(self, tablemodel, field, keyword):
        ''' Usage,
    
            from django.db.models import Q
            qset = (
                Q(defline__icontains=keywords) | Q(locus_tag__icontains=keywords) | Q(gb_tag__icontains=keywords)     |Q(gene_name__icontains=keywords) | Q(xrefs__xref__icontains=keywords) 
            )
            mylist = Protein.objects.filter(qset).distinct().order_by('id')[:2000] # report up to 2000 proteins
    
            where,
                table = Protein
                distinct = True
                orderby = 'id'
                limit = ':2000'
                
            objdiclist = [objdic1, objdic2...]
            objdic1={field1:value1, field2:value2,...}
        '''
        query = {}
        if is_numeric(keyword):
            query['%s__exact'%field] = keyword
        else:
            # Case-sensitive
            #query['%s__contains'%field] = keyword
            # Case-insensitive 
            query['%s__icontains'%field] = keyword
            
            
        objs = tablemodel.objects.filter(**query)
        #print "objs: ", objs
        total = objs.count()
        #print total
        if total==1:
            # already exist
            obj = objs[0]
        else:
            #not defined or duplicated id
            obj = None
        return obj
            
    def retrieveUniqueRecord(self, tablemodel, field, keyword):
        ''' Usage,
    
            from django.db.models import Q
            qset = (
                Q(defline__icontains=keywords) | Q(locus_tag__icontains=keywords) | Q(gb_tag__icontains=keywords)     |Q(gene_name__icontains=keywords) | Q(xrefs__xref__icontains=keywords) 
            )
            mylist = Protein.objects.filter(qset).distinct().order_by('id')[:2000] # report up to 2000 proteins
    
            where,
                table = Protein
                distinct = True
                orderby = 'id'
                limit = ':2000'
                
            objdiclist = [objdic1, objdic2...]
            objdic1={field1:value1, field2:value2,...}
        '''
        obj = self.retrieveUniqueObj(tablemodel, field, keyword)
        #return obj
        return self.__objToDic(obj)
        
        
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
        #print('getOptions')
        objs = tablemodel.objects.all()
        diclist = self.__objsToDicList(objs)
        
        # the followinng format is for a Django form choiceField
        # queryset = tablemodel.objects.all()
        # options = [ (qi.id, qi.title) for qi in queryset]
    
        # the following format is for an easyUI comboBox
        options = []
        selected = False
        for dici in diclist:
            value = dici[valueField]
            option = {}
            option[valueField] = value
            option[textField] = dici[textField]
            if str(value)==str(valueSelected):
                option['selected'] = True
                selected = True
                
            options.append(option)
        
        # if the value selected is not on the list from DB,
        # such as id=0, which is a primary key noot available in DB table,  
        # add a default option for such value, such as set the text as '' 
        if not selected:
            # the option selected, such as id=0, is not available in DB table
            # add an option with '' and set it as the one selected
            option = {}
            option[valueField] = valueSelected
            option[textField] = ''
            option['selected'] = True
            
            options = [option] + options
            
        return simplejson.dumps(options)
        
    def retrieveConstraintRecords(self, tablemodel, constraint):
        ''' Retrieve all records, given
        Input
            tablemodel, the full name of the table, such as [dbname].[dbo].[tablename]
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
        #print constraint
        
        return self.getRecords(tablemodel, constraint)
        
        qset = Q()
        n = 0
        for key, value in constraint.items():
            query = {}
            if is_numeric(value):
                query['%s__exact'%key] = value
            else:
                # Case-sensitive
                #query['%s__contains'%key] = value
                # Case-insensitive 
                query['%s__icontains'%key] = value
            
            if n==0:
                qset = Q(**query)
            else:
                qset = qset & Q(**query)
            n += 1
            
        objs = tablemodel.objects.filter(qset)
        return self.__objsToDicList(objs)
        
    def retrieveContainedRecords(self, tablemodel, constraint):
        ''' Retrieve all records, given
        Input
            tablemodel, the full name of the table, such as [dbname].[dbo].[tablename]
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
        qset = Q()
        n = 0
        for key, value in constraint.items():
            query = {}
            if is_numeric(value):
                query['%s__exact'%key] = value
            else:
                # Case-sensitive
                #query['%s__contains'%key] = value
                # Case-insensitive 
                query['%s__icontains'%key] = value
            
            if n==0:
                qset = Q(**query)
            else:
                qset = qset & Q(**query)
            n += 1
            
        objs = tablemodel.objects.filter(qset)
        return self.__objsToDicList(objs)
        
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
        print "retrieve_table_list"
        orderby = filtersdic['orderby'] # such as " ORDER BY id asc " or " ";
        startNo = filtersdic['startNo'] # such as 1000;
        endNo = filtersdic['endNo']     # such as 1050;
        limit = filtersdic['limit']
        
        filterRules = filtersdic['filterRules']
        qset = self.generateQuerySet(filterRules)
        
        joint_tablemodels_string = ''
        dicList = self.retrieveJoint(tablename, joint_tablemodels_string, qset, orderby, limit)
        
        qset = Q()
        limit = ' '
        dicList_total = self.retrieveJoint(tablename, joint_tablemodels_string, qset, orderby, limit)
        total = len(dicList_total)
        
        #footer = [{"ProjectTC": "Total","AnnualProjectDC": totalADC}]
        footer = []
        return dicList, footer, total
            
    def getQueryValue(self, sqlquery, db_alias=None):
        ''' Run a query to get a value or None.
        Input
            sqlquery, a SQL query for a numberic value, such as
                "select count(id) from table"
                "select volumn from table"
                "select id from table where connnstraint"
        '''
        
        if db_alias is None:
            cursor = self.cursor.execute(sqlquery)
        else:
            cursor = connections[db_alias].cursor()
        
        cursor.execute(sqlquery)
        objs = cursor.fetchall()
        if objs is None:
            value = None
        elif len(objs)==1:
            values = objs[0]
            value = values[0]
            print('objs[0]', value)
        else:
            value = None
        return value    
        
        
    def run_custom_transaction(self, sqlqueries, db_alias=None):
        ''' Execute a cutomized sql query and return results into a list of dictionary.
        Input
            sqlqueries a list of SQL queries, such as,
                [
                    "delete from table1 where id=1",
                    "delete from table2 where id=1",
                    "delete from table3 where id=1",
                    "delete from table4 where id=1",
                    "delete from table5 where id=1"
                ]
                
            db_alias=None, use the default database. Otherwise, use the specific database defined
                in local_settings.py. For more detail, refer to https://docs.djangoproject.com/en/dev/topics/db/multi-db/.
                
                For example, db_alias="seek_dmac"
            
    
        Output
            Returns a list of records, each of which is a dictionary in the following format,
                [
                    {'id':1, 'field1': aaa,...},
                    ...
                    {'id':15, 'field1': a15,...}
                ]
        '''
        #print "okay", sqlquery
        if db_alias is None:
            con = self.conn
        else:
            con = connections[db_alias]
        cur = con.cursor()
        
        sid = transaction.savepoint()
        
        sqlquery = "START TRANSACTION;"
        cur.execute(sqlquery)
        
        try:
            for sqlquery in sqlqueries:
                cur.execute(sqlquery)
    
            sqlquery = "COMMIT;"
            cur.execute(sqlquery)
            transaction.savepoint_commit(sid)
            con.commit()
        #except mdb.MySQLError, e:
        except MySQLdb.Error, e:
            #if con:
            sqlquery = "ROLLBACK;"
            cur.execute(sqlquery)
            transaction.savepoint_rollback(sid)
            con.rollback()
        
            print "Error %d: %s" % (e.args[0],e.args[1])
            return 0
        except:
            #if con:
            sqlquery = "ROLLBACK;"
            cur.execute(sqlquery)
            transaction.savepoint_rollback(sid)
            con.rollback()
            return 0
    
        #finally:    
        #    if con:    
        #        con.close()
        return 1
    
        # the following will not work because objs are not objects from Django model. 
        # return self.__objsToDicList(objs)
    
        # return such as: ((54360982L, None), (54360880L, None))
        #return cursor.fetchall()
    
        # return a list of dictionaries, such as: [{'parent_id': None, 'id': 54360982L}, {'parent_id': None, 'id': 54360880L}]
        #return self.dictfetchall()
        
    def queryRecordsCustom(self, tablemodel, qset):
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
        '''
        objs = tablemodel.objects.filter(qset)
        return self.__objsToDicList(objs)