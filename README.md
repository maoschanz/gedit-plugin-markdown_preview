# Gedit Markdown Preview

This is a plugin for the Gedit text editor, previewing .md files in the bottom or the side panel.

It can:

- load a preview of your markdown file
- zoom in or out
- insert an image in your markdown file
- be displayed in the side panel or in the bottom panel
- apply a CSS stylesheet to the preview

## Dependencies

- `gedit` (of course)
- `pandoc`
- probably the Python binding for WebkitGTK

## Installation

- Download (or clone) the repo.
- Open the folder `gedit-plugin-markdown_preview-master` in a terminal
- Run the `install.sh` script in your terminal.

It needs root privileges because i didn't understand how to create setting schemas otherwise, but the plugin isn't installed system-wide.
