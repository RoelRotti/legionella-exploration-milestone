import pandas as pd
import os   

def multiply_quantities(file_name):
    # Read the input Excel file from HumanReview folder
    input_file = f'./output/4-HumanReview/{file_name}-assets-data-human-review.xlsx'
    df = pd.read_excel(input_file, header=0)
    print("Columns:", df.columns.tolist())
    
    # Convert delete column to integers if it exists, replacing NaN with 0
    if 'delete' in df.columns:
        print("Delete exists")
        df['delete'] = pd.to_numeric(df['delete'], errors='coerce').fillna(0).astype(int)
        df = df[df['delete'] != 1]
    
    # Create empty DataFrame for the expanded rows
    expanded_df = pd.DataFrame(columns=['asset_type', 'asset_location', 'sheet_name'])
    
    # Iterate through each row
    for _, row in df.iterrows():
        # Skip if asset_type is empty or asset_count is empty
        if pd.isna(row['asset_type']) or pd.isna(row['asset_count']):
            continue
            
        # Convert asset_count to integer, default to 1 if not a valid number
        try:
            count = int(float(row['asset_count']))
            if count <= 0:  # Skip if count is 0 or negative
                continue
        except (ValueError, TypeError):
            continue  # Skip if conversion fails
            
        # Create count number of duplicates
        for _ in range(count):
            new_row = pd.DataFrame({
                'asset_type': [row['asset_type']],
                'asset_location': [row['asset_location']], 
                'sheet_name': [row['sheet_name']]
            })
            expanded_df = pd.concat([expanded_df, new_row], ignore_index=True)

    
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join("output", "5-MultipliedQuantities") 
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the expanded DataFrame
    output_file = os.path.join(output_dir, f"{file_name}-assets-multiplied.xlsx")
    expanded_df.to_excel(output_file, index=False)

    print("Expanded DataFrame saved to:", output_file)
    
    # return expanded_df