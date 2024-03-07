from flask import Blueprint
from flask import Flask
from flask import current_app
from flask import render_template
from flask import send_file

catbp = Blueprint('cat', __name__)

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
    app.register_blueprint(catbp)
    return app
