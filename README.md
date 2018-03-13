# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the bottom or the side panel.

It can:

- load a preview of your markdown file
- dynamically update the preview
- zoom in or out
- insert an image in your markdown file
- be displayed in the side panel or in the bottom panel
- apply a CSS stylesheet to the preview
- export your preview (in any format supported by pandoc)

## Dependencies

- `gedit` (of course)
- `pandoc`
- probably some WebkitGTK library (libwebkit2gtk-4.0-dev ?)

## Installation

- Download the project & extract the archive.
- Open the folder `gedit-plugin-markdown_preview-master` in a terminal
- Run the `install.sh` script in your terminal.

It needs root privileges because i didn't understand how to create setting schemas otherwise, but the plugin isn't installed system-wide.
