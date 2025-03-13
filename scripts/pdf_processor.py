import base64
import io
import os
import fitz
from PIL import Image
import openai
import json
import logging
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from llm_confidence.logprobs_handler import LogprobsHandler

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

"""
Scan image for table
"""

from orq_ai_sdk import OrqAI
orq_client = OrqAI(
    api_key=os.environ.get("ORQ_API_KEY"),
    environment="production"
)
orq_client.set_user(id=2024)



def extract_pages_with_tables(input_pdf_path, name_file):
    """
    Extracts pages containing tables from a PDF file and creates a new PDF with only those pages.

    Uses computer vision to identify pages containing tables by converting each page to an image
    and analyzing it with the ORQ AI API. Creates a new PDF containing only the pages where
    tables were detected.

    Args:
        input_pdf_path (str): Path to the input PDF file
        name_file (str): Base name for the output file (e.g., 'llesness')

    Returns:
        str: Path to the output PDF file
    """
    import base64
    import io
    import os
    import fitz
    from PIL import Image
    from PyPDF2 import PdfReader, PdfWriter
    import openai

    # Create output directory if it doesn't exist
    output_dir = './output/1-FilteredPages'
    os.makedirs(output_dir, exist_ok=True)

    # Construct output path
    output_pdf_path = os.path.join(output_dir, f'{name_file}_filtered_pages.pdf')

    logger.info("Starting extraction of pages with tables")

    # Set your OpenAI API key
    # openai.api_key = openai_api_key

    # Open the PDF document
    pdf_document = fitz.open(input_pdf_path)
    pages_with_tables = []

    pdf_reader = PdfReader(input_pdf_path)

    for page_number in range(pdf_document.page_count):
        page = pdf_document[page_number]
        
        # Convert page to image with reduced resolution
        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Optionally resize the image if still too large
        max_size = (800, 800)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert image to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", optimize=True)
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        try:

            # Cost: 0.001 
            response = orq_client.deployments.invoke(
                key="legionella-table-evaluate",
                context={
                    "environments": []
                },
                metadata={
                    "page-number": page_number + 1
                }, 
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Does this image of a pdf (which is a legionella risk assessment) contain a table? If yes, True, if no, False."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ],
                    }
                ],
            )
        
            # # Output the result for each image
            # print(f"Extraction result: {response.choices[0].message.content}")
        
            # Correctly access the response content
            result_content = response.choices[0].message.content.strip()
            if result_content == "True":
                pages_with_tables.append(page_number + 1)

            print(f"Page {page_number + 1} extraction result: {result_content}")

            
        except Exception as e:
            print(f"Error processing page {page_number + 1}: {e}")

    pdf_document.close()

    # Create a new PDF containing only the pages that returned True
    pdf_writer = PdfWriter()
    for page_num in pages_with_tables:
        # PDF page numbers are zero-based in PyPDF2
        pdf_writer.add_page(pdf_reader.pages[page_num - 1])

    # Write the filtered PDF to a file
    with open(output_pdf_path, "wb") as f:
        pdf_writer.write(f)

    print("Filtered PDF created:", output_pdf_path)

## Azure Read ##

def extract_text_from_pdf(document_path, endpoint, key):
    """
    Extracts text content from a PDF using Azure Form Recognizer.

    Uses Azure's Document Analysis Client to perform OCR on the PDF and extract
    text content from all pages.

    Args:
        document_path (str): Path to the PDF file
        endpoint (str): Azure Form Recognizer endpoint URL
        key (str): Azure Form Recognizer API key

    Returns:
        DocumentAnalysisResult: Azure's analysis result containing extracted text and metadata
    """
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    logger.info("Starting extraction of text from PDF with Azure OCR")

    # Initialize the Document Analysis Client
    document_analysis_client = DocumentAnalysisClient(
        endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    # Read the document content
    with open(document_path, "rb") as f:
        document = f.read()

    # Use the Azure Read model to extract text
    poller = document_analysis_client.begin_analyze_document(
        model_id="prebuilt-read", document=document
    )
    result = poller.result()

    # # Extract and print text content
    # print("\nExtracted Text:")
    # for page in result.pages:
    #     print(f"\nPage {page.page_number}:")
    #     for line in page.lines:
    #         print(line.content)

    logger.info("Finished extraction of text from PDF with Azure OCR")

    return result


def process_pdf_pages(document_path, result, high_res=True):
    """
    Processes PDF pages to extract tables and convert them to JSON format.

    Combines computer vision and OCR results to identify and extract tables from each page.
    Uses ORQ AI to convert the identified tables into structured JSON format while maintaining
    fidelity to the extracted text.

    Args:
        document_path (str): Path to the PDF file
        result (DocumentAnalysisResult): Azure OCR results for the PDF
        high_res (bool): If True, uses full resolution for image conversion. Default False.

    Returns:
        None: Writes extracted tables to 'lessness/output.json'
    """
    logger.info("Starting extraction of tables from PDF")

    # Add logging for PDF initialization
    logger.info(f"Attempting to open PDF: {document_path}")
    try:
        pdf_document = fitz.open(document_path)
        logger.info(f"Successfully opened PDF. Page count: {pdf_document.page_count}")
    except Exception as e:
        logger.error(f"Failed to open PDF: {e}")
        return

    # Initialize a dictionary to store results for each page
    pages_results = {}
    
    # Create Excel writer
    with pd.ExcelWriter('lessness/tables.xlsx', engine='xlsxwriter') as excel_writer:
        logger.info(f"Starting to process {pdf_document.page_count} pages")
        for page_number in range(pdf_document.page_count):
            page = pdf_document[page_number]
            logger.info(f"Processing page {page_number + 1}")
            
            # Convert page to image with configurable resolution
            matrix = fitz.Matrix(1, 1) if high_res else fitz.Matrix(0.5, 0.5)
            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Convert image to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG", optimize=True)
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # Extract text content for the current page
            page_text = ""
            for line in result.pages[page_number].lines:
                page_text += line.content + " "

            try:
                response = orq_client.deployments.invoke(
                    key="legionella-table-size",
                    context={
                        "environments": []
                    },
                    metadata={
                        "page-number": page_number + 1
                    }, 
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": """What is/are the dimensions of the table(s) on the page below? just answer with: [columns]x[rows]"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ],
                        }
                    ],
                )
            except Exception as e:
                logger.error(f"Error getting dimensions of table for page {page_number + 1}: {e}")

            table_dimensions = response.choices[0].message.content.strip()

            logger.info(f"Dimensions of table for page {page_number + 1}: {table_dimensions}")

            # # Make a call to OpenAI with the image and extracted text
            # try:
            #     response = orq_client.deployments.invoke(
            #         key="legionella-table-extraction",
            #         context={
            #             "environments": []
            #         },
            #         metadata={
            #             "page-number": page_number + 1
            #         }, 
            #         messages=[
            #         {
            #             "role": "user",
            #                 "content": [
            #                     {
            #                         "type": "text",
            #                         "text": f"""
            #                         You will be given an image of a page from a PDF and the text extracted from the page.
            #                         Convert each table to JSON format following these rules:

            #                         1. Grid Analysis:
            #                         - First analyze the table to determine the standard/most common grid size
            #                         - Count the most frequently occurring number of columns across all rows
            #                         - This becomes your standard column count for all rows

            #                         2. Row-Based Structure:
            #                             - Represent each table as a list of lists, where each inner list represent a row.
            #                             - Rows are read left-to-right and processed in sequence, from the first row to the last.
            #                             - Columns are only determined implicitly by the number of elements in each row. 
            #                             - The first list in the list of lists represents the first row/column headers.
            #                             - The other lists in the list of lists represent the data in the table.
            #                             - Each list in the list of lists must have the same number of elements as the standard column count determined in step 1.
            #                             - The data in the table is read left-to-right across each row.
            #                             - Never combine data vertically from different rows

            #                         3. Grid Consistency:
            #                         - Every row array must have exactly the same number of columns as determined in step 1
            #                         - Read values horizontally across each row to create each array

            #                         4. Merged Cells:
            #                         - When a cell spans multiple columns horizontally, repeat its value for exactly that number of columns
            #                         - Example: If "Food Prep Area" spans 2 columns, the row array should contain ["Food Prep Area", "Food Prep Area"]

            #                         5. Split Cells:
            #                         - When a cell contains multiple distinct values, combine them into a single string with appropriate delimiter
            #                         - Example: Multiple readings in one cell: "42.1°c TMV 3, 42.3°c TMV 4"

            #                         6. Table Naming:
            #                         - Combine the main table title with any section headers using ' : ' as separator
            #                         - Example: If table title is "Hot and Cold Water Distribution Outlets" and section is "Main School - Main Kitchen"
            #                             -> "Hot and Cold Water Distribution Outlets : Main School - Main Kitchen"
            #                         - If table has no section header, use just the main title or derive one from the information in the table
            #                         - Remove any trailing colons or spaces
            #                         """
            #                     },
            #                     {
            #                         "type": "text",
            #                             "text": f"""
            #                             Table: 
            #                             | Name   | Age | City       |
            #                             |--------|-----|------------|
            #                             | Alice  | 30  | New York   |
            #                             | Bob    | 25  | Los Angeles|

            #                         Correct JSON (Row-Based):
            #                         {{
            #                             "tables": {{
            #                                 "Sample Table": [
            #                                     ["Name", "Age", "City"],
            #                                     ["Alice", "30", "New York"],
            #                                     ["Bob", "25", "Los Angeles"]
            #                                 ]
            #                             }}
            #                         }}

            #                         Incorrect JSON (Column-Based):
            #                         {{
            #                             "tables": {{
            #                                 "Sample Table": [
            #                                     ["Name", "Alice", "Bob"],  
            #                                     ["Age", "30", "25"],     
            #                                     ["City", "New York", "Los Angeles"]
            #                                 ]
            #                             }}
            #                         }}


            #                         Use the golden truth text to fill in the actual values, ensuring consistent column count across all rows."""
            #                     },
            #                     {
            #                         "type": "text",
            #                         "text": f"""Here is the text extracted from the page: '''{page_text}'''. 
            #                         Below is the image of the page.
            #                         """
            #                     },
            #                     {
            #                         "type": "image_url",
            #                         "image_url": {
            #                             "url": f"data:image/png;base64,{base64_image}"
            #                         }
            #                     }
            #                 ]
            #             }
            #         ],
            #     )

            #     logger.info(f"Response: {response}")

            #     # Initialize the LogprobsHandler
            #     logprobs_handler = LogprobsHandler()
                
            #     # Process the response
            #     result_content = response.choices[0].message.content.strip()
            #     pages_results[f"Page {page_number + 1}"] = result_content
                
            #     # Convert the JSON string to DataFrame and save to Excel
            #     try:
            #         # Parse the JSON content
            #         table_data = json.loads(result_content)
                    
            #         logger.info(f"Table data: {table_data}")
                    
            #         # If the data contains tables, process each one
            #         if 'tables' in table_data:
            #             for table_name, table_content in table_data['tables'].items():
            #                 # Create DataFrame directly from the table content
            #                 df = pd.DataFrame(table_content[1:], columns=table_content[0])
                            
            #                 # Clean sheet name
            #                 sheet_name = f"P{page_number+1}_{table_name}"[:31]
            #                 sheet_name = "".join(c for c in sheet_name if c not in r'\/:*?"<>|')
                            
            #                 # Save to Excel sheet
            #                 df.to_excel(excel_writer, sheet_name=sheet_name, index=False)
                
            #     except Exception as e:
            #         logger.error(f"Error saving table to Excel for page {page_number + 1}: {e}")

            # except Exception as e:
            #     pages_results[f"Page {page_number + 1}"] = f"Error: {e}"

    # Save JSON output
    with open('lessness/output.json', 'w') as output_file:
        json.dump(pages_results, output_file, indent=4)

    pdf_document.close()

    logger.info("Finished extraction of tables from PDF")

####

# I want to write a function that goes over a JSON file. In the file are JSON representations of tables per page. Each page represents a page of a pdf. This is an example of the first page:

#     "Page 1": "```json\n{\n  \"table\": {\n    \"SITE ADDRESS\": \"Erith Road Belvedere Kent DA17 6HB\",\n    \"SCOPE OF RISK ASSESSMENT\": \"To assess the domestic hot and cold water systems and services to highlight any significant risk factors that can increase the potential for bacterial proliferation.\",\n    \"SITE CONTACT NAME\": \"Jesse Swan (Site Manager)\",\n    \"SITE TELEPHONE NUMBER\": \"01322 433290\",\n    \"DATE OF SURVEY\": \"29.10.2021\",\n    \"ARRIVAL TIME ON SITE\": \"08:30am\",\n    \"P&W WATER HYGIENE LTD RISK ASSESSOR'S NAME\": \"Lewis Barker\",\n    \"REVIEWED/CHECKED BY\": \"Joshua Pollock\",\n    \"DATE REVIEWED/CHECKED\": \"19.11.2021\",\n    \"P&W WATER HYGIENE LTD CONTACT DETAILS\": {\n      \"Telephone\": \"01634 722175\",\n      \"Address 1\": \"Innovation Centre Medway Maidstone Road Chatham Kent ME5 9FD\",\n      \"Email\": \"office@pwwaterhygieneltd.co.uk\",\n      \"Website\": \"www.pwwaterhygieneltd.co.uk\"\n    }\n  }\n}\n```",

# I want the function to make an API call to openAI like so (but without a picture, just with a text message):


# The text message should be : "The JSON Tables given below are extracted from a legionella risk report and may containinformation about water taps/assets. Carefully go over each table and make a list of all assets mentioned in the tables. For each asset, include the 'asset type' and 'location'. Make sure to include all assets, be precise. If no assets are present in the tables return 'False'.  Example of an asset JSON if this were to be mentioned: { "asset type" : "mains pipework, "location" : "boys toilet" }. The tables are:  '''{tables}'''"

# If a JSON is return, add this to a dataframe with the columns 'asset-type' and 'location'

# Once you have gone over all pages and hence all tables, give the length of the dataframe and print dataframe

# # Replace these with your actual PDF and output file paths
input_pdf_path = "Files/Lessness School - Legionella Risk Assessment - 29.10.21.pdf"
output_pdf_path = "lessness/lessness_filtered_pages.pdf"
openai.api_key = "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"


def save_azure_result(result, output_path='lessness/azure_result.pkl'):
    """
    Save Azure OCR result to a pickle file.
    """
    import pickle
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the result object
    with open(output_path, 'wb') as f:
        pickle.dump(result, f)
    
    logger.info(f"Azure OCR result saved to {output_path}")

def load_azure_result(input_path='lessness/azure_result.pkl'):
    """
    Load Azure OCR result from a pickle file.
    """
    import pickle
    
    # Load the result object
    with open(input_path, 'rb') as f:
        result = pickle.load(f)
    
    logger.info(f"Azure OCR result loaded from {input_path}")
    return result

# # 1. Scan images for tables
# extract_pages_with_tables(
#     input_pdf_path="Files/Lessness School - Legionella Risk Assessment - 29.10.21.pdf",
#     output_pdf_path="lessness/lessness_filtered_pages.pdf"
#     #openai_api_key="your_openai_api_key_here"
# )

# 2. Extract text from pages using Azure OCR or load from file
azure_result_path = 'lessness/azure_result.pkl'

if os.path.exists(azure_result_path):
    # Load existing result
    result = load_azure_result(azure_result_path)
else:
    # Generate new result
    result = extract_text_from_pdf(output_pdf_path, "https://westeurope.api.cognitive.microsoft.com/", "7614bee5e8c042439d637938ae2bb3af")
    # Save result for future use
    save_azure_result(result, azure_result_path)

# 3. Process the pages to generate JSON tables  
process_pdf_pages(output_pdf_path, result)


#TODO:
# Retrieve list of asssets from LEGIONELLA
# Match this with tables/excel
# Do search for assets in the tables/excel

