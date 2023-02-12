#!/usr/bin/env python
import subprocess
import json
from subprocess import call

class NextCloudAPI(object):
    def __init__(self, server, username, password):
        self.__server = server
        self.__username = username
        self.__password = password
            
    def runQuery(self, url):
        prefix = "curl -s -X PROPFIND -u" + self.__username + ":" + self.__password + " '" + self.__server
        suffix = "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
        apicmd = prefix + url + suffix
        
        resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
        return resultset
            
    def get_investigation_folders(self):
        oc_folders = ""
        pass
    
        url = "/"
        inv_folders = self.runQuery(url)
        return inv_folders, oc_folders
        
    def get_study_folders(self, investigation):
        pass
        url = "/" + investigation
        oc_folders = self.runQuery(url)
        
        url = "/"
        inv_folders = self.runQuery(url)
        return oc_folders, inv_folders
    
    def get_investigations_folders(self, investigation):
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
            apiqueryi = "/investigations.xml | grep -e \'" + it + "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
            investigation_id = self.__seekapi.runSilentQuery(apiqueryi)
            
            investigations[it] = investigation_id.strip("\n")
        return investigations
        
        
    def investigation(self, investigationIn):
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
    
