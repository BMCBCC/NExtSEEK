from django.shortcuts import render
from django.shortcuts import redirect
from django.http import HttpResponseRedirect, HttpResponse

import csv
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
import tempfile
#import magic
import random

#from urllib.parse import urlparse
from subprocess import call
from subprocess import check_call
from time import strftime, gmtime

#from bioblend.galaxy import GalaxyInstance
#from bioblend.galaxy.client import ConnectionError
from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render_to_response, render, HttpResponseRedirect, redirect, HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from pathlib import Path
from itertools import groupby
from datetime import datetime, timedelta
from pytz import timezone

from django.contrib.auth.models import User
from django import forms
from django.conf import settings

import simplejson
import datetime
import json
import zipfile

from dmac.conversion import dateconversion, dateToString, dateToStringUK, convertDicToOptions, handle_uploaded_file
from dmac.datagrid_custom import DataGrid
from dmac.csv_excel import load_file, load_excelfile
from dmac.iocsv import saveCsvfile

from .seekdb import SeekDB
from .nextcloudapi import NextCloudAPI
from .galaxyapi import GalaxyAPI
from .seekapi import SeekAPI

from .dbtable_sampletype import DBtable_sampletype
from .dbtable_sample import DBtable_sample
from .dbtable_documents import DBtable_documents
from .dbtable_data_files import DBtable_data_files
from .dbtable_sops import DBtable_sops
from .dbtable_sampleattribute import DBtable_sampleattribute
from .dbtable_attributetype import DBtable_attributetype


from subprocess import call

import shlex
from subprocess import Popen, PIPE

from django.conf import settings
# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
# this is usually at "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY  = settings.PROJECT_ROOT + "/static/media/download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + 'download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY
# this is the symbolic link to "project_root/static/media/download/", regardless the theme folder
#DOWNLOAD_DIRECTORY_LINK = '/static/media/download/'

UPLOAD_DIRECTORY = settings.MEDIA_ROOT + "/uploads/"

SEEK_DATAFILE_ROOT = settings.SEEK_DATAFILE_ROOT

DROPBOX_DIRECTORY = settings.MEDIA_ROOT + "/dropbox/"

# the excel file used as the template for publishing samples to FairDomHub
SAMPLE_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/SAMPLE_TEMPLATE.xlsx"

# such as: "https://fairdomhub.org"
PUBLISH_SERVER = settings.PUBLISH_URL

# We always use report to return variables
report = {}
    
def seek(request, url):
    report = {}
    if request.method == 'POST':
        '''
        form = PersonForm(request.POST)
        if form.is_valid():
            #print form.cleaned_data
            try:
                #id = form.data.get('id')
                message = submitForm(form.cleaned_data)
                #return HttpResponse(message)
                return redirect('/sample/sampledb/')
            #except onekpdb.DoesNotExist:
            except:
                message = "form is not valid: " +  form.errors
                #return HttpResponse(message)
                #return redirect('/sample/sampledb/')
                print "form is not valid", form.errors
                return render(request, "person_form.html", {"report" : report, "form": form})
        else:
            print "form is not valid", form.errors
            return render(request, "person_form.html", {"report" : report, "form": form})
        '''
        bodyhtml = "To be implemented"
        return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    else:
        print(url)
        url = "/" + url.replace("-", "/") + "/"
        print(url)
        bodyhtml = getPageRequests(url)
        report = {}
        #report['bodyhtml'] = HttpResponse(bodyhtml)
        report['bodyhtml'] = bodyhtml
        #report['bodytext'] = bodytext
        return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    
def getSeekPage(request, seek_url):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/'
        return HttpResponseRedirect(url_redirect)
        
    bodyhtml = seekdb.getPageRequests(seek_url)
    #return HttpResponse(htmlpage)
    
    report = {}
    #report['bodyhtml'] = HttpResponse(bodyhtml)
    report['bodyhtml'] = bodyhtml
    #report['bodytext'] = bodytext
    return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    
def sample(request, id):
    """
    rdirect to "/samples/id/"
    """
    sample_id = id
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        if sample_id==0:
            url_redirect = '/login/?next=/seek/samples/query/'
        else:
            url_redirect = '/login/?next=/seek/sample/id=' + str(sample_id) + '/'
        return HttpResponseRedirect(url_redirect)
    
    #r = requests.get('https://api.github.com/user', auth=('user', 'pass'))
    
    #print(webpage)
    
    seek_url = "/samples/" + str(id) + "/"
    #print(seek_url)
    #seekapi = SeekAPI(user_seek['server'], user_seek['username'], user_seek['password'])
    bodyhtml = seekdb.getPageRequests(seek_url)
    #return HttpResponse(htmlpage)
    
    report = {}
    #report['bodyhtml'] = HttpResponse(bodyhtml)
    report['bodyhtml'] = bodyhtml
    
    report['sample_id'] = sample_id
    
    dbsample = DBtable_sample()
    
    # these two trees must be shown in sampleTree.embed.html
    #report['treeData_parents'] = dbsample.createSampleTree(sample_id)
    #report['treeData_children'] = dbsample.createSampleChildrenTree(sample_id)
    '''
    udate = str(datetime.datetime.now().strftime("%Y%m%d"))
    lab = dbsample.getLabAbbreviation(user_seek)
    uidprefix = udate[2:] + '-' + lab
    print('uidprefix:', uidprefix)
    
    uidprefix2 = "D.MSP-20200225"
    
    nextIndex = str(dbsample.getSampleUIDIndex(uidprefix2))
    print('nextIndex:', nextIndex)
    
    ffuid = uidprefix + '-' + nextIndex
    print('ffuid:', ffuid)
    '''
    # this tree must be shown in sampleTree2.embed.html
    report['treeData_multiparents'] = dbsample.createSampleMultiParentTree(sample_id)
    
    sampledic, samplelist = dbsample.getSampleInfo(sample_id)
    
    report['sampledic'] = sampledic
    report['sampleinfo'] = samplelist
    
    #report['bodytext'] = bodytext
    return render(request,"samples.html", {'bodyhtml' : bodyhtml, 'report':report})

def sampleTree(request, uid):
    ''' Retrieve sample tree by its uid.
    '''
    sample_uid = uid
    dbsample = DBtable_sample()
    sample_id = dbsample.getSampleID(sample_uid)
    return sample(request, sample_id)
    


def document(request, id):
    """ Get the url for downloading the document with id.
    rdirect to "/seek/document/id=3/", seek "documents/3/"
    """
    document_id = id
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print('document:', user_seek)
    
    if not user_seek['status']:
        err = user_seek['err']
        print(err)
        #url_redirect = "/login/?next=/seek/document/id=" + str(document_id) + "/"
        #return HttpResponseRedirect(url_redirect)
        
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data)) 
    
    #print("userinfo okay")
    seekdoc = DBtable_documents("DEFAULT")
    docurl, filename = seekdoc.getDownloadURL(document_id,
                user_seek['server'],
                user_seek['username'],
                user_seek['password'])
    
    #print(docurl)
    #seek_url = "/documents/" + str(id) + "/"
    if docurl is None:
        msg = 'Sample template is not available. Choose a template from the list.'
        status = 0
        docurl = ''
    else:
        msg = 'Sample template is downloaded in ' + filename
        status = 1
    data = {'msg':msg, 'status': status, 'link':docurl}
    return HttpResponse(simplejson.dumps(data))   

def sampleUpload(request):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    #return sample_type(request, 0)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/samples/upload/")
        
    report = {}
    docs = DBtable_documents()
    report['template_options'] = docs.getOptionsDocuments(0, "Sample Sheet Template")
    return render(request,"sampleUpload.html", {'report':report})
    
def sampleUploadAjax(request):
    ''' Use javascript to upload an excel file for batch-uploading samples
        when the url "/seek/sampleupload/" is selected on samples_upload.embed.html.
    '''
    #print request
    variable = "I received request from /seek/sampleupload/!"
    #print(variable)
    
    #if verifyUser(request)==0:
    #    return HttpResponseRedirect("/accounts/login/?next=/seek/samples/")

    username = str(request.user)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)

    
    #return HttpResponse(variable)
    #print request.user
    #print(request.POST)
    msg = "Error: File not valid"
    message = ''
    status = 0
    data = {'msg':msg, 'status': status, 'link':''}
    if request.method == "POST":
        if request.FILES and request.FILES.get('excelfile_upload'):
            excelfile = request.FILES['excelfile_upload']
            if excelfile:
                #sampletype_id = request.POST.get('sampletype_id')
                #print('sampletype_id:', sampletype_id)
                # no predefined sample type available, use the Instruction sheet to find it out.
                #sampletype_id = 0
                
                inputfile = excelfile.name
                #print(inputfile)
                names = inputfile.split(".")
                n = len(names)
                
                datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                filename = '.'.join(names[:(n-1)]) + '_feedback-' + datenow + '.xls'
                #filename = 'samples_upload_feedback.xls'
                feedbackfile = DOWNLOAD_DIRECTORY + filename
                link = DOWNLOAD_DIRECTORY_LINK + filename
                #print(feedbackfile, link)
                
                sample = DBtable_sample()
                msgi, status = sample.batchUpload(excelfile, feedbackfile, user_seek)
                if status:
                    msg = 'Batch sample uploading successful. To find the UIDs for samples uploaded, refer to the feedback excel file: ' + filename
                    #msg += msgi
                    message = msg + '\n\n' + msgi
                else:
                    message = msgi
                    
                    #msg = 'Batch sample uploading failed. <br/>Refer to the log and the feedback excel file: ' + filename + '.<br/>'
                    terms = msgi.split("<")
                    msg = terms[0] + "<br/><br/>"
                    msg += "Refer to the log and the excel file: " + filename + '.<br/>'
                    
                #    print(msg, status, link)
                data = {'msg':msg, 'status': status, 'link':link}
            else:
                message = 'Error: Not a valid file from client side'
                data = {'msg':message, 'status': 0, 'link':''}
        else:
            message = 'Error: Not a valid file from client side'
            data = {'msg':message, 'status': 0, 'link':''}
    else:
        message = 'Error: Not a valid http POST request'
        data = {'msg':message, 'status': 0, 'link':''}
                
    #message = data['msg']
    if message is not None and '<br/>' in message:
        data['message'] = message.replace('<br/>', '\n')
    else:
        data['message'] = message
                
    return HttpResponse(simplejson.dumps(data))       

        
    
def sampleQuery(request):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    return sample_type(request, 0)
        
def sample_type(request, id):
    """
    rdirect to "/sample_types/id/samples/"
    """
    sampletype_id = int(id)
    print("sampletype_id:", sampletype_id)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        if sampletype_id==0:
            url_redirect = '/login/?next=/seek/samples/query/'
        else:
            url_redirect = '/login/?next=/seek/sample_types/id=' + str(sampletype_id) + '/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    #print report['template_options']
    stype = DBtable_sampletype()
    report['type_options'] = stype.getComboboxOptions(sampletype_id, 'title')
    #print "okay", report['type_options']
    if sampletype_id==0:
        report['showSamplePage'] = True
        report['showSearch'] = True
        report['bodyhtml'] = '<div></div>'
    else:
        report['showSamplePage'] = True
        report['showSearch'] = True
        report['bodyhtml'] = stype.getSamplePage(sampletype_id, user_seek['server'], user_seek['username'], user_seek['password'])
        
    return render(request,"sampleQuery.html", {'bodyhtml' : report['bodyhtml'], 'report':report})
    #return HttpResponse(bodyhtml)
    #data = {'msg':msg, 'status': status, 'bodyhtml':bodyhtml}
    #return HttpResponse(simplejson.dumps(data))

def getAttributes(request, id):
    """ Get a list of attributes for a sample_type id.
    Input:
        id, sample_type id.
    """
    sampletype_id = int(id)
    print("sampletype_id:", sampletype_id)
    
    valueSelected = ''
    ret = request.GET
    if 'valueSelected' in ret:
        valueSelected = ret['valueSelected']
    
    sattr = DBtable_sampleattribute()
    data = sattr.getAttributes(sampletype_id, valueSelected)
    return HttpResponse(simplejson.dumps(data))

def getOperators(request):
    """ Get a list of attributes for a sample_type id.
    Input:
        id, sample_type id.
    """
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    
    sattr = DBtable_sampleattribute()
    data = sattr.getOperators(sampletype_id, attribute)
    return HttpResponse(simplejson.dumps(data))


def sampleSearch(request):
    """
    callback to "/samples/search/" for showing the page searching samples.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/samples/search/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    sampletype_id = 0
    #report['type_options'] = stype.getComboboxOptions(sampletype_id, 'title')
    report['type_options'] = stype.getSampleTypes()
    #print "okay", report['type_options']
    report['showSamplePage'] = True
    report['showSearch'] = True
    #report['bodyhtml'] = stype.getSamplePage(sampletype_id, user_seek['server'], user_seek['username'], user_seek['password'])
        
    return render(request,"sampleSearch.html", {'report':report})

def __searchFilterKeywords(keywords):
    ''' Given a list of tube codes, delimited by space or coma, design a query filter used in
        Django query.
        Input
            keywords, a list of tube codes, delimited by space or coma.
        Output
            qset = Q(...), the query filter used in Django query.
    '''
    print 'keywords: ', keywords
    kkk = keywords.strip()
    if len(kkk)==0:
        uids = []
        return uids
    
    keywords = keywords.replace(" ",",")    
    uids = keywords.split(",")
    print uids
    return uids
    
    qset = None
    #ids = __searchSamples(uids)
    dbsample = DBtable_sample()
    ids = dbsample.search(uids)
    
    ids = []
    #return cellids
    if len(ids)>0:
        qset = Q(id__in=ids)
    
    return qset    

    
def sampleSearching(request):
    """
    Searching the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    ret = request.GET
    '''
    variables = ret["variables"]
    #print "variables: ", variables
    variablesDic = json.loads(variables)
    keywords = variablesDic["keywords"]
    uids = __searchFilterKeywords(keywords)
    # callback for "/cells/searching/" 
    orderby = "ORDER BY id DESC"
    limit = ""
    '''
    
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    filter_rule = ret['filter_rule']
    filter_valueFrom = ret['filter_valueFrom']
    filter_valueTo = ret['filter_valueTo']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    dbsample = DBtable_sample()
    sdata = dbsample.searchSamples(user_seek, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
    
    #sattr = DBtable_sampleattribute()
    #data = sattr.getOperators(sampletype_id, attribute)
    #return HttpResponse(simplejson.dumps(data))
    
    #dbsample = DBtable_sample()
    #sdata = dbsample.search(uids, orderby, limit)

    return HttpResponse(sdata)

#@csrf_exempt
def remote(request):
    
    return samples(request)
    
    return render(request, response.text, context={})
    
    seekdb = SeekDB(request.session.get('storage'),
        request.session.get('username'),
        request.session.get('password'))
    
    webpage = seekdb.getPage('/')
    
    projects = seekdb.getProjects()
    
    selected_project_id = ""
    selected_project_name = ""
    selected_investigation_id = ""
    selected_investigation_name = ""
    selected_study_id = ""
    selected_study_name = ""
    selected_assay_id = ""
    selected_assay_name = ""
    cns = ""
    cna = ""
    eids = {}
    dids = []
    fullname = ""
    tags = []
    edamterm = ""
    
    inv_names = ""
    study_names = ""
    assay_names = ""
    sample_names = ""
    
    selected_disgenet_tags = ""
    stored_disgenet = ""
    stored_edam = ""
    edamterm = ""
    eids = []
    
    return render(
        request,
        "remote.html",
        context={'projects': projects,
                 'investigations': inv_names,
                 'studies': study_names,
                 'assays': assay_names,
                 'samples': sample_names,
                 'proj': selected_project_id,
                 'proj_name': selected_project_name,
                 'inv': selected_investigation_id,
                 'inv_name': selected_investigation_name,
                 'stu': selected_study_id,
                 'stu_name': selected_study_name,
                 'as': selected_assay_id,
                 'as_name': selected_assay_name,
                 'cns': cns,
                 'cna': cna,
                 'fullname': fullname,
                 'disgenet': dids,
                 'disgenettags': selected_disgenet_tags,
                 'storeddisgenet': stored_disgenet,
                 'storededam': stored_edam,
                 'edamterm': edamterm,
                 'edam': eids,
                 'storagetype': request.session.get('storage_type'),
                 'storage': request.session.get('storage')})




def datafileUpload(request):
    """
    Getting the information of datafiles.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
            
    #print(user_seek['userdata'])
    #for attri in user_seek['userdata']:
    #    print(attri)
    
    #print(user_seek['userdata']["relationships"])
    #print(user_seek['userdata']["relationships"]["projects"]["data"])
    
    #status = seekdb.testCreateStudy(user_seek)
    #status = seekdb.testCreateAssay(user_seek)
    
    report = {}
    #docs = DBtable_documents()
    #report['template_options'] = docs.getOptionsDocuments(0, "Sample Sheet Template")
    return render(request,"datafileUpload.html", {'report':report})

def handle_uploaded_file(file, output):
#    logging.debug("upload_here")
    #output = HDF5_REPOSITIRY + file.name
    print "file uploaded into: " + output
    destination = open(output, 'wb+')
    #destination = open('/tmp/'+file.name, 'wb+')
    #destination = open('/tmp', 'wb+')
    for chunk in file.chunks():
        destination.write(chunk)
    destination.close() 

def filesBatchUpload(request):
    """
    Getting the information of datafiles.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    
        filetype=request.POST.get('filetype_id'), one of the following options defined in seek/templates/datafileUpload.html,
                ="NOTSELECTED", not file type is selected, which is not allowed;
                ="DATAFILE",
                ="SOP",
                ="PRESENTATION"
    """
    print("filesBatchUpload:")
    filetype = request.POST.get('filetype')
    print("File type:", filetype)
    md5 = request.POST.get('md5')
    print("MD5:", md5)    
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
    
    #infile = request.FILES["uploadfiles"]
    #print(request)
    infile = request.FILES['file']
    #print(infile)
    #print(infile.name)
    
    # verify whether the file name has been quoted in any sample
    if filetype=="DATAFILE":
        dbsample = DBtable_sample()
        sampleRecord, msg = dbsample.searchFileInSample(seekdb, infile.name, filetype)
        # if the file name has been quoted in any sample has never been quoted in any sample,
        # the file is not allowed to be uploaded into the data lake
        if sampleRecord is None or sampleRecord['id']<=0:
            report = {}
            report['msg'] = msg
            print(report['msg'])
            report['status'] = 0
            report['df_info'] = {}            #df_info, the output from the API query "/sops/id/", such as,
        
            dfrecord = {}
            dfrecord['uid'] = ''
            dfrecord['originalname'] = infile.name
            #dfrecord['fileurl'] = 'Not available'
            dfrecord['fileurl'] = 'Not available ' + settings.SEEK_DATAFILE_SERVER
            dfrecord['notes'] = report['msg']
            dfrecord['content_type'] = filetype
            report['newrow'] = dfrecord
        
            #report['newrow'] = {}               #dfrecord, a record for shown in the table on the DropZone page, which includes    
            return HttpResponse(simplejson.dumps(report))
        
    '''
    sample_uuid = sampleRecord['uuid']
    dfrecord = {}
    dfrecord['uid'] = sample_uuid + "_" + infile.name
    dfrecord['originalname'] = infile.name
    dfrecord['fileurl'] = 'Ready to upload'
    dfrecord['notes'] = msg
    dfrecord['content_type'] = filetype
    report['newrow'] = dfrecord
    #report['newrow'] = {}               #dfrecord, a record for shown in the table on the DropZone page, which includes    
    return HttpResponse(simplejson.dumps(report))
    '''
    
    # Otherwise, continue to upload the file into the data lake.
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        #report = dbdf.uploadFileLink_intoSeek(seekdb, infile)
        sample_uid = sampleRecord['uuid']
        report = dbdf.uploadDF_toStorage(seekdb, infile, sample_uid, md5)
    elif filetype=="SOP":
        print("upload SOP")
        dbsop = DBtable_sops("DEFAULT")
        # upload file to storage server then toSeek
        #report = dbsop.uploadSOP_intoSeek(seekdb, infile)
        
        # upload file only to storage
        report = dbsop.uploadSOP_toStorage(seekdb, infile, md5)
    else:
        report = {}
        report['msg'] = "Warning: the file type is not supported yet: " + filetype
        print(report['msg'])
        report['status'] = 0
        report['df_info'] = {}            #df_info, the output from the API query "/sops/id/", such as,
        report['newrow'] = {}               #dfrecord, a record for shown in the table on the DropZone page, which includes
    
    return HttpResponse(simplejson.dumps(report))
    
    
def uploadToSeek(request):
    """
    After files are batch uploaded into the storage server, use Seek API to upload them into Seek server
    in a sequential order. This implementation is to address the issue that Seek API does not work well
    for parallel uplaoding of files in running seekupload() or seekuploadSOP().

    Arguments:
        request: Getting the information needed to upload the SEEK ISA structure.
    
        filetype=request.POST.get('filetype'), one of the following options defined in seek/templates/datafileUpload.html,
                ="NOTSELECTED", not file type is selected, which is not allowed;
                ="DATAFILE",
                ="SOP",
        fileuid, the uid of the file, generated from the file uploading to the storage server;
        filename, the original file name of the file.
    """
    print("uploadToSeek:")
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
    
        #ret = request.POST.get
    ret = request.POST
    #print(ret)
    filetype = ret['filetype']
    records = ret['records']
    diclist = json.loads(records)
        
    report = {}
    report['msg'] = "Warning: to be implemented"
    report['status'] = 0
    report['link'] = ""
    report['newrow'] = {}               #dfrecord, a record for shown in the table on the DropZone page, which includes
    if filetype=="DATAFILE":
        #return HttpResponse(simplejson.dumps(report))
        
        dbdf = DBtable_data_files("DEFAULT")
        #report = dbdf.uploadFileLink_intoSeek(seekdb, infile)
        report = dbdf.uploadDFs_storageToSeek(seekdb, diclist)
    elif filetype=="SOP":
        print("upload SOP")
        print("File type:", filetype)
        dbsop = DBtable_sops("DEFAULT")
        #report = dbsop.uploadSOP_intoSeek(seekdb, infile)
        
        # load a single file on server into Seek
        #content_type = ret['content_type']
        #originalfilename = ret['originalfilename']
        #report = dbsop.uploadSOP_storageToSeek(seekdb, originalfilename, content_type)
        
        # load multiple files into Seek
        #diclist = records
        #print(diclist)
        #for dici in diclist:
        #    print(dici)
        report = dbsop.uploadSOPs_storageToSeek(seekdb, diclist)
        
    else:
        report = {}
        report['msg'] = "Warning: the file type is not supported yet: " + filetype
        print(report['msg'])
        report['status'] = 0
        report['df_info'] = {}            #df_info, the output from the API query "/sops/id/", such as,
        report['newrow'] = {}               #dfrecord, a record for shown in the table on the DropZone page, which includes
    
    return HttpResponse(simplejson.dumps(report))
    
    

def filesGetUIDs(request):
    ''' upload a 2D tube when the url "/cells//workorder/" is selected
        on wga_cells_paged.embed.html.
    '''
    variable = "Hello, world. You're at the door of filesGetUIDs."
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    print variable
    ret = request.GET
    allFiles = json.loads(ret['allfiles'])
    dbdf = DBtable_data_files("DEFAULT")
    data = dbdf.filesGetUIDs(seekdb, allFiles)
    return HttpResponse(simplejson.dumps(data))
    
def seek(request):
    """Getting the investigations, studies and assays based on the 
    information given by the user in the upload form. The user selects
    the project, investigation, study and assay. After selecting the assay
    the user enter a title and description an can upload a data file to the
    selected assay.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
        
    Notes:
        migrated from MyFair project.
    """
    seekdb = SeekDB(request.session.get('storage'),
        request.session.get('username'),
        request.session.get('password'))
    projects = seekdb.getProjects()
    
    selected_project_id = ""
    selected_project_name = ""
    selected_investigation_id = ""
    selected_investigation_name = ""
    selected_study_id = ""
    selected_study_name = ""
    selected_assay_id = ""
    selected_assay_name = ""
    cns = ""
    cna = ""
    eids = {}
    dids = []
    fullname = ""
    tags = []
    edamterm = ""
    if request.POST.get('stored_disgenet') is not None:
        selected_disgenet_tags = request.POST.get('disgenetresult')
        stored_disgenet = request.POST.get('disgenetresult')
    else:
        stored_disgenet = None
        selected_disgenet_tags = ""
    if request.POST.get('stored_edam') is not None:
        stored_edam = request.POST.get('stored_edam')
    else:
        stored_edam = None
    if request.session.get('storage') is None:
        return HttpResponseRedirect(reverse('index'))
    if request.method == 'POST':
        if request.POST.get('res') is not None:
            datalist = request.POST.get('res').split("\n")
            for edamdata in datalist:
                if "URI" in edamdata:
                    uri = edamdata[4:]
                    stored_edam = uri
                if "Term" in edamdata:
                    edamdata = edamdata.split('\t')
                    edamterm = edamdata[1].strip('\r')
        if request.POST.get('disgenet') is not None and request.POST.get('disgenet') != "":
            selected_disgenet_tags = request.POST.get('disgenetresult')
            dids = disgenet(request.POST.get('disgenet'))
        elif request.POST.get('disgenet') is None and request.POST.get('disgenetresult') is not None:
            dids = request.POST.get('disgenetresult')
        else:
            dids = {}
        if request.POST.get("user") is not None or request.POST.get("user") != "":
            if fullname == "":
                fullname = request.POST.get("user")
            userid = seekdb.getUserid(fullname)
            if userid is None:
                return HttpResponseRedirect(reverse('seek'))
            
            
            # Get projects
            if request.POST.get("projects") is not None and request.POST.get("inv") is None:
                selected_project_id = request.POST.get("projects").split(',')[0]
                selected_project_name = request.POST.get("projects").split(',')[1]
                inv_names = seekdb.getInvestigations(selected_project_name)
            elif request.POST.get("proj-stored"):
                selected_project_id = request.POST.get("proj-stored").split(',')[0]
                selected_project_name = request.POST.get("proj-stored").split(',')[1]
                inv_names = seekdb.getSPARQLinvestigations(selected_investigation_name)
            # Get investigations
            if request.POST.get("investigations") is not None:
                selected_investigation_id = request.POST.get("investigations").split(',')[0]
                selected_investigation_name = request.POST.get("investigations").split(',')[1]
                study_names = seekdb.getStudies(selected_investigation_name)
            elif request.POST.get("inv-stored"):
                selected_investigation_id = request.POST.get("inv-stored").split(',')[0]
                selected_investigation_name = request.POST.get("inv-stored").split(',')[1]
                study_names = seekdb.getStudies(selected_investigation_name)
            else:
                study_names = {}
            # Get studies
            if request.POST.get("studies") is not None:
                selected_study_id = request.POST.get("studies").split(',')[0]
                selected_study_name = request.POST.get("studies").split(',')[1]
                assay_names = seekdb.getAssays(selected_study_name)
            elif request.POST.get("stu-stored"):
                selected_study_id = request.POST.get("stu-stored").split(',')[0]
                selected_study_name = request.POST.get("stu-stored").split(',')[1]
                assay_names = seekdb.getAssays(selected_study_name)
            else:
                assay_names = {}
            # Get assays
            if request.POST.get("assays") is not None:
                selected_assay_id = request.POST.get("assays").split(',')[0]
                selected_assay_name = request.POST.get("assays").split(',')[1]
            elif request.POST.get("as-stored") is not None:
                selected_assay_id = request.POST.get("as-stored").split(',')[0]
                selected_assay_name = request.POST.get("as-stored").split(',')[1]
            cns = request.POST.get('cns')
            cna = request.POST.get('cna')
            if selected_assay_id != "":
                sample_names = seekdb.getSamples(selected_assay_name)
            else:
                sample_names = {}
            if (
                request.POST.get('newstudy')
            ):
                seekdb.createStudy(userid,
                    selected_project_id,
                    selected_investigation_id,
                    request.POST.get('stitle'),
                    request.POST.get('sdescription'),
                    request.POST.get('newstudy')
                )
            if (request.POST.get('newassay')):
                seekcheck = seekdb.createAssay(userid,
                    selected_project_id,
                    selected_study_id,
                    request.POST.get('atitle'),
                    request.POST.get('adescription'),
                    request.POST.get('assay_type'),
                    request.POST.get('technology_type'),
                    request.POST.get('newassay')
                )
                if not seekcheck:
                    return HttpResponseRedirect(reverse('seek'))
            if request.FILES.get('uploadfiles'):
                tags.append(stored_disgenet)
                tags.append(stored_edam.strip('\r\n'))
                upload_dir = (
                    "tmp" +
                    hashlib.md5(request.session.get(
                        'username').encode('utf-8')).hexdigest()
                )
                upload_full_path = os.path.join(
                    settings.MEDIA_ROOT, upload_dir)
                content_type = request.FILES['uploadfiles'].content_type
                if not os.path.exists(upload_full_path):
                    os.makedirs(upload_full_path)
                upload = request.FILES["uploadfiles"]
                while os.path.exists(os.path.join(upload_full_path, upload.name)):
                    upload.name = '_' + upload.name
                dest = open(os.path.join(upload_full_path, upload.name), 'wb')
                for chunk in upload.chunks():
                    dest.write(chunk)
                dest.close()
                seekdb.seekupload(
                    #seekupload(
                    #request.session.get('username'),
                    #request.session.get('password'),
                    #request.session.get('storage'),
                    request.POST.get('datatitle'),
                    os.path.join(upload_full_path, upload.name),
                    upload.name,
                    content_type,
                    userid,
                    selected_project_id,
                    selected_assay_id,
                    request.POST.get('description'),
                    tags
                )
                call(["rm", "-r", upload_full_path])
                call(["rm", "-r", os.path.join(upload_full_path, upload.name)])
                return HttpResponseRedirect(reverse("index"))
    else:
        inv_names = {}
        study_names = {}
        assay_names = {}
        sample_names = {}
    return render(
        request,
        "seek.html",
        context={'projects': projects,
                 'investigations': inv_names,
                 'studies': study_names,
                 'assays': assay_names,
                 'samples': sample_names,
                 'proj': selected_project_id,
                 'proj_name': selected_project_name,
                 'inv': selected_investigation_id,
                 'inv_name': selected_investigation_name,
                 'stu': selected_study_id,
                 'stu_name': selected_study_name,
                 'as': selected_assay_id,
                 'as_name': selected_assay_name,
                 'cns': cns,
                 'cna': cna,
                 'fullname': fullname,
                 'disgenet': dids,
                 'disgenettags': selected_disgenet_tags,
                 'storeddisgenet': stored_disgenet,
                 'storededam': stored_edam,
                 'edamterm': edamterm,
                 'edam': eids,
                 'storagetype': request.session.get('storage_type'),
                 'storage': request.session.get('storage')})


def seek_upload(request):
    """Getting the investigations, studies and assays based on the 
    information given by the user in the upload form. The user selects
    the project, investigation, study and assay. After selecting the assay
    the user enter a title and description an can upload a data file to the
    selected assay.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
        
    Notes:
        migrated from MyFair project.
    """
    if request.session.get('storage') is None:
        return HttpResponseRedirect(reverse('index'))
    
    seekdb = SeekDB(request.session.get('storage'),
        request.session.get('username'),
        request.session.get('password'))
    projects = seekdb.getProjects()
    
    selected_project_id = ""
    selected_project_name = ""
    selected_investigation_id = ""
    selected_investigation_name = ""
    selected_study_id = ""
    selected_study_name = ""
    selected_assay_id = ""
    selected_assay_name = ""
    cns = ""
    cna = ""
    eids = {}
    dids = []
    fullname = ""
    tags = []
    edamterm = ""
    
    stored_disgenet = None
    selected_disgenet_tags = ""
    dids = {}
    
    stored_edam = None
    edamterm = ""
        
    if request.method == 'POST':
        stored_edam, edamterm = __getEdam(request)
                    
        stored_disgenet, selected_disgenet_tags, dids = __getDisgenetTags(request)
            
        if request.POST.get("user") is not None or request.POST.get("user") != "":
            if fullname == "":
                fullname = request.POST.get("user")
            userid = seekdb.getUserid(fullname)
            if userid is None:
                return HttpResponseRedirect(reverse('seek'))
            
            # Get projects
            selected_project_id, selected_project_name, inv_names = __getProjects(request, seekdb)
             
            # Get investigations
            selected_investigation_id, selected_investigation_name, study_names = __getInvestigations(request, seekdb)
                
            # Get studies
            selected_study_id, selected_study_name, assay_names = __getStudies(request, seekdb)

            # Get assays
            selected_assay_id, selected_assay_name, sample_names = __getAssays(request, seekdb)
                
            cns = request.POST.get('cns')
            cna = request.POST.get('cna')

            if (
                request.POST.get('newstudy')
            ):
                seekdb.createStudy(userid,
                    selected_project_id,
                    selected_investigation_id,
                    request.POST.get('stitle'),
                    request.POST.get('sdescription'),
                    request.POST.get('newstudy')
                )
            if (request.POST.get('newassay')):
                seekcheck = seekdb.createAssay(userid,
                    selected_project_id,
                    selected_study_id,
                    request.POST.get('atitle'),
                    request.POST.get('adescription'),
                    request.POST.get('assay_type'),
                    request.POST.get('technology_type'),
                    request.POST.get('newassay')
                )
                if not seekcheck:
                    return HttpResponseRedirect(reverse('seek'))
            if request.FILES.get('uploadfiles'):
                tags.append(stored_disgenet)
                tags.append(stored_edam.strip('\r\n'))
                seekdb.uploadFile_seek(request, userid, selected_project_id, selected_assay_id, tags)
                return HttpResponseRedirect(reverse("index"))
    else:
        inv_names = {}
        study_names = {}
        assay_names = {}
        sample_names = {}
    return render(
        request,
        "seek.html",
        context={'projects': projects,
                 'investigations': inv_names,
                 'studies': study_names,
                 'assays': assay_names,
                 'samples': sample_names,
                 'proj': selected_project_id,
                 'proj_name': selected_project_name,
                 'inv': selected_investigation_id,
                 'inv_name': selected_investigation_name,
                 'stu': selected_study_id,
                 'stu_name': selected_study_name,
                 'as': selected_assay_id,
                 'as_name': selected_assay_name,
                 'cns': cns,
                 'cna': cna,
                 'fullname': fullname,
                 'disgenet': dids,
                 'disgenettags': selected_disgenet_tags,
                 'storeddisgenet': stored_disgenet,
                 'storededam': stored_edam,
                 'edamterm': edamterm,
                 'edam': eids,
                 'storagetype': request.session.get('storage_type'),
                 'storage': request.session.get('storage')})

def __getDisgenetTags(request):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    stored_disgenet = None
    selected_disgenet_tags = ""
    dids = {}
    if request.POST.get('stored_disgenet') is not None:
        selected_disgenet_tags = request.POST.get('disgenetresult')
        stored_disgenet = request.POST.get('disgenetresult')

    if request.POST.get('disgenet') is not None and request.POST.get('disgenet') != "":
        selected_disgenet_tags = request.POST.get('disgenetresult')
        dids = disgenet(request.POST.get('disgenet'))
    elif request.POST.get('disgenet') is None and request.POST.get('disgenetresult') is not None:
        dids = request.POST.get('disgenetresult')
        
    return stored_disgenet, selected_disgenet_tags, dids


def __getEdam(request):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    stored_edam = None
    edamterm = ""
    if request.POST.get('stored_edam') is not None:
        stored_edam = request.POST.get('stored_edam')
        
    if request.POST.get('res') is not None:
        datalist = request.POST.get('res').split("\n")
        for edamdata in datalist:
            if "URI" in edamdata:
                uri = edamdata[4:]
                stored_edam = uri
            if "Term" in edamdata:
                edamdata = edamdata.split('\t')
                edamterm = edamdata[1].strip('\r')
    return stored_edam, edamterm


def __getProjects(request, seekdb):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    selected_project_id = ""
    selected_project_name = ""
    inv_names = {}
    
    # Get projects
    if request.POST.get("projects") is not None and request.POST.get("inv") is None:
        selected_project_id = request.POST.get("projects").split(',')[0]
        selected_project_name = request.POST.get("projects").split(',')[1]
        inv_names = seekdb.getInvestigations(selected_project_name)
    elif request.POST.get("proj-stored"):
        selected_project_id = request.POST.get("proj-stored").split(',')[0]
        selected_project_name = request.POST.get("proj-stored").split(',')[1]
        inv_names = seekdb.getSPARQLinvestigations(selected_investigation_name)
    return selected_project_id, selected_project_name, inv_names

def __getInvestigations(request, seekdb):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    selected_investigation_id = ""
    selected_investigation_name = ""
    
    # Get investigations
    if request.POST.get("investigations") is not None:
        selected_investigation_id = request.POST.get("investigations").split(',')[0]
        selected_investigation_name = request.POST.get("investigations").split(',')[1]
        study_names = seekdb.getStudies(selected_investigation_name)
    elif request.POST.get("inv-stored"):
        selected_investigation_id = request.POST.get("inv-stored").split(',')[0]
        selected_investigation_name = request.POST.get("inv-stored").split(',')[1]
        study_names = seekdb.getStudies(selected_investigation_name)
    else:
        study_names = {}
    return selected_investigation_id, selected_investigation_name, study_names

def __getStudies(request, seekdb):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    selected_study_id = ""
    selected_study_name = ""
    
    # Get studies
    if request.POST.get("studies") is not None:
        selected_study_id = request.POST.get("studies").split(',')[0]
        selected_study_name = request.POST.get("studies").split(',')[1]
        assay_names = seekdb.getAssays(selected_study_name)
    elif request.POST.get("stu-stored"):
        selected_study_id = request.POST.get("stu-stored").split(',')[0]
        selected_study_name = request.POST.get("stu-stored").split(',')[1]
        assay_names = seekdb.getAssays(selected_study_name)
    else:
        assay_names = {}
        
    return selected_study_id, selected_study_name, assay_names

def __getAssays(request, seekdb):
    ''' 
    Notes:
        migrated from def seek(request) in MyFair project.
    '''
    selected_assay_id = ""
    selected_assay_name = ""
    
    # Get assays
    if request.POST.get("assays") is not None:
        selected_assay_id = request.POST.get("assays").split(',')[0]
        selected_assay_name = request.POST.get("assays").split(',')[1]
    elif request.POST.get("as-stored") is not None:
        selected_assay_id = request.POST.get("as-stored").split(',')[0]
        selected_assay_name = request.POST.get("as-stored").split(',')[1]
        
    if selected_assay_id != "":
        sample_names = seekdb.getSamples(selected_assay_name)
    else:
        sample_names = {}
      
    return selected_assay_id, selected_assay_name, sample_names

def seek_revised(request):
    """Getting the investigations, studies and assays based on the 
    information given by the user in the upload form. The user selects
    the project, investigation, study and assay. After selecting the assay
    the user enter a title and description an can upload a data file to the
    selected assay.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
        
    Notes:
        migrated from MyFair project.
    """
    seekdb = SeekDB(request.session.get('storage'),
        request.session.get('username'),
        request.session.get('password'))
    projects = seekdb.getProjects()
    
    print(projects)
    
    fullname = ""
    tags = []
    
    if request.method == 'POST':
        
        if request.POST.get("user") is not None or request.POST.get("user") != "":
            if fullname == "":
                fullname = request.POST.get("user")
            userid = seekdb.getUserid(fullname)
            if userid is None:
                return HttpResponseRedirect(reverse('seek'))
            
            # Get projects
            selected_project_id, selected_project_name, inv_names = __getProjects(request, seekdb)
            
            # Get investigations
            selected_investigation_id, selected_investigation_name, study_names = __getInvestigations(request, seekdb)

            # Get studies
            selected_study_id, selected_study_name, assay_names = __getStudies(request, seekdb)

            # Get assays
            selected_assay_id, selected_assay_name, sample_names = __getAssays(request, seekdb)
                        
            if (request.POST.get('newstudy')):
                seekdb.createStudy(userid,
                    selected_project_id,
                    selected_investigation_id,
                    request.POST.get('stitle'),
                    request.POST.get('sdescription'),
                    request.POST.get('newstudy')
                )
                
            if (request.POST.get('newassay')):
                seekcheck = seekdb.createAssay(userid,
                    selected_project_id,
                    selected_study_id,
                    request.POST.get('atitle'),
                    request.POST.get('adescription'),
                    request.POST.get('assay_type'),
                    request.POST.get('technology_type'),
                    request.POST.get('newassay')
                )
                if not seekcheck:
                    return HttpResponseRedirect(reverse('seek'))
                    
            if request.FILES.get('uploadfiles'):
                tags.append(stored_disgenet)
                tags.append(stored_edam.strip('\r\n'))
                seekdb.uploadFile(request, userid, selected_project_id, selected_assay_id, tags)
                return HttpResponseRedirect(reverse("index"))


def sopDownload(request, uid):
    ''' Download a data file,given
    Input:
        request, http request
        uid, uid of the data file, could be any string.
    Output:
        weblink of the file, or an error message
    
    '''
    return fileDownload(request, uid, "SOP")

def datafileDownload(request, uid):
    ''' Download a data file,given
    Input:
        request, http request
        uid, uid of the data file, could be any string.
    Output:
        weblink of the file, or an error message
    
    '''
    return fileDownload(request, uid, "DATAFILE")
    
def fileDownload(request, uid, filetype):
    print(uid)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/datafiles/uid=' + uid + '/'
        return HttpResponseRedirect(url_redirect)
    
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        msg, status, link = dbdf.downloadDF_fromStorage(user_seek, uid)
    elif filetype=="SOP":
        print("Download SOP")
        print("File type:", filetype)
        dbsop = DBtable_sops("DEFAULT")
        msg, status, link = dbsop.downloadSOP_fromStorage(user_seek, uid)
    else:
        msg = 'Error: file type not supported.'
        status = 0
        link = None
        
    if status==1:
        url_redirect = link
        return HttpResponseRedirect(url_redirect)
    else:
        return render(request, 'pages/404.html')
        return render(request, '404.html', status=404)
        return HttpResponse(msg)
        url_redirect = '/404/'
        return HttpResponseRedirect(url_redirect)
    #return HttpResponse(simplejson.dumps(report))
    return HttpResponse("You're downloading file %s." % uid)
 
def fileQuery(request, filetype):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        if filetype=="DATAFILE":
            url_redirect = '/login/?next=/seek/datafile/query/'
        elif filetype=="SOP":
            url_redirect = '/login/?next=/seek/sop/query/'
        else:
            url_redirect = '/login/'
        return HttpResponseRedirect(url_redirect)

    pk = 0
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        form, report = dbdf.formInfo(request, pk)
        report['table_url'] = '/seek/retrieve/datafiles/'
        report['batchdownload_url'] = '/seek/batchdownload/datafiles/'
        #report['batchpublish_url'] = '/seek/batchpublish/datafiles/'
        report['batchpublish_url'] = '/seek/datafiles/publish/'
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        form, report = dbsop.formInfo(request, pk)
        report['table_url'] = '/seek/retrieve/sops/'
        report['batchdownload_url'] = '/seek/batchdownload/sops/'
        #report['batchpublish_url'] = '/seek/batchpublish/sops/'
        report['batchpublish_url'] = '/seek/sops/publish/'
    else:
        msg = 'Error: file type not supported.'
        status = 0
        report = {}
        form= None
    
    return render(request,"batchSearch.html", {"report" : report, "form": form})

def datafileQuery(request):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    return fileQuery(request, "DATAFILE") 
    
def sopQuery(request):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    return fileQuery(request, "SOP") 
    
def filelist(request, filetype):
    """
    Getting the information of files.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        reportData = dbdf.processRecords(request, user_seek, "retrieve")
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        reportData = dbsop.processRecords(request, user_seek, "retrieve")
    elif filetype=="DOWNLOAD_DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        reportData = dbdf.processRecords(request, user_seek, "download")
    elif filetype=="DOWNLOAD_SOP":
        dbsop = DBtable_sops("DEFAULT")
        reportData = dbsop.processRecords(request, user_seek, "download")
    elif filetype=="PUBLISH_DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        reportData = dbdf.processRecords(request, user_seek, "publish")
    elif filetype=="PUBLISH_SOP":
        dbsop = DBtable_sops("DEFAULT")
        reportData = dbsop.processRecords(request, user_seek, "publish")
    else:
        reportData = simplejson.dumps({})

    return HttpResponse(reportData)  
    
def retrieveSops(request):
    return filelist(request, "SOP")
    
def retrieveDatafiles(request):
    return filelist(request, "DATAFILE")
    
def batchdownloadSops(request):
    return filelist(request, "DOWNLOAD_SOP")
    
def batchdownloadDatafiles(request):
    return filelist(request, "DOWNLOAD_DATAFILE")
    
def batchpublishSops(request):
    return filelist(request, "PUBLISH_SOP")
    
def batchpublishDatafiles(request):
    return filelist(request, "PUBLISH_DATAFILE")
    
    
def callCmdline(cmd):
    """
        Execute the external command and get its exitcode, stdout and stderr.
            
        Input:
            cmd: a command line, such as 
                curl -u 'username:password' -k  -X POST "http://dmac.mit.edu:3000/data_files" -H "accept: application/json" -H "Content-Type: application/json" -d "{}"

        Output
            exitcode: such as 0 if the command runs successfully;
            err: the message returned from Seek, such as:
                 '  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current\n
                       Dload  Upload   Total   Spent    Left  Speed\n\r
                       0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0\r
                       100  1981    0  1411  100   570   1811    731 --:--:-- --:--:-- --:--:--  2543\n'
            out: the feedback of the Seek API call, such as,
                 '{"data":{"id":"20","type":"data_files","attributes":{"policy":{"access":"download","permissions":[{"resource":{"id":"1","type":"projects"},"access":"edit"}]},"title":"testdatafile2","description":"test data file uploading2","license":"CC-BY-4.0","latest_version":1,"tags":null,"versions":[{"version":1,"revision_comments":null,"url":"http://dmac.mit.edu:3000/data_files/20?version=1"}],"version":1,"revision_comments":null,"created_at":"2019-12-10T19:36:54.000Z","updated_at":"2019-12-10T19:36:54.000Z","content_blobs":[{"original_filename":"t-cell-beta.png","url":null,"md5sum":null,"sha1sum":null,"content_type":"image/png","link":"http://dmac.mit.edu:3000/data_files/20/content_blobs/37","size":null}],"other_creators":null},"relationships":{"creators":{"data":[{"id":"1","type":"people"}]},"submitter":{"data":[{"id":"1","type":"people"}]},"people":{"data":[{"id":"1","type":"people"}]},"projects":{"data":[{"id":"1","type":"projects"}]},"investigations":{"data":[{"id":"2","type":"investigations"}]},"studies":{"data":[{"id":"1","type":"studies"}]},"assays":{"data":[{"id":"8","type":"assays"}]},"publications":{"data":[]},"events":{"data":[]}},"links":{"self":"/data_files/20?version=1"},"meta":{"created":"2019-12-10T19:36:53.962Z","modified":"2019-12-10T19:36:54.034Z","api_version":"0.2","uuid":"57e0aa00-fdb2-0137-a0f6-000c295a2b25","base_url":"http://dmac.mit.edu:3000"}},"jsonapi":{"version":"1.0"}}'
                which is exactly the result of running the Seek API.
    """
    args = shlex.split(cmd)
    print(args)
    
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode
        #
    print("exitcode: %", exitcode)
    print("err: %", err)
    print("out: %", out)
    return exitcode, out, err    
    
def __getDropBoxFolders(user_seek, ifMkdir=True):
    '''  Get the folder names for uploading files into DropBox, given
    Input
        user_seek, log in user info,
        ifMkdir, whether or not mkdir if a folder does not exist.
            True, mkdir for folders that do not exist;
            False, otherwise.
    
    Output
    
    '''
    username = user_seek['username']
    # All data files fro dropZone will be stored under the default project and default assay,
    # until it is included in the sample sheet for actual assay association.
    projectname = user_seek['projectname']
        
    institutionname = user_seek['institutionname']
    # lab abbreviation, three letter abbreviation of a lab
    lababbv = user_seek['lababbv']
        
    # Step 1. Get full path of the uploading folder
    # Lab folder, such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab"
    labfolder = lababbv
            
    upload_dropbox_path_labroot = os.path.join(DROPBOX_DIRECTORY, labfolder)
    if not os.path.exists(upload_dropbox_path_labroot) and ifMkdir:
        print("mkdir: ", upload_dropbox_path_labroot)
        os.makedirs(upload_dropbox_path_labroot)
        
    # the sub-folder name, defined by the project name, in which any space is replaced by '_'.
    projectfolder = projectname
    if " " in projectname:
        projectfolder = projectname.replace(" ", "_")
            
    # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
    upload_dropbox_path_projectroot = os.path.join(upload_dropbox_path_labroot, projectfolder)
    print('project_root:', upload_dropbox_path_projectroot)
    if not os.path.exists(upload_dropbox_path_projectroot) and ifMkdir:
        os.makedirs(upload_dropbox_path_projectroot)
        
    # such as "/net/bmc-pub10/data1/bmc/seek/lauffenbourgLab/impactb"
    upload_dropbox_path = upload_dropbox_path_projectroot
    
    # folder path for uploading data files
    dropbox_datafile_folder = os.path.join(upload_dropbox_path, 'for_datafiles')
    if not os.path.exists(dropbox_datafile_folder) and ifMkdir:
        os.makedirs(dropbox_datafile_folder)
    
    # folder path for uploading sop files
    dropbox_sop_folder = os.path.join(upload_dropbox_path, 'for_protocols')
    if not os.path.exists(dropbox_sop_folder) and ifMkdir:
        os.makedirs(dropbox_sop_folder)
        
    return upload_dropbox_path, dropbox_datafile_folder, dropbox_sop_folder
    
def getDropboxPath(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/dropbox/path/'
        return HttpResponseRedirect(url_redirect)

    msg = 'getDropboxPath'
    ifMkdir = True
    upload_dropbox_path, dropbox_datafile_folder, dropbox_sop_folder = __getDropBoxFolders(user_seek, ifMkdir)
        
    readmefile_root = DROPBOX_DIRECTORY + 'ReadME.html'
    cmd = 'cp ' + readmefile_root + ' ' + upload_dropbox_path
    exitcode, out, err = callCmdline(cmd)
    readmefile = upload_dropbox_path + '/ReadME.html'
    print(readmefile)
    
    cmd = '!/myhome/websites/dmac/seek/dropbox.py sharelink ' + readmefile
    
    exitcode, out, err = callCmdline(cmd)
    if exitcode==0:
        #msg = msg + ': ' + out
        msg = out.strip()
        return HttpResponseRedirect(msg)
    else:
        msg = 'Error: Dropbox not ready ' + str(err)
        return HttpResponse(msg)
    
    
def getDropboxStatus(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/dropbox/status/'
        return HttpResponseRedirect(url_redirect)

    msg = 'getDropboxStatus'
    ifMkdir = False
    upload_dropbox_path, dropbox_datafile_folder, dropbox_sop_folder = __getDropBoxFolders(user_seek, ifMkdir)

    # get file names in the folder
    cmd = '~/myhome/websites/dmac/seek/dropbox.py ls ' + dropbox_datafile_folder
    
    exitcode, out, err = callCmdline(cmd)
    if exitcode==0:
        #msg = msg + ': ' + out
        #msg = out.strip()
        msg = out
    elif out is None:
        msg = 'Error: Dropbox not ready ' + str(err)
        return HttpResponse(msg)
    else:
        msg = 'Error: Dropbox not ready ' + str(err)
        return HttpResponse(msg)
        
    
    files = out.strip().split(' ')
    msg = ''
    for file in files:
        if file=='<empty>':
            msg = 'No file is found in the Dropbox folder.'
            continue
        else:
            print(file)
            msg += file + '\n'
    
    return HttpResponse(msg)
    
def retrieveSamples(request):
    """
    Getting the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK DB.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    dbsample = DBtable_sample()
    reportData = dbsample.processRecords(request, user_seek, "retrieve")

    return HttpResponse(reportData) 

def sampleDownload(request):
    """
    Searching the information of samples.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    return sampleDownload_new(request)
    
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    filter_rule = ret['filter_rule']
    filter_valueFrom = ret['filter_valueFrom']
    filter_valueTo = ret['filter_valueTo']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'download-samples-' + datenow + '.xls'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sdata = dbsample.downloadSamples(user_seek, downloadfile, link, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
    return HttpResponse(sdata)
    
def sampleDownload_new(request):
    """
    Download the list of samples into an excel file, in which columns are sample attribute names
    and constants are saved in a separated sheet.

    Arguments:
        request: Getting the list of sample ids.
    """
    ret = request.GET
    allids = ret['allids']
    print(allids)
    
    sampletype_id = ret['sampletype_id']
    
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'download-samples-' + datenow + '.xls'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sdata = dbsample.downloadSamples_new(user_seek, downloadfile, link, sample_ids)
    return HttpResponse(sdata)    

def sampleExport(request):
    """
    Similar to sampleDownload_new(), download the list of samples into an Immport template file, in which columns are Immport headers
    mapped from sample attribute names.

    Arguments:
        request: Getting the list of sample ids.
    """
    ret = request.GET
    allids = ret['allids']
    print(allids)
    
    sampletype_id = ret['sampletype_id']
    
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-export' + datenow + '.xlsx'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    #sdata = dbsample.downloadSamples_new(user_seek, downloadfile, link, sample_ids)
    sdata = dbsample.exportSamples(user_seek, downloadfile, link, sample_ids, sampletype_id)
    return HttpResponse(sdata)   

def sampleFindAjax(request):
    ''' Use javascript to find samples in an excel file for batch-exporting samples
        when the url "/seek/samplefind/" is selected on publishAssets_search.embed.html.
    '''
    #print request
    variable = "I received request from /seek/samplefind/!"
    #print(variable)
    
    #if verifyUser(request)==0:
    #    return HttpResponseRedirect("/accounts/login/?next=/seek/samples/")

    username = str(request.user)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)

    
    #return HttpResponse(variable)
    #print request.user
    #print(request.POST)
    msg = "Error: File not valid"
    message = ''
    status = 0
    data = {'msg':msg, 'status': status, 'link':''}
    if request.method == "POST":
        if request.FILES and request.FILES.get('excelfile_find'):
            excelfile = request.FILES['excelfile_find']
            if excelfile:
                #sampletype_id = request.POST.get('sampletype_id')
                #print('sampletype_id:', sampletype_id)
                # no predefined sample type available, use the Instruction sheet to find it out.
                #sampletype_id = 0
                
                inputfile = excelfile.name
                #print(inputfile)
                names = inputfile.split(".")
                n = len(names)
                
                datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                #filename = 'samples-export' + datenow + '.xlsx'
                filename = 'samples-export' + datenow + '.zip'
                #filename = 'samples_upload_feedback.xls'
                downloadfile = DOWNLOAD_DIRECTORY + filename
                link = DOWNLOAD_DIRECTORY_LINK + filename
                
                dbsample = DBtable_sample()
                sdata = dbsample.findSamplesForExport(user_seek, downloadfile, link, excelfile)
                return HttpResponse(sdata)
                                
                #msgi, status = sample.batchUpload(excelfile, feedbackfile, user_seek)
                if status:
                    msg = 'Batch sample uploading successful. To find the UIDs for samples uploaded, refer to the feedback excel file: ' + filename
                    #msg += msgi
                    message = msg + '\n\n' + msgi
                else:
                    message = msgi
                    
                    #msg = 'Batch sample uploading failed. <br/>Refer to the log and the feedback excel file: ' + filename + '.<br/>'
                    terms = msgi.split("<")
                    msg = terms[0] + "<br/><br/>"
                    msg += "Refer to the log and the excel file: " + filename + '.<br/>'
                    
                #    print(msg, status, link)
                data = {'msg':msg, 'status': status, 'link':link}
            else:
                message = 'Error: Not a valid file from client side'
                data = {'msg':message, 'status': 0, 'link':''}
        else:
            message = 'Error: Not a valid file from client side'
            data = {'msg':message, 'status': 0, 'link':''}
    else:
        message = 'Error: Not a valid http POST request'
        data = {'msg':message, 'status': 0, 'link':''}
                
    #message = data['msg']
    if message is not None and '<br/>' in message:
        data['message'] = message.replace('<br/>', '\n')
    else:
        data['message'] = message
                
    return HttpResponse(simplejson.dumps(data))   

    
def sampleDelete(request):
    """
    Download the list of samples.

    Arguments:
        request: Getting the list of sample ids.
    """
    ret = request.GET
    allids = ret['allids']
    print(allids)
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-deletion' + datenow + '.xls'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sdata = dbsample.deleteSamples(user_seek, downloadfile, link, sample_ids)
    return HttpResponse(sdata)
    
def publishSamples(user_seek, sample_ids, assay_id=None, project_id=None):
    """
    Publish the list of samples so that they are publically accessible.

    Arguments:
        request: Getting the list of sample ids.
    """
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-publish' + datenow + '.xlsx'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    # copy template file as the file for download
    templatefile = SAMPLE_TEMPLATE_FILE
    print(templatefile)
    print(downloadfile)
    #handle_uploaded_file(templatefile, downloadfile)
    cmd = 'cp ' + templatefile + ' ' + downloadfile
    os.system(cmd)
    
    # we can return a json object here
    dbsample = DBtable_sample()
    sdata = dbsample.publishSamples(user_seek, downloadfile, link, sample_ids, assay_id, project_id)
    return HttpResponse(sdata)
    
def __definePublishServer(seekdb, user_seek):
    ''' Define the class for accessing the remote Seek server for publishing assets.
    Input:
        seekdb, local Seek API class.
        user_seek, local seek user 
        
    Output:
        sdb, Remote Seek API class.
        user, Remote Seek user.
    '''
    username = user_seek['username']
    password = user_seek['password']
    person_id = user_seek['person_id']
    # get local user's full name
    fullname = seekdb.getUserFullname(person_id)
        
    # activate the remote Seek server, such as fairdomHub
    # by using the local loginname, password and user fullname.
    server = PUBLISH_SERVER
    sdb = SeekDB(server, username, password)
    user = sdb.updateUserProfile(fullname)
    
    return sdb, user
    
    
def __getISA(seekdb, user_seek, whichServer):
    ''' Retrieve the ISA structure from either the source or destination Seek server.
    
    Input:
        seekdb, source Seek server;
        user_seek, source Seek user;
        whichServer, either "SOURCE", i.e., the source Seek server, from which assets are to be retrieved.
                     or "DESTINATION", i.e., the destination Seek server, to which assets are to be published.
    Output:
        Three lists of investigations, studies and assays, in the format good for COmboBox, such as,
            var investigation_options = [
                { id: "id1", title: "aa1" },
                { id: "id2", title: "aa2" }
            ];
            var studies = {"id1":
                [
                	{ id: "id3", title: "aa3" },
                	{ id: "id4", title: "aa4" }
                ], "id2":
                [
                    { id: "id5", title: "aa5" },
                    { id: "id6", title: "aa6" }
                ]
            };
    
    '''
    if whichServer=="SOURCE":
        # the user on the local source Seek server
        sdb = seekdb
        user = user_seek
        project_title = user['projectname']
        server = 'local'
    elif whichServer=="DESTINATION":
        sdb, user = __definePublishServer(seekdb, user_seek)
        server = PUBLISH_SERVER
        if 'projectname' in user:
            project_title = user['projectname']
        else:
            project_title = None
    else:
        return None, None, None, None, None
    
    project_options, investigation_options_dic, study_options_dic, assay_options_dic = sdb.getISAOptions()
    return project_options, investigation_options_dic, study_options_dic, assay_options_dic, server
    
def samplePublish(request):
    """
    Publish the list of samples so that they are publically accessible.

    Arguments:
        request: Getting the list of sample ids.
    """
    #return publish(request)
    
    
    ret = request.POST
    #print('ret', ret)
    if 'allids' in ret:
        allids = ret['allids']
        sample_ids = json.loads(allids)
    else:
        sample_ids = []
    #print(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-publish' + datenow + '.xlsx'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    # copy template file as the file for download
    templatefile = SAMPLE_TEMPLATE_FILE
    #print(templatefile)
    #print(downloadfile)
    #handle_uploaded_file(templatefile, downloadfile)
    cmd = 'cp ' + templatefile + ' ' + downloadfile
    os.system(cmd)
    
    # we can return a json object here
    #dbsample = DBtable_sample()
    #sdata = dbsample.publishSamples(user_seek, downloadfile, link, sample_ids)
    #return HttpResponse(sdata)
    
    # However, we return a full html page instead
    #investigation_options, study_options_dic, assay_options_dic = __getISA(seekdb, user_seek, "SOURCE")
    #projects_options, investigation_options, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    project_options, investigation_options_dic, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    
    report = {}
    report['project_options'] = project_options
    report['investigation_options_dic'] = investigation_options_dic
    #report['investigation_options'] = investigation_options
    report['study_options_dic'] = study_options_dic
    report['assay_options_dic'] = assay_options_dic
    report['showSamplePage'] = True
    report['showSearch'] = True
    return render(request,"publish.html", {'report':report})
    
def publish_assets(request, idsstring, assetType):
    
    
    
    ids = [int(i) for i in idsstring.split(',')]
    diclist = []
    for id in ids:
        dici = {}
        dici['id'] = id
        dici['asset_type'] = assetType
        if int(id)>0:
            diclist.append(dici)
    
    #print('sample_list in int:', ids)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/publish/'
        return HttpResponseRedirect(url_redirect)
    
    
    # However, we return a full html page instead
    #investigation_options, study_options_dic, assay_options_dic = __getISA(seekdb, user_seek, "SOURCE")
    #projects_options, investigation_options, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    project_options, investigation_options_dic, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    
    report = {}
    report['project_options'] = project_options
    report['investigation_options_dic'] = investigation_options_dic
    #report['investigation_options'] = investigation_options
    report['study_options_dic'] = study_options_dic
    report['assay_options_dic'] = assay_options_dic
    report['showSamplePage'] = True
    report['showSearch'] = True
    report['assetData'] = diclist
    report['publish_server'] = server
    return render(request,"publishAssets.html", {'report':report})
    #return render(request,"publish.html", {'report':report})
    
    
    # user associated projectname
    project_title = user_seek['projectname']
    
    # get investigations under a project in {'id1':'title1', 'id2':'title2', ...}
    investigations = seekdb.getInvestigations(project_title)
    investigation_options = json.dumps(convertDicToOptions(investigations))
    
    report = {}
    report['investigation_options'] = investigation_options
    report['showSamplePage'] = True
    report['showSearch'] = True
    report['assetData'] = diclist
    return render(request,"publishAssets.html", {'report':report})
    
def publish_samples(request, sampleids=None):
    assetType = 'Sample'
    return publish_assets(request, sampleids, assetType)

def publish_datafiles(request, dfids=None):
    assetType = 'Datafile'
    return publish_assets(request, dfids, assetType)

def publish_sops(request, sopids=None):
    assetType = 'Sop'
    return publish_assets(request, sopids, assetType)
    
def publish(request):
    """
    callback to "/seek/publish/" for publishing assets to another Seek system.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/publish/'
        return HttpResponseRedirect(url_redirect)
    
    # user associated projectname
    project_title = user_seek['projectname']
    
    # get investigations under a project in {'id1':'title1', 'id2':'title2', ...}
    investigations = seekdb.getInvestigations(project_title)
    investigation_options = json.dumps(convertDicToOptions(investigations))
    
    report = {}
    report['investigation_options'] = investigation_options
    report['showSamplePage'] = True
    report['showSearch'] = True
    return render(request,"publish.html", {'report':report})
    
    
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/publish/'
        return HttpResponseRedirect(url_redirect)
    
    #report = {}
    #return render(request,"publish.html", {'report':report})
    username = user_seek['username']
    password = user_seek['password']
    
    if request.POST.get('inv') is not None:
        investigation = request.POST.get('inv')
    else:
        investigation = ""
            
    storage = settings.SEEK_URL
    virtuoso = settings.VIRTUOSO_JS_URL
    server = user_seek['server']
    
    investigations,folders = seekdb.get_investigations_folders(investigation)
    '''
    try:
        if request.method == "POST":
            #gusername, workflows, his, dbkeys = get_galaxy_info(
            galaxyapi = GalaxyAPI(
                request.POST.get('server'),
                request.POST.get('galaxyemail'),
                request.POST.get("galaxypass")
            )
            gusername, workflows, his, dbkeys = galaxyapi.get_galaxy_info()
        else:
            #gusername, workflows, his, dbkeys = get_galaxy_info(
            galaxyapi = GalaxyAPI(
                request.session.get('server'),
                request.session.get('galaxyemail'),
                request.session.get("galaxypass")
            )
            gusername, workflows, his, dbkeys = galaxyapi.get_galaxy_info()
    except Exception:
        request.session.flush()
        return render_to_response('publish.html', context={
            'error': 'Credentials incorrect. Please try again'})
    '''
    return render(
        request, "publish.html",
        context={'username': username,
            'password': password, 'server': server,
            'storage': storage,
            'storagetype': user_seek['storagetype'],
            'virtuoso_url': virtuoso,
            'investigations': investigations,
            'studies': folders,
            'inv': investigation
            }
    )
    
    
def getStudiesOptions(request, id):
    """ Get a list of studies for an investigation id.
    Input:
        id, investigation id.
    """    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    investigation_id = id
    studies = seekdb.getStudiesFromID(investigation_id)
    #print(studies)
    #study_options = json.dumps(convertDicToOptions(studies))
    study_options = convertDicToOptions(studies)
    #print(study_options)
    data = {'msg':'okay', 'status': 1, 'study_options':study_options}
    return HttpResponse(simplejson.dumps(data))
    
def getAssaysOptions(request, id):
    """ Get a list of assays for an study id.
    Input:
        id, study id.
    """    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    study_id = id
    assays = seekdb.getAssaysFromID(study_id)
    assay_options = convertDicToOptions(assays)
    data = {'msg':'okay', 'status': 1, 'assay_options':assay_options}
    return HttpResponse(simplejson.dumps(data))
    
def publishSearching(request):
    """
    Searching the list of assets for publish.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    ret = request.GET
    #investigation_id = ret['investigation_id']
    #study_id = ret['study_id']
    assay_id = ret['assay_id']
    investigation = ret['investigation']
    study = ret['study']
    assay = ret['assay']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    #dbsample = DBtable_sample()
    #sdata = dbsample.searchSamples(user_seek, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
    
    diclist = seekdb.getAssayDFs(assay_id, investigation, study, assay)
    #print("results:", diclist)
    data = {}
    data['rows'] = diclist
    data['total'] = len(diclist)
    data['msg'] = 'okay'
    data['status'] = 1 
    sdata = simplejson.dumps(data)
    return HttpResponse(sdata)    
    
def publishAssets(request):
    """
        Called in templates/pages/pulish_stable.embed.html.
        Download an ISA assets in a package and then publish it to a remote server.

    Arguments:
        request: Getting the list of sample ids.
    """
    ret = request.GET
    project = ret['project']
    investigation = ret['investigation']
    study = ret['study']
    assay = ret['assay']
    project_id = ret['project_id']
    investigation_id = ret['investigation_id']
    study_id = ret['study_id']
    assay_id = ret['assay_id']
    allids = ret['allids']
    #print(allids)
    df_ids = json.loads(allids)
    ids = df_ids
    
    assettypes = ret['assettypes']
    types = json.loads(assettypes)
    
    seekdb = SeekDB(None, None, None)
    
    iddic = {}
    for i, type in enumerate(types):
        if type in iddic:
            idlist = iddic[type]
        else:
            idlist = []
            
        id = ids[i]
        idlist.append(id)
        iddic[type] = idlist
        
    for type in iddic:
        if type=='Sample':
            sample_ids = iddic[type]
            user_seek = seekdb.getSeekLogin(request, False)
            return publishSamples(user_seek, sample_ids, assay_id, project_id)
        elif type.upper()=='SOP':
            user_seek = seekdb.getSeekLogin(request)
            sdb, user = __definePublishServer(seekdb, user_seek)
            sop_ids = iddic[type]
            dbsop = DBtable_sops("DEFAULT")
            sdata = dbsop.publishSOPs(user_seek, sdb, user, sop_ids, assay_id, project_id)
            return HttpResponse(sdata)
        elif type=='Datafile':
            user_seek = seekdb.getSeekLogin(request)
            sdb, user = __definePublishServer(seekdb, user_seek)
            df_ids = iddic[type]
            dbdf = DBtable_data_files("DEFAULT")
            sdata = dbdf.publishDFs(user_seek, sdb, user, df_ids, assay_id, project_id)
            return HttpResponse(sdata)
    
    return None
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    #source_json, isa_structure = seekdb.downloadAssets(int(study_id), "studies")
    #print("result:", source_json, isa_structure)
    
    # try upload
    userid = seekdb.user_seek['user_id']
    projectid = seekdb.user_seek['projectid']
    
    title = 'test_study_upload1'
    description = ""
    studyname = title
    seekdb.createStudy(userid, projectid, investigation_id, title, description, studyname)
    
    remoteServer = "https://kibcc2.mit.edu"
    seekdb_remote = SeekDB(remoteServer , seekdb.user_seek['username'], seekdb.user_seek['password'])
    #study_id = 1
    #source_json_r, isa_structure_r = seekdb_remote.downloadAssets(int(study_id), "studies")
    #print("result_remote:", source_json_r, isa_structure_r)
    #seekdb_remote.uploadAssets(seekdb, source_json, isa_structure)
    
    
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'download-samples-' + datenow + '.xls'
     #filename = 'samples_upload_feedback.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    #sdata = dbsample.downloadSamples(user_seek, downloadfile, link, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
    sdata = dbsample.downloadSamples_new(user_seek, downloadfile, link, df_ids)
    return HttpResponse(sdata)
    
def sampleAttributes(request):
    """
    callback to "/samples/attributes/" for showing the page on revision of sample attributes.
    """
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/samples/attributes/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    sampletype_id = 0
    #report['type_options'] = stype.getComboboxOptions(sampletype_id, 'title')
    report['type_options'] = stype.getSampleTypes()
    #print "okay", report['type_options']
    report['showSamplePage'] = True
    report['showSearch'] = True
    #report['bodyhtml'] = stype.getSamplePage(sampletype_id, user_seek['server'], user_seek['username'], user_seek['password'])
    
    attritype = DBtable_attributetype()
    report['attribute_types_options'] = attritype.getAttributeTypeOptions() 
        
    return render(request,"sampleAttributes.html", {'report':report})
    
def getSampleType(request):
    """
    Retrieve the definition of sample type.

    Arguments:
        request: Getting the information needed to search the SEEK ISA structure.
    """
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    dbsample = DBtable_sample()
    sdata = dbsample.getSampleType(user_seek, sampletype_id, attribute)
    return HttpResponse(sdata)
    
def verifySuperUser(request):
    print request.user
    username = request.user
    if request.user.is_authenticated():
        # Do something for authenticated users.
        print("User is authenticated.")
        try:
            user = User.objects.get(username=username)
            #print user.is_staff
            #print user.is_active
            if user.is_superuser:
                return 1
            else:
                return 0
        except User.DoesNotExist:
            print("User does not exist.")
            #return HttpResponseRedirect("/denied/")
            return 0
    else:
        # Do something for anonymous users.
        print("User is not authenticated.")
        #return HttpResponseRedirect("/denied/")
        return 0
    return 0    
    
def sampleAttributeSave(request):
    ''' Callback for saving a record of sample attribute.
    '''
    #print("sampleAttributeSave")
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        print(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data))
        
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        err = 'The login user does not have the permission to add the sample attribute.'
        print(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data))
    
    ret = request.GET
    #print(ret)
    sampletype_id = ret['sampletype_id']
    #print(sampletype_id)
    records = ret['records']
    diclist = json.loads(records)
    #print(diclist)
    
    
    sampleattr = DBtable_sampleattribute()
    attri_renamed = sampleattr.getAttributesRenamed(sampletype_id, diclist)
    
    '''
    print(attri_renamed)
    for record in diclist:
        #print(record)
        record_new = sampleattr.reformatRecordForDB(user_seek, record)
    msg = "Error: Saving an attribute not available yet."
    status = 0
    link = " "
    data = {'msg':msg, 'status': status, 'link': link}
    reportData = simplejson.dumps(data)
    return HttpResponse(reportData)
    '''
    
    reportData = sampleattr.processRecords(request, user_seek, "save")
    data = json.loads(reportData)
    if data['status']==1:
        dbsample = DBtable_sample()
        reportData = dbsample.updateSampleType(user_seek, sampletype_id, attri_renamed)
    
    return HttpResponse(reportData)
    
    #dgtable = DataGrid(alumni)
    #return dgtable.process(request, operation) 
    
def sampleAttributeDelete(request):
    ''' Callback for deleting a record of sample attribute.
    '''
    print("sampleAttributeDelete")
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    #print("user info", user_seek)
    if not user_seek['status']:
        err = user_seek['err']
        print(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data))
        
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        err = 'The login user does not have the permission to delete the sample attribute.'
        print(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data))
    
    #attritype = DBtable_attributetype()
    #return attritype.process(request, "delete")
    '''
    msg = "Error: Deleting an attribute not implelemented yet."
    status = 0
    link = " "
    data = {'msg':msg, 'status': status, 'link': link}
    #print data
    reportData = simplejson.dumps(data)
    '''
    sampleattr = DBtable_sampleattribute()
    reportData = sampleattr.processRecords(request, user_seek, "delete")
    return HttpResponse(reportData)