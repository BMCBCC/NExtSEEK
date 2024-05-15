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
import random

import logging
logger = logging.getLogger(__name__)

from subprocess import call
from subprocess import check_call
from time import strftime, gmtime

from django.conf import settings
from django.core.files.storage import default_storage
from django.shortcuts import render, HttpResponseRedirect, redirect, HttpResponse
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

from rest_framework.decorators import authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from subprocess import call

import shlex
from subprocess import Popen, PIPE

from django.conf import settings
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "/download/"
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + 'download/'  
UPLOAD_DIRECTORY = settings.MEDIA_ROOT + "/uploads/"
SEEK_DATAFILE_ROOT = settings.SEEK_DATAFILE_ROOT
DROPBOX_DIRECTORY = settings.MEDIA_ROOT + "/dropbox/"

SAMPLE_TEMPLATE_FILE = settings.MEDIA_ROOT + "/reserved/SAMPLE_TEMPLATE.xlsx"

PUBLISH_SERVER = settings.PUBLISH_URL

report = {}
def seek(request, url):
    report = {}
    if request.method == 'POST':
        bodyhtml = "To be implemented"
        return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    else:
        url = "/" + url.replace("-", "/") + "/"
        bodyhtml = getPageRequests(url)
        report = {}
        report['bodyhtml'] = bodyhtml
        return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    
def getSeekPage(request, seek_url):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/'
        return HttpResponseRedirect(url_redirect)
        
    bodyhtml = seekdb.getPageRequests(seek_url)
    report = {}
    report['bodyhtml'] = bodyhtml
    return render(request,"samples.html", {'bodyhtml' : bodyhtml})
    
def sample(request, id):
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
    
    seek_url = "/samples/" + str(id) + "/"
    bodyhtml = seekdb.getPageRequests(seek_url)
    
    report = {}
    report['bodyhtml'] = bodyhtml
    report['sample_id'] = sample_id
    dbsample = DBtable_sample()
    report['treeData_multiparents'] = dbsample.createSampleMultiParentTree(sample_id)
    sampledic, samplelist = dbsample.getSampleInfo(sample_id)
    report['sampledic'] = sampledic
    report['sampleinfo'] = samplelist
    return render(request,"samples.html", {'bodyhtml' : bodyhtml, 'report':report})

def sampleTree(request, uid):
    sample_uid = uid
    dbsample = DBtable_sample()
    sample_id = dbsample.getSampleID(sample_uid)
    return sample(request, sample_id)

def document(request, id):
    document_id = id
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data, default=str)) 
    
    seekdoc = DBtable_documents("DEFAULT")
    docurl, filename = seekdoc.getDownloadURL(document_id,
                user_seek['server'],
                user_seek['username'],
                user_seek['password'])
    
    if docurl is None:
        msg = 'Sample template is not available. Choose a template from the list.'
        status = 0
        docurl = ''
    else:
        msg = 'Sample template is downloaded in ' + filename
        status = 1
    data = {'msg':msg, 'status': status, 'link':docurl}
    return HttpResponse(simplejson.dumps(data, default=str))   

def sampleUpload(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/samples/upload/")
        
    report = {}
    docs = DBtable_documents()
    report['template_options'] = docs.getOptionsDocuments(0, "Sample Sheet Template")
    
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        options = []
        options.append({'id':-1, 'title':'Default','selected':True})
    else:
        options = seekdb.getObjectsToOptions("/institutions")
    report['lab_options'] = json.dumps(options, default=str)
    
    return render(request,"sampleUpload.html", {'report':report})
    
def sampleUploadAjax(request):
    username = str(request.user)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    msg = "Error: File not valid"
    message = ''
    status = 0
    data = {'msg':msg, 'status': status, 'link':''}
    if request.method == "POST":
        if request.FILES and request.FILES.get('excelfile_upload'):
            excelfile = request.FILES['excelfile_upload']
            if excelfile:
                instituion_id = request.POST.get('instituion_id')
                creator_id = request.POST.get('people_id')
                if verifySuperUser(request)==1 and int(creator_id)>0:
                    status, msg = seekdb.updateCreator(instituion_id, creator_id)
                    if not status:
                        data = {'msg':msg, 'status': status, 'link':''}
                        return HttpResponse(simplejson.dumps(data, default=str))
                
                inputfile = excelfile.name
                names = inputfile.split(".")
                n = len(names)
                
                datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                filename = '.'.join(names[:(n-1)]) + '_feedback-' + datenow + '.xls'
                feedbackfile = DOWNLOAD_DIRECTORY + filename
                link = DOWNLOAD_DIRECTORY_LINK + filename
                
                backupfile = '.'.join(names[:(n-1)]) + '_v' + datenow + '.' + names[-1]
                backupfile = UPLOAD_DIRECTORY + backupfile
                handle_uploaded_file(excelfile, backupfile)
                
                sample = DBtable_sample()
                msgi, status = sample.batchUpload(excelfile, feedbackfile, seekdb)
                if status:
                    msg = 'Batch sample uploading successful. To find the UIDs for samples uploaded, refer to the feedback excel file: ' + filename
                    message = msg + '\n\n' + msgi
                else:
                    message = msgi
                    
                    terms = msgi.split("<")
                    msg = terms[0] + "<br/><br/>"
                    msg += "Refer to the log and the excel file: " + filename + '.<br/>'
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
                
    if message is not None and '<br/>' in message:
        data['message'] = message.replace('<br/>', '\n')
    else:
        data['message'] = message
                
    return HttpResponse(simplejson.dumps(data, default=str))       

        
    
def sampleQuery(request):
    return sample_type(request, 0)
        
def sample_type(request, id):
    sampletype_id = int(id)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        if sampletype_id==0:
            url_redirect = '/login/?next=/seek/samples/query/'
        else:
            url_redirect = '/login/?next=/seek/sample_types/id=' + str(sampletype_id) + '/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    report['type_options'] = stype.getComboboxOptions(sampletype_id, 'title')
    if sampletype_id==0:
        report['showSamplePage'] = True
        report['showSearch'] = True
        report['bodyhtml'] = '<div></div>'
    else:
        report['showSamplePage'] = True
        report['showSearch'] = True
        report['bodyhtml'] = stype.getSamplePage(sampletype_id, user_seek['server'], user_seek['username'], user_seek['password'])
        
    return render(request,"sampleQuery.html", {'bodyhtml' : report['bodyhtml'], 'report':report})

def getAttributes(request, id):
    sampletype_id = int(id)
    valueSelected = ''
    ret = request.GET
    if 'valueSelected' in ret:
        valueSelected = ret['valueSelected']
    
    sattr = DBtable_sampleattribute()
    data = sattr.getAttributes(sampletype_id, valueSelected)
    return HttpResponse(simplejson.dumps(data, default=str))

def getOperators(request):
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    
    sattr = DBtable_sampleattribute()
    data = sattr.getOperators(sampletype_id, attribute)
    return HttpResponse(simplejson.dumps(data, default=str))


def sampleSearch(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/samples/search/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    sampletype_id = 0
    report['type_options'] = stype.getSampleTypes()
    report['showSamplePage'] = True
    report['showSearch'] = True
    return render(request,"sampleSearch.html", {'report':report})

def __searchFilterKeywords(keywords):
    kkk = keywords.strip()
    if len(kkk)==0:
        uids = []
        return uids
    
    keywords = keywords.replace(" ",",")    
    uids = keywords.split(",")
    return uids

    
def sampleSearching(request):
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    filter_rule = ret['filter_rule']
    filter_valueFrom = ret['filter_valueFrom']
    filter_valueTo = ret['filter_valueTo']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, True)
    
    dbsample = DBtable_sample()
    sdata = dbsample.searchSamples(user_seek, sampletype_id, attribute, filter_rule, filter_valueFrom, filter_valueTo)
    return HttpResponse(sdata)

#@csrf_exempt
def remote(request):
    return samples(request)

def datafileUpload(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
            
    report = {}
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        options = []
        options.append({'id':-1, 'title':'Default','selected':True})
    else:
        options = seekdb.getObjectsToOptions("/institutions")
    
    report['lab_options'] = json.dumps(options, default=str)
    return render(request,"datafileUpload.html", {'report':report})

def __updateLabUser(seekdb, instituion_id, people_id):
    return seekdb

def filesBatchUpload(request):
    filetype = request.POST.get('filetype')
    instituion_id = request.POST.get('instituion_id')
    people_id = request.POST.get('people_id')
    md5 = request.POST.get('md5')
    report = {}
    report['msg'] = "Warning: tStart batch file uploading."
    report['status'] = 0
    report['df_info'] = {}            
    report['newrow'] = {} 
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        report['msg'] = user_seek['err']
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
        
    if verifySuperUser(request)==1 and int(people_id)>0:
        status, msg = seekdb.updateCreator(instituion_id, people_id)
        if not status:
            report['msg'] = msg
            return HttpResponse(simplejson.dumps(report, default=str))
        
    infile = request.FILES['file']
    dfrecord = {}
    dfrecord['uid'] = ''
    dfrecord['originalname'] = infile.name
    dfrecord['fileurl'] = 'Not available ' + settings.SEEK_DATAFILE_SERVER
    dfrecord['notes'] = report['msg']
    dfrecord['content_type'] = filetype
    
    sampleRecord = None
    if filetype=="DATAFILE":
        dbsample = DBtable_sample()
        creator = seekdb.creator
        sampleRecord, msg = dbsample.searchFileInSample(creator, infile.name, filetype)
        if sampleRecord is None or sampleRecord['id']<=0:
            report['msg'] = msg
            report['status'] = 0
            dfrecord['notes'] = report['msg']
            report['newrow'] = dfrecord
            return HttpResponse(simplejson.dumps(report, default=str))

    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        sample_uid = sampleRecord['uuid']
        report = dbdf.uploadDF_toStorage(seekdb.creator, infile, sample_uid, md5)
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        report = dbsop.uploadSOP_toStorage(seekdb.creator, infile, md5)
    else:
        report = {}
        report['msg'] = "Warning: the file type is not supported yet: " + filetype
        report['status'] = 0
        report['df_info'] = {}            
        report['newrow'] = {}              
    
    return HttpResponse(simplejson.dumps(report, default=str))
    
    
def uploadToSeek(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        return HttpResponseRedirect("/login/?next=/seek/data/upload/")
    
    ret = request.POST
    filetype = ret['filetype']
    instituion_id = ret['instituion_id']
    people_id = ret['people_id']
    records = ret['records']
    diclist = json.loads(records)
        
    report = {}
    report['msg'] = "Warning: to be implemented"
    report['status'] = 0
    report['link'] = ""
    report['newrow'] = {}               
    if verifySuperUser(request)==1 and int(people_id)>0:
        status, msg = seekdb.updateCreator(instituion_id, people_id)
        if not status:
            report['msg'] = msg
            return HttpResponse(simplejson.dumps(report, default=str))
    
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        report = dbdf.uploadDFs_storageToSeek(seekdb, diclist)
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        report = dbsop.uploadSOPs_storageToSeek(seekdb, diclist)
        
    else:
        report = {}
        report['msg'] = "Warning: the file type is not supported yet: " + filetype
        report['status'] = 0
        report['df_info'] = {}            
        report['newrow'] = {}              
    
    return HttpResponse(simplejson.dumps(report, default=str))

def filesGetUIDs(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    ret = request.GET
    allFiles = json.loads(ret['allfiles'])
    dbdf = DBtable_data_files("DEFAULT")
    data = dbdf.filesGetUIDs(seekdb, allFiles)
    return HttpResponse(simplejson.dumps(data, default=str))

def sopDownload(request, uid):
    return fileDownload(request, uid, "SOP")


#@api_view(http_method_names=['GET'])
#@authentication_classes((TokenAuthentication,))
#@permission_classes((IsAuthenticated,))
def datafileDownload(request, uid):
    return fileDownload(request, uid, "DATAFILE")
    
def fileDownloadEncoded(request, url_redirect, fileInfo):
    if url_redirect is not None:
        option = 1
        terms = url_redirect.split("/")
        filename = terms[-1]
    elif fileInfo is not None:
        option = 4
    else:
        option = 1
        
    if option==1:
        HttpResponseRedirect(url_redirect)
    elif option==2:
        #https://stackoverflow.com/questions/1156246/having-django-serve-downloadable-files
        from django.utils.encoding import smart_str
        
        file_path = fileInfo['fullfilename']
        file_name = fileInfo['originalfilename']
        
        response = HttpResponse(content_type='application/force-download')
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_name)
        response['X-Sendfile'] = smart_str(file_path)
        return response
    elif option==3:
        from django.views.static import serve
        file_path = fileInfo['fullfilename']
        file_name = fileInfo['originalfilename']
        return serve(request, os.path.basename(file_path), os.path.dirname(file_path))
    elif option==4:
        # https://stackoverflow.com/questions/61351609/how-to-allow-users-to-directly-download-a-file-stored-in-my-media-folder-in-djan
        from django.utils.encoding import smart_str
        import mimetypes
        from wsgiref.util import FileWrapper
        
        file_path = fileInfo['fullfilename']
        file_name = fileInfo['originalfilename']
        
        file_wrapper = FileWrapper(file(file_path,'rb'))
        file_mimetype = mimetypes.guess_type(file_path)
        response = HttpResponse(file_wrapper, content_type=file_mimetype )
        response['X-Sendfile'] = file_path
        response['Content-Length'] = os.stat(file_path).st_size
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str(file_name) 
        return response
    else:
        HttpResponseRedirect(url_redirect)
        
    HttpResponseRedirect(url_redirect)
    
    
#@api_view(http_method_names=['GET'])
#@authentication_classes((TokenAuthentication,))
#@permission_classes((IsAuthenticated,))
def verifyToken(request):
    from rest_framework.authentication import TokenAuthentication
    user_auth_tuple = TokenAuthentication().authenticate(request)
    tokenValidated = False
    if user_auth_tuple is None:
        tokenValidated = False
    else:
        (user, token) = user_auth_tuple 
        tokenValidated = True
    
    return tokenValidated
    
    
def fileDownload(request, uid, filetype):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        logger.error(err)
        if filetype=="DATAFILE":
            url_redirect = '/login/?next=/seek/datafiles/uid=' + uid + '/'
        elif filetype=="SOP":
            url_redirect = '/login/?next=/seek/sop/uid=' + uid + '/'
        else:
            url_redirect = '/login/'
        
        isokay = request.user.is_authenticated
        isTokenAuthenticated = verifyToken(request)
        if not isTokenAuthenticated:
            msg = "Login error: not token authenticated."
            logger.error(msg)
            return HttpResponseRedirect(url_redirect)
    
    url_redirect = None
    fileInfo = None
    if filetype=="DATAFILE":
        dbdf = DBtable_data_files("DEFAULT")
        msg, status, fileInfo = dbdf.downloadDF_fromStorage(user_seek, uid)
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        msg, status, fileInfo = dbsop.downloadSOP_fromStorage(user_seek, uid)
    else:
        msg = 'Error: file type not supported.'
        status = 0
        
    if status==1:
        if filetype=="DATAFILE":
            return fileDownloadEncoded(request, url_redirect, fileInfo)
        elif filetype=="SOP":
            return fileDownloadEncoded(request, url_redirect, fileInfo)
        else:
            return HttpResponseRedirect(url_redirect)
    else:
        return render(request, 'pages/404.html')
    return HttpResponse("You're downloading file %s." % uid)
 
def fileQuery(request, filetype):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
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
        report['batchpublish_url'] = '/seek/datafiles/publish/'
    elif filetype=="SOP":
        dbsop = DBtable_sops("DEFAULT")
        form, report = dbsop.formInfo(request, pk)
        report['table_url'] = '/seek/retrieve/sops/'
        report['batchdownload_url'] = '/seek/batchdownload/sops/'
        report['batchpublish_url'] = '/seek/sops/publish/'
    else:
        msg = 'Error: file type not supported.'
        status = 0
        report = {}
        form= None
    
    return render(request,"batchSearch.html", {"report" : report, "form": form})

def datafileQuery(request):
    return fileQuery(request, "DATAFILE") 
    
def sopQuery(request):
    return fileQuery(request, "SOP") 
    
def filelist(request, filetype):
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
    args = shlex.split(cmd)
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate()
    exitcode = proc.returncode
    return exitcode, out, err    
    
def __getDropBoxFolders(user_seek, ifMkdir=True):
    username = user_seek['username']
    projectname = user_seek['projectname']
    institutionname = user_seek['institutionname']
    lababbv = user_seek['lababbv']
    labfolder = lababbv
            
    upload_dropbox_path_labroot = os.path.join(DROPBOX_DIRECTORY, labfolder)
    if not os.path.exists(upload_dropbox_path_labroot) and ifMkdir:
        os.makedirs(upload_dropbox_path_labroot)
        
    projectfolder = projectname
    if " " in projectname:
        projectfolder = projectname.replace(" ", "_")
            
    upload_dropbox_path_projectroot = os.path.join(upload_dropbox_path_labroot, projectfolder)
    if not os.path.exists(upload_dropbox_path_projectroot) and ifMkdir:
        os.makedirs(upload_dropbox_path_projectroot)
        
    upload_dropbox_path = upload_dropbox_path_projectroot
    dropbox_datafile_folder = os.path.join(upload_dropbox_path, 'for_datafiles')
    if not os.path.exists(dropbox_datafile_folder) and ifMkdir:
        os.makedirs(dropbox_datafile_folder)
    
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
    cmd = 'seek/dropbox.py sharelink ' + readmefile
    exitcode, out, err = callCmdline(cmd)
    if exitcode==0:
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

    cmd = 'seek/dropbox.py ls ' + dropbox_datafile_folder
    exitcode, out, err = callCmdline(cmd)
    if exitcode==0:
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
            msg += file + '\n'
    
    return HttpResponse(msg)
    
def retrieveSamples(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    dbsample = DBtable_sample()
    reportData = dbsample.processRecords(request, user_seek, "retrieve")
    return HttpResponse(reportData) 

def sampleDownload(request):
    if request.method == "POST":
        ret = request.POST
    else:
        ret = request.GET
        
    includeSampleTree = int(ret['includeSampleTree'])
    if 'attributeFilter' in ret:
        attributeFilter = ret['attributeFilter']
    else:
        attributeFilter = None
    
    allids = ret['allids']
    sampletype_id = ret['sampletype_id']
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'download-samples-' + datenow + '.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sampleTypes = dbsample.parseSampleIDs(sample_ids)
    if len(sampleTypes)==1:
        sdata = dbsample.downloadSamples_new(user_seek, downloadfile, link, sample_ids, includeSampleTree, attributeFilter)
    else:
        linkfile = link.replace('.xls', '.zip')
        dzipfile = downloadfile.replace('.xls', '.zip')
        zf = zipfile.ZipFile(dzipfile, mode='w')
        for sampleType in sampleTypes:
            suffix = '-' + sampleType + '.xls'
            downfilei = downloadfile.replace('.xls', suffix)
            filenamei = filename.replace('.xls', suffix)
            ids = sampleTypes[sampleType]
            sdata = dbsample.downloadSamples_new(user_seek, downfilei, linkfile, ids, includeSampleTree, attributeFilter)
            zf.write(downfilei, filenamei)
    
    return HttpResponse(sdata)    

def sampleExport(request):
    if request.method == "POST":
        ret = request.POST
    else:
        ret = request.GET
    
    allids = ret['allids']
    sampletype_id = ret['sampletype_id']
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-export' + datenow + '.xlsx'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sdata = dbsample.exportSamples(user_seek, downloadfile, link, sample_ids, sampletype_id)
    return HttpResponse(sdata)   

def sampleFindAjax(request):
    username = str(request.user)
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    msg = "Error: File not valid"
    message = ''
    status = 0
    data = {'msg':msg, 'status': status, 'link':''}
    if request.method == "POST":
        if request.FILES and request.FILES.get('excelfile_find'):
            excelfile = request.FILES['excelfile_find']
            if excelfile:
                inputfile = excelfile.name
                names = inputfile.split(".")
                n = len(names)
                
                datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                filename = 'samples-export' + datenow + '.zip'
                downloadfile = DOWNLOAD_DIRECTORY + filename
                link = DOWNLOAD_DIRECTORY_LINK + filename
                
                dbsample = DBtable_sample()
                sdata = dbsample.findSamplesForExport(user_seek, downloadfile, link, excelfile)
                return HttpResponse(sdata)
            else:
                message = 'Error: Not a valid file from client side'
                data = {'msg':message, 'status': 0, 'link':''}
        else:
            message = 'Error: Not a valid file from client side'
            data = {'msg':message, 'status': 0, 'link':''}
    else:
        message = 'Error: Not a valid http POST request'
        data = {'msg':message, 'status': 0, 'link':''}
                
    if message is not None and '<br/>' in message:
        data['message'] = message.replace('<br/>', '\n')
    else:
        data['message'] = message
                
    return HttpResponse(simplejson.dumps(data, default=str))   

    
def sampleDelete(request):
    ret = request.GET
    allids = ret['allids']
    sample_ids = json.loads(allids)
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-deletion' + datenow + '.xls'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    dbsample = DBtable_sample()
    sdata = dbsample.deleteSamples(user_seek, downloadfile, link, sample_ids)
    return HttpResponse(sdata)
    
def publishSamples(user_seek, sample_ids, assay_id=None, project_id=None):
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-publish' + datenow + '.xlsx'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    templatefile = SAMPLE_TEMPLATE_FILE
    cmd = 'cp ' + templatefile + ' ' + downloadfile
    os.system(cmd)
    
    dbsample = DBtable_sample()
    sdata = dbsample.publishSamples(user_seek, downloadfile, link, sample_ids, assay_id, project_id)
    return HttpResponse(sdata)
    
def __definePublishServer(seekdb, user_seek):
    username = user_seek['username']
    password = user_seek['password']
    person_id = user_seek['person_id']
    fullname = seekdb.getUserFullname(person_id)
    server = PUBLISH_SERVER
    sdb = SeekDB(server, username, password)
    user = sdb.updateUserProfile(fullname)
    return sdb, user
    
    
def __getISA(seekdb, user_seek, whichServer):
    if whichServer=="SOURCE":
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
    ret = request.POST
    if 'allids' in ret:
        allids = ret['allids']
        sample_ids = json.loads(allids)
    else:
        sample_ids = []
        
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    datenow = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = 'samples-publish' + datenow + '.xlsx'
    downloadfile = DOWNLOAD_DIRECTORY + filename
    link = DOWNLOAD_DIRECTORY_LINK + filename
    
    templatefile = SAMPLE_TEMPLATE_FILE
    cmd = 'cp ' + templatefile + ' ' + downloadfile
    os.system(cmd)
    
    project_options, investigation_options_dic, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    
    report = {}
    report['project_options'] = project_options
    report['investigation_options_dic'] = investigation_options_dic
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
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/publish/'
        return HttpResponseRedirect(url_redirect)
    
    project_options, investigation_options_dic, study_options_dic, assay_options_dic, server = __getISA(seekdb, user_seek, "DESTINATION")
    
    report = {}
    report['project_options'] = project_options
    report['investigation_options_dic'] = investigation_options_dic
    report['study_options_dic'] = study_options_dic
    report['assay_options_dic'] = assay_options_dic
    report['showSamplePage'] = True
    report['showSearch'] = True
    report['assetData'] = diclist
    report['publish_server'] = server
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
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/publish/'
        return HttpResponseRedirect(url_redirect)
    
    project_title = user_seek['projectname']
    investigations = seekdb.getInvestigations(project_title)
    investigation_options = json.dumps(convertDicToOptions(investigations), default=str)
    
    report = {}
    report['investigation_options'] = investigation_options
    report['showSamplePage'] = True
    report['showSearch'] = True
    return render(request,"publish.html", {'report':report})
    
def getStudiesOptions(request, id):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    investigation_id = id
    studies = seekdb.getStudiesFromID(investigation_id)
    study_options = convertDicToOptions(studies)
    data = {'msg':'okay', 'status': 1, 'study_options':study_options}
    return HttpResponse(simplejson.dumps(data, default=str))
    
def getAssaysOptions(request, id):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    study_id = id
    assays = seekdb.getAssaysFromID(study_id)
    assay_options = convertDicToOptions(assays)
    data = {'msg':'okay', 'status': 1, 'assay_options':assay_options}
    return HttpResponse(simplejson.dumps(data, default=str))
    
def publishSearching(request):
    ret = request.GET
    assay_id = ret['assay_id']
    investigation = ret['investigation']
    study = ret['study']
    assay = ret['assay']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    diclist = seekdb.getAssayDFs(assay_id, investigation, study, assay)
    data = {}
    data['rows'] = diclist
    data['total'] = len(diclist)
    data['msg'] = 'okay'
    data['status'] = 1 
    sdata = simplejson.dumps(data, default=str)
    return HttpResponse(sdata)    
    
def publishAssets(request):
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
    
def sampleAttributes(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/samples/attributes/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    sampletype_id = 0
    report['type_options'] = stype.getSampleTypes()
    report['showSamplePage'] = True
    report['showSearch'] = True
    attritype = DBtable_attributetype()
    report['attribute_types_options'] = attritype.getAttributeTypeOptions()         
    return render(request,"sampleAttributes.html", {'report':report})
    
def getSampleType(request):
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    dbsample = DBtable_sample()
    sdata = dbsample.getSampleType(user_seek, sampletype_id, attribute)
    return HttpResponse(sdata)
    
def verifySuperUser(request):
    username = request.user
    if request.user.is_authenticated:
        try:
            user = User.objects.get(username=username)
            if user.is_superuser:
                return 1
            else:
                return 0
        except User.DoesNotExist:
            return 0
    else:
        return 0
    return 0    
    
def sampleAttributeSave(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data, default=str))
        
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        err = 'The login user does not have the permission to add the sample attribute.'
        logger.error(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data, default=str))
    
    ret = request.GET
    sampletype_id = ret['sampletype_id']
    records = ret['records']
    diclist = json.loads(records)
    
    sampleattr = DBtable_sampleattribute()
    attri_renamed = sampleattr.getAttributesRenamed(sampletype_id, diclist)
    reportData = sampleattr.processRecords(request, user_seek, "save")
    data = json.loads(reportData)
    if data['status']==1:
        dbsample = DBtable_sample()
        reportData = dbsample.updateSampleType(user_seek, sampletype_id, attri_renamed)
    
    return HttpResponse(reportData)
    
def sampleAttributeDelete(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        logger.error(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data, default=str))
        
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        err = 'The login user does not have the permission to delete the sample attribute.'
        logger.error(err)
        msg = err
        status = 0
        docurl = ''
        data = {'msg':msg, 'status': status, 'link':docurl}
        return HttpResponse(simplejson.dumps(data, default=str))
    
    sampleattr = DBtable_sampleattribute()
    reportData = sampleattr.processRecords(request, user_seek, "delete")
    return HttpResponse(reportData)
    
    
def getInstituionUsers(request, id):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    
    instituion_id = int(id)
    valueSelected = ''
    ret = request.GET
    if 'valueSelected' in ret:
        valueSelected = ret['valueSelected']
        
    options = []
    status = 0
    msg = 'No user not available'
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0: 
        options.append({'id':-1, 'title':'Default','selected':True})
    else:
        objects = seekdb.getInfoObject("/institutions/", instituion_id)
        try:
            people = objects["relationships"]["people"]["data"]
            for dici in people:
                id = dici['id']
                title = seekdb.getUserFullname(id)
                options += [{'id':id, 'title':title}]
            status = 1
            msg = 'okay'
        except:
            options.append({'id':0, 'title':'','selected':True})
            status = 0
            msg = 'No user is found for the lab'
    
    data = {'msg':msg, 'status': status, 'userOptions':options}
    return HttpResponse(simplejson.dumps(data, default=str))   
        
def searchAdvanced(request):
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, False)
    if not user_seek['status']:
        err = user_seek['err']
        url_redirect = '/login/?next=/seek/search/'
        return HttpResponseRedirect(url_redirect)
    
    report = {}
    stype = DBtable_sampletype()
    sampletype_id = 0
    report['type_options'] = stype.getSampleTypes()
    report['showSamplePage'] = True
    report['showSearch'] = True        
    return render(request,"searchAdvanced.html", {'report':report})
    
def searchingAdvanced(request):
    ret = request.GET
    filters = ret
    
    sampletype_id = ret['sampletype_id']
    attribute = ret['attribute']
    filter_logic = ret['filter_logic']
    filter_searchValue = ret['filter_searchValue']
    filter_searchText = ret['filter_searchText']
    filter_matchType = ret['filter_matchType']
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, True)
    isSupervisor = verifySuperUser(request)
    if isSupervisor==0:
        project_id = user_seek['projectid']
    else:
        project_id = 0
    
    dbsample = DBtable_sample()    
    searchType = "Advanced"
    sdata = dbsample.searchAdvanced(user_seek, filters, searchType, project_id)
    return HttpResponse(sdata)
    
def searchingUIDs(request):
    ret = request.GET
    filters = ret
    
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request, True)
    
    dbsample = DBtable_sample()
    searchType = "UIDs"
    sdata = dbsample.searchAdvanced(user_seek, filters, searchType)
    return HttpResponse(sdata)

    
