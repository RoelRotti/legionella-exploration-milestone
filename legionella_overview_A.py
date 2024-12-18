from scripts.pdf_processor import extract_pages_with_tables
from scripts.pdf_to_excel import ExportPDFToExcel
from scripts.excel_to_data import process_excel_file

#TODO: extract school

#TODO: pdf extraction, no infographics

# Step 1: Extract pages with tables
extract_pages_with_tables(input_pdf = './Files/lLessness School - Legionella Risk Assessment - 29.10.21.pdf', output_pdf = 'llesness')#./lessness/lessness_filtered_pages.pdf')

# Step 2: Convert PDF to Excel
processor = ExportPDFToExcel()
processor.process(file_name = 'llesness')

# Step 3: Convert Excel to Data
process_excel_file(file_name = 'llesness')

# Step 4: Human review of data

# Step 5: Multiply quantities
#TODO: multiply quantities

#TODO: compare with golden data

#TODO: create dashboard

#TODO: create report

#TODO: Create excel workflow
