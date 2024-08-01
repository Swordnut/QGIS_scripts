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
    QgsProcessingException,
    QgsVectorFileWriter,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsPalLayerSettings,
    QgsWkbTypes,
    QgsSimpleFillSymbolLayer,
    QgsFillSymbol,
    QgsSingleSymbolRenderer,
    LabelPlacement
)
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

class CreateLayoutExtentPolygon(QgsProcessingAlgorithm):

    LAYOUT_NAME = 'LAYOUT_NAME'
    MAP_NAME = 'MAP_NAME'
    CUSTOM_MAP_NAME = 'CUSTOM_MAP_NAME'
    SUBTITLE = 'SUBTITLE'
    NOTE = 'NOTE'

    def initAlgorithm(self, config=None):
        layout_manager = QgsProject.instance().layoutManager()
        layout_names = [layout.name() for layout in layout_manager.layouts()]
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.LAYOUT_NAME,
                'Layout Name',
                options=layout_names
            )
        )
        
        map_item_names = ['Map_1', 'In_Report_Map', 'Small Scale Map', 'Mid Scale Map', 'UK Map']
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.MAP_NAME,
                'Map Item Name',
                options=map_item_names
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.CUSTOM_MAP_NAME,
                'Custom Map Item Name (if different)',
                '',
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.SUBTITLE,
                'Subtitle',
                'Your subtitle here'
            )
        )
        
        self.addParameter(
            QgsProcessingParameterString(
                self.NOTE,
                'Note',
                'Your note here'
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        layout_index = self.parameterAsEnum(parameters, self.LAYOUT_NAME, context)
        map_item_index = self.parameterAsEnum(parameters, self.MAP_NAME, context)
        custom_map_item_name = self.parameterAsString(parameters, self.CUSTOM_MAP_NAME, context)
        subtitle = self.parameterAsString(parameters, self.SUBTITLE, context)
        note = self.parameterAsString(parameters, self.NOTE, context)
        
        layout_manager = QgsProject.instance().layoutManager()
        layout_name = layout_manager.layouts()[layout_index].name()
        layout = layout_manager.layoutByName(layout_name)
        
        map_item_names = ['Map_1', 'In_Report_Map', 'Small Scale Map', 'Mid Scale Map', 'UK Map']
        map_item_name = custom_map_item_name if custom_map_item_name else map_item_names[map_item_index]
        
        map_item = layout.itemById(map_item_name)
        
        if not map_item:
            raise QgsProcessingException(f'Map item "{map_item_name}" not found in layout "{layout_name}"')
        
        extent = map_item.extent()
        scale = round(map_item.scale())
        
        project_home = QgsProject.instance().homePath()
        output_path = os.path.join(project_home, f'atlas_{scale}.shp')
        
        if not os.path.exists(output_path):
            project_crs = QgsProject.instance().crs()
            polygon_layer = QgsVectorLayer(f'Polygon?crs={project_crs.authid()}', f'atlas_{scale}', 'memory')
            provider = polygon_layer.dataProvider()
            provider.addAttributes([
                QgsField('order', QVariant.Int),
                QgsField('scale', QVariant.String),
                QgsField('subtitle', QVariant.String),
                QgsField('note', QVariant.String)
            ])
            polygon_layer.updateFields()
            order = 1
        else:
            polygon_layer = QgsVectorLayer(output_path, f'atlas_{scale}', 'ogr')
            if not polygon_layer.isValid():
                raise QgsProcessingException(f'Failed to load existing layer: {output_path}')
            features = list(polygon_layer.getFeatures())
            order = max([f['order'] for f in features], default=0) + 1
        
        points = [
            QgsPointXY(extent.xMinimum(), extent.yMinimum()),
            QgsPointXY(extent.xMaximum(), extent.yMinimum()),
            QgsPointXY(extent.xMaximum(), extent.yMaximum()),
            QgsPointXY(extent.xMinimum(), extent.yMaximum()),
            QgsPointXY(extent.xMinimum(), extent.yMinimum())
        ]
        
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolygonXY([points]))
        feature.setAttributes([order, f'{scale} - {layout_name}', subtitle, note])
        polygon_layer.dataProvider().addFeature(feature)
        
        # Define properties for the symbol layer
        properties = {
            "border_width_map_unit_scale": "3x:0,0,0,0,0,0",
            "color": "255,0,0,50",  # Red with 50% opacity
            "joinstyle": "bevel",
            "offset": "0,0",
            "offset_map_unit_scale": "3x:0,0,0,0,0,0",
            "offset_unit": "MM",
            "outline_color": "0,0,0,255",  # Black outline
            "outline_style": "solid",
            "outline_width": "0.26",
            "outline_width_unit": "MM",
            "style": "solid",
        }
        
        # Create a QgsSimpleFillSymbolLayer with the defined properties
        symbol_layer = QgsSimpleFillSymbolLayer.create(properties)
        if not symbol_layer:
            raise QgsProcessingException('Failed to create symbol layer with the provided properties.')

        # Create the symbol and apply the symbol layer
        symbol = QgsFillSymbol()
        symbol.deleteSymbolLayer(0)
        symbol.appendSymbolLayer(symbol_layer.clone())
        
        # Set the renderer for the polygon layer
        polygon_layer.setRenderer(QgsSingleSymbolRenderer(symbol))
        
        # Set up labeling
        pal_layer = QgsPalLayerSettings()
        pal_layer.fieldName = 'order'
        
        # Use a suitable placement attribute
        pal_layer.placement = LabelPlacement.AroundPoint  # Change to the appropriate LabelPlacement value

        text_format = QgsTextFormat()
        font = QFont("Arial", 30)
        font.setItalic(True)
        text_format.setFont(font)
        
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(False)  # No buffer
        
        text_format.setBuffer(buffer_settings)
        pal_layer.setFormat(text_format)
        
        labeling = QgsVectorLayerSimpleLabeling(pal_layer)
        polygon_layer.setLabelsEnabled(True)
        polygon_layer.setLabeling(labeling)
        
        polygon_layer.triggerRepaint()
        
        # Save the layer to the specified output path
        QgsVectorFileWriter.writeAsVectorFormat(polygon_layer, output_path, "UTF-8", polygon_layer.crs(), "ESRI Shapefile", False)
        
        # Add or update the saved layer in the project
        existing_layers = QgsProject.instance().mapLayersByName(f'atlas_{scale}')
        if existing_layers:
            existing_layer = existing_layers[0]
            existing_layer.reload()
        else:
            saved_layer = QgsVectorLayer(output_path, f'atlas_{scale}', 'ogr')
            if saved_layer.isValid():
                QgsProject.instance().addMapLayer(saved_layer)
            else:
                raise QgsProcessingException(f'Error adding layer to project: {output_path}')
        
        return {}

    def name(self):
        return 'createlayoutextentpolygon'
    
    def displayName(self):
        return 'Create Layout Extent Polygon'
    
    def group(self):
        return 'johan_scripts'
    
    def groupId(self):
        return 'johan_scripts'
    
    def createInstance(self):
        return CreateLayoutExtentPolygon()
