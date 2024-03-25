#!/usr/bin/env python
import subprocess
import json
from subprocess import call
import argparse
import hashlib, os

def verifyPrideFileDownload(filename):
    PRIDE_API_URL = "curl -X GET --header 'Accept: application/json' 'https://www.ebi.ac.uk/pride/ws/archive/v2/files/fileByName?fileName="
    curl_cmd = PRIDE_API_URL + filename + "'"
    print(curl_cmd)
    resultset = subprocess.Popen([curl_cmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    
    resultset = list(resultset)
    resultStr = resultset[0]
    if len(resultStr.strip())==0:
        msg = 'Error: No info found for the file: %s'%filename
        print(msg)
        return msg, 0
    
    dic0 = json.loads(resultset[0])
    if "checksum" not in dic0:
        msg = 'Error: Not found for the file: %s'%filename
        print(msg)
        return msg, 0
    
    sha10 = dic0["checksum"]
    filesize0 = dic0["fileSizeBytes"]
    filelinks = dic0["publicFileLocations"]
    ftplink = ""
    for link in filelinks:
        name = link["name"]
        if name=="FTP Protocol":
            ftplink = link["value"]
            
    print('File sha1 checksum: %s'%sha10)
    
    if len(ftplink)==0:
        msg = 'Error: No download link found for the file: %s'%filename
        print(msg)
        return msg, 0
    
    print(' File remote url: %s'%ftplink)
    curl_cmd = "curl -O " + ftplink
    print(curl_cmd)
    resultset = subprocess.Popen([curl_cmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    
    print("File downloaded: %s"%filename)
    
    if not os.path.isfile(filename):
        msg = 'Error: No downloaded file found in the current folder: %s'%filename
        print(msg)
        return msg, 0
 
    if not os.path.exists(filename):
        msg = 'Error: No downloaded file found in the current folder: %s'%filename
        print(msg)
        return msg, 0
    
    filesize = os.path.getsize(filename)
    if filesize!=filesize0:
        msg = 'Error: File size %s, not match from DB: %s'%(filesize,filesize0)
        print(msg)
        return msg, 0
    print('Correct file size: %s'%filesize)
    
    fi = open(filename,'rb').read()
    sha1Hash = hashlib.sha1(fi)
    sha1 = sha1Hash.hexdigest()
    if sha1!=sha10:
        msg = 'Error: File sha1 checksum %s, not match from DB: %s'%(sha1,sha10)
        print(msg)
        return msg, 0
    print('Correct sha1 checksum: %s'%sha1)
    print('File downloaded successfully: %s'%filename)
    return 'okay', 1
        
def main():
    parser = argparse.ArgumentParser(description="Download and uverify file from Pride database.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument('filename', help='A valid file name from Pride database.')
    args = parser.parse_args()
    filename = args.filename
    verifyPrideFileDownload(filename)

if __name__ == "__main__":
    main()
