# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the side (`F9`) or the bottom (`Ctrl+F9`) panel.

Main features (version 0.8):

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

## Installation

### Dependencies

Be sure to have these packages installed before trying to install the plugin:

- `gedit` (of course)
- `python3-markdown` or `pandoc`
<!--- maybe `libwebkit2gtk-4.0-dev` (that's the name for debian-based distros)-->

### Download

- Using the "**Clone or download**" button, download the project from github.
- Extract the archive.

(If you know how to do, you can also clone the repo with git.)

### Plugin installation

The script `install.sh` can be executed as root (system-wide installation) or as a normal user (user-wide installation, but that works only with some systems, weirdly).

- Open the project's folder in a terminal.
- Run `./install.sh`

The plugin is now installed and has to be activated:

- Open Gedit's preferences.
- Go to the "Plugins" tab.
- Enable the "Markdown Preview" plugin.

----

## Configuration

In Gedit's preferences → Plugins, you can select the plugin to access its settings:

- The preview can be generated (and exported) with [pandoc](https://pandoc.org/) or [python-markdown](https://python-markdown.github.io/). A set of extensions is available with python-markdown.
- A stylesheet (CSS file) can be applied to the preview.
- Chose if you want the plugin to understand relative paths (for links and pictures). Not recommended if you use special characters in filenames (WebKit2GTK can't load URIs with special characters for some reason)

## Available languages

- English
- French (theorically, but in fact it's broken)


