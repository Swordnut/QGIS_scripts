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
    QgsUnitTypes,
    QgsProcessingParameterExpression,
    QgsExpression, 
    QgsExpressionContext, 
    QgsExpressionContextUtils
)
import qgis.analysis
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont

class CreateLayoutExtentPolygon(QgsProcessingAlgorithm):

    LAYOUT_NAME = 'LAYOUT_NAME'
    MAP_NAME = 'MAP_NAME'
    CUSTOM_MAP_NAME = 'CUSTOM_MAP_NAME'
    EXP_1 = 'EXP_1'
    EXP_2 = 'EXP_2'

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
        
        map_item_names = ['Map 1', 'add your list to the script']
        
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
            QgsProcessingParameterExpression(
                self.EXP_1,
                'User Attribute 1 (use single inverted commas for normal text)',
                '',
                optional=True
            )
        )
        
        self.addParameter(
            QgsProcessingParameterExpression(
                self.EXP_2,
                'User Attribute 2 (use single inverted commas for normal text)',
                '',
                optional=True
            )
        )
        



    def processAlgorithm(self, parameters, context, feedback):

        # Minimal feedback output
        feedback.setProgressText('Processing layout extent polygon...')
        
        try:
            layout_index = self.parameterAsEnum(parameters, self.LAYOUT_NAME, context)
            map_item_index = self.parameterAsEnum(parameters, self.MAP_NAME, context)
            custom_map_item_name = self.parameterAsString(parameters, self.CUSTOM_MAP_NAME, context)
            exp_1 = self.parameterAsString(parameters, self.EXP_1, context)
            exp_2 = self.parameterAsString(parameters, self.EXP_2, context)
            
            layout_manager = QgsProject.instance().layoutManager()
            layout_name = layout_manager.layouts()[layout_index].name()
            layout = layout_manager.layoutByName(layout_name)

            # Map Name drop-down options for user convinience the processing toolbox API does not have the option to auto-populate this
            map_item_names = ['Map 1', 'ADD YOUR STANDARD MAP WINDOW ITEM ID'S TO THE SCRIPT']
            map_item_name = custom_map_item_name if custom_map_item_name else map_item_names[map_item_index]
            
            map_item = layout.itemById(map_item_name)
            

            
            if not map_item:
                raise QgsProcessingException(f'Map item "{map_item_name}" not found in layout "{layout_name}"')
            
            extent = map_item.extent()
            scale = round(map_item.scale())
            
            project_home = QgsProject.instance().homePath()
            output_path = os.path.join(project_home, 'atlas.shp')
            
            if not os.path.exists(output_path):
                project_crs = QgsProject.instance().crs()
                polygon_layer = QgsVectorLayer(f'Polygon?crs={project_crs.authid()}', 'atlas', 'memory')
                provider = polygon_layer.dataProvider()
                provider.addAttributes([
                    QgsField('order', QVariant.Int),
                    QgsField('scale', QVariant.String),
                    QgsField('layout',QVariant.String),
                    QgsField('exp_1', QVariant.String),
                    QgsField('exp_2', QVariant.String)
                ])
                polygon_layer.updateFields()
                order = 1
            else:
                polygon_layer = QgsVectorLayer(output_path, 'atlas', 'ogr')
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
    
            # Evaluate the expressions in the context of the current feature
            expression_context = QgsExpressionContext()
            expression_context.appendScopes(QgsExpressionContextUtils.globalProjectLayerScopes(polygon_layer))
            expression_context.setFeature(feature)

            exp_1_value = QgsExpression(exp_1).evaluate(expression_context)
            exp_2_value = QgsExpression(exp_2).evaluate(expression_context)
            
            feature.setAttributes([order, scale, layout_name, exp_1_value, exp_2_value])
            
            polygon_layer.dataProvider().addFeature(feature)
            
            # Save the layer to the specified output path
            QgsVectorFileWriter.writeAsVectorFormat(polygon_layer, output_path, "UTF-8", polygon_layer.crs(), "ESRI Shapefile", False)
            
            # Add or update the saved layer in the project
            existing_layers = QgsProject.instance().mapLayersByName('atlas')
            if existing_layers:
                existing_layer = existing_layers[0]
                existing_layer.reload()
                polygon_layer = existing_layer  # Use the reloaded layer
            else:
                saved_layer = QgsVectorLayer(output_path, 'atlas', 'ogr')
                if saved_layer.isValid():
                    QgsProject.instance().addMapLayer(saved_layer)
                    polygon_layer = saved_layer  # Use the added layer
                else:
                    raise QgsProcessingException(f'Error adding layer to project: {output_path}')
            
            # Apply symbol and labeling styles
            self.applyStyles(polygon_layer)
            
        
            # Limit feedback messages
            if feedback.isCanceled():
                return {}

            feedback.setProgress(100)
        except Exception as e:
            feedback.reportError(f"Error: {str(e)}")
            raise QgsProcessingException(str(e))
        
        return {}

    def applyStyles(self, polygon_layer):
        # Define properties for the symbol layer
        properties = {
            "border_width": "0.26",
            "border_width_unit": "MM",
            "color": "183,72,75,100",  # Fill color from QML
            "joinstyle": "bevel",
            "offset": "0,0",
            "offset_unit": "MM",
            "outline_color": "0,0,0,255",  # Black outline
            "outline_style": "solid",
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
        pal_layer.placement = Qgis.LabelPlacement.OverPoint

        # Text format for labeling
        text_format = QgsTextFormat()
        font = QFont("Arial")
        font.setItalic(True)
        font.setBold(True)
        text_format.setFont(font)
        text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
        text_format.setSize(30)
        text_format.setColor(QColor(0, 0, 0, 255))  # Text color from QML

        # Apply text format to pal_layer settings
        pal_layer.setFormat(text_format)

        # Create and apply labeling to the polygon layer
        labeling = QgsVectorLayerSimpleLabeling(pal_layer)
        polygon_layer.setLabelsEnabled(True)
        polygon_layer.setLabeling(labeling)

        # Refresh the layer to apply changes
        polygon_layer.triggerRepaint()

    def name(self):
        return 'createlayoutextentpolygon'
    
    def displayName(self):
        return 'Create Layout Extent Polygon'
    
    def group(self):
        return 'Johan Scripts'
    
    def groupId(self):
        return 'johan_scripts'
    
    def createInstance(self):
        return CreateLayoutExtentPolygon()

# Ensure the algorithm is recognized by QGIS when adding it via the "Add Script" tool
def classFactory(iface):
    return CreateLayoutExtentPolygon()
