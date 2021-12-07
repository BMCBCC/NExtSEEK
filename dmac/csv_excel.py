import csv
import openpyxl
from openpyxl.cell.read_only import EmptyCell
from conversion import toString

def handle_uploaded_file(file, output):
#    logging.debug("upload_here")
    #output = HDF5_REPOSITIRY + file.name
    print "file uploaded into: " + output
    destination = open(output, 'wb+')
    #destination = open('/tmp/'+file.name, 'wb+')
    #destination = open('/tmp', 'wb+')
    for chunk in file.chunks():
        destination.write(chunk)
    destination.close()    
         
def csv_dict_list(incsvfile):
    ''' https://overlaid.net/2016/02/04/convert-a-csv-to-a-dictionary-in-python/
    # Open variable-based csv, iterate over the rows and map values to a list of dictionaries containing key/value pairs
    '''
    reader = csv.DictReader(open(incsvfile, 'rb'))
    dict_list = []
    for line in reader:
        dict_list.append(line)
    return dict_list

def load_csvfile(csvfile):
    ''' Load a csv file into memory
    Input
        csvfile, the file name from http get
        
    Output
        data = {'file':filename, 'columns':titls, 'rows':matrix, 'status':status, 'msg': msg}
    '''
    filename = csvfile.name
    csvfiledata = {}
    if csvfile:
        #outputfile = SAMPLE_EXCEL_REPOSITIRY + filename
        #print outputfile
        #handle_uploaded_file(csvfile, outputfile)
        
        print "csvfile okay"
        csvfiledata['file'] = csvfile
        
        reader = csv.reader(csvfile)
        
        try:
            # ignore title row
            columns = reader.next()
            print columns
            #columnsnew = columns.replace('"','')
            #print columnsnew
            csvfiledata['columns'] = columns
            rows = []
            n = 0
            for row in reader:
                col0 = row[0]
                if len(col0)>0:
                    #rownew = row.replace('"','')
                    rows.append(row)
                n += 1
            
            msg = "Total rows loaded from input csv file: " + str(len(rows))
            print msg
            csvfiledata['rows'] = rows
            csvfiledata['status'] = 1
            csvfiledata['msg'] = msg
        except csv.Error as e:
            msg = "Error in reading csv file: " + str(filename)
            print msg
            csvfiledata['status'] = 0
            csvfiledata['msg'] = msg
        
    return csvfiledata     
      

def convertToDic(columns, row):
    ''' Convert one row of values from csv input into a dictionary,
        given headers of vlues in columns.  
    '''
    datadic = {}
    if len(columns)!=len(row):
        return datadic
    for index, item in enumerate(row):
        key = columns[index]
        datadic[key] = item
        
    return datadic
      
def convertToDicList(columns, rows):
    ''' Convert one row of values from csv input into a dictionary,
        given headers of vlues in columns.  
    '''
    datadiclist = []
    for row in rows:
        datadic = convertToDic(columns, row)
        datadiclist.append(datadic)
    
    #print datadiclist
    return datadiclist
      
def checkHeaders(headersExpected, headersUploaded):
    ''' Compare two list of strings.
    Input
        headersExpected, a list of headers expected from a csv file
        headersUploaded, a list of headers opened from a csv file
        
    Output
        the number and list of missing headers.
    '''
    # make case insensitive
    headersExpectedNew = [x.lower() for x in headersExpected]
    headersUploadedNew = [x.lower() for x in headersUploaded]
    
    n = 0
    missing = []
    for header in headersExpectedNew:
        if header not in headersUploadedNew:
            n += 1
            missing.append(header)
                
    #print "Number of headers missing: ", n
    return n, missing 
      
def load_csvfile_diclist(csvfile, headersKnown=[]):
    ''' Upload HTTP POST csv file into a list of dictionaries.
        The first row should be headers of columns.
        From second row on, it's the values for each row.
    '''
    print "load_csvfile_diclist: upload HTTP POST csv file into a list of dictionaries"        
    csvdata = load_csvfile(csvfile)
    csv_diclist = []
    if csvdata['status']:
        print 'csvfile loaded okay'
    else:
        return csv_diclist
    
    columns = csvdata['columns']
    if len(headersKnown)>0:
        n, missing = checkHeaders(headersKnown, columns)
        if n>0:
            msg = "Miss the following columns: " + ','.join(missing)
            csvdata['status'] = 0
            csvdata['msg'] = msg
            csvdata['diclist'] = csv_diclist
            return csvdata
        
    rows = csvdata['rows']
    csv_diclist = convertToDicList(columns, rows)
    csvdata['diclist'] = csv_diclist
    csvdata['status'] = 1
    csvdata['msg'] = 'Csv file loaded okay'
    #print csvdata
    return csvdata

def convertToDic_renamed(columns, row, headersmapping):
    ''' Convert one row of values from csv input into a dictionary,
        given headers of vlues in columns.  
    '''
    print "convertToDic_renamed"
    datadic = {}
    if len(columns)!=len(row):
        return datadic
    
    print row
    for index, item in enumerate(row):
        print index, item
        key = columns[index]
        newkey = headersmapping[key]
        datadic[newkey] = item
        
    print datadic
    return datadic
      
def convertToDicList_renamed(columns, rows, headersmapping):
    ''' Convert one row of values from csv input into a dictionary,
        given headers of vlues in columns.  
    '''
    print "convertToDicList_renamed"
    datadiclist = []
    for row in rows:
        datadic = convertToDic_renamed(columns, row, headersmapping)
        datadiclist.append(datadic)
    
    #print datadiclist
    return datadiclist

def load_csvfile_diclist_renamed(csvfile, headersmapping):
    ''' Upload HTTP POST csv file into a list of dictionaries.
        The first row should be headers of columns.
        From second row on, it's the values for each row.
    Input
        csvfile, input csv file name;
        headersmapping, a dictionary in which keys are headers csv file and values are key names used for output.
        For example, if a header is called "name",  headersmapping["name"]="alias",
        then in the output, instead of using {"name":"John"} becomes {"alias":"John"}
        The mapping between keys and values must be in unique one to one correspondence.
    '''
    print "load_csvfile_diclist: upload HTTP POST csv file into a list of dictionaries"
    
    filename = csvfile.name
    #load_excelfile_1stSheet(csvfile)
    csvdata = load_csvfile(csvfile)
    if csvdata['status']:
        print 'csvfile loaded okay'
    else:
        svdata['diclist'] = []
        return csvdata
    
    
    columns = csvdata['columns']
    
    headersKnown = headersmapping.keys()
    if len(headersKnown)>0:
        n, missing = checkHeaders(headersKnown, columns)
        if n>0:
            msg = "Miss the following columns: " + ','.join(missing)
            csvdata['status'] = 0
            csvdata['msg'] = msg
            csvdata['diclist'] = []
            return csvdata
        
    rows = csvdata['rows']
    csv_diclist = convertToDicList_renamed(columns, rows, headersmapping)
    csvdata['diclist'] = csv_diclist
    csvdata['status'] = 1
    csvdata['msg'] = 'Csv file loaded okay'
    #print csvdata
    return csvdata

def load_excelfile_asbook(excelfile):
    print "load_excelfile: ", excelfile
    #workbook = openpyxl.load_workbook(filename = excelfile, use_iterators = True)
    workbook = openpyxl.load_workbook(excelfile, use_iterators = True, data_only=True)
    print "Opened load_excelfile: ", excelfile
    return workbook

def load_excelfile_1stSheet(excelfile, headersmapping):
    ''' Load first sheet in the input excel file as a list of dictionaries by
    using the head row as the keys.
    '''
    print "load_excelfile_1stSheet: ", excelfile
    #workbook = openpyxl.load_workbook(filename = excelfile, use_iterators = True)
    # https://stackoverflow.com/questions/39571560/openpyxl-gives-error-on-load-workbook
    # The use_iterators keyword was removed since 2.4.0. Use read_only=True instead.
    workbook = openpyxl.load_workbook(excelfile, read_only=True, data_only=True)
    worksheets = workbook.get_sheet_names()
    print(worksheets)
    filedata = {}
    if len(worksheets)<1:
        filedata['status'] = 0
        filedata['msg'] = "No valid sheet is opened in the file: " + excelfile.name
        return filedata
    
    
    ##for worksheet in worksheets:
    #    print worksheet
    headersmappingLower = {}
    for key, value in headersmapping.iteritems():
        keyLower = key.lower()
        headersmappingLower[keyLower] = value
    
    worksheet1 = worksheets[0]
    print "worksheet name: ", worksheet1
    sheet = workbook.get_sheet_by_name(worksheet1)
    
    headersKnown = headersmapping.keys()
    diclist = []
    columns = []
    n = 0
    for row in sheet.iter_rows():
        n += 1
        if n==1:
            # the first row, use it as headers of columns
            '''
            cell=RawCell(
                row=1,
                column='A',
                coordinate='A1',
                internal_value=u'PI',
                data_type='s',
                style_id=None,
                number_format=None
            )
            '''
            for cell in row:
                #print cell.column, cell.internal_value
                #value = cell.internal_value
                value = cell.value
                if value is None:
                    value = ''
                #print "header: ", value
                #if value is not None:
                #    value = value.strip()
                columns.append(value)
            #print columns
            n0, missing = checkHeaders(headersKnown, columns)
            if n0>0:
                msg = "Miss the following columns: " + ','.join(missing)
                filedata['status'] = 0
                filedata['msg'] = msg
                filedata['diclist'] = []
                return filedata
        else:
            rowdic = {}
            i = 0
            for cell in row:
                key = columns[i]
                i += 1
                #if key in headersmapping:
                #    newkey = headersmapping[key]
                keyLower = key.lower()
                if keyLower in headersmappingLower:
                    newkey = headersmappingLower[keyLower]
                
                    #value = cell.internal_value
                    value = cell.value
                    #print key, newkey, value
                    
                    if value is None:
                        value = ''
                    rowdic[newkey] = value
                else:
                    print "key not found in the key mapping: ", key
                
            #print rowdic
            diclist.append(rowdic)
            #print rowdic
            
    filedata['diclist'] = diclist
    filedata['status'] = 1
    msg = "From file: " + excelfile.name + " loaded " + str(n) + " rows"
    #print msg
    filedata['msg'] = msg
    return filedata

def load_excelfile_1stSheet_v2(excelfile):
    ''' Load first sheet in the input excel file as a list of dictionaries by
    using the head row as the keys.
    '''
    print "load_excelfile_1stSheet: ", excelfile
    #workbook = openpyxl.load_workbook(filename = excelfile, use_iterators = True)
    # https://stackoverflow.com/questions/39571560/openpyxl-gives-error-on-load-workbook
    # The use_iterators keyword was removed since 2.4.0. Use read_only=True instead.
    workbook = openpyxl.load_workbook(excelfile, read_only=True, data_only=True)
    worksheets = workbook.get_sheet_names()
    filedata = {}
    if len(worksheets)<1:
        filedata['status'] = 0
        filedata['msg'] = "No valid sheet is opened in the file: " + excelfile.name
        return filedata
    
    ##for worksheet in worksheets:
    #    print worksheet
    
    worksheet1 = worksheets[0]
    print "worksheet name: ", worksheet1
    sheet = workbook.get_sheet_by_name(worksheet1)
    diclist = []
    columns = []
    n = 0
    for row in sheet.iter_rows():
        n += 1
        if n==1:
            # the first row, use it as headers of columns
            '''
            cell=RawCell(
                row=1,
                column='A',
                coordinate='A1',
                internal_value=u'PI',
                data_type='s',
                style_id=None,
                number_format=None
            )
            '''
            for cell in row:
                #print cell.column, cell.internal_value
                #value = cell.internal_value
                value = cell.value
                if value is None:
                    value = ''
                #print "header: ", value
                #if value is not None:
                #    value = value.strip()
                columns.append(value)
            print columns
            '''
            headersKnown = headersmapping.keys()
            n0, missing = checkHeaders(headersKnown, columns)
            if n0>0:
                msg = "Miss the following columns: " + ','.join(missing)
                filedata['status'] = 0
                filedata['msg'] = msg
                filedata['diclist'] = []
                return filedata
            '''
        else:
            rowdic = {}
            i = 0
            for cell in row:
                key = columns[i]
                i += 1
                '''
                if key in headersmapping:
                    newkey = headersmapping[key]
                    value = cell.internal_value
                    rowdic[newkey] = value
                else:
                    print "key not found in the key mapping: ", key
                '''
                if cell is not None:
                    #value = cell.internal_value
                    value = cell.value
                    if value is None:
                        value = ''
                    rowdic[key] = value
            #print rowdic
            diclist.append(rowdic)
            print rowdic
            
    filedata['diclist'] = diclist
    filedata['status'] = 1
    msg = "From file: " + excelfile.name + " loaded " + str(n) + " rows"
    #print msg
    filedata['msg'] = msg
    return filedata
    
def load_excelfile_1stSheet_anyformat(excelfile):
    ''' Load first sheet in the input excel file as a list of lists in any format
    '''
    print "load_excelfile_1stSheet_anyformat: ", excelfile
    #workbook = openpyxl.load_workbook(filename = excelfile, use_iterators = True)
    #workbook = openpyxl.load_workbook(excelfile, use_iterators = True)     #load_workbook() got an unexpected keyword argument 'use_iterators'
    workbook = openpyxl.load_workbook(excelfile, data_only=True)
    #worksheets = workbook.get_sheet_names()    #deprecated function get_sheet_names (Use wb.sheetnames)
    worksheets = workbook.sheetnames
    filedata = {}
    if len(worksheets)<1:
        filedata['status'] = 0
        filedata['msg'] = "No valid sheet is opened in the file: " + excelfile.name
        return filedata
    
    ##for worksheet in worksheets:
    #    print worksheet
    
    worksheet1 = worksheets[0]
    #sheet = workbook.get_sheet_by_name(worksheet1)   #deprecated function get_sheet_by_name (Use wb[sheetname])
    sheet = workbook[worksheet1]

    listlists = []
    n = 0
    for row in sheet.iter_rows():
        n += 1
        rowlist = []
        for cell in row:
            value = cell.internal_value
            rowlist.append(value)
        #print rowlist
        listlists.append(rowlist)
            
    filedata['listlists'] = listlists
    filedata['status'] = 1
    msg = "From file: " + excelfile.name + " loaded " + str(n) + " rows"
    print msg
    filedata['msg'] = msg
    return filedata
    
def load_file(infile, headersmapping):
    print "load_file"
    filename = infile.name
    names = filename.split(".")
    #print names
    suffix = names[1]
    if suffix.lower()=='csv':
        print "load csv file: ", filename
        return load_csvfile_diclist_renamed(infile, headersmapping)
    else:
        print "load excel file: ", filename
        return load_excelfile_1stSheet(infile, headersmapping)
    

def saveDiclistCSV(outcsvfile, diclist, fieldnames=[]):
    ''' Output a list of dictionaries into a csv file, given
    Input
        outcsvfile, the csv file name
        diclist, =[dic1, dic2,...], where dic={'name1':value1, 'name2':value2,...}
        fieldnames = diclist[0].keys(), by default, this is the list of keys in the dictionary.
            However, it doesn't handle the order of keys. Therefore, fieldnames=['name2', 'name1',... ]
            so that the order of keys can be customized.
        
    Notes: refer to: https://stackoverflow.com/questions/3086973/how-do-i-convert-this-list-of-dictionaries-to-a-csv-file
    '''
    if len(diclist)==0:
        print "Warning: no date to output to csv file"
        return
    
    if len(fieldnames)==0:
        fieldnames = diclist[0].keys()
        
    with open(outcsvfile, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(diclist)
        #for dici in diclist:
        #    writer.writerow(dici)    
    
    
def load_excelfile(infile):
    print "load_file"
    filename = infile.name
    names = filename.split(".")
    #print names
    suffix = names[1]
    return load_excelfile_1stSheet_v2(infile)
    
def modifyExcelDiclist(excelfile, headers, diclist, titleIn="sheet 1"):
    ''' Run a customized query and save results into a excel file.
    Input
        headers = ["Last Name",...] , the expected headers from columns in excel file.
        diclist, a list of dictionaries.
        
    Output
        excelfile,in "xlsx" extension.
        
    Notes:
        Refer to:
            https://stackoverflow.com/questions/2725852/writing-to-existing-workbook-using-xlwt
            https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        Use openpyxl to save the result, which supports the latest xlsx format,
        whill retrieveAllRecordsIntoExcel supports the older xls format.
    '''
    # https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        
    # Call a Workbook() function of openpyxl  
    # to open an existing Workbook object
    print(excelfile)
    wb = openpyxl.load_workbook(filename=excelfile)
    
    # Get workbook active sheet   
    #sheet = wb.get_sheet_by_name(titleIn)
    if titleIn not in wb:
        return
    
    sheet = wb[titleIn]
    
    rowi = 0
    for index, item in enumerate(headers):
        ci = sheet.cell(row = (rowi+1), column = (index+1))
        ci.value = item
        
    for dici in diclist:
        #print columns
        rowi += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
            else:
                item = ""
            ci = sheet.cell(row = (rowi+1), column = (index+1))
            ci.value = toString(item)

    # Anytime you modify the Workbook object 
    # or its sheets and cells, the spreadsheet 
    # file will not be saved until you call 
    # the save() workbook method. 
    wb.save(excelfile)
    
def modifyExcelCell(excelfile, rowNumber, colNumber, cellText, titleIn="sheet 1"):
    ''' Modify a cell in an existing excel file.
    Input
        excelfile, an existing Excel file
        rowNumber, position of row, such 1,2,3,4
        colNumber, position of column, such as 1,2,.. for column A, B, ...
        cellText, text to be modified
        titleIn, sheet title
        
    Output
        excelfile,in "xlsx" extension.
        
    Notes:
        Refer to:
            https://stackoverflow.com/questions/2725852/writing-to-existing-workbook-using-xlwt
            https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        Use openpyxl to save the result, which supports the latest xlsx format,
        whill retrieveAllRecordsIntoExcel supports the older xls format.
    '''
    # https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        
    # Call a Workbook() function of openpyxl  
    # to open an existing Workbook object
    print(excelfile)
    wb = openpyxl.load_workbook(filename=excelfile)
    
    # Get workbook active sheet   
    #sheet = wb.get_sheet_by_name(titleIn)
    if titleIn not in wb:
        return
    
    sheet = wb[titleIn]
    ci = sheet.cell(row = rowNumber, column = colNumber)
    ci.value = cellText

    # Anytime you modify the Workbook object 
    # or its sheets and cells, the spreadsheet 
    # file will not be saved until you call 
    # the save() workbook method. 
    wb.save(excelfile)
    
    
def saveExcelDiclist(excelfile, headers, diclist, titleIn="sheet 1", isNewSheet=True):
    ''' Save a dlic list into a excel file.
    Input:
        headers = ["Last Name",...] , the expected headers from columns in excel file.
        diclist, a list of dictionaries.
        isNewSheet, True, default, create a new sheet.
                    False, modify the existing sheet, whose name is TitleIn.
        
    Output:
        excelfile,in "xlsx" extension.
        
    Notes:
        Refer to: https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        Use openpyxl to save the result, which supports the latest xlsx format,
        whill retrieveAllRecordsIntoExcel supports the older xls format.
    '''
    # https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
    if not isNewSheet:
        return modifyExcelDiclist(excelfile, headers, diclist, titleIn)
        
    # Call a Workbook() function of openpyxl  
    # to create a new blank Workbook object 
    wb = openpyxl.Workbook() 
  
    # Get workbook active sheet   
    # from the active attribute 
    sheet = wb.active
    sheet.title = titleIn
  
    '''
        # example
        # Cell objects also have row, column 
        # and coordinate attributes that provide 
        # location information for the cell. 
  
        # Note: The first row or column integer 
        # is 1, not 0. Cell object is created by 
        # using sheet object's cell() method. 
        #c1 = sheet.cell(row = 1, column = 1) 
  
        # writing values to cells 
        #c1.value = "ANKIT"
  
        #c2 = sheet.cell(row= 1 , column = 2) 
        #c2.value = "RAI"
  
        # Once have a Worksheet object, one can 
        # access a cell object by its name also. 
        # A2 means column = 1 & row = 2. 
        #c3 = sheet['A2'] 
        #c3.value = "RAHUL"
  
        # B2 means column = 2 & row = 2. 
        #c4 = sheet['B2'] 
        #c4.value = "RAI"
    '''    
    rowi = 0
    for index, item in enumerate(headers):
        ci = sheet.cell(row = (rowi+1), column = (index+1))
        ci.value = item
        
    for dici in diclist:
        #print columns
        rowi += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
            else:
                item = ""
            ci = sheet.cell(row = (rowi+1), column = (index+1))
            ci.value = toString(item)

    # Anytime you modify the Workbook object 
    # or its sheets and cells, the spreadsheet 
    # file will not be saved until you call 
    # the save() workbook method. 
    wb.save(excelfile)
    
def reviseExcelDiclist(excelfile, headers, diclist, sheet_name="sheet 1"):
    ''' Save a dlic list into a excel file.
    Input:
        headers = ["Last Name",...] , the expected headers from columns in excel file.
        diclist, a list of dictionaries.
        
    Output:
        excelfile,in "xlsx" extension.
        
    Notes:
        Refer to: https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
        Use openpyxl to save the result, which supports the latest xlsx format,
        whill retrieveAllRecordsIntoExcel supports the older xls format.
    '''
    # https://www.geeksforgeeks.org/python-writing-excel-file-using-openpyxl-module/
    # https://stackoverflow.com/questions/36582460/how-to-clear-a-range-of-values-in-an-excel-workbook-using-openpyxl
        
    # Call a Workbook() function of openpyxl  
    # to open an existing Workbook object
    print(excelfile)
    wb = openpyxl.load_workbook(filename=excelfile)
    
    # Get workbook active sheet   
    #sheet = wb.get_sheet_by_name(titleIn)
    titleIn = sheet_name
    if titleIn not in wb:
        return
    
    # index of [sheet_name] sheet
    idx = wb.sheetnames.index(sheet_name)

    #    remove [sheet_name]
    # old versions: wb.remove(writer.book.worksheets[idx])
    # for new versions, tested with 3.0.3
    ws = wb.get_sheet_by_name(sheet_name)
    wb.remove(ws)

    # create an empty sheet [sheet_name] using old index
    wb.create_sheet(sheet_name, idx)
    
    sheet = wb[titleIn]
    
    rowi = 0
    for index, item in enumerate(headers):
        ci = sheet.cell(row = (rowi+1), column = (index+1))
        ci.value = item
        
    for dici in diclist:
        #print columns
        rowi += 1
        for index, header in enumerate(headers):
            if header in dici:
                item = dici[header]
            else:
                item = ""
            ci = sheet.cell(row = (rowi+1), column = (index+1))
            ci.value = toString(item)

    # Anytime you modify the Workbook object 
    # or its sheets and cells, the spreadsheet 
    # file will not be saved until you call 
    # the save() workbook method. 
    wb.save(excelfile)
    
    
def loadSheet_all(sheet):
    diclist = []
    columns = []
    n = 0
    for row in sheet.iter_rows():
        empty = all(isinstance(cell, EmptyCell) for cell in row) # check if all cells are empty
        if empty:
            # ignore any empty row
            #print("loadSheet_all: empty row", row)
            continue
        
        n += 1
        if n==1:
            # the first row, use it as headers of columns
            '''
            cell=RawCell(
                row=1,
                column='A',
                coordinate='A1',
                internal_value=u'PI',
                data_type='s',
                style_id=None,
                number_format=None
            )
            '''
            for cell in row:
                #print cell.column, cell.internal_value
                #value = cell.internal_value
                value = cell.value
                if value is None:
                    value = ''
                #print "header: ", value
                #if value is not None:
                #    value = value.strip()
                columns.append(value)
            #print columns
        else:
            rowdic = {}
            i = 0
            isEmpty = 0
            for cell in row:
                key = columns[i]
                i += 1
                if cell is not None:
                    #value = cell.internal_value
                    value = cell.value
                    if value is None:
                        value = ''
                    else:
                        isEmpty = 1
                    rowdic[key] = value
                    
            #print rowdic
            if isEmpty==0:
                # ignore any empty row
                #print("loadSheet_all: empty row", row)
                continue
            else:
                diclist.append(rowdic)
            #print rowdic
            
    sheetData = {'diclist':diclist, 'headers':columns}
    return sheetData
    
    
def loadSheet(sheet):
    sheetData = loadSheet_all(sheet)
    return sheetData['diclist']
    
def load_excelfile_asdic(excelfile):
    ''' Load an excel file as a dictionary of sheets.
    Input
        excelfile, the excel file.
    
    Output
        filedata={
            'sheetname1':diclist1,
            'sheetname2':diclist2,
            ...,
            'sheetnames':sheetnames,
            'status': 0 or 1,
            'msg': ''
        }
    '''
    print("loading excelfile asdic: %s"%excelfile)
    #workbook = openpyxl.load_workbook(filename = excelfile, use_iterators = True)
    workbook = openpyxl.load_workbook(excelfile, read_only=True, data_only=True)
    #print "Opened load_excelfile: ", excelfile
    #worksheets = workbook.get_sheet_names()
    worksheets = workbook.sheetnames
    
    #print(worksheets)
    filedata = {}
    if len(worksheets)<1:
        filedata['status'] = 0
        #filedata['msg'] = "No valid sheet is opened in the file: " + excelfile.name
        filedata['msg'] = "No valid sheet is opened in the file. "
        return filedata
    
    sheetnames = []
    for sheetname in worksheets:
        name = sheetname.upper().strip()
        print("sheet name: %s"%name)
        sheetnames.append(name)
        #sheet = workbook.get_sheet_by_name(sheetname)
        sheet = workbook[sheetname]
        #diclist = loadSheet(sheet)
        #filedata[name] = diclist
        sheetData = loadSheet_all(sheet)
        filedata[name] = sheetData
        
        #print(sheetname, len(diclist))
    
    print("loaded excelfile asdic: %s"%excelfile)
    filedata['sheetnames'] = sheetnames
    if len(sheetnames)>0:
        filedata['status'] = 1
        #filedata['msg'] = "Loaded file: " + excelfile.name
        filedata['msg'] = "Loaded file. "
    else:
        filedata['status'] = 0
        #filedata['msg'] = "Error: No sheet loaded file: " + excelfile.name
        filedata['msg'] = "Error: No sheet loaded file. "
        print(filedata['msg'])
    return filedata
    
    