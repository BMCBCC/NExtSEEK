#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for running Seek API queries.
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

import shlex
from subprocess import Popen, PIPE

class SeekAPI(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        seekapi = SeekAPI()
    '''
    #def __init__(self, server=SEEK_SERVER, username=SEEK_USER, password=SEEK_PWD):
    def __init__(self, server, username, password):
        ''' We do need the username and password for accessing the Seek API. 
        '''
        self.__server = server
        self.__username = username
        self.__password = password
            
    def __curlPrefix(self):
        ''' Get the prefix of the curl command line.
        
        Notes:
        (1) the '-k' option disables the verification of the SSL certificate on the SEEK server.
            For more detail, refer to: https://curl.haxx.se/docs/sslcerts.html
        (2) the '-u' option is surrounded with ''. Otherwise, it will throw an error that "!12: event not found",
            if the password contains "!12". 
        '''
        if self.__username is None:
            curl_prefix = "curl -k "
        else:    
            curl_prefix = "curl -u '" + self.__username + ":" + self.__password + "' -k "
        return curl_prefix
            
    def apiPost(self):
        ''' The POST command for accessing the Seek API, given
        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password

        Returns:
            The command for accessing the Seek API without options.
        '''
        apicmd = self.__curlPrefix() + " -X POST \"" + self.__server + "\""
        return apicmd
    
    def __apiGet(self):
        ''' The GET command for accessing the Seek API, given
        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password

        Returns:
            The command for accessing the Seek API without options.
            
        Example:
            curl -X GET "10.159.0.74:3000//assays" -H "accept: application/json"
            curl -X GET 10.159.0.74:3000/people -H "accept: application/json"
            
            where it works with or without the quotes "".
        '''
        apicmd = self.__curlPrefix() + " -X GET " + self.__server
        return apicmd        
            
    def __apiSilent(self):
        ''' The GET command in Silent mode for accessing the Seek API, given
        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password

        Returns:
            The command for accessing the Seek API without options.
        '''
        apicmd = self.__curlPrefix() + " -s " + self.__server
        return apicmd         
            
    def __queryRaw(self, apiquery):
        ''' Run api query and return results in its raw format.
        Arguments:
            apiquery: a query based on Seek API.

        Returns:
            results: results in raw format
            
        Example:
            apiquery:
                curl -X GET 10.159.0.74:3000/people -H "accept: application/json"
            resultset:
                {"data":[{"id":"1","type":"people","attributes":{"title":"DBAdmin DBAdmin"},"links":{"self":"/people/1"}}],"jsonapi":{"version":"1.0"},"meta":{"base_url":"http://dmac.mit.edu:3000","api_version":"0.2"}}
        '''
        #print(apiquery)
        #resultset = subprocess.Popen([apiquery],
        #    stdout=subprocess.PIPE,
        #    shell=True).communicate()[0].decode()
        
        # use 'utf-8' instaed of the default decode
        resultset = subprocess.Popen([apiquery],
            stdout=subprocess.PIPE,
            shell=True).communicate()[0].decode("utf-8")
        
        # refer to: https://stackoverflow.com/questions/29546311/popen-communicate-throws-unicodedecodeerror
        # support utf-8 instead off text
        # good for python3.6 
        #resultset = subprocess.Popen([apiquery],
        #    stdout=subprocess.PIPE,
        #    shell=True, encoding="utf-8", universal_newlines=True).communicate()[0].decode()
        
        #print(resultset)
        return resultset        
            
            
    def __query(self, apiquery):
        ''' Run api query and return results in list.
        Arguments:
            apiquery: a query based on Seek API.

        Returns:
            resultDic: results in a dictionary.
            
        Example:
            apiquery:
                curl -X GET 10.159.0.74:3000/people -H "accept: application/json"
            resultset:
                {"data":[{"id":"1","type":"people","attributes":{"title":"DBAdmin DBAdmin"},"links":{"self":"/people/1"}}],"jsonapi":{"version":"1.0"},"meta":{"base_url":"http://dmac.mit.edu:3000","api_version":"0.2"}}
            resultDic:
                {'data': [{'id': '1', 'type': 'people', 'attributes': {'title': 'DBAdmin DBAdmin'}, 'links': {'self': '/people/1'}}], 'jsonapi': {'version': '1.0'}, 'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}}
        '''
        print(apiquery)
        resultset = self.__queryRaw(apiquery)
        #print('resultset:', resultset)
        if 'Access denied' in resultset:
            resultDic = None
        else:
            resultDic = json.loads(resultset)
        
        #print(resultset)
        #print(resultDic)
        return resultDic
    
    def callAPI(self, apiquery):
        ''' Call Seek API for uploading operation, such as creatingg a new assay.
        Arguments:
            apiquery: an uploading query based on Seek API.

        Returns:
            result with results.
            
        Example:
        '''
        #print(apiquery)
        #return self.callCmdline(apiquery)
        
        try:
            call([apiquery], shell=True)
            status = True
        except:
            status = False
        return status
    
    def callCmdline(self, cmd):
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
        #print(args)
    
        proc = Popen(args, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        exitcode = proc.returncode
        #
        print("exitcode: %", exitcode)
        print("err: %", err)
        print("out: %", out)
        return exitcode, out, err
    
        
    def runGetQuery(self, queryurl):
        ''' Run GET query through the Seek API, given
        Arguments:
            server: SEEK server address.
            username: SEEK username
            password: SEEK password
            queryurl: a URL for running the GET query, such as,
                "/people"
                "/assays/3"
            
        Returns:
            resultDic: results in a dictionary.
        
        Example:
            getquery:
                "/people -H \"accept: application/json\""
            Meaning:
                Run http GET on "http://server_url/people" in json format. 
        '''       
        apicmd = self.__apiGet()
        suffix = " -H \"accept: application/json\""
        apiquery = (apicmd + queryurl + suffix)
        return self.__query(apiquery)
        
    def runGetPage(self, queryurl):
        ''' Run GET query through the Seek API, given
        Arguments:
            self.__server: SEEK server address.
            self.__username: SEEK username
            self.__password: SEEK password
            queryurl: a URL for running the GET query, such as,
                "/people"
                "/assays/3"
            
        Returns:
            The original page
        
        Example:
            getquery:
                "/people -H \"accept: application/json\""
            Meaning:
                Run http GET on "http://server_url/people" in json format. 
        '''       
        apicmd = self.__apiGet()
        suffix = " "
        apiquery = (apicmd + queryurl + suffix)
        #print(apiquery)
        #return apiquery
        resultset = self.__queryRaw(apiquery)
        return resultset
        return self.__query(apiquery)
        
    def runSilentQuery(self, apiquery):
        ''' Run a silent query through the Seek API, given
        Arguments:
            server: SEEK server address.
            username: SEEK username 
            password: SEEK password
            apiquery: a GET query, such as,
                
            
        Returns:
            resultset: results in original format.
        
        Example:
            apiquery:
                "/assays/4.xml | grep -e \'sample xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
            
            "/assays/4.xml":  get the output from this url
                ...
                <samples total="2" hidden_count="0">
                    <sample xlink:href="http://dmac.mit.edu:3000/samples/7" xlink:title="t2d00002" id="7" uuid="4087c790-8492-0137-3e0d-000c295a2b25" resourceType="Sample"/>      
                    <sample xlink:href="http://dmac.mit.edu:3000/samples/6" xlink:title="t2d00001" id="6" uuid="28a6f550-8492-0137-3e0d-000c295a2b25" resourceType="Sample"/>    
                </samples>
                ...
            "grep -e \'sample xlink\'": trim the output above to get the value at "sample xlink".
                http://dmac.mit.edu:3000/samples/7 
                http://dmac.mit.edu:3000/samples/6 
            
            resultset:
                http://dmac.mit.edu:3000/samples/7 
                http://dmac.mit.edu:3000/samples/6
        '''       
        apicmd = self.__apiSilent()
        queryi = apicmd + apiquery
        return self.__queryRaw(queryi)
    
    def getIDfromTitle(self, url, title):
        """Get unique ID based on the unique title, through Seek API.
    
        Arguments:
            username: The SEEK username, from request.session.get('username').
            password: The SEEK password, from request.session.get('password').
            storage: The SEEK URL, from request.session.get('storage').
            
            title: a title, such as "library prep assay"
            url: the url for an object, such as "/assays/"

        Returns:
            unique ID, such as 3
            
        Example:
        
        """
        # From the url, such as "/assays/", get all objects accessible to username, in json dictionaries.
        json_objects = self.runGetQuery(url)
        
        title = title.split("/")[-1]
        title = title.strip("\n")
        id = None
        for x in range(0, len(json_objects["data"])):
            if json_objects["data"][x]["attributes"]["title"] == title:
                id = json_objects["data"][x]["id"]
                
        return id
    
    
    def callFileAPI(self, apiurl, file):
        ''' Such as
        
        curl -u 'username:password' -k -X PUT "http://dmac.mit.edu:3000/data_files/19/content_blobs/36" -H "accept: */*" -H "Content-Type: application/octet-stream" -T "/home/huiming/myhome/websites/dmac/themes/SmartAdmin/static/media/uploads/Default_Project/_dbadmin_dropzone-2.PNG"
        '''
        data_file_query = (
            "curl -u '" +
            self.__username + ":" + self.__password +
            "' -k -X PUT \"" + apiurl + "\" "
            "-H \"accept: */*\" -H \"Content-Type: application/octet-stream\" -T \"" +
            file + "\""
        )
        print(data_file_query)
        #call([data_file_query], shell=True)
        #call(["rm", "-r", file])
        exitcode, out, err = self.callCmdline(data_file_query)
        return exitcode, out, err
        
        
    def __reviseURLs(self, htmlpage):
        ''' Revise urls in the htmlpage from the valid urls on Seek server to the urls that will be
        redirected within the DMAC system.
        
        Input
            htmlpage, the htmlpage retrieved from Seek
            
        Output
            htmlpage, in which all urls are revised.
         
        '''
        htmlpage = htmlpage.replace('/assets/', (self.__server + '/assets/'))
        #htmlpage = htmlpage.replace('href="/', ('href="' + server + '/'))
        htmlpage = htmlpage.replace('href="/samples/', ('href="/seek/sample/id='))
        
        return htmlpage
        
    def __getHtmlpageDiv(self, htmlpage, div_id):
        ''' get a division of the original htmlpage from Seek server so it can be shown as an embeded division of
        the htmlpage in DMAC system.
        
        Input
            htmlpage, the htmlpage retrieved from Seek server.
            div_id, such as 'content', the id of the division in the original htmlpage.
            
        Output
            htmlpage, a division of the original htmlpage.
         
        '''
        from BeautifulSoup import BeautifulSoup
        parsed_html = BeautifulSoup(htmlpage)
        # print the page in good format
        #print(parsed_html.prettify())
        #return parsed_html.prettify()
    
        #bodyhtml = parsed_html.body.find('div', attrs={'class':'container-fluid'})
        #bodyhtml = parsed_html.body.find('div', attrs={'class':'table-responsive'})
        bodyhtml = parsed_html.body.find('div', attrs={'id':div_id})
        
        bodytext = bodyhtml.text
        header = parsed_html.head
    
        #return render(request,"index.html", {"report" : report, "form": form})
        #return HttpResponse(bodyhtml)
        #return HttpResponse(htmlpage)
        #return bodyhtml.prettify() + header.prettify()
        return bodyhtml.prettify()
        
    def getPageRequests(self, seekurl):
        ''' Get a seek page via its url by using requests protocol.
        Input
            seekurl, such as '/sample_types/12/samples'
        
        Output
            httpresponse
        '''
        import requests
        #urlIn = server + '/sample_types/12/samples'
        urlIn = self.__server + seekurl
        # no login available, if using redirect
        #return HttpResponseRedirect(urlIn)
        print(urlIn)
    
        # allows login
        response = requests.get(urlIn, auth=(self.__username, self.__password), verify=False)
        #print("response:", response)
        #return response.text
        htmlpage = response.text
        #print("htmlpage:", htmlpage)
        
        # revise urls in the original htmlpage
        htmlpage = self.__reviseURLs(htmlpage)
        
        # get the division of content
        return self.__getHtmlpageDiv(htmlpage, 'content')
    
    
    def __getPageClient(self, seekurl):
        ''' Get a seek page via its url by using django.test.client protocol.
        Input
            seekurl, such as '/sample_types/12/samples'
        
        Output
            httpresponse
            
        Notes
            it works for accessing the localhost only.
        '''
        from django.test.client import Client
        c = Client()
        loginpage = self.__server + '/login/'
        response = c.post(loginpage, {'username': self.__username, 'password': self.__password})
        #return HttpResponse(response.status_code)
    
        # 'http://10.159.0.74:3000/sample_types/12/samples'
        urlIn = self.__server + seekurl
        response = c.get(urlIn)
        print(response.content)
        return HttpResponse(response.content)
    
    def getPageUrllib2(self, seekurl):
        ''' Get a seek page via its url by using urllib2.
        Input
            seekurl, such as '/sample_types/12/samples'
        
        Output
            httpresponse
            
        Notes
            it works for accessing the localhost only.
        '''    
        import urllib2

        seekurl = 'https://api.github.com'

        req = urllib2.Request(seekurl)

        password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, seekurl, self.__username, self.__password)

        auth_manager = urllib2.HTTPBasicAuthHandler(password_manager)
        opener = urllib2.build_opener(auth_manager)

        urllib2.install_opener(opener)

        handler = urllib2.urlopen(req)

    #print handler.getcode()
    #print handler.headers.getheader('content-type')
    #return handler   
    

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
            A dictionary with the info of the object. 
            
        Example 1,
            fullname: "DBAdmin DBAdmin"
            username: 'dbadmin'
            object_url: "/people/"
            object_id: 1
            jsonobject:
                {'data': [{'id': '1', 'type': 'people', 'attributes': {'title': 'DBAdmin DBAdmin'}, 'links': {'self': '/people/1'}}], 'jsonapi': {'version': '1.0'}, 'meta': {'base_url': 'http://dmac.mit.edu:3000', 'api_version': '0.2'}}
        Example 2:
            object_url: "/projects/"
            object_id: 2
            pinfo = self.getInfoObject("/projects/", int(projectid))
            projectname = pinfo['attributes']['title']
        """
        #userquery = ("curl -X GET " + server +
        #         "/people -H \"accept: application/json\"")
        objectdata = None
        if object_id<=0:
            return objectdata
        
        #queryurl = "/people/" + str(object_id)
        queryurl = object_url + str(object_id)
        #print(queryurl)
        jsonobject = self.runGetQuery(queryurl)
        #for item in jsonobject:
        #    print item
        
        if jsonobject is None:
            objectdata = None
        elif "data" in jsonobject:
            objectdata = jsonobject["data"]
        
        return objectdata

    def getTitleFromID(self, object_url, object_id):
        ''' Get title from id, given
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
        Output:
            title of the object.
        
        
        Usage:
            investigation_title = self.getTitleFromID("/investigations/", investigation_id)
        '''
        title = "undefined"
        try:
            id = int(object_id)
        except:
            return title
        
        objinfo = self.getInfoObject(object_url, id)
        #print(objinfo)
        if objinfo is None:
            return title
        
        if 'attributes' in objinfo:
            if 'title' in objinfo['attributes']:
                title =  objinfo['attributes']['title']
        return title
    
    
    
    def getProjects(self):
        """
        Get a list of projects, through the Seek API.

        Arguments:

        Returns:
            A dictionary with SEEK projectss and ids (URLs).
            
        Example:
            Queries:
                curl -s -u 'username':password server_ip:3000/projects.xml | grep -e 'project xlink' | sed -n 's/.*title="\([^"]*\).*/\1/p'
                curl -s -u 'username':password server_ip:3000/investigations.xml | grep -e 'investigation2' | sed -n 's/.*href="\([^"]*\).*/\1/p'
                curl -s -u 'username':password server_ip:3000/investigations.xml | grep -e 'investigation1' | sed -n 's/.*href="\([^"]*\).*/\1/p'
            resultset:
                {'project1': 'http://dmac.mit.edu:3000/projects/1', 'project2': 'http://dmac.mit.edu:3000/projects/2'}
            which is different from the result set returned from the sparql query,
                {'1': rdflib.term.Literal('project1'), '2': rdflib.term.Literal('project2')}
        
        
        Notes: to be completed and tested
        
        """
        
        #investigation_titles = subprocess.Popen([
        #    "curl -s -u \'" + username + "\':" + password + " " + storage +
        #    "/investigations.xml | grep -e \'investigation xlink\' | "
        #    "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"],
        #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        apiquery = "/projects.xml | grep -e \'project xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        
        print(apiquery)
        project_titles = self.runSilentQuery(apiquery)
        print(project_titles)
        
        project_titles = project_titles.split("\n")
        project_titles = list(filter(None, project_titles))
        projects = {}
        for it in project_titles:
            #investigation_id = subprocess.Popen([
            #    "curl -s -u \'" + username + "\':" + password + " " + storage +
            #    "/investigations.xml | grep -e \'" + it +
            #    "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"],
            #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            apiqueryi = "/projects.xml | grep -e \'" + it + "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
            project_id = self.runSilentQuery(apiqueryi)
            
            projects[it] = project_id.strip("\n")
        return projects
    
    def getInvestigations(self, project_title):
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
        
        Notes:
            Modified from getAPIinvestigations()
        """
        
        #investigation_titles = subprocess.Popen([
        #    "curl -s -u \'" + username + "\':" + password + " " + storage +
        #    "/investigations.xml | grep -e \'investigation xlink\' | "
        #    "sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"],
        #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        if project_title is None or project_title=="":
            apiquery = "/investigations.xml | grep -e \'investigation xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        else:
            projectid = self.getIDfromTitle("/projects/", project_title)
            apiquery = "/projects/" + projectid + ".xml | grep -e \'investigation xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        
        #print(apiquery)
        investigation_titles = self.runSilentQuery(apiquery)
        #print(investigation_titles)
        
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
            investigation_id = self.runSilentQuery(apiqueryi)
            
            investigations[it] = investigation_id.strip("\n")
        return investigations
    
    def __getStudyTitle(self, study_id):
        """Get investigation ID based on an investigation, through Seek API.
    
        Arguments:
            username: The SEEK username, from request.session.get('username').
            password: The SEEK password, from request.session.get('password').
            storage: The SEEK URL, from request.session.get('storage').
            study_id: a study id

        Returns:
            study title
            
        Example:
            study_command:
                curl -u 'username':password -X GET 10.159.0.74:3000/studies/5 -H "accept: application/json"
            study_title;
                'title_ultra_low_sequencing'
        """
        queryurl = "/studies/" + study_id
        json_study = self.runGetQuery(queryurl)
        
        study_title = json_study["data"]["attributes"]["title"]
        return study_title
    
    
    def getStudies(self, investigation_id):
        """Get all SEEK studies based on an investigation.
            Modified from get_seek_studies().
            
        Arguments:
            username: The SEEK username, from request.session.get('username').
            password: The SEEK password, from request.session.get('password').
            storage: The SEEK URL, from request.session.get('storage').
            investigation_id: Investigation id

        Returns:
            A dictionary with SEEK studies and URLs.
            
        Example:
            investigation: investigation1
            studies: {'blood sample taken': '1', 'extraction plasma': '2', 'library prep': '3', 'Sequencing cfDNA sampple': '4', 'title_ultra_low_sequencing': '5'}
        """
        #print(investigation)
        
        studies = {}
        
        queryurl = "/investigations/" + investigation_id
        json_study_link = self.runGetQuery(queryurl)
        
        study_count = len(json_study_link["data"]["relationships"]["studies"]["data"])
        for i in range(study_count):
            study_id = json_study_link["data"]["relationships"]["studies"]["data"][i]["id"]
            study_title = self.__getStudyTitle(study_id)
            studies[study_title] = study_id
        
        return studies
    
    def getAssays(self, studyid):
        """Gets the SEEK assays based on a study.
            Modified from get_seek_assays().

        Arguments:
            username: The SEEK username.
            password: The SEEK password.
            storage: The SEEK URL.
            studyid: either 'http://dmac.mit.edu:3000/studies/5' or '5'

        Returns:
            A dictionary with SEEK assay title as the key and assay url as the value, such as, 
                assays:
                    {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}
        """
        # Step 1: Get study id
        study_id = studyid.split("/")[-1]
        #print("study, id:", study, study_id)
        #print("study, id:", study, study_id)
        
        # Step 2. Get all assays for the study
        #This is wrong: apiquery = "/studies/" + study_id + ".xml | grep -e \'study xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        # The followinng is right to get a list oof assays for the study
        apiquery = "/studies/" + study_id + ".xml | grep -e \'assay xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        assay_titles = self.runSilentQuery(apiquery)
        #print("runSilentQuery:", assay_titles)
        # example:
        #   "Zika infection\nlibrary prep assay"
        
        assay_titles = assay_titles.split("\n")
        # example:
        #   ["Zika infection", "library prep assay"]
        
        # convert result set into a list
        assay_titles = list(filter(None, assay_titles))
        #print(assay_titles)
        #        ['Zika infection', 'library prep assay']
        
        assays = {}
        for at in assay_titles:
            apiqueryi = "/studies/" + study_id + ".xml | grep -e \'" + at + "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
            assay_id = self.runSilentQuery(apiqueryi)
            if assay_id is not None or study_id != '':
                assays[at] = assay_id.strip("\n")
            else:
                assays["0"] = "None"
                
        #print("assays:", assays)
        # example:
        #   {'Zika infection': 'http://dmac.mit.edu:3000/assays/5', 'library prep assay': 'http://dmac.mit.edu:3000/assays/4'}
        return assays
    
    def getSamples(self, assayid):
        """Gets the SEEK ssamples based on a assay.
        
        Arguments:
            username: The SEEK username.
            password: The SEEK password.
            storage: The SEEK URL.
            assay_id: assay id, either 'http://dmac.mit.edu:3000/assay/3' or '3'

        Returns:
            A dictionary with SEEK sample IDs and URLs.
        """
        # Step 1. get assay id from assay title, such as '"4"
        assay_id = assayid.split("/")[-1]
        
        # get all samples from the assay id, such as "4"
        apiquery = "/assays/" + assay_id + ".xml | grep -e \'sample xlink\' | sed -n \'s/.*title=\"\\([^\"]*\\).*/\\1/p\'"
        sample_titles = self.runSilentQuery(apiquery)
        print(sample_titles)
        # example:
        #   "sample_title1\nsample_title2"
        
        sample_titles = sample_titles.split("\n")
        # example:
        #   ["sample_title1","sample_title2"]
        
        sample_titles = list(filter(None, sample_titles))
        samples = {}
        for st in sample_titles:
            apiqueryi = "/assays/" + assay_id + ".xml | grep -e \'" + st + "\' | sed -n \'s/.*href=\"\\([^\"]*\\).*/\\1/p\'"
            sample_id = self.runSilentQuery(apiqueryi)
            if sample_id is not None or sample_id != '':
                samples[st] = sample_id.strip("\n")
            else:
                samples["0"] = "None"
                
        # example:
        #   {'sample_title1': 'http://dmac.mit.edu:3000/samples/1', 'sample_title2': 'http://dmac.mit.edu:3000/samples/2'}
        return samples
    
    def getAssayDFs(self, assay):
        """Get the results based on the SEEK assay name.
        Returns data file IDs and titles to show in the result page.

        Arguments:
            storage: SEEK URL
            assay: Name of the assay where the result is stored.

        Returns:
            A Dictionary with data IDs and titles, such as,
                {u'1': u'sample data', u'2': u'sample data 2'}
            
        Notes:
            Modified from get_seek_result(storage, assay) in myFAIR/views.py
        """
        # assay = assay.strip("[").strip("]")
        
        #get_assays_cmd = ("curl -X GET \"" + storage +
        #              "\"/assays -H \"accept: application/json\"")
        #all_assays = subprocess.Popen(
        #    [get_assays_cmd],
        #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
        #json_assays = json.loads(all_assays)
        
        queryurl = "/assays"
        json_assays = self.__seekapi.runGetQuery(queryurl)
        
        assayid = None
        for ar in range(0, len(json_assays["data"])):
            if json_assays["data"][ar]["attributes"]["title"] in assay:
                assayid = json_assays["data"][ar]["id"]
                        
        return self.getAssayDFsFromID(assayid)
    
    def getAssayDFsFromID(self, assayid):
        """Get the results based on the SEEK assay name.
        Returns data file IDs and titles to show in the result page.

        Arguments:
            storage: SEEK URL
            assay: Name of the assay where the result is stored.

        Returns:
            A Dictionary with data IDs and titles, such as,
                {u'1': u'sample data', u'2': u'sample data 2'}
            
        Notes:
            Modified from get_seek_result(storage, assay) in myFAIR/views.py
        """
        results = {}
        if assayid is None or assayid==0:
            return results
        
        queryurl = "/assays/" + assayid
        json_assay = self.runGetQuery(queryurl)
        
        fileidlist = []
        for df in range(0, len(json_assay["data"]["relationships"]["data_files"]["data"])):
            fileidlist.append(
                json_assay["data"]["relationships"]["data_files"]["data"][df]["id"])
        for fileid in fileidlist:
            
            #get_file_cmd = ("curl -X GET \"" + storage + "\"/data_files/" +
            #            fileid + " -H \"accept: application/json\"")
            #file_info = subprocess.Popen(
            #    [get_file_cmd],
            #    stdout=subprocess.PIPE, shell=True).communicate()[0].decode()
            #json_file = json.loads(file_info)
            
            queryurl = "/data_files/" + fileid
            json_file = self.runGetQuery(queryurl)
            
            results[json_file["data"]["id"]
                ] = json_file["data"]["attributes"]["title"]
            
        return results

