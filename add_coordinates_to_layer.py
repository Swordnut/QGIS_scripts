import os
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsField,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProcessingAlgorithm,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterVectorLayer,
    QgsProcessingException,
    QgsVectorFileWriter,
    QgsWkbTypes,
    QgsProcessingParameterFeatureSink,
    QgsProcessing
)
from qgis.PyQt.QtCore import QVariant

class AddCoordinatesToLayer(QgsProcessingAlgorithm):

    LAYER = 'LAYER'
    OUTPUT_LAYER = 'OUTPUT_LAYER'
    OVERWRITE_EXISTING_ATTRIBUTES = 'OVERWRITE_EXISTING_ATTRIBUTES'
    CREATE_NEW_LAYER = 'CREATE_NEW_LAYER'
    POLY_TRENCH_ENDS_ONLY = 'POLY_TRENCH_ENDS_ONLY'

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.LAYER,
                'Layer',
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.OVERWRITE_EXISTING_ATTRIBUTES,
                'Overwrite existing attributes',
                defaultValue=True
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CREATE_NEW_LAYER,
                'Create new output layer (will save new file to the same folder as the input and add to map)',
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.POLY_TRENCH_ENDS_ONLY,
                'Extract mid-points of the shortest sides of polygon trenches',
                defaultValue=False
            )
        )

    def define_fields(self, layer, overwrite_existing):
        geometry_type = layer.geometryType()
        fields_to_add = []

        if geometry_type == QgsWkbTypes.PointGeometry:
            fields_to_add = ["x", "y"]
        elif geometry_type == QgsWkbTypes.LineGeometry:
            fields_to_add = ["start_x", "start_y", "end_x", "end_y"]
        elif geometry_type == QgsWkbTypes.PolygonGeometry:
            fields_to_add = ["mid1_x", "mid1_y", "mid2_x", "mid2_y"]

        existing_fields = {field.name(): field for field in layer.fields()}
        fields_to_use = {}

        for field in fields_to_add:
            if field in existing_fields:
                if overwrite_existing or self.is_field_empty(layer, field):
                    fields_to_use[field] = field  # Use the existing field
                else:
                    continue  # Skip creating a new field if it's already populated
            else:
                fields_to_use[field] = field  # Use the original field name
        
        return fields_to_use

    def is_field_empty(self, layer, field_name):
        """Check if a field is entirely empty."""
        for feature in layer.getFeatures():
            if feature[field_name] is not None:
                return False
        return True

    def add_fields_to_layer(self, layer, fields_to_use):
        layer_provider = layer.dataProvider()

        for field, new_name in fields_to_use.items():
            if new_name not in layer.fields().names():
                layer_provider.addAttributes([QgsField(new_name, QVariant.Double)])
        layer.updateFields()

    def get_centroid(self, feature):
        geom = feature.geometry()
        return geom.centroid().asPoint()

    def get_start_point(self, geom):
        if QgsWkbTypes.isMultiType(geom.wkbType()):
            return geom.asMultiPolyline()[0][0]
        else:
            return geom.asPolyline()[0]

    def get_end_point(self, geom):
        if QgsWkbTypes.isMultiType(geom.wkbType()):
            return geom.asMultiPolyline()[0][-1]
        else:
            return geom.asPolyline()[-1]
    
    def get_shortest_side_midpoints(self, geom):
        """Identify the two shortest sides of a polygon and return their midpoints."""
        if geom.isMultipart():
            vertices = geom.asMultiPolygon()[0][0]
        else:
            vertices = geom.asPolygon()[0]

        # Get all edges and their lengths
        edges = []
        for i in range(len(vertices) - 1):
            p1 = vertices[i]
            p2 = vertices[i + 1]
            length = QgsPointXY(p1).distance(QgsPointXY(p2))
            midpoint = QgsPointXY((p1.x() + p2.x()) / 2, (p1.y() + p2.y()) / 2)
            edges.append((length, midpoint))

        # Sort edges by length and pick the two shortest
        edges.sort(key=lambda x: x[0])
        shortest_edges_midpoints = [edges[0][1], edges[1][1]]

        return shortest_edges_midpoints

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.LAYER, context)
        overwrite_existing = self.parameterAsBoolean(parameters, self.OVERWRITE_EXISTING_ATTRIBUTES, context)
        create_new_layer = self.parameterAsBoolean(parameters, self.CREATE_NEW_LAYER, context)
        poly_trench_ends_only = self.parameterAsBoolean(parameters, self.POLY_TRENCH_ENDS_ONLY, context)
        
        if not layer:
            raise QgsProcessingException('Layer not found or invalid.')

        geometry_type = layer.geometryType()
        wkb_type = layer.wkbType()

        multi_part_warning = ""
        if QgsWkbTypes.isMultiType(wkb_type):
            geometry_type = QgsWkbTypes.geometryType(wkb_type)
            multi_part_warning = f"Warning: Layer is a multi-part {QgsWkbTypes.displayString(wkb_type)}. Coordinates will be averaged for features with multiple parts."

        fields_to_use = self.define_fields(layer, overwrite_existing)
        
        self.add_fields_to_layer(layer, fields_to_use)

        layer_provider = layer.dataProvider()

        if create_new_layer:
            # Create a new layer
            new_layer = layer.clone()
            new_layer.startEditing()
            for feature in new_layer.getFeatures():
                geom = feature.geometry()

                if geometry_type == QgsWkbTypes.PointGeometry:
                    point = geom.asPoint()
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["x"]), point.x())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["y"]), point.y())

                elif geometry_type == QgsWkbTypes.LineGeometry:
                    start_point = self.get_start_point(geom)
                    end_point = self.get_end_point(geom)
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["start_x"]), start_point.x())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["start_y"]), start_point.y())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["end_x"]), end_point.x())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["end_y"]), end_point.y())

                elif geometry_type == QgsWkbTypes.PolygonGeometry and poly_trench_ends_only:
                    midpoints = self.get_shortest_side_midpoints(geom)
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["mid1_x"]), midpoints[0].x())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["mid1_y"]), midpoints[0].y())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["mid2_x"]), midpoints[1].x())
                    new_layer.changeAttributeValue(feature.id(), new_layer.fields().lookupField(fields_to_use["mid2_y"]), midpoints[1].y())

            new_layer.commitChanges()

            # Determine the output filename
            input_path = layer.dataProvider().dataSourceUri().split('|')[0]
            input_dir = os.path.dirname(input_path)
            input_name = os.path.splitext(os.path.basename(input_path))[0]

            output_path = os.path.join(input_dir, f"{input_name}_coords.shp")
            count = 1
            while os.path.exists(output_path):
                output_path = os.path.join(input_dir, f"{input_name}_coords_{count}.shp")
                count += 1

            # Save the new layer
            QgsVectorFileWriter.writeAsVectorFormat(new_layer, output_path, "utf-8", new_layer.crs(), "ESRI Shapefile")

            # Add the new layer to the project
            new_layer_loaded = QgsVectorLayer(output_path, os.path.basename(output_path), "ogr")
            if not new_layer_loaded.isValid():
                raise QgsProcessingException(f"Failed to load the new layer from {output_path}")
            
            QgsProject.instance().addMapLayer(new_layer_loaded)

            return {self.OUTPUT_LAYER: output_path}
        else:
            # Modify the existing layer
            for feature in layer.getFeatures():
                geom = feature.geometry()

                if geometry_type == QgsWkbTypes.PointGeometry:
                    point = geom.asPoint()
                    layer_provider.changeAttributeValues({
                        feature.id(): {layer.fields().lookupField(fields_to_use["x"]): point.x(),
                                       layer.fields().lookupField(fields_to_use["y"]): point.y()}
                    })

                elif geometry_type == QgsWkbTypes.LineGeometry:
                    start_point = self.get_start_point(geom)
                    end_point = self.get_end_point(geom)
                    layer_provider.changeAttributeValues({
                        feature.id(): {layer.fields().lookupField(fields_to_use["start_x"]): start_point.x(),
                                       layer.fields().lookupField(fields_to_use["start_y"]): start_point.y(),
                                       layer.fields().lookupField(fields_to_use["end_x"]): end_point.x(),
                                       layer.fields().lookupField(fields_to_use["end_y"]): end_point.y()}
                    })

                elif geometry_type == QgsWkbTypes.PolygonGeometry and poly_trench_ends_only:
                    midpoints = self.get_shortest_side_midpoints(geom)
                    layer_provider.changeAttributeValues({
                        feature.id(): {layer.fields().lookupField(fields_to_use["mid1_x"]): midpoints[0].x(),
                                       layer.fields().lookupField(fields_to_use["mid1_y"]): midpoints[0].y(),
                                       layer.fields().lookupField(fields_to_use["mid2_x"]): midpoints[1].x(),
                                       layer.fields().lookupField(fields_to_use["mid2_y"]): midpoints[1].y()}
                    })

            layer.commitChanges()

            # Clean up empty fields that were created
            self.cleanup_empty_fields(layer, fields_to_use)

            if multi_part_warning:
                feedback.pushInfo(multi_part_warning)

            return {}

    def cleanup_empty_fields(self, layer, fields_to_use):
        """Remove any fields created by the script that are entirely empty."""
        layer_provider = layer.dataProvider()
        fields_to_remove = []

        for field_name in fields_to_use.values():
            if self.is_field_empty(layer, field_name):
                fields_to_remove.append(layer.fields().indexOf(field_name))

        if fields_to_remove:
            layer_provider.deleteAttributes(fields_to_remove)
            layer.updateFields()


    def name(self):
        return 'addcoordinatestolayer'
    
    def displayName(self):
        return 'Add Coordinates to Layer'
    
    def group(self):
        return 'Johan scripts'
    
    def groupId(self):
        return 'johan_scripts'
    
    def createInstance(self):
        return AddCoordinatesToLayer()

# Ensure the algorithm is recognized by QGIS when adding it via the "Add Script" tool
def classFactory(iface):
    return AddCoordinatesToLayer()
