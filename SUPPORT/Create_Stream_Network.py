# ==========================================================================================
# Name: Create_Stream_Network.py
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

#
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

    try:
        import getpass, time

        arcInfo = arcpy.GetInstallInfo()  # dict of ArcGIS Pro information

        f = open(textFilePath,'a+')
        f.write("\n################################################################################################################\n")
        f.write("Executing \"2.Create Stream Network\" Tool\n")
        f.write("User Name: " + getpass.getuser() + "\n")
        f.write("Date Executed: " + time.ctime() + "\n")
        f.write(arcInfo['ProductName'] + ": " + arcInfo['Version'])
        f.write("User Parameters:\n")
        f.write("\tWorkspace: " + userWorkspace + "\n")
        f.write("\tDem_AOI: " + DEM_aoi + "\n")

        if culvertsExist:

            if int(arcpy.GetCount_management(burnCulverts).getOutput(0)) > 1:
                f.write("\tCulverts Digitized: " + str(numOfCulverts) + "\n")
            else:
                f.write("\tCulverts Digitized: 0\n")

        else:
            f.write("\tCulverts Digitized: 0\n")

        f.write("\tStream Threshold: " + str(streamThreshold) + "\n")

        f.close
        del f

    except:
        print_exception()
        exit()

## ================================================================================================================
def determineOverlap(culvertLayer):
    # This function will compute a geometric intersection of the project_AOI boundary and the culvert
    # layer to determine overlap.

    try:
        # Make a layer from the project_AOI
        if gp.exists("AOI_lyr"):
            gp.delete_management("AOI_lyr")

        gp.MakeFeatureLayer(projectAOI_path,"AOI_lyr")

        if gp.exists("culvertsTempLyr"):
            gp.delete_management("culvertsTempLyr")

        gp.MakeFeatureLayer(culvertLayer,"culvertsTempLyr")

        numOfCulverts = int((gp.GetCount_management(culvertLayer)).GetOutput(0))

        # Select all culverts that are completely within the AOI polygon
        gp.SelectLayerByLocation("culvertsTempLyr", "completely_within", "AOI_lyr")
        numOfCulvertsWithinAOI = int((gp.GetCount_management("culvertsTempLyr")).GetOutput(0))

        # There are no Culverts completely in AOI; may be some on the AOI boundary
        if numOfCulvertsWithinAOI == 0:

            gp.SelectLayerByAttribute_management("culvertsTempLyr", "CLEAR_SELECTION", "")
            gp.SelectLayerByLocation("culvertsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            # Check for culverts on the AOI boundary
            numOfIntersectedCulverts = int((gp.GetCount_management("culvertsTempLyr")).GetOutput(0))

            # No culverts within AOI or intersecting AOI
            if numOfIntersectedCulverts == 0:

                AddMsgAndPrint("\tAll Culverts are outside of your Area of Interest",0)
                AddMsgAndPrint("\tNo culverts will be used to hydro enforce " + os.path.basename(DEM_aoi),0)

                gp.delete_management("AOI_lyr")
                gp.delete_management("culvertsTempLyr")
                del numOfCulverts
                del numOfCulvertsWithinAOI
                del numOfIntersectedCulverts

                return False

            # There are some culverts on AOI boundary but at least one culvert completely outside AOI
            else:

                # All Culverts are intersecting the AOI
                if numOfCulverts == numOfIntersectedCulverts:

                    AddMsgAndPrint("\tAll Culvert(s) are intersecting the AOI Boundary",0)
                    AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

                 # Some Culverts intersecting AOI and some completely outside.
                else:

                    AddMsgAndPrint("\t" + str(numOfCulverts) + " Culverts digitized",0)
                    AddMsgAndPrint("\n\tThere is " + str(numOfCulverts - numOfIntersectedCulverts) + " culvert(s) completely outside the AOI Boundary",0)
                    AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

                clippedCulverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedCulverts"
                gp.Clip_analysis(culvertLayer, projectAOI_path, clippedCulverts)

                gp.delete_management("AOI_lyr")
                gp.delete_management("culvertsTempLyr")
                del numOfCulverts
                del numOfCulvertsWithinAOI
                del numOfIntersectedCulverts

                gp.delete_management(culverts)
                gp.rename(clippedCulverts,culverts)

                AddMsgAndPrint("\n\t" + str(int(gp.GetCount_management(culverts).getOutput(0))) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)

                return True

        # all culverts are completely within AOI; Ideal scenario
        elif numOfCulvertsWithinAOI == numOfCulverts:

            AddMsgAndPrint("\n\t" + str(numOfCulverts) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)

            gp.delete_management("AOI_lyr")
            gp.delete_management("culvertsTempLyr")
            del numOfCulverts
            del numOfCulvertsWithinAOI

            return True

        # combination of scenarios.  Would require multiple outlets to have been digitized. A
        # will be required.
        else:

            gp.SelectLayerByAttribute_management("culvertsTempLyr", "CLEAR_SELECTION", "")
            gp.SelectLayerByLocation("culvertsTempLyr", "crossed_by_the_outline_of", "AOI_lyr")

            numOfIntersectedCulverts = int((gp.GetCount_management("culvertsTempLyr")).GetOutput(0))

            AddMsgAndPrint("\t" + str(numOfCulverts) + " Culverts digitized",0)

            # there are some culverts crossing the AOI boundary and some within.
            if numOfIntersectedCulverts > 0 and numOfCulvertsWithinAOI > 0:

                AddMsgAndPrint("\n\tThere is " + str(numOfIntersectedCulverts) + " culvert(s) intersecting the AOI Boundary",0)
                AddMsgAndPrint("\tCulverts will be clipped to AOI",0)

            # there are some culverts outside the AOI boundary and some within.
            elif numOfIntersectedCulverts == 0 and numOfCulvertsWithinAOI > 0:

                AddMsgAndPrint("\n\tThere is " + str(numOfCulverts - numOfCulvertsWithinAOI) + " culvert(s) completely outside the AOI Boundary",0)
                AddMsgAndPrint("\tCulverts(s) will be clipped to AOI",0)

            # All outlets are are intersecting the AOI boundary
            else:
                AddMsgAndPrint("\n\tOutlet(s) is intersecting the AOI Boundary and will be clipped to AOI",0)

            clippedCulverts = watershedGDB_path + os.sep + "Layers" + os.sep + projectName + "_clippedCulverts"
            gp.Clip_analysis(culvertLayer, projectAOI_path, clippedCulverts)

            gp.delete_management("AOI_lyr")
            gp.delete_management("culvertsTempLyr")
            del numOfCulverts
            del numOfCulvertsWithinAOI
            del numOfIntersectedCulverts

            gp.delete_management(culverts)
            gp.rename(clippedCulverts,culverts)

            AddMsgAndPrint("\n\t" + str(int(gp.GetCount_management(culverts).getOutput(0))) + " Culvert(s) will be used to hydro enforce " + os.path.basename(DEM_aoi),0)

            return True

    except:
        AddMsgAndPrint("\nFailed to determine overlap with " + projectAOI_path + ". (determineOverlap)",2)
        print_exception()
        AddMsgAndPrint("No culverts will be used to hydro enforce " + os.path.basename(DEM_aoi),2)
        return False

## ================================================================================================================
# Import system modules
import arcpy, sys, os, traceback
from arcpy.sa import *

if __name__ == '__main__':

    try:

        # Check out Spatial Analyst License
        if arcpy.CheckExtension("spatial") == "Available":
            arcpy.CheckOutExtension("spatial")
        else:
            arcpy.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu\n",2)
            exit()

        # --------------------------------------------------------------------------------------------- Input Parameters
        AOI = arcpy.GetParameterAsText(0)
        burnCulverts = arcpy.GetParameterAsText(1)
        streamThreshold = arcpy.GetParameterAsText(2)

        # Uncomment the following  3 lines to run from pythonWin
##        AOI = r'C:\flex\flex_EngTools.gdb\Layers\Project_AOI'
##        burnCulverts = ""
##        streamThreshold = 1

        # Set environmental variables
        arcpy.env.parallelProcessingFactor = "75%"
        arcpy.env.overwriteOutput = True

        # --------------------------------------------------------------------------------------------- Define Variables
        aoiDesc = arcpy.da.Describe(AOI)
        aoiPath = aoiDesc['catalogPath']
        aoiName = aoiDesc['name']
        aoiExtent = aoiDesc['extent']

        # exit if AOI doesn't follow file structure
        if aoiPath.find('.gdb') == -1 or not aoiName.endswith('AOI'):
            AddMsgAndPrint("\n\n" + aoiName + " is an invalid project_AOI Feature",2)
            AddMsgAndPrint("Run Watershed Delineation Tool #1. Define Area of Interest\n\n",2)
            exit()

        watershedGDB_path = aoiPath[:aoiPath.find('.gdb')+4]
        watershedGDB_name = os.path.basename(watershedGDB_path)
        watershedGDB_FDpath = watershedGDB_path + os.sep + 'Layers'
        userWorkspace = os.path.dirname(watershedGDB_path)
        projectName = arcpy.ValidateTableName(os.path.basename(userWorkspace).replace(" ","_"))

        # --------------------------------------------------------------- Datasets
        # ------------------------------ Permanent Datasets
        culverts = watershedGDB_FDpath + os.sep + projectName + "_Culverts"
        streams =watershedGDB_FDpath + os.sep + projectName + "_Streams"
        DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
        hydroDEM = watershedGDB_path + os.sep + "hydroDEM"
        Fill_hydroDEM = watershedGDB_path + os.sep + "Fill_hydroDEM"
        FlowAccum = watershedGDB_path + os.sep + "flowAccumulation"
        FlowDir = watershedGDB_path + os.sep + "flowDirection"

        # ----------------------------- Temporary Datasets
        culvertRaster = watershedGDB_path + os.sep + "culvertRaster"
        conFlowAccum = watershedGDB_path + os.sep + "conFlowAccum"
        streamLink = watershedGDB_path + os.sep + "streamLink"

        # check if culverts exist.  This is only needed b/c the script may be executed manually
        numOfCulverts = int(arcpy.GetCount_management(burnCulverts).getOutput(0))
        if burnCulverts == "#" or burnCulverts == "" or burnCulverts == False or numOfCulverts < 1 or len(burnCulverts) < 1:
            culvertsExist = False
        else:
            culvertsExist = True

        # Path of Log file
        textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

        # record basic user inputs and settings to log file for future purposes
        logBasicSettings()

        # ---------------------------------------------------------------------------------------------------------------------- Check Parameters
        # Make sure the FGDB and DEM_aoi exists from Define Area of Interest tool.
        if not arcpy.Exists(watershedGDB_path) or not arcpy.Exists(DEM_aoi):
            AddMsgAndPrint("\nThe \"" + str(projectName) + "_DEM\" raster file or the File Geodatabase from Step 1 was not found",2)
            AddMsgAndPrint("Run Watershed Delineation Tool #1: Define Area of Interest",2)
            exit()

        # ----------------------------------------------------------------------------------------------------------------------- Delete old datasets

        datasetsToRemove = (streams,Fill_hydroDEM,hydroDEM,FlowAccum,FlowDir,culvertsTemp,culvertBuffered,culvertRaster,conFlowAccum,streamLink)

        x = 0
        for dataset in datasetsToRemove:

            if arcpy.Exists(dataset):

                if x < 1:
                    AddMsgAndPrint("\nRemoving old datasets from FGDB: " + watershedGDB_name)
                    x += 1

                try:
                    arcpy.Delete_management(dataset)
                    AddMsgAndPrint("\tDeleting....." + os.path.basename(dataset))
                except:
                    pass

        # -------------------------------------------------------------------------------------------------------------------- Retrieve DEM Properties
        demDesc = arcpy.da.Describe(DEM_aoi)
        demName = demDesc['name']
        demPath = demDesc['catalogPath']
        demCellSize = demDesc['meanCellWidth']
        demFormat = demDesc['format']
        demSR = demDesc['spatialReference']
        demCoordType = demSR.type
        linearUnits = demSR.linearUnitName

        arcpy.env.extent = "MINOF"
        arcpy.env.cellSize = demCellSize
        arcpy.env.snapRaster = demPath
        arcpy.env.outputCoordinateSystem = demSR

        # ------------------------------------------------------------------------------------------------------------------------ Incorporate Culverts into DEM
        reuseCulverts = False
        # Culverts will be incorporated into the DEM_aoi if at least 1 culvert is provided.
        if culvertsExist:

            if numOfCulverts > 0:

                # if paths are not the same then assume culverts were manually digitized
                # or input is some from some other feature class/shapefile
                if not arcpy.da.Describe(burnCulverts)['catalogPath'] == culverts:

                    # delete the culverts feature class; new one will be created
                    if arcpy.Exists(culverts):
                        arcpy.Delete_management(culverts)
                        arcpy.CopyFeatures_management(burnCulverts, culverts)
                        AddMsgAndPrint("\nSuccessfully Recreated \"Culverts\" feature class.",1)

                    else:
                        arcpy.CopyFeatures_management(burnCulverts, culverts)
                        AddMsgAndPrint("\nSuccessfully Created \"Culverts\" feature class",1)

                # paths are the same therefore input was from within FGDB
                else:
                    AddMsgAndPrint("\nUsing Existing \"Culverts\" feature class:",1)
                    reuseCulverts = True

                # --------------------------------------------------------------------- determine overlap of culverts & AOI
                AddMsgAndPrint("\nChecking Placement of Culverts")

                # True: culverts are properly inside of AOI
                # False: culverts are intersecting AOI or outside
                bCulvertIntersection = True

                for row in arcpy.da.SearchCursor(culverts,['SHAPE@']):
                    culvertExtent = row[0].extent
                    if not aoiExtent.contains(culvertExtent):
                        bCulvertIntersection = False
                        break

                # ------------------------------------------------------------------- Buffer Culverts
                if bCulvertIntersection:
                    cellSize = demCellSize

                    # determine linear units to set buffer value to the equivalent of 1 pixel
                    if linearUnits in ('Meter','Meters'):
                        bufferSize = str(cellSize) + " Meters"
                        AddMsgAndPrint("\nBuffer size applied on Culverts: " + str(cellSize) + " Meter(s)")

                    elif linearUnits in ('Foot','Foot_US','Feet'):
                        bufferSize = str(cellSize) + " Feet"
                        AddMsgAndPrint("\nBuffer size applied on Culverts: " + bufferSize)

                    else:
                        bufferSize = str(cellSize) + " Unknown"
                        AddMsgAndPrint("\nBuffer size applied on Culverts: Equivalent of 1 pixel since linear units are unknown",0)

                    # Buffer the culverts to 1 pixel
                    culvertBuffered = "in_memory" + os.sep + os.path.basename(arcpy.CreateScratchName("culvertBuffered",data_type="FeatureClass",workspace=watershedGDB_path))
                    arcpy.Buffer_analysis(culverts, culvertBuffered, bufferSize, "FULL", "ROUND", "NONE", "")

                    # Dummy field just to execute Zonal stats on each feature
                    expression = "!" + arcpy.da.Describe(culvertBuffered)['OIDFieldName'] + "!"
                    arcpy.AddField_management(culvertBuffered, "ZONE", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED")
                    arcpy.CalculateField_management(culvertBuffered, "ZONE", expression, "PYTHON3")

                    # Get the minimum elevation value for each culvert
                    outZonalStats = ZonalStatistics(culvertBuffered, "ZONE", DEM_aoi, "MINIMUM", "NODATA")
                    AddMsgAndPrint("\nApplying the minimum Zonal DEM Value to the Culverts")

                    # Elevation cells that overlap the culverts will get the minimum elevation value
                    mosaicList = DEM_aoi + ";" + outZonalStats
                    arcpy.MosaicToNewRaster_management(mosaicList, watershedGDB_path, "hydroDEM", "#", "32_BIT_FLOAT", cellSize, "1", "LAST", "#")
                    AddMsgAndPrint("\nFusing Culverts and " + os.path.basename(DEM_aoi) + " to create " + os.path.basename(hydroDEM),1)

                    gp.Fill_sa(hydroDEM, Fill_hydroDEM)
                    AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections",1)

                # No Culverts will be used due to no overlap or determining overlap error.
                else:
                    cellSize = gp.Describe(DEM_aoi).MeanCellWidth
                    gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
                    AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(hydroDEM) + " to remove small imperfections",1)

                del proceed

            # No culverts were detected.
            else:
                AddMsgAndPrint("\nNo Culverts detected!",1)
                cellSize = gp.Describe(DEM_aoi).MeanCellWidth
                gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
                AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections",1)

        else:
            AddMsgAndPrint("\nNo Culverts detected!",1)
            cellSize = gp.Describe(DEM_aoi).MeanCellWidth
            gp.Fill_sa(DEM_aoi, Fill_hydroDEM)
            AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to remove small imperfections",1)

        # ---------------------------------------------------------------------------------------------- Create Stream Network
        # Create Flow Direction Grid...
        gp.FlowDirection_sa(Fill_hydroDEM, FlowDir, "NORMAL", "")

        # Create Flow Accumulation Grid...
        gp.FlowAccumulation_sa(FlowDir, FlowAccum, "", "INTEGER")

        # Need to compute a histogram for the FlowAccumulation layer so that the full range of values is captured for subsequent stream generation
        # This tries to fix a bug of the primary channel not generating for large watersheds with high values in flow accumulation grid
        gp.CalculateStatistics_management(FlowAccum)

        AddMsgAndPrint("\nSuccessfully created Flow Accumulation and Flow Direction",1)

        # stream link will be created using pixels that have a flow accumulation greater than the
        # user-specified acre threshold
        if streamThreshold > 0:

            # Calculating flow accumulation value for appropriate acre threshold
            if gp.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Meter":
                acreThresholdVal = round((float(streamThreshold) * 4046.85642)/(cellSize*cellSize))
                conExpression = "Value >= " + str(acreThresholdVal)

            elif gp.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot":
                acreThresholdVal = round((float(streamThreshold) * 43560)/(cellSize*cellSize))
                conExpression = "Value >= " + str(acreThresholdVal)

            elif gp.Describe(DEM_aoi).SpatialReference.LinearUnitName == "Foot_US":
                acreThresholdVal = round((float(streamThreshold) * 43560)/(cellSize*cellSize))
                conExpression = "Value >= " + str(acreThresholdVal)

            else:
                acreThresholdVal = round(float(streamThreshold)/(cellSize*cellSize))
                conExpression = "Value >= " + str(acreThresholdVal)



            # Select all cells that are greater than conExpression
            gp.Con_sa(FlowAccum, FlowAccum, conFlowAccum, "", conExpression)

            # Create Stream Link Works
            gp.StreamLink_sa(conFlowAccum, FlowDir, streamLink)
            del conExpression

        # All values in flowAccum will be used to create stream link
        else:
            acreThresholdVal = 0
            gp.StreamLink_sa(FlowAccum, FlowDir, streamLink)

        # Converts a raster representing a linear network to features representing the linear network.
        # creates field grid_code
        gp.StreamToFeature_sa(streamLink, FlowDir, streams, "SIMPLIFY")
        AddMsgAndPrint("\nSuccessfully created stream linear network using a flow accumulation value >= " + str(acreThresholdVal),1)

        # ------------------------------------------------------------------------------------------------ Delete unwanted datasets
        gp.delete_management(Fill_hydroDEM)
        gp.delete_management(conFlowAccum)
        gp.delete_management(streamLink)

        # ------------------------------------------------------------------------------------------------ Compact FGDB
        try:
            gp.compact_management(watershedGDB_path)
            AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),1)
        except:
            pass

        # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap

        gp.SetParameterAsText(3, streams)

        if not reuseCulverts:
            gp.SetParameterAsText(4, culverts)

        AddMsgAndPrint("\nAdding Layers to ArcMap",1)
        AddMsgAndPrint("",1)

        # ------------------------------------------------------------------------------------------------ Clean up Time!
        gp.RefreshCatalog(watershedGDB_path)

        # Restore original environments
        gp.extent = tempExtent
        gp.mask = tempMask
        gp.SnapRaster = tempSnapRaster
        gp.CellSize = tempCellSize
        gp.OutputCoordinateSystem = tempCoordSys

    except:
        print_exception()









