# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the bottom or the side panel.

Main features (v0.4), for any .md or .html file:

- load a preview of a file
- dynamically update the preview
- zoom in or out on the preview
- "slideshow" mode (preview your file section by section)
- export your preview (to any format supported by [pandoc](https://pandoc.org/))
- print your preview

Also:

- it can insert an image in your file (markdown only)
- it can open most relative links (as an option, because WebKit2GTK can't load URIs with special characters)
- it can apply a CSS stylesheet to the preview (markdown only)

The preview be displayed in the side panel or in the bottom panel

----

## Screenshots

![With the preview in the bottom panel, slideshow mode](http://image.noelshack.com/fichiers/2018/11/5/1521221133-capture-d-ecran-de-2018-03-16-18-25-21.png)

![With the preview in the side panel, dynamically updated](http://image.noelshack.com/fichiers/2018/11/5/1521221246-capture-d-ecran-de-2018-03-16-18-27-19.png)

----

## Dependencies

- `gedit` (of course)
- `pandoc`
- `libwebkit2gtk-4.0-dev` (that's the name for .deb-based distros)

## Installation

- Download the project & extract the archive (or clone the repo).
- Open the project's folder `gedit-plugin-markdown_preview-master` in a terminal
- Run the `install.sh` script

The script `install.sh` can be executed as root (installation system-wide) or as a normal user (installation user-wide).

## Available languages

- English
- French

