"""
/***************************************************************************
 PgTopoEditorDialog
                                 A QGIS plugin
 Edit toolbar for PostGIS topology primitives (ISO SQL/MM based)
                        -------------------
        begin          : 2011-10-21
        copyright      : (C) 2011-2015 by Sandro Santilli <strk@kbt.io>
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

from qgis.PyQt import QtWidgets
from .ui_pgtopoeditor import Ui_PgTopoEditor
# create the dialog for zoom to point
class PgTopoEditorDialog(QtWidgets.QDialog):
    def __init__(self):
        QtWidgets.QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = Ui_PgTopoEditor()
        self.ui.setupUi(self)
