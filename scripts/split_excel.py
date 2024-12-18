# Start Generation Here
import pandas as pd

excel_file_path = 'output/ExportPDFToExcel/merged_output.xlsx'
output_file_path = 'output/ExportPDFToExcel/split_output.xlsx'

excel_file = pd.ExcelFile(excel_file_path)

with pd.ExcelWriter(output_file_path, engine='xlsxwriter') as writer:
    for sheet_name in excel_file.sheet_names:
        df = excel_file.parse(sheet_name)
        
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
                
                new_sheet_name = f"{sheet_name}_table_{table_counter}"
                sub_df.to_excel(writer, sheet_name=new_sheet_name, index=False)
                table_counter += 1  # Only increment when we actually write a table
        else:
            # If no empty rows, save the entire dataframe as one sheet
            df.to_excel(writer, sheet_name=sheet_name, index=False)
