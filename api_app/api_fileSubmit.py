#!/usr/bin/env python
import subprocess
import json
from subprocess import call

import string
import getpass
from urllib2 import urlopen, Request

import urllib2
import io
import argparse

SERVER = "http://test-server"
USERNAME = ''
PASSWORD = ''
USERPWD = " "
AUTH_URL = "/api/rest-auth/login/"
SAMPLE_FILE_ACCESSOR_NAME = "file_"         # such as 'file_qc', where the suffix 'qc' matches the suffix in 'link_qc'.
SAMPLE_LINK_ACCESSOR_NAME = "link_"         # such as 'link_qc'

def runQuery(url, server=None, token=None):
    if token is not None:
        return runAuthQuery(url, token, server)
    
    suffix = "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
    serverIn = SERVER
    if server is not None:
        serverIn = server
    
    prefix = "curl " + USERPWD + " -s -X GET " + serverIn
    suffix = " -H 'accept: application/json'"
    apicmd = prefix + url + suffix
    print(apicmd)
        
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    return resultset

def runAuthQuery(url, token, server=None):
    suffix = "' | grep -oPm250 '(?<=<d:href>)[^<]+'"
    
    serverIn = SERVER
    if server is not None:
        serverIn = server
        
    prefix = "curl -s -X GET " + serverIn
    suffix = " -H 'Authorization: Token " + token + "' -H 'accept: application/json'"
    apicmd = prefix + url + suffix
    print(apicmd)
        
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    return resultset

def getDseqFiles(sample_id):
    try:
        id = int(sample_id)
        url = "/api/samples/" + str(id) + "/"
        search = 0
    except:
        uid = sample_id
        url = "/api/samples/?search=" + str(uid)
        search = 1
    
    resultset = list(runQuery(url))
    dic0 = json.loads(resultset[0])
    print(dic0)
    
    if search==1:
        dic0 = dic0[0]

    for key, value in dic0.iteritems():
        if "file_primarydata" in key:
            filename = value
            file_uid, file_link = searchDatafileUID(filename)
            if len(file_link)>0:
                downloadFile(file_link)
                
    filef = ""
    if "file_primarydata_forward" in dic0:
        filef = dic0["file_primarydata_forward"]
    
    filer = ""
    if "file_primarydata_forward" in dic0:
        filer = dic0["file_primarydata_reverse"]
        
    print("forward reads: ", filef)
    print("reverse reads: ", filer)
    return filef, filer

def parseDatafile(df_dic, ifDownload=False):
    df_uid = ''
    if not isinstance(df_dic, dict):
        print('Error: No data file info is retrieved from DB.')
        return df_uid
        
    if 'status' not in df_dic:
        print('Error: Data file info incomplete.')
        return df_uid
        
    status = df_dic['status']
    if not status:
        print('Error: Data file info incorrect: %s'%df_dic['msg'])
        return df_uid
        
    df_uid = df_dic['uid']
    print("Data file has valid UID: %s "%df_uid)
    return df_uid

def parseExternalDatafile(filename, filelink):
    msg = 'To be implemented'
    status = 0
    if PRIDE_URL in filelink:
        from api_calls_pride import verifyPrideFileDownload
        msg, status = verifyPrideFileDownload(filename)
        
    return msg, status


def searchSampleFiles(sample_keyword, server, token):
    fileDicList = []
    
    if len(str(sample_keyword))==0:
        print("No sample found: empty keyword")
        return fileDicList
    
    url = "/api/samples/?search=" + str(sample_keyword)
    resultset = list(runQuery(url, server, token))
    if len(resultset)==0:
        print("No sample found: no match")
        return fileDicList
    
    jsonstr = resultset[0]
    dicList = json.loads(jsonstr)
    if len(dicList)==0:
        print("No sample found: no match")
        return fileDicList
    
    for dici in dicList:
        fileDic = {}
        for key, value in dici.iteritems():
            if "file_" in key:
                df_dic = value
                if isinstance(df_dic, dict):
                    df_uid = parseDatafile(df_dic)
                else:
                    filelink_key = key.replace('file_','link_')
                    if filelink_key in dici:
                        filename = value
                        filelink = dici[filelink_key]
                        print("Data file is external: %s "%filelink) 
                        msg, status = parseExternalDatafile(filename, filelink)
                    else:
                        print("Data file is not external: %s "%filelink)  
                
                fileDic[key] = df_uid
        fileDic['sample_uid'] =  dici['uid']
        fileDicList.append(fileDic)
    print("Number of samples found: %d"%len(fileDicList))
    return fileDicList
    
def querySampleFiles(sample_id, server, token):
    fileDic = {}
    try:
        id = int(sample_id)
        url = "/api/samples/" + str(id) + "/"
    except:
        print("No sample found: not valid sample id")
        return fileDic
    
    resultset = list(runQuery(url, server, token))
    if len(resultset)==0:
        print("No sample found: no match")
        return fileDic
    
    jsonstr = resultset[0]
    sample_dic = json.loads(jsonstr)
    if not sample_dic:
        print("No sample found: empty sample meta-data")
        return fileDic
    
    if 'sample_uid' not in sample_dic:
        print("No sample found: sample uid not available")
        return fileDic

    for key, value in sample_dic.iteritems():
        if "file_" in key:
            fileDic[key] = value
            '''
            filename = value
            file_uid, file_link = searchDatafileUID(filename)
            if len(file_link)>0:
                downloadFile(file_link)
            ''' 

    fileDic['sample_uid'] =  sample_dic['uid']
    return fileDic    
    
    
def getSampleFiles(sample_id, server=None, token=None):
    try:
        id = int(sample_id)
        url = "/api/samples/" + str(id) + "/"
        fileDic = querySampleFiles(id, server, token)
        fileDicList = [fileDic]
    except:
        sample_keyword = sample_id
        url = "/api/samples/?search=" + str(sample_keyword)
        fileDicList = searchSampleFiles(sample_keyword, server, token)

    return fileDicList

def searchDatafileUID(datafilename):
    if len(datafilename.strip())==0:
        return "", ""
    
    url = "/api/datafiles/?search=" + str(datafilename.strip())
    resultset = runQuery(url)
    dic0 = json.loads(resultset[0])
    dic0 = dic0[0]
    datafileuid = ""
    datafilelink = ""
    if "title" in dic0:
        datafileuid = dic0["title"]
        datafilelink = dic0['link']
        
    print("datafileuid: ", datafileuid)
    print("datafilelink: ", datafilelink)
    return datafileuid, datafilelink
    

def downloadFile(url):
    file_name = url.split('/')[-1]
    u = urllib2.urlopen(url)
    f = open(file_name, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print("Downloading: %s Bytes: %s" % (file_name, file_size))

    file_size_dl = 0
    block_sz = 8192
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
    f.close()
    
def dwonloadDF(url, filename, username, password):
    import urllib2
    req = urllib2.Request(url)
    base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
    authheader =  "Basic %s" % base64string
    req.add_header("Authorization", authheader)
    res = urllib2.urlopen(req)
    with open(filename,'wb') as output:
        output.write(res.read())

def submitSalmonJob(fileDownload):
    filef = ""
    if "file_primarydata_forward" in fileDownload:
        filef = fileDownload["file_primarydata_forward"]
    
    filer = ""
    if "file_primarydata_forward" in fileDownload:
        filer = fileDownload["file_primarydata_reverse"]
        
    if len(filef)==0 or len(filer)==0:
        print("Exit: not paired reads")
        return

    if "_1_sequence.fastq" not in filef:
        print("Exit: fastq file for forward reads not in standard format: ", filef)
        return
    
    fileprefixf = filef.replace("_1_sequence.fastq", "")
    
    if "_2_sequence.fastq" not in filer:
        print("Exit: fastq file for reverse reads not in standard format: ", filer)
        return
    
    fileprefixr = filer.replace("_2_sequence.fastq", "")
    
    if fileprefixf!=fileprefixr:
        print("Exit: fastq files for forward and reverse reads not match")
        return
    
    prefix = "sbatch ./salmon.sh "
    apicmd = prefix + fileprefixr
    try:
        call([apicmd], shell=True)
        status = True
        print(apicmd)
    except:
        status = False
        print("Failed in submitting Salmon alignment: " + apicmd)
    return status
        
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    return resultset

def getAuthToken(username, password, server=None):
    if username is None:
        print("Error: User name is not valid")
        return None
    if password is None:
        print("Error: password is not valid")
        return None
    
    serverIn = SERVER + AUTH_URL
    if server is not None:
        serverIn = server + AUTH_URL
    
    prefix = "curl -X POST -d "
    pwd = '"username": "' + username + '","password": "' + password + '"'
    pwd = "'{" + pwd + "}'"
    suffix = " -H 'Content-Type: application/json' "
    apicmd = prefix + pwd + suffix + serverIn
    print(apicmd)
        
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    
    dic0 = json.loads(resultset[0])
    token = ''
    if 'key' in dic0:
        token = dic0['key']
    elif 'auth_token' in dic0:
        token = dic0['token']
        
    print("Auth token: %s"%token)
    return token

def runSalmonWorkflow(sampleid, server):
    fileDicList = getSampleFiles(sampleid, server)
    for fileDic in fileDicList:
        if 'sample_uid' in fileDic:
            print('sample_uid: %s'% fileDic['sample_uid'])
        else:
            continue
        
        fileDownload = {}
        n = 0
        for key, value in fileDic.iteritems():
            if "file_" in key:
                datafile_uid = value
                if datafile_uid in fileDic:
                    datafile_link = fileDic[datafile_uid]
                    if len(datafile_link)>0:
                        downloadFile(datafile_link)
                        fileDownload[key] = datafile_uid
        submitSalmonJob(fileDownload)

def getSampleTypes(diclist_ins):
    sampleTypes = []
    mapping = {}
    msg = 'Error: the following sample attibutes not in the right format sampleType::attribute: '
    status = 1
    for dici in diclist_ins:
        field = dici['Field']
        dbField = dici['Database Field']
        if "::" not in dbField:
            msg += dbField + ';'
            print(msg)
            status = 0
            continue
            
        sampleType, attribute = dbField.split("::")
        if sampleType not in sampleTypes:
            sampleTypes.append(sampleType)
        mapping[field] = dbField 
    
    if status==1:
        msg = 'okay'
    else:
        sampleTypes = []
        mapping = {}
        
    return msg, status, sampleTypes, mapping

def getSampleData(sampleType, sampleDic, mapping):
    sampledata = {}
    for field, value in sampleDic.iteritems():
        if field not in mapping:
            msg = "Warning: attribute " + field + " not found in mapping: "
            continue
        
        dbField = mapping[field]
        stype, attribute = dbField.split("::")
        if stype==sampleType:
            key = attribute.lower()
            sampledata[key] = value
    
    sampledata = json.dumps(sampledata)
    return sampledata

def runAuthSampleBatchSubmission(sampleDiclist, diclist_ins, token, userInfo, submitDfile=False):
    url = "/api/sampleupload/"
    msg, status, sampleTypes, mapping = getSampleTypes(diclist_ins)
    if status==0:
        return sampleDiclist
    
    sampleDiclistNew = []
    i = 0
    for dici in sampleDiclist:
        if i>0:
            continue
        
        i += 1
        for sampleType in sampleTypes:
            sampledata = getSampleData(sampleType, dici, mapping)
            resultdic = runAuthSampleSubmission(sampledata, sampleType, token, userInfo)
            uid = resultdic['UID']
            status = resultdic['status']
            msg = resultdic['msg']
            
            if status==1:
                minfo = uid
            else:
                minfo = msg
                
            key = sampleType + "::UID"
            dici[key] = minfo
            for field, dbField in mapping.iteritems():
                if dbField==key:
                    dici[field] = minfo
                
        sampleDiclistNew.append(dici)
    
    return sampleDiclistNew


def runAuthFileSubmission(sampledata, sampleType, token, userInfo):
    url = "/api/sampleupload/"
    sdata = json.loads(sampledata)
    
    uid = None
    if 'UID' in sdata:
        uid = sdata['UID']
    elif 'uid' in sdata:
        uid = sdata['uid']
        
    if uid is not None:
        if len(uid.strip())>0:
            print("Update operation")
            jsondic = sampledata
            resultdic = runAuthPostFile(url, jsondic, token)
            return
        
    data = {}
    data['User'] = userInfo
    data['Samples'] = sdata
    data['Sample type'] = sampleType
    jsondic = json.dumps(data)
    resultdic = runAuthPost(url, jsondic, token)
    
    return resultdic
 
def runAuthPostFile(url, fullfilename, token, server=None):
    serverIn = SERVER
    if server is not None:
        serverIn = server
    
    prefix = "curl -i -X POST " + serverIn
    suffix = " -H 'Authorization: Token " + token + "'"
    suffix += " -F 'file=@"
    suffix += fullfilename + "'"
    apicmd = prefix + url + suffix
    print(apicmd)
        
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    
    resultdDic = json.loads(resultset[-1])
    print(resultdDic)
    
    status = resultdDic['status']
    msg = resultdDic['msg']
    if status:
        print("Sample submission successful")
    else:
        print("Sample submission with error: " + msg)
    
    return resultdDic 
        
def main():
    parser = argparse.ArgumentParser(description="Submit a data file through API call to the Seek system",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-s', '--server', 
                        help='Optional, choose which server to use for the API call. ',
                        default=SERVER)
    
    parser.add_argument('-u', '--username', 
                        help='The valid user name for running the API call. ',
                        default=None)
    
    parser.add_argument('-p', '--pwd', 
                        help='The valid password for running the API call. ',
                        default=None)
    parser.add_argument('datafile', help="Sample meta data in a json dictionary")
    args = parser.parse_args()
    server = args.server
    username = args.username
    pwd = args.pwd
    
    datafile = args.datafile
    token = getAuthToken(username, pwd, server)
    url = "/api/datafileupload/"
    runAuthPostFile(url, datafile, token)
    return


if __name__ == "__main__":
    main()
