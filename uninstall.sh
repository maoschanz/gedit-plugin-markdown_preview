#!/bin/bash

if (( $EUID == 0 )); then
	install_dir="/usr/lib/x86_64-linux-gnu/gedit/plugins"
	schemas_dir="/usr/share/glib-2.0/schemas"
else
	install_dir="$HOME/.local/share/gedit/plugins"
	schemas_dir="$HOME/.local/share/glib-2.0/schemas"
fi

echo "Removing setting schemas from $schemas_dir"
rm $schemas_dir/org.gnome.gedit.plugins.markdown_preview.gschema.xml
glib-compile-schemas $schemas_dir

echo "Removing plugin files from $install_dir"
rm $install_dir/markdown_preview.plugin
rm -r $install_dir/markdown_preview

echo "Done."
exit 0

