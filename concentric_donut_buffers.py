import os
from qgis.core import (
    QgsProcessing, QgsVectorLayer, QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer, QgsProcessingParameterFolderDestination, 
    QgsProcessingParameterString, QgsProcessingParameterBoolean, 
    QgsProject, QgsSymbol, QgsSimpleLineSymbolLayer, 
    QgsSimpleFillSymbolLayer, QgsFillSymbol, 
    QgsSingleSymbolRenderer, QgsPalLayerSettings, 
    QgsTextFormat, QgsVectorLayerSimpleLabeling, 
    QgsUnitTypes, QgsProcessingException
)
from qgis.PyQt.QtGui import QColor, QFont  # Correct import for QColor and QFont
from qgis.PyQt.QtCore import QCoreApplication  # Correct import for QCoreApplication
from qgis.core import Qgis
from qgis import processing  # Correct import for processing module

class ConcentricDonutBuffers(QgsProcessingAlgorithm):
    INPUT_LAYER = 'INPUT_LAYER'
    OUTPUT_FOLDER = 'OUTPUT_FOLDER'
    CUSTOM_DISTANCES = 'CUSTOM_DISTANCES'
    ADD_TO_PROJECT = 'ADD_TO_PROJECT'

    def initAlgorithm(self, config=None):
        # Define input polygon layer as a dropdown of available polygon layers
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT_LAYER,
                self.tr('Select Polygon/Multipolygon Layer'),
                [QgsProcessing.TypeVectorPolygon]  # Restrict to polygon layers
            )
        )

        # Define output folder for ring buffers
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_FOLDER,
                self.tr('Output Folder'),
                defaultValue=os.path.join(QgsProject.instance().homePath(), 'donut_buffers')
            )
        )

        # Define a pre-populated comma-separated list for buffer distances
        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_DISTANCES,
            self.tr('Add more distances separated by commas (e.g., 30, 40.5, 50.25)'),
            defaultValue='2, 5, 10, 20'  # Prepopulated with 2, 5, 10, 20 km
        ))

        # Add option to load generated layers into the current project
        self.addParameter(QgsProcessingParameterBoolean(
            self.ADD_TO_PROJECT,
            self.tr('Add generated layers to the current project'),
            defaultValue=True
        ))

    def processAlgorithm(self, parameters, context, feedback):
        # Get the input layer and output folder
        input_layer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        feedback.pushInfo(f"Input layer: {input_layer.name()}")

        # Check if the input layer is valid
        if not input_layer.isValid():
            feedback.reportError(f"Selected layer {input_layer.name()} is not valid. Please check the layer.")
            return {}

        # Handle the output folder path, ensure it's correct
        output_folder = self.parameterAsString(parameters, self.OUTPUT_FOLDER, context)
        output_folder = os.path.normpath(output_folder)
        feedback.pushInfo(f"Output folder path: {output_folder}")

        # Create a subfolder for raw buffers
        raw_folder = os.path.join(output_folder, 'gluten_free')
        if not os.path.exists(raw_folder):
            os.makedirs(raw_folder)

        # Collect buffer distances from the comma-separated string
        custom_distances = self.parameterAsString(parameters, self.CUSTOM_DISTANCES, context)
        try:
            # Convert distances from km to meters, ensure correct formatting, and remove unnecessary decimals
            buffer_distances = [float(d.strip()) * 1000 for d in custom_distances.split(',') if d.strip()]
            buffer_names = [f'{int(d) if d.is_integer() else d}_km_study_area'.replace(".", "_") for d in [float(d.strip()) for d in custom_distances.split(',') if d.strip()]]
        except ValueError:
            feedback.reportError("Invalid format for distances. Please ensure they are valid numbers separated by commas.")
            return {}

        # Check if the distances are sequential and at least 10 meters apart
        if not self.validateDistances(buffer_distances, feedback):
            return {}

        # Check if layers should be added to the current project
        add_to_project = self.parameterAsBoolean(parameters, self.ADD_TO_PROJECT, context)

        # Step 1: Create all buffers in the order of smallest to largest
        buffers = []
        for i, dist in enumerate(buffer_distances):
            buffer_name = buffer_names[i]

            # Create buffer for the current distance
            feedback.pushInfo(f"Creating buffer for {dist / 1000} km...")
            current_buffer = processing.run("native:buffer", {
                'INPUT': input_layer,
                'DISTANCE': dist,
                'SEGMENTS': 50,  # Number of segments for smoother buffers
                'DISSOLVE': True,
                'OUTPUT': 'memory:'
            }, context=context, feedback=feedback)['OUTPUT']

            buffers.append(current_buffer)

            # Save intermediate buffer for debugging into the gluten_free folder
            raw_file = os.path.join(raw_folder, f'{buffer_name}_solid.gpkg')
            processing.run("native:savefeatures", {
                'INPUT': current_buffer,
                'OUTPUT': raw_file
            }, context=context, feedback=feedback)
            feedback.pushInfo(f"Saved raw buffer {buffer_name} at {raw_file}")

        # Step 2: Sequentially clip buffers using an indexed order
        for i in range(1, len(buffers)):
            outer_buffer = buffers[i]
            inner_buffer = buffers[i - 1]

            feedback.pushInfo(f"Clipping buffer {i} ({buffer_names[i]}) with buffer {i - 1} ({buffer_names[i - 1]})...")

            # Clip outer buffer with inner buffer to create a ring
            ring_buffer = processing.run("native:difference", {
                'INPUT': outer_buffer,
                'OVERLAY': inner_buffer,
                'OUTPUT': 'memory:'
            }, context=context, feedback=feedback)['OUTPUT']

            # Save the ring buffer
            buffer_name = buffer_names[i]
            output_file = os.path.join(output_folder, f'{buffer_name}.gpkg')

            processing.run("native:savefeatures", {
                'INPUT': ring_buffer,
                'OUTPUT': output_file
            }, context=context, feedback=feedback)

            # Apply the manual styling to the layer
            self.applyStyles(output_file, context, feedback)

            # Add layer to the project if the option is enabled
            if add_to_project:
                self.add_layer_to_project(output_file, buffer_name, feedback)

            feedback.pushInfo(f"Saved donut buffer {buffer_name} at {output_file}")

        # Save the smallest buffer directly (the first one)
        first_buffer_name = buffer_names[0]
        first_output_file = os.path.join(output_folder, f'{first_buffer_name}.gpkg')
        processing.run("native:savefeatures", {
            'INPUT': buffers[0],
            'OUTPUT': first_output_file
        }, context=context, feedback=feedback)

        # Apply the manual styling to the layer
        self.applyStyles(first_output_file, context, feedback)

        # Add layer to the project if the option is enabled
        if add_to_project:
            self.add_layer_to_project(first_output_file, first_buffer_name, feedback)

        feedback.pushInfo(f"Saved smallest buffer {first_buffer_name} at {first_output_file}")

        return {}
            """ 
            This styling code is not working with V26 and up - WIP
            to do - 
                get it working 
                investigate - is native styling panel possible to bruing into the processing toolbox?
                give user option to point at QML style file?
            """
    def applyStyles(self, layer_path, context, feedback):
        """ Manually apply styles to the layer """
        layer = QgsVectorLayer(layer_path, "Styled Layer", "ogr")
        if layer.isValid():
            # Define properties for the symbol layer
            properties = {
                "border_width": "0.26",
                "border_width_unit": "MM",
                "color": "183,72,75,100",  # Fill color
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
            layer.setRenderer(QgsSingleSymbolRenderer(symbol))

            # Set up labeling (optional, but included for demonstration)
            pal_layer = QgsPalLayerSettings()
            pal_layer.fieldName = 'order'  # Replace with a suitable field

            # Placement for labeling
            pal_layer.placement = Qgis.LabelPlacement.OverPoint

            # Text format for labeling
            text_format = QgsTextFormat()
            font = QFont("Arial")
            font.setItalic(True)
            font.setBold(True)
            text_format.setFont(font)
            text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
            text_format.setSize(30)
            text_format.setColor(QColor(0, 0, 0, 255))  # Text color

            # Apply text format to pal_layer settings
            pal_layer.setFormat(text_format)

            # Create and apply labeling to the polygon layer
            labeling = QgsVectorLayerSimpleLabeling(pal_layer)
            layer.setLabelsEnabled(True)
            layer.setLabeling(labeling)

            # Refresh the layer to apply changes
            layer.triggerRepaint()
            feedback.pushInfo(f"Manually applied style and labeling to {layer.name()}")
        else:
            feedback.reportError(f"Layer {layer_path} is not valid for styling.")

    def add_layer_to_project(self, layer_path, layer_name, feedback):
        """ Add the generated layer to the current QGIS project """
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            feedback.pushInfo(f"Added layer {layer_name} to the current project.")
        else:
            feedback.reportError(f"Layer {layer_name} could not be added to the project.")

    def validateDistances(self, distances, feedback):
        # Check that distances are in ascending order and at least 10 meters apart
        for i in range(len(distances) - 1):
            if distances[i + 1] <= distances[i]:
                feedback.reportError("Buffers must be in increasing order.")
                return False
            if distances[i + 1] - distances[i] < 10:
                feedback.reportError("Each buffer must be at least 10 meters larger than the previous one.")
                return False
        return True

    def name(self):
        return 'concentric_donut_buffers'

    def displayName(self):
        return self.tr('Create Concentric Donut Buffers')

    def group(self):
        return self.tr('Johan Scripts')

    def groupId(self):
        return 'johan_scripts'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ConcentricDonutBuffers()
