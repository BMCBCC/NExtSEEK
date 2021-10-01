#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for talking to Seek system.
*   Author - Huiming Ding: huiming@mit.edu

*  This program is a trial software: you can redistribute it and/or modify
*  it under the terms of the MIT License. 
*  Due to the nature of the on-going research, the redistribution is limited to authorized users 
*  in the current phase of the study. 
 
* The above copyright notice and this permission notice shall be included in all
* copies or substantial portions of the Software.

* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
* IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
* FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
* AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
* LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
* OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
* SOFTWARE.

****************************************************************************'''

'''****************************************************************************

*   To run the program
*   For example - python 

*   Logic - 

****************************************************************************'''
from .sparql import Sparql
from .seekapi import SeekAPI

from django.conf import settings
import hashlib
import os
import json
from pandas.io.json import json_normalize
from dmac.conversion import convertDicToOptions

#import magic

class SeekDB(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        seekdb = SeekDB()
    '''
    def __init__(self, server, username, password):
        ''' Initialize the class, given the information of Seek server, 
        Input:
            server, If None is provided, the initialization must be loaded through the login page
                    returned from getSeekLogin(request).
                    such as:
                        "http://127.0.0.1:3000",
                        "https://kibcc2.mit.edu"
                    etc.
            username,
            password, 
        
        Usage:
            seekdb = SeekDB(None, None, None)
            user_seek = seekdb.getSeekLogin(request)
            
        or:
            
            
        '''
        #self.__sparql = Sparql()
        self.__sparql = None
        self.__seekapi = SeekAPI(server, username, password)
        self.user_seek = None
        if username is not None:
            self.user_seek = {}
            self.user_seek['server'] = server
            self.user_seek['storage'] = server
            self.user_seek['storagetype'] = 'SEEK'
            self.user_seek['username'] = username
            self.user_seek['password'] = password
            self.getSeekLogin(None)
            
        
    def __getFeatureInfo(self, userdata, featureName, defaultIndex=0):
        ''' Get the information for a feature.
        Input:
            userdata: = user_seek['userdata']
            featureName: a name available in the userdata["relationships"], such as
                "projects", "institutions", "investigations", "studies" etc in,
                    "relationships":{
                        "projects":{"data":[
                            {"id":"1","type":"projects"},
                            {"id":"2","type":"projects"}
                        ]},
                        "institutions":{"data":[{"id":"1","type":"institutions"}]},
                        "investigations":{"data":[
                            {"id":"1","type":"investigations"}
                        ]},
                        "studies":{"data":[...]},
                        "assays":{"data":[...]},
                        "data_files":{"data":[...]},
                        "models":{"data":[]},
                        "sops":{"data":[]},
                        "publications":{"data":[]},
                        "presentations":{"data":[]},
                        "events":{"data":[]},
                        "documents":{"data":[]}
                    },
                    
            defaultIndex: default=0, if the list of feature data has more than one record,
                which record to return. 
        Output:
            featureInfo:
                if defaultIndex=0, output a dictionary with the info of the feature, such as,
                    fid = featureInfo['id']
                    featureInfo['type']     # such as "projects", "institutions" etc
                    featureInfo['title']    # such as "Default Project"
                if if defaultIndex=-1, output a list of dictionaries, such as,
                    featureInfo = [{'id':1, 'title':'ImpacTB'}, {'id':2, 'title':'SRF'}]
                
                
        '''
        featureInfo = {}
        if "relationships" not in userdata:
            print('"relationships" not in userdata')
            return featureInfo
        
        relationships = userdata["relationships"]
        if featureName not in relationships:
            print('featureName not in relationships:', featureName)
            return featureInfo
        
        featureData = relationships[featureName]["data"]
        nfeatures = len(featureData)
        if nfeatures==0 or defaultIndex>(nfeatures-1):
            print('No feature available', featureName)
            return featureInfo
        
        # such as {"id":"1","type":"institutions"} or {"id":"1","type":"projects"} etc.
        if defaultIndex>=0:
            # only choose the deafult one
            featureInfo = featureData[defaultIndex]
            #print(featureInfo)
        
            fid = featureInfo['id']
            ftype = featureInfo['type']  # such as "projects", "institutions" etc
            furl = "/" + ftype + "/"     # such as "/projects/"
            finfo = self.getInfoObject(furl, int(fid))
            featureInfo['title'] = finfo['attributes']['title']
            
            return featureInfo
        else:
            # If defaultIndex=-1, output a list of info dics instead.
            # For example, if defaultIndex=0 and eatureName="projects", output the frist project with index=0 in a dictionary, such as {'id':1, 'title':'ImpacTB'}
            # However, if defaultIndex=-1 and eatureName="projects", output a list of dictionaries, such as  [{'id':1, 'title':'ImpacTB'}, {'id':2, 'title':'SRF'}]
            featureInfoList = []
            print("featureData:", featureData)
            for featureInfo in featureData:
                #featureInfo = featureData[index]
                #print(featureInfo)
        
                fid = featureInfo['id']
                ftype = featureInfo['type']  # such as "projects", "institutions" etc
                furl = "/" + ftype + "/"     # such as "/projects/"
                finfo = self.getInfoObject(furl, int(fid))
                featureInfo['title'] = finfo['attributes']['title']
                
                ffinfo = {}
                ffinfo['id'] = fid
                ffinfo['title'] = featureInfo['title']
                featureInfoList.append(ffinfo)
            return featureInfoList
        
        
    def getUserInfo(self, user_id):
        ''' Given a user id, get its project and lab info.
        Input:
            user_id, the id in people table
        
        Output:
            msg
            status
            userInfo['projectid']
            userInfo['projectname']
            userInfo['institutionid']
            userInfo['institutionname']
            userInfo['lababbv']
        '''
        userInfo = {}
        status = True
        msg = ''
        if user_id<=0:
            msg = "User id not valid: " + str(user_id)
            status = False
            userInfo['userdata'] = None
            return userInfo, status, msg
        
        userInfo['user_id'] = user_id
        userInfo['person_id'] = user_id
        
        userdata = self.getLoginUserInfo(user_id)
        userInfo['userdata'] = userdata
        if userdata is None:
            status = False
            userInfo['projectid'] = 0
            userInfo['institution'] = "NA"
            msg = "Password not valid"
            return userInfo, status, msg
        
        projectInfo = self.__getFeatureInfo(userdata, "projects")
        #print(projectInfo)
        if 'id' in projectInfo:
            # return the default project id, which is the first project on the list
            userInfo['projectid'] = projectInfo['id']
            userInfo['projectname'] = projectInfo['title']
                        
            #projectdata = self.getInfoObject("/projects/", projectInfo['id'])
            #print "project info:", projectdata
        else:
            userInfo['projectid'] = 0
            userInfo['projectname'] = 'NA'
            status = False
            msg = "No project is assigned, ask Admin for help."
                
        projectOptions = self.__getFeatureInfo(userdata, "projects", -1)
        userInfo['projectOptions'] = projectOptions
                
        institutionInfo = self.__getFeatureInfo(userdata, "institutions")
        #print(institutionInfo)
        if 'id' in institutionInfo:
            # return the default project id, which is the first project on the list
            userInfo['institutionid'] = institutionInfo['id']
            userInfo['institutionname'] = institutionInfo['title']
            institutionname = userInfo['institutionname']
            if len(institutionname)>3:
                lababbv = institutionname[0:3]
                lababbv = lababbv.upper()
            else:
                lababbv = institutionname.upper()
            if " " in lababbv:
                lababbv = lababbv.replace(" ", "_")
            userInfo['lababbv'] = lababbv
        else:
            userInfo['institutionid'] = 0
            userInfo['institutionname'] = 'NA'
            userInfo['lababbv'] = 'NA'
            status = False
            mag = "No institution/lab is assigned, ask Admin for help."    
        
        return userInfo, status, msg
        
    def getUserFullname(self, person_id):
        ''' Given person_id, which is found based on login user name and password from "User" table,
            retrieve user's full name, such as first and last name from "People" table.
            
        Input:
            person_id, usually fom calling person_id=self.__getSeekPersonID(username), which
                    is not through Seek API. 
            
        Output:
            fullname = firstname + ' ' + lastname
        
        '''
        fullname = self.__getNameFromID('people', person_id)
        return fullname
        
        
    def updateUserProfile(self, fullname):
        ''' Given user's first and last name, get user's id and other info, such as
            project id, etc.
        Input:
            fullname = firstname + ' ' + lastname
            
        Output:
            Update the user's profile in self.seek_user.
            user_profile['msg']
            user_profile['status']
            user_profile['projectid']
            user_profile['projectname']
            user_profile['institution']
            user_profile['institutionname']
            user_profile['lababbv']
        
        Notes:
            An user's profile consists of two tables:
                user table, in which user's login_name and password are stored with an user_id. User_id
                            is private and not used for public access.
                people table, in which an user's first and last name are stored under the primary key people_id.
                            people_id is publically accessible through the API call "people/id".
            Therefore, given a login_name and password, we can't find the people_id for retrieving the person's profile.
            An user's first and last name must be provided to retrieve a person's profile.
        '''
        print("__getUserProfile")
        
        self.user_seek['status'] = True
        self.user_seek['msg'] = "Okay"
        
        person_id = self.getUserid(fullname)
        userInfo, status, msg = self.getUserInfo(person_id)
        self.user_seek.update(userInfo)
        return self.user_seek
        
        
    def getSeekLogin(self, request, whetherFullInfo=True):
        ''' Get the information of valid Seek user, either from login through POST
        or from Session info.
        
        Once the user is valid, re-initialize the class.
        Input
            request, either POST or GET.
            whetherFullInfo, True, default, retrieve full user information, such as project, lab etc, which runs slower. 
                             False,  only retrieve server name, user name and password, which runs faster.
        Output
            user_seek, a dictionary with the login user info, such as,
                user_seek['server'],
                user_seek['storage'],
                user_seek['storagetype'],
                user_seek['username'],
                user_seek['password'],
                user_seek['noexpire'],
                user_seek['user_id'],
                user_seek['userdata'],
                user_seek['status'],
                user_seek['err']
                user_seek['projectid'], 0 or the first default project id, 
            
            where
                if we run:
                    $ curl -u username:password -X GET http://dmac.mit.edu:3000/people/1/ -H "accept: application/json"
                userdata = user_seek['userdata'] is the returned dictionary from Seek API, including,
                =
                {
                    'id': '1',
                    'type': 'people',
                    'attributes': {'title': 'DBAdmin DBAdmin'}, 
                    'links': {'self': '/people/1'},
                    'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}
                    "relationships":{
                        "projects":{"data":[
                            {"id":"1","type":"projects"},
                            {"id":"2","type":"projects"}
                        ]},
                        "institutions":{"data":[{"id":"1","type":"institutions"}]},
                        "investigations":{"data":[
                            {"id":"1","type":"investigations"}
                        ]},
                        "studies":{"data":[...]},
                        "assays":{"data":[...]},
                        "data_files":{"data":[...]},
                        "models":{"data":[]},
                        "sops":{"data":[]},
                        "publications":{"data":[]},
                        "presentations":{"data":[]},
                        "events":{"data":[]},
                        "documents":{"data":[]}
                    },
                    "links":{"self":"/people/1"},
                    "meta":{"created":"2019-07-02T15:23:41.000Z","modified":"2019-07-16T14:42:14.000Z","api_version":"0.2","uuid":"4c1807a0-7f0b-0137-3e0c-000c295a2b25","base_url":"http://dmac.mit.edu:3000"}
                }
            
                where the list of projects for a valid user can be found in,
                    projects = user_seek['userdata']["relationships"]["projects"]["data"]
            
        '''
        user_seek = {}
        status = True
        err = []
        if request is None:
            print("getSeekLogin from command line")
            if self.user_seek is None:
                user_seek['server'] = settings.SEEK_URL
                user_seek['storage'] = settings.SEEK_URL
                user_seek['storagetype'] = 'SEEK'
                user_seek['username'] = None
                user_seek['password'] = None
            else:
                user_seek['server'] = self.user_seek['server']
                user_seek['storage'] = self.user_seek['storage']
                user_seek['storagetype'] = self.user_seek['storagetype']
                user_seek['username'] = self.user_seek['username']
                user_seek['password'] = self.user_seek['password']
            
        elif request.method == 'POST':
            print("getSeekLogin from POST")
            user_seek['server'] = settings.SEEK_URL
            user_seek['storage'] = settings.SEEK_URL
            user_seek['storagetype'] = 'SEEK'
            # get SEEK login info from POST
            user_seek['username'] = request.POST.get('username')
            user_seek['password'] = request.POST.get('password')
            #storagetype = request.POST.get("storagetype")
            user_seek['noexpire'] = request.POST.get('no-expire')
            #print(user_seek['username'],user_seek['password'], user_seek['noexpire'])
        
            #if user_seek['storage']=="":
            #    status = False
            
            username = request.POST.get("user")
            if username is None and user_seek['username'] is None:
                print("getSeekLogin from Session")
                # Though it is POST, it is already loged in
                user_seek['server'] = request.session.get('server')
                user_seek['storage'] = settings.SEEK_URL
                user_seek['storagetype'] = 'SEEK'
                user_seek['username'] = request.session.get('username')
                user_seek['password'] = request.session.get('password')
            '''
            print(user_seek)

            if request.POST.get("user") is not None or request.POST.get("user") != "":
                username = request.POST.get("user")
                print('username:', username)
                #userid = self.getUserid(username)
                #print(username, userid)
            else:
                print('user:', request.POST.get("user"))
            print(user_seek)
            '''
        else:
            print("getSeekLogin from GET")
            # get SEEKlogin info from Session
            user_seek['server'] = request.session.get('server')
            user_seek['storage'] = settings.SEEK_URL
            user_seek['storagetype'] = 'SEEK'
            user_seek['username'] = request.session.get('username')
            user_seek['password'] = request.session.get('password')
            print(user_seek)
        
        if user_seek['username'] is None or user_seek['username']=="":
            # login required
            err.append("No valid username or password")
            print("No valid username or password")
            status = False
        
        if user_seek['server']=="":
            err.append("No server selected")
            print("No server selected")
            status = False
            
        if user_seek['password']=="":
            err.append("No valid username or password")
            print("No valid username or password")
            status = False
            
        if status:
            # user name, password and server name are available
            if request is None:
                print("SeekAPI should already be initialized")
                person_id = 0
                err.append("Person id not defined")
                status = False
                print("Person id not defined")
            else:
                # this is to prevent the loop if user info is from http request
                #self.__init__(user_seek['server'], user_seek['username'], user_seek['password'])
                self.__seekapi = SeekAPI(user_seek['server'], user_seek['username'], user_seek['password'])
                
                if whetherFullInfo:
                    person_id = self.__getSeekPersonID(user_seek['username'])
                    userInfo, status, msg = self.getUserInfo(person_id)
                    user_seek.update(userInfo)
                    if not status:
                        err.append(msg)
            
        user_seek['status'] = status
        user_seek['err'] = err
        print('Login status: ', status)
        self.user_seek = user_seek
        return user_seek
    
    def getPageRequests(self, seek_url):
        bodyhtml = self.__seekapi.getPageRequests(seek_url)
        return bodyhtml
        
        
    def __getSeekPersonID(self, username):
        ''' get Seek user_id/people_id from Seek.users table, given
        Input
            username, the login user name.
        Output
            id, >0, valid user_id/people_id
                =0, not available
    
        '''
        
        # such as {u'1': u'Default Project', u'3': u'MIT_SRP', u'2': u'IMPAcTb'}
        #projects = self.getProjects(True)
        #print("projects:" , projects)
        #getInvestigations(self, project_title, useSeekAPI=True)
        #return self.getUserid(username)
        
        
        # Only use API call, never ever use DB access.
        from seek.models import Users
        from django.db.models import Q
        filter = Q(login__icontains=username)
        userobjs = Users.objects.filter(filter).values()
        #print(userobjs)
        if len(userobjs)==1:
            userinfo = userobjs[0]
            # user id in the user table is private and never used on Seek front
            #seek_userid = userinfo['id']
            # therefore, we should use person id in people table, which is
            # accessible through "/people/person_id/'.
            # In theory, person is should be the same as the user id.
            # however, on kibcc2, it is proved not always the case.
            seek_personid = userinfo['person_id']
        else:
            seek_personid = 0
        
        #print("seek_personid:", seek_personid)
        return seek_personid
        


        
        
    def getProjects(self, useSeekAPI=True):
        """
        Get a list of projects, regardless through Seek API or SPARQL.
        
        Arguments:
            
        Returns:
            A dictionary with SEEK project id and title, such as,
                {'1': 'project1', '2': 'project2'}
            
        Example:
            Queries:
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation xlink' | sed -n 's/.*title="\([^"]*\).*/\1/p'
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation2' | sed -n 's/.*href="\([^"]*\).*/\1/p'
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation1' | sed -n 's/.*href="\([^"]*\).*/\1/p'
            resultset:
                {'investigation2': 'http://dmac.mit.edu:3000/investigations/1', 'investigation1': 'http://dmac.mit.edu:3000/investigations/2'}
            which is different from the result set returned from the sparql query,
                {'1': rdflib.term.Literal('investigation2'), '2': rdflib.term.Literal('investigation1')}
        """
        if useSeekAPI:
            #projects = self.__getProjectsAPI()
            projects = self.__seekapi.getProjects()
            return self.__convertKeyValue(projects)
        else:
            return self.__sparql.getProjects()
            #return self.__getProjectsSPARQL()
        
    def disgenet(self, disgenet):
        """Finds the DisGeNET URI based on the searched disease entered
        when uploading data to the SEEK server.

        Arguments:
            disgenet: Disease entered in the SEEK upload form.

        Returns:
            DisGeNET URIs that are connected to the disease entered in the upload form.
        """
        sparql_query = (
            "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>" +
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>" +
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>" +
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" +
            "PREFIX dcterms: <http://purl.org/dc/terms/>" +
            "PREFIX foaf: <http://xmlns.com/foaf/0.1/>" +
            "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>" +
            "PREFIX void: <http://rdfs.org/ns/void#>" +
            "PREFIX sio: <http://semanticscience.org/resource/>" +
            "PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>" +
            "PREFIX up: <http://purl.uniprot.org/core/>" +
            "PREFIX dcat: <http://www.w3.org/ns/dcat#>" +
            "PREFIX dctypes: <http://purl.org/dc/dcmitype/>" +
            "PREFIX wi: <http://http://purl.org/ontology/wi/core#>" +
            "PREFIX eco: <http://http://purl.obolibrary.org/obo/eco.owl#>" +
            "PREFIX prov: <http://http://http://www.w3.org/ns/prov#>" +
            "PREFIX pav: <http://http://http://purl.org/pav/>" +
            "PREFIX obo: <http://purl.obolibrary.org/obo/>" +
            "SELECT * " +
            "WHERE { SERVICE <http://rdf.disgenet.org/sparql/> { " +
            "?uri dcterms:title ?disease . " +
            "?disease bif:contains \'\"" + disgenet + "\"\' ." +
            "} " +
            "} LIMIT 30"
        )
        
        disgenet_uri = {}
        rows = self.__sparql.query(sparql_query)
        for row in rows:
            disgenet_uri[row[0].strip("rdflib.term.URIRef")] = row[1]
        return disgenet_uri
        
    def getUserid(self, fullname):
        """Gets the SEEK user ID based on the full name of the user.

        Arguments:
            server: SEEK server address for __seekapi
            username: SEEK username for __seekapi
            password: SEEK password for __seekapi
            
            fullname: Full name of the user in SEEK, i.e.,
                fullname = firstname = ' ' + lastname

        Returns:
            The person ID based on the full name of the user or None.
            
        Example,
            fullname: "DBAdmin DBAdmin"
            jsonpeople:
                {'data': [{'id': '1', 'type': 'people', 'attributes': {'title': 'DBAdmin DBAdmin'}, 'links': {'self': '/people/1'}}], 'jsonapi': {'version': '1.0'}, 'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}}

            userid = 1
        """
        #userquery = ("curl -X GET " + server +
        #         "/people -H \"accept: application/json\"")
        queryurl = "/people"
        jsonpeople = self.__seekapi.runGetQuery(queryurl)
        print("jsonpeople:", jsonpeople)
        
        person_id = None
        for uid in range(0, len(jsonpeople["data"])):
            if jsonpeople["data"][uid]["attributes"]["title"] == fullname:
                person_id = str(jsonpeople["data"][uid]["id"])
        return person_id
    
    
    def getInfoObject(self, object_url, object_id):
        """Gets the SEEK object info based on the object ID based.

        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password
            
            object_url, such as
                "/people/" for user object
                "/samples/" for sample object
                "/documents/" for document object, etc
                
            object_id, the id in object table, retrieved from API, for example,
            
                "/samples/3" for sample object 3;
                "/documents/5" for document object 5, etc
            
        Returns:
            The profile of person with the id from people table.
            
        Example,
            fullname: "DBAdmin DBAdmin"
            username: 'dbadmin'
            object_id: 1
            jsonobject:
                {'data': [{'id': '1', 'type': 'people', 'attributes': {'title': 'DBAdmin DBAdmin'}, 'links': {'self': '/people/1'}}], 'jsonapi': {'version': '1.0'}, 'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}}

        Usage:
            To use it,
                seekdb = SeekDB(None, None, None)
                user_seek = seekdb.getSeekLogin(request)
                resultJson1 = seekdb.getInfoObject("/studies/", 1)
                print("resultJson1:", resultJson1)
            
                resultJson1 = datadic =
                    {
                        u'relationships': {...}, 
                        u'links': {u'self': u'/studies/1'}, 
                        u'meta': {u'base_url': u'http://dmac.mit.edu:3000', u'uuid': u'a3672050-83e5-0137-3e0d-000c295a2b25', u'modified': u'2019-07-09T16:20:50.000Z', u'api_version': u'0.2', u'created': u'2019-07-08T19:36:43.000Z'}, 
                        u'attributes': {u'description': None, u'title': u'blood sample taken', u'snapshots': None, u'other_creators': None, u'person_responsible_id': u'1', u'experimentalists': None}, 
                        u'type': u'studies', 
                        u'id': u'1'
                    }

            We caan also use SeekSession to retrieve it,
                from seeksession import SeekSession
                session = SeekSession(user_seek['username'], user_seek['password'])
                seekurl = "http://localhost:3000/studies/1/"
                resultJson2 = session.getSeekURL(seekurl)
                print("resultJson2:", resultJson2)
            
            where the result json dictionary is in the following format:
                resultJson2 = {
                    u'data': datadic, 
                    u'jsonapi': {u'version': u'1.0'}
                }
            where datadic = resultJson2['data'] = resultJson1
            
        """
        #userquery = ("curl -X GET " + server +
        #         "/people -H \"accept: application/json\"")
        objectdata = None
        if object_id<=0:
            return objectdata
        
        #queryurl = "/people/" + str(object_id)
        queryurl = object_url + str(object_id)
        #print(queryurl)
        jsonobject = self.__seekapi.runGetQuery(queryurl)
        #for item in jsonobject:
        #    print item
        
        if jsonobject is None:
            objectdata = None
        elif "data" in jsonobject:
            objectdata = jsonobject["data"]
        
        return objectdata
    
    def __getProjectName(self, projectid):
        # return self.__getNameFromID("projects", projectid)
        
        if projectid is None or projectid=="":
            return ""
        
        pinfo = self.getInfoObject("/projects/", int(projectid))
        #print(pinfo)
        
        projectname =  pinfo['attributes']['title']
        #print(projectname)
        return projectname
    
    def __getNameFromID(self, objectname, id):
        ''' Get name from id,given
        Input:
            objectname, such as "projects", "studies", "assays" or 'people' etc,
            id, the id
        
        Output:
            title of the object.
        

        '''
        if id is None or id=="":
            return ""
        
        item = "/" + objectname + "/"
        pinfo = self.getInfoObject(item, int(id))
        #print(pinfo)
        
        name =  pinfo['attributes']['title']
        return name
    
    def getLoginUserInfo(self, user_id):
        """Gets the SEEK user ID based on the login user name.

        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password
            
            user_id, the id in users table, based on the login user name,
                retrieved directly from DB, rather than from API.
        Returns:
            The profile of person with the id from people table.
                {
                    'id': '1',
                    'type': 'people',
                    'attributes': {'title': 'DBAdmin DBAdmin'}, 
                    'links': {'self': '/people/1'},
                    'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}
                    'relationships':{}
                }

                {"data":{
                    "id":"1",
                    "type":"people",
                    "attributes":{
                        "avatar":null,
                        "title":"name",
                        "description":"MIT",
                        "first_name":"first",
                        "last_name":"last",
                        "orcid":null,
                        "mbox_sha1sum":"a2d47f8059f76c56e11d508aac074ff9cd517e38",
                        "expertise":null,
                        "tools":null,
                        "project_positions":null
                    },
                    "relationships":{
                        "projects":{"data":[{"id":"1","type":"projects"}]},
                        "institutions":{"data":[{"id":"1","type":"institutions"}]},
                        "investigations":{"data":[]},"studies":{"data":[]},
                        "assays":{"data":[]},
                        "data_files":{"data":[]},"models":{"data":[]},
                        "sops":{"data":[]},
                        "publications":{"data":[]},
                        "presentations":{"data":[]},
                        "events":{"data":[]},
                        "documents":{"data":[]}
                    },
                    "links":{"self":"/people/1"},
                    "meta":{
                        "created":"2019-07-01T17:48:29.000Z",
                        "modified":"2019-07-01T17:48:29.000Z",
                        "api_version":"0.2",
                        "uuid":"5bddcdb0-7e56-0137-7e53-000c290e4b57",
                        "base_url":"https://fairdata.mit.edu"}
                    },
                    "jsonapi":{"version":"1.0"}
                }


        Example,
            fullname: "DBAdmin DBAdmin"
            username: 'dbadmin'
            user_id: 1
            jsonpeople:
                {'data': [{'id': '1', 'type': 'people', 'attributes': {'title': 'DBAdmin DBAdmin'}, 'links': {'self': '/people/1'}}], 'jsonapi': {'version': '1.0'}, 'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}}

        """
        #userquery = ("curl -X GET " + server +
        #         "/people -H \"accept: application/json\"")
        return self.getInfoObject("/people/", user_id)
        '''
        print jsonpeople["data"]
        return jsonpeople["data"]
        
        for uid in range(0, len(jsonpeople["data"])):
            #print(jsonpeople["data"][uid])
            id = jsonpeople["data"][uid]["id"]
            name = jsonpeople["data"][uid]["attributes"]["title"]
            print(id, name)
            
            queryurli = "/people/" + str(id) + "/edit"
            jsonuser = self.__seekapi.runGetQuery(queryurli)
            print('user:', jsonuser)
            
            if jsonpeople["data"][uid]["attributes"]["title"] == username:
                userid = str(jsonpeople["data"][uid]["id"])
        return userid
        '''
        
    def __checkPermissions(self, userid, studyid):
        """Checks if the user has permissions to add an assay to the 
            selected study. Returns a true if user can create the assay.

        Arguments:
            username: SEEK username.
            password: SEEK password.
            server: The SEEK server URL.
            userid: User ID of the logged in user.
            studyid: Study ID to check for permissions.

        Returns:
            True/False: The user has permissions to add an assay to the study or 
                the user does not have permissions to add an assay to the study.
                
        Notes:
            The Seek API call through curl must be authenticated by
                "curl -u username:password"
            Otherwise, incomplete result set will be returned. 
        
                
        Example
            jsonuser:
            {
                'data': {
                    'id': '1', 
                    'type': 'people', 
                    'attributes': {
                            'avatar': None, 
                            'title': 'DBAdmin DBAdmin', 
                            'description': None, 
                            'first_name': 'DBAdmin', 
                            'last_name': 'DBAdmin', 
                            'orcid': None, 
                            'mbox_sha1sum': '32f3f8468f5a40e648086c15d8ef6669c593d617', 
                            'expertise': None, 
                            'tools': None, 
                            'project_positions': None
                    }, 
                    'relationships': {
                        'projects': {'data': [{'id': '1', 'type': 'projects'}, {'id': '2', 'type': 'projects'}]}, 
                        'institutions': {'data': [{'id': '1', 'type': 'institutions'}]}, 
                        'investigations': {'data': []}, 
                        'studies': {'data': [{'id': '4', 'type': 'studies'}, {'id': '5', 'type': 'studies'}]}, 
                        'assays': {'data': []}, 'data_files': {'data': []}, 
                        'models': {'data': []}, 
                        'sops': {'data': []}, 
                        'publications': {'data': []}, 
                        'presentations': {'data': []}, 
                        'events': {'data': []}, 
                        'documents': {'data': []}
                    }, 
                    'links': {'self': '/people/1'}, 
                    'meta': {
                        'created': '2019-07-02T15:23:41.000Z', 
                        'modified': '2019-07-16T14:42:14.000Z', 
                        'api_version': '0.2', 
                        'uuid': '4c1807a0-7f0b-0137-3e0c-000c295a2b25', 
                        'base_url': 'http://dmac.mit.edu:3000'
                    }
                }, 
                'jsonapi': {'version': '1.0'}
            }
        
        """
        #peoplequery = ("curl -X GET " + server + "/people/" + str(userid) +
        #           " -H \"accept: application/json\"")
        
        sids = []
        queryurl = "/people/" + str(userid)
        jsonuser = self.__seekapi.runGetQuery(queryurl)
       # print("studyid", studyid)
        #userinfo = subprocess.Popen([peoplequery],
        #                        stdout=subprocess.PIPE,
        #                        shell=True).communicate()[0].decode()
        #jsonuser = json.loads(userinfo)
        studyids = jsonuser["data"]["relationships"]["studies"]["data"]
        #print(studyids)
        # such as
        # [
        #    {u'type': u'studies', u'id': u'1'},
        #    {u'type': u'studies', u'id': u'2'},
        #    {u'type': u'studies', u'id': u'3'},
        #    {u'type': u'studies', u'id': u'4'}, {u'type': u'studies', u'id': u'5'}, {u'type': u'studies', u'id': u'6'}, {u'type': u'studies', u'id': u'7'}, {u'type': u'studies', u'id': u'8'}]
        for datanr in range(0, len(studyids)):
            #print(datanr)
            sids.append(jsonuser["data"]["relationships"]["studies"]["data"][datanr]["id"])
            
        #print(sids)
        #print(studyid)
        if str(studyid) in sids:
            return True
        else:
            return False
        
    def createStudy(self, userid, projectid,
                 investigationid, title, description, studyname):
        """Creates a new study in SEEK.

        Arguments:
            username: SEEK Login name
            password: SEEK password
            server: SEEK server URL
            userid: Creator ID in SEEK
            projectid: Selected SEEK project ID.
            investigationid: Selected SEEK investigation ID.
            title: Title entered when creating a new assay.
            description: Description entered when creating a new assay.
            studyname: The name of the new study.
        """
        new_study_json = self.__createStudyDic(userid, projectid,investigationid, title, description)
        from seeksession import SeekSession
        session = SeekSession(self.user_seek['server'], self.user_seek['username'], self.user_seek['password'])
        study_id = session.postSeekURL("studies", new_study_json)
        print('study_id 1:', study_id)
        return new_study_json, study_id
        
        # The following also works
        #study_creation_query = (
        #    "curl -u " + username + ":" + password +
        #    " -X POST \"" + server + "/studies\" "
        
        apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
        apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
        print(apiPostCmd)
        study_creation_query = (
            apiPostCmd + "/studies\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d \"{ \\\"data\\\": "
            "{ \\\"type\\\": \\\"studies\\\", "
            "\\\"attributes\\\": "
            "{ \\\"title\\\": \\\"" + title + "\\\", "
            "\\\"description\\\": \\\"" + description + "\\\", "
            "\\\"person_responsible_id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"policy\\\": "
            "{ \\\"access\\\": \\\"download\\\", "
            "\\\"permissions\\\": [ { "
            "\\\"resource\\\": "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" }, "
            "\\\"access\\\": \\\"view\\\" } ] } }, "
            "\\\"relationships\\\": "
            "{ \\\"investigation\\\": "
            "{ \\\"data\\\": "
            "{ \\\"id\\\": \\\"" + str(investigationid) + "\\\", "
            "\\\"type\\\": \\\"investigations\\\" } }, "
            "\\\"creators\\\": "
            "{ \\\"data\\\": [ { "
            "\\\"id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"type\\\": \\\"people\\\" } ] } } }}\""
        )
        print(study_creation_query)
        
        status = self.__seekapi.callAPI(study_creation_query)
        objects = self.__seekapi.runGetQuery("/studies")
        object_id = 0
        for object in range(0, len(objects["data"])):
            #print(object)
            ti = objects["data"][object]["attributes"]["title"]
            if ti==title:
                object_id = int(objects["data"][object]["id"])
   
        study_id2 = object_id
        print('study_id 2:', study_id2)
        
        # The following does not work
        title_3 = 'test_upload_study_c'
        new_study_json = self.__createStudyDic(userid, projectid,investigationid, title_3, description)
        study_json_str = json.dumps(new_study_json)
        study_creation_query = (
            apiPostCmd + "/studies\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d " + study_json_str
        )
        print(study_creation_query)
        status = self.__seekapi.callAPI(study_creation_query)
        objects = self.__seekapi.runGetQuery("/studies")
        object_id = 0
        for object in range(0, len(objects["data"])):
            #print(object)
            ti = objects["data"][object]["attributes"]["title"]
            if ti==title_3:
                object_id = int(objects["data"][object]["id"])
   
        study_id3 = object_id
        print('study_id 3:', study_id3)
        
        return status
    
    def createAssay(self, userid, projectid, studyid,
            title, description, assay_type, technology_type, assayname):
        """Creates a new assay in SEEK.

        Arguments:
            username {str} -- SEEK Login name
            password {str} -- SEEK password
            server {str} -- SEEK server URL
            userid {int} -- Creator ID in SEEK
            projectid {int} -- Selected SEEK project ID.
            studyid {int} -- Selected SEEK study ID.
            title {str} -- Title entered when creating a new assay.
            description {str} -- Description entered when creating a new assay.
            assay_type {str} -- The selected assay type when creating a new assay.
            technology_type {str} -- The selected technology type 
            when creating a new assay.
            assayname {str} -- The name of the new assay.
        
        Example
            
        
        
        """
        if self.__checkPermissions(userid, studyid):
            #assay_creation_query = (
            #    "curl -u " + username + ":" + password +
            #    " -X POST \"" + server + "/assays\" "
            
            apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
            apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
            print(apiPostCmd)
            assay_creation_query = (
                apiPostCmd + "/assays\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": "
                "{ \\\"type\\\": \\\"assays\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"assay_class\\\": { \\\"key\\\": \\\"EXP\\\" }, "
                "\\\"assay_type\\\": { \\\"uri\\\": \\\"" + assay_type + "\\\" }, "
                "\\\"technology_type\\\": { \\\"uri\\\": \\\"" +
                technology_type + "\\\" }, "
                "\\\"description\\\": \\\"" + description + "\\\", "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"download\\\", "
                "\\\"permissions\\\": [ { "
                "\\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                "\\\"access\\\": \\\"view\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"study\\\": "
                "{ \\\"data\\\": "
                "{ \\\"id\\\": \\\"" + str(studyid) + "\\\", "
                "\\\"type\\\": \\\"studies\\\" } }, "
                "\\\"creators\\\": "
                "{ \\\"data\\\": [ { "
                "\\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] } } }}\""
            )
            print(assay_creation_query)
            return self.__seekapi.callAPI(assay_creation_query)
        else:
            print("no permission to create assay")
            return False
        
    def __convertKeyValue(self, dicIn):
        ''' Convert key,value in a dictionary to value,key of the dictionary.
        Arguments:
            dicIn: a dictionary, such as
                {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}

        Returns:
            A dictionary whose keys are dicIn's values, while its values are dicIn's keys. For example,
                {'5':'Zika infection', '4':'library prep assay'}
            
        '''
        dicOut = {}
        for k,v in dicIn.items():
            #if d[k] is v: print '\tthey are the same object'
            # example: v = 'http://dmac.mit.edu:3000/assays/5'
            #          id = 5
            id = v.split("/")[-1]
            dicOut[id] = k
        return dicOut    
                
    def getInvestigations(self, project_title, useSeekAPI=True):
        """Get all investigations, regardless through Seek API or SPARQL.
        
        Arguments:
            username: The SEEK username, from request.session.get('username').
            password: The SEEK password, from request.session.get('password').
            storage: The SEEK URL, from request.session.get('storage').
            project_title: a valid project title, or (None, "") for any project.
            
        Returns:
            A dictionary with SEEK investigation id and title, such as,
                {'1': 'investigation2', '2': 'investigation1'}
            
        Example:
            Queries:
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation xlink' | sed -n 's/.*title="\([^"]*\).*/\1/p'
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation2' | sed -n 's/.*href="\([^"]*\).*/\1/p'
                curl -s -u 'username':password 10.159.0.74:3000/investigations.xml | grep -e 'investigation1' | sed -n 's/.*href="\([^"]*\).*/\1/p'
            resultset:
                {'investigation2': 'http://dmac.mit.edu:3000/investigations/1', 'investigation1': 'http://dmac.mit.edu:3000/investigations/2'}
            which is different from the result set returned from the sparql query,
                {'1': rdflib.term.Literal('investigation2'), '2': rdflib.term.Literal('investigation1')}
        """
        if useSeekAPI:
            #investigations = self.__getInvestigationsAPI(project_title)
            investigations = self.__seekapi.getInvestigations(project_title)
            return self.__convertKeyValue(investigations)
        else:
            #return self.__getInvestigationsSPARQL(project_title)
            return self.__sparql.getInvestigations(project_title)
                
    def getStudies(self, investigation_title, useSeekAPI=True):
        """Gets the SEEK studies based on an investigation title.

        Arguments:
            investigation_title: investigation title, such as "investigation1".

        Returns:
            A dictionary with SEEK study IDs and URLs for an investigation, such as 
                assays: 
                    {'2':'Library exraction', '3':'library prep'}
                    
        Notes:
            Now we can generate the result by calling either the SPARQL or Seek API.
        """
        if useSeekAPI:
            if investigation_title is None or investigation_title=="":
                # Maybe we should retrieve all studie, regardless any investigation
                return {}
            
            investigationid = self.__seekapi.getIDfromTitle("/investigations/", investigation_title)
            print('investigation_title,id:',investigation_title, investigationid)
            #studies = self.__getStudiesAPI(investigationid)
            studies = self.__seekapi.getStudies(investigationid)
            # example:  {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}
            return self.__convertKeyValue(studies)
        
        else:
            #return self.__getStudiesSPARQL(investigation_title)
            return self.__sparql.getStudies(investigation_title) 
        
    def getStudiesFromID(self, investigation_id, useSeekAPI=True):
        """Gets the SEEK studies based on an investigation id.

        Arguments:
            investigation_title: investigation title, such as "investigation1".

        Returns:
            A dictionary with SEEK study IDs and URLs for an investigation, such as 
                assays: 
                    {'2':'Library exraction', '3':'library prep'}
                    
        Notes:
            Now we can generate the result by calling either the SPARQL or Seek API.
        """
        if useSeekAPI:
            #studies = self.__getStudiesAPI(investigation_id)
            studies = self.__seekapi.getStudies(investigation_id)
            return self.__convertKeyValue(studies)
        else:
            investigation_title = self.__seekapi.getTitleFromID("/investigations/", investigation_id)
            #return self.__getStudiesSPARQL(investigation_title)
            return self.__sparql.getStudies(investigation_title)
    
    def getAssays(self, study_title, useSeekAPI=True):
        """Gets the SEEK assays based on a study title.

        Arguments:
            study: Study title, such as "library prep" study.

        Returns:
            A dictionary with SEEK assay IDs and URLs for a study, such as 
                assays: 
                    {'5':'Zika infection', '4':'library prep assay'}
                    
        Notes:
            Now we can generate the result by calling either the SPARQL or Seek API.
        """
        if useSeekAPI:
            if study_title is None or study_title=="":
                # Maybe we should retrieve all assays, regardless any study.
                return {}
            
            studyid = self.__seekapi.getIDfromTitle("/studies/", study_title)
            print('study_title,id:',study_title, studyid)
            #assays = self.__getAssaysAPI(studyid)
            assays = self.__seekapi.getAssays(studyid)
            # example:  {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}
            return self.__convertKeyValue(assays)
        
        else:
            #return self.__getAssaysSPARQL(study_title)
            return self.__sparql.getAssays(study_title)
        
    
    def getAssaysFromID(self, study_id, useSeekAPI=True):
        """Gets the SEEK assays based on an study id.

        Arguments:
            study_title: study title, such as "study1".

        Returns:
            A dictionary with SEEK assay IDs and URLs for an study, such as 
                assays: 
                    {'2':'Library exraction', '3':'library prep'}
                    
        Notes:
            Now we can generate the result by calling either the SPARQL or Seek API.
        """
        if useSeekAPI:
            study_id = str(study_id)
            #assays = self.__getAssaysAPI(study_id)
            assays = self.__seekapi.getAssays(study_id)
            return self.__convertKeyValue(assays)
        else:
            study_title = self.__seekapi.getTitleFromID("/studies/", study_id)
            #return self.__getStudiesSPARQL(study_title)
            return self.__sparql.getStudies(study_title)
    
    def getAPIsamples(self, assayid):
        """Gets the SEEK ssamples based on a assay.
        
        Arguments:
            username: The SEEK username.
            password: The SEEK password.
            storage: The SEEK URL.
            assay_id: assay id, either 'http://dmac.mit.edu:3000/assay/3' or '3'

        Returns:
            A dictionary with SEEK sample IDs and URLs.
        """
        return self.__seekapi.getSamples(assayid)
        
    
    def getSamples(self, assay_title):
        """Gets the SEEK assays based on a study title.

        Arguments:
            study: Study title, such as "library prep" study.

        Returns:
            A dictionary with SEEK assay IDs and URLs for a study, such as 
                assays: 
                    {'5':'Zika infection', '4':'library prep assay'}
                    
        Notes:
            Now we can generate the result by calling either the SPARQL or Seek API.
        """
        useSeekAPI = True
        if useSeekAPI:
            if assay_title is None or assay_title=="":
                # Maybe we should retrieve all assays, regardless any study.
                return {}
            
            assayid = self.__seekapi.getIDfromTitle("/assays/", assay_title)
            print('assay_title,id:',assay_title, assayid)
            #samples = self.getAPIsamples(assayid)
            samples = self.__seekapi.getSamples(assayid)
            # example:  {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}
            return self.__convertKeyValue(samples)
        
        else:
            #return self.__getSPARQLsamples(assay_title)
            return self.__sparql.getSamples(assay_title)
            
            
    def __get_investigation_folders(self):
        """Gets the user's investigation folders from the storage URL,
        This will be shown on the homepage for storing existing Galaxy 
        histories.
        
        Modified from views.get_investigation_folders()

        Arguments:
            storage: The URL of the ISA structure storage.
            storagetype: The storage type (SEEK or Owncloud)
            username: The username of the ISA structure storage.
            password: The password of the ISA structure storage.

        Returns:
            A list of investigation folder and a list of study folders.
        """
        investigations = self.getInvestigations("")
        print("investigations:", investigations)
        # example
        #   {'1': 'investigation2', '2': 'investigation1'}
        
        oc_folders = ""
        inv_folders = []
        for dummyii, it in investigations.items():
            inv_folders.append(it)
            #seek_sparql_studies(it)
            #seek_study = self.getStudies(it)
        return inv_folders, oc_folders
    
    def __get_study_folders(self, investigation):
        """Gets the study folders based on the selected investigation from the
        homepage. This is used to store existing Galaxt histories.

        Arguments:
            storage: The URL of the ISA structure storage.
            username: The username of the ISA structure storage.
            password: The password of the ISA structure storage.
            investigation: SEEK investigation title?

        Returns:
            A list of investigationa folders and a list of study folders.
        """
        #seek_inv = seek_sparql_investigations("")
        seek_inv = self.getInvestigations("")
        inv_folders = []
        for dummyii, it in seek_inv.items():
            inv_folders.append(it)
            
        it = investigation    
        seek_study = self.getStudies(it)
        oc_folders = []
        for st, dummysi in seek_study.items():
            oc_folders.append(st)
        return oc_folders, inv_folders
    
    def get_investigations_folders(self, investigation):
        """Gets the study folders based on the selected investigation from the
        homepage. This is used to store existing Galaxt histories.

        Arguments:
            storage: The URL of the ISA structure storage.
            username: The username of the ISA structure storage.
            password: The password of the ISA structure storage.
            investigation: SEEK investigation title?

        Returns:
            A list of investigations and a list of study folders.
        """
        folders = []
        investigations = []
        if investigation is not None and investigation != "":
            oc_folders, inv_folders = self.__get_study_folders(investigation)
        else:
            inv_folders, oc_folders = self.__get_investigation_folders()
            
        for inv in inv_folders:
            investigation_name = inv.replace('/remote.php/webdav/', '').replace('/', '')
            if "." not in investigation_name:
                new = investigation_name
                investigations.append(new)

        for oc in oc_folders:
            study = oc.replace('/remote.php/webdav/', '')
            study = study.replace('/', '').replace(investigation, '')
            if "." not in study:
                new = study
                folders.append(new)
 
        folders = list(filter(None, folders))
        investigations = list(filter(None, investigations))
        return investigations,folders
    
    
    def investigation(self, investigationIn):
        """Get studies based on the investigation that was selected 
        in the indexing menu.

        Arguments:
            investigationIn: = request.POST.get('folder') or request.POST.get('selected_folder')
        """
        #inv_names = self.__getInvestigationsAPI('')
        inv_names = self.__seekapi.getInvestigations('')
        oc_folders = inv_names.keys()
        oc_list = list(filter(None, oc_folders))
        oc_studies = ""
        folders = []
        studies = []
        if oc_list:
            for oc in oc_folders:
                folders.append(oc)
                
            folders = list(filter(None, folders))
            if(investigationIn != "" and investigationIn is not None):
                oc_studies = []
                for it, dummyii in inv_names.items():
                    if it == investigationIn:
                        #studydict = self.__getStudiesAPI(it)
                        studydict = self.__seekapi.getStudies(it)
                for st, dummysi in studydict.items():
                    oc_studies.append(st)
            
            if oc_studies != "":
                oc_studies = list(filter(None, oc_studies))
                for s in oc_studies:
                    studies.append(s)
                    
                studies = list(filter(None, studies))
                return oc_list, oc_studies, folders, studies
            else:
                return oc_list, oc_studies, folders, studies

        return oc_list, oc_studies, folders, studies
    
    
    def store_results(self, column, datafiles, server, username, password, storage,
        workflowid, groups, resultid, investigations, date,
        historyid, storagetype):
        """Store input and output files that where created or used in a Galaxy workflow.

        Arguments:
            column: Column number containing 1 or 3. 
            1 for data and 3 for metadata.
            datafiles: A List of datafiles
            server: The Galaxy server URL.
            username: Username used for the storage location.
            password: Password used for the storage location.
            storage: The URL for the storage location.
            workflowid: The Galaxy workflow ID.
            groups: A list of studies.
            resultid: The result ID. 
            investigations: A list of investigations.
            date: The current date and time.
            historyid: The Galaxy history ID.
            storagetype: The type of storage (SEEK or Owncloud)
        """
        if not groups:
            groups.append('Phenomenal')
        assay_id_list = []
        o = 0
        for name in datafiles[column]:
            cont = subprocess.Popen([
                "curl -s -k " + server + datafiles[column-1][o]
            ], stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            old_name = name.replace('/', '_').replace(' ', '_')
            with open(username + "/" + old_name, "w") as outputfile:
                outputfile.write(cont)
            new_name = sha1sum(username + "/" + old_name) + "_" + old_name
            os.rename(username + "/" + old_name, username + "/" + new_name)
            # export = gi.histories.export_history(
            #             historyid,
            #             include_deleted=False,
            #             include_hidden=True)
            # home = str(Path.home())+ "/"
            # call(["touch", home + username + "/" + historyid + ".tar"])
            # f = open(home + username + "/" + historyid + ".tar", 'rb+')
            # gi.histories.download_history(
            #     historyid,
            #     export,
            #     f)
            # shaname = sha1sum(f.name) + "_" + f.name.split('/')[-1]
            # os.rename(f.name, home + username + "/" +
            #         strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)
            # history_tar = strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname
            # url.append(strftime("%d_%b_%Y_%H:%M:%S", gmtime()) + "_" + shaname)

            o += 1
            
        
        studies = self.runGetQuery("/studies")
        
        for s in range(0, len(studies["data"])):
            study_name = studies["data"][s]["attributes"]["title"]
            if study_name in groups:
                studyid = studies["data"][s]["id"]
                study_title = study_name
                
                projects = self.runGetQuery("/projects")
                
                for p in range(1, len(projects["data"]) + 1):
                    
                    apiurl = "/projects/" + str(p)
                    project =self.runGetQuery(apiurl)
                    
                    for ps in range(0, len(project["data"]["relationships"]["studies"]["data"])):
                        if studyid == project["data"]["relationships"]["studies"]["data"][ps]["id"]:
                            projectid = str(p)
                if column == 1:
                    assay_title = (study_title + "__result__" + str(resultid))
                    
                    self.createAssay(
                        1, projectid, studyid, assay_title,
                        "Results for ID: " + str(resultid),
                        "http://jermontology.org/ontology/JERMOntology#Experimental_assay_type",
                        "http://jermontology.org/ontology/JERMOntology#Technology_type", assay_title
                    )
                    
                assays = self.runGetQuery("/assays")
                
                mime = magic.Magic(mime=True)
                content_type = mime.from_file(username + "/" + new_name)
                for ail in range(0, len(assays["data"])):
                    assay_id_list.append(int(assays["data"][ail]["id"]))
                for galaxyfile in os.listdir(username):
                    tags = []
                    self.seekupload(
                        galaxyfile,
                        username + "/" + galaxyfile,
                        str(galaxyfile), content_type, 1, projectid,
                        str(max(assay_id_list)), workflowid, tags
                    )
    
    def seekupload(self, title, file, filename,
               content_type, userid, projectid, assayid, description, tags):
        """Uploads data files to an assay.

        Arguments:
            username: SEEK username.
            password: SEEK password.
            storage: SEEK URL
            title: Title of the uploaded data file.
            file: The file that will be uploaded to the SEEK server.
            filename: Name of the uploaded file.
            content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
            userid: SEEK user ID of the data uploader.
            projectid: SEEK project ID related to the data file.
            assayid: SEEK assay ID related to the data file.
            description: The description of the data.
            
        Output
            msg, any message
            status, 0 or 1 for successful uploading into Seek
            df_info, returned dictionary for the data file
            datafile_url, such as "/data_files/19/", which is the Url link to the seek server to access the data file,
                such as "/data_files/19", which should be added to the root url of the seek server.
        """
        # Step 1. Define the query for running the Seek API
        apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
        apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
        #print(apiPostCmd)
        '''
        data_instance_query = (
            #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
            #" -X POST \"" + self.__seekapi.__server +
            apiPostCmd +
            "/data_files\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
            "\\\"attributes\\\": "
            "{ \\\"title\\\": \\\"" + title + "\\\", "
            "\\\"description\\\": \\\"" + description + "\\\", "
            #"\\\"tags\\\": ["
            #"\\\"" + tags[0] + "\\\", "
            #"\\\"" + tags[1] + "\\\""
            #"], "
            "\\\"license\\\": \\\"CC-BY-4.0\\\", "
            "\\\"content_blobs\\\": [ { "
            "\\\"original_filename\\\": \\\"" + filename + "\\\", "
            "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
            "\\\"policy\\\": "
            #"{ \\\"access\\\": \\\"download\\\", "
            "{ \\\"access\\\": \\\"no_access\\\", "
            "\\\"permissions\\\": [ "
            "{ \\\"resource\\\": "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" }, "
            #"\\\"access\\\": \\\"edit\\\" } ] } }, "
            "\\\"access\\\": \\\"manage\\\" } ] } }, "
            "\\\"relationships\\\": "
            "{ \\\"creators\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"type\\\": \\\"people\\\" } ] }, "
            "\\\"projects\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" } ] }"
            #", \\\"assays\\\": "
            #"{ \\\"data\\\": [ "
            #"{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
            #"\\\"type\\\": \\\"assays\\\" } ] } "
            "} }} \""
        )
        refer to: What's the following error: access_type is too permissive?
        The access policy below allows public to be "download" and project to be "edit",
        which is changed to public to be "no_access" and project to be "download",
        '''
        if assayid is None or assayid<=0:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/data_files\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + filename + "\\\", "
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] }"
                #", \\\"assays\\\": "
                #"{ \\\"data\\\": [ "
                #"{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                #"\\\"type\\\": \\\"assays\\\" } ] } "
                "} }} \""
            )
        else:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/data_files\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + filename + "\\\", "
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] }"
                ", \\\"assays\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                "\\\"type\\\": \\\"assays\\\" } ] } "
                "} }} \""
            )
            
        
        print(data_instance_query)
        #return '',0,None
        
        # Step 2. Run the Seek API to post the data file 
        #status = self.__seekapi.callAPI(data_instance_query)
        exitcode, out, err = self.__seekapi.callCmdline(data_instance_query)
        df_info = out
        datafile_url = None
        if exitcode==0:
            msg = 'data file uploaded successfully'
            print(out)
            #return msg, 1, df_info
        else:
            msg = 'Error: data file not uploaded.' 
            print(msg, err)
            status = 0
            return msg, status, df_info, datafile_url
        
        #if not status:
        #    msg = 'data file not uploaded'
        #    print(msg)
        #    return msg, status
        
        # Step 3. Get the content blob for the data file, which is just uploaded 
        seek_data_ids = []  # List with data_file ids
        data_files = self.__seekapi.runGetQuery("/data_files")
        for df in range(0, len(data_files["data"])):
            #print(df)
            seek_data_ids.append(int(data_files["data"][df]["id"]))
    
        apiurl = "/data_files/" + str(max(seek_data_ids))
        #print(apiurl)
        #such as "/data_files/19"
        content_blob = self.__seekapi.runGetQuery(apiurl)
        #print(content_blob)
    
        content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
        #print(content_blob_url)
        # such as http://dmac.mit.edu:3000/data_files/19/content_blobs/36
        self.__seekapi.callFileAPI(content_blob_url, file)
        
        msg = 'okay'
        status = 1
        datafile_url = apiurl
        return msg, status, df_info, datafile_url
    
    def seekupload_url(self, title, file, filename,
               content_type, userid, projectid, assayid, description, tags):
        """Uploads data files to an assay.

        Arguments:
            username: SEEK username.
            password: SEEK password.
            storage: SEEK URL
            title: Title of the uploaded data file.
            file: The file that will be uploaded to the SEEK server.
            filename: Name of the uploaded file.
            content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
            userid: SEEK user ID of the data uploader.
            projectid: SEEK project ID related to the data file.
            assayid: SEEK assay ID related to the data file.
            description: The description of the data.
        """
        # Step 1. Define the query for running the Seek API
        apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
        apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
        #print(apiPostCmd)
        data_instance_query = (
            #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
            #" -X POST \"" + self.__seekapi.__server +
            apiPostCmd +
            "/data_files\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
            "\\\"attributes\\\": "
            "{ \\\"title\\\": \\\"" + title + "\\\", "
            "\\\"description\\\": \\\"" + description + "\\\", "
            #"\\\"tags\\\": ["
            #"\\\"" + tags[0] + "\\\", "
            #"\\\"" + tags[1] + "\\\""
            #"], "
            "\\\"license\\\": \\\"CC-BY-4.0\\\", "
            "\\\"content_blobs\\\": [ { "
            "\\\"original_filename\\\": \\\"" + filename + "\\\", "
            "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
            "\\\"policy\\\": "
            #"{ \\\"access\\\": \\\"download\\\", "
            "{ \\\"access\\\": \\\"no_access\\\", "
            "\\\"permissions\\\": [ "
            "{ \\\"resource\\\": "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" }, "
            #"\\\"access\\\": \\\"edit\\\" } ] } }, "
            "\\\"access\\\": \\\"manage\\\" } ] } }, "
            "\\\"relationships\\\": "
            "{ \\\"creators\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"type\\\": \\\"people\\\" } ] }, "
            "\\\"projects\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" } ] }, "
            "\\\"assays\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
            "\\\"type\\\": \\\"assays\\\" } ] } } }} \""
        )
        
        #print(data_instance_query)
        
        # Step 2. Run the Seek API to post the data file 
        #status = self.__seekapi.callAPI(data_instance_query)
        exitcode, out, err = self.__seekapi.callCmdline(data_instance_query)
        df_info = out
        if exitcode==0:
            msg = 'data file uploaded successfully'
            print(out)
        else:
            msg = 'Error: data file not uploaded.' 
            print(msg, err)
            status = 0
            return msg, status, df_info
        
        #if not status:
        #    msg = 'data file not uploaded'
        #    print(msg)
        #    return msg, status
        
        # Step 3. Get the content blob for the data file, which is just uploaded 
        seek_data_ids = []  # List with data_file ids
        data_files = self.__seekapi.runGetQuery("/data_files")
        for df in range(0, len(data_files["data"])):
            #print(df)
            seek_data_ids.append(int(data_files["data"][df]["id"]))
    
        apiurl = "/data_files/" + str(max(seek_data_ids))
        #print(apiurl)
        #such as "/data_files/19"
        content_blob = self.__seekapi.runGetQuery(apiurl)
        #print(content_blob)
    
        content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
        #print(content_blob_url)
        # such as http://dmac.mit.edu:3000/data_files/19/content_blobs/36
        self.__seekapi.callFileAPI(content_blob_url, file)
        
        msg = 'okay'
        status = 1
        return msg, status, df_info


    def getPage(self, queryurl):
        """Get the webpage for the url.
    
        Arguments:
            url, the url of the webpage.

        Returns:
            the webpage
            
        Example:
            study_command:
                curl -u 'username':password -X GET 10.159.0.74:3000/studies/5/
            
        """
        webpage = self.__seekapi.runGetPage(queryurl)
        return webpage
    
    def handle_uploaded_file_seek(self, infile, outfilename):
        ''' 
        Notes:
            migrated from def seek(request) in MyFair project.
        '''
        dest = open(outfilename, 'wb')
        for chunk in infile.chunks():
            dest.write(chunk)
        dest.close()

    def uploadFile_intoSeek(self, request, username, userid, project_id, assay_id, tags):
        ''' Upload a data file into Seek system by using Seek API.
        Input:
            username,  user_seek['username'] or request.session.get('username')
            userid, user_seek['user_id'] or self.__getSeekPersonID(user_seek['username'])
            project_id,
            assay_id,
            tags, not in use
        Output:
         
        
        
        Notes:
            migrated from def seek(request) in MyFair project.
        '''
        #infile = request.FILES["uploadfiles"]
        infile = request.FILES['file']
        content_type = infile.content_type
        print('content_type:', content_type)
            
        # define output file name
        outfilename, upload_full_path = self.__defineUploadPath(username, infile.name)
    
        # upload file to a temp file 
        self.handle_uploaded_file_seek(infile, outfilename)
                
        # use API to upload file into Seek
        #datatitle = request.POST.get('datatitle')
        datatitle = 'testdatafile'
        #description = request.POST.get('description')
        description = 'test data file uploading'
        
        return 
        
        self.seekupload(
            #seekupload(
            #request.session.get('username'),
            #request.session.get('password'),
            #request.session.get('storage'),
            datatitle,
            outfilename,
            infile.name,
            content_type,
            userid,
            project_id,
            assay_id,
            description,
            tags
        )
    
        # remove temp folder and file
        call(["rm", "-r", outfilename])
        call(["rm", "-r", upload_full_path])
        
    def __defineUploadPath(self, username, infilename):
        upload_dir = (
            "tmp" +
            hashlib.md5(username.encode('utf-8')).hexdigest()
        )
        
        # such as tmp03a73f3e7c9a7b38d196cd34c072567e
        # print(upload_dir)
        
        upload_full_path = os.path.join(settings.MEDIA_ROOT, upload_dir)
        if not os.path.exists(upload_full_path):
            os.makedirs(upload_full_path)
    
        outfilename = os.path.join(upload_full_path, infilename)
        while os.path.exists(outfilename):
            infilename = '_' + infilename
            outfilename = os.path.join(upload_full_path, infilename)
            
        return outfilename, upload_full_path
        
        
    def testCreateStudy(self, user_seek):
        ''' Test creating a study by using Seek API.
        Input:
            user_seek: the login user info
            
        Output
            status = True or False
        '''
        userid = user_seek['user_id']
        projectid = user_seek['projectid']
        investigationid = 1
        title = 'testStudy2'
        description = 'try testStudy2'
        studyname = 'testStudy 2'
        return self.createStudy(userid, projectid,investigationid, title, description, studyname)
    
    def testDeleteStudy(self, user_seek, studyid):
        ''' Test deleting a study by using Seek API.
        Input:
            user_seek: the login user info
            studyid: the primary key of a study
        Output
            status = True or False
        '''
        print('deleting study to be implemented')
        
    def testCreateAssay(self, user_seek):
        ''' Test creating a study by using Seek API.
        Input:
            user_seek: the login user info
            
        Output
            status = True or False
        '''
        userid = user_seek['user_id']
        projectid = user_seek['projectid']
        
        studyid = 7
        title = 'testAssay2'
        description = 'test testAssay2' 
        assayname = 'testAssay2'
        assay_type = 'http://jermontology.org/ontology/JERMOntology#DNA_sequencing'
        technology_type = 'http://jermontology.org/ontology/JERMOntology#RNA-Seq'
        
        return self.createAssay(userid, projectid, studyid,
            title, description, assay_type, technology_type, assayname)
    
    
    def testSeekupload(self, user_seek):
        ''' Test creating a study by using Seek API.
        Input:
            user_seek: the login user info
            
        Output
            status = True or False
        '''
        userid = user_seek['user_id']
        projectid = user_seek['projectid']
        
        studyid = 7
        title = 'testAssay2'
        description = 'test testAssay2' 
        assayname = 'testAssay2'
        assay_type = 'http://jermontology.org/ontology/JERMOntology#DNA_sequencing'
        technology_type = 'http://jermontology.org/ontology/JERMOntology#RNA-Seq'
        
        return self.createAssay(userid, projectid, studyid,
            title, description, assay_type, technology_type, assayname)
        
    def seekuploadSOP(self, title, fullfilename, originalfilename,
               content_type, userid, projectid, assayid, description, tags):
        """Uploads SOP to Seek.

        Arguments:
            username: SEEK username.
            password: SEEK password.
            storage: SEEK URL
            title: Title of the uploaded data file.
            fullfilename: The file name with path on the storage server that will be uploaded to the SEEK server.
            originalfilename: Name of the uploaded file, which may contain space in it.
            content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
            userid: SEEK user ID of the data uploader.
            projectid: SEEK project ID related to the data file.
            assayid: SEEK assay ID related to the data file.
            description: The description of the data.
            
        Output
            msg, any message
            status, 0 or 1 for successful uploading into Seek
            df_info, returned dictionary for the data file
            datafile_url, such as "/data_files/19/", which is the Url link to the seek server to access the data file,
                such as "/data_files/19", which should be added to the root url of the seek server.
        """
        if not os.path.exists(fullfilename):
            msg = "Error: file not available: ", fullfilename 
            print(msg)
            status = 0
            return msg, status, None, None
        
        # Step 1. Define the query for running the Seek API
        apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
        apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
        #print(apiPostCmd)
        '''
        data_instance_query = (
            #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
            #" -X POST \"" + self.__seekapi.__server +
            apiPostCmd +
            "/sops\" "
            "-H \"accept: application/json\" "
            "-H \"Content-Type: application/json\" "
            "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"sops\\\", "
            "\\\"attributes\\\": "
            "{ \\\"title\\\": \\\"" + title + "\\\", "
            "\\\"description\\\": \\\"" + description + "\\\", "
            #"\\\"tags\\\": ["
            #"\\\"" + tags[0] + "\\\", "
            #"\\\"" + tags[1] + "\\\""
            #"], "
            "\\\"license\\\": \\\"CC-BY-4.0\\\", "
            "\\\"content_blobs\\\": [ { "
            "\\\"original_filename\\\": \\\"" + originalfilename + "\\\", "
            "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
            "\\\"policy\\\": "
            #"{ \\\"access\\\": \\\"download\\\", "
            "{ \\\"access\\\": \\\"no_access\\\", "
            "\\\"permissions\\\": [ "
            "{ \\\"resource\\\": "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" }, "
            #"\\\"access\\\": \\\"edit\\\" } ] } }, "
            "\\\"access\\\": \\\"manage\\\" } ] } }, "
            "\\\"relationships\\\": "
            "{ \\\"creators\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
            "\\\"type\\\": \\\"people\\\" } ] }, "
            "\\\"projects\\\": "
            "{ \\\"data\\\": [ "
            "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
            "\\\"type\\\": \\\"projects\\\" } ] }"
            #", \\\"assays\\\": "
            #"{ \\\"data\\\": [ "
            #"{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
            #"\\\"type\\\": \\\"assays\\\" } ] } "
            "} }} \""
        )
        
        refer to: What's the following error: access_type is too permissive?
        The access policy below allows public to be "download" and project to be "edit",
        which is changed to public to be "no_access" and project to be "download",
        
        '''
        if assayid is None or assayid<=0:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/sops\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"sops\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + originalfilename + "\\\", "
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] }"
                #", \\\"assays\\\": "
                #"{ \\\"data\\\": [ "
                #"{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                #"\\\"type\\\": \\\"assays\\\" } ] } "
                "} }} \""
            )
        else:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/sops\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"sops\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + originalfilename + "\\\", "
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] }"
                ", \\\"assays\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                "\\\"type\\\": \\\"assays\\\" } ] } "
                "} }} \""
            )
        print(data_instance_query)
        #return '',0,None
        
        # Step 2. Run the Seek API to post the data file 
        #status = self.__seekapi.callAPI(data_instance_query)
        exitcode, out, err = self.__seekapi.callCmdline(data_instance_query)
        object_info = out
        object_url = None
        if exitcode==0:
            msg = 'SOP uploaded successfully'
            print(out)
            #return msg, 1, object_info
        else:
            msg = 'Error: SOP not uploaded.' 
            print(msg, err)
            status = 0
            return msg, status, object_info, object_url
        
        #if not status:
        #    msg = 'data file not uploaded'
        #    print(msg)
        #    return msg, status
        
        # Step 3. Get the content blob for the data file, which is just uploaded 
        seek_data_ids = []  # List with data_file ids
        sops = self.__seekapi.runGetQuery("/sops")
        for df in range(0, len(sops["data"])):
            #print(df)
            seek_data_ids.append(int(sops["data"][df]["id"]))
    
        apiurl = "/sops/" + str(max(seek_data_ids))
        #print(apiurl)
        #such as "/sops/19"
        content_blob = self.__seekapi.runGetQuery(apiurl)
        print(content_blob)
    
        content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
        #print(content_blob_url)
        # such as http://dmac.mit.edu:3000/sops/19/content_blobs/36
        # upload file to the Seek folder
        self.__seekapi.callFileAPI(content_blob_url, fullfilename)
        
        msg = 'okay'
        status = 1
        object_url = apiurl
        return msg, status, object_info, object_url
    
    
    def seekupload_dfurl(self, title, fullfilename, originalfilename,
               content_type, userid, projectid, assayid, description, tags, weburl):
        """Upload a data file url into Seek by calling the Seek API.
        Refer to: https://codings.genenets.com/dokuwiki/doku.php?id=computer:websites:dmac:datafile

        Arguments:
            username: SEEK username.
            password: SEEK password.
            storage: SEEK URL
            title: Title of the uploaded data file.
            fullfilename: The file name with path on the storage server that will be uploaded to the SEEK server.
            originalfilename: Name of the uploaded file, which may contain space in it.
            originalfilename: Name of the uploaded file.
            content_type: Content type of the uploaded file (e.g. pdf, xml etc.)
            userid: SEEK user ID of the data uploader.
            projectid: SEEK project ID related to the data file.
            assayid: SEEK assay ID related to the data file.
            description: The description of the data.
            
        Output:
            msg,
            status,
            object_url, 
            df_info, such as,
                {
                    u'type': u'data_files',
                    u'id': u'158',
                    u'relationships': {
                        u'investigations': {u'data': []},
                        u'people': {u'data': [{u'type': u'people', u'id': u'9'}]},
                        u'publications': {u'data': []},
                        u'assays': {u'data': []},
                        u'submitter': {u'data': [{u'type': u'people', u'id': u'9'}]},
                        u'creators': {u'data': [{u'type': u'people', u'id': u'9'}]},
                        u'studies': {u'data': []},
                        u'events': {u'data': []},
                        u'projects': {u'data': [{u'type': u'projects', u'id': u'1'}]}
                    },
                    u'links': {u'self': u'/data_files/158?version=1'},
                    u'meta': {
                        u'base_url': u'https://kibcc2.mit.edu',
                        u'uuid': u'78be90e0-7a88-0138-f22a-000c29258bdc',
                        u'modified': u'2020-05-17T16:22:05.000Z',
                        u'api_version': u'0.2',
                        u'created': u'2020-05-17T16:22:05.000Z'
                    },
                    u'attributes': {
                        u'content_blobs': [{
                            u'original_filename': u'20181001_A549_BaP_R1_TMT10plex_pY_AC41_AC34.xlsx',
                            u'url': None,
                            u'md5sum': None,
                            u'link': u'https://kibcc2.mit.edu/data_files/158/content_blobs/436',
                            u'content_type': u'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            u'size': None,
                            u'sha1sum': None
                        }],
                        u'description': u'File uploaded from DropZone',
                        u'license': u'CC-BY-4.0',
                        u'tags': None,
                        u'created_at': u'2020-05-17T16:22:06.000Z',
                        u'title': u'A.MSP-20200304-454_20181001_A549_BaP_R1_TMT10plex_pY_AC41_AC34.xlsx',
                        u'updated_at': u'2020-05-17T16:22:06.000Z',
                        u'latest_version': 1,
                        u'other_creators': None,
                        u'revision_comments': None,
                        u'versions': [{u'url': u'https://kibcc2.mit.edu/data_files/158?version=1', u'revision_comments': None, u'version': 1}],
                        u'version': 1,
                        u'policy': {
                            u'access': u'no_access',
                            u'permissions': [{u'access': u'download', u'resource': {u'type': u'projects', u'id': u'1'}}]
                        }
                    }    
                }
        """
        # Step 1. Define the query for running the Seek API
        apiPostCmd = self.__seekapi.apiPost()       # such as "curl -u username:password -X POST \"server\""
        apiPostCmd = apiPostCmd[:-1]                # becomes "curl -u username:password -X POST \"server"
        #print(apiPostCmd)
        if assayid is None or assayid<=0:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/data_files\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + originalfilename + "\\\", "
            
                # If you add the following line into the call,
                # an error message will show:  {"error":"bad upload"}
                # refer to: http://www.visualseq.net/dokuwiki/doku.php?id=computer:websites:dmac:datafile#step_1_select_an_example
                #"\\\"url\\\": \\\"" + weburl + "\\\", "
                #"\\\"md5sum\\\": \\\"" + md5sum + "\\\", "
                #"\\\"sha1sum\\\": \\\"" + sha1sum + "\\\", "
                #"\\\"link\\\": \\\"" + link + "\\\", "
                #"\\\"size\\\": \\\"" + size + "\\\", "
            
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] } "
                #"\\\"type\\\": \\\"projects\\\" } ] }, "
                #",\\\"assays\\\": "
                #"{ \\\"data\\\": [ "
                #"{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                #"\\\"type\\\": \\\"assays\\\" } ] } } }} \""
                "} }} \""
            )
        else:
            data_instance_query = (
                #"curl -u " + self.__seekapi.__username + ":" + self.__seekapi.__password +
                #" -X POST \"" + self.__seekapi.__server +
                apiPostCmd +
                "/data_files\" "
                "-H \"accept: application/json\" "
                "-H \"Content-Type: application/json\" "
                "-d \"{ \\\"data\\\": { \\\"type\\\": \\\"data_files\\\", "
                "\\\"attributes\\\": "
                "{ \\\"title\\\": \\\"" + title + "\\\", "
                "\\\"description\\\": \\\"" + description + "\\\", "
                #"\\\"tags\\\": ["
                #"\\\"" + tags[0] + "\\\", "
                #"\\\"" + tags[1] + "\\\""
                #"], "
                "\\\"license\\\": \\\"CC-BY-4.0\\\", "
                "\\\"content_blobs\\\": [ { "
                "\\\"original_filename\\\": \\\"" + originalfilename + "\\\", "
            
                # If you add the following line into the call,
                # an error message will show:  {"error":"bad upload"}
                # refer to: http://www.visualseq.net/dokuwiki/doku.php?id=computer:websites:dmac:datafile#step_1_select_an_example
                #"\\\"url\\\": \\\"" + weburl + "\\\", "
                #"\\\"md5sum\\\": \\\"" + md5sum + "\\\", "
                #"\\\"sha1sum\\\": \\\"" + sha1sum + "\\\", "
                #"\\\"link\\\": \\\"" + link + "\\\", "
                #"\\\"size\\\": \\\"" + size + "\\\", "
            
                "\\\"content_type\\\": \\\"" + content_type + "\\\" } ], "
                "\\\"policy\\\": "
                "{ \\\"access\\\": \\\"no_access\\\", "
                "\\\"permissions\\\": [ "
                "{ \\\"resource\\\": "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" }, "
                #"\\\"access\\\": \\\"download\\\" } ] } }, "
                "\\\"access\\\": \\\"manage\\\" } ] } }, "
                "\\\"relationships\\\": "
                "{ \\\"creators\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(userid) + "\\\", "
                "\\\"type\\\": \\\"people\\\" } ] }, "
                "\\\"projects\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(projectid) + "\\\", "
                "\\\"type\\\": \\\"projects\\\" } ] } "
                #"\\\"type\\\": \\\"projects\\\" } ] }, "
                ",\\\"assays\\\": "
                "{ \\\"data\\\": [ "
                "{ \\\"id\\\": \\\"" + str(assayid) + "\\\", "
                "\\\"type\\\": \\\"assays\\\" } ] } "
                "} }} \""
            )
            
            
        print('seekupload_dfurl command:')
        print(data_instance_query)
        
        # Step 2. Run the Seek API to post the data file 
        #status = self.__seekapi.callAPI(data_instance_query)
        exitcode, out, err = self.__seekapi.callCmdline(data_instance_query)
        
        df_info = out
        if exitcode==0:
            msg = 'data file uploaded successfully'
            print(out)
        else:
            msg = 'Error: data file not uploaded.' 
            print(msg, err)
            status = 0
            return msg, status, df_info
        
        #if not status:
        #    msg = 'data file not uploaded'
        #    print(msg)
        #    return msg, status
        
        # Step 3. Get the content blob for the data file, which is just uploaded 
        data_files = self.__seekapi.runGetQuery("/data_files")
        df_id = 0
        for df in range(0, len(data_files["data"])):
            #print(df)
            ti = data_files["data"][df]["attributes"]["title"]
            if ti==title:
                df_id = int(data_files["data"][df]["id"])
            
        #print("Data file id now: ", df_id, max(seek_data_ids))
        print("Data file id now: ", df_id)
        if df_id==0:
            msg = "Error: data file not found in DB:" + title
            print(msg)
            return msg, 0, None, None
    
        apiurl = "/data_files/" + str(df_id)
        print(apiurl)
        #such as "/data_files/19"

        #content_blob = self.__seekapi.runGetQuery(apiurl)
        #print(content_blob)
        #content_blob_url = content_blob["data"]["attributes"]["content_blobs"][0]["link"]
        df_dic = self.__seekapi.runGetQuery(apiurl)
        #print(df_dic)
        df_info = df_dic["data"]
        #print(df_info)
        content_blob = df_info["attributes"]["content_blobs"][0]
        content_blob_url = content_blob["link"]
        print(content_blob_url)
        # such as https://kibcc2.mit.edu/data_files/158/content_blobs/436
        
        # refer to http://www.visualseq.net/dokuwiki/doku.php?id=computer:websites:dmac:datafile#step_3_find_the_primary_keys_in_data_files_and_content_blobs_tables
        
        # Step 4. Update the content_blob record
        # Here, instead of uploading the data file into Seeek, so that the content_blob record is updated, as the following,
        #self.__seekapi.callFileAPI(content_blob_url, fullfilename)
        # We simply update the record in the content_blob so that the following fields are updated according to the API at
        #
        
        msg = 'okay'
        status = 1
        object_url = apiurl
        return msg, status, df_info, object_url
    
    def getAssayDFs(self, assayid, investigation, study, assay):
        ''' Get a list of data files that are associated with an assay, given
        Input:
            assay_id, the id of an assay
        
        Output:
            a list of dictionaries, such as,
                [{'id':'1', 'title':'sample data'}, {'id':'2', 'title':'sample data 2'}]
                
        Usage:
            Used when "Search for assets" button is clicked on the Publish page at "seek/publish".
        '''
        resultDic = self.__seekapi.getAssayDFsFromID(assayid)
        dicList = []
        for k,v in resultDic.items():
            dici = {}
            dici['id'] = k
            dici['title'] = v
            dici['investigation'] = investigation
            dici['study'] = study
            dici['assay'] = assay
            dici['selected'] = '1'
            dicList.append(dici)
        
        return dicList
    
    def getISAOptions(self):
        ''' Retrieve the ISA structure from Seek and organize them into the format as options shown in comboboxes.
    
        Input:
            seekdb, this class;
            user_seek, self.user_seek;
            whichServer, this Seek server
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
        '''
            projects = sdb.getProjects(True)
            projects_options = json.dumps(convertDicToOptions(projects))
            print("projects:" , projects)
    
            investigationsDic = {} 
            for pid, project in projects.iteritems():
                investigations = sdb.getInvestigations(project, True)
                investigation_options = convertDicToOptions(investigations)
                investigationsDic[pid] = investigation_options
    
            investigationsDic_options = json.dumps(investigationsDic)
    
        '''
        # Step 1. Get project options, including the first empty one
        projects = [{ 'id': "0", 'title': " " }]
        if 'projectOptions' in self.user_seek:
            projects = self.user_seek['projectOptions']
        project_options = json.dumps(projects)
        #print("projects_options:", projects_options)
        
        # 
        allinvestigations = {}
        investigation_options_dic = {}
        for pinfo in projects:
            #print('pinfo:', pinfo)
            project_title = pinfo['title']
            project_id = pinfo['id']
            
            # get investigations under a project in {'id1':'title1', 'id2':'title2', ...}
            investigations = self.getInvestigations(project_title, True)
            #investigation_options = json.dumps(convertDicToOptions(investigations))
            #print(investigation_options)
            allinvestigations.update(investigations)
            
            investigation_options = convertDicToOptions(investigations)
            investigation_options_dic[project_id] = investigation_options
            
        investigation_options_dic = json.dumps(investigation_options_dic) 
    
        study_options_dic = {}
        allstudies = {}
        for iid, investigation in allinvestigations.iteritems():
            studies = self.getStudies(investigation, True)
            study_options = convertDicToOptions(studies)
            study_options_dic[iid] = study_options
        
            # same as allstudies.update(studies)
            for sid, study in studies.iteritems():
                if sid not in allstudies:
                    allstudies[sid] = study
            

        study_options_dic = json.dumps(study_options_dic)
        #print(study_options_dic)

        assay_options_dic = {}
        for sid, study in allstudies.iteritems():
            assays = self.getAssays(study, True)
            assay_options = convertDicToOptions(assays)
            assay_options_dic[sid] = assay_options
            
        assay_options_dic = json.dumps(assay_options_dic)
        #print(assay_options_dic)
    
        #return projects_options, investigation_options, study_options_dic, assay_options_dic, server
        return project_options, investigation_options_dic, study_options_dic, assay_options_dic
        
    
    def __formatJsonDataRelationships(self, input_data):
        ''' FORMAT RELATIONSHIPS OF A JSON ([{'type':'data_files', 'id':3}])
            Modified from formatJsonDataRelationships() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
            
        Input:
            input_data, = resultjson['data'], refer to self.downloadAssets()
                {
                    u'sops': {u'data': []},
                    u'documents': {u'data': []},
                    u'people': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'models': {u'data': []},
                    u'investigation': {u'data': {u'type': u'investigations', u'id': u'2'}},
                    u'publications': {u'data': []},
                    u'assays': {u'data': [{u'type': u'assays', u'id': u'1'}, {u'type': u'assays', u'id': u'7'}, {u'type': u'assays', u'id': u'8'}]},
                    u'submitter': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'data_files': {u'data': [{u'type': u'data_files', u'id': u'18'}, {u'type': u'data_files', u'id': u'19'}, {u'type': u'data_files', u'id': u'20'}, {u'type': u'data_files', u'id': u'21'}]},
                    u'creators': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'projects': {u'data': [{u'type': u'projects', u'id': u'2'}]}
                }
                
        Output:
            a list of associations, in the following format,
                source_relationships = [
                    {'type': 'people', 'id': u'1'},
                    {'type': 'creators', 'id': u'1'},
                    {'type': 'submitter', 'id': u'1'},
                    {'type': u'projects', 'id': u'2'},
                    {'type': u'investigations', 'id': u'2'},
                    {'type': u'assays', 'id': u'2'},
                    {'type': u'assays', 'id': u'3'},
                    {'type': u'data_files', 'id': u'1'},
                    {'type': u'data_files', 'id': u'2'},
                ]    
        '''
        
        files = []
        #source_relationships = input_data['data']['relationships']
        source_relationships = input_data['relationships']
    
        for dtype in source_relationships:
            #print(dtype)    #data_files, investigation, study, projects
            source_dtype_entry = source_relationships[str(dtype)]['data']
        
            source_data_type = 'none'
            source_data_id = 'none'       
        
            # different formats if plural or singular
                #'projects': {'data': [{'id': '2', 'type': 'projects'}]}
                #'investigation': {'data': {'id': '3', 'type': 'investigations'}}
                #'study': {'data': {'id': '3', 'type': 'studies'}}
                #'data_files': {'data': [{'id': '38', 'type': 'data_files'}]}        
        
            if(dtype=='investigation' or dtype=='study'):#formated differently
                item = source_dtype_entry
                #print("item ", item)
                source_data_type = item['type']
                source_data_id = item['id']
            
                files.append({
                    'type':source_data_type, #j['data']['type'],
                    'id':source_data_id, #j['data']['id'],
                })

            else:
                for item in source_dtype_entry:
                    #print("item ", item)
                    #print(dtype, ": ", item['type'], item['id'])
                
                    source_data_id = item['id']
                    source_data_type = item['type']
                    if(item['type']=='people'): #instead of type 'people', passing submitter, creators etc.
                        source_data_type = str(dtype)
                    
                    files.append({
                        'type':source_data_type,
                        'id':source_data_id, #j['data']['id'],
                    })
                
    
            #if(source_data_type != 'none'): print("\t \t", dtype, ": ", source_data_type, "/", source_data_id)                

        print() 
        print(str(len(files)) + " relationships found: \n") #print(str(len(files)) + " \'" + grep_typep + "\' found: \n") 
        print(json_normalize(files)) 
        return files
        
        
    def __formatJsonDataRelationshipsTitle(self, input_data):#, data_types_list
        ### FORMAT RELATIONSHIPS OF A JSON ([{'type':'data_files', 'id':3, 'title':'New Image'}])
        ###  def formatJsonDataRelationshipsTitle(session, headers_json, source_base_url, input_data):#, data_types_list
        ''' FORMAT RELATIONSHIPS OF A JSON ([{'type':'data_files', 'id':3}])
            Modified from formatJsonDataRelationships() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
            
            
            This is the same as self.formatJsonDataRelationships(), except that the output also contains the title of each related object.


        Input:
            input_data, = resultjson['data'], refer to self.downloadAssets()
                {
                    u'sops': {u'data': []},
                    u'documents': {u'data': []},
                    u'people': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'models': {u'data': []},
                    u'investigation': {u'data': {u'type': u'investigations', u'id': u'2'}},
                    u'publications': {u'data': []},
                    u'assays': {u'data': [{u'type': u'assays', u'id': u'1'}, {u'type': u'assays', u'id': u'7'}, {u'type': u'assays', u'id': u'8'}]},
                    u'submitter': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'data_files': {u'data': [{u'type': u'data_files', u'id': u'18'}, {u'type': u'data_files', u'id': u'19'}, {u'type': u'data_files', u'id': u'20'}, {u'type': u'data_files', u'id': u'21'}]},
                    u'creators': {u'data': [{u'type': u'people', u'id': u'1'}]},
                    u'projects': {u'data': [{u'type': u'projects', u'id': u'2'}]}
                }
                
        Output:
            a list of associations, in the following format,
                source_relationships = [
                    {'type': 'people', 'id': u'1', 'title':'DBAdmin DBAdmin'},
                    {'type': 'creators', 'id': u'1', 'title':'...'},
                    {'type': 'submitter', 'id': u'1', 'title':'...'},
                    {'type': u'projects', 'id': u'2', 'title':'...'},
                    {'type': u'investigations', 'id': u'2', 'title':'...'},
                    {'type': u'assays', 'id': u'2', 'title':'...'},
                    {'type': u'assays', 'id': u'3', 'title':'...'},
                    {'type': u'data_files', 'id': u'1', 'title':'...'},
                    {'type': u'data_files', 'id': u'2', 'title':'...'},
                ]
                
            For example:
                 9 relationships found:

                  id                        title            type
                0  1              DBAdmin DBAdmin          people
                1  2               investigation1  investigations
                2  2  plasma extraction operation          assays
                3  3             Extraction cfDNA          assays
                4  1              DBAdmin DBAdmin       submitter
                5  1                  sample data      data_files
                6  2                sample data 2      data_files
                7  1              DBAdmin DBAdmin        creators
                8  2                Breast Cancer        projects
   
                
        '''
        files = []
        #source_relationships = input_data['data']['relationships']
        source_relationships = input_data['relationships']
    
        for dtype in source_relationships:
            #print(dtype)    #data_files, investigation, study, projects
            source_dtype_entry = source_relationships[str(dtype)]['data']
        
            source_data_type = 'none'
            source_data_id = 'none'       
        
            # different formats if plural or singular
                #'projects': {'data': [{'id': '2', 'type': 'projects'}]}
                #'investigation': {'data': {'id': '3', 'type': 'investigations'}}
                #'study': {'data': {'id': '3', 'type': 'studies'}}
                #'data_files': {'data': [{'id': '38', 'type': 'data_files'}]}        
        
            if(dtype=='investigation' or dtype=='study'):#formated differently
                item = source_dtype_entry
                #print("item ", item)
                source_data_type = item['type']
                source_data_id = item['id']
            
                #j = json_for_resource(session,headers_json,source_base_url,item['type'],item['id'])
                title = self.__getNameFromID(item['type'],item['id'])
            
                files.append({
                    'type':source_data_type, #j['data']['type'],
                    'id':source_data_id, #j['data']['id'],
                    #'title':j['data']['attributes']['title'],      
                    'title': title
                })

            else:
                for item in source_dtype_entry:
                    #print("item ", item)
                    #print(dtype, ": ", item['type'], item['id'])
                
                    source_data_id = item['id']
                    source_data_type = item['type']
                    if(item['type']=='people'): #instead of type 'people', passing submitter, creators etc.
                        source_data_type = str(dtype)
                
                    #j = json_for_resource(session,headers_json,source_base_url,item['type'],item['id'])  
                    title = self.__getNameFromID(item['type'],item['id'])
                    files.append({
                        'type':source_data_type,
                        'id':source_data_id, #j['data']['id'],
                        #'title':j['data']['attributes']['title'],
                        'title':title   
                    })
                

            #if(source_data_type != 'none'): print("\t \t", dtype, ": ", source_data_type, "/", source_data_id)                

        print() 
        print(str(len(files)) + " relationships found: \n") #print(str(len(files)) + " \'" + grep_typep + "\' found: \n") 
        print(json_normalize(files)) 
        return files  

    def __determineISAstructureFromRelationships(self, data_type, input_relationships):
        '''  ISA STRUCTURE (takes in input data type and formatted relationships ([{'type':'data_files', 'id':3}]))
            defines the hierarchy of the data types
        
        Modified from determineISAstructureFromRelationships() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
            
        Input:
            input_relationships, a list of associations, in the following format,
                source_relationships = [
                    {'type': 'people', 'id': u'1'},
                    {'type': 'creators', 'id': u'1'},
                    {'type': 'submitter', 'id': u'1'},
                    {'type': u'projects', 'id': u'2'},
                    {'type': u'investigations', 'id': u'2'},
                    {'type': u'assays', 'id': u'2'},
                    {'type': u'assays', 'id': u'3'},
                    {'type': u'data_files', 'id': u'1'},
                    {'type': u'data_files', 'id': u'2'},
                ]    
            
        Output:
            isa_structure_up, the related objects in the ISA STRUCTURE UP, such as,
                      id            type
                    0  2  investigations
                    1  2        projects
            
            isa_structure_down, the related objects in the ISA STRUCTURE DOWN, such as,
                  id        type
                0  2      assays
                1  3      assays
                2  1  data_files
                3  2  data_files
            
            isa_structure_people, the related people in the ISA STRUCTURE, such as,
                  id       type
                0  1     people
                1  1  submitter
                2  1   creators
                
            If 'title' is included in the input, the output becomes,
                ISA STRUCTURE UP:
              id           title            type
            0  2  investigation1  investigations
            1  2   Breast Cancer        projects
            ()
                ISA STRUCTURE DOWN:
              id                        title        type
            0  2  plasma extraction operation      assays
            1  3             Extraction cfDNA      assays
            2  1                  sample data  data_files
            3  2                sample data 2  data_files
            ()
                ISA STRUCTURE PEOPLE:
              id            title       type
            0  1  DBAdmin DBAdmin     people
            1  1  DBAdmin DBAdmin  submitter
            2  1  DBAdmin DBAdmin   creators

        '''
        #print(input_relationships)
    
        #ISA structure
        #print();print("ISA STRUCTURE: ")
        structure = ['projects', 'investigations', 'studies', 'assays', 'data_files'] # investigation, study
    
        structure_up = []
        structure_down = []
        structure_people = ['creators', 'submitter', 'people'] # creator?
    
        isa_structure_up = []
        isa_structure_down = []  
        isa_structure_people = []    
    
        if(data_type == 'projects'):
            structure_up = [] 
            structure_down = ['investigations', 'studies', 'assays', 'data_files'] 
        if(data_type == 'investigations'):
            structure_up = ['projects'] 
            structure_down = ['studies', 'assays', 'data_files']         
        if(data_type == 'studies'):
            structure_up = ['projects', 'investigations'] # investigation
            structure_down = ['assays', 'data_files'] 
        if(data_type == 'assays'):
            structure_up = ['projects', 'investigations', 'studies'] # investigation, study
            structure_down = ['data_files'] 
        if(data_type == 'data_files'):
            structure_up = ['projects', 'investigations', 'studies', 'assays']
            structure_down = []   
    
        for item in input_relationships:
            for y in range(0, len(structure_up)):
                if(item['type']==structure_up[y]):
                    isa_structure_up.append(item)  
            for y in range(0, len(structure_down)):
                if(item['type']==structure_down[y]):
                    isa_structure_down.append(item) 
            for y in range(0, len(structure_people)):
                #if(source_data_type==structure_people[y]):
                #if(dtype==structure_people[y]):
                if(item['type']==structure_people[y]):
                    isa_structure_people.append(item)              
             
        #print()
        #print(json_normalize(isa_structure))
        if(len(isa_structure_up)>0):
            print("ISA STRUCTURE UP:");print(json_normalize(isa_structure_up));print()
        if(len(isa_structure_down)>0):        
            print("ISA STRUCTURE DOWN:");print(json_normalize(isa_structure_down));print()
        if(len(isa_structure_people)>0): 
            print("ISA STRUCTURE PEOPLE:");print(json_normalize(isa_structure_people));print()
        
        #return isa_structure
        return isa_structure_up, isa_structure_down, isa_structure_people    
      
    ### READ / PRINT JSON
    def readJsonData(self, object_id, object_type):
        #def readJsonData(session, headers_json, url, data_id, data_type):
        ''' Get the object info, given
        Input:
            session, rthe current session.
            headers_json, a header of a json 
            url, the server url, such as 'http://localhost:3000'
            data_id, the primary key of the object, such as 3
            data_type, the type of the object, such as 'studies'
        
        Output:
            resultJson = {
                u'data': datadic, 
                u'jsonapi': {u'version': u'1.0'}
            }
            where datadic = resultJson['data'] = resultJson1, returned from,
        
                seekdb = SeekDB(None, None, None)
                user_seek = seekdb.getSeekLogin(request)
                resultJson1 = seekdb.getInfoObject("/studies/", 1)
                print("resultJson1:", resultJson1)
    
        '''
        #result_json = json_for_resource(session, headers_json, url, data_type, data_id)
        #filetitle = result_json['data']['attributes']['title']
        #print("Name of \'" + data_type + "\': " + filetitle + "\n")
        #print(result_json)
        #return result_json
        
        #source_json = readJsonData(session, headers_json, url, data_id, data_type)
        #print(source_json['data']['relationships'])
        object_url = "/" + object_type + "/"
        source_json= self.getInfoObject(object_url, object_id)
        return source_json
      
      
    def __getDISA(self, object_id, object_type): #uses: readJsonData(), formatJsonDataRelationshipsTitle(), determineISAstructureFromRelationships()
        ###def getDISA(session, headers_json, url, data_id, data_type): #uses: readJsonData(), formatJsonDataRelationshipsTitle(), determineISAstructureFromRelationships()
        ### GET DISA (DOWNWARDS ISA STRUCTURE)
        ''' Modified from getDISA() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
        
        '''
        ### READ JSON FILE
        print("FILE: ")
        #source_json = readJsonData(session, headers_json, url, data_id, data_type)
        #print(source_json['data']['relationships'])
        #object_url = "/" + object_type + "/"
        #source_json = self.getInfoObject(object_url, object_id)
        
        source_json = self.readJsonData(object_id, object_type)
        #print("source_json:", source_json)
    
        ### FORMAT RELATIONSHIPS
        print("RELATIONSHIPS: ")
        #source_relationships = formatJsonDataRelationshipsTitle(session, headers_json, url, source_json)
        #source_relationships = formatJsonDataRelationships(source_json)
        source_relationships =  self.__formatJsonDataRelationshipsTitle(source_json)
    
        ### DETERMINE DISA
        #print();
        print("ISA STRUCTURE: ")
        #isas = determineISAstructureFromRelationships(data_type, source_relationships)
        isas = self.__determineISAstructureFromRelationships(object_type, source_relationships)
        return isas[1]#isa_structure_down (DISA)

    def __getFullDISA(self, source_json_id, source_data_type):#uses: getDISA()
        ###def getFullDISA(session1, headers1, source_base_url, source_json_id, source_data_type):#uses: getDISA()
        ### GET DISA OF THE ORIGINAL JSON ENTRY AND OF EACH OF ITS RESULT ENTRIES

        # 1st element is the intial entry
        #   [intial entry e.g. study, [list of its downwards isa structure]]
        #   [1st element of downwards ISA, [list of its downwards isa structure]]
        #   ...
        #   [last element of downwards ISA, [list of its downwards isa structure]]
        ''' Modified from getFullDISA() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
            
        Input:
            object_id, the primary key of the object, such as 3
            object_type, the type of the object, such as 'studies', 'assays', etc
    
        Output:
            isa_struct, in the following format of a list, such as,
            [
                [
                    {'type': 'studies', 'id': 2}, 
                    [
                        {'type': u'assays', 'id': u'2', 'title': u'plasma extraction operation'}, 
                        {'type': u'assays', 'id': u'3', 'title': u'Extraction cfDNA'}, 
                        {'type': u'data_files', 'id': u'1', 'title': u'sample data'}, 
                        {'type': u'data_files', 'id': u'2', 'title': u'sample data 2'}
                    ]
                ], 
                [
                    {'type': u'assays', 'id': u'2', 'title': u'plasma extraction operation'}, 
                    []
                ], 
                [
                    {'type': u'assays', 'id': u'3', 'title': u'Extraction cfDNA'}, 
                    [
                        {'type': u'data_files', 'id': u'1', 'title': u'sample data'}, 
                        {'type': u'data_files', 'id': u'2', 'title': u'sample data 2'}
                    ]
                ], 
                [
                    {'type': u'data_files', 'id': u'1', 'title': u'sample data'}, 
                    []
                ], 
                [
                    {'type': u'data_files', 'id': u'2', 'title': u'sample data 2'}, 
                    []
                ]
            ]
        
        '''
        ### ISA STRUCTURE OF THE INITAL FILE
        #out = getDISA(session1, headers1, source_base_url, source_json_id, source_data_type)
        out = self.__getDISA(source_json_id, source_data_type)
    
        ### GET THE ISA STRUCTURE OF EACH ENTRY FROM 'out' (ISA STRUCTURE OF THE INITAL FILE)
        isa_struct = []
        isa_struct.append([{'type': source_data_type, 'id': source_json_id}, out])
        for entry_num in range(0, len(out)):
            #out_temp = getDISA(session1, headers1, source_base_url, out[entry_num]['id'], out[entry_num]['type'])
            out_temp = self.__getDISA(out[entry_num]['id'], out[entry_num]['type'])
            #also checking the DISA for data_files, just to not omit anything (not likely that they have any)
            if(len(out_temp)>0):#if there is a DISA
                print("OUTPUT:\n", json_normalize(out_temp),"\n")
                isa_struct.append([out[entry_num], out_temp])
            else:
                out_temp = [];
                print("OUTPUT: empty \n")  
                isa_struct.append([out[entry_num], out_temp])
            
        print('isa_struct:', isa_struct)
        return isa_struct
    
        
    def downloadAssets(self, object_id, object_type):
        ''' Download assets and pack them into proper package for publishing to remote Seek.
            This function is modified according to download() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
            
        Input:
            object_id, the primary key of the object, such as 3
            object_type, the type of the object, such as 'studies', 'assays', etc
        
        Output:
            resultJson = {
                u'data': datadic, 
                u'jsonapi': {u'version': u'1.0'}
            }
            where datadic = resultJson['data'] = resultJson1, returned from,
        
                seekdb = SeekDB(None, None, None)
                user_seek = seekdb.getSeekLogin(request)
                resultJson1 = seekdb.getInfoObject("/studies/", 1)
                print("resultJson1:", resultJson1)
        
        '''
        ### READ JSON FILE
        print("FILE: ")
        #source_json = readJsonData(session, headers_json, url, data_id, data_type)
        #print(source_json['data']['relationships'])
        source_json = self.readJsonData(object_id, object_type)
        #print("source_json:", source_json)

        isa_structure = self.__getFullDISA(object_id, object_type)
        return source_json, isa_structure
        
        out = self.__getDISA(object_id, object_type)
        return out
    
    def __createStudyDic(self, userid, projectid, investigationid, study_title, study_description):
        """Creates a new study in dictionary format.

        Arguments:
            username: SEEK Login name
            password: SEEK password
            server: SEEK server URL
            userid: Creator ID in SEEK
            projectid: Selected SEEK project ID.
            investigationid: Selected SEEK investigation ID.
            title: Title entered when creating a new assay.
            description: Description entered when creating a new assay.
            studyname: The name of the new study.
        """
        new_study_json = {}
        new_study_json['data'] = {}
        new_study_json['data']['type'] = 'studies'

        new_study_json['data']['attributes'] = {}
        new_study_json['data']['attributes']['title'] = study_title
        new_study_json['data']['attributes']['description'] = study_description


        #new_assay_json['data']['attributes']['policy'] = in_assay_json['data']['attributes']['policy']
        new_study_json['data']['attributes']['policy'] = {'access':'no_access'}
        new_study_json['data']['attributes']['policy']['permissions'] = [{'resource':{'id':projectid,'type':'projects'},'access':'download'}];

        #new_assay_json['data']['attributes']['assay_class'] = in_assay_json['data']['attributes']['assay_class']
        #new_assay_json['data']['attributes']['assay_type'] = in_assay_json['data']['attributes']['assay_type']
        #new_assay_json['data']['attributes']['technology_type'] = in_assay_json['data']['attributes']['technology_type']

        new_study_json['data']['relationships'] = {}
        new_study_json['data']['relationships']['creators'] = {}
        new_study_json['data']['relationships']['creators']['data'] = [{'id' : userid, 'type' : 'people'}]
        #new_study_json['data']['relationships']['study'] = {}
        #new_study_json['data']['relationships']['study']['data'] = {'id' : target_study_id, 'type' : 'studies'}
        new_study_json['data']['relationships']['investigation'] = {}
        new_study_json['data']['relationships']['investigation']['data'] = {'id' : investigationid, 'type' : 'investigations'}
        new_study_json['data']['relationships']['projects'] = {}
        new_study_json['data']['relationships']['projects']['data'] = {'id' : projectid, 'type' : 'projects'}
        return new_study_json
    
    ### REGISTER STUDY
    def registerStudy(self, in_study_json, target_project_id, target_investigation_id, target_creator_id):
        ''' Modified from
        def registerStudy(session, in_study_json, target_project_id, target_investigation_id, target_creator_id):
        
        
        '''
        study_title = in_study_json['attributes']['title']
        study_description = in_study_json['attributes']['description']
        new_study_json, study_id = self.createStudy(target_creator_id, target_project_id, target_investigation_id,
            study_title, study_description, "")
        return new_study_json, study_id
        
    def createAssayDic(self, userid, projectid, investigationid, studyid,
            title, description, assay_type, technology_type, assay_class):
        """Creates a new assay in dictionary format.

        Arguments:
            username {str} -- SEEK Login name
            password {str} -- SEEK password
            server {str} -- SEEK server URL
            userid {int} -- Creator ID in SEEK
            projectid {int} -- Selected SEEK project ID.
            studyid {int} -- Selected SEEK study ID.
            title {str} -- Title entered when creating a new assay.
            description {str} -- Description entered when creating a new assay.
            assay_type {str} -- The selected assay type when creating a new assay.
            technology_type {str} -- The selected technology type 
            when creating a new assay.
            assayname {str} -- The name of the new assay.
        
        Example
        """
        new_assay_json = {}
        new_assay_json['data'] = {}
        new_assay_json['data']['type'] = 'assays'

        new_assay_json['data']['attributes'] = {}
        new_assay_json['data']['attributes']['title'] = title
        new_assay_json['data']['attributes']['description'] = description

        #new_assay_json['data']['attributes']['policy'] = in_assay_json['data']['attributes']['policy']
        new_assay_json['data']['attributes']['policy'] = {'access':'no_access'}
        new_assay_json['data']['attributes']['policy']['permissions'] = [{'resource':{'id':projectid,'type':'projects'},'access':'download'}];

        new_assay_json['data']['attributes']['assay_class'] = assay_class
        new_assay_json['data']['attributes']['assay_type'] = assay_type
        new_assay_json['data']['attributes']['technology_type'] = technology_type

        new_assay_json['data']['relationships'] = {}
        new_assay_json['data']['relationships']['creators'] = {}
        new_assay_json['data']['relationships']['creators']['data'] = [{'id' : userid, 'type' : 'people'}]
        new_assay_json['data']['relationships']['study'] = {}
        new_assay_json['data']['relationships']['study']['data'] = {'id' : studyid, 'type' : 'studies'}
        new_assay_json['data']['relationships']['investigation'] = {}
        new_assay_json['data']['relationships']['investigation']['data'] = {'id' : investigationid, 'type' : 'investigations'}
        new_assay_json['data']['relationships']['projects'] = {}
        new_assay_json['data']['relationships']['projects']['data'] = {'id' : projectid, 'type' : 'projects'}
        return new_assay_json


    def registerAssay(self, in_assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id):
        '''
        ### REGISTER ASSAY
        Modified from def registerAssay(session, in_assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id):
        '''
        title = in_assay_json['attributes']['title']
        description = in_assay_json['attributes']['description']
        assay_type = in_assay_json['attributes']['assay_type']
        technology_type = in_assay_json['attributes']['technology_type']
        assay_class = in_assay_json['attributes']['assay_class']
        new_assay_json = self.createAssayDic(target_creator_id, target_project_id, target_investigation_id, target_study_id,
            title, description, assay_type, technology_type, assay_class)
        
        from seeksession import SeekSession
        session = SeekSession(self.user_seek['server'], self.user_seek['username'], self.user_seek['password'])
        id = session.postSeekURL("assays", new_assay_json)
        print('assay_id 1:', id)
        return new_assay_json, id


    def registerAndCopyStudyAndBelow(self, source_seekdb, source_json, isa_structure, #source_json, 
                target_project_id, target_investigation_id, target_creator_id):#isa_structure
        '''
        ### REGISTER THE ISA STRUCTURE DOWN (DISA) IN THE TARGET DATABASE AND COPY DATA
        ### uses: getFullDISA() -> getDISA() -> readJsonData(), formatJsonDataRelationshipsTitle(), determineISAstructureFromRelationships()
        ### uses: readJsonData(), registerStudy(), 
        ### uses: readJsonData(), registerAssay(),
        ### uses: readBlobData(), registerBlobData(), uploadBlobData()
        modified from  def registerAndCopyStudyAndBelow(session1, session2, headers1, headers2, headers3, 
                                 source_base_url, source_json_id, source_data_type, #source_json, 
                                 target_base_url, target_project_id, target_investigation_id, target_creator_id):#isa_structure
        Input:
            source_seekdb, seekDB class for the source Seek server
            source_json, source json directory for upload
            isa_structure, source ISA structure for upload
            
            target_project_id,
            target_investigation_id,
            target_creator_id
        
        Output:
        
        
        
        '''
        ### GET DOWNWARD ISA STRUCTURE
        #isa_structure = getFullDISA(session1, headers1, source_base_url, source_json_id, source_data_type)    

        ### READ SOURCE JSON
        #source_json = readJsonData(session1, headers1, source_base_url, source_json_id, source_data_type)
    
        ### PEOPLE need to be improved later
        #target_creator_id = 1      # Dorotea           (same id as source seek, since they are originaly clones)   
    
        ### REGISTER TARGET JSON (STUDY) 
        #out_json = registerStudy(session2, source_json, target_project_id, target_investigation_id, target_creator_id)#out_json[0] - json   ;  #out_json[1] - id
        out_json = self.registerStudy(source_json, target_project_id, target_investigation_id, target_creator_id)#out_json[0] - json   ;  #out_json[1] - id
        target_study_id = out_json[1]
    
        ### FORMAT OF isa_structure
            #print("study:", isa_structure[0][0])    # study entry
            #print("DISA study 1st entry: ",isa_structure[0][1][0]) # 1st entry of the list
            ##print("DISA study 1st entry: ",isa_structure[0][1][0]['type']) 
            ##print("DISA study 1st entry: ",isa_structure[0][1][0]['id']) 
            ##print("DISA study 1st entry: ",isa_structure[0][1][0]['title'])
            #print("DISA study 2nd entry: ",isa_structure[0][1][1]) # 1st entry of the list
            #print("DISA study 3rd entry: ",isa_structure[0][1][2]) # 1st entry of the list
            #print("DISA study 4th entry: ",isa_structure[0][1][3]) # 1st entry of the list
            #print()
            ##print("DISA study 1st entry + its DISA ", isa_structure[1])
            #print("DISA study 1st entry: ", isa_structure[1][0])# assay entry
            ##print("DISA of DISA study list: ", isa_structure[1][1])# its downwards ISA list
            #print("DISA of DISA study 1st entry: ", isa_structure[1][1][0])# 1st entry of the list
            #print()
            #print("DISA study 2nd entry: ", isa_structure[2][0])# assout_json[1]ay entry
            #print("DISA of DISA study 2nd entry: ", isa_structure[2][1][0])# 1st entry of the list
            #print()
            #print("DISA study 3rd entry: ", isa_structure[3][0])# image entry
            #print("DISA of DISA study 3rd entry: ", isa_structure[3][1])# 1st entry of the list (empty, so no 1st element)
            #print()
            #print("DISA study 4th entry: ", isa_structure[4][0])# image entry
            #print("DISA of DISA study 4th entry: ", isa_structure[4][1])# 1st entry of the list (empty, so no 1st element)    
            ### OUTPUT
            #isa_structure[0][0]    study: {'type': 'studies', 'id': 3}
            #isa_structure[0][1][0] DISA study 1st entry:  {'type': 'assays', 'id': '3', 'title': 'assay linked to data file'}
            #isa_structure[0][1][1] DISA study 2nd entry:  {'type': 'assays', 'id': '4', 'title': 'Assay to be copied'}
            #isa_structure[0][1][2] DISA study 3rd entry:  {'type': 'data_files', 'id': '4', 'title': 'New Pink Image'}
            #isa_structure[0][1][3] DISA study 4th entry:  {'type': 'data_files', 'id': '38', 'title': 'Network Image'}
            #isa_structure[1][0]    DISA study 1st entry:  {'type': 'assays', 'id': '3', 'title': 'assay linked to data file'}
            #isa_structure[1][1][0] DISA of DISA study 1st entry:  {'type': 'data_files', 'id': '4', 'title': 'New Pink Image'}
            #isa_structure[2][0]    DISA study 2nd entry:  {'type': 'assays', 'id': '4', 'title': 'Assay to be copied'}
            #isa_structure[2][1][0] DISA of DISA study 2nd entry:  {'type': 'data_files', 'id': '38', 'title': 'Network Image'}
            #isa_structure[3][0]    DISA study 3rd entry:  {'type': 'data_files', 'id': '4', 'title': 'New Pink Image'}
            #isa_structure[3][1]    DISA of DISA study 3rd entry:  []
            #isa_structure[4][0]    DISA study 4th entry:  {'type': 'data_files', 'id': '38', 'title': 'Network Image'}
            #isa_structure[4][1]    DISA of DISA study 4th entry:  []    

        ### GO THROUGH DISA - READ, REGISTER, UPLOAD   (isa_structure[0][1][x] (fro json)
        for x in range(0, len(isa_structure)):# go through DISA  m 0) or isa_structure[x][0] (from 1))
            ### ASSAYS -> DATA_FILES
            if(len(isa_structure)>1):# if there is DISA (1st one is the initial source
                if(isa_structure[x][0]['type']=='assays'):# if it is an assay
                
                    ### READ JSON
                    #assay_json = readJsonData(session1, headers1, source_base_url, isa_structure[x][0]['id'], isa_structure[x][0]['type'])
                    assay_json = source_seekdb.readJsonData(isa_structure[x][0]['id'], isa_structure[x][0]['type'])
                
                    ### REGISTER ASSAY (in second seek and get the id)
                    #target_assay_id = registerAssay(session2, assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id)
                    target_assay_id = self.registerAssay(assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id)
            
                    ### CHECK ASSAY DISA (see which data file goes to which assay from isa_structure)
                    if(len(isa_structure[x][1])>0):#if there is a downwards structure of the assay
                        for y in range(0, len(isa_structure[x][1])):#go through each element
                            #isa_structure[x][1][y]['type']
                            #isa_structure[x][1][y]['id']
                            if(isa_structure[x][1][y]['type']=='data_files'):#if it is a data file
                            
                                ### READ DATA FILE BLOB FROM SOURCE
                                dataRead = readBlobData(session1, headers1, headers2, source_base_url, isa_structure[x][1][y]['id'], 'data_files')
                            
                                dataBinary = dataRead[7]
                                #target_data_file_id - will be obtained after registering a data_file
                                #target_data_file_data_type = 'data_files'
                                target_filetitle = dataRead[1]
                                target_filelicense = dataRead[4]
                                # data_file blob
                                target_filename = dataRead[2]
                                target_filetype = dataRead[3]
                                target_blob = {'original_filename' : target_filename, 'content_type' : target_filetype}           
                   
                                ### REGISTER DATA FILE AND BLOB TO TARGET SEEK
                                target_data_file  = registerBlobData(session2, target_base_url, 'data_files', target_filetitle, target_filelicense, target_blob, 
                                                                 target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id)    
                                target_data_file_id = target_data_file[0]
                                target_data_file_link = target_data_file[1]
                   
                                ### UPLOAD BLOB INTO DATA FILE IN TARGET DATABASE
                                uploadBlobData(session2, headers1, headers3, target_base_url, 'data_files', target_data_file_id, target_data_file_link, dataBinary)
                        
                                ### COMBINES REGISTER DATA FILE AND UPLOAD BLOB
                                #TransferData(session2, headers1, headers3, target_base_url, 'data_files', 
                                #             target_filetitle, target_filelicense, target_blob, dataBinary, 
                                #             target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id)

    print("DONE")    
        
        
    def uploadAssets(self, source_seekdb, source_json, isa_structure):
        ''' Modified from upload() in snapshot.py, which is the sample script for
            publishing to another seek, developed by Seek. Refer to: "Publish assets to FairdomHUB".
        Publish assets to the Seek system. This is a test.
        
        Input:
            source_seekdb, source SeekDB class
            source_json, source json directory for upload
            isa_structure, source ISA structure for upload
        
        Output:
        
        
        
        Usage:
            remoteServer = "https://kibcc2.mit.edu"
            seekdb_remote = SeekDB(remoteServer , seekdb.user_seek['username'], seekdb.user_seek['password'])
            study_id = 1
            result_remote = seekdb_remote.downloadAssets(int(study_id), "studies")
            print("result_remote:", result_remote)
        
        '''
        
        
        #print("okay")
        #session2 = authenticate(headers1)
        ### TARGET DATA PARAMETERS (ENTRY POINT FOR COPYING)

        ### DATABASE
        #target_base_url = 'http://localhost:4000'
        #target_base_url = 'http://doroteadesktop:4000'

        ### TARGET PROJECT
        target_project_id = 2 # Project Alpha
        target_project_type = 'projects'

        ### TARGET INVESTIGATION
        target_investigation_id = 4 # investigation two
        target_investigation_data_type = 'investigatons'

        ### PEOPLE (THIS IS NOT RESOLVED NICELY YET, SO FOR NOW JUST SETTING NOT COPYING)
        target_creator_id = 1      # Dorotea           (same id as source seek, since they are originaly clones)
        #target_creator_id2 = 3    # Teodora           (same id as source seek, since they are originaly clones)
        
        #registerAndCopyStudyAndBelow(session1, session2, headers1, headers2, headers3, 
        #    source_base_url, source_json_id, source_data_type, #source_json, 
        #    target_base_url, target_project_id, target_investigation_id, target_creator_id)#, isa_structure
        
        self.registerAndCopyStudyAndBelow(source_seekdb, source_json, isa_structure, 
                target_project_id, target_investigation_id, target_creator_id)


        #deleteISA(session2, headers1, target_base_url, 11, 'studies')
        
        
        
    def reviseOwnership(self, username):
        ''' Revise the ownership of data files from the admin user to the login user on the ftp server.
        Input:
            username: the login username from the ftp server.
            
            
        
        '''
        #print('login user: ', self.user_seek)
        person_id = self.__getSeekPersonID(username)
        #print('person_id:', person_id)
        
        userInfo, status, msg = self.getUserInfo(person_id)
        print('File owner: ', userInfo)
        
        self.user_seek.update(userInfo)
        #print('Mixed user: ', self.user_seek)
        
        
        
        