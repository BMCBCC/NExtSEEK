import pandas as pd
from unidecode import unidecode
import xlwt
from dmac.conversion import toString, cleanString, is_numeric

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
    if strIn is None:
        strOut = ""
    else:
        try:
            strOut = str(strIn)
        except ValueError:
            strOut = strIn
    return strOut

def getFloat(row, columns, header):
    str = getString(row, columns, header)
    value = convertFloat(str)
    return value

def saveCsvfile(outcsvfile, columns, rows):
    fo = open(outcsvfile,"w")
    line = ','.join(columns) + '\n'
    fo.write(line)
    for row in rows:
        line = ""
        for col in columns:
            if col in row:
                line += convertString(row[col]) + ","
            else:
                line += "NA,"
        line = line[:-1] + "\n"
        fo.write(line)
    fo.close()

def saveRecordsIntoExcelPD(rows, columns, excelfile):
    n = 0
    newlist = []
    for row in rows:
        newrow = []
        for index, item in enumerate(row):
            newitem = toString(item)
            newrow.append(newitem)
            
        newlist.append(newrow)
        n += 1
            
    df = pd.DataFrame(newlist, columns=columns)
    writer = pd.ExcelWriter(excelfile)
    df.to_excel(writer, sheet_name='All records')
    writer.save()
    
def saveDiclistIntoExcelPD(diclist, excelfile):
    df = pd.DataFrame.from_dict(diclist)
    writer = pd.ExcelWriter(excelfile)
    df.to_excel(writer, sheet_name='All records')
    writer.save()

def saveAllRecordsIntoExcel(olumns, rows, excelfile):
    book = xlwt.Workbook(encoding="utf-8")
    sheet1 = book.add_sheet("Sheet 1")
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
        
    book.save(excelfile)   
    
def filterDiclist(headers, diclist):
    headers_new = []
    
    for header in headers:
        headerOkay = False
        for dici in diclist:
            dici = {k.lower(): v for k, v in dici.items()}
            if header.lower() in dici:
                value = dici[header.lower()]
                if value is not None:
                    try:
                        vstr = str(value)
                        vstr = vstr.strip()
                        if len(vstr)>0:
                            headerOkay = True
                    except:
                        headerOkay = True
        if headerOkay:
            headers_new.append(header)
    
    return headers_new

def removeDiclistDuplicates(diclist):
    seen = set()
    diclistOut = []
    for d in diclist:
        t = tuple(d.items())
        if t not in seen:
            seen.add(t)
            diclistOut.append(d)
    
    return diclistOut
    
    
def getConstantRows(headers, diclist):
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
            dici = {}
            dici["Sample attribute"] = header
            dici["Constant value"] = value0
            diclist_constant.append(dici)
        else:
            headers_noneConstant.append(header)
    
    headers_constant = ["Sample attribute", "Constant value"]
    return headers_noneConstant, diclist_constant, headers_constant
    
def reviseDiclistIntoExcel(diclist, excelfile, headers, titleIn="Sheet 1", isNewSheet=True):
    book = xlwt.Workbook(encoding="utf-8")
    if isNewSheet:
        sheet1 = book.add_sheet(titleIn)
    else:
        sheet1 = book.add_sheet(titleIn)

    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
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
        
    book.save(excelfile)
    
def saveDiclistIntoExcel(diclist, excelfile, headers, titleIn="Sheet 1", isNewSheet=True):
    if not isNewSheet:
        return reviseDiclistIntoExcel(diclist, excelfile, headers, titleIn)
    
    book = xlwt.Workbook(encoding="utf-8")
    sheet1 = book.add_sheet(titleIn)
    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
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
        
    book.save(excelfile)
    
def writeDiclistToExcelSheet(book, diclist, headers, titleIn="Sheet 1"):
    sheet1 = book.add_sheet(titleIn)
    row = 0
    for index, header in enumerate(headers):
        newitem = toString(header)
        try:
            sheet1.write(row, index, newitem)
        except:
            newitem = cleanString(newitem)
            sheet1.write(row, index, newitem)
    
    for dici in diclist:
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
    book = xlwt.Workbook(encoding="utf-8")
    book = writeDiclistToExcelSheet(book, diclist1, headers1, title1)
    book = writeDiclistToExcelSheet(book, diclist2, headers2, title2)
    book.save(excelfile)
    
    
    
    
