# from pdf_processor import extract_pages_with_tables
# from pdf_to_excel import ExportPDFToExcel
# from excel_to_data import process_excel_file

#TODO: extract school

# # Step 1: Extract pages with tables
# extract_pages_with_tables(input_pdf = './Files/lLessness School - Legionella Risk Assessment - 29.10.21.pdf', output_pdf = 'llesness')#./lessness/lessness_filtered_pages.pdf')

# # Step 2: Convert PDF to Excel
# processor = ExportPDFToExcel()
# processor.process(file_name = 'llesness')

# # Step 3: Convert Excel to Data
# process_excel_file(file_name = 'llesness')

# # Step 4: Human review of data




from scripts.reshape_assets_excel import multiply_quantities

# Step 5: Multiply quantities
# multiply_quantities(file_name='llesness')

# Step 6: Compare with golden data
from scripts.compare_excels import compare_excel_files

compare_excel_files(golden_file_path = './output/6-CompareGoldenOutput/Lessness Primary School.xlsx', created_file_name = 'llesness')
#TODO: create dashboard

#TODO: create report

#TODO: Create excel workflow