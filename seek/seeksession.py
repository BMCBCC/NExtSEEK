#!/usr/bin/env python

'''****************************************************************************
*   Program - A class for running Seek queries through http session.
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

Notes:
Modified from SeekDataTransfer-master/ data_transfer_09.ipynb for testing the download of a snapshot of ISA structure. 

****************************************************************************'''

'''****************************************************************************

*   To run the program
*   For example - python 

*   Logic - 

****************************************************************************'''
import requests
#authentication
import getpass

class SeekSession(object):
    ''' The class is used to run Seek operations, regardless the underlayer query approach. 
    
    Typical usage of the class
    
        session = SeekSession(username, password)
        resultJson = session.getSeekURL(url)
    Or    
        session = SeekSession(None, None)
        session.loginShell()
        resultJson = session.getSeekURL(url)
    '''
    #def __init__(self, server=SEEK_SERVER, username=SEEK_USER, password=SEEK_PWD):
    def __init__(self, server, username, password):
        ''' We do need the username and password for accessing the Seek API.
        Usage:
            session = SeekSession(username, password)
            resultJson = session.getSeekURL(url)
        '''
        self.__server = server
        self.__username = username
        self.__password = password
        
        self.__headers1 = { #headers_json
            "Accept": "application/vnd.api+json", 
            "Content-type": "application/vnd.api+json",
            "Accept-Charset": "ISO-8859-1" 
        } 
    
        ### AUTHENTICATION
        #API_TOKEN = open("token").readline().strip() #"user:password" encoded in base64
        # Refer to: https://www.url-encode-decode.com/base64-encode-decode/
        self.__API_TOKEN = "aHVpbWluZzpKaWFuZ0BuYW4hMTI="

        self.__headers2 = { #headers_token
            "Authorization": "Basic %s" %self.__API_TOKEN,
            #'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
            "Accept": "application/vnd.api+json", #'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            "Content-type": "application/vnd.api+json",
            "Accept-Charset": "ISO-8859-1" #'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
            #'Accept-Encoding': 'none',
            #'Accept-Language': 'en-US,en;q=0.8',
            #'Connection': 'keep-alive'
        }

        self.__headers3 = { #headers_stream
            "Authorization": "Basic %s" %self.__API_TOKEN,    
            "Accept": "application/octet-stream",
            "Content-Type": "application/octet-stream"
        } 
        if username is not None and password is not None:
            session = self.__authenticate(self.__headers1, username, password)
        else:
            session = None
        self.__session = session

    def __authenticate(self, headers, username, password):
        ''' Create a http session, given
        Input:
            username,
            password
        
        Output:
            session, the http session.
        '''
        session = requests.Session()
        session.headers.update(headers)
        #session.auth = (input('Username:'), getpass.getpass('Password'))
        session.auth = (username, password)
        return session
    
    def loginShell(self):
        ''' Create a http session by asking for username and password under shell.
        
        Output:
            session, the http session.
            
        Usage:
            session = SeekSession(None, None)
            session.loginShell()
            resultJson = session.getSeekURL(url)
        '''
        session = requests.Session()
        session.headers.update(self.__headers1)
        session.auth = (input('Username:'), getpass.getpass('Password'))
        self.__session = session
        
    def getSeekURL(self, seekurl):
        ''' Query Seek through a http session, given
        Input:
            self.__session, a valid not None http session.
            seekurl, a valid Seek url, such as, for example,
                "studies/1/"
            
                seekurl_complete = "http://localhost:3000/studies/1/"
        
        Output:
            A json dictionary, with the query result returned from Seek.
            
        Usage:
            from seeksession import SeekSession
            session = SeekSession(user_seek['username'], user_seek['password'])
            seekurl = "http://localhost:3000/studies/1/"
            resultJson2 = session.getSeekURL(seekurl)
            print("resultJson2:", resultJson2)
            
            The result json dictionary is in the following format:
                resultJson2 = {
                    u'data': datadic, 
                    u'jsonapi': {u'version': u'1.0'}
                }
            where datadic is in the same format as returned from,
            
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
        '''
        if self.__session is None:
            return {}
            
        server = self.__server
        if server[-1]!="/":
            server += "/"
            
        seekurl_complete = server + seekurl
        
        #r = session.get(url + "/" + type + "/" + str(id), headers=headers_json)
        r = self.__session.get(seekurl_complete, headers=self.__headers1)
        if (r.status_code != 200):
            # if not okay, print the error message
            print(r.json())
        r.raise_for_status()
        return r.json()
        
    def postSeekURL(self, seekurl, data_json):
        ''' Post a data_json to Seek through a http session, given
        Input:
            self.__session, a valid not None http session.
            seekurl, a valid Seek url, such as, for example,
                seekurl = "studies", which forms the following complete url,
                
                    seekurl_complete = "http://localhost:3000/studies"
                                     = self.__server + "studies",
                    where:
                        self.__server = "http://localhost:3000/"
            data_json, input data in json format, such as
                new_study_json = {}
                new_study_json['data'] = {}
                new_study_json['data']['type'] = 'studies'
                new_study_json['data']['attributes'] = {}
                new_study_json['data']['attributes']['title'] = title
                new_study_json['data']['attributes']['description'] = description
                new_study_json['data']['attributes']['policy'] = {'access':'no_access'}
                new_study_json['data']['attributes']['policy']['permissions'] = [{'resource':{'id':target_project_id,'type':'projects'},'access':'download'}];
                new_study_json['data']['relationships'] = {}
                new_study_json['data']['relationships']['creators'] = {}
                new_study_json['data']['relationships']['creators']['data'] = [{'id' : target_creator_id, 'type' : 'people'}]
                new_study_json['data']['relationships']['investigation'] = {}
                new_study_json['data']['relationships']['investigation']['data'] = {'id' : target_investigation_id, 'type' : 'investigations'}
                new_study_json['data']['relationships']['projects'] = {}
                new_study_json['data']['relationships']['projects']['data'] = {'id' : target_project_id, 'type' : 'projects'}

        Output:
            id, the primary key of the object posted.
            
        Usage:
            from seeksession import SeekSession
            server = "http://localhost:3000/"
            session = SeekSession(server, user_seek['username'], user_seek['password'])
            seekurl = "studies"
            new_study_json = {...}
            study_id = session.postSeekURL(seekurl, new_study_json)
            print("study_id:", study_id)
            
        '''
        if self.__session is None:
            return None
        
        server = self.__server
        if server[-1]!="/":
            server += "/"
            
        seekurl_complete = server + seekurl
        r = self.__session.post(seekurl_complete, json=data_json)
        if (r.status_code != 201):
            print(r.json())
            return None
        
        r.raise_for_status()
        populated_object = r.json()
        print("Registered object: ", populated_object)   
        id = populated_object['data']['id']
        return id
        