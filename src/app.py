from flask import Flask, request, send_from_directory, Response
from api.routes import bp
import logging

app = Flask(__name__)
app.register_blueprint(bp)

def create_app():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='app.log',
        filemode='w')

    app.run(debug=True, host='0.0.0.0')