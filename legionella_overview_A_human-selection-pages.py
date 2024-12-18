from scripts.pdf_to_excel import ExportPDFToExcel
from scripts.excel_to_data import process_excel_file

#TODO: extract school

#TODO: pdf extraction, no infographics

# # Step 1: Extract pages with tables
# Manually

# Step 2: Convert PDF to Excel
processor = ExportPDFToExcel()
processor.process(file_name = 'parkwood', input_pdf_path_filtered_pages='./output-human-selection-pages/1-FilteredManually/', output_path='./output-human-selection-pages/2-ExportPDFToExcel/')

# Step 3: Convert Excel to Data
process_excel_file(file_name='parkwood', input_path='output-human-selection-pages/2-ExportPDFToExcel/', output_path='output-human-selection-pages/3-ExcelToData/')

# Step 4: Human review of data

# Step 5: Multiply quantities
#TODO: multiply quantities

#TODO: compare with golden data

#TODO: create dashboard

#TODO: create report

#TODO: Create excel workflow
