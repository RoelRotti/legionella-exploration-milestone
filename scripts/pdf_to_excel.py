import logging
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
import PyPDF2
import pandas as pd
import streamlit as st
import xlsxwriter

# Define a monkeypatch function that will execute before importing Adobe SDK
def apply_adobe_sdk_print_patch():
    """
    Apply a monkeypatch to fix Python 2 style print statements in the Adobe SDK.
    This is specifically targeting the 'Missing parentheses in call to print' error.
    """
    import importlib.util
    import sys
    from types import ModuleType
    
    # Create a custom module loader that fixes Python 2 print statements
    class Py2PrintFixer(ModuleType):
        def __init__(self, module):
            super().__init__(module.__name__)
            self.__dict__.update(module.__dict__)
        
        def __getattribute__(self, name):
            attr = super().__getattribute__(name)
            # If this is code that's being executed, fix Python 2 print statements
            if isinstance(attr, str) and "print " in attr:
                # This is a very simple fix and might not catch all edge cases
                return attr.replace("print ", "print(").replace("\n", ")\n")
            return attr
    
    # Apply the patch to relevant modules
    # Note: This is a simplified approach. A more comprehensive approach would 
    # involve parsing the Python code and fixing the syntax properly.
    logging.info("Applying Adobe SDK print statement patch")

# Apply the monkeypatch before importing Adobe modules
apply_adobe_sdk_print_patch()

# Import Adobe PDF Services modules
try:
    from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
    from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
    from adobe.pdfservices.operation.io.cloud_asset import CloudAsset
    from adobe.pdfservices.operation.io.stream_asset import StreamAsset
    from adobe.pdfservices.operation.pdf_services import PDFServices
    from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
    from adobe.pdfservices.operation.pdfjobs.jobs.export_pdf_job import ExportPDFJob
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_params import ExportPDFParams
    from adobe.pdfservices.operation.pdfjobs.params.export_pdf.export_pdf_target_format import ExportPDFTargetFormat
    from adobe.pdfservices.operation.pdfjobs.result.export_pdf_result import ExportPDFResult
    adobe_sdk_available = True
    logging.info("Successfully imported Adobe PDF Services SDK")
except SyntaxError as e:
    logging.error(f"SyntaxError importing Adobe SDK: {str(e)}")
    adobe_sdk_available = False
except Exception as e:
    logging.error(f"Error importing Adobe SDK: {str(e)}")
    adobe_sdk_available = False

logging.basicConfig(level=logging.INFO)
load_dotenv()

class ExportPDFToExcel:
    def __init__(self):
        if not adobe_sdk_available:
            error_msg = "Adobe PDF Services SDK failed to initialize. Check previous error logs for details."
            logging.error(error_msg)
            raise RuntimeError(error_msg)

        # Get credentials from environment variables
        client_id = os.environ.get("PDF_SERVICES_CLIENT_ID")
        client_secret = os.environ.get("PDF_SERVICES_CLIENT_SECRET")
        
        # Log credential presence (without exposing values)
        logging.info(f"PDF_SERVICES_CLIENT_ID present: {bool(client_id)}")
        logging.info(f"PDF_SERVICES_CLIENT_SECRET present: {bool(client_secret)}")
        
        if not client_id or not client_secret:
            error_msg = "Adobe PDF Services credentials are missing from environment variables"
            logging.error(error_msg)
            raise ValueError("Adobe PDF Services credentials (PDF_SERVICES_CLIENT_ID and PDF_SERVICES_CLIENT_SECRET) must be set in environment variables")
        
        logging.info("Initializing Adobe PDF Services with credentials")
        try:
            self.credentials = ServicePrincipalCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            logging.info("Successfully created ServicePrincipalCredentials")
            
            self.pdf_services = PDFServices(credentials=self.credentials)
            logging.info("Successfully initialized PDFServices")
            
            # Test credentials by attempting a simple operation
            logging.info("Testing Adobe PDF Services credentials...")
            test_result = self.pdf_services.get_service_info()
            logging.info(f"Credentials test successful. Service info: {test_result}")
            
        except Exception as e:
            error_msg = f"Failed to initialize Adobe PDF Services: {str(e)}"
            logging.error(error_msg)
            if hasattr(e, 'response'):
                logging.error(f"Response status: {e.response.status_code}")
                logging.error(f"Response body: {e.response.text}")
            raise RuntimeError(error_msg)
            
        self.temp_dir = 'temp_pdfs'
        os.makedirs(self.temp_dir, exist_ok=True)
        logging.info(f"Created temp directory at {self.temp_dir}")

    def split_pdf(self, input_pdf):
        pdf_reader = PyPDF2.PdfReader(input_pdf)
        temp_files = []
        
        for page_num in range(len(pdf_reader.pages)):
            pdf_writer = PyPDF2.PdfWriter()
            pdf_writer.add_page(pdf_reader.pages[page_num])
            
            output_filename = os.path.join(self.temp_dir, f'page_{page_num + 1}.pdf')
            with open(output_filename, 'wb') as output_file:
                pdf_writer.write(output_file)
            temp_files.append(output_filename)
            
        return temp_files

    def convert_pdf_to_excel(self, pdf_path, page_num):
        try:
            logging.info(f"Starting PDF to Excel conversion for page {page_num}")
            logging.info(f"Reading PDF file: {pdf_path}")
            
            with open(pdf_path, 'rb') as file:
                input_stream = file.read()
                logging.info(f"Successfully read PDF file, size: {len(input_stream)} bytes")

            logging.info("Uploading PDF to Adobe services")
            input_asset = self.pdf_services.upload(input_stream=input_stream, 
                                                 mime_type=PDFServicesMediaType.PDF)
            logging.info("PDF uploaded successfully")

            logging.info("Creating export job parameters")
            export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.XLSX)
            export_pdf_job = ExportPDFJob(input_asset=input_asset, 
                                         export_pdf_params=export_pdf_params)
            logging.info("Export job parameters created")

            logging.info("Submitting export job")
            location = self.pdf_services.submit(export_pdf_job)
            logging.info(f"Job submitted successfully, location: {location}")

            logging.info("Waiting for job result")
            pdf_services_response = self.pdf_services.get_job_result(location, ExportPDFResult)
            logging.info("Got job result")

            result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
            stream_asset: StreamAsset = self.pdf_services.get_content(result_asset)
            logging.info("Retrieved result content")

            output_file = os.path.join(self.output_dir, f'page_{page_num}.xlsx')
            logging.info(f"Writing result to: {output_file}")
            with open(output_file, "wb") as f:
                content = stream_asset.get_input_stream()
                f.write(content)
                logging.info(f"Successfully wrote {len(content)} bytes to Excel file")
            
            return output_file

        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            logging.exception(f'Adobe API Exception encountered while executing operation: {str(e)}')
            if hasattr(e, 'response'):
                logging.error(f'Response status: {e.response.status_code}')
                logging.error(f'Response body: {e.response.text}')
            return None
        except Exception as e:
            logging.exception(f'Unexpected error during PDF to Excel conversion: {str(e)}')
            return None

    def merge_excel_files(self, excel_files):
        writer = pd.ExcelWriter(os.path.join(self.output_dir, f'{self.file_name}-pdf-extract.xlsx'), 
                              engine='xlsxwriter')
        
        for excel_file in excel_files:
            if excel_file:
                page_num = os.path.splitext(os.path.basename(excel_file))[0]
                df = pd.read_excel(excel_file, engine='openpyxl')
                
                # Find indices of empty rows (where all values are NaN)
                empty_rows = df.isna().all(axis=1)
                empty_row_indices = empty_rows[empty_rows].index.tolist()
                
                # If there are empty rows, split the dataframe into multiple tables
                if empty_row_indices:
                    # Add the start and end indices to create complete splits
                    split_indices = [0] + empty_row_indices + [len(df)]
                    
                    # Create sub-dataframes for each table
                    table_counter = 1  # Initialize counter here
                    for i in range(len(split_indices) - 1):
                        start_idx = split_indices[i]
                        end_idx = split_indices[i + 1]
                        
                        # Skip empty sections
                        if start_idx + 1 == end_idx:
                            continue
                        
                        # If start_idx is an empty row index, start from next row
                        if start_idx in empty_row_indices:
                            start_idx += 1
                        
                        sub_df = df.iloc[start_idx:end_idx].reset_index(drop=True)
                        
                        # Skip if sub_df is empty
                        if sub_df.empty:
                            continue
                        
                        # Check if this is the only table (no empty rows)
                        if len(split_indices) == 2:  # Only one split means no additional tables
                            new_sheet_name = f"{page_num}"  # Just use page_x
                        else:
                            new_sheet_name = f"{page_num}_table_{table_counter}"
                            table_counter += 1  # Only increment when we actually write a table
                        
                        sub_df.to_excel(writer, sheet_name=new_sheet_name, index=False)
                else:
                    # If no empty rows, save the entire dataframe as one sheet
                    df.to_excel(writer, sheet_name=page_num, index=False)
        
        writer.close()

    def cleanup(self, temp_files, excel_files):
        # Clean up temporary PDF files
        for file in temp_files:
            if os.path.exists(file):
                os.remove(file)
        
        # Clean up individual Excel files
        for file in excel_files:
            if file and os.path.exists(file):
                os.remove(file)

    def process(self, file_name, input_path='./output/1-FilteredPages/', output_path='./output/2-ExportPDFToExcel/'):
        logging.info(f"Processing file {file_name}")
        # Create output directory if it doesn't exist
        self.file_name = file_name
        self.output_dir = output_path
        os.makedirs(self.output_dir, exist_ok=True)

        # Construct input path and verify file
        input_pdf_path = f'{input_path}{file_name}-filtered-pages.pdf'
        if not os.path.exists(input_pdf_path):
            error_msg = f"Input PDF file not found: {input_pdf_path}"
            logging.error(error_msg)
            raise FileNotFoundError(error_msg)
            
        # Log file details
        file_size = os.path.getsize(input_pdf_path)
        logging.info(f"Input PDF file size: {file_size} bytes")
        
        # Verify file is readable
        try:
            with open(input_pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                page_count = len(pdf_reader.pages)
                logging.info(f"Successfully opened PDF. Page count: {page_count}")
        except Exception as e:
            error_msg = f"Failed to read input PDF: {str(e)}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Split PDF into individual pages
        temp_pdf_files = self.split_pdf(input_pdf_path)
        logging.info(f"Split PDF into {len(temp_pdf_files)} temporary files")
        
        # Convert each page to Excel
        excel_files = []
        for i, pdf_file in enumerate(temp_pdf_files):
            logging.info(f"Processing page {i + 1}")
            excel_file = self.convert_pdf_to_excel(pdf_file, i + 1)
            if excel_file:
                excel_files.append(excel_file)
            else:
                logging.warning(f"Failed to convert page {i + 1} to Excel")
        
        if not excel_files:
            error_msg = "No Excel files were generated from PDF conversion"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
        
        # Merge Excel files
        logging.info(f"Merging {len(excel_files)} Excel files")
        self.merge_excel_files(excel_files)
        
        # Verify output file
        output_path = os.path.join(self.output_dir, f'{self.file_name}-pdf-extract.xlsx')
        if not os.path.exists(output_path):
            error_msg = f"Output Excel file was not created: {output_path}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
            
        output_size = os.path.getsize(output_path)
        logging.info(f"Generated Excel file size: {output_size} bytes")
        
        # Cleanup temporary files
        self.cleanup(temp_pdf_files, excel_files)
        
        logging.info("Processing complete. Check the output directory for the merged Excel file.")

if __name__ == "__main__":
    processor = ExportPDFToExcel()
    processor.process(file_name = 'llesness')