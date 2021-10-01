#!/usr/bin/env python

'''****************************************************************************
*   Program - A program for uploading a snapshot of a ISA into Seek system.
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

* Modified based on https://github.com/DoroteaDudas/SeekDataTransfer
# TRANSFER STUDY + DOWNWARD ISA STRUCTURE FROM ONE SEEK TO ANOTHER: STUDY, 2X ASSAYS, 2X DATA FILES
#                                                         assay -> data_file
#                  (project -> investigation) -> study ->
#                                                         assay -> data_file

# SOURCE SEEK:
#    GET/READ/PRINT JSON RESOURCE (ASSAY)    readJsonData()               (session.get)
#    FORMAT RELATIONSHIPS                    formatJsonDataRelationships() / formatJsonDataRelationshipsTitle() 
#    READ DATA FILE BLOB, DOWNLOAD BLOB      readBlobData()(              (session.get, urlopen(Request(url=download_link, headers=headers2)))

#    DETERMINE ISA STRUCTURE                 determineISAstructureFromRelationships()
#    DETERMINE DOWNWARDS ISA STRUCTURE       getDISA()  
#    DETERMINE ALL DOWNWARDS ISA STRUCTURES  getFullDISA()                (from input entry and each of its DISA entries)
        
# TARGET SEEK: 
#    REGISTER STUDY                          registerStudy()              (session.post)
#    REGISTER ASSAY                          registerAssay()              (session.post)
#    REGISTER DATA FILE AND BLOB             registerBlobData()           (session.post)
#    UPLOAD BLOB INTO DATA FILE              uploadBlobData()             (session.put)
#    COMBINES REGISTER DATA FILE AND UPLOAD BLOB   TransferData()

#    REGISTER / UPLOAD STUDY AND BELOW       registerAndCopyStudyAndBelow()
#    DELETES THE ISA STRUCTURE               deleteISA()                  

# USING 2 SEEKS

****************************************************************************

*   To run the program, pass three arguments with the python script on command line.
*   For example - python snapshot.py ...

****************************************************************************'''
"""
Import the libraries so that they can be used within the notebook

  * **requests** is used to make HTTP calls
  * **json** is used to encode and decode strings into JSON
  * **string** is used to perform text manipulation and checking
  * **pandas** helps format the JSON data in a more readable format
"""

import requests
import json
import string
# Importing the libraries we need to format the data in a more readable way. 
import pandas as pd
from pandas.io.json import json_normalize
#authentication
import getpass
#import urllib.request
#from urllib.request import urlopen, Request
from urllib2 import urlopen, Request
from PIL import Image
import io
#from IPython.core.display import display, HTML
#display(HTML("<style>.container { width:98% !important; }</style>"))

import argparse

### FUNCTIONS

def authenticate(headers):
    session = requests.Session()
    session.headers.update(headers)
    #session.auth = (input('Username:'), getpass.getpass('Password'))
    
    session.auth = ('huiming', getpass.getpass('Password')) 
    return session

### GET JSON
def json_for_resource(session, headers_json, url, type, id):
    ''' This is identical to,
            seekdb = SeekDB(None, None, None)
            user_seek = seekdb.getSeekLogin(request)
            object = "/" + type + "/"
            resultJson = seekdb.getInfoObject(object, id)
            
            resultJson == this['data']
    
    '''
    r = session.get(url + "/" + type + "/" + str(id), headers=headers_json)
    if (r.status_code != 200):
      # if not okay, print the error message
        print(r.json())
    r.raise_for_status()
    return r.json()

### READ / PRINT JSON
def readJsonData(session, headers_json, url, data_id, data_type):
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
    result_json = json_for_resource(session, headers_json, url, data_type, data_id)
    filetitle = result_json['data']['attributes']['title']
    print("Name of \'" + data_type + "\': " + filetitle + "\n")
    #print(result_json)
    return result_json

### FORMAT RELATIONSHIPS OF A JSON ([{'type':'data_files', 'id':3, 'title':'New Image'}])
def formatJsonDataRelationshipsTitle(session, headers_json, source_base_url, input_data):#, data_types_list
    files = []
    source_relationships = input_data['data']['relationships']
    
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
            
            j = json_for_resource(session,headers_json,source_base_url,item['type'],item['id'])  
            
            files.append({
                'type':source_data_type, #j['data']['type'],
                'id':source_data_id, #j['data']['id'],
                'title':j['data']['attributes']['title'],      
            })

        else:
            for item in source_dtype_entry:
                #print("item ", item)
                #print(dtype, ": ", item['type'], item['id'])
                
                source_data_id = item['id']
                source_data_type = item['type']
                if(item['type']=='people'): #instead of type 'people', passing submitter, creators etc.
                    source_data_type = str(dtype)
                
                j = json_for_resource(session,headers_json,source_base_url,item['type'],item['id'])  
                
                files.append({
                    'type':source_data_type,
                    'id':source_data_id, #j['data']['id'],
                    'title':j['data']['attributes']['title'],      
                })
                

        #if(source_data_type != 'none'): print("\t \t", dtype, ": ", source_data_type, "/", source_data_id)                

    print() 
    print(str(len(files)) + " relationships found: \n") #print(str(len(files)) + " \'" + grep_typep + "\' found: \n") 
    print(json_normalize(files)) 
    return files

### FORMAT RELATIONSHIPS OF A JSON ([{'type':'data_files', 'id':3}])
def formatJsonDataRelationships(input_data):
    files = []
    source_relationships = input_data['data']['relationships']
    
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

### READ DATA_FILE DATA, GET BLOB DATA
def readBlobData(session, headers_json, headers_token, url, data_id, data_type):
    result_json = json_for_resource(session, headers_json, url, data_type, data_id)#uses session
    
    filetitle = result_json['data']['attributes']['title']
    #print("Name of \'" + data_type + "\': " + filetitle + "\n")
    #print("Policy: ", result_json['data']['attributes']['policy'],"\n")
    filelicense = result_json['data']['attributes']['license']
    
    blob = result_json['data']['attributes']['content_blobs'][0]
    #print("Blob: ", blob,"\n")
    
    filename = blob['original_filename']
    filetype = blob['content_type']

    
    link = blob['link']
    download_link = link + "/download"
    #print("Download link is: " + download_link)
    
    #get blob data
    #response = urllib.request.urlopen(download_link)
    ###from urllib.request import urlopen, Request
    req = Request(url=download_link, headers=headers_token) 
    data = urlopen(req).read()
    
    #data = response.read()
    #print(response)
    #print(data)
    return result_json, filetitle, filename, filetype, filelicense, link, download_link, data

###############################################################


### REGISTER STUDY
def registerStudy(session, in_study_json, target_project_id, target_investigation_id, target_creator_id):
    new_study_json = {}
    new_study_json['data'] = {}
    new_study_json['data']['type'] = 'studies'

    new_study_json['data']['attributes'] = {}
    new_study_json['data']['attributes']['title'] = in_study_json['data']['attributes']['title']
    new_study_json['data']['attributes']['description'] = in_study_json['data']['attributes']['description']

    #new_assay_json['data']['attributes']['policy'] = in_assay_json['data']['attributes']['policy']
    new_study_json['data']['attributes']['policy'] = {'access':'no_access'}
    new_study_json['data']['attributes']['policy']['permissions'] = [{'resource':{'id':target_project_id,'type':'projects'},'access':'download'}];

    #new_assay_json['data']['attributes']['assay_class'] = in_assay_json['data']['attributes']['assay_class']
    #new_assay_json['data']['attributes']['assay_type'] = in_assay_json['data']['attributes']['assay_type']
    #new_assay_json['data']['attributes']['technology_type'] = in_assay_json['data']['attributes']['technology_type']

    new_study_json['data']['relationships'] = {}
    new_study_json['data']['relationships']['creators'] = {}
    new_study_json['data']['relationships']['creators']['data'] = [{'id' : target_creator_id, 'type' : 'people'}]
    #new_study_json['data']['relationships']['study'] = {}
    #new_study_json['data']['relationships']['study']['data'] = {'id' : target_study_id, 'type' : 'studies'}
    new_study_json['data']['relationships']['investigation'] = {}
    new_study_json['data']['relationships']['investigation']['data'] = {'id' : target_investigation_id, 'type' : 'investigations'}
    new_study_json['data']['relationships']['projects'] = {}
    new_study_json['data']['relationships']['projects']['data'] = {'id' : target_project_id, 'type' : 'projects'}

    r = session.post(target_base_url + '/studies', json=new_study_json)
    r.raise_for_status()
    populated_study = r.json()
    print("Registered study: ", populated_study)   
    study_id = populated_study['data']['id']
    
    return new_study_json, study_id


### REGISTER ASSAY
def registerAssay(session, in_assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id):
    new_assay_json = {}
    new_assay_json['data'] = {}
    new_assay_json['data']['type'] = 'assays'

    new_assay_json['data']['attributes'] = {}
    new_assay_json['data']['attributes']['title'] = in_assay_json['data']['attributes']['title']
    new_assay_json['data']['attributes']['description'] = in_assay_json['data']['attributes']['description']

    #new_assay_json['data']['attributes']['policy'] = in_assay_json['data']['attributes']['policy']
    new_assay_json['data']['attributes']['policy'] = {'access':'no_access'}
    new_assay_json['data']['attributes']['policy']['permissions'] = [{'resource':{'id':target_project_id,'type':'projects'},'access':'download'}];

    new_assay_json['data']['attributes']['assay_class'] = in_assay_json['data']['attributes']['assay_class']
    new_assay_json['data']['attributes']['assay_type'] = in_assay_json['data']['attributes']['assay_type']
    new_assay_json['data']['attributes']['technology_type'] = in_assay_json['data']['attributes']['technology_type']

    new_assay_json['data']['relationships'] = {}
    new_assay_json['data']['relationships']['creators'] = {}
    new_assay_json['data']['relationships']['creators']['data'] = [{'id' : target_creator_id, 'type' : 'people'}]
    new_assay_json['data']['relationships']['study'] = {}
    new_assay_json['data']['relationships']['study']['data'] = {'id' : target_study_id, 'type' : 'studies'}
    new_assay_json['data']['relationships']['investigation'] = {}
    new_assay_json['data']['relationships']['investigation']['data'] = {'id' : target_investigation_id, 'type' : 'investigations'}
    new_assay_json['data']['relationships']['projects'] = {}
    new_assay_json['data']['relationships']['projects']['data'] = {'id' : target_project_id, 'type' : 'projects'}

    r = session.post(target_base_url + '/assays', json=new_assay_json)
    r.raise_for_status()
    populated_assay = r.json()
    print("Registered assay: ", populated_assay)   
    assay_id = populated_assay['data']['id']
    
    return assay_id


### REGISTER DATA FILE AND BLOB 
def registerBlobData(session, base_url, data_type, filetitle, filelicense, blob, target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id):
    data_array_name = {}
    data_array_name['data'] = {}
    data_array_name['data']['type'] = data_type
    
    data_array_name['data']['attributes'] = {}
    data_array_name['data']['attributes']['title'] = filetitle
    data_array_name['data']['attributes']['license'] = filelicense #'CC-BY-4.0'
    #data_array_name['data']['attributes']['policy'] = {'access':'download'}
    data_array_name['data']['attributes']['policy'] = {'access':'no_access'}
    data_array_name['data']['attributes']['policy']['permissions'] = [{'resource':{'id':target_project_id,'type':'projects'},'access':'download'}];
    data_array_name['data']['attributes']['content_blobs'] = [blob] #error if blob is not there
        
    data_array_name['data']['relationships'] = {}
    data_array_name['data']['relationships']['projects'] = {}
    data_array_name['data']['relationships']['projects']['data'] = [{'id' : target_project_id, 'type' : 'projects'}]
    data_array_name['data']['relationships']['investigations'] = {}
    data_array_name['data']['relationships']['investigations']['data'] = [{'id' : target_investigation_id, 'type' : 'investigations'}]
    data_array_name['data']['relationships']['studies'] = {}
    data_array_name['data']['relationships']['studies']['data'] = [{'id' : target_study_id, 'type' : 'studies'}]
    data_array_name['data']['relationships']['assays'] = {}
    data_array_name['data']['relationships']['assays']['data'] = [{'id' : target_assay_id, 'type' : 'assays'}]
    data_array_name['data']['relationships']['creators'] = {}
    data_array_name['data']['relationships']['creators']['data'] = [{'id' : target_creator_id, 'type' : 'people'}]
    
    #register data file
    r = session.post(base_url + '/' + data_type, json = data_array_name)
    r.raise_for_status()

    populated_data_file = r.json()
    print("Registered data_file: ", populated_data_file["data"])
    #print("Registered json:")
    data_file_id = populated_data_file["data"]['id']
    data_file_link = populated_data_file['data']['attributes']['content_blobs'][0]['link']  

    
    return data_file_id, data_file_link


### UPLOAD BLOB INTO DATA FILE
def uploadBlobData(session, headers_json, headers_stream, base_url, data_type, blob_id, blob_url, binary_data):

    #get url from json content blob
    #blob_url = registered_json_data['data']['attributes']['content_blobs'][0]['link']    
 
    #PUT data
    upload = session.put(blob_url, data = binary_data, headers = headers_stream)
    upload.raise_for_status()
    
    #print content blob
    #blob_id = registered_json_data['data']['id']  
    created_json = json_for_resource(session, headers_json, base_url, data_type, blob_id)
    print("Uploaded blob data: ", created_json['data']['attributes']['content_blobs'])
    
        
### COMBINES REGISTER DATA FILE AND UPLOAD BLOB (not needed)
def TransferData(session, headers_json, headers_stream, base_url, data_type, filetitle, filelicense, blob, dataBinary,
    target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id): # register, upload
    #registered_json_data = registerBlobData(session, base_url, data_type, filetitle, blob)
    #uploadBlobData(session, base_url, data_type, registered_json_data, dataBinary)
    
    #target_data_file  = registerBlobData(
    #    session2, target_base_url, target_data_file_data_type, target_filetitle, target_filelicense, target_blob, 
    #    target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id2)
    #target_data_file_id = target_data_file[0]
    #target_data_file_link = target_data_file[1]
    
    #uploadBlobData(session2, headers3, target_base_url, target_data_file_data_type, target_data_file_id, target_data_file_link, dataBinary)
    
    target_data_file  = registerBlobData(
        session, base_url, data_type, filetitle, filelicense, blob, 
        target_project_id, target_investigation_id, target_study_id, target_assay_id, target_creator_id)
    target_data_file_id = target_data_file[0]
    target_data_file_link = target_data_file[1]
    
    print()
    uploadBlobData(session, headers_json, headers_stream, base_url, data_type, target_data_file_id, target_data_file_link, dataBinary)      

### ISA STRUCTURE (takes in input data type and formatted relationships ([{'type':'data_files', 'id':3}]))
### defines the hierarchy of the data types
def determineISAstructureFromRelationships(data_type, input_relationships):
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

### GET DISA (DOWNWARDS ISA STRUCTURE)
def getDISA(session, headers_json, url, data_id, data_type): #uses: readJsonData(), formatJsonDataRelationshipsTitle(), determineISAstructureFromRelationships()

    ### READ JSON FILE
    print("FILE: ")
    source_json = readJsonData(session, headers_json, url, data_id, data_type)
    #print(source_json['data']['relationships'])
    
    ### FORMAT RELATIONSHIPS
    print("RELATIONSHIPS: ")
    source_relationships = formatJsonDataRelationshipsTitle(session, headers_json, url, source_json)
    #source_relationships = formatJsonDataRelationships(source_json)
    
    ### DETERMINE DISA
    print();print("ISA STRUCTURE: ")
    isas = determineISAstructureFromRelationships(data_type, source_relationships)
    
    return isas[1]#isa_structure_down (DISA)

### GET DISA OF THE ORIGINAL JSON ENTRY AND OF EACH OF ITS RESULT ENTRIES

# 1st element is the intial entry
#   [intial entry e.g. study, [list of its downwards isa structure]]
#   [1st element of downwards ISA, [list of its downwards isa structure]]
#   ...
#   [last element of downwards ISA, [list of its downwards isa structure]]

def getFullDISA(session1, headers1, source_base_url, source_json_id, source_data_type):#uses: getDISA()
    ### ISA STRUCTURE OF THE INITAL FILE
    out = getDISA(session1, headers1, source_base_url, source_json_id, source_data_type)
    
    ### GET THE ISA STRUCTURE OF EACH ENTRY FROM 'out' (ISA STRUCTURE OF THE INITAL FILE)
    isa_struct = []
    isa_struct.append([{'type': source_data_type, 'id': source_json_id}, out])
    for entry_num in range(0, len(out)):
        out_temp = getDISA(session1, headers1, source_base_url, out[entry_num]['id'], out[entry_num]['type'])
        #also checking the DISA for data_files, just to not omit anything (not likely that they have any)
        if(len(out_temp)>0):#if there is a DISA
            print("OUTPUT:\n", json_normalize(out_temp),"\n")
            isa_struct.append([out[entry_num], out_temp])
        else:
            out_temp = [];
            print("OUTPUT: empty \n")  
            isa_struct.append([out[entry_num], out_temp])
            
    return isa_struct



def download(headers1):
    session1 = authenticate(headers1)

    ### SOURCE DATA PARAMETERS

    source_base_url = 'http://localhost:3000'

    ########### ISA structure ########
    #### project 
    #source_project_id = 2      # Project Alpha
    #source_data_type = 'projects'

    ### data file (with Project Alpha)
    #source_data_id = 35 # Network Image                
    #source_data_type = 'data_files'

    ### data file (with Project Alpha) (also in Default Project)
    #source_data_id = 1 # Pink Test Image               
    #source_data_type = 'data_files'

    #### investigation (with Project Alpha)
    #source_investigation_id = 3 # investigation one
    #source_data_type = 'investigations'
    #source_data_type_alt = 'investigation'

    #### study (with investigation one)
    source_study_id = 1 # study one
    source_data_type = 'studies'    
    #source_data_type_alt = 'study'
    
    #### assay (with study one) 
    #source_assay_id = 3 # assay linked to data file
    #source_data_type = 'assays'

    ### data file (with "assay linked to data file")  
    #source_data_id = 4 # New Pink Image                
    #source_data_type = 'data_files'

    #### assay (with study one) 
    #source_assay_id = 4 # Assay to be copied
    #source_data_type = 'assays'

    ### data file (with "Assay to be copied") 
    #source_data_id = 38 # Network Image                
    #source_data_type = 'data_files'


    ### people (with Project Alpha)
    #source_person_id = 1 # Dorotea Dudas                
    #source_data_type = 'creators'
    #source_data_type_alt = 'creator'

    ### people (with Default Project)
    #source_person_id = 3 # Teodora Dudas                
    #source_data_type = 'creators'
    #source_data_type_alt = 'creator'

    source_json_id = source_study_id
    #source_json_id = source_investigation_id
    
    ### GET/READ/PRINT JSON RESOURCE (ASSAY)
    source_json = readJsonData(session1, headers1, source_base_url, source_json_id, source_data_type)
    print(source_json)
    
    ### FORMAT RELATIONSHIPS OF A JSON 
    #source_relationships = formatJsonDataRelationshipsTitle(session1, headers1, source_base_url, source_json)
    source_relationships = formatJsonDataRelationships(source_json)


    ### ISA STRUCTURE
    isas = determineISAstructureFromRelationships(source_data_type,source_relationships)

    ### GET DISA (DOWNWARDS ISA STRUCTURE)
    out = getDISA(session1, headers1, source_base_url, source_json_id, source_data_type)
    print("OUTPUT:\n", json_normalize(out))
    
    return session1, source_base_url, source_json_id, source_data_type #source_json, 

def upload(headers1):
    print("okay")
    session2 = authenticate(headers1)
    ### TARGET DATA PARAMETERS (ENTRY POINT FOR COPYING)

    ### DATABASE
    #target_base_url = 'http://localhost:4000'
    target_base_url = 'http://doroteadesktop:4000'

    ### TARGET PROJECT
    target_project_id = 2 # Project Alpha
    target_project_type = 'projects'

    ### TARGET INVESTIGATION
    target_investigation_id = 4 # investigation two
    target_investigation_data_type = 'investigatons'

    ### PEOPLE (THIS IS NOT RESOLVED NICELY YET, SO FOR NOW JUST SETTING NOT COPYING)
    target_creator_id = 1      # Dorotea           (same id as source seek, since they are originaly clones)
    #target_creator_id2 = 3    # Teodora           (same id as source seek, since they are originaly clones)
    
    return session2, target_base_url, target_project_id, target_investigation_id, target_creator_id

### REGISTER THE ISA STRUCTURE DOWN (DISA) IN THE TARGET DATABASE AND COPY DATA
### uses: getFullDISA() -> getDISA() -> readJsonData(), formatJsonDataRelationshipsTitle(), determineISAstructureFromRelationships()
### uses: readJsonData(), registerStudy(), 
### uses: readJsonData(), registerAssay(),
### uses: readBlobData(), registerBlobData(), uploadBlobData()
def registerAndCopyStudyAndBelow(session1, session2, headers1, headers2, headers3, 
                                 source_base_url, source_json_id, source_data_type, #source_json, 
                                 target_base_url, target_project_id, target_investigation_id, target_creator_id):#isa_structure
    
    ### GET DOWNWARD ISA STRUCTURE
    isa_structure = getFullDISA(session1, headers1, source_base_url, source_json_id, source_data_type)    

    ### READ SOURCE JSON
    source_json = readJsonData(session1, headers1, source_base_url, source_json_id, source_data_type)
    
    ### PEOPLE need to be improved later
    #target_creator_id = 1      # Dorotea           (same id as source seek, since they are originaly clones)   
    
    ### REGISTER TARGET JSON (STUDY) 
    out_json = registerStudy(session2, source_json, target_project_id, target_investigation_id, target_creator_id)#out_json[0] - json   ;  #out_json[1] - id
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

    ### GO THROUGH DISA - READ, REGISTER, UPLOAD   (isa_structure[0][1][x] (from 0) or isa_structure[x][0] (from 1))
    ### ASSAYS -> DATA_FILES
    if(len(isa_structure)>1):# if there is DISA (1st one is the initial source json)
        for x in range(0, len(isa_structure)):# go through DISA  
            if(isa_structure[x][0]['type']=='assays'):# if it is an assay
                
                ### READ JSON
                assay_json = readJsonData(session1, headers1, source_base_url, isa_structure[x][0]['id'], isa_structure[x][0]['type'])
                
                ### REGISTER ASSAY (in second seek and get the id)
                target_assay_id = registerAssay(session2, assay_json, target_project_id, target_investigation_id, target_study_id, target_creator_id)
            
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
    
### DELETE THE COPIED ISA STRUCTURE (USING the output from getFullDISA())
def deleteISA(session, headers_json, base_url, data_id, data_type):
    
    ### GET DISA FROM COPIED DATA (could also use output from getDISA)
    isa_structure = getFullDISA(session, headers_json, base_url, data_id, data_type)
    
    for x in reversed(range(0, len(isa_structure))):  
        #print(isa_structure[x][0])
        print(isa_structure[x][0]['type'], isa_structure[x][0]['id'])
        
        ### READ JSON TO GET THE LINK FOR DELETION
        json_entry = json_for_resource(session, headers_json, base_url, isa_structure[x][0]['type'], isa_structure[x][0]['id'])
        
        ### LINK TO ENTRY 
        json_entry_url = json_entry['data']['links']['self']
        
        ### DELETE ENTRY
        session.delete(base_url + json_entry_url)
        
    print("DONE")

def test():
    ### AUTHENTICATION
    #API_TOKEN = open("token").readline().strip() #"user:password" encoded in base64
    # Refer to: https://www.url-encode-decode.com/base64-encode-decode/
    API_TOKEN = "aHVpbWluZzpKaWFuZ0BuYW4hMTI="

    headers1 = { #headers_json
        "Accept": "application/vnd.api+json", 
        "Content-type": "application/vnd.api+json",
        "Accept-Charset": "ISO-8859-1" 
    } 
    session1, source_base_url, source_json_id, source_data_type = download(headers1)
    return

    headers2 = { #headers_token
        "Authorization": "Basic %s" %API_TOKEN,
        #'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        "Accept": "application/vnd.api+json", #'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        "Content-type": "application/vnd.api+json",
        "Accept-Charset": "ISO-8859-1" #'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        #'Accept-Encoding': 'none',
        #'Accept-Language': 'en-US,en;q=0.8',
        #'Connection': 'keep-alive'
    }

    headers3 = { #headers_stream
        "Authorization": "Basic %s" %API_TOKEN,    
        "Accept": "application/octet-stream",
        "Content-Type": "application/octet-stream"
    } 
    
    
    session2, target_base_url, target_project_id, target_investigation_id, target_creator_id = upload(headers1)
    
    registerAndCopyStudyAndBelow(session1, session2, headers1, headers2, headers3, 
        source_base_url, source_json_id, source_data_type, #source_json, 
        target_base_url, target_project_id, target_investigation_id, target_creator_id)#, isa_structure

    deleteISA(session2, headers1, target_base_url, 11, 'studies')
    
    """Close the HTTP **session**"""
    session1.close()
    session2.close()

def test2():
    from seeksession import SeekSession
    session = SeekSession("huiming", "Jiang@nan!12")
    seekurl = "http://localhost:3000/studies/1/"
    resultJson = session.getSeekURL(seekurl)
    print(resultJson)

def main():
    parser = argparse.ArgumentParser(description="Download and upload a snapshot of ISA from a Seek to another Seek.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    '''
    parser.add_argument('inputFilename', help='Input matrix file in tab-delimited txt format')
    parser.add_argument('-m', '--colormappingfile', metavar='colormapping_file',
        help='Input file for the mapping between cluster name and color for the UMAP plot.', default=None)
    
    # this option is foor a txt file with a list of targets, which is a subset of all targets in the
    # feature matrix file, i.e., the list of first column in the inputFilename
    parser.add_argument('-f', '--predictionfile', metavar='prediction_file',
        help='Input file for the list of targets  predicted.', default=None)
    
    #parser.add_argument('outputFilename', help='Output tab delimited file')
    #parser.add_argument('kmerSize', type=int, help='k-mer length')
    #parser.add_argument('-s', '--single-directed', action='store_true',
    #                    help='Avoid outputting the whole skew-simmetric graph and output only one edge between two nodes',
    #                    dest='single_directed')
    
    args = parser.parse_args()
    inputfile = args.inputFilename
    colormappingfile = args.colormappingfile
    '''
    
    #test()
    test2()
    return


if __name__ == "__main__":
    main()
