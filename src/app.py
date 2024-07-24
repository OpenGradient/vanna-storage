from flask import Flask, request, send_from_directory, Response
import logging
from api.routes import bp

app = Flask(__name__)
app.register_blueprint(bp)

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='app.log',
        filemode='w')

    app.run(debug=True, host='0.0.0.0')