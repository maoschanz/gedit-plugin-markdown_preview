#!/bin/bash

sudo cp org.gnome.gedit.plugins.markdown_preview.gschema.xml /usr/share/glib-2.0/schemas/org.gnome.gedit.plugins.markdown_preview.gschema.xml
sudo glib-compile-schemas /usr/share/glib-2.0/schemas/
cp markdown_preview.plugin ~/.local/share/gedit/plugins/markdown_preview.plugin
cp markdown_preview.py ~/.local/share/gedit/plugins/markdown_preview.py
#sudo cp markdown_preview.py /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.py
#sudo cp markdown_preview.plugin /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.plugin

