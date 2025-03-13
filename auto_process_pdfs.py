#!/usr/bin/env python3
import os
import logging
import argparse
import glob
from scripts.pdf_to_excel import ExportPDFToExcel
from scripts.excel_to_data import process_excel_file
from scripts.reshape_assets_excel import multiply_quantities
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """Create all required output directories if they don't exist."""
    base_path = './output-batch-processing'
    subdirs = [
        '1-FilteredManually',
        '2-ExportPDFToExcel',
        '3-ExcelToData',
        '4-HumanReview',
        '5-MultipliedQuantities'
    ]
    
    for subdir in subdirs:
        dir_path = os.path.join(base_path, subdir)
        os.makedirs(dir_path, exist_ok=True)
    
    # Create final output directory
    os.makedirs('./final-output', exist_ok=True)

def process_pdf(pdf_path, language='english'):
    """
    Process a single PDF file through the entire pipeline
    
    Args:
        pdf_path: Path to the PDF file
        language: Language to use for processing ('english' or 'nederlands')
        
    Returns:
        Tuple of (success, output_path) where output_path is the path to the final Excel file
    """
    try:
        # Get filename without extension to use as nickname
        file_nickname = os.path.splitext(os.path.basename(pdf_path))[0]
        logger.info(f"Processing PDF: {pdf_path} with nickname: {file_nickname}")
        
        # Copy PDF to input directory
        input_pdf_path = f'./output-batch-processing/1-FilteredManually/{file_nickname}-filtered-pages.pdf'
        shutil.copy2(pdf_path, input_pdf_path)
        logger.info(f"Copied PDF to {input_pdf_path}")
        
        # Step 2: Convert PDF to Excel
        processor = ExportPDFToExcel()
        processor.process(
            file_name=file_nickname, 
            input_path='./output-batch-processing/1-FilteredManually/', 
            output_path='./output-batch-processing/2-ExportPDFToExcel/'
        )
        logger.info(f"PDF converted to Excel successfully")
        
        # Step 3: Convert Excel to Data
        process_excel_file(
            file_name=file_nickname, 
            input_path='./output-batch-processing/2-ExportPDFToExcel/', 
            output_path='./output-batch-processing/3-ExcelToData/', 
            assets_known=True,
            language=language
        )
        logger.info(f"Excel processed to data successfully")
        
        # Step 4: Human review would normally happen here, but we'll skip it for automation
        # Copy the file to the human review folder as if it had been reviewed
        src_file = f'./output-batch-processing/3-ExcelToData/{file_nickname}-assets-data.xlsx'
        dest_file = f'./output-batch-processing/4-HumanReview/{file_nickname}-assets-data-human-review.xlsx'
        shutil.copy2(src_file, dest_file)
        logger.info(f"Copied file to human review folder (skipping actual review)")
        
        # Step 5: Multiply quantities
        multiply_quantities(
            file_name=file_nickname, 
            folder_path='./output-batch-processing/'
        )
        logger.info(f"Quantities multiplied successfully")
        
        # Copy the final output file to the final output directory
        final_output_file = f'./output-batch-processing/5-MultipliedQuantities/{file_nickname}-assets-multiplied.xlsx'
        final_destination = f'./final-output/{file_nickname}-final.xlsx'
        shutil.copy2(final_output_file, final_destination)
        logger.info(f"Final Excel file saved to: {final_destination}")
        
        return True, final_destination
    
    except Exception as e:
        logger.error(f"Error processing {pdf_path}: {str(e)}")
        return False, None

def main():
    """
    Main function to process all PDFs in a folder
    """
    parser = argparse.ArgumentParser(description='Process multiple PDF files for Legionella assessment')
    parser.add_argument('--input-folder', required=True, help='Folder containing PDF files to process')
    parser.add_argument('--language', choices=['english', 'nederlands'], default='english', 
                        help='Language to use for processing')
    args = parser.parse_args()
    
    # Ensure all necessary directories exist
    ensure_directories_exist()
    
    # Find all PDF files in the input folder
    pdf_files = glob.glob(os.path.join(args.input_folder, '*.pdf'))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {args.input_folder}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Process each PDF file
    successful = 0
    failed = 0
    output_files = []
    
    for pdf_file in pdf_files:
        success, output_path = process_pdf(pdf_file, args.language)
        if success:
            successful += 1
            output_files.append(output_path)
        else:
            failed += 1
    
    # Print summary
    logger.info("=" * 50)
    logger.info(f"Processing complete: {successful} successful, {failed} failed")
    logger.info("Output files:")
    for output_file in output_files:
        logger.info(f"  - {output_file}")
    logger.info("=" * 50)

if __name__ == "__main__":
    main() 