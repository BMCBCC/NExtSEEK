
import hashlib
import os
import argparse
import subprocess
import json

def getFileChecksum(fullfilename, checksumFormat='MD5'):
    cf = checksumFormat.upper()
    if cf=='MD5':
        fi = open(fullfilename,'rb').read()
        print('open file: %s'%fullfilename)
        print('Calculate MD5 checksum...')
        md5 = hashlib.md5(fi).hexdigest()
        checksum = md5
        print('MD5 checksum: %s'%md5)
    elif cf=='SHA1':
        openedFile = open(fullfilename,'rb')
        readFile = openedFile.read()
        sha1Hash = hashlib.sha1(readFile)
        sha1Hashed = sha1Hash.hexdigest()
        checksum = sha1Hashed
        print('SHA1 checksum: %s'%checksum)
    else:
        checksum = 'NA'
    return checksum

def dwonloadDF(url, filename):
    import urllib2
    req = urllib2.Request(url)
    res = urllib2.urlopen(req)
    with open(filename,'wb') as output:
        output.write(res.read())

def runCurlQuery(url):
    prefix = "curl -s -X GET "
    suffix = " -H 'accept: application/json'"
    apicmd = prefix + url + suffix
    resultset = subprocess.Popen([apicmd], stdout=subprocess.PIPE, shell=True
        ).communicate()[0].decode().split("\n")
    
    resultdDic = json.loads(resultset[1])
    return resultdDic


def getFileChecksumSRA(sraID):
    url_prefix = "https://www.ebi.ac.uk/ena/portal/api/filereport?accession="
    url_suffix = "&result=read_run&fields=study_accession,sample_accession,experiment_accession,run_accession,tax_id,scientific_name,fastq_md5,fastq_ftp,submitted_ftp,sra_md5,sra_ftp&format="
    rformat = "json&download=true&limit=0"
    url = "'" + url_prefix + str(sraID) + url_suffix + rformat + "'"
    resultdDic = runCurlQuery(url)
    md5checksum = resultdDic["fastq_md5"]
    print("MD5 checksum: %s"%md5checksum)
    return md5checksum

def run_command(args, wait=False):
    try:
        if (wait):
            p = subprocess.Popen(
                args,
                stdout = subprocess.PIPE)
            p.wait()
        else:
            p = subprocess.Popen(
                args,
                stdin = None, stdout = None, stderr = None, close_fds = True)

        (result, error) = p.communicate()
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            "common::run_command() : [ERROR]: output = %s, error code = %s\n"
            % (e.output, e.returncode))

    return result

def dwonloadDF2(url):
    cmd = ["wget", url]
    result = run_command(cmd, True)
    print(result)
    
def calChecksumFiles(inputfile):
    outfile = inputfile.replace(".txt", "-result.txt")
    
    fi = open(inputfile, "r")
    fo = open(outfile, "w")
    for x in fi:
        terms = x.split("\t")
        url = terms[0]
        if "https://sra-pub-run-odp.s3.amazonaws.com/sra/" in url:
            ids = url.split("/")
            sraid = ids[-1]
            sraid = sraid.strip()
            md5 = getFileChecksumSRA(sraid)
        elif "https://www.ncbi.nlm.nih.gov/geo/download/" in url:
            filename = 'temp'
            print("Downloading file as %s..."%filename)
            dwonloadDF(url, filename)
            md5 = getFileChecksum(filename, 'MD5')
            cmd = ["rm", filename]
            result = run_command(cmd, True)
        else:
            md5 = ''
        
        line = url + "\t" + str(md5) + "\n"
        fo.write(line)
    
    fi.close()
    fo.close()

def main():
    parser = argparse.ArgumentParser(description="Submit a data file through API call to the Seek system",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('inputFilename', help='Input file')
    
    parser.add_argument('-t', '--inputType', help='the type of inputFilename: single, list, sra.', default='single')
    args = parser.parse_args()
    inputfile = args.inputFilename
    inputType = args.inputType
    if inputType=='sra':
        sraID = inputfile
        getFileChecksumSRA(sraID)
    elif inputType=='list':
        calChecksumFiles(inputfile)
    else:
        if os.path.exists(inputfile):
            getFileChecksum(inputfile, 'MD5')
            getFileChecksum(inputfile, 'SHA1')
        else:
            print("Input file not found: %s"%inputfile)
    return

if __name__ == "__main__":
    main()
    
    
    
    