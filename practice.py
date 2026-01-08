import os
from flask import Flask, render_template, request, redirect
from db import db
from markupsafe import escape



def create_app(test_config=None):
    app = Flask(__name__)
    

    @app.route("/")
    def home():
        return render_template('home.html')

    @app.route("/about")
    def aboutpage():
        return render_template('about.html')

    @app.route("/ratearoommate")

    def formpage():
        return render_template('ratearoommatepage.html')
    
    return app
app = create_app()

app.run(debug=True)


