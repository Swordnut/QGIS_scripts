# QGIS_scripts

Scripts for QGIS to add to the processing toolbox

## Compare_Layers_by_Attribute.py

This script compares attribute values in two different layers and selects features based on the user options below. The log message displays a count of the selected features. Layers of any geometry can be compared, including mismatched geometries (e.g., points can be compared with polygons).

### User Inputs

1. **Layers**:
   - Two layers: "old" and "new"

2. **Attribute Field**:
   - Attribute field from each layer to be used for comparison

### Options for Feature Selection

1. **Select features in the "new" layer and not in the "old" layer**
   - Outputs in "new" layer's geometry

2. **Select features in the "old" layer and not in the "new" layer**
   - Outputs in "old" layer's geometry

3. **Select features in both "old" and "new" layers**
   - Outputs in "new" layer's geometry

### Output Options

1. **Layer Type**:
   - Temporary or permanent layer

2. **Project Addition**:
   - Option to add the layer to the current project


## layout_extent_polygon.py

This fetches the extent of your selcted layout window and creates a rectangle polygon

**The new layer will be named "atlas_{mapscale}" and will be saved un the project home
**Attributes: the layout order (int), origin "{mapscale} {layoutname}" and 2 empty character attributes for you to use as you want
**Layout order will be incremented if the script is used to generate more polygons in the same scale. 
**If a new scale is used, the script will save the polygon as a new layer. 
   - You can edit the layer as normal though, including inserting different sized polygons. Subsequent uses of the script will keep incrementing the order number, as it just looks for the highest number so far
** Produces styled polygons
   - transparent boxes, big helpful label for the order number
** Drop-down menu for map window names is not auto-populated
   - QGIS does not support that in the proccessing toolbox. You will have to add your own or replace my list in the code. I have left a user input parameter to catch anything else.


## layout_extent_polygon_qgis_36_and_up.py

Same as the last script except I had to change it to account for the changes to labeling from QGIS 36.0 onward

