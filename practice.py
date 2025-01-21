from flask import Flask
from markupsafe import escape

app = Flask(__name__)
@app.route("/")
def index():
    return 'Index Page'
@app.route("/hello")
def hello_world():
    return "<p> Hello, World! <p>"