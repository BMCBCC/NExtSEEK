#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for running NextCloud API queries.
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
import subprocess
import json
from subprocess import call

class NextCloudAPI(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        nextapi = NextCloudAPI()
    '''
    def __init__(self, server, username, password):
        ''' We do need the username and password for accessing the Seek API. 
        '''
        self.__server = server
        self.__username = username
        self.__password = password
            
    def runQuery(self, url):
        """ Run typical query using the API.
        
        Arguments:
            url: The url for running the query, such as
                "/"
                "/" + investigation

        Returns:
            A list of investigation folder and a list of study folders.
            
        Example:
            resultset = subprocess.Popen([
                "curl -s -X PROPFIND -u" + self.__username + ":" + self.__password +
                " '" + self.__server + "/' | grep -oPm250 '(?<=<d:href>)[^<]+'"
            ], stdout=subprocess.PIPE, shell=True
            ).communicate()[0].decode().split("\n")
        
        """
        prefix = "curl -s -X PROPFIND -u" + self.__username + ":" + self.__password + " '" + self.__server
        
        suffix = "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
        apicmd = prefix + url + suffix
        
        resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
        return resultset
            
    def get_investigation_folders(self):
        """Gets the user's investigation folders from the storage URL,
        This will be shown on the homepage for storing existing Galaxy 
        histories.

        Arguments:
            storage: The URL of the ISA structure storage.
            storagetype: The storage type (SEEK or Owncloud)
            username: The username of the ISA structure storage.
            password: The password of the ISA structure storage.

        Returns:
            A list of investigation folder and a list of study folders.
        """
        oc_folders = ""
        pass
    
        url = "/"
        inv_folders = self.runQuery(url)
        return inv_folders, oc_folders
        
    def get_study_folders(self, investigation):
        """Gets the study folders based on the selected investigation from the
        homepage. This is used to store existing Galaxt histories.

        Arguments:
            storage: The URL of the ISA structure storage.
            username: The username of the ISA structure storage.
            password: The password of the ISA structure storage.
            investigation: SEEK investigation ID.

        Returns:
            A list of investigationa folders and a list of study folders.
        """
        pass
        url = "/" + investigation
        oc_folders = self.runQuery(url)
        
        url = "/"
        inv_folders = self.runQuery(url)
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
            A list of investigationa folders and a list of study folders.
        """
        folders = []
        investigations = []
        if investigation is not None and investigation != "":
            oc_folders, inv_folders = self.get_study_folders(investigation)
        else:
            inv_folders, oc_folders = self.get_investigation_folders()
            
        for inv in inv_folders:
            investigation_name = inv.replace(
                '/owncloud/remote.php/webdav/', '').replace('/', '')
            if "." not in investigation_name:
                new = investigation_name
                investigations.append(new)

        for oc in oc_folders:
            study = oc.replace('/owncloud/remote.php/webdav/', '')
            study = study.replace('/', '').replace(investigation, '')
            if "." not in study:
                new = study
                folders.append(new)
 
        folders = list(filter(None, folders))
        investigations = list(filter(None, investigations))
        return investigations,folders
    
    def getInvestigationsFolders(self, project_title):
        """Get all investigations through Seek API that the logged in user has access to, regardless to which project they belong. 
            Modified from get_seek_investigations().

        Arguments:
            username: The SEEK username, from request.session.get('username').
            password: The SEEK password, from request.session.get('password').
            storage: The SEEK URL, from request.session.get('storage').
            project_title: a valid project title, or (None, "") for any project.

        Returns:
            A dictionary with SEEK investigations and URLs.
            
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
        
        #investigation_titles = subprocess.Popen([
        #    "curl -s -u \'" + username + "\':" + password + " " + storage +
        #    "/investigations.xml | grep -e \'investigation xlink\' | "
        #    "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"],
        #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        if project_title is None or project_title=="":
            apiquery = "/investigations.xml | grep -e \'investigation xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        else:
            projectid = self.__seekapi.getIDfromTitle("/projects/", project_title)
            apiquery = "/projects/" + projectid + ".xml | grep -e \'investigation xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        
        investigation_titles = self.__seekapi.runSilentQuery(apiquery)
        
        investigation_titles = investigation_titles.split("\n")
        investigation_titles = list(filter(None, investigation_titles))
        investigations = {}
        for it in investigation_titles:
            #investigation_id = subprocess.Popen([
            #    "curl -s -u \'" + username + "\':" + password + " " + storage +
            #    "/investigations.xml | grep -e \'" + it +
            #    "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"],
            #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            apiqueryi = "/investigations.xml | grep -e \'" + it + "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
            investigation_id = self.__seekapi.runSilentQuery(apiqueryi)
            
            investigations[it] = investigation_id.strip("\n")
        return investigations
        
        
    def investigation(self, investigationIn):
        """Get studies based on the investigation that was selected 
        in the indexing menu.

        Arguments:
            investigationIn: = request.POST.get('folder') or request.POST.get('selected_folder')
        """
        oc_folders = self.runQuery("/")
        oc_list = list(filter(None, oc_folders))
        oc_studies = ""
        folders = []
        studies = []
        if oc_list:
            for oc in oc_folders:
                if "/owncloud/" in self.__server:
                    new = oc.replace(
                        '/owncloud/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
                else:
                    new = oc.replace(
                        '/remote.php/webdav/', '').replace('/', '')
                    if "." not in new:
                        folders.append(new)
            folders = list(filter(None, folders))
            
            if(investigationIn != "" and investigationIn is not None):
                url = "/" + investigationIn
                oc_studies = self.runQuery(url)
                
            if oc_studies != "":
                for s in oc_studies:
                    if(investigationIn != "" and investigationIn is not None):
                        oc_studies = list(filter(None, oc_studies))
                        if "/owncloud/" in self.__server:
                            new = s.replace(
                                '/owncloud/remote.php/webdav/' +
                                investigationIn + "/", '').replace(
                                    '/', '')
                        else:
                            new = s.replace(
                                '/remote.php/webdav/' +
                                investigationIn + "/", '').replace(
                                    '/', '')
                        studies.append(new)
                studies = list(filter(None, studies))
                return oc_list, oc_studies, folders, studies
            else:
                return oc_list, oc_studies, folders, studies

        return oc_list, oc_studies, folders, studies
    
