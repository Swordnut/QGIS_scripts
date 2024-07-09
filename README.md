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
