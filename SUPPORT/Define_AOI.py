# Define_AOI.py
## ===============================================================================================================
def print_exception():
    
    tb = sys.exc_info()[2]
    l = traceback.format_tb(tb)
    l.reverse()
    tbinfo = "".join(l)
    AddMsgAndPrint("\n----------------------------------- ERROR Start -----------------------------------",2)
    AddMsgAndPrint("Traceback Info: \n" + tbinfo + "Error Info: \n    " +  str(sys.exc_type)+ ": " + str(sys.exc_value) + "",2)
    AddMsgAndPrint("------------------------------------- ERROR End -----------------------------------\n",2)

## ================================================================================================================    
def AddMsgAndPrint(msg, severity=0):
    # prints message to screen if run as a python script
    # Adds tool message to the geoprocessor
    # 
    # Split the message on \n first, so that if it's multiple lines, a GPMessage will be added for each line

    print msg
    
    try:

        f = open(textFilePath,'a+')
        f.write(msg + " \n")
        f.close

        del f

        if ArcGIS10:
            if not msg.find("\n") < 0 and msg.find("\n") < 4:
                gp.AddMessage(" ")
        
        for string in msg.split('\n'):
            
            # Add a geoprocessing message (in case this is run as a tool)
            if severity == 0:
                gp.AddMessage(string)
                
            elif severity == 1:
                gp.AddWarning(string)
                
            elif severity == 2:
                gp.AddMessage("    ")
                gp.AddError(string)

        if ArcGIS10:
            if msg.find("\n") > 4:
                gp.AddMessage(" ")
                
    except:
        pass

## ================================================================================================================
def logBasicSettings():    
    # record basic user inputs and settings to log file for future purposes

    import getpass, time

    f = open(textFilePath,'a+')
    f.write("\n################################################################################################################\n")
    f.write("Executing \"1.Define Area of Interest\" tool\n")
    f.write("User Name: " + getpass.getuser() + "\n")
    f.write("Date Executed: " + time.ctime() + "\n")
    f.write("ArcGIS Version: " + str(version) + "\n")
    f.write("User Parameters:\n")
    f.write("\tWorkspace: " + userWorkspace + "\n")
    f.write("\tInput Dem: " + gp.Describe(inputDEM).CatalogPath + "\n")
    
    if len(interval) > 0:
        f.write("\tContour Interval: " + str(interval) + "\n")
    else:
        f.write("\tContour Interval: NOT SPECIFIED\n")
        
    if len(zUnits) > 0:
        f.write("\tElevation Z-units: " + zUnits + "\n")

    else:
        f.write("\tElevation Z-units: BLANK" + "\n")
    
    f.close
    del f

## ================================================================================================================
def splitThousands(someNumber):
# will determine where to put a thousands seperator if one is needed.
# Input is an integer.  Integer with or without thousands seperator is returned.

    try:
        return re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1]        

## --------------Use this code in case you want to preserve numbers after the decimal.  I decided to just round up
##        # Number is a floating number        
##        if str(someNumber).find("."):
##            
##            dropDecimals = int(someNumber)
##            numberStr = str(someNumber)
##
##            afterDecimal = str(numberStr[numberStr.find("."):numberStr.find(".")+2])
##            beforeDecimalCommas = re.sub(r'(\d{3})(?=\d)', r'\1,', str(dropDecimals)[::-1])[::-1]
##
##            return beforeDecimalCommas + afterDecimal
##
##        # Number is a whole number    
##        else:
##            return int(re.sub(r'(\d{3})(?=\d)', r'\1,', str(someNumber)[::-1])[::-1])
    
    except:
        print_exception()
        return someNumber

## ================================================================================================================
# Import system modules
import sys, os, arcgisscripting, traceback, re

# Create the Geoprocessor object
gp = arcgisscripting.create(9.3)
gp.OverWriteOutput = 1

# Used to determine ArcGIS version
d = gp.GetInstallInfo('desktop')

keys = d.keys()

for k in keys:

    if k == "Version":

        version = " \nArcGIS %s : %s" % (k, d[k])

        if version.find("10.") > 0:
            ArcGIS10 = True

        else:
            ArcGIS10 = False

        break 

del d, keys
   
if version < 9.3:
    gp.AddError("\nThis tool requires ArcGIS version 9.3 or Greater.....EXITING")
    sys.exit("")           

try:
    # Check out Spatial Analyst License        
    if gp.CheckExtension("spatial") == "Available":
        gp.CheckOutExtension("spatial")
    else:
        gp.AddError("Spatial Analyst Extension not enabled. Please enable Spatial analyst from the Tools/Extensions menu\n")
        sys.exit("")

    # --------------------------------------------------------------------------------------------- Input Parameters
    userWorkspace = gp.GetParameterAsText(0)
    inputDEM = gp.GetParameterAsText(1)         #DEM
    zUnits = gp.GetParameterAsText(2)           # elevation z units of input DEM
    AOI = gp.GetParameterAsText(3)              # AOI that was drawn
    interval = gp.GetParameterAsText(4)         # user defined contour interval


    # Uncomment the following 5 lines to run from pythonWin           
##    userWorkspace = r'C:\flex'
##    inputDEM = r'G:\MLRAData\elevation\WI_Dane\Dane_LiDAR.gdb\wi025_dem_3m_utm16'  #DEM
##    AOI = r'C:\flex\test10.shp'                 # AOI  
##    interval = 10                                 # user defined contour interval
##    zUnits = "Meters"

    # --------------------------------------------------------------------------------------------- Define Variables
    projectName = gp.ValidateTablename(os.path.basename(userWorkspace).replace(" ","_"))
    textFilePath = userWorkspace + os.sep + projectName + "_EngTools.txt"

    watershedGDB_name = os.path.basename(userWorkspace).replace(" ","_") + "_EngTools.gdb"  # replace spaces for new FGDB name
    watershedGDB_path = userWorkspace + os.sep + watershedGDB_name
    watershedFD = watershedGDB_path + os.sep + "Layers"

    # ---------------------------------------------------------- Datasets
    # ------------------------------ Permanent Datasets
    projectAOI = watershedFD + os.sep + projectName + "_AOI"
    Contours = watershedFD + os.sep + projectName + "_Contours_" + str(interval.replace(".","_")) + "ft"
    DEM_aoi = watershedGDB_path + os.sep + projectName + "_DEM"
    Hillshade = watershedGDB_path + os.sep + projectName + "_Hillshade"
    depthGrid = watershedGDB_path + os.sep + projectName + "_DepthGrid"

    # ----------------------------- Temporary Datasets
    DEMsmooth = watershedGDB_path + os.sep + "DEMsmooth"
    aoiTemp = watershedFD + os.sep + "aoiTemp"
    ContoursTemp = watershedFD + os.sep + "ContoursTemp"
    Fill_DEMaoi = watershedGDB_path + os.sep + "Fill_DEMaoi"
    FilMinus = watershedGDB_path + os.sep + "FilMinus"

    # ------------------------------- Map Layers
    aoiOut = "" + projectName + "_AOI"
    contoursOut = "" + projectName + "_Contours"
    demOut = "" + projectName + "_DEM"
    hillshadeOut = "" + projectName + "_Hillshade"
    depthOut = "" + projectName + "_DepthGrid"    

    # record basic user inputs and settings to log file for future purposes
    logBasicSettings()

    # ---------------------------------------------------------------------------------------------- Count the number of features in AOI
    # Exit if AOI contains more than 1 digitized area.
    if int(gp.GetCount_management(AOI).getOutput(0)) > 1:
        AddMsgAndPrint("\n\nYou can only digitize 1 Area of interest! Please Try Again.",2)
        sys.exit()
        
    # ---------------------------------------------------------------------------------------------- Check DEM Coordinate System and Linear Units
    desc = gp.Describe(inputDEM)
    sr = desc.SpatialReference

    units = sr.LinearUnitName
    cellSize = desc.MeanCellWidth

    if units == "Meter":
        units = "Meters"
    elif units == "Foot":
        units = "Feet"
    elif units == "Foot_US":
        units = "Feet"
    else:
        AddMsgAndPrint("\nCould not determine linear units of DEM....Exiting!",2)
        sys.exit()

    # if zUnits were left blank than assume Z-values are the same as XY units.
    if not len(zUnits) > 0:
        zUnits = units

    AddMsgAndPrint("\nGathering information about DEM: " + os.path.basename(inputDEM)+ ":",1)    

    # Coordinate System must be a Projected type in order to continue.
    # zUnits will determine Zfactor for the creation of foot contours.
    # if XY units differ from Z units then a Zfactor must be calculated to adjust
    # the z units by multiplying by the Zfactor

    if sr.Type == "Projected":
        if zUnits == "Meters":
            Zfactor = 3.280839896       # 3.28 feet in a meter

        elif zUnits == "Centimeters":   # 0.033 feet in a centimeter
            Zfactor = 0.0328084

        elif zUnits == "Inches":        # 0.083 feet in an inch
            Zfactor = 0.0833333

        # z units and XY units are the same thus no conversion is required
        else:
            Zfactor = 1

        AddMsgAndPrint("\tProjection Name: " + sr.Name,0)
        AddMsgAndPrint("\tXY Linear Units: " + units,0)
        AddMsgAndPrint("\tElevation Values (Z): " + zUnits,0) 
        AddMsgAndPrint("\tCell Size: " + str(desc.MeanCellWidth) + " x " + str(desc.MeanCellHeight) + " " + units,0)

    else:
        AddMsgAndPrint("\n\n\t" + os.path.basename(inputDEM) + " is NOT in a projected Coordinate System....EXITING",2)
        sys.exit()
        
    # ----------------------------- Capture User environments
    tempExtent = gp.Extent
    tempMask = gp.mask
    tempSnapRaster = gp.SnapRaster
    tempCellSize = gp.CellSize
    tempCoordSys = gp.OutputCoordinateSystem

    # ----------------------------- Set the following environments
    gp.Extent = "MINOF"
    gp.CellSize = cellSize
    gp.mask = ""
    gp.SnapRaster = inputDEM
    gp.OutputCoordinateSystem = sr
    
    # ---------------------------------------------------------------------------------------------- Delete any project layers from ArcMap
    layersToRemove = (demOut,hillshadeOut,depthOut)#aoiOut,contoursOut,

    x = 0
    for layer in layersToRemove:
        
        if gp.exists(layer):
            if x == 0:
                AddMsgAndPrint("\nRemoving previous layers from your ArcMap session " + watershedGDB_name ,1)
                x+=1
                
            try:
                gp.delete_management(layer)
                AddMsgAndPrint("\tRemoving " + layer + "",0)
            except:
                pass

    del x
    del layer
    del layersToRemove
    
    # ------------------------------------------------------------------------ If project geodatabase exists remove any previous datasets 
    if gp.exists(watershedGDB_path):

        datasetsToRemove = (DEM_aoi,Hillshade,depthGrid,DEMsmooth,ContoursTemp,Fill_DEMaoi,FilMinus)

        x = 0
        for dataset in datasetsToRemove:

            if gp.exists(dataset):

                # Strictly Formatting
                if x < 1:
                    AddMsgAndPrint("\nRemoving old datasets from FGDB: " + watershedGDB_name ,1)
                    x += 1
                    
                try:
                    gp.delete_management(dataset)
                    AddMsgAndPrint("\tDeleting....." + os.path.basename(dataset),0)
                except:
                    pass
                
        del dataset
        del datasetsToRemove
        del x

        if not gp.exists(watershedFD):
            gp.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)

    # ------------------------------------------------------------ If project geodatabase and feature dataset do not exist, create them.
    else:
        # Create project file geodatabase
        gp.CreateFileGDB_management(userWorkspace, watershedGDB_name)
        
        # Create Feature Dataset using spatial reference of input DEM
        gp.CreateFeatureDataset_management(watershedGDB_path, "Layers", sr)
        
        AddMsgAndPrint("\nSuccessfully created File Geodatabase: " + watershedGDB_name,1)
        
    # ----------------------------------------------------------------------------------------------- Create New AOI
    # if AOI path and  projectAOI path are not the same then assume AOI was manually digitized
    # or input is some from some other feature class/shapefile
    if not gp.Describe(AOI).CatalogPath == projectAOI:       

        # delete the existing projectAOI feature class and recreate it.
        if gp.exists(projectAOI):
            
            try:
                gp.delete_management(projectAOI)
                gp.CopyFeatures_management(AOI, projectAOI)
                AddMsgAndPrint("\nSuccessfully Recreated \"" + str(projectName) + "_AOI\" feature class",1)
                
            except:
                print_exception()
                gp.OverWriteOutput = 1
            
        else:
            gp.CopyFeatures_management(AOI, projectAOI)
            AddMsgAndPrint("\nSuccessfully Created \"" + str(projectName) + "_AOI\" feature class",1)

    # paths are the same therefore AOI is projectAOI
    else:
        AddMsgAndPrint("\nUsing Existing \"" + str(projectName) + "_AOI\" feature class:",1)
        
        # Use temp lyr, delete from TOC and copy back to avoid refresh issues in arcmap
        gp.CopyFeatures_management(AOI, aoiTemp)
        
        if gp.Exists(aoiOut):
            gp.Delete_management(aoiOut)
            
        gp.CopyFeatures_management(aoiTemp, projectAOI)
        gp.Delete_management(aoiTemp)
        
    # -------------------------------------------------------------------------------------------- Exit if AOI was not a polygon    
    if gp.Describe(projectAOI).ShapeType != "Polygon":
        AddMsgAndPrint("\n\nYour Area of Interest must be a polygon layer!.....Exiting!",2)
        sys.exit()
  
    # --------------------------------------------------------------------------------------------  Populate AOI with DEM Properties
    # Write input DEM name to AOI 
    if len(gp.ListFields(projectAOI,"INPUT_DEM")) < 1:
        gp.AddField_management(projectAOI, "INPUT_DEM", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        
    gp.CalculateField_management(projectAOI, "INPUT_DEM", "\"" + os.path.basename(inputDEM) +  "\"", "VB", "")
    
    # Write XY Units to AOI
    if len(gp.ListFields(projectAOI,"XY_UNITS")) < 1:
        gp.AddField_management(projectAOI, "XY_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        
    gp.CalculateField_management(projectAOI, "XY_UNITS", "\"" + str(units) + "\"", "VB", "")
    
    # Write Z Units to AOI
    if len(gp.ListFields(projectAOI,"Z_UNITS")) < 1:
        gp.AddField_management(projectAOI, "Z_UNITS", "TEXT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
        
    gp.CalculateField_management(projectAOI, "Z_UNITS", "\"" + str(zUnits) + "\"", "VB", "")

    # Delete unwanted "Id" remanant field
    if len(gp.ListFields(projectAOI,"Id")) > 0:
        
        try:
            gp.DeleteField_management(projectAOI,"Id")
        except:
            pass
    
    # --------------------------------------------------------------- Get the Shape Area to notify user of Area and Acres of AOI
    rows = gp.searchcursor(projectAOI,"","","SHAPE_Area")
    row = rows.next()    

    area = ""

    while row:
        area = row.SHAPE_Area
        break

    del rows
    del row

    if area != 0:

        AddMsgAndPrint("\t" + str(projectName) + "_AOI Area:  " + str(splitThousands(round(area,2))) + " Sq. " + units,0)

        if units == "Meters":
            acres = area/4046.86
            AddMsgAndPrint("\t" + str(projectName) + "_AOI Acres: " + str(splitThousands(round(acres,2))) + " Acres",0)
            del acres

        elif units == "Feet":
            acres = area/43560
            AddMsgAndPrint("\t" + str(projectName) + "_AOI Acres: " + str(splitThousands(round(acres,2))) + " Acres",0)
            del acres

        else:
            AddMsgAndPrint("\tCould not calculate Acres",2)

    del area

    # ------------------------------------------------------------------------------------------------- Clip inputDEM
    gp.ExtractByMask_sa(inputDEM, projectAOI, DEM_aoi)
    AddMsgAndPrint("\nSuccessully Clipped " + os.path.basename(inputDEM) + " using " + os.path.basename(projectAOI),1)

    # ------------------------------------------------------------------------------------------------ Create Smoothed Contours
    # Smooth DEM and Create Contours if user-defined interval is greater than 0 and valid
    createContours = False
    
    if len(interval) > 0:
        
        if interval > 0:
            createContours = True
            
            try:
                float(interval)
            except:
                AddMsgAndPrint("\n\tContour Interval Must be a Number. Contours will NOT be created!",0)
                createContours = False
                
    else:
        createContours = False
        AddMsgAndPrint("\nContours will not be created since interval was not specified or set to 0",0)

        
    if createContours:
        
        # Run Focal Statistics on the DEM_aoi for the purpose of generating smooth contours
        gp.focalstatistics_sa(DEM_aoi, DEMsmooth,"RECTANGLE 3 3 CELL","MEAN","DATA")

        gp.Contour_sa(DEMsmooth, ContoursTemp, interval, "0", Zfactor)
        
        AddMsgAndPrint("\nSuccessfully Created " + str(interval) + " foot Contours from " + os.path.basename(DEM_aoi) + " using a Z-factor of " + str(Zfactor),1)
        
        gp.AddField_management(ContoursTemp, "Index", "DOUBLE", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")

        if gp.exists("ContourLYR"):
            
            try:
                gp.delete_management("ContourLYR")
            except:
                pass
            
        gp.MakeFeatureLayer_management(ContoursTemp,"ContourLYR","","","")

        # Every 4th contour will be indexed to 1
        expression = "MOD( \"CONTOUR\"," + str(float(interval) * 5) + ") = 0"
        
        gp.SelectLayerByAttribute("ContourLYR", "NEW_SELECTION", expression)
        indexValue = 1
        
        gp.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
        del indexValue

        # All othe contours will be indexed to 0
        gp.SelectLayerByAttribute("ContourLYR", "SWITCH_SELECTION", "")
        indexValue = 0
        
        gp.CalculateField_management("ContourLYR", "Index", indexValue, "VB","")
        del indexValue

        # Clear selection and write all contours to a new feature class        
        gp.SelectLayerByAttribute("ContourLYR","CLEAR_SELECTION","")      
        gp.CopyFeatures_management("ContourLYR", Contours)

        # Delete unwanted "Id" remanant field
        if len(gp.ListFields(Contours,"Id")) > 0:
            
            try:
                gp.DeleteField_management(Contours,"Id")
            except:
                pass        

        # Delete unwanted datasets
        gp.delete_management(DEMsmooth)
        gp.delete_management(ContoursTemp)
        gp.delete_management("ContourLYR")
       
        del expression

    # ---------------------------------------------------------------------------------------------- Create Hillshade and Depth Grid
    # Process: Creating Hillshade from DEM_aoi
    gp.HillShade_sa(DEM_aoi, Hillshade, "315", "45", "#", Zfactor)
    AddMsgAndPrint("\nSuccessfully Created Hillshade from " + os.path.basename(DEM_aoi),1)
    fill = False

    try:
        # Fills sinks in DEM_aoi to remove small imperfections in the data.
        gp.Fill_sa(DEM_aoi, Fill_DEMaoi, "")
        AddMsgAndPrint("\nSuccessfully filled sinks in " + os.path.basename(DEM_aoi) + " to create Depth Grid",1)
        fill = True

    except:
        gp.AddError("\n\nError encountered while filling sinks on " + os.path.basename(DEM_aoi) + "\n")
        AddMsgAndPrint("Depth Grid will not be created\n",2)
        print_exception()

    if fill:
        # DEM_aoi - Fill_DEMaoi = FilMinus
        gp.Minus_sa(Fill_DEMaoi, DEM_aoi, FilMinus)

        # Create a Depth Grid; Any pixel where there is a difference write it out
        gp.Con_sa(FilMinus, FilMinus, depthGrid, "", "VALUE > 0")

        # Delete unwanted rasters
        gp.delete_management(Fill_DEMaoi)
        gp.delete_management(FilMinus)
        
        AddMsgAndPrint("\nSuccessfully Created a Depth Grid",1)

    # ------------------------------------------------------------------------------------------------ Compact FGDB
    try:
        gp.compact_management(watershedGDB_path)
        AddMsgAndPrint("\nSuccessfully Compacted FGDB: " + os.path.basename(watershedGDB_path),1)    
    except:
        pass      

    # ------------------------------------------------------------------------------------------------ Prepare to Add to Arcmap
    if createContours:
        gp.SetParameterAsText(5, Contours)
        
    gp.SetParameterAsText(6, projectAOI)
    gp.SetParameterAsText(7, DEM_aoi)
    gp.SetParameterAsText(8, Hillshade)
    gp.SetParameterAsText(9, depthGrid)
    

    AddMsgAndPrint("\nAdding Layers to ArcMap",1)
    AddMsgAndPrint("\n",1)

    # ------------------------------------------------------------------------------------------------ Clean up Time!
    gp.RefreshCatalog(watershedGDB_path)
    
    # Restore User environments
    gp.extent = tempExtent
    gp.mask = tempMask
    gp.SnapRaster = tempSnapRaster
    gp.CellSize = tempCellSize
    gp.OutputCoordinateSystem = tempCoordSys
    
    try:
        del gp
        del userWorkspace
        del inputDEM
        del AOI
        del interval
        del zUnits
        del projectName
        del textFilePath
        del watershedGDB_name
        del watershedGDB_path
        del watershedFD
        del aoiOut
        del contoursOut
        del demOut
        del hillshadeOut
        del depthOut
        del projectAOI
        del Contours
        del DEM_aoi
        del DEMsmooth
        del Hillshade
        del depthGrid
        del ContoursTemp
        del Fill_DEMaoi
        del FilMinus
        del desc
        del sr
        del units
        del Zfactor
        del fill
        del version
        del aoiTemp
        del ArcGIS10
        del tempExtent
        del tempMask
        del tempSnapRaster
        del tempCellSize
        del tempCoordSys
    except:
        pass

except SystemExit:
    pass

except KeyboardInterrupt:
    AddMsgAndPrint("Interruption requested....exiting")

except:
    print_exception()
