# Gedit Markdown Preview

<!-- TODO

- [ ] comment retirer le fichier CSS ??
	- [ ] connecter le switch des préférences
	- [x] code dans preview.py
- [ ] pages séparées (général/style)
- [ ] help labels and links for pandoc too! et toutes les pages en fait
- [ ] CSS for admonitions (and other default plugins ?)
	- [ ] and pymdown ??
- [ ] cesser les zouaveries avec pandoc et les pre-strings/post-strings, il y a de vraies options
- [ ] reveal js https://github.com/jgm/pandoc/wiki/Using-pandoc-to-produce-reveal.js-slides
	- [ ] rendu
	- [ ] transitions
	- [ ] paramètres de thème
- [ ] compléter les descriptions des schémas
- [ ] se souvenir du splitter
- [ ] ajouter le réglage pour le splitter dans les préférences
- [ ] bring back the fullscreen, but better

~     TODO -->

This is a plugin for the Gedit text editor, previewing .md files in the side (`F9`) or the bottom (`Ctrl+F9`) pane.

<!-- Main features (version 0.8): -->

- Previewing:
	- show a preview of a file
	- dynamically update the preview
	- zoom in or out on the preview
	- search in the preview
	- open links and image
- Exporting:
	- print the preview
	- export to any file format supported by [pandoc](https://pandoc.org/)
	- or export to HTML with `python3-markdown` and its [extensions](https://python-markdown.github.io/extensions/)
- Edition assistance:
	- insert an image in your file
	- insert markdown tags in your text with right-click menu or keyboard shortcuts

----

## Installation

this plugin is **work in progress**, there is no stable release yet

### Dependencies

Be sure to have these packages installed before trying to install the plugin:

- `gedit` (≥3.22)
- `python3-markdown` or `pandoc`
- maybe `libwebkit2gtk-4.0-37`

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

The plugin's options can be accessed…

- from Gedit's preferences → Plugins → Markdown preview → Preferences
- or with the extension's "3-dots menu" → Options

Available settings include:

- The preview can be generated (and exported) with [pandoc](https://pandoc.org/) or [python-markdown](https://python-markdown.github.io/). A set of [extensions](https://python-markdown.github.io/extensions/) is provided with python-markdown.
- A stylesheet (CSS file) can be applied to the preview.
- Choose if you want the plugin to understand relative paths (for links and pictures). Not recommended if you use special characters in filenames (WebKit2GTK can't load URIs with special characters for some reason)
- Set keyboard shortcuts to add/remove tags *(beta)*

## Available languages

- English
- French
- Dutch

----

## Screenshots

![With the preview in the side panel, menu opened](https://i.imgur.com/wo2pUrR.png)

![With the preview in the bottom panel, searching](https://i.imgur.com/NaVogWH.png)

----

