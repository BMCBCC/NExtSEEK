from datetime import date
from dateutil.parser import parse
import datetime
from unidecode import unidecode

from math import log
import hashlib
import os
import argparse

def __timeconversion(timein):
    strs = timein.split(':')
    if len(strs)==3:
        timeout = strs[0] + ':' + strs[1] + ":00"   #ignore second
    else:
        timeout = timein
    return timeout

def convertDate_1(startDate, startTime):
    dateappointed = startDate + " " + startTime
    try:
        dateconverted = parse(dateappointed) 
    except ValueError:
        msg = "Error: Incorrect date format not in MM/DD/YYYY: '" + dateappointed + "'"
        dateconverted = dateappointed

    return dateconverted

def __convertDateFormat(fieldValue):
    DATE_FORMAT = "%Y-%m-%d" 
    TIME_FORMAT = "%H:%M:%S"

    if isinstance(fieldValue, datetime.date):
        fieldValueOut = fieldValue.strftime(DATE_FORMAT)
    elif isinstance(fieldValue, datetime.time):
        fieldValueOut = fieldValue.strftime(TIME_FORMAT)
    elif isinstance(fieldValue, datetime.datetime):
        fieldValueOut = fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
    else:
        fieldValueOut = fieldValue
            
    return fieldValueOut

def toInt(valueIn):
    if valueIn is None:
        valueOut = 0
    else:
        try:
            valueOut = int(valueIn)
        except:
            valueOut = 0
    return valueOut

def toString(itemIn):
    return toStringPython2(itemIn)
    
    if itemIn is None:
        itemOut = ' '
    else:
        if type(itemIn) == str:
            itemOut = str(itemIn)
        else:
            try:
                itemOut = str(itemIn)
            except:
                itemOut = unidecode(itemIn)
    return itemOut.strip()


def toStringPython2(itemIn):
    if itemIn is None:
        itemOut = ' '
        return itemOut
    
    try:
        itemOut = str(itemIn)
    except:
        strtype = type(itemIn)
        if strtype == unicode:          
            itemOut = itemIn.encode("utf-8")
            itemOut = str(itemOut)
        else:
            itemOut = unidecode(itemIn)
            
    return itemOut.strip()
    
def toStringPython3(itemIn):
    if itemIn is None:
        itemOut = ' '
        return itemOut
        
    try:
        itemOut = str(itemIn)
    except:
        itemOut = unidecode(itemIn)
    return itemOut.strip()

def toBinary(valueIn):
    if valueIn is None:
        valueOut = False
    elif valueIn==0:
        valueOut = False
    elif valueIn==1:
        valueOut = True
    else:
        valueOut = False
    
    return valueOut

def toBinaryTinyInt(valueIn):
    valueOut = 0
    if valueIn is None:
        return valueOut 
    
    try:
        valueOut = int(valueIn)
        if valueOut!=1:
            valueOut = 0
            
    except ValueError:
        try:
            sss = str(valueIn)
            sss = sss.lower().strip()
            if sss=='true':
                valueOut = 1
            elif sss=='yes':
                valueOut = 1
            else:
                valueOut = 0
        except ValueError:
            valueOut = 0
    
    return valueOut

def toFloat(valueIn):
    if valueIn is None:
        valueOut = 0.0
    else:
        try:
            valueOut = float(valueIn)
        except ValueError:
            valueOut = 0.0
    
    return valueOut

def formatPercent(valueIn, zerostring=' '):
    if valueIn is None:
        valueOut = zerostring
    elif valueIn==0:
        valueOut = zerostring
    else:
        value = "%.0f" % valueIn
        valueOut = str(value)
    return valueOut

def formatStringMSSQL(strin):
    if strin is None:
        strout = strin
    else:
        strin = strin.strip()
        if "'" in strin:
            str1 = strin.replace("'", "''")
        else:
            str1 = strin
        
        if '"' in str1:
            strout = str1.replace('"', "''")
        else:
            strout = str1
    return strout

def intToStr(valueIn):
    if valueIn is None:
        valueOut = ' '
    elif valueIn==0:
        valueOut = ' '
    else:
        valueOut = str(valueIn)
    return valueOut
    

def format_currency(valueIn, nonestring='$0'):
    if valueIn is None:
        value = nonestring   
    elif valueIn < 0:
        try:
            results = '${:,.0f}'.format(valueIn)
            value = "(" + results.replace("-","") + ")"
        except ValueError:
            value = str(valueIn)
        
    elif valueIn > 0:
        results = '${:,.0f}'.format(valueIn)
        value = str(results)
    else:
        value = nonestring
    return value

def toCurrency(valueIn, nonestring='$0'):
    if valueIn is None:
        valueOut = nonestring
    elif not is_numeric(valueIn):
        valueOut = nonestring
    elif valueIn==0:
        valueOut = nonestring
    else:
        valueOut = format_currency(toFloat(valueIn))
    return valueOut


def fromCurrency(valueIn):
    if valueIn is None:
        valueOut = 0
        return valueOut
    
    sss = str(valueIn)
    if sss[0]=='$':     
        sss = sss[1:]  
    
    if ',' in sss:     
        sss=sss.replace(',', '')   

    try:
        valueOut = float(sss)
    except ValueError:
        valueOut = 0
    return valueOut

def toDate(dateIn):
    if dateIn is None:
        dateOut = ' '
    else:
        dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
        dateOut = '{0}/{1}/{2:02}'.format(dt.month, dt.day, dt.year % 100)
    return dateOut
    
def toUSDate(dateIn):
    if dateIn is None:
        dateOut = ' '
    else:
        dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
        dateOut = '{0:02}/{1:02}/{2:04}'.format(dt.month, dt.day, dt.year)
    return dateOut
    
def toDateClass(datetimein):
    if datetimein is None:
        return None
    
    if isinstance(datetimein, datetime.date):
        return datetimein
    elif isinstance(datetimein, datetime.time):
        return None
    elif isinstance(datetimein, datetime.datetime):
        return datetimein
    
    strs1 = datetimein.split(' ')
    if len(strs1)>1:
        strs2 = strs1[0]
        if len(strs1[1])>0:
            return None
    else:
        strs2 = datetimein
        
    if '/' in strs2:
        strs3 = strs2.split('/')
        if len(strs3)==3:
            yearStr = strs3[2]
            if len(yearStr)!=4:
                return None
            
            try:
                dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            except:
                dateout = None
        else:
            dateout = None
    elif '-' in strs2:
        strs3 = strs2.split('-')
        if len(strs3)==3:
            try:
                dateout = date(int(strs3[0]), int(strs3[1]), int(strs3[2]))
            except:
                dateout = None
        else:
            dateout = None
    else:
        dateout = None
        
    return dateout
    
def dateconversion(datetimein):
    if datetimein is None:
        return " "
    
    strs1 = datetimein.split(' ')
    if len(strs1)>1:
        strs2 = strs1[0]
        strs3 = strs2.split('/')
        if len(strs3)==3:
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = strs2

        timein = strs1[1] 
        timeout = __timeconversion(timein)
        datetimeout = str(dateout) + 'T' + timeout
    else:
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = datetimein

    datetimeout = str(dateout)
    return datetimeout    
    
def toISODate(datetimein):
    if datetimein is None:
        return None
    
    if isinstance(datetimein, datetime.date):
        try:
            dateout = datetimein.date()
        except:
            dateout = datetimein
        return dateout
    str0 = str(datetimein)
    strs1 = str0.split(' ')
    if len(strs1)>1:
        strs2 = strs1[0] # '8/16/2012'
        strs3 = strs2.split('/')
        if len(strs3)==3:
            try:
                dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            except:
                dateout = None
        else:
            dateout = strs2
    else:
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            try:
                dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            except:
                dateout = None
        else:
            dateout = datetimein

    if dateout is None:
        datetimeout = None
    else:
        datetimeout = str(dateout) 
    return datetimeout    
    
def monthconversion(datetimein):
    strs1 = datetimein.split(' ')
    if len(strs1)>1:
        strs2 = strs1[0] 
        strs3 = strs2.split('/')
        if len(strs3)==3:
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = strs2

        timein = strs1[1] 
        timeout = __timeconversion(timein)
        datetimeout = str(dateout) + 'T' + timeout
    else:
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            dateout = strs3[0] + '/' + strs3[2]
        else:
            dateout = datetimein

    datetimeout = str(dateout) 
    return datetimeout 
    
def dateToString(dateIn):
    if dateIn is None:
        dateOut = ' '
    else:
        if isinstance(dateIn, datetime.date):
            dateOut = '{0}/{1}/{2:02}'.format(dateIn.month, dateIn.day, dateIn.year % 100)
        elif isinstance(dateIn, datetime.datetime):
            dateOut = '{0}/{1}/{2:02}'.format(dateIn.month, dateIn.day, dateIn.year % 100)
        else:
            dateOut = str(dateIn)
    return dateOut

def dateToISOstring(dateIn):
    if dateIn is None:
        dateOut = ' '
    else:
        if isinstance(dateIn, datetime.date):
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
        elif isinstance(dateIn, datetime.datetime):
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
        else:
            dateOut = str(dateIn)
    return dateOut

def convertDateListToString(fieldName, objsdiclist):
    newlist = []
    for objdic in objsdiclist:
        fieldValue = objdic[fieldName]
        objdic[fieldName] = dateToString(fieldValue)
        newlist.append(objdic)
        
    return newlist

def checkSingleQuote(stringIn):
    strtemp = stringIn
    if "''" in stringIn:
        strtemp = stringIn.replace("''", "__")
    
    if "'" in strtemp:
        strtemp = strtemp.replace("'", "''")
        
    if "__" in strtemp:
        strtemp = strtemp.replace("__", "''")
        
    return strtemp
    
def is_numeric(s):
    if s is None:
        return False
    
    try:
        i = float(s)
    except ValueError:
        return False
    return True
    
def getYearFromDate(dateIn):
    year = 0
    if "/" in dateIn:
        terms = dateIn.split("/")
        if len(terms)==3:
            year = int(terms[2])
        else:
            year = 0
    elif "-" in dateIn:
        terms = dateIn.split("-")
        if len(terms)==3:
            year = int(terms[0])
        else:
            year = 0
    return year
    
def toStringDB(itemIn):
    if itemIn is None:
        itemOut = ' '
    else:
        if type(itemIn) == str:
            itemOut = str(itemIn)
        else:
            try:
                itemOut = str(itemIn)
            except:
                itemOut = unidecode(itemIn)
    
    if '\x19' in itemOut:
        itemOut = itemOut.replace('\x19', '')
    return itemOut.strip()
        
def cleanStringDB(itemIn):
    if type(itemIn)==unicode:
        itemOut = itemIn.encode("utf-8")
        return itemOut
        
    newitem = unicode(itemIn, "utf-8", errors="ignore")
    itemOut = unidecode(newitem)
    return itemOut

def verifyUSDate(usdateIn):
    try:
        datetime.datetime.strptime(usdateIn, '%m/%d/%Y')
        return True
    except ValueError:
        return False
    return False
    
def convertBoolstrToInt(valueIn):
    if valueIn is None:
        value = -1
        return value
            
    valueStr = str(valueIn)
    valueStr = valueStr.upper()
    if valueStr=="YES":
        value = 1
    elif valueStr=="NO":
        value = 0
    elif valueStr=="1":
        value = 1
    elif valueStr=="0":
        value = 0
    else:
        value = -1
            
    return value

def convertBoolstrToBool(valueIn):
    if valueIn is None:
        value = False
        return value
            
    valueStr = str(valueIn)
    valueStr = valueStr.upper()
    if valueStr=="YES":
        value = True
    elif valueStr=="NO":
        value = False
    elif valueStr=="1":
        value = True
    elif valueStr=="0":
        value = False
    elif valueStr=="TRUE":
        value = True
    elif valueStr=="False":
        value = False
    else:
        value = False
            
    return value
    
def convertInttoBoolstr(valueIn):
    if valueIn is None:
        value = 'N/A'
        value = '?'
    elif valueIn==1:
        value = "Yes"
    elif valueIn==0:
        value = "No"
    else:
        value = 'N/A'
        value = '?'
            
    return value

def percentToFloat(percentIn):
    if percentIn is None:
        return 0.00
    
    valuein = str(percentIn)
    valuein= valuein.strip()
    if "%" in valuein:
        valuein = valuein.replace('%','')
    
    pct = toFloat(valuein)
    return pct
    
def percentValidate(pct, pctmin, pctmax):
    msg = "okay"
    status = 1
    if pct is None:
        msg = "Percent not valid: None"
        status = 0
        return msg, status
        
    try:
        pctstr = str(pct)
        if "%" in pctstr:
            pctstr = pctstr.replace('%','')
                
        fpct = float(pctstr)
        if fpct<pctmin or fpct>pctmax:
            msg = "Percent not valid: " + str(pct)
            status = 0
        else:
            value = percentToFloat(fpct)
            msg = "Percent converted: " + str(value) + ' from ' + str(pct)
            
    except:
        msg = "Percent not valid: " + pct
        status = 0
        
    return msg, status
    
def stringValidate(strIn, validStrings):
    status = 1
    msg = 'ok'
    if strIn is None:
        msg = "String is invalid None. "
        status = 0
        return msg, status
        
    try:
        strok = str(strIn)
        strok = strok.strip()
        if strok not in validStrings:
            msg = "String not on the list: " + strok
            status = 0
        else:
            msg = "String is valid: " + strok
            #status = 0
    except:
        msg = "String not valid: " + strIn
        status = 0
        
    return msg, status
    
    
def retrieveSubset(listdics, headers):
    newlistdics = []
    for row in listdics:
        newrow = dict((k, row[k]) for k in headers if k in row)
        newlistdics.append(newrow)
    return newlistdics     
    
def convertInttoBoolstr(valueIn):
    if value is None:
        value = 'N/A'
        value = '?'
    elif value==1:
        value = "Yes"
    elif value==0:
        value = "No"
    else:
        value = 'N/A'
        value = '?'
            
    return value    
    
def convertBoolstrToInt(valueIn):
    if valueIn is None:
        value = -1
        return value
            
    valueStr = str(valueIn)
    valueStr = valueStr.upper()
    if valueStr=="YES":
        value = 1
    elif valueStr=="NO":
        value = 0
    elif valueStr=="1":
        value = 1
    elif valueStr=="0":
        value = 0
    else:
        value = -1
            
    return value

def floatToStr(valueIn):
    if valueIn is None:
        valueOut = str(NONE_VALUE)
    elif valueIn==0:
        valueOut = '0'
    else:
        valueOut = str(valueIn)
    return valueOut

def toUSAZipcode(valueIn):
    if valueIn is None:
        valueOut = ''
    elif len(str(valueIn))==0:
        valueOut = ''
    else:
        valueOut = str(valueIn).zfill(5)
    return valueOut

def dateToStringUK(dateIn):
    if dateIn is None:
        dateOut = None
    elif len(str(dateIn))==0:
        dateOut = None
    elif len(str(dateIn))<4:
        dateOut = None
    elif len(str(dateIn))==4:
        try:
            dt = parse(str(dateIn))
            dateOut = '{0:04}-{1}-{2}'.format(dt.year, 12, 31)
        except ValueError:
            msg = 'Not right date format: ', dateIn
            dateOut = None
    else:
        if isinstance(dateIn, datetime.date):
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
        elif isinstance(dateIn, datetime.datetime):
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
        else:
            dateOut = validateDate(dateIn)
    return dateOut

def absFloats(float1, float2):
    diff = 0.0
    if float1 is None and float2 is None:
        diff = 0.0
    elif float1 is None:
        if float2==NONE_VALUE:
            diff = 0.0
        else:
            diff = abs(float2)
    elif float2 is None:
        if float1==NONE_VALUE:
            diff = 0.0
        else:
            diff = abs(float1)
    else:
        if float1==NONE_VALUE and float2==NONE_VALUE:
            diff = 0.0
        elif float1==NONE_VALUE:
            diff = abs(float2)
        elif float2==NONE_VALUE:
            diff = abs(float1)
        else:
            diff = abs(float1 - float2)
    
    return diff
    
    
def validateDate(dateIn):
    try:
        dt = parse(dateIn)
        dateOut = '{0:04}-{1}-{2}'.format(dt.year, dt.month, dt.day)
    except ValueError:
        msg = 'Not right date format: ', dateIn
        dateOut = None
        
    return dateOut
    
def toBooleanValue(formdata, fieldname):
    value_new = False
    if fieldname in formdata:
        value = formdata[fieldname]
        if value is not None:
            value = str(value)
            value = value.upper().strip()
            if value=="1" or value=="Y" or value=="YES" or value=="TRUE" or value=="T":
                value_new = True
            
    formdata[fieldname] = value_new
    return formdata

def getDefaultDate():
    datenow = datetime.datetime.now().strftime("%Y-%m-%d")
    return datenow

def getDefaultDate():
    datenow = datetime.datetime.now().strftime("%Y-%m-%d")
    return datenow

def getDefaultDateTime():
    datenow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return datenow

def cleanString(itemIn):
    return cleanStringDB(itemIn)
    
def convertSQLString(value):
    if isinstance(value, datetime.date):
        strValue = "'" + str(value) + "'"
    elif is_numeric(value):
        strValue = str(value)
    else:
        if value is None:
            strValue = "''"
        elif "'" in value:
            strValue = value.replace("'", "''")
            strValue = "'" + strValue + "'"
        elif '"' in value:
            strValue = value.replace('"', "''")
            strValue = "'" + strValue + "'"
        else:
            strValue = "'" + value + "'"
            
    return strValue

def handle_uploaded_file(infile, outfilename):
    dest = open(outfilename, 'wb')
    for chunk in infile.chunks():
        dest.write(chunk)
    dest.close()
    
def correctFileName(infilename):
    if infilename is None:
        return None
        
    outfilename = infilename.strip()
    if ' ' in outfilename:
        outfilename = outfilename.replace(' ', '-')
            
    return outfilename
        
def convertDicToOptions(dicIn):
    options = []
    
    si = {"selected": 'true', "id": 0, "title": ""}
    options.append(si)
    for k,v in dicIn.items():
        si = {}
        si["id"] = k
        si["title"] = v
        options.append(si)
    return options
    
    
def sizeof_fmt(num):
    if num is None:
        return ''
    
    num = toInt(num)
    unit_list = list(zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2]))
    if num > 1:
        exponent = min(int(log(num, 1024)), len(unit_list) - 1)
        quotient = float(num) / 1024**exponent
        unit, num_decimals = unit_list[exponent]
        format_string = '{:.%sf} {}' % (num_decimals)
        return format_string.format(quotient, unit)
    if num == 0:
        return '0 bytes'
    if num == 1:
        return '1 byte'
    
    
def getFileChecksum(fullfilename, checksumFormat='MD5'):
    cf = checksumFormat.upper()
    if cf=='MD5':
        fi = open(fullfilename,'rb').read()
        md5 = hashlib.md5(fi).hexdigest()
        checksum = md5
    elif cf=='SHA1':
        openedFile = open(fullfilename,'rb')
        readFile = openedFile.read()
        sha1Hash = hashlib.sha1(readFile)
        sha1Hashed = sha1Hash.hexdigest()
        checksum = sha1Hashed
    else:
        checksum = 'NA'
    return checksum
    
    
def verifyFileChecksum(fullfilename):
    fi = open(fullfilename,'rb').read()
    md5 = hashlib.md5(fi).hexdigest()
    
    sha1Hash = hashlib.sha1(fi)
    sha1 = sha1Hash.hexdigest()
    
    filesize = os.path.getsize(fullfilename)
    return md5, sha1, filesize
    
    
    
def verifyValueType(valuetype, value):
    if valuetype is None:
        return False
    
    valuetypeStr = toString(valuetype)
    valuetypeStr = valuetypeStr.strip().upper()
    
    if valuetypeStr=='DATE':
        dateValue = toDateClass(value)
        if dateValue is None:
            return False
        else:
            return True
    elif valuetypeStr=='TEXT':
        valueStr = toString(value)
        return True
    elif valuetypeStr=='NUMBER' or valuetypeStr=='FLOAT':
        return is_numeric(value)
        
    return True
    
    
def main():
    parser = argparse.ArgumentParser(description="Submit a data file through API call to the Seek system",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('inputFilename', help='Input file')
    args = parser.parse_args()
    inputfile = args.inputFilename
    getFileChecksum(inputfile, 'MD5')
    getFileChecksum(inputfile, 'SHA1')
    return

if __name__ == "__main__":
    main()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
