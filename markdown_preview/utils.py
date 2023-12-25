
import importlib, shutil, os, gi
from gi.repository import Gio

def recognize_format(document):
	name = get_display_name(document)

	mime = None
	if document.get_language():
		mime = document.get_language().get_mime_types()[0]

	if mime and 'markdown' in mime:
		extension = 'md'
	elif mime and 'html' in mime:
		extension = 'html'
	elif name is None:
		# jadis on avait une API "is_untitled" mais elle a été virée et personne
		# n'a l'air de savoir pourquoi ni d'en avoir quelque chose à foutre
		extension = _("Unsaved document")
	elif '.' in name:
		extension = name.split('.')[-1].lower()
	elif mime is None:
		extension = _("Unknown document")
	else:
		extension = mime

	if extension == 'svg':
		# The webview can render SVG files too, so we take advantage of that.
		extension = 'html'

	return extension

def get_display_name(document):
	try:
		file = document.get_file().get_location()
		file_info = file.query_info(Gio.FILE_ATTRIBUTE_STANDARD_DISPLAY_NAME, 0, None)
	except Exception as e:
		return None
	return file_info.get_display_name()

################################################################################

def get_backends_dict():
	return {
		'pandoc': shutil.which('pandoc') is not None,
		'p3md': importlib.util.find_spec('markdown') is not None
	}

################################################################################

def init_gettext():
	current_folder_path = os.path.dirname(os.path.realpath(__file__))
	locale_path = os.path.join(current_folder_path, 'locale')

	try:
		import gettext
		gettext.bindtextdomain('gedit-plugin-markdown-preview', locale_path)
		gettext.textdomain('gedit-plugin-markdown-preview')
		_ = gettext.gettext
	except:
		_ = lambda s: s

	return _

################################################################################

