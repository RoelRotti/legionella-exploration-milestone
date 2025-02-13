# Legionella Overview Processing App

A Streamlit-based application designed to process and analyze Legionella Overview documents, converting PDF/Excel inputs into structured asset data with human verification capabilities.

## Overview

This application streamlines the process of extracting asset information from Legionella Overview documents through a three-phase workflow:
- Phase A: PDF/Excel to structured data conversion
- Phase B: Data processing and quantity multiplication
- Phase C: Golden data comparison (optional)

## Installation

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
streamlit run legionella-overview-human-selection.py
```

## Data Flow

The application uses several Python scripts located in the `scripts/` directory to process the data through multiple phases:

### Phase A: PDF to Excel Conversion

1. **Input**:
   - PDF file containing asset tables OR
   - Excel file with pre-extracted tables
   - File nickname (e.g., 'parkwood')
   - Language selection (English/Nederlands)

2. **Processing Scripts**:
   
   a. **PDF Processing** (`scripts/pdf_to_excel.py`):
   - Class: `ExportPDFToExcel`
   - Functionality:
     - Reads PDF files using PDF extraction libraries
     - Identifies and extracts tables from PDF pages
     - Converts table data to structured Excel format
     - Handles multi-page documents and table splitting
   - Output: Excel file with tables in separate sheets

   b. **Excel Processing** (`scripts/excel_to_data.py`):
   - Function: `process_excel_file`
   - Functionality:
     - Splits large tables into manageable chunks (15 rows max)
     - Preserves table headers across splits
     - Handles data validation and cleaning
     - Adds tracking columns for human review
   - Output: Structured Excel file ready for human review

3. **Data Structure**:
   The processed Excel file contains the following columns:
   - Asset identification fields
   - Quantity information
   - Verification flags:
     - 'Check' flags for uncertain entries
     - 'sonnet_wrong' for marking incorrect predictions
     - 'delete' for marking rows to remove
     - 'row_added' for tracking new entries

### Phase B: Excel Data Processing

1. **Human Review Process**:
   The application provides a structured workflow for reviewing and modifying the data:
   
   a. **Review Steps**:
   - Review entries flagged with 'Check'
   - Verify Sonnet model predictions
   - Add missing assets
   - Remove incorrect entries
   - Validate quantity information

   b. **Tracking Modifications**:
   - Mark incorrect Sonnet predictions (sonnet_wrong = 1)
   - Flag rows for deletion (delete = 1)
   - Mark newly added rows (row_added = 1)
   - Document asset assumption changes

2. **Quantity Processing** (`scripts/reshape_assets_excel.py`):
   - Function: `multiply_quantities`
   - Functionality:
     - Processes the reviewed Excel file
     - Applies quantity calculations based on asset types
     - Handles unit conversions if necessary
     - Validates calculation results
   - Output: Final Excel file with processed quantities

### Phase C: Golden Data Comparison (Optional)

1. **Comparison Processing** (`scripts/compare_excels.py`):
   - Function: `compare_excel_files`
   - Functionality:
     - Compares processed data against golden dataset
     - Identifies missing entries
     - Highlights discrepancies
     - Generates comparison reports
   - Outputs:
     - Extra entries report
     - Missing entries report
     - Discrepancy summary

### Script Dependencies and Structure

```
scripts/
├── pdf_to_excel.py          # PDF extraction and conversion
├── excel_to_data.py         # Data structuring and validation
├── reshape_assets_excel.py  # Quantity processing
└── compare_excels.py        # Golden data comparison
```

Each script is designed to be:
- Modular and independent
- Configurable through parameters
- Error-handled with detailed logging
- Integrated with the Streamlit interface

### Data Flow Diagram

```
[PDF/Excel Input] → [Phase A] → [Human Review] → [Phase B] → [Phase C (Optional)]
     ↓                 ↓            ↓              ↓             ↓
   Raw Data → Structured Tables → Verified Data → Processed → Comparison
                                                  Quantities    Reports
```

## Features

- Supports both PDF and Excel inputs
- Automatic table detection and extraction
- Human verification workflow
- Quantity multiplication
- Bilingual support (English/Nederlands)
- Session state management for multi-phase processing
- Downloadable outputs at each phase

## Error Handling

- Validates file uploads
- Provides clear error messages
- Maintains processing state
- Allows process reset at each phase

## Best Practices

1. **File Naming**:
   - Use descriptive nicknames for files
   - Maintain consistent naming across phases

2. **Data Verification**:
   - Always review flagged entries
   - Verify quantity calculations
   - Document any manual changes

3. **Processing**:
   - Complete each phase sequentially
   - Download and backup outputs regularly
   - Verify data integrity between phases

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## CI/CD

This project uses GitHub Actions for continuous integration and deployment. The workflow is configured to automatically build and push a Docker image to Azure Container Registry (ACR) whenever changes are pushed to the main branch.

### GitHub Workflow

The workflow (`.github/workflows/docker-build-push.yml`) performs the following steps:
1. Checks out the code
2. Logs in to Azure Container Registry
3. Builds the Docker image
4. Pushes the image to ACR with the `latest` tag

The Docker image is stored at `ldstreamlitapp.azurecr.io/streamlit-app:latest`.

The image should be updated, but for deploying as webapp this can easiest be done directly from the ACR

## License

This project is licensed under the MIT License - see the LICENSE.md file for details 