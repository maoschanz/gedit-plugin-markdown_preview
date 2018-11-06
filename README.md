**please do not install the master version**

# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the bottom or the side panel.

Main features (v0.6), for any .md or .html file:

- load a preview of a file
- dynamically update the preview
- zoom in or out on the preview
- "slideshow" mode (preview your file section by section)
- export your preview (to any format supported by [pandoc](https://pandoc.org/))
- print your preview
- search in the page

Also:

- it can insert an image in your file (markdown only)
- it can open most relative links (as an option, because WebKit2GTK can't load URIs with special characters)
- it can apply a CSS stylesheet to the preview (markdown only)

The preview can be displayed in the side panel or in the bottom panel, and this setting can be changed dynamically.

----

## Screenshots

![With the preview in the bottom panel, slideshow mode, searching](https://i.imgur.com/4xnqoUZ.png)

![With the preview in the side panel, menu opened](https://i.imgur.com/k9qIsgw.png)

----

## Dependencies

- `gedit` (of course)
- `python3-markdown`
- `pandoc`
- `libwebkit2gtk-4.0-dev` (that's the name for debian-based distros)

## Installation

- Download the project & extract the archive (or clone the repo).
- Open the project's folder `gedit-plugin-markdown_preview-master` in a terminal
- Run the `install.sh` script

The script `install.sh` can be executed as root (installation system-wide) or as a normal user (installation user-wide, but it works only with some systems, weirdly).

## Available languages

- English
- ~~French~~

