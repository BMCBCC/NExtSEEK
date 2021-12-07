import pandas as pd
from unidecode import unidecode

from conversion import toString, cleanString, is_numeric

def printline(fout, dict, fieldnames):
    l = len(fieldnames) - 1
    for i, key in enumerate(fieldnames):
        fout.write(dict[key])
        if i < l:
            fout.write('\t')
        else:
            fout.write('\n')

def getDataCSV(file_in, file_out, sep='\t', skipheader=True,
               comment='#', dtype=None):
    if skipheader and file_out:
        with open(file_in) as fin:
            with open(file_out, 'w') as fout:
                fout.write(fin.readline())
    return pd.read_csv(file_in, sep=sep, comment=comment, dtype=dtype)
    
    
def getString(row, columns, header):
    ''' Input
            row, a list of values in the format [v1, v2, ..., vn]
            columns, a list of headers in the format ['h1', 'h2', ..., 'hn']
            header, a particular header such as 'h5'
            
        Output
            a string from the particular column
    '''
    strIn = 'None'
    if header in columns:
        index = columns.index(header)
        strIn = row[index]
    
    strOut = strIn.strip()
    return strOut

def getIndex(strlist, strIn):
    if strIn in strlist:
        return strlist.index(strIn)
    else:
        return -1
    
def convertFloat(value):
    #print "value in", value
    if value is None:
        return -100
    elif value=='None':
        return -100
    elif value=='':
        return -100
    elif value=='NA':
        return -100
    else:
        try:
            x = float(value)
        except ValueError:
            x = -100
    return x

def convertString(strIn):
    #print "value in", value
    if strIn is None:
        #strOut = "None"
        strOut = ""
    else:
        try:
            strOut = str(strIn)
        except ValueError:
            strOut = strIn
    return strOut

def getFloat(row, columns, header):
    ''' Input
            row, a list of values in the format [v1, v2, ..., vn]
            columns, a list of headers in the format ['h1', 'h2', ..., 'hn']
            header, a particular header such as 'h5'
            
        Output
            a string from the particular column
    '''
    str = getString(row, columns, header)
    value = convertFloat(str)
    return value

def saveCsvfile(outcsvfile, columns, rows):
    ''' Output data into a csv file.
        Input
            outcsvfile, csv file name with the path for output
            columns, the definition of columns, = [str1, str2, str3,...,strN]
            rows, the data in rows, = [row1, row2,...,rowM], while
                row = {str1:v1, str2:v2, ..., strN:vN} 
    '''
    fo = open(outcsvfile,"w")
    line = ','.join(columns) + '\n'
    fo.write(line)
    for row in rows:
        #print row
        line = ""
        for col in columns:
            if col in row:
                line += convertString(row[col]) + ","
            else:
                line += "NA,"
        # replace last "," with "\n"
        line = line[:-1] + "\n"
        #line = ','.join(row) + '\n'
        #print line
        fo.write(line)
    fo.close()
    
    print "save into csv file ", outcsvfile

def saveRecordsIntoExcelPD(rows, columns, excelfile):
    print "saveRecordsIntoExcelPD"    
    # http://stackoverflow.com/questions/18977387/how-to-export-sql-server-result-to-excel-in-python

    n = 0
    newlist = []
    for row in rows:
        newrow = []
        #for i in range(nc):
        for index, item in enumerate(row):
            newitem = toString(item)
            newrow.append(newitem)
            
        newlist.append(newrow)
        n += 1
            
    import pandas as pd
    df = pd.DataFrame(newlist, columns=columns)
    print df
    #df = pd.read_sql_query(sqlquery, self.cnxn)
    print "pd.DataFrame okay"

    writer = pd.ExcelWriter(excelfile)
    print "writer okay"
    df.to_excel(writer, sheet_name='All records')
    print "to_excel okay"
    writer.save()
    print "retrieveAllRecordsIntoExcel okay"
    
def saveDiclistIntoExcelPD(diclist, excelfile):
    '''
    Paras
        diclist, a list of dictionary.
    '''
    print "saveDiclistIntoExcelPD"    
    # http://stackoverflow.com/questions/18977387/how-to-export-sql-server-result-to-excel-in-python

    import pandas as pd
    df = pd.DataFrame.from_dict(diclist)
    #print df
    #df = pd.read_sql_query(sqlquery, self.cnxn)
    #print "pd.DataFrame okay"

    writer = pd.ExcelWriter(excelfile)
    #print "writer okay"
    df.to_excel(writer, sheet_name='All records')
    #print "to_excel okay"
    writer.save()
    #print "retrieveAllRecordsIntoExcel okay"


def saveAllRecordsIntoExcel(olumns, rows, excelfile):
    print "saveAllRecordsIntoExcel"
    # http://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
    import xlwt
    book = xlwt.Workbook(encoding="utf-8")
    sheet1 = book.add_sheet("Sheet 1")
        
    # example
    #sheet1.write(0, 0, "Display")
    #sheet1.write(1, 0, "Dominance")
    #sheet1.write(2, 0, "Test")

    #sheet1.write(0, 1, x)
    #sheet1.write(1, 1, y)
    #sheet1.write(2, 1, z)
    row = 0
    for index, item in enumerate(columns):
        sheet1.write(row, index, item)

    for rowi in rows:
        row += 1
        for index, item in enumerate(rowi):
            newitem = toString(item)
            try:
                sheet1.write(row, index, newitem)
            except:
                newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
        
    print "book.save"
    book.save(excelfile)       
    print "saveAllRecordsIntoExcel okay"
    
def filterDiclist(headers, diclist):
    ''' Filter the list of dictionaries so that a key is removed, if the corresponding value for the key is all empty in the list.
    
    Input:
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        headers, a list of headers as the header for excel file.
    
    Output:
        headers_new, a list of headers as the header fo excel file.
    '''
    headers_new = []
    
    for header in headers:
        headerOkay = False
        for dici in diclist:
            if header in dici:
                value = dici[header]
                if value is not None:
                    try:
                        vstr = str(value)
                        vstr = vstr.strip()
                        if len(vstr)>0:
                            # not an empty string
                            headerOkay = True
                    except:
                        # maybe a date?
                        headerOkay = True
        if headerOkay:
            headers_new.append(header)
    
    return headers_new

def removeDiclistDuplicates(diclist):
    ''' Filter the list of dictionaries so that any duplicated dictionary is removed.
    
    Input:
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
    
    Output:
        diclistOut
        
    Refer to:
        https://stackoverflow.com/questions/9427163/remove-duplicate-dict-in-list-in-python
    '''
    
    # the code below does not reserve the order of the list.
    #diclistOut = [dict(t) for t in set{tuple(d.items()) for d in diclist}]
    
    # to reserve the order of the list, while still remove duplicates, use the following,
    seen = set()
    diclistOut = []
    for d in diclist:
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            diclistOut.append(d)
    
    return diclistOut
    
    
def getConstantRows(headers, diclist):
    ''' Get the list of headers whose values are constant across all rows of the dic list.
    
    Input:
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        headers, a list of headers as the header fo excel file.
    
    Output:
        headers_noneConstant, a list of headers as the header for excel file, whose values are not constant across all
            rows of the dic list.
        diclist_constant, =[{header_1:constant_1}, {header_2:constant_2}, ...], a list of dictionaries with
            header:constant_value pairs, which will be output into an excel tab as the list of rows.
            
        headers_constant, such as ["Sample attribute", "Constant value"], indicates the nature of dictionary in diclist_constant.
    '''
    headers_noneConstant = []
    
    diclist_constant = []
    for header in headers:
        isConstant = True
        
        value0 = None
        for dici in diclist:
            if header in dici:
                value = dici[header]
                if value0 is None:
                    value0 = value
                elif value != value0:
                    isConstant = False
            
        if isConstant:
            # this header has constant value for all rows
            dici = {}
            dici["Sample attribute"] = header
            dici["Constant value"] = value0
            diclist_constant.append(dici)
        else:
            # this header does not have constant value for all rows
            headers_noneConstant.append(header)
    
    headers_constant = ["Sample attribute", "Constant value"]
    
    return headers_noneConstant, diclist_constant, headers_constant
    
def reviseDiclistIntoExcel(diclist, excelfile, headers, titleIn="Sheet 1", isNewSheet=True):
    ''' Save a list of dictionaries into excel file, given
    Params
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        excelfile, excel file for output
        headers, a list of headers as the header fo excel file.
        isNewSheet, True, default, create a new sheet.
                    False, modify the existing sheet, whose name is TitleIn.
        
    Returns
        
    '''
    print("saveAllRecordsIntoExcel")
    print("headers", headers)
    # http://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
    import xlwt
    book = xlwt.Workbook(encoding="utf-8")
    if isNewSheet:
        sheet1 = book.add_sheet(titleIn)
    else:
        sheet1 = book.add_sheet(titleIn)
        
    # example
    #sheet1.write(0, 0, "Display")
    #sheet1.write(1, 0, "Dominance")
    #sheet1.write(2, 0, "Test")

    #sheet1.write(0, 1, x)
    #sheet1.write(1, 1, y)
    #sheet1.write(2, 1, z)
    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
        #print(dici)
        row += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
                newitem = toString(item)
            else:
                newitem = "N/A"
            try:
                sheet1.write(row, index, newitem)
            except:
                newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
        
    #print("book.save")
    book.save(excelfile)       
    #print("saveAllRecordsIntoExcel okay")    
    
def saveDiclistIntoExcel(diclist, excelfile, headers, titleIn="Sheet 1", isNewSheet=True):
    ''' Save a list of dictionaries into excel file, given
    Params
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        excelfile, excel file for output
        headers, a list of headers as the header fo excel file.
        isNewSheet, True, default, create a new sheet.
                    False, modify the existing sheet, whose name is TitleIn.
        
    Returns
        
    '''
    #print("saveAllRecordsIntoExcel")
    #print("headers", headers)
    # http://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
    if not isNewSheet:
        return reviseDiclistIntoExcel(diclist, excelfile, headers, titleIn)
    
    
    import xlwt
    book = xlwt.Workbook(encoding="utf-8")
    sheet1 = book.add_sheet(titleIn)
        
    # example
    #sheet1.write(0, 0, "Display")
    #sheet1.write(1, 0, "Dominance")
    #sheet1.write(2, 0, "Test")

    #sheet1.write(0, 1, x)
    #sheet1.write(1, 1, y)
    #sheet1.write(2, 1, z)
    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
        #print(dici)
        row += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
                newitem = toString(item)
            else:
                newitem = "N/A"
            try:
                sheet1.write(row, index, newitem)
            except:
                newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
        
    #print("book.save")
    book.save(excelfile)       
    #print("saveAllRecordsIntoExcel okay")
    
def writeDiclistToExcelSheet(book, diclist, headers, titleIn="Sheet 1"):
    ''' Write a list of dictionaries to a sheet in an excel file, given
    Params
        book, an Excel book, created by,
            import xlwt
            book = xlwt.Workbook(encoding="utf-8")
    
        diclist, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        headers, a list of headers as the header fo excel file.
        titleIn, sheet title
        
    Returns
        the book
    '''
    # http://stackoverflow.com/questions/13437727/python-write-to-excel-spreadsheet
    sheet1 = book.add_sheet(titleIn)
        
    # example
    #sheet1.write(0, 0, "Display")
    #sheet1.write(1, 0, "Dominance")
    #sheet1.write(2, 0, "Test")

    #sheet1.write(0, 1, x)
    #sheet1.write(1, 1, y)
    #sheet1.write(2, 1, z)
    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
        #print(dici)
        row += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
                newitem = toString(item)
            else:
                newitem = "N/A"
            try:
                sheet1.write(row, index, newitem)
            except:
                newitem = cleanString(newitem)
                sheet1.write(row, index, newitem)
        
    return book

def saveTwoDiclistsIntoExcel(excelfile, diclist1, headers1, title1, diclist2, headers2, title2):
    ''' Save two lists of dictionaries into an excel file in two tabs, given
    Params
        excelfile, excel file for output
        diclist1, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        headers1, a list of headers as the header fo excel file.
        title1, the title for tab1.
        diclist2, = [dic_1, ...,dic_n], where dic_i = {} is a dictionary.
        headers2, a list of headers as the header fo excel file.
        title2, the title for tab1.
    
    Returns
        
    '''
    import xlwt
    book = xlwt.Workbook(encoding="utf-8")
    book = writeDiclistToExcelSheet(book, diclist1, headers1, title1)
    book = writeDiclistToExcelSheet(book, diclist2, headers2, title2)
    book.save(excelfile)
    
    
    
    