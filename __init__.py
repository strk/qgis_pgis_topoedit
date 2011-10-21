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
 This script initializes the plugin, making it known to QGIS.
"""
def name():
    return "PostGIS Topology Editor"
def description():
    return "Edit toolbar for PostGIS topology primitives (ISO SQL/MM based)"
def version():
    return "Version 0.1"
def icon():
    return "icon.png"
def qgisMinimumVersion():
    return "1.0"
def classFactory(iface):
    # load PgTopoEditor class from file PgTopoEditor
    from pgtopoeditor import PgTopoEditor
    return PgTopoEditor(iface)
