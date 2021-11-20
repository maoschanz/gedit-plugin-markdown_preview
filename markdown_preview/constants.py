# constants.py
# GPL v3

from .utils import init_gettext

_ = init_gettext()

################################################################################

MD_PREVIEW_KEY_BASE = 'org.gnome.gedit.plugins.markdown_preview'

BASE_TEMP_NAME = '/tmp/gedit_plugin_markdown_preview'

MARKDOWN_SPLITTERS = {
	'hr': "\n----",
	'h1': "\n# ",
	'h2': "\n## "
}

################################################################################

class HelpLabels():

	P3mdExtensions1 = _("Aside of default extensions provided by the " + \
	         "python3-markdown package, you can <b>install</b> third-party " + \
	      "extensions using instructions provided by their respective authors.")
	P3mdExtensions2 = _("These third-party extensions are <b>not</b> Gedit " + \
	                                   "plugins, they extend python3-markdown.")
	P3mdExtensions3 = _("Next, to improve the preview of your markdown " + \
	  "file with the features of these extensions, please add their module " + \
	                 "names to the list using the text entry and the '+' icon.")
	
	PandocGeneral = _("Pandoc is a command line utility with several " + \
	                      "possible options, input formats and output formats.")
	PandocCustom = _("Any command where $INPUT_FILE would be the input " + \
	       "file, and printing valid HTML to the standard output, is accepted.")
	PandocExport = _("Any command where $INPUT_FILE would be the input " + \
	         "file, and $OUTPUT_FILE the name of the output file, is accepted.")

	StyleCSS = _("You can select a stylesheet (.css file) to make your " + \
	           "document look nice and modern, or to increase its readability.")

	############################################################################
################################################################################

class BackendsEnums():

	P3mdExtensions = {
		'extra': _("Extras"),
		'toc': _("Table of content"),
		'codehilite': "CodeHilite",
		'nl2br': _("New Line To Break"),
		'smarty': "SmartyPants",
		'sane_lists': _("Sane Lists"),
		'admonition': _("Admonitions"),
		'wikilinks': _("WikiLinks")
	}
	P3mdDescriptions = {
		'extra': _("A compilation of various extensions (Abbreviations, Attribute Lists, Definition Lists, Fenced Code Blocks, Footnotes, Tables)."),
		'toc': _("Shows a clickable table of content with the [TOC] tag."),
		'nl2br': _("Adds a line break at each new line."),
		'smarty': _("Converts ASCII dashes, quotes and ellipses to their nice-looking equivalents."),
		'sane_lists': _("Alters the behavior of the lists syntax."),
		'admonition': _("Adds admonitions (notes, warnings, tips, …) with the !!! tag."),
		'wikilinks': _("Converts any [[bracketed]] word to a link."),
		'codehilite': _("Highlights your code with a correct syntax coloration (it needs to be set up and have some dependencies)."), # XXX et du coup, lesquelles?
	}

	############################################################################

	PandocFormatsFull = {
		'pdf': _("Portable Document Format (.pdf)"),
		'html5': _("HTML5"),
		'odt': _("OpenOffice text document (.odt)"),
		'docx': _("Microsoft Word (.docx)"),
		'latex': _("LaTeX (.tex)"),
		'beamer': _("LaTeX beamer slideshow (.tex)"),
		'plain': _("plain text (.txt)"),
		'pptx': _("PowerPoint slideshow (.pptx)"),
		'rtf': _("Rich Text Format (.rtf)"),
		'custom': _("Custom command line"),
	}
	PandocFormatsPreview = {
		'html5': _("HTML5"),
		# 'custom': _("Custom command line")
	}

	############################################################################
################################################################################

