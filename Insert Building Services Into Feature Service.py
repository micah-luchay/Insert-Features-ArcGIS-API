from arcgis.gis import GIS
import arcgis, time
import arcpy, os, shutil, json

arcpy.management.Delete(r"memory") # delete anything in memory before running script
arcpy.env.workspace = r"memory" # use memory as a workspace for faster performance
arcpy.env.addOutputsToMap = False # don't add outputs to map for faster processing
arcpy.env.overwriteOutput = True # overwrite existing outputs

gis = GIS("Pro") # log into your org's Portal using ArcPro

def remove_zeroes_empty(featureLayer):
    
    with arcpy.da.UpdateCursor(featureLayer, '*') as cursor:  
        for row in cursor:
            updated = False  # Track if any value in the row is updated
            for i, cell in enumerate(row):
                if cell == '0' or cell == 0 or cell == '' or cell == '#REF!':  # Check for zero in numeric or string form or empty string
                    row[i] = None  # Update the cell in the row
                    updated = True
                try:
                    if cell is not None and 'Null' in cell:
                        row[i] = None
                        updated = True
                except:
                    pass
            if updated:
                cursor.updateRow(row)  # Update the row only if a change was made
    
    del cursor

def update_table_domains(featureLayer):
    
    fields = ["Utility_Status", "Customer_Status", "Customer_Source", "Customer_Side_Notes", "Utility_Source", "Utility_Side_Notes"]
    with arcpy.da.UpdateCursor(featureLayer, fields) as cursor: # update table to be domain code compliant
        for row in cursor:
            if row[0] == 'Non-Lead': # update utilty status values
                row[0] = 2
            elif row[0] == 'Unknown':
                row[0] = 0
            if row[1] == 'Non-Lead': # update customer status values
                row[1] = 2
            elif row[1] == 'Unknown':
                row[1] = 0
            elif row[1] == 'Lead Status Unknown':
                row[1] = 0
            elif row[1] == 'Galvanized Requiring Replacement':
                row[1] = 3
            
            if row[2] is not None and 'Predictive' in row[2]: # remove predictive modeling from cust source, make 'other' and update customer notes
                row[2] = "Other"
                if row[3]: # cust notes field is not empty
                    row[3] = row[3] + "; Predictive Model"
                elif not row[3]: # cust notes field is empty:
                    row[3] = "Predictive Model"
                    
            if row[2] == 'Previous Materials Evaluation': # wrong domain value for customer source
                row[2] = 'Previous materials evaluation'
            elif row[2] == 'Service line diameter is > 2 inches': # wrong domain value for customer source
                row[2] = 'Service line diameter is greater than 2 inches'
                
            if row[4] is not None and 'Predictive' in row[4]: # util source is predictive modeling, change to other
                row[4] = "Other"
                if row[5]: # util notes field is not empty
                    row[5] = row[5] + "; Predictive Model"
                elif not row[5]: # util notes field is empty:
                    row[5] = "Predictive Model"
              
            cursor.updateRow(row)
            
    del cursor

def replace_null_with_none(geojson_data): 
    # Recursively convert nulls in the GeoJSON to None (Python's null equivalent)
    if isinstance(geojson_data, dict):
        return {k: replace_null_with_none(v) for k, v in geojson_data.items()}
    elif isinstance(geojson_data, list):
        return [replace_null_with_none(item) for item in geojson_data]
    elif geojson_data is None:  # Replace 'null' with 'None'
        return None
    else:
        return geojson_data

def create_building_services(link1, link2, link3, masterGDB, appendFC_Name, templateFC):
    print("Creating Building Services.")
    
    AptServices = arcpy.management.MakeFeatureLayer(link1, "AptServices") # make feature layer of apt services
    MHServices = arcpy.management.MakeFeatureLayer(link2, "MHServices") # make feature layer of mobile home services
    SchoolServices = arcpy.management.MakeFeatureLayer(link3, "SchoolServices") # make feature layer of school services
    templateFL = arcpy.management.MakeFeatureLayer(templateFC, "templateFL") # make feature layer of template FC
    
    newFC = arcpy.management.CreateFeatureclass(masterGDB, appendFC_Name, "POINT", templateFC)
    Building_Services = arcpy.management.MakeFeatureLayer(newFC, "Building_Services") # merged services
    
    apt_fields = ["Account_ID", "Address", "Other_Location_Identifier", "Sensitive_Population", "Disadvantaged_Neighborhood", "Utility_Asset_ID", "Utility_Material", "Ever_Lead_", "Utility_Install_Date", "Utility_Diameter", "Utility_Source", "Utility_Side_Verified", "Utility_Verification_Method", "Utility_Verification_Date", "Utility_Status", "Utility_Side_Notes", "Customer_Asset_ID", "Customer_Material", "Customer_Install_Date", "Customer_Diameter", "Customer_Source", "Customer_Side_Verified", "Customer_Verification_Method", "Customer_Verification_Date", "Customer_Status", "Customer_Side_Notes", "Entire_Service_Line_Status", "Lead_Connector", "Lead_Solder", "Other_Fittings_Containing_Lead", "Building_Type", "Point_of_Entry_or_Point_of_Use", "Copper_Pipes_with_Lead_Solder_Before_Lead_Ban", "Current_LCR_Sampling_Site", "Replacement_Status", "Utility_Side_Scheduled_Replacement_Date", "Utility_Side_Replacement_Date", "Customer_Side_Scheduled_Replacement_Date", "Customer_Side_Replacement_Date", "Reason_for_Replacement", "Notified_Customer", "Notification_Date", "Year_Structure_Built", "SHAPE@"]
    MH_fields = ["Account_ID", "Address_1", "Other_Location_Identifier", "Sensitive_Population", "Disadvantaged_Neighborhood", "Utility_Asset_ID", "Utility_Material", "Ever_Lead_", "Utility_Install_Date", "Util_Diameter_DBL", "Utility_Source", "Utility_Side_Verified", "Utility_Verification_Method", "utilverifdate_DATE", "Utility_Status", "Utility_Side_Notes", "Customer_Asset_ID", "Customer_Material", "Customer_Install_Date", "Cust_Diameter_DBL", "Customer_Source", "Customer_Side_Verified", "Customer_Verification_Method", "custverifdate_DATE", "Customer_Status", "Customer_Side_Notes", "Entire_Service_Line_Status", "Lead_Connector", "Lead_Solder", "Other_Fittings_Containing_Lead", "Building_Type", "Point_of_Entry_or_Point_of_Use", "Copper_Pipes_with_Lead_Solder_Before_Lead_Ban", "Current_LCR_Sampling_Site", "Replacement_Status", "Utility_Side_Scheduled_Replacement_DATETIME", "Utility_Side_Replacement_DATETIME", "Customer_Side_Scheduled_Replacement_DATETIME", "Customer_Side_Replacement_DATETIME", "Reason_for_Replacement", "Notified_Customer", "Notification_DATETIME", "Year_Structure_Built", "SHAPE@"]
    school_fields = ["Account_ID", "Address_1", "Other_Location_Identifier", "Sensitive_Population", "Disadvantaged_Neighborhood", "Utility_Asset_ID", "Utility_Material", "Ever_Lead_", "Utility_Install_DATETIME", "Utility_Diameter", "Utility_Source", "Utility_Side_Verified", "Utility_Verification_Method", "utilverifdate_DATE", "Utility_Status", "Utility_Side_Notes", "Customer_Asset_ID", "Customer_Material", "Customer_Install_DATETIME", "Customer_Diameter", "Customer_Source", "Customer_Side_Verified", "Customer_Verification_Method", "custverifdate_DATE", "Customer_Status", "Customer_Side_Notes", "Entire_Service_Line_Status", "Lead_Connector", "Lead_Solder", "Other_Fittings_Containing_Lead", "Building_Type", "Point_of_Entry_or_Point_of_Use", "Copper_Pipes_with_Lead_Solder_Before_Lead_Ban", "Current_LCR_Sampling_Site", "Replacement_Status", "Utility_Side_Scheduled_Replacement_DATETIME", "Utility_Side_Replacement_DATETIME", "Customer_Side_Scheduled_Replacement_DATETIME", "Customer_Side_Replacement_DATETIME", "Reason_for_Replacement", "Notified_Customer", "Notification_DATETIME", "Year_Structure_Built", "SHAPE@"]
    serviceLine_fields = ["accountid", "address", "location", "sensitivepop", "disadvantaged", "utilassetid", "utilmaterial", "everlead", "utilinstalldate", "utildiameter", "utilsource", "utilverified", "utilverifmethod", "utilverifdate", "utilstatus", "utilnotes", "custassetid", "custmaterial", "custinstalldate", "custdiameter", "custsource", "custverified", "custverifmethod", "custverifdate", "custstatus", "custnotes", "bothsidesstatus", "leadconnector", "leadsolder", "otherfittings", "buildingtype", "pointofentry", "copperwithlead", "samplingsite", "replacestatus", "scheddate", "utilreplacedate", "custscheddate", "custreplacedate", "replacereason", "custnotified", "notifydate", "yearstructbuilt", "SHAPE@"]
   
    #### UPDATE APT SERVICES ####
    
    remove_zeroes_empty(AptServices) # remove zeros and empty strings
    update_table_domains(AptServices) # update table with domain codes

    icur = arcpy.da.InsertCursor(Building_Services, serviceLine_fields)
    with arcpy.da.SearchCursor(AptServices, apt_fields) as cursor: # use insert cursor to avoid field maps for Apartment services
        for row in cursor:
            icur.insertRow(row)
    
    del cursor
    print("Finished with Apts.")
    
    #### UPDATE MOBILE HOME SERVICES ####
    
    arcpy.management.AddField(MHServices, "Util_Diameter_DBL", "DOUBLE") # current diameter fields are text in type, need to convert
    arcpy.management.CalculateField(MHServices, "Util_Diameter_DBL", "!Utility_Diameter!")
    arcpy.management.AddField(MHServices, "Cust_Diameter_DBL", "DOUBLE")
    arcpy.management.CalculateField(MHServices, "Cust_Diameter_DBL", "!Customer_Diameter!")
    arcpy.management.AddField(MHServices, "utilverifdate_DATE", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "utilverifdate_DATE", "!Utility_Verification_Date!")
    arcpy.management.AddField(MHServices, "custverifdate_DATE", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "custverifdate_DATE", "!Customer_Verification_Date!")
    arcpy.management.AddField(MHServices, "Utility_Side_Scheduled_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "Utility_Side_Scheduled_Replacement_DATETIME", "!Utility_Side_Scheduled_Replacement_Date!")
    arcpy.management.AddField(MHServices, "Utility_Side_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "Utility_Side_Replacement_DATETIME", "!Utility_Side_Replacement_Date!")
    arcpy.management.AddField(MHServices, "Customer_Side_Scheduled_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "Customer_Side_Scheduled_Replacement_DATETIME", "!Customer_Side_Scheduled_Replacement_Date!")
    arcpy.management.AddField(MHServices, "Customer_Side_Replacement_DATETIME", "Date") 
    arcpy.management.CalculateField(MHServices, "Customer_Side_Replacement_DATETIME", "!Customer_Side_Replacement_Date!")
    arcpy.management.AddField(MHServices, "Notification_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(MHServices, "Notification_DATETIME", "!Notification_Date!")
    
    remove_zeroes_empty(MHServices) # remove zeros and empty strings
    update_table_domains(MHServices) # update table with domain codes

    with arcpy.da.SearchCursor(MHServices, MH_fields) as cursor: # use insert cursor to avoid field maps for mobile home services
        for row in cursor:
            icur.insertRow(row)      
    
    print("Finished with Mobile Homes.")
    
    #### UPDATE SCHOOL SERVICES ####
    
    arcpy.management.AddField(SchoolServices, "Utility_Install_DATETIME", "Date") # convert to date format
    arcpy.management.CalculateField(SchoolServices, "Utility_Install_DATETIME", "!Utility_Install_Date!")
    arcpy.management.AddField(SchoolServices, "Customer_Install_DATETIME", "Date") # convert to date format
    arcpy.management.CalculateField(SchoolServices, "Customer_Install_DATETIME", "!Customer_Install_Date!")
    arcpy.management.AddField(SchoolServices, "utilverifdate_DATE", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "utilverifdate_DATE", "!Utility_Verification_Date!")
    arcpy.management.AddField(SchoolServices, "custverifdate_DATE", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "custverifdate_DATE", "!Customer_Verification_Date!")
    arcpy.management.AddField(SchoolServices, "Utility_Side_Scheduled_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "Utility_Side_Scheduled_Replacement_DATETIME", "!Utility_Side_Scheduled_Replacement_Date!")
    arcpy.management.AddField(SchoolServices, "Utility_Side_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "Utility_Side_Replacement_DATETIME", "!Utility_Side_Replacement_Date!")
    arcpy.management.AddField(SchoolServices, "Customer_Side_Scheduled_Replacement_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "Customer_Side_Scheduled_Replacement_DATETIME", "!Customer_Side_Scheduled_Replacement_Date!")
    arcpy.management.AddField(SchoolServices, "Customer_Side_Replacement_DATETIME", "Date") 
    arcpy.management.CalculateField(SchoolServices, "Customer_Side_Replacement_DATETIME", "!Customer_Side_Replacement_Date!")
    arcpy.management.AddField(SchoolServices, "Notification_DATETIME", "Date") # change date field 
    arcpy.management.CalculateField(SchoolServices, "Notification_DATETIME", "!Notification_Date!")
    
    remove_zeroes_empty(SchoolServices) # remove zeros and empty strings
    update_table_domains(SchoolServices) # update table with domain codes

    with arcpy.da.SearchCursor(SchoolServices, school_fields) as cursor: # use insert cursor to avoid field maps for school services
        for row in cursor:
            icur.insertRow(row)
            
    print("Finished with Schools.")

    #### UPDATE NULL STATUSES ####
    
    query = 'utilstatus IS NULL'
    arcpy.management.SelectLayerByAttribute(Building_Services, "NEW_SELECTION", query) # select null util status
    arcpy.management.CalculateField(Building_Services, "utilstatus", "Unknown") # set nulls to be unknown
    
    query = 'custstatus IS NULL'
    arcpy.management.SelectLayerByAttribute(Building_Services, "NEW_SELECTION", query) # select null cust status
    arcpy.management.CalculateField(Building_Services, "custstatus", "Unknown") # set nulls to be unknown
    
    arcpy.management.SelectLayerByAttribute(Building_Services, "CLEAR_SELECTION") # clear seelction
    
    print("Finished with misc tranformations.")
    return Building_Services 

def replace_crs(FeatureSet):
    for feature in FeatureSet.features:
        if 'spatialReference' in feature.geometry:
            feature.geometry['spatialReference']['wkid'] = 3857  # Change wkid to 3857
            feature.geometry['spatialReference']['latestWkid'] = 3857  # Change wkid to 3857
        else:
            feature.geometry['spatialReference'] = {'wkid': 3857, 'latestWkid': 4326}  # Add spatial reference if not present
    return FeatureSet

def geojson_export(featureLayer, geoJSONFolder, outputName):
    print("Prepping data to append to feature service.")
    
    with arcpy.da.SearchCursor(featureLayer, "OBJECTID") as cursor: # grab largest objectid
        max_objectid = int(max(row[0] for row in cursor))
    del cursor    
    
    queryList = []
    incrementor = 100 # add features 100 at a time to feature service
    
    for i in range(0, max_objectid, incrementor):
        if i + incrementor > max_objectid : # last request to server, number is over feature count
            where_clause = f"OBJECTID >= {str(i+1)} AND OBJECTID <= {str(max_objectid)}"
            queryList.append(where_clause)
        else:  
            where_clause = f"OBJECTID >= {str(i+1)} AND OBJECTID <= {str(i + incrementor)}" # request is under feature count
            queryList.append(where_clause)
    
    for index, query in enumerate(queryList, 1):
        selection = arcpy.management.SelectLayerByAttribute(featureLayer, "NEW_SELECTION", query) # select features in loop
        name = "Building_Services_" + str(index)
        FC = arcpy.management.CopyFeatures(selection, name) # create separate FC from selection
        FC_FL = arcpy.management.MakeFeatureLayer(FC, "FC_FL") # create FL to be able to export
        
        geoJSONFile = os.path.join(geoJSONFolder, name + ".geojson")
        arcpy.conversion.FeaturesToJSON(FC_FL, geoJSONFile, "FORMATTED", geoJSON = "GEOJSON") # export as JSON file
        arcpy.management.SelectLayerByAttribute(featureLayer, "CLEAR_SELECTION") # clear selection
        arcpy.management.Delete(FC)
        arcpy.management.Delete(FC_FL)

def insert_rows_service(itemID, geoJSONFolder):
    print("Adding meters to the feature service.")
    files = os.listdir(geoJSONFolder)
    
    portalItem = gis.content.get(itemID) # grab the item by itemID
    portalLayer = portalItem.layers[0] # access the first layer of the item
    
    for file in files:
        fullFile = os.path.join(geoJSONFolder, file) # create full path name

        with open(fullFile, 'r') as file:
            geojson_data = json.load(file)  # Load GeoJSON as a Python dictionary, it is WGS84 in projection, keep it as that!

        FeatureSet = arcgis.features.FeatureSet.from_geojson(geojson_data) # create featureset from geojson file
        FeatureSet = replace_crs(FeatureSet) # replace wkid with 3857, for some reason loading it in the featureset turns it to 4326

        response = portalLayer.edit_features(adds = FeatureSet) # append FeatureSet to feature service, make sure to use the WGS84 projection!
        print(response["addResults"][0]) # show some status message
        time.sleep(3) # give the server a mini-break

#itemID = "XXXX" # item ID of potable inventory feature service on Hazen Portal
itemID = "XXXX" # item ID of potable inventory feature service on Tampa Portal

Apt_Services = r"O:\GIS\Projects\41077-000\41077-016\Data\Databases\Building Services\BuildingCount_Deliverables12042024.gdb\AptPoints_12052024" # services for apartments
MH_Services = r"O:\GIS\Projects\41077-000\41077-016\Data\Databases\Building Services\BuildingCount_Deliverables12042024.gdb\MHPoints_12052024" # services for mobile homes
School_Services = r"O:\GIS\Projects\41077-000\41077-016\Data\Databases\Building Services\BuildingCount_Deliverables12042024.gdb\SchoolPoints_12052024" # services for schools
masterGDB = r"O:\GIS\Projects\41077-000\41077-016\ArcGISPro\City of Tampa LCR Phase 2 (MML)\City of Tampa LCR Phase 2 (MML).gdb\Working" # project gdb, write the merged services here
templateFC = r"O:\GIS\Projects\41077-000\41077-016\Data\Databases\Inventory\Potable Inventory\ServiceLine.gdb\ServiceLine" # use this as a template for creating a fC

Building_Services = create_building_services(Apt_Services, MH_Services, School_Services, masterGDB, "Building_Services", templateFC) # create feature layer for the building services

geoJSONFolder = r"O:\GIS\Projects\41077-000\41077-016\Data\GeoJSON\Building Services" # store geojson data in this folder
servicesGeoJSON = geojson_export(Building_Services, geoJSONFolder, "Building_Services") # create geojson file to add to feature service

insert_rows_service(itemID, geoJSONFolder) # insert building services into the feature service

