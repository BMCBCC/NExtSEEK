from datetime import date
from dateutil.parser import parse
import datetime
from unidecode import unidecode

from math import log
import hashlib


def __timeconversion(timein):
    ''' such as 12:30:56 '''
    strs = timein.split(':')
    if len(strs)==3:
        timeout = strs[0] + ':' + strs[1] + ":00"   #ignore second
    else:
        timeout = timein
    return timeout

def convertDate_1(startDate, startTime):
    '''
        StartDate   StartTime     
        1/11/2016   10:00:00 AM
        
        Usage
            used in samples.py
    '''
    dateappointed = startDate + " " + startTime
    try:
        #print "dateappointed: ", dateappointed
        dateconverted = parse(dateappointed)
        #print "date converted: ", dateconverted  
    except ValueError:
        #raise ValueError("Incorrect data format, should be YYYY-MM-DD")
        msg = "Error: Incorrect date format not in MM/DD/YYYY: '" + dateappointed + "'"
        #print msg
        dateconverted = dateappointed

    return dateconverted

def __convertDateFormat(fieldValue):
    #print  "fieldValue: ", fieldValue
    DATE_FORMAT = "%Y-%m-%d" 
    TIME_FORMAT = "%H:%M:%S"

    if isinstance(fieldValue, datetime.date):
        fieldValueOut = fieldValue.strftime(DATE_FORMAT)
    elif isinstance(fieldValue, datetime.time):
        fieldValueOut = fieldValue.strftime(TIME_FORMAT)
    elif isinstance(fieldValue, datetime.datetime):
        fieldValueOut = fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
    else:
        #print "No change in date format"
        fieldValueOut = fieldValue
            
    #print "fieldValueOut: ", fieldValueOut
    #fieldValueOut = parse(fieldValueOut)
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
        #http://stackoverflow.com/questions/3224268/python-unicode-encode-error
        if type(itemIn) == str:
            # Ignore errors even if the string is not proper UTF-8 or has
            # broken marker bytes.
            # Python built-in function unicode() can do this.
            #itemOut = unicode(itemIn, "utf-8", errors="ignore")
            itemOut = str(itemIn)
        else:
            # Assume the value object has proper __unicode__() method
            #itemOut = unicode(itemIn)
            try:
                itemOut = str(itemIn)
            except:
                #itemOut = itemIn.encode('ascii', 'ignore')
                itemOut = unidecode(itemIn)
    return itemOut.strip()


def toStringPython2(itemIn):
    ''' Convert input into a string, tested in python2.7.17. 
    '''
    if itemIn is None:
        itemOut = ' '
        return itemOut
    
    # Assume the value object has proper __unicode__() method
    #itemOut = unicode(itemIn)
    try:
        itemOut = str(itemIn)
    except:
        #http://stackoverflow.com/questions/3224268/python-unicode-encode-error
        strtype = type(itemIn)
        if strtype == unicode:          #only works in python2.7
            # convert unicode to utf-8
            itemOut = itemIn.encode("utf-8")
            # convert utf-8 back to string
            itemOut = str(itemOut)
        else:
            #itemOut = itemIn.encode('ascii', 'ignore')
            itemOut = unidecode(itemIn)
            
    return itemOut.strip()
    
def toStringPython3(itemIn):
    ''' Convert input into a string, tested in python3.6.9
    '''
    if itemIn is None:
        itemOut = ' '
        return itemOut
        
    try:
        # works for string, unicode and utf-8
        itemOut = str(itemIn)
    except:
        #itemOut = itemIn.encode('ascii', 'ignore')
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
        # not numeric
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
            # not numeric
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
    ''' Used to format string os it can be stored properly into MSSQL database.
    The problem happens when there is ' or " in a string, which should be converted to
    '' instead, i.e., double '.
    '''
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
    ''' Convert currency value to string,
    Input
        valueIn, the currency in float value
        nonestring, string used for 0 or none value
    Output
        currency in string
    '''
    ''' example
            >>> x = 3274523847523874
            >>> y = '${:,.2f}'.format(x)
            >>> y
                '$3,274,523,847,523,874.00'
            >>> y = '${:,.0f}'.format(x)
            >>> y
                '$3,274,523,847,523,874'
    '''
    #print "value:", valueIn
    if valueIn is None:
        value = nonestring   
    elif valueIn < 0:
        #up to cent
        #results = '${:,.2f}'.format(value)
        # up to dollar
        #results = '${:,}'.format(value)
        try:
            #results = '${:,.2f}'.format(valueIn)
            results = '${:,.0f}'.format(valueIn)
            value = "(" + results.replace("-","") + ")"
        except ValueError:
            #print valueIn
            value = str(valueIn)
        
    elif valueIn > 0:
        #up to cent
        #value =  '${:,.1f}'.format(value)
        #up to dollar
        #value =  '${:,}'.format(value)
        #value =  '{}'.format(value)
        #results = '${:,}'.format(valueIn)
        results = '${:,.0f}'.format(valueIn)
        value = str(results)
    else:
        value = nonestring
    #print valueIn, value
    return value

def toCurrency(valueIn, nonestring='$0'):
    ''' Convert currency value to string,
    Input
        valueIn, the currency in float value
        nonestring, string used for 0 or none value
    Output
        currency in string
    '''
    if valueIn is None:
        valueOut = nonestring
    elif not is_numeric(valueIn):
        valueOut = nonestring
    elif valueIn==0:
        valueOut = nonestring
    else:
        #valueOut = format_currency(toInt(valueIn))
        valueOut = format_currency(toFloat(valueIn))
    return valueOut


def fromCurrency(valueIn):
    ''' The input value could be either a float number or a money amount in the format of "$12345"
    '''
    if valueIn is None:
        valueOut = 0
        return valueOut
    
    sss = str(valueIn)
    if sss[0]=='$':     # such as sss = '$123,456.00'
        sss = sss[1:]   # such as sss = '123,456.00'
    
    if ',' in sss:      # such as sss = '123,456.00'
        sss=sss.replace(',', '')    # such as sss = '123456.00'

    try:
        valueOut = float(sss)
    except ValueError:
        # not numeric
        valueOut = 0
    return valueOut

def toDate(dateIn):
    '''
        dateIn = "2013-1-25"
        
        fateOut = "1/25/2013"
    '''
    if dateIn is None:
        dateOut = ' '
    else:
        dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
        #dateOut = '{0}/{1}/{2:04}'.format(dt.month, dt.day, dt.year % 100)
        dateOut = '{0}/{1}/{2:02}'.format(dt.month, dt.day, dt.year % 100)
    return dateOut
    
def toUSDate(dateIn):
    '''
        dateIn = "2013-1-25"
        
        fateOut = "01/25/2013"
    '''
    if dateIn is None:
        dateOut = ' '
    else:
        dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
        dateOut = '{0:02}/{1:02}/{2:04}'.format(dt.month, dt.day, dt.year)
    return dateOut
    
def toDateClass(datetimein):
    '''
    Input
        datetimein, either "1/25/2013" or "2013-1-25", or "1/25/2013 hour:minute:second"
        
    Ouput
        date = datetime.date(year, month, day)
    '''
    print "toDateClass: ", datetimein
    
    if isinstance(datetimein, datetime.date):
        return datetimein
    elif isinstance(datetimein, datetime.time):
        return None
    elif isinstance(datetimein, datetime.datetime):
        return datetimein
    
    if datetimein is None:
        return None
    
    strs1 = datetimein.split(' ')
    #print strs1
    if len(strs1)>1:
        strs2 = strs1[0] # '8/16/2012'
    else:
        strs2 = datetimein
        
    if '/' in strs2:
        strs3 = strs2.split('/')
        if len(strs3)==3:
            # "1/25/2013"
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = None
    elif '-' in strs2:
        strs3 = strs2.split('-')
        if len(strs3)==3:
            # "2013-1-25"
            dateout = date(int(strs3[0]), int(strs3[1]), int(strs3[2]))
        else:
            dateout = None
    else:
        dateout = None
        
    print datetimein, dateout
    return dateout
    
def dateconversion(datetimein):
    '''
        dateIn = "1/25/2013"
        
        dateOut = "2013-1-25"
    '''
    #print "dateconversion: ", datetimein
    if datetimein is None:
        return " "
    
    strs1 = datetimein.split(' ')
    #print strs1
    if len(strs1)>1:
        strs2 = strs1[0] # '8/16/2012'
        strs3 = strs2.split('/')
        if len(strs3)==3:
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = strs2

        #print "dateout: ", dateout
        timein = strs1[1] # '12:30:56' 
        timeout = __timeconversion(timein)
        datetimeout = str(dateout) + 'T' + timeout
    else:
        # such as 8/14/2014
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            #dateout = strs3[2] + '-' + strs3[0] + '-' + strs3[1]
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = datetimein

    datetimeout = str(dateout)
        
    #print 'dateout ', datetimeout
    return datetimeout    
    
def toISODate(datetimein):
    '''
        dateIn = "1/25/2013"
        
        dateOut = "2013-1-25"
        
        datetimein = 4/91/20
        dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        ValueError: day is out of range for month

    '''
    if datetimein is None:
        return None
    
    #print "toISODate: date in: ", str(datetimein)
    if isinstance(datetimein, datetime.date):
        #print "toISODate: a date type", str(datetimein)
        try:
            dateout = datetimein.date()
        except:
            dateout = datetimein
        #print "datetime.date: ", dateout
        return dateout
    #else:
    #    print "toISODate: not  a date type", str(datetimein)
    
    str0 = str(datetimein)
    strs1 = str0.split(' ')
    #print strs1
    if len(strs1)>1:
        strs2 = strs1[0] # '8/16/2012'
        #print "strs2: ", strs2
        strs3 = strs2.split('/')
        if len(strs3)==3:
            try:
                dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            except:
                dateout = None
        else:
            dateout = strs2
    else:
        # such as 8/14/2014 or 2018-09-01
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            #dateout = strs3[2] + '-' + strs3[0] + '-' + strs3[1]
            try:
                dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            except:
                dateout = None
        else:
            dateout = datetimein

    #print dateout
    if dateout is None:
        # date out of range
        datetimeout = None
    else:
        datetimeout = str(dateout) 
    #print 'dateout ', datetimeout
    return datetimeout    
    
def monthconversion(datetimein):
    '''
        dateIn = "1/25/2013"
        
        fateOut = "2013-1-25"
    '''
    strs1 = datetimein.split(' ')
    if len(strs1)>1:
        strs2 = strs1[0] # '8/16/2012'
        strs3 = strs2.split('/')
        if len(strs3)==3:
            dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
        else:
            dateout = strs2

        timein = strs1[1] # '12:30:56' 
        timeout = __timeconversion(timein)
        datetimeout = str(dateout) + 'T' + timeout
    else:
        # such as 8/14/2014
        strs3 = datetimein.split('/')
        if len(strs3)==3:
            #dateout = strs3[2] + '-' + strs3[0] + '-' + strs3[1]
            #dateout = date(int(strs3[2]), int(strs3[0]), int(strs3[1]))
            dateout = strs3[0] + '/' + strs3[2]
        else:
            dateout = datetimein

    datetimeout = str(dateout) 
    print 'dateout ', datetimeout
    return datetimeout 
    
def dateToString(dateIn):
    '''
        dateIn = datetime.date(2017, 2, 28)
        
        fateOut = "1/25/2013"
    '''
    #print "dateToString"
    if dateIn is None:
        dateOut = ' '
    else:
        if isinstance(dateIn, datetime.date):
            # such as 2017-02-15
            #print "date format: ", dateIn
            #fieldValueOut = fieldValue.strftime(DATE_FORMAT)
            # to output 2/25/17, use
            dateOut = '{0}/{1}/{2:02}'.format(dateIn.month, dateIn.day, dateIn.year % 100)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        elif isinstance(dateIn, datetime.datetime):
            #print "datetime format: ", dateIn
            #fieldValueOut = fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
            # to output 2/25/17, use
            dateOut = '{0}/{1}/{2:02}'.format(dateIn.month, dateIn.day, dateIn.year % 100)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        else:
            #print "other format: ", dateIn
            #dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
            #dt = parse(dateIn)
            #print "dt: ", dt
            #dateOut = '{0}/{1}/{2:04}'.format(dt.month, dt.day, dt.year % 100)
            dateOut = str(dateIn)
    return dateOut

def dateToISOstring(dateIn):
    print "dateToISOstring: ", dateIn
    if dateIn is None:
        dateOut = ' '
    else:
        if isinstance(dateIn, datetime.date):
            print "A"
            # such as 2017-02-15
            #print "date format: ", dateIn
            #fieldValueOut = fieldValue.strftime(DATE_FORMAT)
            # to output 2/25/17, use
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        elif isinstance(dateIn, datetime.datetime):
            print "B"
            #print "datetime format: ", dateIn
            #fieldValueOut = fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
            # to output 2/25/17, use
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        else:
            print "C"
            #print "other format: ", dateIn
            #dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
            #dt = parse(dateIn)
            #print "dt: ", dt
            #dateOut = '{0}/{1}/{2:04}'.format(dt.month, dt.day, dt.year % 100)
            dateOut = str(dateIn)
    return dateOut

def convertDateListToString(fieldName, objsdiclist):
    ''' Convert Date format to string format in a list of dictionaries.
        Input
            fieldName, the name of a field in the dictionary;
            objsdiclist=[{}, {}, ...]
            
        Output
            The date format will be changed.
    '''
    print "convertDateListToString"
    newlist = []
    for objdic in objsdiclist:
        fieldValue = objdic[fieldName]
        #objdic[fieldName] = __convertDateFormat(fieldValue)
        objdic[fieldName] = dateToString(fieldValue)
        newlist.append(objdic)
        
    return newlist

def checkSingleQuote(stringIn):
    ''' this is to prevent the error that Incorrect syntax near 's' in MSSQL insert when
        a string contains single quote such as 'Brigham and Women's Hospital',
        which should be corrected to 'Brigham and Women''s Hospital' instead.
        Refer to https://stackoverflow.com/questions/775687/how-to-insert-text-with-single-quotation-sql-server-2005
    '''
    strtemp = stringIn
    if "''" in stringIn:
        strtemp = stringIn.replace("''", "__")
    
    # only change single quote to double single quote
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
        # not numeric
        return False
    # numeric
    return True
    
def getYearFromDate(dateIn):
    '''
    Input
        dateIn, such as 03/25/2003, a date.
    Output
        year, such as 2003, in integer.
    '''
    year = 0
    if "/" in dateIn:
        terms = dateIn.split("/")
        if len(terms)==3:
            year = int(terms[2])
        else:
            year = 0
    elif "-" in dateIn:
        # assume year-month-day format
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
        #http://stackoverflow.com/questions/3224268/python-unicode-encode-error
        if type(itemIn) == str:
            # Ignore errors even if the string is not proper UTF-8 or has
            # broken marker bytes.
            # Python built-in function unicode() can do this.
            #itemOut = unicode(itemIn, "utf-8", errors="ignore")
            itemOut = str(itemIn)
        else:
            # Assume the value object has proper __unicode__() method
            #itemOut = unicode(itemIn)
            try:
                itemOut = str(itemIn)
            except:
                #itemOut = itemIn.encode('ascii', 'ignore')
                itemOut = unidecode(itemIn)
    
    if '\x19' in itemOut:
        itemOut = itemOut.replace('\x19', '')
    return itemOut.strip()
        
def cleanStringDB(itemIn):
    ''' Generate a clean string from the one that may contain unicode characters.
    '''
    # convert to unicode first
    print("cleanStringDB:", itemIn)
    
    if type(itemIn)==unicode:
        # if the input string is already an unicode, unicode(itemIn) will throw an error
        # convert type "unicode" to type "str" 
        itemOut = itemIn.encode("utf-8")
        return itemOut
        
    newitem = unicode(itemIn, "utf-8", errors="ignore")
    # ignore unnicode characters now
    #itemOut = newitem.encode('ascii', 'ignore')
    itemOut = unidecode(newitem)
    return itemOut

def verifyUSDate(usdateIn):
    ''' Verify whether the usdateIn follows the format "month/day/year".
    
    '''
    try:
        datetime.datetime.strptime(usdateIn, '%m/%d/%Y')
        #print('The date {} is valid.'.format(usdateIn))
        return True
    except ValueError:
        #print('The date {} is invalid'.format(usdateIn))
        return False
    return False
    
def convertBoolstrToInt(valueIn):
    ''' Convert "yes", "no" or "unknown" type input string to int, which can be saved in DB table.
    Input
        valueIn, a string or an int, where
            a string could be either "yes", "no" or "unknown";
            a int value could be 1, 0 or -1.
    Output
        an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
                
    '''
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
    ''' Convert "yes", "no" or "unknown" type input string to int, which can be saved in DB table.
    Input
        valueIn, a string or an int, where
            a string could be either "yes", "no" or "unknown";
            a int value could be 1, 0 or -1.
    Output
        an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
                
    '''
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
    ''' Convert tiny int value into either "yes", "no" or "unknown" string, which can be shown on html page.
    Input
        an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
        
    Output
        valueIn, a string , either "Yes", "No" or "?" ("Unknown").    
    '''
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
    ''' Coonvert percent into float value
    Input
        percentIn, such as 100, 50, or 33%, 50% etc.
        
    Output
        100.00, 50.00, 33.00, 50.00
    '''
    if percentIn is None:
        return 0.00
    
    valuein = str(percentIn)
    valuein= valuein.strip()
    #if valuein[-1]=='%':
    #    valuein = valuein[:-1]
    if "%" in valuein:
        valuein = valuein.replace('%','')
    
    pct = toFloat(valuein)
    
    #notes: when the cell type in an excel file is "Percent",
    # a value such as "100%" in the cell will be read as the actual value of '1',
    # instead of '100%'. Therefore, we have too do the conversion here.
    #if pct<=1.0:
    #    pct = pct*100
    return pct
    
def percentValidate(pct, pctmin, pctmax):
    ''' Validate percent which should be in the range of 0 to 100, with or without "%".
    '''
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
            #status = 0
            
    except:
        msg = "Percent not valid: " + pct
        status = 0
        
    return msg, status
    
def stringValidate(strIn, validStrings):
    ''' Validate whether a str is among the list of valid strings.
    '''
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
    ''' Input
            listdics, = [{n1:v11, n2:v12, }, {n1:v21, n2:v22,...},...], a list of dictionaries usually from q DB query.
            hdears = [n1, n3, ni, nj, ...], a list of keys, which are subset of the keys used in the dictionary.
        Output
            listdics, = [{n1:v11, n2:v12, }, {n1:v21, n2:v22,...},...], a list of dictionaries usually from q DB query.
    '''
    newlistdics = []
    for row in listdics:
        newrow = dict((k, row[k]) for k in headers if k in row)
        newlistdics.append(newrow)
    return newlistdics     
    
def convertInttoBoolstr(valueIn):
    ''' Convert tiny int value into either "yes", "no" or "unknown" string, which can be shown on html page.
    Input
        an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
        
    Output
        valueIn, a string , either "Yes", "No" or "?" ("Unknown").    
    '''
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
    ''' Convert "yes", "no" or "unknown" type input string to int, which can be saved in DB table.
    Input
        valueIn, a string or an int, where
            a string could be either "yes", "no" or "unknown";
            a int value could be 1, 0 or -1.
    Output
        an int, used for storing into db, which will be either 1, 0 or -1, corresponding to "yes", "no" or "unknown".
                
    '''
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
        # https://stackoverflow.com/questions/33137686/python-loading-zip-codes-into-a-dataframe-as-strings
        # if valueIn = 2114, output will be '02114'
        # if valueIn = '2114', output will be '02114' as well.
        # Only work for USA zipcode
        valueOut = str(valueIn).zfill(5)
    return valueOut

def dateToStringUK(dateIn):
    '''
        dateIn = datetime.date(2017, 2, 28)
        
        dateOut = "2017-02-28"
    '''
    #print "dateToString"
    if dateIn is None:
        dateOut = None
        #dateOut = '0000-00-00'
    elif len(str(dateIn))==0:
        dateOut = None
        #dateOut = '0000-00-00'
    elif len(str(dateIn))<4:
        dateOut = None
        #dateOut = '0000-00-00'
    elif len(str(dateIn))==4:
        # such as "2017" only year is provided,
        print dateIn
        try:
            dt = parse(str(dateIn))
            # however, if # example dt = parse("2003")
            # it will be = datetime.datetime(2003, today's month, today's day, 0, 0)
            # however, prefer to use last day of the year
            dateOut = '{0:04}-{1}-{2}'.format(dt.year, 12, 31)
        except ValueError:
            msg = 'Not right date format: ', dateIn
            print msg
            dateOut = None
    else:
        if isinstance(dateIn, datetime.date):
            # such as 2017-02-15
            #print "date format: ", dateIn
            #fieldValueOut = fieldValue.strftime(DATE_FORMAT)
            # to output 2/25/17, use
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        elif isinstance(dateIn, datetime.datetime):
            #print "datetime format: ", dateIn
            #fieldValueOut = fieldValue.strftime("%s %s" % (DATE_FORMAT, TIME_FORMAT))
            # to output 2/25/17, use
            #dateOut = '{0}/{1}/{2:02}'.format(dateIn.month, dateIn.day, dateIn.year % 100)
            dateOut = '{0:04}-{1}-{2}'.format(dateIn.year, dateIn.month, dateIn.day)
            # to output 2/25/2017, use
            #dateOut = '{0}/{1}/{2:04}'.format(dateIn.month, dateIn.day, dateIn.year)
        else:
            #print "other format: ", dateIn
            #dt = datetime.datetime.strptime(dateIn, '%Y-%m-%d')
            #dt = parse(dateIn)
            #print "dt: ", dt
            #dateOut = '{0}/{1}/{2:04}'.format(dt.month, dt.day, dt.year % 100)
            #dateOut = str(dateIn)
            dateOut = validateDate(dateIn)
    return dateOut

def absFloats(float1, float2):
    ''' Return absolute difference between two float values.
        The complexity here is that float1 or float2 may be None or -100 value.
    '''
    #print "absFloats: ", float1, float2
    
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
    
    #print "absFloats: ", float1, float2, diff
    return diff
    
    
def validateDate(dateIn):
    try:
        dt = parse(dateIn)
        # example dt = parse("2003-09-25") = datetime.datetime(2003, 9, 25, 0, 0)
        dateOut = '{0:04}-{1}-{2}'.format(dt.year, dt.month, dt.day)
        # it will be 2003-09-25
        # however, if # example dt = parse("2003")
        # it will be = datetime.datetime(2003, today's month, today's day, 0, 0)
    except ValueError:
        msg = 'Not right date format: ', dateIn
        print msg
        dateOut = None
        
    return dateOut
    
def toBooleanValue(formdata, fieldname):
    ''' Set the right boolean value for a boolean field.
    Input
        formdata, ={"name1":value1, "name2":value2,....}, such as {"is_present":"yes"}
        fieldname, the name for a boolean field, such as "is_present"
    Output
        formdata, , such as {"is_present":True}
            
    Notes
        the boolean value will be True if the original value is 1, "1", "y", "Y", "yes", "Yes", "t", "T", "Ture" etc.
    '''
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
    ''' Given a numeric or string input value, convert it into a string used for SQL query.
    '''
    #print "dbconn_mssql: __convertSQLString", value
    if isinstance(value, datetime.date):
        # such as date(2019, 1,1) becomes "'2019-01-01'"
        strValue = "'" + str(value) + "'"
    elif is_numeric(value):
        # such as 13 becomes '13'
        strValue = str(value)
    else:
        if value is None:
            strValue = "''"
        elif "'" in value:
            # such as "Jonh's report"
            strValue = value.replace("'", "''")
            # it becomes "Jonh''s report" so mssql accepts it
            strValue = "'" + strValue + "'"
            # now it becomes "'Jonh''s report'"
        elif '"' in value:
            # such as 'Jonh"s report'
            strValue = value.replace('"', "''")
            # it becomes "Jonh''s report" so mssql accepts it
            strValue = "'" + strValue + "'"
            # now it becomes "'Jonh''s report'"
        else:
            strValue = "'" + value + "'"
            
    #print "StrValue: ", strValue
    return strValue

def handle_uploaded_file(infile, outfilename):
    ''' 
        Notes:
            migrated from def seek(request) in MyFair project.
    '''
    dest = open(outfilename, 'wb')
    for chunk in infile.chunks():
        dest.write(chunk)
    dest.close()
    
def correctFileName(infilename):
    ''' This is to fix the issue that a protocol file name has space in it.
        We will use "-" to replace space in the output filename, which will used for storing on the
        file storage server on ki-pub10. 
        The original filename will be kept as the original file name.
        
    '''
    if infilename is None:
        return None
        
    outfilename = infilename.strip()
    if ' ' in outfilename:
        outfilename = outfilename.replace(' ', '-')
            
    return outfilename
        
def convertDicToOptions(dicIn):
    ''' Convert a dictionary into a format as options used in a comboBox.
    Input:
        dicIn, {'id1':'title1', 'id2':'title2',....}
        
    Output:
        [s1,s2,...], where
            si = {"id":i, "title":'CEL", "gorup":"D"}
    '''
    options = []
    
    si = {"selected": 'true', "id": 0, "title": ""}
    options.append(si)
    for k,v in dicIn.items():
        #if d[k] is v: print '\tthey are the same object'
        # example: v = 'http://dmac.mit.edu:3000/assays/5'
        #          id = 5
        si = {}
        si["id"] = k
        si["title"] = v
        #si["group"] = ""
        options.append(si)
    return options
    
    
def sizeof_fmt(num):
    """Human friendly file size.
    Refer to: https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    if num is None:
        return ''
    
    num = toInt(num)
    unit_list = zip(['bytes', 'kB', 'MB', 'GB', 'TB', 'PB'], [0, 0, 1, 2, 2, 2])
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
        #md5 = hashlib.md5(open(fullfilename,'rb').read()).hexdigest()
        fi = open(fullfilename,'rb').read()
        print('open file: %s'%fullfilename)
        print'Calculate MD5 checksum...'
        md5 = hashlib.md5(fi).hexdigest()
        checksum = md5
        print('MD5 checksum: %s'%md5)
    elif cf=='SHA1':
        openedFile = open(fullfilename,'rb')
        readFile = openedFile.read()

        #md5Hash = hashlib.md5(readFile)
        #md5Hashed = md5Hash.hexdigest()

        sha1Hash = hashlib.sha1(readFile)
        sha1Hashed = sha1Hash.hexdigest()
        checksum = sha1Hashed
    else:
        checksum = 'NA'
    return checksum
    
    
    
    