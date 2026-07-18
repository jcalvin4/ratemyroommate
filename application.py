import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix  # <-- ADDED
from markupsafe import escape
from forms import QuestionaireForm

def create_app(test_config=None):
    application = Flask(__name__)
    
    # --- ADDED: Tell Flask it is behind a proxy (CloudFront) so url_for uses https:// ---
    application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)
    
    # Secret key for session management
    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

    # --- Initialize Cognito OAuth ---
    oauth = OAuth(application)
    cognito = oauth.register(
        name='oidc',
        authority='https://cognito-idp.us-west-2.amazonaws.com/us-west-2_4lor5BvYC',
        client_id='6luip31388jlngdepqlv2oq8h5',
        client_secret=os.environ.get('COGNITO_CLIENT_SECRET'), 
        server_metadata_url='https://cognito-idp.us-west-2.amazonaws.com/us-west-2_4lor5BvYC/.well-known/openid-configuration',
        client_kwargs={'scope': 'phone openid email'}
    )

    # --- Auth Decorator for Protected Routes ---
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    # --- Authentication Routes ---
    @application.route("/login")
    def login():
        # Authlib uses url_for under the hood here. 
        # ProxyFix ensures this dynamic URL builds with 'https://' automatically.
        redirect_uri = url_for('authorize', _external=True)
        return cognito.authorize_redirect(redirect_uri)

    @application.route("/authorize")
    def authorize():
        token = cognito.authorize_access_token()
        user_info = token.get('userinfo')
        if user_info:
            session['user'] = user_info
        return redirect(url_for('home'))

    @application.route("/logout")
    def logout():
        session.clear()
        
        # --- FIXED: Use your actual Cognito domain prefix here ---
        # It should look something like: https://<your-domain-prefix>.auth.us-west-2.amazoncognito.com
        cognito_domain = "https://us-west-24lor5bvyc.auth.us-west-2.amazoncognito.com"
        
        client_id = "6luip31388jlngdepqlv2oq8h5"
        logout_redirect = url_for('home', _external=True)
        return redirect(f"{cognito_domain}/logout?client_id={client_id}&logout_uri={logout_redirect}")

    # --- Standard App Routes ---
    @application.route("/")
    def home():
        user = session.get('user')
        return render_template('home.html', user=user)

    @application.route("/about")
    def aboutpage():
        return render_template('about.html')

    @application.route("/ratearoommate")
    @login_required  
    def formpage():
        form = QuestionaireForm()
        return render_template('bio-page.html', form=form, user=session.get('user'))

    return application

application = create_app()

if __name__ == '__main__':
    application.run(debug=True)

