import pandas as pd
import os
from difflib import SequenceMatcher

def normalize_string(s):
    return s.strip().lower()

def string_similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def compare_excel_files(golden_file_path, created_file_name, folder_path='./output'):
    # Read the excel files
    golden_df = pd.read_excel(golden_file_path, header=0)
    created_file_path = f'{folder_path}/5-MultipliedQuantities/{created_file_name}-assets-multiplied.xlsx'
    created_df = pd.read_excel(created_file_path, header=0)
    
    # Create copies with standardized column names for comparison
    golden_compare = golden_df[['Asset Type', '*Room']].copy()
    golden_compare.columns = ['asset_type', 'asset_location']
    
    created_compare = created_df[['asset_type', 'asset_location']].copy()
    
    # Ensure columns are strings
    created_compare['asset_type'] = created_compare['asset_type'].astype(str)
    created_compare['asset_location'] = created_compare['asset_location'].astype(str)
    golden_compare['asset_type'] = golden_compare['asset_type'].astype(str)
    golden_compare['asset_location'] = golden_compare['asset_location'].astype(str)

    # Normalize data
    created_compare['asset_type'] = created_compare['asset_type'].apply(normalize_string)
    created_compare['asset_location'] = created_compare['asset_location'].apply(normalize_string)
    golden_compare['asset_type'] = golden_compare['asset_type'].apply(normalize_string)
    golden_compare['asset_location'] = golden_compare['asset_location'].apply(normalize_string)

    # Instead of merge, we'll use word-by-word comparison
    missing_in_created = golden_compare.copy()
    extra_in_created = created_compare.copy()
    
    # Indices to drop
    golden_indices_to_drop = []
    created_indices_to_drop = []
    
    # Compare each row in golden with all rows in created
    for golden_idx, golden_row in missing_in_created.iterrows():
        for created_idx, created_row in extra_in_created.iterrows():

            # Needed since there are a lot of duplicates
            if created_idx in created_indices_to_drop:
                continue
            
            # Split strings into words
            golden_type_words = set(golden_row['asset_type'].split())
            golden_location_cleaned = golden_row['asset_location'].replace('/', ' ').replace('-', ' ').replace('  ', ' ')
            created_type_words = set(created_row['asset_type'].split())
            created_location_cleaned = created_row['asset_location'].replace('/', ' ').replace('-', ' ').replace('  ', ' ')
            
            # Split cleaned strings into words
            golden_location_words = set(golden_location_cleaned.split())
            created_location_words = set(created_location_cleaned.split())
            
            # Check if all separate words in asset_type are substrings of any strings in the other DataFrame
            type_match = all(word in created_row['asset_type'] for word in golden_type_words) or \
                         all(word in golden_row['asset_type'] for word in created_type_words)
            
            # Check if all separate words in asset_location are substrings of any strings in the other DataFrame
            location_match = all(word in created_location_cleaned for word in golden_location_words) or \
                             all(word in golden_location_cleaned for word in created_location_words)
            
            # If both type and location match
            if type_match and location_match:
                # Debugging output
                print(f"Match found: Golden Index {golden_idx} with Created Index {created_idx}")
                print(f"Golden: {golden_row['asset_type']} - {golden_row['asset_location']}")
                print(f"Created: {created_row['asset_type']} - {created_row['asset_location']}\n")
                
                # Mark these indices for removal
                golden_indices_to_drop.append(golden_idx)
                created_indices_to_drop.append(created_idx)
                break

    print(f"length of golden_indices_to_drop: {len(golden_indices_to_drop)}")
    print(f"length of created_indices_to_drop: {len(created_indices_to_drop)}")

    print(f"length of golden_compare: {len(golden_compare)}")
    print(f"length of created_compare: {len(created_compare)}")
    
    # Remove matched rows from both DataFrames
    missing_in_created = missing_in_created.drop(golden_indices_to_drop)
    extra_in_created = extra_in_created.drop(created_indices_to_drop)
    print(f'created_indices_to_drop: {len(set(created_indices_to_drop))}')

    print(f"length of missing_in_created: {len(missing_in_created)}")
    print(f"length of extra_in_created: {len(extra_in_created)}")
    
    # Calculate match percentage
    total_golden_records = len(golden_compare)
    matching_records = total_golden_records - len(missing_in_created)
    match_percentage = (matching_records / total_golden_records) * 100 if total_golden_records > 0 else 0
    
    # Add match percentage as a single value in asset_type column
    missing_in_created.loc[len(missing_in_created), 'asset_type'] = f'Match Percentage: {match_percentage:.2f}%'
    extra_in_created.loc[len(extra_in_created), 'asset_type'] = f'Match Percentage: {match_percentage:.2f}%'
    
    # Save the results to Excel files
    missing_in_created.to_excel(f'{folder_path}/6-CompareGoldenOutput/{created_file_name}-missing-in-created.xlsx', index=False)
    extra_in_created.to_excel(f'{folder_path}/6-CompareGoldenOutput/{created_file_name}-extra-in-created.xlsx', index=False)
    
    print("\nRecords in golden file but missing from created file:")
    print(missing_in_created if not missing_in_created.empty else "None")
    
    print("\nExtra records in created file that don't exist in golden file:")
    print(extra_in_created if not extra_in_created.empty else "None")
    
    # Calculate match percentage
    total_golden_records = len(golden_compare)
    matching_records = total_golden_records - len(missing_in_created)
    match_percentage = (matching_records / total_golden_records) * 100 if total_golden_records > 0 else 0
    
    print(f"\nMatch percentage: {match_percentage:.2f}%")

    # return {
    #     'missing_records': missing_in_created,
    #     'extra_records': extra_in_created,
    #     'match_percentage': match_percentage
    # }
#compare_excel_files(golden_file_path = './output/6-GoldenOutput/Lessness Primary School.xlsx', created_file_name = 'llesness')