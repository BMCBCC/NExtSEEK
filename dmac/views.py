from django.shortcuts import redirect, render_to_response, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.models import User
from django import forms
from django.db.models import Q
#from django.shortcuts import HttpResponseRedirect, HttpResponse

from django.conf import settings

import simplejson
import datetime
import json

import os
from subprocess import call
from subprocess import check_call
from seek.seekdb import SeekDB
#from .nextcloudapi import NextCloudAPI
#from .galaxyapi import GalaxyAPI

#from .datagrid import querySuffix, getStartRows, getFilteringParameters
from .dbtable import DBtable

# This is the absolute path to the download folder, usually at "project_root/theme/SmartAdmin/static/media/download/"
# To be figured out: ideally, we should use 'project_root/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY  = settings.MEDIA_ROOT + "download/"

# This is the relative path to the download folder, usually at "/theme/SmartAdmin/static/media/download/" without project_root.
# To be figured out: ideally, we should use '/static/media/download", which does not rely on the theme. 
DOWNLOAD_DIRECTORY_LINK = settings.MEDIA_URL + 'download/'   # this is a symbolic link to DOWNLOAD_DIRECTORY


# We always use report to return variables
report = {}

from dbtable import DBtable

#from django.contrib.auth.views import login
from django.contrib.auth import authenticate, login


def __process(request, operation):
    dbtable = DBtable("DEFAULT")
    return dbtable.process(request, operation) 
    
    #dgtable = DataGrid(alumni)
    #return dgtable.process(request, operation) 
   
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

#def getSeekLogin(request):
#    seekdb = SeekDB(None, None, None)
#    return seekdb.getSeekLogin(request)

    
def login_seek(request):
    ''' Process login authentication on Seek server, which is customized.
    Reference:
        http://www.visualseq.net/dokuwiki/doku.php?id=computer:software:django:user-customization#django_login_model
    
    if request.user.is_authenticated():
        return HttpResponseRedirect('')
    else:
        return login(request)
    '''
    print('login_seek')
    seekdb = SeekDB(None, None, None)
    user_seek = seekdb.getSeekLogin(request)
    
    status = user_seek['status']
    err = user_seek['err']
    
    print("Login status: ", status)
    print("Login error message: ", err)
    
    if request.method == 'POST':
        if user_seek['status']:
            request.session['server'] = user_seek['server']
            request.session['storage_type'] = user_seek['storagetype']
            request.session['storage'] = user_seek['storage']
            request.session['username'] = user_seek['username']
            request.session['password'] = user_seek['password']
        
            if user_seek['noexpire'] == "yes":
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(43200)
                
                
            # Log into DMAC system itself
            # refer to: http://www.visualseq.net/dokuwiki/doku.php?id=computer:software:django:user-customization#how_to_log_an_user_in
            username = user_seek['username']
            password = user_seek['password']
            # for Django 3.0
            #user = authenticate(request, username=username, password=password)
            # for Django 1.10
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
            #else:
            # try register a new user. Refer to:
            #    user = User.objects.create_user(username, 'dinghuim@gmail.com', password)
            #    user.last_name = 'Lennon'
            #    user.first_name = 'john'
            #    user.is_staff = 1
            #    user.is_active = 1
            #    user.save()
            #    user = authenticate(username=username, password=password)
            #    if user is not None:
            #        login(request, user)
                
                       
            # refer to: https://docs.djangoproject.com/en/dev/ref/request-response/#django.http.HttpRequest.build_absolute_uri
            httpurl = request.get_full_path()
            print(httpurl)
            
            #example "/login/?next=/seek/samples/"
            urls = httpurl.split('?next=')
            if len(urls)>1:
                url_redirect = urls[1]
            else:
                #url_redirect = urls[0]
                url_redirect = "/"
            print(url_redirect)
            #print("redirect")
            #return index(request)
            #url_redirect = "/login/?next=/seek/document/id=" + str(document_id) + "/"
            #url_redirect = "/seek/samples/"
            return HttpResponseRedirect(url_redirect)
        else:
            print("re-login")
            request.session.flush()
            #return HttpResponseRedirect("/login/")
            #return render_to_response('login.html', context={'error': user_seek['err']})
            return render(request, 'login.html', {'error': user_seek['err']})
        
    return render(request, 'login.html')
    
    ''' 
    if request.method == 'POST':
        err = []
        username = request.POST.get('username')
        password = request.POST.get('password')
        server = settings.SEEK_URL
        storage = settings.SEEK_URL
        #storagetype = request.POST.get("storagetype")
        storagetype = 'SEEK'
        noexpire = request.POST.get('no-expire')
        if storage != "":
            request.session['storage_type'] = storagetype
            request.session['storage'] = storage
        else:
            request.session.flush()
        
        if server != "":
            request.session['server'] = server
        else:
            err.append("No server selected")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
            
        if username != "" and password != "":
            request.session['username'] = username
            request.session['password'] = password
        else:
            err.append("No valid username or password")
            request.session.flush()
            return render_to_response('login.html', context={'error': err})
        if noexpire == "yes":
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(43200)
        #return render_to_response('seek_login.html', context={'error': err})
        return index(request)
        
    return render(request, 'login.html')
    '''

def logout_seek(request):
    """Flush the exisiting session with the users login details.

    Arguments:
        request: Request the session so it can be flushed and the folder
        with the logged in user can be removed.
    """
    if request.session.get('username') is not None:
        call(["rm", "-r", request.session.get('username')])
        request.session.flush()
    return HttpResponseRedirect(reverse('index'))
    
def login_full(request):
    """Login page where Galaxy server, email address, Galaxy password,
    storage location, username and password are stored in a session.

    Arguments:
        request: Login details filled in from the login page.
        
        
    Notes:
        Migrated from MyFair.
    """
    if request.method == 'POST':
        err = []
        if request.POST.get('server')[-1] == '/':
            server = request.POST.get('server')
        else:
            server = request.POST.get('server') + '/'
        # if request.POST.get('storage')[-1] == '/':
        #     storage = request.POST.get('storage')[:-1]
        # else:
        #     storage = request.POST.get('storage')
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        '''
        galaxypass = request.POST.get("galaxypass")
        galaxyemail = request.POST.get("galaxyemail")
        if galaxypass != "":
            request.session["galaxypass"] = galaxypass
        else:
            err.append("No email address or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if galaxyemail != "":
            request.session["galaxyemail"] = galaxyemail
        else:
            err.append("No email address or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        '''
        server = settings.SEEK_URL
        storage = settings.SEEK_URL
        storagetype = request.POST.get("storagetype")
        noexpire = request.POST.get('no-expire')
        if storage != "":
            request.session['storage_type'] = storagetype
            request.session['storage'] = storage
        else:
            request.session.flush()
        
        if server != "":
            request.session['server'] = server
        else:
            err.append("No server selected")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
            
        if username != "" and password != "":
            request.session['username'] = username
            request.session['password'] = password
        else:
            err.append("No valid username or password")
            request.session.flush()
            return render_to_response('login.html', context={
                'error': err})
        if noexpire == "yes":
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(43200)
        return render_to_response('home.html', context={
            'error': err})
        
    return render(request, 'login.html')
    
def index(request):
    """Homepage information. The ISA information from the storage location and
    the triple storea re available from the homepage. Data can be searched or
    Galaxy histories can be send to an existing investigation - Study.

    Arguments:
        request: Getting the user details from request.session.

    Raises:
        Exception: Failed to het galaxy user information.
    """
    print(request.session.get('username'))
    print(request.session.get('password'))
    
    if (request.method == 'POST' and
        request.session.get('username') is None
    ):
        login(request)
    else:
        pass
    
    
    if (
        request.session.get('username') is None or
        request.session.get('username') == ""
    ):
        err = ""
        return render_to_response('login.html', context={
            'error': err})
    else:
        if not os.path.isdir(request.session.get('username')):
            call(["mkdir", request.session.get('username')])
        if request.POST.get('inv') is not None:
            investigation = request.POST.get('inv')
        else:
            investigation = ""
            
        username = request.session.get('username')
        password = request.session.get('password')
        storage = settings.SEEK_URL
        virtuoso = settings.VIRTUOSO_JS_URL
        server = request.session.get('server')
        
        print('next to seekdb')
        print(storage)
        
        seekdb = SeekDB(storage, username, password)
        user_seek = seekdb.getSeekLogin(request)
        if user_seek['status']:
            userinfo_seek = user_seek['userdata']
        else:
            userinfo_seek = None
        
        investigations,folders = seekdb.get_investigations_folders(investigation)
        #print(investigations)
        #print(folders)
        
        return render(
            request, 'seek_login.html',
            context={'user': username, 'username': username,
                     'password': password, 'server': server,
                     'storage': storage,
                     'storagetype': request.session.get('storage_type'),
                     'virtuoso_url': virtuoso,
                     'investigations': investigations,
                     'studies': folders,
                     'inv': investigation
            }
        )    
    
    