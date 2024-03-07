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
            return [ "This url does not belong to the app."
                    f" Expected prefix {self.prefix!r}".encode()]


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
    return render_template('main.html', file_content=file_content)

def create_app():
    """
    Application factory.
    """
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_envvar('WEBCAT_INSTANCE_RELATIVE_CONFIG')

    prefix = app.config.get('PREFIX')
    if prefix:
        app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix)

    app.register_blueprint(catbp)
    return app
