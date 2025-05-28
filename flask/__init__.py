import json
from types import SimpleNamespace

class Request(SimpleNamespace):
    def get_json(self):
        return getattr(self, '_json', None)

request = Request(args={}, form={})

session = {}

class DummyResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status
        self.headers = {}

    def get_json(self):
        if isinstance(self.data, (str, bytes)):
            return json.loads(self.data)
        return self.data

def jsonify(obj):
    return obj

def make_response(data, status):
    return DummyResponse(data, status)

def redirect(url):
    return DummyResponse('', 302)

def url_for(endpoint):
    return f'/{endpoint}'

def render_template(template, **context):
    return ''

class Blueprint:
    def __init__(self, name, import_name):
        self.name = name
        self.routes = []

    def route(self, rule, methods=['GET']):
        def decorator(func):
            self.routes.append((rule, methods, func))
            return func
        return decorator

    def register(self, app):
        for rule, methods, func in self.routes:
            app._add_route(rule, methods, func)

class Flask:
    def __init__(self, name):
        self.name = name
        self.routes = {}
        self.config = {}

    def route(self, rule, methods=['GET']):
        def decorator(func):
            self._add_route(rule, methods, func)
            return func
        return decorator

    def _add_route(self, rule, methods, func):
        for method in methods:
            self.routes[(rule, method)] = func

    def register_blueprint(self, bp):
        bp.register(self)

    def test_client(self):
        app = self
        class Client:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                pass
            def get(self, path, query_string=None):
                request.args = query_string or {}
                request.form = {}
                request._json = None
                func = app.routes.get((path, 'GET'))
                result = func()
                if isinstance(result, DummyResponse):
                    return result
                if isinstance(result, tuple):
                    data, status = result
                else:
                    data, status = result, 200
                return DummyResponse(data, status)
            def post(self, path, json=None, data=None):
                request.args = {}
                request.form = data or {}
                request._json = json
                func = app.routes.get((path, 'POST'))
                result = func()
                if isinstance(result, DummyResponse):
                    return result
                if isinstance(result, tuple):
                    data, status = result
                else:
                    data, status = result, 200
                return DummyResponse(data, status)
        return Client()
