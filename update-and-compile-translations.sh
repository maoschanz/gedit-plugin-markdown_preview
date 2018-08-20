#!/bin/bash

echo "Generating .pot file..."
xgettext --files-from=POTFILES --output=markdown_preview/locale/gedit-plugin-markdown-preview.pot

IFS='
'
liste=`ls ./markdown_preview/locale/`

for dossier in $liste
do
	if [ "$dossier" != "gedit-plugin-markdown-preview.pot" ]; then
		echo "Updating translation for: $dossier"
		msgmerge ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.po ./markdown_preview/locale/gedit-plugin-markdown-preview.pot > ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.temp.po
		mv ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.temp.po ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.po
		echo "Compiling translation for: $dossier"
		msgfmt ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.po -o ./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview.mo
	fi
done

exit 0
