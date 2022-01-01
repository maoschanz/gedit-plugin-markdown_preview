
import importlib, shutil, os

def recognize_format(document):
	name = document.get_short_name_for_display()

	mime = None
	if document.get_language():
		mime = document.get_language().get_mime_types()[0]

	if mime and 'markdown' in mime:
		extension = 'md'
	elif mime and 'html' in mime:
		extension = 'html'
	elif document.is_untitled():
		extension = _("Unsaved document")
	elif '.' in name:
		extension = name.split('.')[-1].lower()
	else:
		extension = mime

	return name, extension

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

