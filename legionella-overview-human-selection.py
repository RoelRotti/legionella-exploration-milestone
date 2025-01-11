import streamlit as st
import logging
import time
from scripts.pdf_to_excel import ExportPDFToExcel
from scripts.excel_to_data import process_excel_file
from scripts.reshape_assets_excel import multiply_quantities
from scripts.compare_excels import compare_excel_files
import sys
import pandas as pd

# At the top of the file, after the imports
if 'phase_a_completed' not in st.session_state:
    st.session_state.phase_a_completed = False

if 'start_phase_a' not in st.session_state:
    st.session_state.start_phase_a = False

if 'phase_b_completed' not in st.session_state:
    st.session_state.phase_b_completed = False

if 'start_phase_b' not in st.session_state:
    st.session_state.start_phase_b = False

if 'phase_c_completed' not in st.session_state:
    st.session_state.phase_c_completed = False

if 'start_phase_c' not in st.session_state:
    st.session_state.start_phase_c = False

# Add reset button function
def reset_phase_a():
    st.session_state.phase_a_completed = False
    st.session_state.start_phase_a = False

# Add reset function for phase B
def reset_phase_b():
    st.session_state.phase_b_completed = False
    st.session_state.start_phase_b = False

# Add reset function for phase C
def reset_phase_c():
    st.session_state.phase_c_completed = False
    st.session_state.start_phase_c = False

# Streamlit app setup
st.title("Legionella Overview Processing App")
st.write("This app is designed to process Legionella Overview PDF documents and generate an asset list.")

# Add nickname input field before PDF upload
file_nickname = st.text_input("Enter a nickname for your file (e.g., 'parkwood')", )

# Phase A: File upload and processing
st.header("Phase A: PDF to Excel Conversion")
st.write("Upload a PDF file with filtered pages. Filter the pages for tables that contain assets.")
uploaded_pdf = st.file_uploader("Upload PDF or Excel file", type=["pdf", "xlsx", "xls"])

# Add start button and reset button
if uploaded_pdf and file_nickname:
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.phase_a_completed:
            if st.button("Start Phase A Processing"):
                st.session_state.start_phase_a = True
    with col2:
        if st.session_state.phase_a_completed:
            if st.button("Process Another File"):
                reset_phase_a()

# Move processing logic inside condition for button press
if st.session_state.start_phase_a and not st.session_state.phase_a_completed:

    file_extension = uploaded_pdf.name.split('.')[-1].lower()

    if file_extension == 'pdf':
        # Add explicit logging for upload
        logging.info("PDF uploaded successfully!")
        st.info("Starting PDF processing...")  # Add visual feedback in Streamlit

        # Save uploaded PDF to the filtered manually folder
        input_pdf_path = f'./output-human-selection-pages/1-FilteredManually/{file_nickname}-filtered-pages.pdf'
        with open(input_pdf_path, 'wb') as f:
            f.write(uploaded_pdf.getvalue())
        
        # Process the uploaded PDF file
        processor = ExportPDFToExcel()
        
        try:
            ### Step 2 ### Convert PDF to Excel
            # Add more explicit logging
            logging.info(f"Starting to process file: {uploaded_pdf.name}")
            processor.process(file_name=file_nickname, 
                            input_path='./output-human-selection-pages/1-FilteredManually/', 
                            output_path='./output-human-selection-pages/2-ExportPDFToExcel/')
            
            # Log success message
            logging.info("PDF converted successfully!")

        except Exception as e:
            logging.error(f"Error processing PDF: {str(e)}")
            st.error(f"An error occurred while processing the PDF: {str(e)}")

    elif file_extension == 'xlsx' or file_extension == 'xls':
        try:
            ### Step 2 ### Convert Excel batched excel
            # Save uploaded Excel to the filtered manually folder
            input_excel_path = f'./output-human-selection-pages/1-FilteredManually/{file_nickname}-filtered-pages.xlsx'
            with open(input_excel_path, 'wb') as f:
                f.write(uploaded_pdf.getvalue())
            
            # Process the Excel file to split tables
            # Read the Excel file
            df = pd.read_excel(input_excel_path)
            
            # Split dataframe where there are empty rows (NaN values)
            tables = []
            current_table = []
            
            for idx, row in df.iterrows():
                if row.isna().all():  # If row is completely empty
                    if current_table:
                        tables.append(pd.DataFrame(current_table))
                        current_table = []
                else:
                    current_table.append(row)
            
            # Add the last table if it exists
            if current_table:
                df_table = pd.DataFrame(current_table)
                
                # Split tables longer than 15 rows
                if len(df_table) > 15:
                    header = df_table.iloc[0]  # Save header row
                    remaining_rows = df_table.iloc[1:]  # Get all rows except header
                    
                    # Split into chunks of 15 rows
                    chunks = [remaining_rows.iloc[i:i+15] for i in range(0, len(remaining_rows), 15)]
                    
                    # Add header to each chunk and append to tables
                    for chunk in chunks:
                        chunk_with_header = pd.concat([pd.DataFrame([header]), chunk])
                        tables.append(chunk_with_header.reset_index(drop=True))
                else:
                    tables.append(df_table)

            
            
            # Save each table to a separate sheet in the output Excel
            output_excel_path = f'./output-human-selection-pages/2-ExportPDFToExcel/{file_nickname}-pdf-extract.xlsx'
            with pd.ExcelWriter(output_excel_path) as writer:
                for i, table in enumerate(tables, 1):
                    table.to_excel(writer, sheet_name=f'Table_{i}', index=False)
            
            logging.info("Excel tables split successfully!")
            st.success("Excel file processed and tables split successfully!")

        except Exception as e:
            logging.error(f"Error processing Excel: {str(e)}")
            st.error(f"An error occurred while processing the Excel file: {str(e)}")
    
    
    ### Step 3 ### Convert Excel to Data
    process_excel_file(file_name=file_nickname, 
                    input_path='./output-human-selection-pages/2-ExportPDFToExcel/', 
                    output_path='./output-human-selection-pages/3-ExcelToData/', 
                    assets_known=True)
    
    # Allow user to download the output Excel file
    st.success("PDF processed successfully! Download your Excel file below:")
    
    # Read the Excel file contents before creating the download button
    output_excel_path = f'./output-human-selection-pages/4-HumanReview/{file_nickname}-assets-data-human-review.xlsx'
    with open(output_excel_path, 'rb') as file:
        excel_contents = file.read()
        
    st.download_button(
        label="Download Excel file",
        data=excel_contents,
        file_name=f"{file_nickname}-pdf-extract.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Force update logs after processing
    #st.rerun()  # Changed from st.experimental_rerun()
    st.session_state.phase_a_completed = True
### Step 4 ### Human review of data

# Phase B: File upload and processing
st.header("Phase B: Excel Data Processing")
st.write("""  Upload the altered Excel file that you created in Phase A. \n
         Instructions for altering the Excel: \n
         Check the rows where the 'flag' value is 'Check'. \n
         The value in the cells is from the 'Sonnet' model. If this is wrong, change it and put a '1' in the 'sonnet_wrong' column. \n
         1) if a row needs to be deleted, fill in a 1 in the column 'delete'. \n
         2) if you add have to add a row, add it and fill in a '1' in the column 'row_added' \n
         3) if the flag is 'Sonnet assumed no assets, GPT did assume assets', but there are assets in this page, then fill in a '1' in the column 'sonnet_wrong' \n
         Quantities will be multiplied later. 
         """)
uploaded_excel = st.file_uploader("Upload altered Excel file", type=["xlsx"])


if uploaded_excel and file_nickname:
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.phase_b_completed:
            if st.button("Start Phase B Processing"):
                st.session_state.start_phase_b = True
    with col2:
        if st.session_state.phase_b_completed:
            if st.button("Process Another Excel File"):
                reset_phase_b()

if st.session_state.start_phase_b and not st.session_state.phase_b_completed:
    
    # Save uploaded PDF to the filtered manually folder
    input_excel_path = f'./output-human-selection-pages/4-HumanReview/{file_nickname}-assets-data-human-review.xlsx'
    with open(input_excel_path, 'wb') as f:
        f.write(uploaded_excel.getvalue())

    ### Step 5 ### Multiply quantities
    multiply_quantities(file_name=file_nickname, folder_path='./output-human-selection-pages/')
    
    logging.info("Excel processed successfully!")
    st.success("Excel processed successfully! Download your multiplied quantities file below:")
    st.session_state.phase_b_completed = True

# Phase B download button
if st.session_state.phase_b_completed:
    try:
        with open(f'./output-human-selection-pages/5-MultipliedQuantities/{file_nickname}-assets-multiplied.xlsx', 'rb') as file:
            contents = file.read()
            st.download_button(
                label="Download updated Excel file",
                data=contents,
                file_name=f"{file_nickname}-multiplied.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error loading multiplied quantities file: {str(e)}")

# Ommitted phase C for clarity
# # Add Phase C section
# st.header("Phase C: Compare with Golden Data")
# st.write("Compare your processed Excel file with the golden data to identify differences.")

# uploaded_golden_excel = st.file_uploader("Upload golden Excel file", type=["xlsx"])

# if uploaded_golden_excel and file_nickname and st.session_state.phase_b_completed:
#     col1, col2 = st.columns(2)
#     with col1:
#         if not st.session_state.phase_c_completed:
#             if st.button("Start Phase C Processing"):
#                 st.session_state.start_phase_c = True
#     with col2:
#         if st.session_state.phase_c_completed:
#             if st.button("Run Another Comparison"):
#                 reset_phase_c()

# if st.session_state.start_phase_c and not st.session_state.phase_c_completed:
#     ### Step 6 ### Compare with golden data
#     compare_excel_files(golden_file_path=uploaded_golden_excel, 
#                        created_file_name=file_nickname, 
#                        folder_path='./output-human-selection-pages/')
    
#     logging.info("Comparison completed successfully!")
#     st.success("Comparison completed successfully! Download your comparison files below:")
#     st.session_state.phase_c_completed = True

# # Phase C download buttons
# if st.session_state.phase_c_completed:
#     comparison_files = {
#         "extra in created Excel file": f'./output-human-selection-pages/6-CompareGoldenOutput/{file_nickname}-extra-in-created.xlsx',
#         "missing in created Excel file": f'./output-human-selection-pages/6-CompareGoldenOutput/{file_nickname}-missing-in-created.xlsx'
#     }

#     for label, path in comparison_files.items():
#         try:
#             with open(path, 'rb') as file:
#                 contents = file.read()
#                 st.download_button(
#                     label=f"Download {label}",
#                     data=contents,
#                     file_name=f"{file_nickname}-{label.split()[0]}.xlsx",
#                     mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#                 )
#         except Exception as e:
#             st.error(f"Error loading {label}: {str(e)}")

#TODO: Add additional functionalities for dashboard and report creation

