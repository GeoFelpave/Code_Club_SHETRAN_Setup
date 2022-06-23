"""==============================================================================
 
 Title              :04_setting_lake_map.py
 Description        :Generate a lake map for SHETRAN
 Author             :LF Velasquez - I Rohrmueller 
 Date               :Feb 2022
 Version            :1.0
 Usage              :04_setting_lake_map.py
 Notes              :
                    - Before starting the process the files containing the sys 
                      path and env path for qgis need to be created.
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

# Step 1. Setting lake shp ready for work
# Format: vlayer = QgsVectorLayer(data_source, layer_name, provider_name)
vlayer = QgsVectorLayer(str(Path(dir_abs / 'Data/inputs/lakes.shp')),
'Lake_layer', 'ogr')
if not vlayer.isValid():
    print('Lake shapefile failed to load.')
else:
    print('Lake shapefile loaded...')

# Step 2. Loading catchment mask
grid_file = Path(dir_abs/ 'Data/outputs/catchm_mask.shp')
vlayer_grid = QgsVectorLayer(str(grid_file), 'catchment', 'ogr')

# Step 3. Preparing the mask
# Checking the file can be edited
caps = vlayer_grid.dataProvider().capabilities()
# Adding lake id field
if caps & QgsVectorDataProvider.AddAttributes:
    res = vlayer_grid.dataProvider().addAttributes([QgsField('LAKE_ID', QVariant.Int)])
    vlayer_grid.updateFields()

# Step 5. Adding lake id based on the selection of catchment grid cells
# Adding 1 to cells that represent a lake
select_params_lake = { 'INPUT' : vlayer_grid, 'INTERSECT' : vlayer, 'METHOD' : 0,'PREDICATE' : [0] }
processing.run("qgis:selectbylocation", select_params_lake)
selection_lake = vlayer_grid.selectedFeatures()
with edit(vlayer_grid):
    for feat in selection_lake:
        feat['LAKE_ID'] = '1'
        vlayer_grid.updateFeature(feat)
vlayer_grid.removeSelection()
# Adding -9999 to cells outside of lakes
exp_zero = '"LAKE_ID" IS NULL'
select_params_outs = { 'INPUT' : vlayer_grid, 'EXPRESSION' : exp_zero, 'METHOD' : 0}
processing.run("qgis:selectbyexpression", select_params_outs)
selection_outs = vlayer_grid.selectedFeatures()
with edit(vlayer_grid):
    for feat in selection_outs:
        feat['LAKE_ID'] = '-9999' 
        vlayer_grid.updateFeature(feat)
vlayer_grid.removeSelection()

# Step 6. Saving attribute table in pandas dataframe
# https://gis.stackexchange.com/questions/403081/attribute-table-into-pandas-dataframe-pyqgis
columns = [f.name() for f in vlayer_grid.fields()]
columns_types = [f.typeName() for f in vlayer_grid.fields()]
row_list = []
for f in vlayer_grid.getFeatures():
    row_list.append(dict(zip(columns, f.attributes())))
df = pd.DataFrame(row_list, columns=columns)

# Step 7. Pivoting dataframe to replicate SHETRAN format
# Pivoting dataframe using X as column and Y as row
df_pivot = df.pivot(index='Y', columns='X', values='LAKE_ID')
df_pivot = df_pivot.sort_index(ascending=False)

# Step 8. Saving dataframe as text file
filename = Path(dir_abs / 'Data/outputs/final_lake_map_SHETRAN.txt')
np.savetxt(filename, df_pivot.values, fmt='%d')

# Step 9. Creating header needed for SHETRAN
ncols = df_pivot.shape[1]
nrows = df_pivot.shape[0]
xllcorner = int(list(df_pivot.columns)[0])
yllcorner = int(df_pivot.index[-1])
cellsize = 5000
no_data_val = -9999

# Step 10. Adding header to text file
# Copying current information in text file
append_copy = open(filename, "r")
original_text = append_copy.read()
append_copy.close()
# Adding header information - this deletes any information in the text file
append_copy = open(filename, "w")
append_copy.write(
    "ncols         " + str(ncols) + "\n" + 
    "nrows         " + str(nrows) +  "\n" +
    "xllcorner     " + str(xllcorner) +  "\n" +
    "yllcorner     " + str(yllcorner) + "\n" +
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
print('Lake map created!! Go and check.')
print('-----')


# =============================================================================
# Exit the QGIS processing module
# =============================================================================
qgs.exitQgis()