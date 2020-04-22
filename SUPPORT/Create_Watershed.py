# ==========================================================================================
# Name: Create_Watershed.py
#
# Author: Peter Mead
# e-mail: pemead@co.becker.mn.us
#
# Author: Chris Morse
#         IN State GIS Coordinator
#         USDA - NRCS
# e-mail: chris.morse@usda.gov
# phone: 317.501.1578
#
# Author: Adolfo.Diaz
#         GIS Specialist
#         National Soil Survey Center
#         USDA - NRCS
# e-mail: adolfo.diaz@usda.gov
# phone: 608.662.4422 ext. 216

# Created by Peter Mead, Adolfo Diaz, USDA NRCS, 2013
# Updated by Chris Morse, USDA NRCS, 2019

# ==========================================================================================
# Updated  4/15/2020 - Adolfo Diaz

# Create_Watershed.py
## ===============================================================================================================
def print_exception():

    try:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        theMsg = "\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[1] + "\n\t" + traceback.format_exception(exc_type, exc_value, exc_traceback)[-1]

        if theMsg.find("exit") > -1:
            AddMsgAndPrint("\n\n")
            pass
        else:
            AddMsgAndPrint("\n----------------------------------- ERROR Start -----------------------------------",2)
            AddMsgAndPrint(theMsg,2)
            AddMsgAndPrint("------------------------------------- ERROR End -----------------------------------\n",2)

    except:
        AddMsgAndPrint("Unhandled error in print_exception method", 2)
        pass

## ================================================================================================================
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    # Split the message on  \n first, so that if it's multiple lines, a GPMessage will be added for each line

    print(msg)

    try:
        f = open(textFilePath,'a+')
        f.write(msg + " \n")
        f.close
        del f

        if severity == 0:
            arcpy.AddMessage(msg)

        elif severity == 1:
            arcpy.AddWarning(msg)

        elif severity == 2:
            arcpy.AddError(msg)

    except:
        pass

## ================================================================================================================
def logBasicSettings():
    # record basic user inputs and settings to log file for future purposes

    import getpass, time
    arcInfo = arcpy.GetInstallInfo()  # dict of ArcGIS Pro information

    f = open(textFilePath,'a+')
    f.write("\n################################################################################################################\n")
    f.write("Executing \"3. Create Watershed\" for ArcGIS 9.3 and 10\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write(arcInfo['ProductName'] + ": " + arcInfo['Version'])
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tStreams: " + streamsPath + "\n")

    if int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
        f.write("\toutlet Digitized: " + str(arcpy.GetCount_management(outlet)) + "\n")
    else:
        f.write("\toutlet Digitized: 0\n")

    f.write("\tWatershed Name: " + watershedOut + "\n")

    if bCalcLHL:
        f.write("\tCreate flow paths: SELECTED\n")
    else:
        f.write("\tCreate flow paths: NOT SELECTED\n")

    f.close
    del f

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]
    except:
        print_exception()
        return someNumber


## ================================================================================================================
# Import system modules
import arcpy, sys, os, string, traceback, re
from arcpy.sa import *

if __name__ == '__main__':

    try:

        # Check out Spatial Analyst License
        if arcpy.CheckExtension("spatial") == "Available":
            arcpy.CheckOutExtension("spatial")
        else:
            arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu\n",2)
            exit()

        # Script Parameters
        streams = arcpy.GetParameterAsText(0)
        outlet = arcpy.GetParameterAsText(1)
        userWtshdName = arcpy.GetParameterAsText(2)
        createFlowPaths = arcpy.GetParameterAsText(3)

        # Uncomment the following 4 lines to run from pythonWin
        ##    streams = r'C:\flex\flex_EngTools.gdb\Layers\Streams'
        ##    outlet = r'C:\flex\flex_EngTools.gdb\Layers\outlet'
        ##    userWtshdName = "testing10"
        ##    createFlowPaths = "true"

        if str(createFlowPaths).upper() == "TRUE":
            bCalcLHL = True
        else:
            bCalcLHL = False

        # --------------------------------------------------------------------------------------------- Define Variables
        streamsPath = arcpy.da.Describe(streams)['catalogPath']

        if streamsPath.find('.gdb') > 0 and streamsPath.find('_Streams') > 0:
            watershedGDB_path = streamsPath[:streamsPath.find(".gdb")+4]
        else:
            arcpy.AddError("\n\n" + streams + " is an invalid Stream Network Feature")
            arcpy.AddError("Run Watershed Delineation Tool #2. Create Stream Network\n\n")
            exit()

        userWorkspace = os.path.dirname(watershedGDB_path)
        watershedGDB_name = os.path.basename(watershedGDB_path)
        watershedFD = watershedGDB_path + os.sep + "Layers"
        projectName = arcpy.ValidateTablename(os.path.basename(userWorkspace).replace(" ","_"))
        projectAOI = watershedFD + os.sep + projectName + "_AOI"
        aoiName = os.path.basename(projectAOI)

        # --------------------------------------------------------------- Datasets
        # ------------------------------ Permanent Datasets
        watershed = watershedFD + os.sep + (arcpy.ValidateTablename(userWtshdName, watershedFD))
        FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"
        FlowDir = watershedGDB_path + os.sep + "flowDirection"
        DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
        DEMsmooth = watershedGDB_path + os.sep + "DEMsmooth"

        # Must Have a unique name for watershed -- userWtshdName gets validated, but that doesn't ensure a unique name
        # Append a unique digit to watershed if required -- This means that a watershed with same name will NOT be
        # overwritten.
        x = 1
        while x > 0:
            if arcpy.Exists(watershed):
                watershed = watershedFD + os.sep + (arcpy.ValidateTablename(userWtshdName, watershedFD)) + str(x)
                x += 1
            else:
                x = 0
        del x

        outletFC = watershedFD + os.sep + os.path.basename(watershed) + "_outlet"

        # ---------------------------------------------------------------------------------------------- Temporary Datasets
        wtshdDEMsmooth = watershedGDB_path + os.sep + "wtshdDEMsmooth"
        slopeGrid = watershedGDB_path + os.sep + "slopeGrid"
        slopeStats = watershedGDB_path + os.sep + "slopeStats"

        # Features in Arcmap
        watershedOut = "" + os.path.basename(watershed) + ""
        outletOut = "" + os.path.basename(outletFC) + ""

        # -----------------------------------------------------------------------------------------------  Path of Log file
        textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

        # record basic user inputs and settings to log file for future purposes
        logBasicSettings()

        # ---------------------------------------------------------------------------------------------- Check some parameters
        # If validated name becomes different than userWtshdName notify the user
        if os.path.basename(watershed) != userWtshdName:
            AddMsgAndPrint("\nUser Watershed name: " + str(userWtshdName) + " is invalid or already exists in project geodatabase.",1)
            AddMsgAndPrint("\tRenamed output watershed to " + str(watershedOut),1)

        # Make sure the FGDB and streams exists from step 1 and 2
        if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(streamsPath):
            AddMsgAndPrint("\nThe \"Streams\" Feature Class or the File Geodatabase from Step 1 was not found",2)
            AddMsgAndPrint("Re-run Step #1 and #2",2)
            exit()

        # Must have one pour points manually digitized
        if not int(arcpy.GetCount_management(outlet).getOutput(0)) > 0:
            AddMsgAndPrint("\n\nAt least one Pour Point must be used! None Detected. Exiting\n",2)
            exit()

        # Flow Accumulation grid must in FGDB
        if not arcpy.Exists(FlowAccum):
            AddMsgAndPrint("\n\nFlow Accumulation Grid was not found in " + watershedGDB_path,2)
            AddMsgAndPrint("Run Tool#2: \"Create Stream Network\" Again!  Exiting.....\n",2)
            exit()

        # Flow Direction grid must present to proceed
        if not arcpy.Exists(FlowDir):
            AddMsgAndPrint("\n\nFlow Direction Grid was not found in " + watershedGDB_path,2)
            AddMsgAndPrint("Run Tool#2: \"Create Stream Network\" Again!  Exiting.....\n",2)
            sys.exit(0)

        # ---------------------------------------------------------------------------------------------- Delete old datasets
        datasetsToRemove = (outletBuffer,pourPointGrid,watershedGrid,watershedTemp,watershedDissolve,wtshdDEMsmooth,slopeGrid,slopeStats)

        x = 0
        for dataset in datasetsToRemove:

            if arcpy.Exists(dataset):

                if x < 1:
                    AddMsgAndPrint("\nRemoving old datasets from FGDB: " + watershedGDB_name ,1)
                    x += 1

                try:
                    arcpy.Delete_management(dataset)
                    AddMsgAndPrint("\tDeleting....." + os.path.basename(dataset),0)
                except:
                    pass

        del dataset
        del datasetsToRemove
        del x

        # ----------------------------------------------------------------------------------------------- Create New Outlet
        # -------------------------------------------- Features reside on hard disk;
        #                                              No heads up digitizing was used.
        if (os.path.dirname(arcpy.Describe(outlet).CatalogPath)).find("memory") < 0:

            # if paths between outlet and outletFC are NOT the same
            if not arcpy.Describe(outlet).CatalogPath == outletFC:

                # delete the outlet feature class; new one will be created
                if arcpy.Exists(outletFC):
                    arcpy.Delete_management(outletFC)
                    arcpy.CopyFeatures_management(outlet, outletFC)
                    AddMsgAndPrint("\nSuccessfully Recreated " + str(outletOut) + " feature class from existing layer",1)

                else:
                    arcpy.CopyFeatures_management(outlet, outletFC)
                    AddMsgAndPrint("\nSuccessfully Created " + str(outletOut) + " feature class from existing layer",1)

            # paths are the same therefore input IS pour point
            else:
                AddMsgAndPrint("\nUsing Existing " + str(outletOut) + " feature class",1)

        # -------------------------------------------- Features reside in Memory;
        #                                              heads up digitizing was used.
        else:

            if arcpy.Exists(outletFC):
                arcpy.Delete_management(outletFC)
                arcpy.Clip_analysis(outlet,projectAOI,outletFC)
                #arcpy.CopyFeatures_management(outlet, outletFC)
                AddMsgAndPrint("\nSuccessfully Recreated " + str(outletOut) + " feature class from digitizing")

            else:
                arcpy.Clip_analysis(outlet,projectAOI,outletFC)
                #arcpy.CopyFeatures_management(outlet, outletFC)
                AddMsgAndPrint("\nSuccessfully Created " + str(outletOut) + " feature class from digitizing")

        if arcpy.Describe(outletFC).ShapeType != "Polyline" and arcpy.Describe(outletFC).ShapeType != "Line":
            AddMsgAndPrint("\n\nYour Outlet must be a Line or Polyline layer!.....Exiting!",2)
            exit()

        AddMsgAndPrint("\nChecking Placement of Outlet(s)....")
        numOfOutletsWithinAOI = int(arcpy.GetCount_management(outletFC).getOutput(0))
        if numOfOutletsWithinAOI < 1:
            AddMsgAndPrint("\nThere were no outlets digitized within " + aoiName + "....EXITING!",2)
            arcpy.Delete_management(outletFC)
            exit()

        # ---------------------------------------------------------------------------------------------- Create Watershed
        # ---------------------------------- Retrieve DEM Properties
        demDesc = arcpy.da.Describe(DEM_aoi)
        demName = demDesc['name']
        demPath = demDesc['catalogPath']
        demCellSize = demDesc['meanCellWidth']
        demFormat = demDesc['format']
        demSR = demDesc['spatialReference']
        demCoordType = demSR.type
        linearUnits = demSR.linearUnitName

        if linearUnits == "Meter":
            linearUnits = "Meters"
        elif linearUnits == "Foot":
            linearUnits = "Feet"
        elif linearUnits == "Foot_US":
            linearUnits = "Feet"

        # ----------------------------------- Set Environment Settings
        arcpy.env.extent = "MAXOF"
        arcpy.env.cellSize = demCellSize
        arcpy.env.snapRaster = demPath
        arcpy.env.outputCoordinateSystem = demSR
        arcpy.env.workspace = watershedGDB_path

        # --------------------------------------------------------------------- Convert outlet Line Feature to Raster Pour Point.

        # Add dummy field for buffer dissolve and raster conversion using OBJECTID (which becomes subbasin ID)
        objectIDfld = "!" + arcpy.da.Describe(outletFC)['OIDFieldName'] + "!"
        arcpy.AddField_management(outletFC, "IDENT", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED")
        arcpy.CalculateField_management(outletFC, "IDENT", objectIDfld, "PYTHON3")

        # Buffer outlet features by  raster cell size
        outletBuffer = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("outletBuffer",data_type="FeatureClass",workspace=watershedGDB_path))
        bufferDist = "" + str(demCellSize) + " " + str(linearUnits) + ""
        arcpy.Buffer_analysis(outletFC, outletBuffer, bufferDist, "FULL", "ROUND", "LIST", "IDENT")

        # Convert bufferd outlet to raster
        #arcpy.MakeFeatureLayer(outletBuffer,"outletBufferLyr")
        pourPointGrid = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("PourPoint",data_type="RasterDataset",workspace=watershedGDB_path))
        arcpy.PolygonToRaster_conversion(outletBuffer,"IDENT",pourPointGrid,"MAXIMUM_AREA","NONE",demCellSize)

        # Delete intermediate data
        arcpy.Delete_management(outletBuffer)
        arcpy.DeleteField_management(outletFC, "IDENT")

        # Create Watershed Raster using the raster pour point
        AddMsgAndPrint("\nDelineating Watershed(s)...")
        watershedGrid = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("watershedGrid",data_type="RasterDataset",workspace=watershedGDB_path))
        arcpy.Watershed_sa(FlowDir,pourPointGrid,watershedGrid,"VALUE")

        # Convert results to simplified polygon
        watershedTemp = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("watershedTemp",data_type="FeatureClass",workspace=watershedGDB_path))
        arcpy.RasterToPolygon_conversion(watershedGrid,watershedTemp,"SIMPLIFY","VALUE")

        # Dissolve watershedTemp by GRIDCODE or grid_code
        arcpy.Dissolve_management(watershedTemp, watershed, "GRIDCODE", "", "MULTI_PART", "DISSOLVE_LINES")
        AddMsgAndPrint("\n\tSuccessfully Created " + str(int(arcpy.GetCount_management(watershed).getOutput(0))) + " Watershed(s) from " + str(outletOut),0)

        arcpy.Delete_management(pourPointGrid)
        arcpy.Delete_management(watershedGrid)

        # -------------------------------------------------------------------------------------------------- Add and Calculate fields
        # Add Subbasin Field in watershed and calculate it to be the same as GRIDCODE
        arcpy.AddField_management(watershed, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED")

        arcpy.CalculateField_management(watershed, "Subbasin", "!GRIDCODE!", "PYTHON3")
        arcpy.DeleteField_management(watershed, "GRIDCODE")

        # Add Acres Field in watershed and calculate them and notify the user
        arcpy.AddField_management(watershed, "Acres", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED")
        arcpy.CalculateField_management(watershed, "Acres", "!shape.area@acres!", "PYTHON3")

        # ---------------------------------------------------------------------------- If user opts to calculate watershed flow paths
        if bCalcLHL:
            try:

                # ------------------------------------------- Permanent Datasets (..and yes, it took 13 other ones to get here)
                Flow_Length = watershedFD + os.sep + os.path.basename(watershed) + "_FlowPaths"
                FlowLengthName = os.path.basename(Flow_Length)

                # ------------------------------------------- Derive Longest flow path for each subbasin
                # Create Longest Path Feature Class
                arcpy.CreateFeatureClass_management(watershedFD, FlowLengthName, "POLYLINE")
                arcpy.AddField_management(Flow_Length, "Subbasin", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED")
                arcpy.AddField_management(Flow_Length, "Reach", "LONG", "", "", "", "", "NULLABLE", "NON_REQUIRED")
                arcpy.AddField_management(Flow_Length, "Type", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED")
                arcpy.AddField_management(Flow_Length, "Length_ft", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED")

                AddMsgAndPrint("\nCalculating watershed flow path(s)")

                # -------------------------------------------- Raster Flow Length Analysis
                # Set mask to watershed to limit calculations
                arcpy.env.mask = watershed

                # Calculate total upstream flow length on FlowDir grid
                UP_GRID = FlowLength(FlowDir, "UPSTREAM")

                # Calculate total downsteam flow length on FlowDir grid
                DOWN_GRID = FlowLength(FlowDir, DOWN_GRID, "DOWNSTREAM")

                # Sum total upstream and downstream flow lengths
                PLUS_GRID = Plus(UP_GRID, DOWN_GRID)

                # Get Maximum downstream flow length in each subbasin
                MAX_GRID = ZonalStatistics(watershed, "Subbasin", DOWN_GRID, "MAXIMUM", "DATA")

                # Subtract tolerance from Maximum flow length -- where do you get tolerance from?
                MINUS_GRID = Minus(MAX_GRID, "0.3")

                # Extract cells with positive difference to isolate longest flow path(s)
                LONGPATH = GreaterThan(PLUS_GRID, MINUS_GRID)
                LP_Extract = Con(LONGPATH, LONGPATH, "", "\"VALUE\" = 1")

                # Try to use Stream to Feature process to convert the raster Con result to a line (DUE TO 10.5.0 BUG)
                LFP_StreamLink = StreamLink(LP_Extract, FlowDir)
                LongpathTemp = StreamToFeature(LFP_StreamLink, FlowDir, "NO_SIMPLIFY")

                # Smooth and Dissolve results
                LP_Smooth = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("LP_Smooth",data_type="FeatureClass",workspace=watershedGDB_path))
                arcpy.SmoothLine_management(LongpathTemp, LP_Smooth, "PAEK", "100 Feet", "FIXED_CLOSED_ENDPOINT", "NO_CHECK")

                # Intersect with watershed to get subbasin ID
                LongpathTemp1 = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("LongpathTemp1",data_type="FeatureClass",workspace=watershedGDB_path))
                arcpy.Intersect_analysis(LP_Smooth + "; " + watershed, LongpathTemp1, "ALL", "", "INPUT")

                # Dissolve to create single lines for each subbasin
                arcpy.Dissolve_management(LongpathTemp1, Flow_Length, "Subbasin", "", "MULTI_PART", "DISSOLVE_LINES")

                # Add Fields / attributes & calculate length in feet
                arcpy.AddField_management(Flow_Length, "Reach", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED")
                objectIDfld2 = "!" + arcpy.da.Describe(Flow_Length)['OIDFieldName'] + "!"
                arcpy.CalculateField_management(Flow_Length, "Reach", objectIDfld2", "PYTHON3")

                arcpy.AddField_management(Flow_Length, "Type", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
                arcpy.CalculateField_management(Flow_Length, "Type", '"Natural Watercourse"', "PYTHON3", "")

                arcpy.AddField_management(Flow_Length, "Length_ft", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

                if linearUnits == "Meters":
                    arcpy.CalculateField_management(Flow_Length, "Length_ft", "[shape_length] * 3.28084", "PYTHON3", "")
                else:
                    arcpy.CalculateField_management(Flow_Length, "Length_ft", "[shape_length]", "PYTHON3", "")

                # ---------------------------------------------------------------------------------------------- Set up Domains
                # Apply domains to watershed geodatabase and Flow Length fields to aid in user editing
                bDomainTables = True
                ID_Table = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "ID_TABLE")
                Reach_Table = os.path.join(os.path.dirname(sys.argv[0]), "Support.gdb" + os.sep + "REACH_TYPE")

                # If support tables not present skip domains -- user is on their own.
                if not arcpy.Exists(ID_Table):
                    bDomainTables = False

                if not arcpy.Exists(Reach_Table):
                    bDomainTables = False

                if bDomainTables:
                    # describe present domains, estrablish and apply if needed
                    desc = arcpy.describe(watershedGDB_path)
                    listOfDomains = []

                    domains = desc.Domains

                    for domain in domains:
                        listOfDomains.append(domain)

                    del desc, domains

                    if not "Reach_Domain" in listOfDomains:
                        arcpy.TableToDomain_management(ID_Table, "IDENT", "ID_DESC", watershedGDB_path, "Reach_Domain", "Reach_Domain", "REPLACE")

                    if not "Type_Domain" in listOfDomains:
                        arcpy.TableToDomain_management(Reach_Table, "TYPE", "TYPE", watershedGDB_path, "Type_Domain", "Type_Domain", "REPLACE")

                    del listOfDomains
                    del ID_Table
                    del Reach_Table
                    del bDomainTables

                    # Assign domain to flow length fields for User Edits...
                    arcpy.AssignDomainToField_management(Flow_Length, "Reach", "Reach_Domain", "")
                    arcpy.AssignDomainToField_management(Flow_Length, "TYPE", "Type_Domain", "")

                #---------------------------------------------------------------------- Flow Path Calculations complete
                AddMsgAndPrint("\n\tSuccessfully extracted watershed flow path(s)",0)

            except:
                # If Calc LHL fails prompt user to delineate manually and continue...  ...capture error for reference
                AddMsgAndPrint("\nUnable to Calculate Flow Path(s) .. You will have to trace your stream network to create them manually.."+ arcpy.GetMessages(2),2)
                AddMsgAndPrint("\nContinuing....",1)

        # ----------------------------------------------------------------------------------------------- Calculate Average Slope
        calcAvgSlope = False

        # ----------------------------- Retrieve Z Units from AOI
        if arcpy.Exists(projectAOI):

            rows = arcpy.searchcursor(projectAOI)
            row = rows.next()
            zUnits = row.Z_UNITS

            del rows
            del row

            # Assign proper Z factor
            if zUnits == "Meters":

                if units == "Feet":
                    Zfactor = 3.28084
                if units == "Meters":
                    Zfactor = 1

            elif zUnits == "Feet":

                if units == "Feet":
                    Zfactor = 1
                if units == "Meters":
                    Zfactor = 0.3048

            elif zUnits == "Centimeters":

                if units == "Feet":
                    Zfactor = 30.48
                if units == "Meters":
                    Zfactor = 0.01

            # zUnits must be inches; no more choices
            else:

                if units == "Feet":
                    Zfactor = 12
                if units == "Meters":
                    Zfactor = 39.3701
        else:
            Zfactor = 0 # trapped for below so if Project AOI not present slope isnt calculated

        # --------------------------------------------------------------------------------------------------------
        if Zfactor > 0:
            AddMsgAndPrint("\nCalculating average slope...",1)

            if arcpy.Exists(DEMsmooth):

                # Use smoothed DEM to calculate slope to remove exteraneous values
                arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

                arcpy.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
                arcpy.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
                arcpy.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
                calcAvgSlope = True

                # Delete unwanted rasters
                arcpy.Delete_management(DEMsmooth)
                arcpy.Delete_management(wtshdDEMsmooth)
                arcpy.Delete_management(slopeGrid)

            elif arcpy.Exists(DEM_aoi):

                # Run Focal Statistics on the DEM_aoi to remove exteraneous values
                arcpy.focalstatistics_sa(DEM_aoi, DEMsmooth,"RECTANGLE 3 3 CELL","MEAN","DATA")

                arcpy.AddField_management(watershed, "Avg_Slope", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

                arcpy.ExtractByMask_sa(DEMsmooth, watershed, wtshdDEMsmooth)
                arcpy.Slope_sa(wtshdDEMsmooth, slopeGrid, "PERCENT_RISE", Zfactor)
                arcpy.ZonalStatisticsAsTable_sa(watershed, "Subbasin", slopeGrid, slopeStats, "DATA")
                calcAvgSlope = True

                # Delete unwanted rasters
                arcpy.Delete_management(DEMsmooth)
                arcpy.Delete_management(wtshdDEMsmooth)
                arcpy.Delete_management(slopeGrid)

            else:
                AddMsgAndPrint("\nMissing DEMsmooth or DEM_aoi from FGDB. Could not Calculate Average Slope",2)

        else:
            AddMsgAndPrint("\nMissing Project AOI from FGDB. Could not retrieve Z Factor to Calculate Average Slope",2)

        # -------------------------------------------------------------------------------------- Update Watershed FC with Average Slope
        if calcAvgSlope:

            # go through each zonal Stat record and pull out the Mean value
            rows = arcpy.searchcursor(slopeStats)
            row = rows.next()

            AddMsgAndPrint("\n\tSuccessfully Calculated Average Slope",0)

            AddMsgAndPrint("\nCreate Watershed Results:",1)
            AddMsgAndPrint("\n===================================================",0)
            AddMsgAndPrint("\tUser Watershed: " + str(watershedOut),0)

            while row:
                wtshdID = row.OBJECTID

                # zonal stats doesnt generate "Value" with the 9.3 geoprocessor
                if len(arcpy.ListFields(slopeStats,"Value")) > 0:
                    zonalValue = row.VALUE

                else:
                    zonalValue = row.SUBBASIN

                zonalMeanValue = row.MEAN

                whereclause = "Subbasin = " + str(zonalValue)
                wtshdRows = arcpy.UpdateCursor(watershed,whereclause)
                wtshdRow = wtshdRows.next()

                # Pass the Mean value from the zonalStat table to the watershed FC.
                while wtshdRow:

                    wtshdRow.Avg_Slope = zonalMeanValue
                    wtshdRows.UpdateRow(wtshdRow)

                    # Inform the user of Watershed Acres, area and avg. slope
                    AddMsgAndPrint("\n\tSubbasin: " + str(wtshdRow.OBJECTID),0)
                    AddMsgAndPrint("\t\tAcres: " + str(splitThousands(round(wtshdRow.Acres,2))),0)
                    AddMsgAndPrint("\t\tArea: " + str(splitThousands(round(wtshdRow.Shape_Area,2))) + " Sq. " + units,0)
                    AddMsgAndPrint("\t\tAvg. Slope: " + str(round(zonalMeanValue,2)),0)

                    break

                row = rows.next()

                del wtshdID
                del zonalValue
                del zonalMeanValue
                del whereclause
                del wtshdRows
                del wtshdRow

            del rows
            del row
            AddMsgAndPrint("\n===================================================",0)
            arcpy.Delete_management(slopeStats)

        import time
        time.sleep(5)

        # ------------------------------------------------------------------------------------------------ Compact FGDB
        try:
            arcpy.compact_management(watershedGDB_path)
            AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),1)
        except:
            pass

        # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
        # Set paths for derived layers
        arcpy.SetParameterAsText(4, outletFC)
        arcpy.SetParameterAsText(5, watershed)

        if bCalcLHL:
            arcpy.SetParameterAsText(6, Flow_Length)
            del Flow_Length

        AddMsgAndPrint("\nAdding Layers to ArcMap",1)
        AddMsgAndPrint("\n",1)

        arcpy.RefreshCatalog(watershedGDB_path)

        # Restore original environments
        arcpy.extent = tempExtent
        arcpy.mask = tempMask
        arcpy.SnapRaster = tempSnapRaster
        arcpy.CellSize = tempCellSize
        arcpy.OutputCoordinateSystem = tempCoordSys

    except SystemExit:
        pass

    except KeyboardInterrupt:
        AddMsgAndPrint("Interruption requested....exiting")

    except:
        print_exception()
