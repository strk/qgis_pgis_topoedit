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
 *   the Free Software Foundation; either version 3 of the License, or     *
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

        # Create action for ST_ModEdgeHeal
        self.action_remedge = QAction(QIcon(":/plugins/pgtopoeditor/icons/healedge.png"), \
            "ST_ModEdgeHeal", self.iface.mainWindow())
        QObject.connect(self.action_remedge, SIGNAL("triggered()"), self.doModEdgeHeal)
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

        uri = QgsDataSourceURI( layer.source() )

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        edge_id_fno = layer.fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return 

        # get the selected features
        errors = []
        selected = layer.selectedFeatures()
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        for feature in selected:
          # get its edge_id
          edge_id = feature.attributeMap()[edge_id_fno].toInt()[0]
          try:
            cur = conn.cursor()
            cur.execute("SELECT ST_RemEdgeModFace(%s, %s)", (toponame, edge_id))
            conn.commit()
            cur.close()
          except psycopg2.Error as e:
            errors.append("Removing edge " + str(edge_id) + ":\n" + str(e))
            conn.commit()
            cur.close()
            continue
        conn.close()

        removed = len(selected) - len(errors)
        report = "Removed " + str(removed) + " edges over " + str(len(selected)) + " selected\n"
        if errors:
          report += "\nFailures ("
          if len(errors) > 5:
            report += "first 5 of "
          report += str(len(errors)) + "):\n\n" + "\n".join(errors[:5])
        QMessageBox.information(None, toolname, report)

        #QMessageBox.information(None, toolname, "Edge " + str(edge_id) + " in topology " + toponame + " removed");
        self.iface.mapCanvas().refresh()

    # Remove selected nodes (if of degree 2)
    def doModEdgeHeal(self):

        toolname = "EdgeHeal"

        # check that a layer is selected
        layer = self.iface.mapCanvas().currentLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A topology edge layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        uri = QgsDataSourceURI( layer.source() )

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        edge_id_fno = layer.fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return 

        # get the selected features
        selected = layer.selectedFeatures()
        if ( len(selected) != 2 ):
          QMessageBox.information(None, toolname, "You must select exactly two edges")
          return 

        # get their edge_id
        edge1_id = selected[0].attributeMap()[edge_id_fno].toInt()[0]
        edge2_id = selected[1].attributeMap()[edge_id_fno].toInt()[0]
        try:
            conn = psycopg2.connect( str(uri.connectionInfo()) )
            cur = conn.cursor()
            cur.execute("SELECT ST_ModEdgeHeal(%s, %s, %s)", (toponame, edge1_id, edge2_id))
            conn.commit()
            cur.close()
            self.iface.mapCanvas().refresh()
        except psycopg2.Error as e:
            QMessageBox.information(None, toolname, str(e));
            conn.commit()
            cur.close()
            conn.close()


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
          QMessag.Bo.information(None, toolname, "Selected layer must be a table, not a view\n"
            "(no table set in datasource)")
          return;

        # get the layer column
        col = str(uri.geometryColumn())
        if not col:
          QMessageBox.information(None, toolname, "Selected layer must be a table, not a view\n"
            "(no column set in datasource)")
          return;


        layername = '"' + schema + '"."' + table + '"."' + col +'"'

        try:
          conn = psycopg2.connect( str(uri.connectionInfo()) )
          cur = conn.cursor()

          # get the layer topology
          cur.execute("SELECT t.name, l.layer_id FROM topology.topology t, topology.layer l WHERE l.schema_name = %s AND l.table_name = %s AND l.feature_column = %s AND t.id = l.topology_id", (schema, table, col))
          if cur.rowcount == 1:
            (toponame, layer_id) = cur.fetchone()

            # delete orphaned geoms...
            cur.execute('DELETE FROM "' + toponame
              + '"."relation" WHERE layer_id = %s AND topogeo_id NOT IN ( SELECT id("'
              + col + '") FROM "' + schema + '"."' + table + '")', (str(layer_id)))
            QMessageBox.information(None, toolname, str(cur.rowcount)
              + ' orphaned topogeometry objects removed from layer ' + layername)

            conn.commit()
          else:
            QMessageBox.information(None, toolname, layername + ' is not a topology layer (not registered in topology.layer table)')
          cur.close()
          conn.close()
        except psycopg2.Error as e:
          QMessageBox.information(None, toolname, "ERROR: " + str(e))
          return

        #QMessageBox.information(None, toolname, "Not implemeted yet, but we know the layer is " + schema + "." + table + "." + col + ", the topology name is " + toponame + " and layer_id is " + str(layer_id))
        self.iface.mapCanvas().refresh()
          
