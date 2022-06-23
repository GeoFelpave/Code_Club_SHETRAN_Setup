# ------------------------
#  SHETRAN_Input_Files
# ------------------------

Collaborators: Luis FP Velasquez (LV) and Irina Rohrmueller (IR)

This repository includes scripts to automatically generate input files for the physically-based, spatially distributed hydrological mdoel SHETRAN.

  1. 01_setting_mask.py uses a catchment boundary in shapefile format to generate a catchment mask in text format.
  2. 02_setting_DEM.py uses a DEM in raster format to generate two separate DEMs, one containing the minimum elevation and one the average elevation for each grid cell, both in text format.
  3. 03_setting_land_cover.py uses a land cover map in raster format to generate a land cover file in text format.
  4. 04_setting_lake_map.py uses a lake map in shapefile format to generate a lake map in text format.
