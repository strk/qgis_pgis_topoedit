#/***************************************************************************
# PgTopoEditor
# 
# Edit toolbar for PostGIS topology primitives (ISO SQL/MM based)
#                     -------------------
#        begin        : 2011-10-21
#        copyright    : (C) 2011-2015 by Sandro Santilli <strk@keybit.net>
#        email        : strk@keybit.net
# ***************************************************************************/
# 
#/***************************************************************************
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 3 of the License, or     *
# *   (at your option) any later version.                                   *
# *                                                                         *
# ***************************************************************************/

# Makefile for a PyQGIS plugin 

PLUGINNAME = pgtopoeditor

PY_FILES = pgtopoeditor.py pgtopoeditordialog.py __init__.py

EXTRAS = icons/topoedit.png icons/remedge.png metadata.txt COPYING

UI_FILES = ui_pgtopoeditor.py

RESOURCE_FILES = resources.py

DISTFILES = $(PY_FILES) $(UI_FILES) $(RESOURCE_FILES) $(EXTRAS)

default: compile

compile: $(UI_FILES) $(RESOURCE_FILES)

%.py : %.qrc
	pyrcc4 -o $@  $<

%.py : %.ui
	pyuic4 -o $@ $<

# The deploy  target only works on unix like operating system where
# the Python plugin directory is located at:
# $HOME/.qgis/python/plugins
deploy: compile
	mkdir -p $(HOME)/.qgis/python/plugins/$(PLUGINNAME)
	cp -vf $(DISTFILES) $(HOME)/.qgis/python/plugins/$(PLUGINNAME)

dist: compile
	rm -f $(PLUGINNAME) # just in case
	ln -s . $(PLUGINNAME)
	( cd $(PLUGINNAME) && find $(DISTFILES); ) | sed 's@^@$(PLUGINNAME)/@' | zip $(PLUGINNAME).zip -@
	rm -f $(PLUGINNAME)

clean:
	rm -f $(PLUGINNAME).zip
	rm -f *.pyc
	rm -f resources.py ui_pgtopoeditor.py
