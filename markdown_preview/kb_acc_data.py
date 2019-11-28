# kb_acc_data.py
# GPLv3

import os

BASE_PATH = os.path.dirname(os.path.realpath(__file__))
LOCALE_PATH = os.path.join(BASE_PATH, 'locale')

try:
	import gettext
	gettext.bindtextdomain('gedit-plugin-markdown-preview', LOCALE_PATH)
	gettext.textdomain('gedit-plugin-markdown-preview')
	_ = gettext.gettext
except:
	_ = lambda s: s

# This file just provides data for building keyboard shortcuts

ACTIONS_NAMES = [
	'win.md-prev-format-italic',
	'win.md-prev-format-bold',
	'win.md-prev-insert-picture',
	'win.md-prev-format-title-lower',
	'win.md-prev-format-title-upper'
] # TODO pas fini évidemment

SETTINGS_KEYS = [
	'kb-italic',
	'kb-bold',
	'kb-insert-picture',
	'kb-title-lower',
	'kb-title-upper'
] # TODO pas fini évidemment

LABELS = [
	_("Italic"),
	_("Bold"),
	_("Insert a picture"),
	_("Lower title"),
	_("Upper title")
] # TODO pas fini évidemment

################################################################################

