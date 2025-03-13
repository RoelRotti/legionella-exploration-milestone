#!/bin/bash

# make script executable
chmod +x auto_process_pdfs.py

# Check if the input folder is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-pdf-folder> [language]"
    echo "  language: english (default) or nederlands"
    exit 1
fi

# Check if the folder exists
if [ ! -d "$1" ]; then
    echo "Error: Folder '$1' does not exist"
    exit 1
fi

# Set the language (default to english if not provided)
LANGUAGE=${2:-english}

echo "Starting batch processing of PDFs in folder: $1"
echo "Using language: $LANGUAGE"

# Run the Python script
./auto_process_pdfs.py --input-folder "$1" --language "$LANGUAGE"

# Check if processing was successful
if [ $? -eq 0 ]; then
    echo "Processing completed. Results are in the 'final-output' folder."
    
    # Count the number of Excel files in the output folder
    excel_count=$(find ./final-output -name "*.xlsx" | wc -l)
    echo "Generated $excel_count Excel files."
    
    # List the files
    echo "Generated files:"
    ls -la ./final-output
else
    echo "Processing failed."
fi 