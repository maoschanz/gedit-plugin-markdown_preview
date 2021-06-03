
# Gedit Markdown Preview

<!-- TODO

- Faire une branche à part, où je tue:
	- [x] les options de pandoc,
	- [x] le support revealjs,
	- [x] le menu contextuel,
	- [x] et les raccourcis clavier associés

- [] En faire une release 1.0

- [~] différencier explicitement le chemin d'exécution pour l'ouverture d'un
  fichier (reconnaissance format etc.) d'un reload normal
	- [ ] si un doc est ouvert et que c'est désac et qu'on active, ça ne réagit
	      pas et on ne peut pas recharger
- print(doc.get_mime_type(), doc.get_content_type())
- [ ] CSS for admonitions (and other default plugins ?)
	- [ ] and pymdown ??
- [ ] bring back the fullscreen, but better

~     TODO -->

This is a plugin for the Gedit text editor, previewing .md files in the side pane
(<kbd>F9</kbd>) or the bottom (<kbd>Ctrl</kbd>+<kbd>F9</kbd>) pane.

### Previewing

- show a preview of a file
- dynamically update the preview
- zoom in or out on the preview
- search in the preview
- open links and images

This works for Markdown files, and theoretically HTML files too.

### Exporting

You can print the preview, or export it:

- if [`pandoc`](https://pandoc.org/) is installed on your system, you can export to any format it supports
	- a stylesheet can be applied to most file formats
	- options are available when exporting to a [revealjs](https://revealjs.com) slideshow (**WORK IN PROGRESS**)
	- be careful if you want to export to PDF: pandoc doesn't come with all necessary dependencies by default
- if only `python3-markdown` is installed, you can export to HTML
	- a stylesheet can be applied
	- `python3-markdown` [extensions](https://python-markdown.github.io/extensions/) can be used (including [third-party extensions](https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions) like [these great ones](https://facelessuser.github.io/pymdown-extensions/)

----

## Screenshots

| With the preview in the side pane, menu opened | With the preview in the bottom pane, searching |
|------|------|
| ![With the preview in the side pane, menu opened](https://i.imgur.com/wo2pUrR.png) | ![With the preview in the bottom pane, searching](https://i.imgur.com/NaVogWH.png) |

<!--TODO c'est pas à jour ça-->

----

## Installation

this plugin is **work in progress**, there is no stable release yet

### Dependencies

Be sure to have these packages installed before trying to install the plugin:

- `gedit` (≥3.22)
- `gir1.2-webkit2-4.0`
- `python3-markdown` or `pandoc`
- if you want to export to PDF with pandoc, you'll need `pdflatex` and `lmodern`

### Download

- Using the "**Clone or download**" button, download the project from github.
- Extract the archive.

(If you know how to do, you can also clone the repo with git.)

### Plugin installation

The script `install.sh` can be executed as root (system-wide installation) or as
a normal user (user-wide installation).

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
- or with the plugin's "3-dots menu" → Options

### General options

- Position of the preview (left side or bottom)
- If you want the plugin to understand relative paths (for links and pictures). This is not recommended if you use special characters in filenames (some versions of WebKit2GTK can't load URIs with special characters for some reason)

### Rendering options

The preview can be generated with [pandoc](https://pandoc.org/) or
[python-markdown](https://python-markdown.github.io/).

A stylesheet (CSS file) can be applied to the preview (markdown files only, it
will not be loaded for HTML files).

##### Options with python-markdown

A set of [extensions](https://python-markdown.github.io/extensions/) is provided
natively with python-markdown. You can enable or disable them depending on your
needs.

[Great third-party extensions](https://facelessuser.github.io/pymdown-extensions/)
exist too, and once installed they can be added manually to the list.

----

## Available languages

- English
- French
- Dutch

