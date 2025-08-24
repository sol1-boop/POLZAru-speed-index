import sys
from importlib import import_module

sys.modules['flask'] = import_module('tests.flask_stub')
