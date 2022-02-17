"""==============================================================================
 
 Title              :setting_mask.py
 Description        :Create the catchment mask necessary for SHETRAN
 Author             :LF Velasquez
 Date               :Feb 2022
 Version            :1.0
 Usage              :setting_mask.py
 Notes              :
                    - Before starting the process the files containing the sys 
                      path and env path for qgis need to be created. Check: ADD LINK TO WEBSITE
python version  :3.8.7
 
=============================================================================="""
# =============================================================================
# Setting all packages
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

# Setting the path to the work environment
p = Path(__file__)
dir_abs = p.parent.absolute()

# =============================================================================
# Adding all default configuration for QGIS
# =============================================================================

# set up system paths
qspath = Path(dir_abs / 'qgis_sys_paths.csv')
paths = pd.read_csv(qspath).paths.tolist()
sys.path += paths

# set up environment variables
qepath = Path(dir_abs / 'qgis_env.json')
js = json.loads(open(qepath, "r").read())
for k, v in js.items():
    os.environ[k] = v


# In special cases, we might also need to map the PROJ_LIB to handle the projections
# for mac OS
os.environ['PROJ_LIB'] = '/Applications/QGIS-LTR.app/Contents/Resources/proj/'

# qgis library imports
import PyQt5.QtCore
from PyQt5.QtCore import *
import qgis.PyQt.QtCore
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms

# initializing processing module
QgsApplication.setPrefixPath(js["HOME"], True)
qgs = QgsApplication([], False)
qgs.initQgis() # Start processing module

# # Import processing
import processing
from processing.core.Processing import Processing
Processing.initialize()

# '''At this point all QGIS libraries and spatial algorithms are available'''

# =============================================================================
# End of default configuration for QGIS
# =============================================================================

# =============================================================================
# Start Process
# =============================================================================

# 1. Setting catchment shp ready for work

# The format is:
# vlayer = QgsVectorLayer(data_source, layer_name, provider_name)

vlayer = QgsVectorLayer(str(Path(dir_abs / 'Data/inputs/23001.shp')), 'Catch_layer', 'ogr')
if not vlayer.isValid():
    print('Layer failed to load!')
else:
    print('Layer has been loaded')
    # QgsProject.instance().addMapLayer(vlayer)


# 2. Create the fishnet - catchment mask

grid_file = Path(dir_abs/ 'Data/outputs/catchm_mask.shp')

# set parameters for algorithm
params   = { 'CRS' : QgsCoordinateReferenceSystem('EPSG:27700'), 'EXTENT' : vlayer,
            'HOVERLAY' : 0, 'HSPACING' : 5000, 'OUTPUT' : str(grid_file),
            'TYPE' : 2, 'VOVERLAY' : 0, 'VSPACING' : 5000 }
# create fishnet
create_grid = processing.run("qgis:creategrid", params)

# 3. Working with the mask
vlayer_grid = QgsVectorLayer(str(grid_file), 'catchment', 'ogr')

# checking the file can be edited
caps = vlayer_grid.dataProvider().capabilities()

# add coordinates and shetran id fields
if caps & QgsVectorDataProvider.AddAttributes:
    res = vlayer_grid.dataProvider().addAttributes([QgsField('X', QVariant.Double), 
                                                    QgsField('Y', QVariant.Double), 
                                                    QgsField('SHETRAN_ID', QVariant.Int)])
    vlayer_grid.updateFields()


# 3. Calculate cell centroids

expressionX = QgsExpression('x(centroid($geometry))')
expressionY = QgsExpression('y(centroid($geometry))')

# set the context to the layer
context = QgsExpressionContext()
context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(vlayer_grid))

with edit(vlayer_grid):
    for f in vlayer_grid.getFeatures():
        context.setFeature(f)
        f['X'] = expressionX.evaluate(context)
        f['Y'] = expressionY.evaluate(context)
        vlayer_grid.updateFeature(f)


# 4. Add shetran id based on the selection of catchment grid cells (values of one and zero)

# add 1 to select features 
select_params_one = { 'INPUT' : vlayer_grid, 'INTERSECT' : vlayer, 'METHOD' : 0, 'PREDICATE' : [0] } # set param for selection
processing.run("qgis:selectbylocation", select_params_one) # run selection
selection_one = vlayer_grid.selectedFeatures() # only use selected features
# update selected features
with edit(vlayer_grid):
    for feat in selection_one:
        feat['SHETRAN_ID'] = 1
        vlayer_grid.updateFeature(feat)
# Clear selection before other process
vlayer_grid.removeSelection()

# add 0 to unselected features
exp_zero = '"SHETRAN_ID" IS NULL'
select_params_zero = { 'INPUT' : vlayer_grid, 'EXPRESSION' : exp_zero, 'METHOD' : 0} # set param for selection
processing.run("qgis:selectbyexpression", select_params_zero) # run selection
selection_zero = vlayer_grid.selectedFeatures() # only use selected features
# update selected features
with edit(vlayer_grid):
    for feat in selection_zero:
        # zero needs to be passed as int as otherwise it won't work - needs further checks 
        # https://news.icourban.com/crypto-https-gis.stackexchange.com/questions/363927/pyqgis-inline-function-to-replace-null-values-with-0-in-all-fields-not-coalesc#
        feat['SHETRAN_ID'] = '0' 
        vlayer_grid.updateFeature(feat)
# Clear selection before other process
vlayer_grid.removeSelection()

# 5. Attribute table to pandas dataframe
# https://gis.stackexchange.com/questions/403081/attribute-table-into-pandas-dataframe-pyqgis

columns = [f.name() for f in vlayer_grid.fields()]
columns_types = [f.typeName() for f in vlayer_grid.fields()] # We exclude the geometry. Human readable
row_list = []
for f in vlayer_grid.getFeatures():
    row_list.append(dict(zip(columns, f.attributes())))

df = pd.DataFrame(row_list, columns=columns)

# Pivot dataframe using X as column and Y as rows 
df_pivot = df.pivot(index='Y', columns='X', values='SHETRAN_ID')
df_pivot = df_pivot.sort_index(ascending=False)
# print(df_pivot)

# 6. Save dataframe as a text file
np.savetxt(Path(dir_abs / 'final_mask_SHETRAN.txt'), df_pivot.values, fmt='%d')
# df_pivot.to_csv(Path(dir_abs / 'final_mask_SHETRAN.csv'), index=False, header=False)

# =============================================================================
# End Process
# =============================================================================
print('-----')
print('The process has ended!! Go and check')
print('-----')
# =============================================================================
# Exit the QGIS processing module
# =============================================================================
qgs.exitQgis()