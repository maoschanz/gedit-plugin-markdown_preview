
import subprocess, importlib

def get_backends_dict():
	available_backends = {}

	try:
		status = subprocess.call(['which', 'pandoc'])
		assert(status == 0)
		available_backends['pandoc'] = True
	except Exception:
		print("Package pandoc not installed")
		available_backends['pandoc']  = False

	available_backends['p3md'] = importlib.util.find_spec('markdown') is not None

	return available_backends


