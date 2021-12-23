
# Gedit Markdown Preview

<!-- TODO

Pour la release 3.0 :

- à terminer :
	- [ ] revealjs
	- [ ] clic-droit
	- [ ] raccourcis claviers
- [ ] numéro de version etc.

----

Pour un moment indéterminé :

Traceback (most recent call last):
  File "/home/roschan/.local/share/gedit/plugins/markdown_preview/prefs/rendering_settings.py", line 206, in on_remember
    new_command = self.pandoc_cli_entry.get_buffer().get_text()
TypeError: Gtk.TextBuffer.get_text() takes exactly 4 arguments (1 given)

- [~] différencier explicitement le chemin d'exécution pour l'ouverture d'un
      fichier (reconnaissance format etc.) d'un reload normal
	- [ ] si un doc est ouvert et que c'est désac et qu'on active, ça ne réagit
	      pas et on ne peut pas recharger
- reveal js https://github.com/jgm/pandoc/wiki/Using-pandoc-to-produce-reveal.js-slides
	- [ ] prefs
		- [ ] rendu fonctionnel
		- [ ] transitions
		- [ ] numéros de pages
		- [ ] paramètres de thème
	- [ ] export
		- [ ] ne pas désactiver l'entrée quand on exporte
		- [ ] rendu fonctionnel
		- [ ] transitions
		- [ ] numéros de pages
		- [ ] paramètres de thème
- print(doc.get_mime_type(), doc.get_content_type())
- [ ] CSS for admonitions (and other default plugins ?)
	- [ ] and pymdown ??
- [ ] bring back the fullscreen, but better

~     TODO -->

This is a plugin for the Gedit text editor, previewing .md files in the side
pane (<kbd>F9</kbd>) or the bottom (<kbd>Ctrl</kbd>+<kbd>F9</kbd>) pane.

### Previewing

- show a preview of a file
- dynamically update the preview
- zoom in or out on the preview
- search in the preview
- open links and images

This works for Markdown files, and HTML files.

### Exporting

You can print the preview, or export it:

- if [`pandoc`](https://pandoc.org/) is installed on your system, you can export to any format it supports
	- a stylesheet can be applied to most file formats
	- be careful if you want to export to PDF: pandoc doesn't come with all necessary dependencies by default
- if only `python3-markdown` is installed, you can export to HTML
	- a stylesheet can be applied
	- `python3-markdown` [extensions](https://python-markdown.github.io/extensions/) can be used (including [third-party extensions](https://github.com/Python-Markdown/markdown/wiki/Third-Party-Extensions) like [these great ones](https://facelessuser.github.io/pymdown-extensions/)

<!-- ### Editing assistance -->

<!-- - insert an image in your file -->
<!-- - insert markdown tags in your text with right-click menu or keyboard shortcuts -->

----

## Screenshots

| With the preview in the side pane, menu opened | With the preview in the bottom pane, searching |
|------|------|
| ![With the preview in the side pane, menu opened](https://i.imgur.com/wo2pUrR.png) | ![With the preview in the bottom pane, searching](https://i.imgur.com/NaVogWH.png) |

<!--TODO c'est pas à jour ça-->

----

## Installation

### Packages

- For Arch Linux and its derivatives: the [AUR](https://aur.archlinux.org/packages/gedit-plugin-markdown_preview) package is named `gedit-plugin-markdown_preview`.

Even if you install the plugin with a package manager, you may like to read the
following sections, since installing optional dependencies will enable new
features of the plugin.

### Manual installation

1. Dependencies. Be sure to have these packages before installing the plugin:
  - `gedit` (≥3.22)
  - `gir1.2-webkit2-4.0`
  - `python3-markdown` or `pandoc`
  - if you want to export to PDF with pandoc, you'll need at least `pdflatex`
    and `lmodern`. Those are provided by `texlive` packages whose names vary
    depending on the distribution. Warning: the version provided by Debian is
    sadly broken (some error message about *xcolor.sty*).
2. Download the ZIP of [the last release](https://github.com/maoschanz/gedit-plugin-markdown_preview/releases).
3. Extract the archive.
4. Open the project's folder in a terminal.
5. Run `./install.sh` — it can be executed as root (system-wide installation) or
   as a normal user (user-wide installation).

## Activation

The plugin is now installed and has to be enabled:

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

<!-- ##### Options with pandoc -->

<!-- You can decide to render the file: -->

<!-- - directly as HTML (it may then use the CSS file you set); -->
<!--- or as HTML with the stylesheet and javascript code from _revealjs_, to preview-->
<!--the file as a slideshow, which comes with pre-defined themes and slide-->
<!--transition types. (**WORK IN PROGRESS**);-->
<!--- or following what you write as the "custom" option: be sure to write a full-->
<!--correct command whose output will be HTML code, and press "Remember" to save-->
<!--your custom command. (**WORK IN PROGRESS**)-->

<!-- ### Keyboard shortcuts -->

<!-- Customize keyboard shortcuts to add/remove tags (**WORK IN PROGRESS**) -->

----

## Available languages

- English
- French
- Dutch

