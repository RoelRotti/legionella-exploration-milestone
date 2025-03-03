import logging
import pandas as pd
import json
import os
from orq_ai_sdk import Orq
from dotenv import load_dotenv
import streamlit as st
import openpyxl  # Explicitly import openpyxl

load_dotenv()

# Initialize the Orq client using environment variable directly
orq_api_key = os.environ.get("ORQ_API_KEY")
if not orq_api_key:
    logging.error("ORQ API key is missing from environment variables")
    raise ValueError("ORQ_API_KEY must be set in environment variables")

orq_client = Orq(api_key=orq_api_key)

def process_excel_file(file_name, input_path='./output/2-ExportPDFToExcel/', output_path='./output/3-ExcelToData/', assets_known=False, language='english'):

    check_counter = 0

    logging.info("Processing file "+file_name)

    excel_file_path = input_path+file_name+'-pdf-extract.xlsx'

    try:
        # Directly use openpyxl to read the workbook
        logging.info(f"Reading Excel file: {excel_file_path}")
        workbook = openpyxl.load_workbook(excel_file_path, read_only=True)
        
        # Create a dictionary to store DataFrames for each sheet
        dfs = {}
        
        # Process each sheet
        for sheet_name in workbook.sheetnames:
            worksheet = workbook[sheet_name]
            
            # Get data from worksheet
            data = []
            for row in worksheet.rows:
                data.append([cell.value for cell in row])
            
            # Convert data to DataFrame
            if data:
                # Use first row as header
                headers = data[0]
                if data[1:]:
                    df = pd.DataFrame(data[1:], columns=headers)
                    dfs[sheet_name] = df
        
        logging.info(f"Successfully read {len(dfs)} sheets from Excel file")
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
        
        prompt_unknown_if_assets_nederlands = """Hieronder staat een tabel geëxtraheerd uit een Excel bestand in CSV formaat.
                            De tabel is onderdeel van een legionella risicobeoordeling. Onderzoek deze zorgvuldig.
                            Je moet specifieke data uit de tabel halen indien aanwezig. De data waar je
                            naar zoekt zijn specifieke assets. Assets zijn watergerelateerde apparatuur, zoals kranen, douches etc. maar kunnen variëren van alles tot doodlopende leidingen bijvoorbeeld.

                            Onderzoek eerst de tabel en kijk of er expliciet assets worden genoemd, met expliciete locaties.

                            Als dat het geval is, onderzoek de tabel nogmaals en haal voor elk asset de volgende informatie eruit:
                            -Asset type (zoals kranen, douches, doodlopende leidingen, alles wat water/loodgieterswerk gerelateerd is etc)
                            -Asset locatie (zoals Hoofdschool, etc)
                            -Asset aantal (zoals 6x, 1x etc, zet hier alleen het nummer)

                            Assets kunnen voedingsbronnen hebben of andere assets voeden, dus wees voorzichtig met assets die genoemd worden in combinatie met 'toevoer' en geen expliciete locatie hebben.
                            Negeer deze 'toevoer' gerelateerde assets. Als de locatie een asset lijkt te zijn, is het zeer waarschijnlijk dat het een toevoer gerelateerde asset is.
                            Assets die genoemd worden in combinatie met 'toevoer' zijn geen assets en mogen genegeerd worden aangezien deze al elders genoemd zijn.

                            Wees ook voor elke asset tabel grondig in welke informatie je extraheert. 'Type tappunt' bijvoorbeeld mag genegeerd worden als 'asset' expliciet genoemd wordt in de tabel.

                            Retourneer de data in het volgende formaat:

                            {{ "assets" : [ {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, ...] }}
                            Als er meerdere assets genoemd worden (zoals (6x Toiletten Hoofdschool)) retourneer dan elk asset als een aparte rij, zoals
                            {{ "assets" : [ {{ "asset_type" : "Toiletten", "asset_location" : "Hoofdschool", "asset_count" : "6" }}, .... }}

                            Neem alleen assets op als de combinatie van asset type en locatie expliciet genoemd wordt. Als de locatie in combinatie met het asset type niet expliciet genoemd wordt, negeer dan het asset. Je kunt geen asset retourneren zonder locatie.
                            Geef alleen de naam van de locatie, niets anders. Wees zo specifiek mogelijk over de locatie.
                            De locatie moet een fysieke locatie in een gebouw zijn. Als er meerdere niveaus van locaties genoemd worden, begin dan met het grootste niveau en combineer met kleinere niveaus, verbonden met een koppelteken.
                            Bijvoorbeeld: "Hoofdschool - Keuken - Toiletten"

                            Voor het asset aantal is de standaardwaarde 1, tenzij het expliciet anders genoemd wordt.

                            Als er geen assets gevonden worden, retourneer dan een lege lijst."""
        
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


        prompt_known_if_assets_nederlands = """Hieronder staat een tabel geëxtraheerd uit een Excel bestand in CSV formaat.
                            De tabel is onderdeel van een legionella risicobeoordeling. Onderzoek deze zorgvuldig.
                            Je moet specifieke data uit de tabel halen indien aanwezig. De data waar je
                            naar zoekt zijn specifieke assets. Assets zijn watergerelateerde apparatuur, zoals kranen, douches, doodlopende leidingen etc.
                            De tabellen zijn geselecteerd door een mens, dus het is zeer waarschijnlijk dat ze assets bevatten. Houd hier rekening mee bij het onderzoeken van de tabel.
                            De tabellen zijn echter geëxtraheerd uit pagina's, en één pagina kan meerdere tabellen bevatten.
                            Het zou dus kunnen dat je een tabel onderzoekt van een pagina waar een andere tabel de assets bevatte.
                            In dat geval moet je geen assets extraheren uit de tabel die je onderzoekt.

                            Onderzoek eerst de tabelstructuur zorgvuldig.

                            Extraheer vervolgens voor elk asset de volgende informatie:
                            -Asset type (zoals kranen, douches, doodlopende leidingen, alles wat water/loodgieterswerk gerelateerd is etc)
                            -Asset locatie (zoals Hoofdschool, etc)
                            -Asset aantal (zoals 6x, 1x etc, zet hier alleen het nummer)

                            Assets kunnen voedingsbronnen hebben of andere assets voeden, dus wees voorzichtig met assets die genoemd worden in combinatie met 'toevoer' en geen expliciete locatie hebben.
                            Negeer deze 'toevoer' gerelateerde assets. Als de locatie een asset lijkt te zijn, is het zeer waarschijnlijk dat het een toevoer gerelateerde asset is.
                            Assets die genoemd worden in combinatie met 'toevoer' zijn geen assets en mogen genegeerd worden aangezien deze al elders genoemd zijn.

                            Wees ook voor elke asset tabel grondig in welke informatie je extraheert. 'Type tappunt' bijvoorbeeld mag genegeerd worden als 'asset' expliciet genoemd wordt in de tabel.

                            Retourneer de data in het volgende formaat:

                            {{ "assets" : [ {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, {{ "asset_type" : "asset_type", "asset_location" : "asset_location", "asset_count" : "asset_count" }}, ...] }}
                            Als er meerdere assets genoemd worden (zoals (6x Toiletten Hoofdschool)) retourneer dan elk asset als een aparte rij, zoals
                            {{ "assets" : [ {{ "asset_type" : "Toiletten", "asset_location" : "Hoofdschool", "asset_count" : "6" }}, .... }}

                            Neem alleen assets op als de combinatie van asset type en locatie expliciet genoemd wordt. Als de locatie in combinatie met het asset type niet expliciet genoemd wordt, negeer dan het asset. Je kunt geen asset retourneren zonder locatie.
                            Geef alleen de naam van de locatie, niets anders. Wees zo specifiek mogelijk over de locatie.
                            De locatie moet een fysieke locatie in een gebouw zijn. Als er meerdere niveaus van locaties genoemd worden, begin dan met het grootste niveau en combineer met kleinere niveaus, verbonden met een koppelteken.
                            Bijvoorbeeld: "Hoofdschool - Keuken - Toiletten"

                            Voor het asset aantal is de standaardwaarde 1, tenzij het expliciet anders genoemd wordt."""
        

        # Two different prompts, one for known assets, one for unknown assets
        if assets_known:
            prompt_assets = prompt_known_if_assets
        else:
            prompt_assets = prompt_unknown_if_assets

        prompt_english = f"""{prompt_assets}
                            An asset can be any of the following (or a variation thereof) : 
                                Above Ground Grease Separator
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


         # Two different prompts, one for known assets, one for unknown assets
        if assets_known:
            prompt_assets = prompt_known_if_assets_nederlands
        else:
            prompt_assets = prompt_unknown_if_assets_nederlands

        prompt_nederlands = f"""{prompt_assets}
                            Een asset kan een van de volgende zijn (of een variant daarvan) : 
                            
                                Leveringspunt
                                Drukverhoger met schakelvat
                                Drukverhoger met schakelvat en variabele rotatie-frequentie
                                Drukverhoger zonder schakelvat en variabele rotatie-frequentie
                                Drukverhoger met druk(voorraad)ketel
                                Drukverhoger met drukloos hoogreservoir
                                Dubbele pompset
                                Waterreservoir
                                Ontharder
                                Omgekeerde osmose
                                Gedemineraliseerd water
                                Gede-mineraliseerd water
                                Overig
                                Doseerpomp
                                Ultrafiltratie
                                UV-licht
                                Koper-zilver ionisatie
                                Anodische oxidatie
                                Koeltoren
                                Combinatieboiler
                                Voorraadvat
                                Platenwisselaar met ketel
                                Platen-wisselaar met ketel
                                Platenwisselaar met zonnecollector
                                Platen-wisselaar met zonnecollector
                                Platenwisselaar met WKO
                                Platen-wisselaar met WKO
                                Warmtepomp
                                Direct gestookte boiler
                                Elektrische boiler
                                Close-in boiler
                                Close-up boiler
                                Indirect gestookte boiler
                                Indirect gestookte boiler met ketel
                                Indirect gestookte boiler met zonnecollector
                                Indirect gestookte boiler met platenwisselaar
                                Indirect gestookte boiler met platen-wisselaar
                                Indirect gestookte boiler met WKO
                                Voorraadvat met platenwisselaar
                                Voorraadvat met platen-wisselaar
                                Voorraadvat met doorstroomtoestel
                                Voorraadvat met doorstroom-toestel
                                Voorraadvat met WKO
                                Doorstroomtoestel
                                Doorstroom-toestel
                                Geiser
                                Gasboiler
                                Combiketel
                                Platenwisselaar zonder voorraadvat
                                Platen-wisselaar zonder voorraadvat
                                Warmwaterbereider
                                Warmwater-bereider
                                Plintboiler
                                Kokendwater-boiler
                                Enkelvoudig circulatiesysteem
                                Enkelvoudig circulatie-systeem
                                Meervoudig circulatiesysteem
                                Meervoudig circulatie-systeem
                                Deelcirculatieleiding
                                Deelcirculatie-leiding
                                Meervoudige uittapleiding (warmwater)
                                Mengwatersysteem
                                Mengwater-systeem
                                Circulerend mengwatersysteem
                                Circulerend mengwater-systeem
                                Drinkwaterringnet
                                Enkelvoudige uittapleiding (warmwater)
                                Hoofdleiding (warmwater)
                                Hoofdleiding (drinkwater)
                                Brandslanghaspel
                                Terreinleiding met brandkranen
                                Automatische sprinklerinstallatie
                                Automatische sprinkler-installatie
                                Gescheiden brandslanghaspel installatie
                                Gescheiden brandslang-haspel installatie
                                Sprinkler
                                Enkelvoudige uittapleiding (drinkwater)
                                Meervoudige uittapleiding (drinkwater)
                                Suppletieleiding (drinkwater)
                                Suppletie-leiding (drinkwater)
                                Bypass (drinkwater)
                                Verdeler (drinkwater)
                                Dode leiding (drinkwater)
                                Bad (mengkraan)
                                Bedpanspoeler
                                Bad (thermostatische mengkraan)
                                Bidet
                                CV-vulkraan
                                Aanrecht (mengkraan)
                                Aanrecht mengkraan
                                Aanrecht (thermostatische mengkraan)
                                Vaatwasser
                                Nooddouche
                                Oogdouche
                                Tappunt
                                Fontein
                                Gevelkraan
                                Handdouche
                                Slangwartelkraan
                                IJsmachine
                                Mengkraan
                                Mengventiel
                                Douche
                                Wastafel
                                Slophopper
                                Uitstortgootsteen
                                Spuithaspel
                                Knijpdouche
                                Stoombevochtiger
                                Toilet
                                Urinoir
                                Wasmachine
                                Suppletie koeling
                                Suppletie bevochtiger
                                Suppletie naar leidinggroep
                                Suppletie proceswater
                                Keukenmengkraan
                                Hoog/laagbad
                                Aansluiting
                                Koffieautomaat
                                Douchemengkraan thermostatisch
                                Tapkraan
                                Voetenwasbak
                                Wastrog
                                Douchemengkraan
                                Labkraan
                                Labmengkraan
                                Waterkoeler
                                Hogedrukreiniger
                                Reduceerventiel
                                Dode leiding (warmwater)
                                Bypass (warmwater)
                                Suppletieleiding (warmwater)
                                Suppletie-leiding (warmwater)
                                Inregelventiel
                                Sensorkraan
                                Lagedrukmengkraan
                                Steamer
                                Industriële vaatwasser
                                CV-vulkraan >45kW
                                Kappersdouche
                                Kappers-douche
                                Luchtbevochtiger
                                Lucht-bevochtiger
                                Onderspoelkraan
                                Onder-spoelkraan
                                Glazenspoeler
                                Industriële wasmachine
                                Zuurkast
                                Nood- & oogdouche
                                Au bain-marie
                                Zeepdoseersysteem
                                Zeepdoseer-systeem
                                Automatische spuiklep
                                Quooker
                                Soepautomaat
                                Drankautomaat
                                Drank-automaat
                                Grof filter
                                Fijn filter
                                Hoofdafsluiter
                                Tussenafsluiter
                                Tussen-afsluiter
                                Douchepaneel
                                Niveausignalering
                                Niveau-signalering
                                Geleidbaarheidsmeter
                                Geleidbaar-heidsmeter
                                Spuiklep
                                Circulatiepomp drinkwater
                                Circulatie-pomp drinkwater
                                Tussenwatermeter
                                Brandkraan
                                Kniewasbak
                                Automatische spoelinrichting
                                Break unit
                                tapApplianceType.Break+unit.button.label
                                Terugspoelfilter
                                Terugspoel-filter
                                Wasbak met kniebediening
                                Handwasbak
                                Zwembad vul/suppletie
                                Warme drankenmachine
                                Tandartsstoel
                                Postmix installatie
                                Laarzen reinigingstoestel
                                Patroon Demiwater
                                Pannenvulpunt
                                Wastafelmengkraan
                                Wastafel-mengkraan
                                Crushedijs machine
                                IJsblokjes machine
                                Combi-steamer
                                Kookketel
                                Braadslede
                                Thermostatisch mengventiel
                                Mengventiel thermo.
                                Expansieautomaat
                                Expansie-automaat
                                Tussenmeter
                                Toevoer koud
                                Toevoer warm
                                Toevoerleiding
                                Retourleiding
                                Voedingsleiding
                                Legionellafilter
                                Legionella-filter
                                Ontgasser
                                Wastafel-mengkraan thermo
                                Wastafel-mengkraan thermo.
                                Keuken mengkraan thermo
                                Keuken-mengkraan thermo.
                                Micro thermostatisch mengtoestel
                                Autoclaaf medisch sterilisatie instrument
                                Autoclaaf
                                Drinknippel(vee)
                                Drinknippel (vee)
                                Spoelkop(Bier)
                                Spoelkop (Bier)
                                Biertapinstallatie met fusten-reinigingsinstallatie
                                Biertapinstallatie met fusten – reinigingsinstallatie
                                Biertapinstallatie met tankreinigingsinstallatie
                                Biertapinstallatie met tankreiniging installatie
                                Automatische CV ontgasser
                                Chemisch toilet
                                Barkraan
                                Afsluiter
                                Drinkbak
                                --NIET SELECTEREN-- Waterreservoir
                                Automatische CV vulstation
                                Automatisch CV vulstation
                                Openbaar drinkwatertappunt
                                Aftapper
                                Automatisch C.V.-vulsysteem/ ontgasser
                                Barspoelkraan
                                Drankenautomaat
                                Bidet/toilet met randspoeling en onderdouche
                                Bidet / toilet met randspoeling en onderdouche
                                Kokendwaterkraan
                                Hose Union Bib Tap
                                Melkopschuimer
                                Melk Opschuimer
                                Heetwaterafsluiter (fail-safe)
                                Douchemengkraan thermostatisch met handdouche en regendouche
                                Bad/douche combinatie (mengkraan)
                                Bad/douche combinatie (thermostatische mengkraan)
                                Breaktank
                                Break tank
                                --NIET SELECTEREN-- Koudwaterreservoir (UK)
                                Voorspoeldouche
                                Dode leiding
                                Vulpunt CV - automatisch
                                Verwarmingsboiler
                                Ovenspray
                                Expansievat
                                Brandveiligheidssysteem
                                Chemische waterbehandeling
                                Waterkoelers
                                Theepunt
                                Water heater
                                Groentewastafel
                                Elektrische douche
                                Drukverhoger - Enkele pompset
                                Drukverhoger - dubbele pompset
                                Drukverhoger - Drievoudige pompset
                                Drukverhoger - Viervoudige pompset
                                Koelwaterbassin
                                Druppelafscheider
                                Vulpakket
                                Brominator
                                Chemische doseerinstallatie
                                Ozongenerator
                                Incubator
                                Afvoer koeltoren
                                Waterdistributiesysteem
                                Hydrocycloon
                                Zandfilter
                                Suppletietank
                                Aftap condensatorpomp
                                Filter condensatorpomp
                                Condensatorpomp
                                Bassincirculatiepomp
                                Koeler (tegenstroomapparaat)
                                Ventilator
                                Monsternamepunt
                                Aftap afsluiter
                                Voorraadvat chemicaliën
                                Chemicaliëndoseerpomp
                                Automatische ontluchtingsklep
                                Magneetklep
                                Verdampingscondensator
                                Andere - Airconditioningsysteem
                                Anders - Wellness/Zwembad/Jacuzzi
                                Anders - Industrieel proceswatersysteem
                                Inline-filter
                                Korffilter
                                Boorput
                                Open put
                                Warmtewisselaars
                                pH-meter
                                Proceswater
                                Anders - Fontein
                                Sediment filter
                                Elektrolytische ontkalker
                                Waterfilter
                                IJslepelbakje
                                Multifunctionele (slimme) kraan
                                Reinwaterkelder
                                Opvangsysteem voor regenwater
                                Opvangtank voor regenwater
                                Directe waterverwarmer
                                Tertiaire retour-lus
                                Secundaire retour-lus
                                Handmatig snel vullen
                                Verminderde Drukventiel
                                Bovengrondse vetafscheider
                                Bovengrondse vetsplitter
                                Ondergrondse vetafscheider
                                Ondergrondse vetsplitter
                                Vetafscheider Slipafscheider
                                Slibafscheider
                                Warm water circulatiepomp
                                Terrein leiding
                                Muur gemonteerde Breaktank
                                Gestabiliseerde Aqueous Ozongenerator
                                Sproei tappunt
                                TapApplianceType.SprayOutlet.Button.Label
                                TapApplianceType.Bath
                                TapApplianceType.Bath.Button.Label
                                Enkelvoudige Uittapleiding (Mengwater)
                                Meervoudige uittapleiding (mengwater)
                                Verdeelleiding
                                Sluice
                                Blusleiding
                                Steam boiler
                                Hoge druk tappunt
                                Lage druk tappunt
                                Indirect verwarmd voorraadvat met warmtepomp
                                Warmtepomp boiler
                                Douchemengkraan met handdouche en regendouche
                                Waseenheid
                                Gekoeld watersysteem
                                Laag temperatuur warmwater
                                Run-around warmtewisselaars
                                Condenser systeem
                                Medium temperatuur warmwater
                                Hoog temperatuur warmwater
                                Voeding en expansievat
                                Hoofdtank
                                Waterspeeltoestel
                                Water speel toestel
                                Bubbelbuis
                                Sensor apparaat
                                Drukventiel
                                Wastafel met handwasunit
                                Aanrecht met handwasunit
                                Aanrecht

                            This is the CSV table:

                                {df_string}         

                                Als er lege waarden in de CSV staan, kan dit ook komen door eerder samengevoegde/gesplitste cellen, aangezien deze CSV is geëxtraheerd uit een Excel bestand.

                                GEEF ALLEEN DE JSON TERUG, GEEF NIETS ANDERS TERUG.              """

        if language == 'english':
            prompt = prompt_english
        elif language == 'nederlands':
            prompt = prompt_nederlands

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

