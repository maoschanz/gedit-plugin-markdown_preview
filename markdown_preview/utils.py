
import importlib, shutil

def get_backends_dict():
	return {
		'pandoc': shutil.which('pandoc') is not None,
		'p3md': importlib.util.find_spec('markdown') is not None
	}

