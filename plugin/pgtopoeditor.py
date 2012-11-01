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

        self.toolbar = self.iface.addToolBar('topoedit');

        # Create action for ST_RemEdgeModFace
        self.action_remedge = QAction(QIcon(":/plugins/pgtopoeditor/icons/remedge.png"), \
            "ST_RemEdgeModFace", self.iface.mainWindow())
        QObject.connect(self.action_remedge, SIGNAL("triggered()"), self.doRemEdgeModFace)
        self.toolbar.addAction(self.action_remedge)

        # Create action for collecting orphaned topogeom
        self.action_gctgeom = QAction(QIcon(":/plugins/pgtopoeditor/icons/gctgeom.png"), \
            "Collect orphaned TopoGeoms", self.iface.mainWindow())
        QObject.connect(self.action_gctgeom, SIGNAL("triggered()"), self.doDropOrphanedTopoGeoms)
        self.toolbar.addAction(self.action_gctgeom)

    def unload(self):
        # Remove the plugin menu item and icons
        del self.toolbar

    # Remove selected edge
    def doRemEdgeModFace(self):

        toolname = "RemoveEdge"

        # check that a layer is selected
        layer = self.iface.mapCanvas().currentLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A topology edge layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        # get the selected features
        selected = layer.selectedFeatures()
        if len(selected) != 1:
          QMessageBox.information(None, toolname, "A (single) edge must be selected.\n" + str(len(selected)) + " feature selected instead")
          return
        feature = selected[0]

        # get its edge_id
        edge_id_fno = layer.fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "The selected feature does not have an 'edge_id' field (not a topology edge layer?)")
          return
        edge_id = feature.attributeMap()[edge_id_fno].toInt()[0]

        uri = QgsDataSourceURI( layer.source() )

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        try:
          conn = psycopg2.connect( str(uri.connectionInfo()) )
          cur = conn.cursor()
          cur.execute("SELECT ST_RemEdgeModFace(%s, %s)", (toponame, edge_id))
          conn.commit()
          cur.close()
          conn.close()
        except psycopg2.Error as e:
          QMessageBox.information(None, toolname, "ERROR: " + str(e))
          return

        #QMessageBox.information(None, toolname, "Edge " + str(edge_id) + " in topology " + toponame + " removed");
        self.iface.mapCanvas().refresh()

    # Collect all topogeoms registered as being in the currently selected
    # topolayer and not really present in it
    #
    def doDropOrphanedTopoGeoms(self):

        toolname = "CollectTopogeoms"

        # check that a layer is selected
        layer = self.iface.mapCanvas().currentLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A TopoGeom layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        uri = QgsDataSourceURI( layer.source() )

        # get the layer schema
        schema = str(uri.schema())
        if not schema:
          QMessageBox.information(None, toolname, "Selected layer must be a table, not a view\n"
            "(no schema set in datasource " + str(uri.uri()) + ")")
          return;

        # get the layer table
        table = str(uri.table())
        if not table:
          QMessageBox.information(None, toolname, "Selected layer must be a table, not a view\n"
            "(no table set in datasource)")
          return;

        # get the layer column
        col = str(uri.geometryColumn())
        if not col:
          QMessageBox.information(None, toolname, "Selected layer must be a table, not a view\n"
            "(no column set in datasource)")
          return;

        # TODO: get the layer topology

# "delete from hun_adm1_topo.relation where layer_id = 1 and topogeo_id not in ( select id(topogeom) from hun_adm1 );"
        QMessageBox.information(None, toolname, "Not implemeted yet, but we know the layer is " + schema + "." + table + "." + col)


#        try:
#          conn = psycopg2.connect( str(uri.connectionInfo()) )
#          cur = conn.cursor()
#          cur.execute("SELECT ST_RemEdgeModFace(%s, %s)", (toponame, edge_id))
#          conn.commit()
#          cur.close()
#          conn.close()
#        except psycopg2.Error as e:
#          QMessageBox.information(None, "RemoveEdge", "ERROR: " + str(e))
#          return
#
#        #QMessageBox.information(None, "RemoveEdge", "Edge " + str(edge_id) + " in topology " + toponame + " removed");
#        self.iface.mapCanvas().refresh()
          
