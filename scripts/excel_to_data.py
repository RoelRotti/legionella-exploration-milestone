import logging
import pandas as pd
import json
import os
from orq_ai_sdk import OrqAI
from dotenv import load_dotenv

load_dotenv()

orq_client = OrqAI(
    api_key=os.environ.get("ORQ_API_KEY"),
    environment="production"
)
orq_client.set_user(id=2024)


def process_excel_file(file_name, input_path='./output/2-ExportPDFToExcel/', output_path='./output/3-ExcelToData/', assets_known=False):

    check_counter = 0

    logging.info("Processing file "+file_name)

    excel_file_path = input_path+file_name+'-pdf-extract.xlsx'

    try:
        # Explicitly use only openpyxl engine
        dfs = pd.read_excel(
            excel_file_path,
            sheet_name=None,  # None means read all sheets
            engine='openpyxl'
        )
    except Exception as e:
        logging.error(f"Error reading Excel file: {str(e)}")
        raise

    df_assets = pd.DataFrame()

    # Process each sheet
    for sheet_name, df in dfs.items():
        # Save each sheet to a separate CSV file using the sheet name
        df_string = df.to_csv(index=False)  # Gets CSV string format

        # TODO : convert csv to row data: https://blog.langchain.dev/benchmarking-question-answering-over-csv-data/ https://python.langchain.com/docs/integrations/document_loaders/csv/?ref=blog.langchain.dev

        # TODO: If table < 12 rows input as one input, otherwise in batches 

        prompt_unknown_if_assets = """Below is a table extracted from an excel file in a CSV format. 
                            The table is part of a legionella risk assessment. Examine it carefully. 
                            You should extract specific data from the table if is present. The data you
                            are looking for is specific assets. Assets are water-related equipment, like taps, showers etc. but may vary from anything to dead ends for example.

                            First examine the table and see if any assets are explicitly mentioned, with explicit locations.

                            If that is the case examine the table again and extract each asset and extract the following:
                            -Asset type (like taps, showers, dead ends, anything that is water/plumbing related etc)
                            -Asset location (like Main School, etc)
                            -Asset count (like 6x, 1x etc, just put the number here)

                            Assets my have supply sources or supply to other assets, so be careful to not extract assets that are mentioned in combination with 'supply' and do not have an explicit location.
                            Ignore these 'supply' related assets. If the location seems to be an asset, it is highly probable that it is a supply related asset. 
                            Assets that are mentioned in combination with 'supply' are not assets may be ignored since these are already mentioned elsewhere.

                            Also, for each asset table be thorough in  what information to extract. 'Type of outlet' for example may be ignored if 'asset' is mentioned explicitly in the table.

                            Return the data in the following format:

                            {{ "assets" : [ {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, {{ "asset_type" : "asset_type", "asset_location  " : "asset_location", "asset_count" : "asset_count"  }}, ...] }}
                            If multiples of assets are mentioned (like (6x Toilets	Main School)) then return each asset as a separate row, like
                            {{ "assets" : [ {{ "asset_type" : "Toilets", "asset_location" : "Main School", "asset_count" : "6" }}, .... }}
                            


                            Only include assets if the asset type and location combination are explicitly mentioned. If the location in combination with the asset type is not explicitly mentioned, then ignore the asset. You cannot return an asset without a location.
                            Only give the name of the location, nothing else. Be as specific as possible about the location.
                            The location needs to be a physical location in a building. If mulitple scopes of locations are mentinioned, start with biggest scope and then combine with smaller scopes, connected with a hyphen.
                            For example: "Main School - Kitchen - Toilets"

                            For the asset count, the default value is 1, unless it is explicitly mentioned.

                            If no assets are found, return an empty list."""
        
        #TODO: add sheet name, only include sub-tables if multiple tables.
        prompt_known_if_assets = """Below is a table extracted from an excel file in a CSV format. 
                            The table is part of a legionella risk assessment. Examine it carefully. 
                            You should extract specific data from the table if is present. The data you
                            are looking for is specific assets. Assets are water/plumbing-related equipment, like taps, showers, dead ends etc.
                            The tables are selected by a human, so they are extremely likely likely to contain assets. Take this into account when examing the table
                            The tables are extracted from pages however, and one page may contain multiple tables.
                            So it could be that case that you are examining a table from a page where another table contained the assets.
                            In that case, you should not extract the assets from the table you are examining.
                            

                            First examine the table structure carefully.

                            Then extract each asset and extract the following:
                            -Asset type (like taps, showers, dead ends, anything that is water/plumbing related etc)
                            -Asset location (like Main School, etc)
                            -Asset count (like 6x, 1x etc, just put the number here)

                            Assets my have supply sources or supply to other assets, so be careful to not extract assets that are mentioned in combination with 'supply' and do not have an explicit location.
                            Ignore these 'supply' related assets. If the location seems to be an asset, it is highly probable that it is a supply related asset. 
                            Assets that are mentioned in combination with 'supply' are not assets may be ignored since these are already mentioned elsewhere.

                            Also, for each asset table be thorough in  what information to extract. 'Type of outlet' for example may be ignored if 'asset' is mentioned explicitly in the table.

                            Return the data in the following format:

                            {{ "assets" : [ {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, {{ "asset_type" : "asset_type", "asset_location  " : "asset_location", "asset_count" : "asset_count"  }}, ...] }}
                            If multiples of assets are mentioned (like (6x Toilets	Main School)) then return each asset as a separate row, like
                            {{ "assets" : [ {{ "asset_type" : "Toilets", "asset_location" : "Main School", "asset_count" : "6" }}, .... }}
                            


                            Only include assets if the asset type and location combination are explicitly mentioned. If the location in combination with the asset type is not explicitly mentioned, then ignore the asset. You cannot return an asset without a location.
                            Only give the name of the location, nothing else. Be as specific as possible about the location.
                            The location needs to be a physical location in a building. If mulitple scopes of locations are mentinioned, start with biggest scope and then combine with smaller scopes, connected with a hyphen.
                            For example: "Main School - Kitchen - Toilets"

                            For the asset count, the default value is 1, unless it is explicitly mentioned."""

        # Two different prompts, one for known assets, one for unknown assets
        if assets_known:
            prompt_assets = prompt_known_if_assets
        else:
            prompt_assets = prompt_unknown_if_assets

        prompt = f"""{prompt_assets}
                            An asset can be any of the following (or a variation thereof) : Above Ground Grease Separator
    Alternative techniques
    Anodic oxidation
    Asset Register
    Au bain marie
    Autoclave
    Automatic CV degasser
    Automatic filling unit
    Automatic flush valve
    Automatic flushing device
    Automatic solenoid
    Automatic sprinkler system
    Backwash filter
    Balancing valve
    Bar tap
    Baseboard integrated heater
    Basket strainer
    Bath mixer
    Bath thermostatic mixer
    Bath/shower combination mixer
    Bath/shower combination thermostatic mixer
    Bedpan washer
    Beer tap installation with tank cleaning installation
    Bib tap
    Bidet
    Bleed solenoid valve
    Blending valve
    Blowdown valve
    Boiling kettle
    Boiling water heater
    Boiling water tap
    Boot cleaner
    Borewell
    Breaktank
    Brominator
    Buffer vessel
    Buffer vessel with heater
    Buffer vessel with hot and cold storage
    Buffer vessel with plate heat exchanger
    Butler sink
    Bypass (cold water)
    Calorifier
    Canister demineralised water
    Chemical dosing pump
    Chemical dosing unit
    Chemical stock tank
    Chemical toilet
    Chemical water treatment
    Chilled water dispenser
    Chiller
    Coffee machine
    Cold water storage tank
    Combi boiler
    Combi steamer
    Combi water heater
    Condenser bleed tank
    Condenser pump
    Condenser pump strainer
    Conductivity meter
    config.components.Flexibletapconnector.name
    config.components.ldtestcoolingtowerdefault.name
    Cooling tower
    Cooling tower drain
    Copper-silver ionisation
    Crushed ice machine
    Cyclone
    Dead end (drinking water)
    Dead end (hot water)
    Deadleg
    Degasser
    Demineralised water
    Dental chair
    Direct gas fired heater
    Dishwasher
    Dosing pump
    Drain
    Drain valve
    Drift eliminator
    Drinking bowl
    Drinking water circulation pump
    Drinks Dispenser
    Duplicate pump set
    Electric shower
    Electric water heater
    Emergency eye wash
    Emergency eye wash & shower
    Emergency shower
    Evaporative condenser
    Expansion Automats
    Expansion vessel
    Fan
    Fill pack
    Filling loop tap
    Filling loop tap > 45kW
    Fine filter
    Fire
    Fire fighting system
    Fire hose reel
    Firehydrant
    Foot washbasin
    Fountain tap
    Fumehood
    Gas water heater
    Glass rinser
    Glass Rinser (Beer)
    Grease Separator Sludge Separator
    Hairdresser shower
    Hand shower
    Hand washbasin
    Heat Exchange Coils
    Heat pump
    Heating boiler
    Height adjustable bath
    High pressure cleaner
    High pressure cleaner
    Hose tap
    Hose Union Bib Tap
    Hot drinks machine
    Hot Water Circulation Pump
    Humidifier
    Ice cream dipper well
    Ice machine
    Ice maker
    Incoming mains
    Incubator
    Indirect fired heater
    Indirect fired heater with heater
    Indirect fired heater with hot and cold storage
    Indirect fired heater with plate heat exchanger
    Indirect fired heater with solar thermal collectors
    Industrial dishwasher
    Industrial washing machine
    Inline strainer
    Instantaneous water heater
    Instantaneous water heater (tankless)
    Intermediate meter
    Intermediate valve
    Intermediate water meter
    Kitchen spray outlet
    Kitchen tap
    Kitchen tap thermostatic
    Knee wash basin
    Laboratory mixer tap
    Laboratory tap
    Legionella Filter
    Level Signaler
    Low pressure mixer
    Main valve
    Make-up tank
    Manual Quick Fill
    Micro thermostatic mixer
    Micron filter
    Milk Frother
    Mixer tap
    Mixer valve
    Multifunctional (smart) faucet
    Open well
    Other - Air conditioning system
    Other - Industrial process water system
    Other - Spa/Pool/Jacuzzi
    Other - Water feature
    Outlet
    Outlet connection
    Oven spray
    Over Sink Heater
    Ozone generator
    pH meter
    Pipework
    Plate heat exchanger with heater
    Plate heat exchanger with hot and cold storage
    Plate heat exchanger with solar thermal collectors
    Plate heat exchanger without buffer vessel
    Point of use water heater
    Pool fill/supplement
    Post-mix installation
    Pre-rinse/wash spray tap
    Pressure booster with pressure vessel
    Pressure booster with pressureless reservoir
    Pressure booster with switch vessel
    Pressure booster with switch vessel and variable rotation-frequency
    Pressure booster without switch vessel and variable rotation-frequency
    Pressure regulating valve
    Pressurisation units for closed systems
    Principal return loop
    Process water
    Public drinking water outlet
    Quooker
    Rain water harvesting system
    Rain water harvesting tank
    Reduced Pressure Zone Valve
    Return pipe
    Reverse osmosis
    Roasting pan
    Sample point
    Sand filter
    Scale inhibitor
    Secondary Return Loop
    Sensor Outlet
    Separated fire hose reel installation
    Shower
    Shower mixer
    Shower mixer thermostatic
    Shower panel
    Sink
    Sink (thermostatic)
    Sink with knee operation
    Slop hopper
    Sludge Separator
    Soap Dispenser
    Soup machine
    Spray reel
    Sprinkler
    Stabilized Aqueous Ozone Generator
    Star tap
    Steamer
    Subordinate return loop
    Sump circulation pump
    Tap
    TapApplianceType.Bath
    TapApplianceType.SprayOutlet
    Tea point
    Terrain Pipe
    Tertiary Return Loop
    Thermostatic mixer valve
    Thermostatic mixing tap
    Toilet
    Ultrafiltration
    Under rinse tap
    Under Sink Heater
    Underground Grease Separator
    Underground water storage tank
    Urinal
    Utility sink
    UV light
    Valve
    Veg Prep Sink
    Wall Mounted Breaktank
    Washbasin
    Washbasin mixer
    Washbasin mixer thermostatic
    Washing machine
    Washing through
    Water booster
    Water booster - Double pump set
    Water booster - Quadruple pump set
    Water booster - Single pump set
    Water booster - Triple pump set
    Water cooler
    Water distribution system
    Water filter
    Water heater
    Water heaters
    Water Meter
    Water softener
    Water source
    Water treatment

    This is the CSV table:

    {df_string}         

    If there are empty values in the CSV this could also be due to formerly merged/split cells, as this CSV was extracted from an Excel file. 

    ONLY RETURN THE JSON, DO NOT RETURN ANYTHING ELSE.              """
                        

        # Cost: 0.001 
        response = orq_client.deployments.invoke(
            key="legionella-table-extraction-v2",
            context={
                "environments": []
            },
            metadata={
                "page-number": sheet_name
            }, 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt},
                    ],
                }
            ],
        )

        result_content = response.choices[0].message.content.strip()
        #print(result_content)
        
        # Parse the JSON response
        try:
            data = json.loads(result_content)
            assetsGPT = data.get("assets", [])
        except json.JSONDecodeError as e:
            print(f"JSON decoding failed with GPT: {e}")
            assetsGPT = []

        #if assetsGPT:

        # Repeat with Sonnet 3.5
        response = orq_client.deployments.invoke(
            key="legionella-table-extraction-v2",
            context={
                "environments": [],
                "model_choice": [
                    "sonnet"
                ]

            },
            metadata={
                "page-number": sheet_name
            }, 
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt},
                    ],
                }
            ],
        )

        result_content = response.choices[0].message.content.strip()
        # Parse the JSON response
        try:
            data = json.loads(result_content)
            assetsSonnet = data.get("assets", [])

            # Check if total assets and total number of assets are the same
            total_assets_gpt = sum(int(asset["asset_count"]) for asset in assetsGPT)
            total_assets_sonnet = sum(int(asset["asset_count"]) for asset in assetsSonnet)
            if len(assetsGPT) == len(assetsSonnet) and total_assets_gpt == total_assets_sonnet:
                flag = ""
            else:
                flag = "Check"

            print(flag)

            if flag == "Check":
                check_counter += 1

            # # Check if results are the same
            # # Check in here because Sonnet cannot adhere to JSON Schema
            # response = orq_client.deployments.invoke(
            #     key="legionella-table-extraction-v2",
            #     context={
            #         "environments": [],
            #         "model_choice": [
            #             "4oCompare"
            #         ]

            #     },
            #     metadata={
            #         "page-number": sheet_name
            #     }, 
            #     messages=[
            #         {
            #             "role": "user",
            #             "content": [
            #                 {
            #                     "type": "text",
            #                     "text": f"""Below are two lists of assets. They are both structured like:
                                
            #                     {{ "assets" : [ {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, {{ "asset_type" : "asset_type", "asset_location  " : "asset_location", "asset_count" : "asset_count"  }}, ...] }}
            #                     If multiples of assets are mentioned (like (6x Toilets	Main School)) then return each asset as a separate row, like
            #                     {{ "assets" : [ {{ "asset_type" : "Toilets", "asset_location" : "Main School", "asset_count" : "6" }}, .... }} 
                                
            #                     Compare the two lists and determine if they are the same. The order does not matter. If the naming is slightly different,
            #                     it is also not a problem. Most important is that the number of assets are the same.

            #                     List 1: 
            #                     {assetsGPT}

            #                     List 2: 
            #                     {assetsSonnet}

            #                     If the lists are the same, return True. If they are not the same, return False. Do not reply with anything else.
            #                     """},
            #             ],
            #         }
            #     ],
            # )

            # result_content = response.choices[0].message.content.strip()
            # print(result_content)
            # if result_content == "True":
            #     flag = ""
            # else:
            #     flag = "Check"
            # Create the output directory if it doesn't exist


            # Create the output directory if it doesn't exist
            output_dir = output_path
            os.makedirs(output_dir, exist_ok=True)

            # Special case: If assetsSonnet is empty and assetsGPT is not empty, then still make a row 
            # with flag = "Check". Sonnet is better than 4o-mini, but we want to manually check
            if (len(assetsSonnet) == 0) & (len(assetsGPT) > 0):
                new_row = pd.DataFrame({
                        'asset_type': [""],
                        'asset_location': [""],
                        'asset_count': [""],
                        'sheet_name': [sheet_name],
                        'flag': ["Sonnet assumed no assets, GPT did assume assets"]
                })
                df_assets = pd.concat([df_assets, new_row], ignore_index=True)
            
            else: 
                # Convert assets list to DataFrame
                for asset in assetsSonnet:
                    #for asset_type, asset_location in asset.items():
                    asset_type_ = asset["asset_type"]
                    asset_location_ = asset["asset_location"]
                    asset_count_ = asset["asset_count"]
                    flag_ = flag
                    new_row = pd.DataFrame({
                        'asset_count': [asset_count_],
                        'asset_type': [asset_type_],
                        'asset_location': [asset_location_],
                        'sheet_name': [sheet_name],
                        'flag': [flag_]
                    })
                    df_assets = pd.concat([df_assets, new_row], ignore_index=True)

            # Don't go on to registering GPT's assets
            continue


        except json.JSONDecodeError as e:
            print(f"JSON decoding failed with Sonnet 3.5: {e}")
            assetsSonnet = []
            flag = "Check, Sonnet failed"

        # TODO: also include LLama

    #print(result_content)

    
        # Create the output directory if it doesn't exist
        output_dir = output_path
        os.makedirs(output_dir, exist_ok=True)

        # Convert assets list to DataFrame
        for asset in assetsGPT:
            #for asset_type, asset_location in asset.items():
            asset_type_ = asset["asset_type"]
            asset_location_ = asset["asset_location"]
            asset_count_ = asset["asset_count"]
            flag_ = flag
            new_row = pd.DataFrame({
                'asset_count': [asset_count_],
                'asset_type': [asset_type_],
                'asset_location': [asset_location_],
                'sheet_name': [sheet_name],
                'flag': [flag_]
            })
            df_assets = pd.concat([df_assets, new_row], ignore_index=True)

    logging.info(f'Number of checks: {check_counter}')
    logging.info(f'Number of assets: {len(df_assets)}')

    # Save in output/3-ExcelToData
    df_assets.to_excel(os.path.join(output_dir, f"{file_name}-assets-data.xlsx"), index=False)

    # Save in output/4-HumanReview

    # Extract first folder from output_path and merge with human review folder
    base_output_folder = output_path.split('/')[1]
    human_review_path = os.path.join(base_output_folder, "4-HumanReview")
    os.makedirs(human_review_path, exist_ok=True)

    # Add columns for human review
    df_assets['delete'] = ''
    df_assets['sonnet_wrong'] = ''
    df_assets['row_added'] = ''

    logging.info(f"Saving human review file to {human_review_path}")
    
    df_assets.to_excel(os.path.join(human_review_path, f"{file_name}-assets-data-human-review.xlsx"), index=False)


#process_excel_file(file_name = 'llesness') #excel_file_path = 'output/ExportPDFToExcel/split_output.xlsx')

