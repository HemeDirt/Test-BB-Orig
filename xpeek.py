import openpyxl, sys
wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)
for ws in wb.worksheets:
    print('SHEET:', ws.title, 'max_row:', ws.max_row, 'max_col:', ws.max_column)
    for i, row in enumerate(ws.iter_rows(max_row=3, values_only=True)):
        print('  r%d:' % i, [str(c)[:26] if c is not None else '' for c in row][:14])
wb.close()
