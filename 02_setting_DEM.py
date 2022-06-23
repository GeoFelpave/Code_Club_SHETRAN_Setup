"""==============================================================================
 
 Title              :02_setting_DEM.py
 Description        :Generate a minimum and average DEM for SHETRAN
 Author             :LF Velasquez - I Rohrmueller 
 Date               :Feb 2022
 Version            :1.0
 Usage              :02_setting_DEM.py
 Notes              :
                    - Before starting the process the files containing the sys 
                      path and env path for qgis need to be created.
                    - DEM must be a single tif file, in the same projection as the catchment
                    mask.
python version      :3.8.7
 
=============================================================================="""
# =============================================================================
# Setting packages
# =============================================================================

from operator import index
import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path


# =============================================================================
# Global variables
# =============================================================================

# Setting path to work environment
p = Path(__file__)
dir_abs = p.parent.absolute()


# =============================================================================
# Adding default configurations for QGIS
# =============================================================================

# Setting up system paths
qspath = Path(dir_abs / 'QGIS_env/qgis_sys_paths.csv')
paths = pd.read_csv(qspath).paths.tolist()
sys.path += paths

# Setting up environment variables
qepath = Path(dir_abs / 'QGIS_env/qgis_env.json')
js = json.loads(open(qepath, "r").read())
for k, v in js.items():
    os.environ[k] = v

# For mac OS we might need to map the PROJ_LIB to handle the projections
# os.environ['PROJ_LIB'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj/'

# QGIS library imports
import PyQt5.QtCore
from PyQt5.QtCore import *
import qgis.PyQt.QtCore
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms

# Initialising processing module
QgsApplication.setPrefixPath(js["HOME"], True)
qgs = QgsApplication([], False)
qgs.initQgis() # Start processing module

# Import processing
import processing
from processing.core.Processing import Processing
Processing.initialize()

# At this point all QGIS libraries and spatial algorithms are available


# =============================================================================
# End of default configuration for QGIS
# Start Process
# =============================================================================

# Step 1. Setting catchment and elevation data ready for work
# Format: vlayer = QgsVectorLayer(data_source, layer_name, provider_name)
vlayer_grid = QgsVectorLayer(str(Path(dir_abs / 'Data/outputs/catchm_mask.shp')),
'Catch_layer', 'ogr')
rlayer_DEM = QgsRasterLayer(str(Path(dir_abs / 'Data/inputs/DEM.tif')), 'DEM_Layer')
DEM_Stats = str(Path(dir_abs / 'Data/outputs/DEM_Raster_Stats.shp'))

# Step 2. Running Raster Statistics for Polygons - QGIS
zonal_stats_params = { 'GRIDS' : [rlayer_DEM], 'POLYGONS' : vlayer_grid, 'METHOD' : 0,
'NAMING' : 0, 'COUNT' : False, 'MIN' : True, 'MAX' : False, 'RANGE' : False,
'SUM' : False, 'MEAN' : True, 'VAR' : False, 'STDDEV' : False, 'QUANTILE' : False,
'RESULT' : DEM_Stats }
processing.run("saga:rasterstatisticsforpolygons", zonal_stats_params)
vlayer_DEM_Stats = QgsVectorLayer(str(Path(dir_abs / 'Data/outputs/DEM_Raster_Stats.shp')),
'DEM_Stats')

# Step 3. Saving attribute table in pandas dataframe
# https://gis.stackexchange.com/questions/403081/attribute-table-into-pandas-dataframe-pyqgis
columns = [f.name() for f in vlayer_DEM_Stats.fields()]
columns_types = [f.typeName() for f in vlayer_DEM_Stats.fields()]
row_list = []
for f in vlayer_DEM_Stats.getFeatures():
    row_list.append(dict(zip(columns, f.attributes())))
df = pd.DataFrame(row_list, columns=columns)

# Step 4. Generating pivoted dataframe with minimum elevation per cell
# Pivoting dataframe to replicate SHETRAN format using X as column and Y as rows
df_pivot_min = df.pivot(index='Y', columns='X', values='G01_MIN')
df_pivot_min = df_pivot_min.sort_index(ascending=False)

# Step 5. Generating pivoted dataframe with mean elevation per cell
# Pivoting dataframe to replicate SHETRAN format using X as column and Y as row
df_pivot_mean = df.pivot(index='Y', columns='X', values='G01_MEAN')
df_pivot_mean = df_pivot_mean.sort_index(ascending=False)

# Step 6. Saving dataframes as text files
filename_min = Path(dir_abs / 'Data/outputs/final_dem_min_SHETRAN.txt')
filename_mean = Path(dir_abs / 'Data/outputs/final_dem_mean_SHETRAN.txt')
np.savetxt(filename_min, df_pivot_min.values, fmt='%d')
np.savetxt(filename_mean, df_pivot_mean.values, fmt='%d')

# Step 7. Creating header needed for SHETRAN
# Defining text file header
ncols_min = df_pivot_min.shape[1]
ncols_mean = df_pivot_mean.shape[1]
nrows_min = df_pivot_min.shape[0]
nrows_mean = df_pivot_mean.shape[0]
xllcorner_min = int(list(df_pivot_min.columns)[0])
xllcorner_mean = int(list(df_pivot_mean.columns)[0])
yllcorner_min = int(df_pivot_min.index[-1])
yllcorner_mean = int(df_pivot_mean.index[-1])
cellsize = 5000
no_data_val = -9999

# Step 8. Adding header to 'final_dem_min_SHETRAN.txt'
# Copying current information in text file
append_copy = open(filename_min, "r")
original_text = append_copy.read()
append_copy.close()
# Adding header information - this deletes any information in the text file
append_copy = open(filename_min, "w")
append_copy.write(
    "ncols         " + str(ncols_min) + "\n" + 
    "nrows         " + str(nrows_min) +  "\n" +
    "xllcorner     " + str(xllcorner_min) +  "\n" +
    "yllcorner     " + str(yllcorner_min) + "\n" +
    "cellsize      " + str(cellsize) + "\n" +
    "NODATA_value  " + str(no_data_val) + "\n")
# Pasting content that was in text file before adding header
append_copy.write(original_text)
# Saving text file
append_copy.close()

# Step 9. Adding header to 'final_dem_mean_SHETRAN.txt'
# Copying current information in text file
append_copy = open(filename_mean, "r")
original_text = append_copy.read()
append_copy.close()
# Adding header information - this deletes any information in the text file
append_copy = open(filename_mean, "w")
append_copy.write(
    "ncols         " + str(ncols_mean) + "\n" + 
    "nrows         " + str(nrows_mean) +  "\n" +
    "xllcorner     " + str(xllcorner_mean) +  "\n" +
    "yllcorner     " + str(yllcorner_mean) + "\n" +
    "cellsize      " + str(cellsize) + "\n" +
    "NODATA_value  " + str(no_data_val) + "\n")
# Pasting content that was in text file before adding header
append_copy.write(original_text)
# Saving text file
append_copy.close()


# =============================================================================
# End Process
# =============================================================================

print('-----')
print('Minimum and average DEM created!! Go and check.')
print('-----')


# =============================================================================
# Exit the QGIS processing module
# =============================================================================
qgs.exitQgis()