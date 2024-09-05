from flask import Flask
from api.routes import bp
import logging

def create_app():
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='app.log',
        filemode='w'
    )
    
    app.register_blueprint(bp)
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')