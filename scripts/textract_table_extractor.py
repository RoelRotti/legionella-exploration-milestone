import boto3
import io
from PIL import Image
import streamlit as st
import PyPDF2  # Add this import at the top
import time

def upload_to_s3(uploaded_file, bucket):
    """
    Upload a local file to S3
    """
    s3_client = boto3.client(
        's3',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_REGION_EU"]
    )
    
    try:
        # Read and process the PDF
        file_bytes = uploaded_file.read()
        pdf_stream = io.BytesIO(file_bytes)
        
        # Create a new PDF using PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        pdf_writer = PyPDF2.PdfWriter()
        
        # Copy all pages to new PDF
        for page in pdf_reader.pages:
            pdf_writer.add_page(page)
        
        # Save to new PDF
        output_pdf = io.BytesIO()
        pdf_writer.write(output_pdf)
        output_pdf.seek(0)
        
        # Upload the processed PDF
        filename = f"uploads/processed_{uploaded_file.name}"
        s3_client.upload_fileobj(output_pdf, bucket, filename)
        
        st.info("PDF has been processed for better compatibility")
        return filename
            
    except Exception as e:
        st.error(f"S3 Upload Error: {e}")
        return None

def extract_tables_from_pdf(bucket, document):
    """
    Extract tables from a PDF document stored in an S3 bucket
    
    Args:
        bucket (str): S3 bucket name
        document (str): PDF document path in S3
    
    Returns:
        list: Extracted tables
    """
    textract = boto3.client(
        'textract',
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name='eu-west-3'
    )
    
    try:
        # Start asynchronous job
        response = textract.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': document
                }
            },
            FeatureTypes=['TABLES']
        )
        
        job_id = response['JobId']
        st.info(f"Started analysis job: {job_id}")
        
        # Wait for the job to complete
        while True:
            response = textract.get_document_analysis(JobId=job_id)
            status = response['JobStatus']
            st.write(f"Job status: {status}")
            
            if status in ['SUCCEEDED', 'FAILED']:
                break
                
            time.sleep(5)  # Wait 5 seconds before checking again
            
        if status == 'FAILED':
            st.error("Analysis job failed")
            return []
            
        # Get all pages of results
        pages = []
        next_token = None
        
        while True:
            if next_token:
                response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
            else:
                response = textract.get_document_analysis(JobId=job_id)
                
            pages.extend(response['Blocks'])
            
            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break
        
        # After job succeeds, add debugging information
        st.text("Analyzing blocks...")
        
        # Debug information
        block_types = {}
        for block in pages:
            block_type = block['BlockType']
            block_types[block_type] = block_types.get(block_type, 0) + 1
            
        st.write("Document contains:", block_types)
        
        # Process tables with better error handling
        tables = []
        table_blocks = [block for block in pages if block['BlockType'] == 'TABLE']
        
        if not table_blocks:
            st.warning("No table structures were detected in the document.")
            return []
            
        for table in table_blocks:
            try:
                # Get all cells for this table
                cells = [block for block in pages 
                        if block['BlockType'] == 'CELL' 
                        and block.get('TableIndex') == table.get('TableIndex')]
                
                if not cells:
                    continue
                    
                # Get table dimensions
                max_row = max(cell['RowIndex'] for cell in cells)
                max_col = max(cell['ColumnIndex'] for cell in cells)
                
                st.write(f"Found table with dimensions: {max_row}x{max_col}")
                
                # Initialize empty table
                current_table = [['' for _ in range(max_col)] for _ in range(max_row)]
                
                # Fill in cells
                for cell in cells:
                    row_idx = cell['RowIndex'] - 1
                    col_idx = cell['ColumnIndex'] - 1
                    
                    # Extract cell text
                    cell_text = ''
                    if 'Relationships' in cell:
                        for relationship in cell['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                for child_id in relationship['Ids']:
                                    child_block = next((block for block in pages if block['Id'] == child_id), None)
                                    if child_block and child_block['BlockType'] == 'WORD':
                                        cell_text += child_block['Text'] + ' '
                    
                    current_table[row_idx][col_idx] = cell_text.strip()
                
                tables.append(current_table)
                
            except Exception as e:
                st.error(f"Error processing table: {str(e)}")
                continue
        
        if not tables:
            st.warning("No valid tables could be extracted.")
        else:
            st.success(f"Successfully extracted {len(tables)} tables.")
            
        return tables
        
    except Exception as e:
        st.error(f"Error extracting tables: {str(e)}")
        return []

def print_tables(tables):
    """
    Print extracted tables in a readable format
    
    Args:
        tables (list): List of tables to print
    """
    if not tables:
        st.warning("No tables found.")
        return
    
    st.write(f"Total Tables Found: {len(tables)}")
    
    for i, table in enumerate(tables, 1):
        st.write(f"\n### Table {i}")
        
        # Display table using Streamlit
        st.dataframe(table)

def main():
    st.title("Amazon Textract PDF Table Extractor")
    
    # AWS Configuration
    BUCKET_NAME = st.secrets["AWS_S3_BUCKET"]
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            st.info("Uploading file to S3...")
            s3_filename = upload_to_s3(uploaded_file, BUCKET_NAME)
            
            if s3_filename:  # Only proceed if upload was successful
                st.success("File uploaded successfully!")
                
                # Extract tables
                st.info("Extracting tables...")
                tables = extract_tables_from_pdf(BUCKET_NAME, s3_filename)
                
                # Print tables
                print_tables(tables)
            else:
                st.error("Failed to upload file to S3")
        
        except Exception as e:
            st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()