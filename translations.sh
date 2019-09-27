#!/bin/bash

echo "Generating .pot file…"
xgettext --files-from=POTFILES --from-code=UTF-8 --output=markdown_preview/locale/gedit-plugin-markdown-preview.pot

IFS='
'
liste=`ls ./markdown_preview/locale/`

for dossier in $liste
do
	if [ "$dossier" != "gedit-plugin-markdown-preview.pot" ]; then
		echo "Updating translation for: $dossier"
		filename="./markdown_preview/locale/$dossier/LC_MESSAGES/gedit-plugin-markdown-preview"
		msgmerge $filename.po ./markdown_preview/locale/gedit-plugin-markdown-preview.pot > $filename.temp.po
		mv $filename.temp.po $filename.po
		echo "Compiling translation for: $dossier"
		msgfmt $filename.po -o $filename.mo
	fi
done

echo "Done."
exit 0
