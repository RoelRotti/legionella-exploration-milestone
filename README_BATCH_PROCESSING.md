# Batch Processing for Legionella PDFs

This folder contains scripts to automatically process multiple Legionella PDF files and generate Excel outputs.

## Requirements

- Make sure you have all the required dependencies installed from `requirements.txt`
- Ensure that all environment variables are set up correctly (PDF_SERVICES_CLIENT_ID, PDF_SERVICES_CLIENT_SECRET, ORQ_API_KEY)

## Scripts

1. `auto_process_pdfs.py` - Main Python script that processes PDFs
2. `run_batch_process.sh` - Shell script to easily run the batch processing

## How to Use

### Step 1: Prepare Your PDFs

Place all your PDF files (up to 10 or more) in a folder. For example:
```
mkdir -p ~/Documents/legionella_pdfs
# Copy your PDFs to this folder
```

### Step 2: Run the Batch Processing Script

Run the shell script with the path to your PDF folder:

```bash
./run_batch_process.sh ~/Documents/legionella_pdfs
```

By default, the script uses English for processing. If you want to use Dutch:

```bash
./run_batch_process.sh ~/Documents/legionella_pdfs nederlands
```

### Step 3: Find Your Results

After processing, all generated Excel files will be in the `final-output` folder:

```bash
ls -la ./final-output
```

## Output Structure

The script creates the following folder structure:

```
output-batch-processing/
├── 1-FilteredManually/
├── 2-ExportPDFToExcel/
├── 3-ExcelToData/
├── 4-HumanReview/
└── 5-MultipliedQuantities/

final-output/  # Final Excel files are here
```

## Important Notes

1. This script skips the manual human review step that would normally be part of the workflow
2. If you want to process new PDFs, the old results will remain in the output folders
3. For larger PDF files, processing may take some time

## Troubleshooting

Check the console output for detailed error messages and logs. Common issues include:

1. Missing environment variables
2. PDF files that don't contain the expected asset data
3. Permissions issues with writing to the output folders

If you encounter persistent issues, review the log messages and ensure your PDF files are in a supported format. 