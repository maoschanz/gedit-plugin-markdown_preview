#!/bin/bash

if (( $EUID == 0 )); then

	if [ ! -d "/usr/lib/x86_64-linux-gnu/gedit/plugins" ]; then
		mkdir /usr/lib/x86_64-linux-gnu/gedit/plugins
	fi

	echo "Installing setting schemas in /usr/share/glib-2.0/schemas"
	
	cp org.gnome.gedit.plugins.markdown_preview.gschema.xml /usr/share/glib-2.0/schemas
	glib-compile-schemas /usr/share/glib-2.0/schemas

	echo "Installing plugin files in /usr/lib/x86_64-linux-gnu/gedit/plugins/"
	
	cp markdown_preview.plugin /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.plugin
	cp -r markdown_preview /usr/lib/x86_64-linux-gnu/gedit/plugins/

else

	echo "Checking if adequate folders exist..."
	
	if [ ! -d "$HOME/.local/share/glib-2.0" ]; then
		mkdir ~/.local/share/glib-2.0
	fi
	if [ ! -d "$HOME/.local/share/glib-2.0/schemas" ]; then
		mkdir ~/.local/share/glib-2.0/schemas
	fi
	if [ ! -d "$HOME/.local/share/gedit" ]; then
		mkdir ~/.local/share/gedit
	fi
	if [ ! -d "$HOME/.local/share/gedit/plugins" ]; then
		mkdir ~/.local/share/gedit/plugins
	fi

	echo "Installing setting schemas in ~/.local/share/glib-2.0/schemas"

	cp org.gnome.gedit.plugins.markdown_preview.gschema.xml ~/.local/share/glib-2.0/schemas
	glib-compile-schemas ~/.local/share/glib-2.0/schemas

	echo "Installing plugin files in ~/.local/share/gedit/plugins/"

	cp markdown_preview.plugin ~/.local/share/gedit/plugins/markdown_preview.plugin
	cp -r markdown_preview ~/.local/share/gedit/plugins/
		
fi

echo "Done."

exit

