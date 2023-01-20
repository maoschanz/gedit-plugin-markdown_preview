#!/bin/bash

function throw_error () {
	echo -e "\e[1m\e[7m\e[41m$1\e[0m"
	exit 1
}

if (( $EUID == 0 )); then
	install_dir="/usr/lib/x86_64-linux-gnu/gedit/plugins"
	schemas_dir="/usr/share/glib-2.0/schemas"
else
	install_dir="$HOME/.local/share/gedit/plugins"
	schemas_dir="$HOME/.local/share/glib-2.0/schemas"
fi

echo "Checking if adequate folders exist…"
mkdir -p $install_dir
mkdir -p $schemas_dir

echo "Installing setting schemas in $schemas_dir"
cp org.gnome.gedit.plugins.markdown_preview.gschema.xml $schemas_dir
glib-compile-schemas $schemas_dir || throw_error "Have you installed libglib2.0-bin?"

echo "Installing plugin files in $install_dir"
cp markdown_preview.plugin $install_dir/markdown_preview.plugin
cp -r markdown_preview $install_dir/

echo "Done."
exit 0
