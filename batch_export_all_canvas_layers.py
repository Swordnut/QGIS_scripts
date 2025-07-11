for vLayer in iface.mapCanvas().layers():
    QgsVectorFileWriter.writeAsVectorFormat( vLayer, 
        myDir + vLayer.name() + ".shp", "utf-8", 
        vLayer.crs(), "ESRI Shapefile" )