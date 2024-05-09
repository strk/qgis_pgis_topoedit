"""
/***************************************************************************
 PgTopoEditor
                                 A QGIS plugin
 Edit toolbar for PostGIS topology primitives (ISO SQL/MM based)
                        -------------------
        begin          : 2011-10-21
        copyright      : (C) 2011-2016 by Sandro Santilli <strk@kbt.io>
        email          : strk@kbt.io
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
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QProgressBar
from qgis.core import Qgis, QgsDataSourceUri
from qgis.gui import QgsMessageBar
# Initialize Qt resources from file resources.py
from . import resources
# Import the code for the dialog
from .pgtopoeditordialog import PgTopoEditorDialog

import psycopg2

def getIntAttributeByIndex(feature, index):
  # QMessageBox.information(None, '?', "Version of qgis is " + str(QGis.QGIS_VERSION_INT))
  if Qgis.QGIS_VERSION_INT < 10900:
    return feature[index].toInt()[0]
  else:
    return feature[index]

class PgTopoEditor:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface

    def initGui(self):

        self.toolbar = self.iface.addToolBar('PostGIS Topology Edit Toolbar');
        self.toolbar.setObjectName('PostGIS_Topology_Edit_Toolbar');

        # Create action for selecting dangling edges
        action = QAction(QIcon(":/plugins/pgtopoeditor/icons/seldanglingedge.png"), \
            "Select dangling edges", self.iface.mainWindow())
        action.triggered.connect(self.doSelDanglingEdges)
        self.toolbar.addAction(action)

        # Create action for selecting edge's left ring
        action = QAction(QIcon(":/plugins/pgtopoeditor/icons/selringleft.png"), \
            "Select left ring", self.iface.mainWindow())
        action.triggered.connect(self.doSelLeftRing)
        self.toolbar.addAction(action)

        # Create action for selecting edge's right ring
        action = QAction(QIcon(":/plugins/pgtopoeditor/icons/selringright.png"), \
            "Select right ring", self.iface.mainWindow())
        action.triggered.connect(self.doSelRightRing)
        self.toolbar.addAction(action)

        # Create action for ST_RemEdgeModFace
        action = QAction(QIcon(":/plugins/pgtopoeditor/icons/remedge.png"), \
            "Remove selected edges", self.iface.mainWindow())
        action.triggered.connect(self.doRemEdgeModFace)
        self.toolbar.addAction(action)

        # Create action for ST_ModEdgeHeal
        action = QAction(QIcon(":/plugins/pgtopoeditor/icons/healedge.png"), \
            "Remove selected nodes", self.iface.mainWindow())
        action.triggered.connect(self.doRemoveNode)
        self.toolbar.addAction(action)

        # Create action for collecting orphaned topogeom
        self.action_gctgeom = QAction(QIcon(":/plugins/pgtopoeditor/icons/gctgeom.png"), \
            "Collect orphaned TopoGeoms", self.iface.mainWindow())
        self.action_gctgeom.triggered.connect(self.doDropOrphanedTopoGeoms)
        self.toolbar.addAction(self.action_gctgeom)

    def unload(self):
        # Remove the plugin menu item and icons
        del self.toolbar

    def requireEdgeLayerSelected(self, toolname):
        # check that a layer is selected
        layer = self.iface.activeLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A topology edge layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        return layer

    # Select dangling edges
    def doSelDanglingEdges(self):

        toolname = "SelectDanglingEdges"

        # check that a layer is selected
        layer = self.iface.activeLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A topology edge layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        uri = QgsDataSourceUri(layer.source())

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        edge_id_fno = layer.dataProvider().fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return

        # find dangling edges
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        cur = conn.cursor()
        #cur.execute('SELECT edge_id FROM "' + toponame + '".edge_data LIMIT 1')
        cur.execute('''
select distinct (array_agg(e.edge_id))[1] eid
from "''' + toponame + '''".edge_data e, "''' + toponame + '''".node n
   where ( n.node_id = e.start_node or n.node_id = e.end_node )
    and e.start_node != e.end_node
    group by n.node_id
    having count(e.edge_id) = 1''')
        fids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()

        layer.select( fids )
        # layer.select seems to automatically refresh canvas
        #self.iface.mapCanvas().refresh()

    # Select left ring of edge
    def doSelLeftRing(self):

        toolname = "SelectLeftRing"

        # check that a layer is selected
        layer = self.requireEdgeLayerSelected(toolname)
        if not layer:
          return

        uri = QgsDataSourceUri(layer.source())

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return

        edge_id_fno = layer.dataProvider().fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return

        # get the selected features
        errors = []
        selected = layer.selectedFeatures()
        if not selected:
          QMessageBox.information(None, toolname, "Select the edge you want the left ring of")
          return
        if len(selected) > 1:
          QMessageBox.information(None, toolname, "Select a single edge")
          return

        feature = selected[0]
        edge_id = getIntAttributeByIndex(feature, edge_id_fno)

        # find left ring
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        cur = conn.cursor()
        cur.execute("select distinct abs(edge) from GetRingEdges('{toponame}',{edge_id})".
          format(toponame=toponame, edge_id=edge_id)
        )
        fids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()

        layer.select( fids )

    # Select right ring of edge
    def doSelRightRing(self):

        toolname = "SelectRightRing"

        # check that a layer is selected
        layer = self.requireEdgeLayerSelected(toolname)
        if not layer:
          return

        uri = QgsDataSourceUri(layer.source())

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return

        edge_id_fno = layer.dataProvider().fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return

        # get the selected features
        errors = []
        selected = layer.selectedFeatures()
        if not selected:
          QMessageBox.information(None, toolname, "Select the edge you want the left ring of")
          return
        if len(selected) > 1:
          QMessageBox.information(None, toolname, "Select a single edge")
          return

        feature = selected[0]
        edge_id = getIntAttributeByIndex(feature, edge_id_fno)

        # find right ring
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        cur = conn.cursor()
        cur.execute("select distinct abs(edge) from GetRingEdges('{toponame}',{edge_id})".
          format(toponame=toponame, edge_id=-edge_id)
        )
        fids = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()

        layer.select( fids )


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

        uri = QgsDataSourceUri(layer.source())

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology edge layer.\n(no schema set in datasource)")
          return;

        edge_id_fno = layer.dataProvider().fieldNameIndex('edge_id')
        if ( edge_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'edge_id' field (not a topology edge layer?)")
          return 

        # get the selected features
        errors = []
        selected = layer.selectedFeatures()
        if not selected:
          QMessageBox.information(None, toolname, "Select the edge(s) you want to remove")
          return
        msgBar = self.iface.messageBar()
        pb = QProgressBar( msgBar )
        msgBar.pushWidget( pb, Qgis.Info, 5 )
        pb.setRange( 0, len(selected) )
        pb.setValue( 0 )
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        for feature in selected:
          pb.setValue(pb.value()+1)
          # get its edge_id
          edge_id = getIntAttributeByIndex(feature, edge_id_fno)
          try:
            cur = conn.cursor()
            cur.execute("SELECT topology.ST_RemEdgeModFace(%s, %s)", (toponame, edge_id))
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

        layer.removeSelection()
        self.iface.mapCanvas().refresh()

    # Remove selected nodes (of degree 2 or isolated)
    def doRemoveNode(self):

        toolname = "RemoveNode"

        # check that a layer is selected
        layer = self.iface.mapCanvas().currentLayer()
        if not layer:
          QMessageBox.information(None, toolname, "A topology node layer must be selected")
          return

        # check that the selected layer is a postgis one
        if layer.providerType() != 'postgres':
          QMessageBox.information(None, toolname, "A PostGIS layer must be selected")
          return

        uri = QgsDataSourceUri(layer.source())

        # get the layer schema
        toponame = str(uri.schema())
        if not toponame:
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " doesn't look like a topology node layer.\n(no schema set in datasource)")
          return;

        node_id_fno = layer.dataProvider().fieldNameIndex('node_id')
        if ( node_id_fno < 0 ):
          QMessageBox.information(None, toolname, "Layer " + layer.name() + " does not have an 'node_id' field (not a topology node layer?)")
          return 

        # get the selected features
        errors = []
        selected = layer.selectedFeatures()
        if not selected:
          QMessageBox.information(None, toolname, "Select the node(s) you want to remove")
          return
        msgBar = self.iface.messageBar()
        pb = QProgressBar( msgBar )
        msgBar.pushWidget( pb, Qgis.Info, 5 )
        pb.setRange( 0, len(selected) )
        pb.setValue( 0 )
        conn = psycopg2.connect( str(uri.connectionInfo()) )
        for feature in selected:
          pb.setValue(pb.value()+1)
          # get its node_id
          node_id = getIntAttributeByIndex(feature, node_id_fno)
          try:
            cur = conn.cursor()
            cur.execute("SELECT abs((topology.GetNodeEdges(%s, %s)).edge)", (toponame, node_id))
            if cur.rowcount == 2:
              (edge1_id) = cur.fetchone()
              (edge2_id) = cur.fetchone()
              cur.close()
              if edge1_id != edge2_id:
                cur = conn.cursor()
                cur.execute("SELECT topology.ST_ModEdgeHeal(%s, %s, %s)", (toponame, edge1_id, edge2_id))
                conn.commit()
                cur.close()
              else:
                errors.append("Node " + str(node_id) + " is the only node in a ring, cannot be removed")
            elif cur.rowcount == 0:
              cur.close()
              cur = conn.cursor()
              cur.execute("SELECT topology.ST_RemIsoNode(%s, %s)", (toponame, node_id))
              conn.commit()
              cur.close()
            else:
              cur.close()
              errors.append("Node " + str(node_id) + " is not of degree 2 nor isolated")

          except psycopg2.Error as e:
            errors.append("Removing node " + str(node_id) + ":\n" + str(e))
            conn.commit()
            cur.close()
            continue
        conn.close()

        removed = len(selected) - len(errors)
        report = "Removed " + str(removed) + " nodes over " + str(len(selected)) + " selected\n"
        if errors:
          report += "\nFailures ("
          if len(errors) > 5:
            report += "first 5 of "
          report += str(len(errors)) + "):\n\n" + "\n".join(errors[:5])
        QMessageBox.information(None, toolname, report)

        layer.removeSelection()
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

        uri = QgsDataSourceUri( layer.source() )

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


        layername = '"' + schema + '"."' + table + '"."' + col +'"'

        try:
          conn = psycopg2.connect( str(uri.connectionInfo()) )
          cur = conn.cursor()

          # get the layer topology
          cur.execute("SELECT t.name, l.layer_id FROM topology.topology t, topology.layer l WHERE l.schema_name = %s AND l.table_name = %s AND l.feature_column = %s AND t.id = l.topology_id", (schema, table, col))
          if cur.rowcount == 1:
            (toponame, layer_id) = cur.fetchone()

            # delete orphaned geoms...
            cur.execute('DELETE FROM "' + toponame +
              '"."relation" WHERE layer_id = %s AND topogeo_id NOT IN ( SELECT id("'
              + col + '") FROM "' + schema + '"."' + table + '")', (str(layer_id),))
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
          
