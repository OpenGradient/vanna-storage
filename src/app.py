from flask import Flask, request, send_from_directory, Response
from api.routes import bp
import logging
from logging.config import dictConfig

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    dictConfig({
        'version': 1,
        'formatters': {'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }},
        'handlers': {'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }},
        'root': {
            'level': 'INFO',
            'handlers': ['wsgi']
        },
        'loggers': {
            'werkzeug': {
                'level': 'WARNING',  # Reduce logging for werkzeug (handles GET requests)
            },
            'core.ipfs_client': {
                'level': 'INFO',  # Set to DEBUG if you want to see all IPFS operations
            },
        }
    })
    
    app.register_blueprint(bp)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')