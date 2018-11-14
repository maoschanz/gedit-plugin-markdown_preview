# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the bottom or the side panel.

Main features (v0.8):

- show a preview of a file
- dynamically update the preview (while remembering the position in the page)
- zoom in or out on the preview
- export your preview (to any format supported by [pandoc](https://pandoc.org/))
- print your preview
- search in the preview
- insert an image in your file or other markdown tags in your text

----

## Screenshots

![With the preview in the bottom panel, slideshow mode, searching](https://i.imgur.com/4xnqoUZ.png)

![With the preview in the side panel, menu opened](https://i.imgur.com/k9qIsgw.png)

----

## Dependencies

- `gedit` (of course)
- `python3-markdown` (that's the name for debian-based distros)
- `pandoc`
- maybe `libwebkit2gtk-4.0-dev` (that's the name for debian-based distros)

## Installation

- Download the project & extract the archive (or clone the repo).
- Open the project's folder `gedit-plugin-markdown_preview-master` in a terminal
- Run the `install.sh` script

The script `install.sh` can be executed as root (installation system-wide) or as a normal user (installation user-wide, but it works only with some systems, weirdly).

## Configuration

In gedit's preferences → plugins, some settings are available:

- The preview can be generated (and exported) with [pandoc](https://pandoc.org/) or [python-markdown](https://python-markdown.github.io/). A set of extensions is available with python-markdown.
- A stylesheet (CSS file) can be applied to the preview.
- Chose if you want the plugin to understand relative paths (for links and pictures). Not recommended if you use special characters in filenames (WebKit2GTK can't load URIs with special characters for some reason)

## Available languages

- English
- Theorically french, but in fact it's broken



