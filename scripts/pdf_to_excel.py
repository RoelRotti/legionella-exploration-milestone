import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import PyPDF2
import pandas as pd
import streamlit as st

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

logging.basicConfig(level=logging.INFO)
load_dotenv()

class ExportPDFToExcel:
    def __init__(self):
        # Use Streamlit secrets instead of os.getenv
        if 'PDF_SERVICES_CLIENT_ID' not in st.secrets:
            raise ValueError("PDF Services credentials not found in environment variables")
            
        self.credentials = ServicePrincipalCredentials(
            client_id=st.secrets['PDF_SERVICES_CLIENT_ID'],
            client_secret=st.secrets['PDF_SERVICES_CLIENT_SECRET']
        )
        self.pdf_services = PDFServices(credentials=self.credentials)
        self.temp_dir = 'temp_pdfs'
        os.makedirs(self.temp_dir, exist_ok=True)

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
            with open(pdf_path, 'rb') as file:
                input_stream = file.read()

            input_asset = self.pdf_services.upload(input_stream=input_stream, 
                                                 mime_type=PDFServicesMediaType.PDF)

            export_pdf_params = ExportPDFParams(target_format=ExportPDFTargetFormat.XLSX)
            export_pdf_job = ExportPDFJob(input_asset=input_asset, 
                                         export_pdf_params=export_pdf_params)

            location = self.pdf_services.submit(export_pdf_job)
            pdf_services_response = self.pdf_services.get_job_result(location, ExportPDFResult)

            result_asset: CloudAsset = pdf_services_response.get_result().get_asset()
            stream_asset: StreamAsset = self.pdf_services.get_content(result_asset)

            output_file = os.path.join(self.output_dir, f'page_{page_num}.xlsx')
            with open(output_file, "wb") as f:
                f.write(stream_asset.get_input_stream())
            
            return output_file

        except (ServiceApiException, ServiceUsageException, SdkException) as e:
            logging.exception(f'Exception encountered while executing operation: {e}')
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

        # Construct output path
        input_pdf_path= f'{input_path}{file_name}-filtered-pages.pdf'
        #utput_pdf_path = os.path.join(self.output_dir, f'{file_name}-pdf-extract.xlsx')

        
        # Split PDF into individual pages
        temp_pdf_files = self.split_pdf(input_pdf_path)
        
        # Convert each page to Excel
        excel_files = []
        for i, pdf_file in enumerate(temp_pdf_files):
            logging.info(f"Processing page {i + 1}")
            excel_file = self.convert_pdf_to_excel(pdf_file, i + 1)
            excel_files.append(excel_file)
        
        # Merge Excel files
        logging.info("Merging Excel files")
        self.merge_excel_files(excel_files)
        
        # Cleanup temporary files
        self.cleanup(temp_pdf_files, excel_files)
        
        logging.info("Processing complete. Check the output directory for the merged Excel file.")

if __name__ == "__main__":
    processor = ExportPDFToExcel()
    processor.process(file_name = 'llesness')