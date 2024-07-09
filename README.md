# QGIS_scripts
Scripts for QGIS to add to the processing toolbox

Compare_Layers_by_Attribute.py 
  compare attribute values in 2 different layers and select features based on the user options below.
  log message displays a count of the selected features
  layers of any geometry can be compared, including miss-matched geometries (points can be compared with polygons, etc)
  user input of 2 layers "old" and "new" 
  user input for the attribute field from each layer to be used for comparison
  use option input: 
    select features in the "new" layer" and not in the "old" layer - outputs in "new" layer's geometry 
    select features in the "old" layer and not in the "new" layer  - outputs in "old" layer's geometry
    select features in both "old" and "new" layers  - outputs in "new" layer's geometry
  user option for output:
    temporary or permanent layer
    add to the current project
  
