from qgis.core import (QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterFeatureSink, QgsProcessingParameterField,
                       QgsProcessingParameterEnum, QgsFeatureSink, QgsProcessingException,
                       QgsWkbTypes, QgsFeature)

class CompareLayersAlgorithm(QgsProcessingAlgorithm):
    OLD_LAYER = 'OLD_LAYER'
    NEW_LAYER = 'NEW_LAYER'
    OLD_LAYER_ATTRIBUTE = 'OLD_LAYER_ATTRIBUTE'
    NEW_LAYER_ATTRIBUTE = 'NEW_LAYER_ATTRIBUTE'
    SELECTION_OPTION = 'SELECTION_OPTION'
    OUTPUT_LAYER = 'OUTPUT_LAYER'
    
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.OLD_LAYER,
                'Old Layer',
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.NEW_LAYER,
                'New Layer',
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.OLD_LAYER_ATTRIBUTE,
                'Attribute from Old Layer',
                parentLayerParameterName=self.OLD_LAYER,
                type=QgsProcessingParameterField.Any
            )
        )
        
        self.addParameter(
            QgsProcessingParameterField(
                self.NEW_LAYER_ATTRIBUTE,
                'Attribute from New Layer',
                parentLayerParameterName=self.NEW_LAYER,
                type=QgsProcessingParameterField.Any
            )
        )
        
        self.addParameter(
            QgsProcessingParameterEnum(
                self.SELECTION_OPTION,
                'Selection Option',
                options=[
                    'Select features common to both layers',
                    'Select features in the old layer that are not in the new layer',
                    'Select features in the new layer that are not in the old layer'
                ],
                defaultValue=2  # Default to selecting features in the new layer that are not in the old layer
            )
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LAYER,
                'Output Layer',
                QgsProcessing.TypeVectorAnyGeometry
            )
        )
    
    def processAlgorithm(self, parameters, context, feedback):
        old_layer = self.parameterAsVectorLayer(parameters, self.OLD_LAYER, context)
        new_layer = self.parameterAsVectorLayer(parameters, self.NEW_LAYER, context)
        old_layer_attribute = self.parameterAsString(parameters, self.OLD_LAYER_ATTRIBUTE, context)
        new_layer_attribute = self.parameterAsString(parameters, self.NEW_LAYER_ATTRIBUTE, context)
        selection_option = self.parameterAsEnum(parameters, self.SELECTION_OPTION, context)
        
        if not new_layer or not old_layer:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.NEW_LAYER if not new_layer else self.OLD_LAYER))
        
        # Create sets of attribute values from both layers
        old_attr_set = set(feature[old_layer_attribute] for feature in old_layer.getFeatures())
        new_attr_set = set(feature[new_layer_attribute] for feature in new_layer.getFeatures())
        
        # Determine the output layer geometry type and fields
        if selection_option in [0, 2]:  # Use new layer geometry for common or new-only features
            output_wkb_type = new_layer.wkbType()
            output_crs = new_layer.crs()
            fields = new_layer.fields()
        else:  # Use old layer geometry for old-only features
            output_wkb_type = old_layer.wkbType()
            output_crs = old_layer.crs()
            fields = old_layer.fields()
        
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT_LAYER, context, fields, output_wkb_type, output_crs)
        
        # Select features based on the chosen option
        count = 0
        if selection_option == 0:  # Select features common to both layers
            for feature in new_layer.getFeatures():
                if feature[new_layer_attribute] in old_attr_set:
                    sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    count += 1
        elif selection_option == 1:  # Select features in the old layer that are not in the new layer
            for feature in old_layer.getFeatures():
                if feature[old_layer_attribute] not in new_attr_set:
                    sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    count += 1
        elif selection_option == 2:  # Select features in the new layer that are not in the old layer
            for feature in new_layer.getFeatures():
                if feature[new_layer_attribute] not in old_attr_set:
                    sink.addFeature(feature, QgsFeatureSink.FastInsert)
                    count += 1
        
        # Log the number of selected features
        feedback.pushInfo(f"Number of features selected: {count}")
        
        # Return the output layer as a result
        return {self.OUTPUT_LAYER: dest_id}
    
    def name(self):
        return 'compare_layers'
    
    def displayName(self):
        return 'Compare Layers by Attribute'
    
    def group(self):
        return 'Johan Scripts'
    
    def groupId(self):
        return 'johan_scripts'
    
    def createInstance(self):
        return CompareLayersAlgorithm()

# Ensure the algorithm is recognized by QGIS when adding it via the "Add Script" tool
def classFactory(iface):
    return CompareLayersAlgorithm()
