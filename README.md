# Gedit Markdown Preview

<!-- TODO

- [ ] tex support sucks, remove it entirely
- [ ] casser prefs_and_export en 2 mais intelligemment
- [ ] help labels and links for pandoc too! et toutes les pages en fait
- [ ] CSS for admonitions (and other default plugins ?)
	- [ ] and pymdown ??
- [ ] reveal js https://github.com/jgm/pandoc/wiki/Using-pandoc-to-produce-reveal.js-slides
	- [ ] rendu
	- [ ] transitions
	- [ ] numéros de pages
	- [ ] paramètres de thème
- [ ] se souvenir du splitter
- [ ] ajouter le réglage pour le splitter dans les préférences
- [ ] bring back the fullscreen, but better
- [ ] style broken with paginated HTML

~     TODO -->

This is a plugin for the Gedit text editor, previewing .md files in the side (`F9`) or the bottom (`Ctrl+F9`) pane.

## Main features

### Previewing

- show a preview of a file
- dynamically update the preview
- zoom in or out on the preview
- search in the preview
- open links and images

This works for Markdown files (and theorically HTML files)

### Exporting

You can print the preview, or export it:

- if [pandoc](https://pandoc.org/) is installed on your system, you can export to any format it supports
	- a stylesheet can be applied to most file formats
	- options are available when exporting to a [https://revealjs.com](revealjs) slideshow (**WORK IN PROGRESS**)
- if only `python3-markdown` is installed, you can export to HTML
	- a stylesheet can be applied
	- `python3-markdown` [extensions](https://python-markdown.github.io/extensions/) can be used (including [third-party extensions](https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions) like [these great ones](https://facelessuser.github.io/pymdown-extensions/)

### Editing assistance

- insert an image in your file
- insert markdown tags in your text with right-click menu or keyboard shortcuts

----

## Screenshots

![With the preview in the side pane, menu opened](https://i.imgur.com/wo2pUrR.png)

![With the preview in the bottom pane, searching](https://i.imgur.com/NaVogWH.png)

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

### General options

- Select the position of the pane
- Choose if you want the plugin to understand relative paths (for links and pictures). Not recommended if you use special characters in filenames (some versions of WebKit2GTK can't load URIs with special characters for some reason)

### Rendering options

The preview can be generated with [pandoc](https://pandoc.org/) or [python-markdown](https://python-markdown.github.io/).

##### Options with pandoc

You can decide to render the file as classic HTML (it may then use the CSS file you set) or as HTML with the stylesheet and javascript code from _revealjs_. (**WORK IN PROGRESS**)

A third "custom" option is possible: be sure to write a full, correct command whose output will be HTML, press "Remember" to save your custom command. (**WORK IN PROGRESS**)

##### Options with python-markdown

A set of [extensions](https://python-markdown.github.io/extensions/) is provided natively with python-markdown. You can enable or disable them depending on your needs.

[Great third-party extensions](https://facelessuser.github.io/pymdown-extensions/) exist too, and once installed they can be added manually to the list.

### Style

A stylesheet (CSS file) can be applied to the preview.

- doesn't work when previewing HTML files
- doesn't work if you preview the file as a revealjs slideshow

<!--TODO-->
<!--revealjs options-->

### Keyboard shortcuts

Set keyboard shortcuts to add/remove tags (**WORK IN PROGRESS**)

----

## Available languages

- English
- French
- Dutch


