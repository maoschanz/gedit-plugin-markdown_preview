
import importlib, shutil, os

def get_backends_dict():
	return {
		'pandoc': shutil.which('pandoc') is not None,
		'p3md': importlib.util.find_spec('markdown') is not None
	}

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

