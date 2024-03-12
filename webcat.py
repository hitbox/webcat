import sqlalchemy as sa

from flask import Blueprint
from flask import Flask
from flask import current_app
from flask import render_template
from flask import send_file

catbp = Blueprint('cat', __name__)

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


def database_result(engine, querydata):
    """
    Run query with engine and capture its result along with other configured
    values intended for the templates.
    """
    with engine.connect() as conn:
        result = conn.execute(querydata['query'])
        result_data = dict(
            title = querydata['title'],
            id = querydata['id'],
            result = dict(
                fieldnames = result.keys(),
                rows = result.all(),
            ),
        )
        return result_data

def database_data_from_config():
    """
    Package the results of configured queries into a list of dicts intended for
    the templates.
    """
    servers = current_app.config['WEBCAT_SERVERS']
    queries = current_app.config['WEBCAT_SHOW_QUERIES']

    results = []
    for querydata in queries:
        url = servers[querydata['server']]
        engine = sa.create_engine(url)
        results.append(database_result(engine, querydata))
    return results

@catbp.route('/favicon')
def favicon():
    """
    Instance specific favicon from config.
    """
    # NOTE
    # - trying to keep anything instance specific out of repo
    return send_file(current_app.config['WEBCAT_FAVICON'])

@catbp.route('/')
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
    return render_template('main.html', **context)

def create_app():
    """
    Application factory.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Configuration from file pointed at by environment variable.
    # The path is relative to this project's directory.
    app.config.from_envvar('WEBCAT_INSTANCE_RELATIVE_CONFIG')

    prefix = app.config.get('PREFIX')
    if prefix:
        app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix)

    app.register_blueprint(catbp)
    return app
