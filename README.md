# QGIS_scripts

Scripts for QGIS to add to the processing toolbox

## Compare_Layers_by_Attribute.py

Processing toolbox script.  

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

for Atlas layouts
Processing toolbox script.  

This helps create and edit atlas layouts. It fetches the extent of your selcted layout window and creates a scaled rectangle polygon layer

   - The new layer will be named "atlas.shp" and will be saved to the project home.
   - Attributes: the layout order (int), scale, layout origin and 2 empty character attributes for you to use as you want, including using expressions.
   -Layout order will be incremented if the script is used to generate more polygons in the same scale. 
      - If a new scale is used, the script will save the polygon in the same layer but will note the scale as an attribute. 
      - Subsequent uses of the script will keep incrementing the order number, as it just looks for the highest number so far
   - Produces styled polygons
      - transparent boxes, big helpful label for the order number
   - Drop-down menu for map window names is not auto-populated
      - QGIS does not support that in the proccessing toolbox. You will have to add your own or replace my list in the code. I have left a user input parameter to catch anything else.


## add_coordinates_to_layer.py

Processing toolbox script.  

This is for archaeological trenching, plus general usefulness

Adds x and y coordinates to a layer without creating a new virtual layer. 
Create a new shapefile or modify the existing one.
Add new attribute fileds or overwrite existing ones

It should add x and y coords:
•	Points and polys – centroid x and y
•	Lines - start and end x and y
•	Trenches that are polygons – x and y for the mid points of the 2 shortest sides. 

Options 
   - overwrite existing fields 
      - yes by default
      - untick this to get x_1, y_1 etc, if you want to know how they have changed or if you need to keep the old coordinates.
   - create a new layer 
      - no by default
         - there is already a thing that adds coords and spits out a new layer but I thought it best to have the option
   - Do the start and end of trench polygons.
      - Johan does need telling – otherwise you just get the centrepoints. 

T-shaped trenches are not something it will deal with. Johan is not a clever digital manservant, just a hard-working one. 


## concentric_donut_buffers.py

Processing toolbox script.  
Creates sequential user-defined buffers, then uses the DIFFERENCE tool to turn them into donuts. 
Each donut buffer is saved as a new layer in the project home /donut_buffers for ease of (and more options for) query and display. Als, the multi Ring Buffer plugin does a 1-layer output so it seemed redundant
The solid buffers are saved in a sub-folder /donut_buffers/gluten_free.



## MapOverviewGuidelines

Layout - Map window script
creates a dynamic polygon around an inset map and the overview generated by a QGIS map window, effectively replicating extent indicators from ArchGIS
This is WIP. it is only a function you woould have to add to yout project. but Ill make it into a toolbox script or plugin at some point. 


## Auto-updating Centre-Point Style

Point Layer style
Creates a single point that will position itself at the centre of a target layer and update when the target changes.
Add an empty point layer and set up a marker style. Add the script to the Geometry Generator. 

