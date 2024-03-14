import random
import time

from flask import Blueprint
from flask import Flask
from flask import current_app
from flask import request
from flask import send_file
from flask import stream_template
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

cat_bp = Blueprint('cat', __name__)

class PrefixMiddleware:
    """
    Require a prefix for all url paths.
    """

    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        """
        Raise error if url is not properly prefixed. Otherwise, strip prefix
        and ship off to application's path.
        """
        path_info = environ.get('PATH_INFO', '')
        if path_info.lower().startswith(self.prefix.lower()):
            # strip the prefix off the url path
            environ['PATH_INFO'] = path_info[len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            response = (
                "This url does not belong to the app."
                f" Expected prefix {self.prefix!r}".encode()
            )
            return [response]


class FlaskSQLAlchemy:
    """
    Simple Flask extension with SQLAlchemy.
    """

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.binds = app.config.get('WEBCAT_BINDS', {})
        for bindname, engine_options in self.binds.items():
            self.binds[bindname] = create_engine(**engine_options)

        self.session_makers = {
            name: sessionmaker(engine) for name, engine in self.binds.items()
        }
        self.scoped_sessions = {
            name: scoped_session(session_maker)
            for name, session_maker in self.session_makers.items()
        }

        app.teardown_appcontext(self._teardown_session)

    def _teardown_session(self, exception):
        for scoped_session in self.scoped_sessions.values():
            scoped_session.remove()


db = FlaskSQLAlchemy()

def database_data_from_config():
    binds = current_app.config['WEBCAT_BINDS']
    queries = current_app.config['WEBCAT_SHOW_QUERIES']

    for querydata in queries:
        bindname = querydata['bind']
        query = querydata['query']
        bind = db.binds[bindname]
        session = db.scoped_sessions[bindname]
        result = session.execute(query)
        yield result

@cat_bp.route('/favicon')
def favicon():
    """
    Instance specific favicon from config.
    """
    # NOTE
    # - trying to keep anything instance specific out of repo
    return send_file(current_app.config['WEBCAT_FAVICON'])

def slow_rows(delayfunc, nrows, nfields, prefix=''):
    """
    Generate fake rows with a delay.
    """
    for row_num in range(nrows):
        yield tuple(prefix + f'value-{valn}-{row_num}' for valn in range(nfields))
        time.sleep(delayfunc())

def slow_database_results():
    """
    Fake slow database connection.
    """
    for querydata in current_app.config['WEBCAT_SHOW_QUERIES']:
        id = querydata['id']
        nfields = querydata['_nfields']
        nrows = querydata['_nrows']

        if '_delay' in querydata and '_random_delay' in querydata:
            raise ValueError('incompatible keys')
        elif '_delay' in querydata:
            delay = querydata['_delay']
            delayfunc = lambda: delay
        elif '_random_delay' in querydata:
            a, b = querydata['_random_delay']
            def delayfunc():
                return random.uniform(a, b)
        else:
            delayfunc = lambda: 0

        yield dict(
            title = querydata['title'],
            id = id,
            result = dict(
                fieldnames = [f'{id}-field-{fieldn}' for fieldn in range(nfields)],
                rows = slow_rows(delayfunc, nrows, nfields, prefix=f'{id}-'),
            ),
        )

@cat_bp.route('/')
def output():
    """
    Read file and render html.
    """
    with open(current_app.config['WEBCAT_FILE']) as webcat_file:
        file_content = webcat_file.read()

    database_results = database_data_from_config()
    context = dict(
        file_content = file_content,
        database_results = database_results,
    )
    return stream_template('main.html', **context)

def create_app():
    """
    Application factory.
    """
    app = Flask(__name__, instance_relative_config=True)

    app.jinja_env.globals.update(zip=zip)

    # Configuration from file pointed at by environment variable.
    # The path is relative to this project's directory.
    app.config.from_envvar('WEBCAT_INSTANCE_RELATIVE_CONFIG')

    prefix = app.config.get('PREFIX')
    if prefix:
        app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix)

    app.register_blueprint(cat_bp)

    db.init_app(app)

    return app
