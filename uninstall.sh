#!/bin/bash

if (( $EUID == 0 )); then

	echo "Removing setting schemas from /usr/share/glib-2.0/schemas"

	rm  /usr/share/glib-2.0/schemas/org.gnome.gedit.plugins.markdown_preview.gschema.xml
	glib-compile-schemas /usr/share/glib-2.0/schemas

	echo "Removing plugin files from /usr/lib/x86_64-linux-gnu/gedit/plugins/"
	
	rm /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview.plugin
	rm -r /usr/lib/x86_64-linux-gnu/gedit/plugins/markdown_preview

else

	echo "Removing setting schemas in ~/.local/share/glib-2.0/schemas"

	rm ~/.local/share/glib-2.0/schemas/org.gnome.gedit.plugins.markdown_preview.gschema.xml
	glib-compile-schemas ~/.local/share/glib-2.0/schemas

	echo "Removing plugin files in ~/.local/share/gedit/plugins/"

	rm ~/.local/share/gedit/plugins/markdown_preview.plugin
	rm -r  ~/.local/share/gedit/plugins/markdown_preview
		
fi

echo "Done."

exit
