#!/bin/bash

if [ ! -d "$HOME/.local/share/glib-2.0" ]; then
	mkdir ~/.local/share/glib-2.0
fi
if [ ! -d "$HOME/.local/share/glib-2.0/schemas" ]; then
	mkdir ~/.local/share/glib-2.0/schemas
fi

cp org.gnome.gedit.plugins.markdown_preview.gschema.xml ~/.local/share/glib-2.0/schemas
glib-compile-schemas ~/.local/share/glib-2.0/schemas

cp markdown_preview.plugin ~/.local/share/gedit/plugins/markdown_preview.plugin
cp -r markdown_preview ~/.local/share/gedit/plugins/

#sudo cp markdown_preview.py /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.py
#sudo cp markdown_preview.plugin /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.plugin

