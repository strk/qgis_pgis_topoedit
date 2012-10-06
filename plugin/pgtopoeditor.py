"""
/***************************************************************************
 PgTopoEditor
                                 A QGIS plugin
 Edit toolbar for PostGIS topology primitives (ISO SQL/MM based)
                              -------------------
        begin                : 2011-10-21
        copyright            : (C) 2011 by Sandro Santilli <strk@keybit.net>
        email                : strk@keybit.net
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from pgtopoeditordialog import PgTopoEditorDialog

import psycopg2

class PgTopoEditor:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/pgtopoeditor/icons/remedge.png"), \
            "ST_RemEdgeModFace", self.iface.mainWindow())
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.doRemEdgeModFace)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        #self.iface.addPluginToDatabaseMenu("&PostGIS Topology Editor", self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        #self.iface.removeDatabaseMenu("&PostGIS Topology Editor",self.action)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def doRemEdgeModFace(self):

        # check that a layer is selected
        layer = self.iface.mapCanvas().currentLayer()
        if not layer:
          QMessageBox.information(None, "RemoveEdge", "A topology edge layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, "RemoveEdge", "A PostGIS layer must be selected")
          return

        # get the selected features
        selected = layer.selectedFeatures()
        if len(selected) != 1:
          QMessageBox.information(None, "RemoveEdge", "A (single) edge must be selected.\n" + str(len(selected)) + " feature selected instead")
          return
        feature = selected[0]

        # get its edge_id
        edge_id_fno = layer.fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, "RemoveEdge", "The selected feature does not have an 'edge_id' field (not a topology edge layer?)")
          return
        edge_id = feature.attributeMap()[edge_id_fno].toInt()[0]

        uri = QgsDataSourceURI( layer.source() )

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, "RemoveEdge", "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        try:
          conn = psycopg2.connect( str(uri.connectionInfo()) )
          cur = conn.cursor()
          cur.execute("SELECT ST_RemEdgeModFace(%s, %s)", (toponame, edge_id))
          conn.commit()
          cur.close()
          conn.close()
        except psycopg2.Error as e:
          QMessageBox.information(None, "RemoveEdge", "ERROR: " + str(e))
          return

        QMessageBox.information(None, "RemoveEdge", "Edge " + str(edge_id) + " in topology " + toponame + " removed");
        self.iface.mapCanvas().refresh()

          
