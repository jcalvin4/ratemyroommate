import os
from flask import Flask, render_template, request, redirect
from markupsafe import escape
from forms import QuestionaireForm



def create_app(test_config=None):
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = 'temporary_secret_key_for_development'

    @app.route("/")
    def home():
        return render_template('home.html')

    @app.route("/about")
    def aboutpage():
        return render_template('about.html')

    @app.route("/ratearoommate")

    def formpage():
        form = QuestionaireForm()
        return render_template('bio-page.html', form=form)
    
    return app
app = create_app()

app.run(debug=True)


