import os
from functools import wraps
from flask import Flask, flash, render_template, request, redirect, url_for, session
from authlib.integrations.flask_client import OAuth
from werkzeug.middleware.proxy_fix import ProxyFix  # <-- ADDED
from markupsafe import escape
from forms import QuestionaireForm, RoommateRatingForm
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(test_config=None):
    application = Flask(__name__)

    application.config['SERVER_NAME'] = 'roomiestatz.com'
    
    #Tell Flask it is behind a proxy (CloudFront) so url_for uses https:// ---
    application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)
    
    application.config['PREFERRED_URL_SCHEME'] = 'https'
    # Secret key for session management
    application.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

     # --- database config ---
    db_user = os.environ.get('DB_USER')
    db_password = os.environ.get('DB_PASSWORD')
    db_host = os.environ.get('DB_HOST')
    db_port = os.environ.get('DB_PORT', '3306')
    db_name = os.environ.get('DB_NAME')

    application.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(application) 

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

    @application.context_processor
    def inject_user():
        return dict(user=session.get('user'))
        
    @application.route("/debug-redirect")
    def debug_redirect():
        # This prints out exactly what Authlib/Flask are building
        generated_url = url_for('authorize', _external=True, _scheme='https')
        return {
            "What_Flask_Generates": generated_url,
            "Current_Request_Host_Header": request.headers.get('Host'),
            "Current_Request_Scheme": request.scheme
        }

    @application.route("/init-db")
    def init_db():
        from models import User, QuestionaireRating, RoommateRating
        db.create_all()
        return "Tables created!"

    # --- Authentication Routes ---
    @application.route("/login")
    def login():
        # Authlib uses url_for under the hood here. 
        # ProxyFix ensures this dynamic URL builds with 'https://' automatically.
        redirect_uri = url_for('authorize', _external=True, _scheme='https')
        return cognito.authorize_redirect(redirect_uri)

    @application.route("/authorize")
    def authorize():
        token = cognito.authorize_access_token()
        user_info = token.get('userinfo')

        if user_info:
            session['user'] = user_info

            # Find or create the User row tied to this Cognito account
            from models import User, QuestionaireRating

            user = User.query.filter_by(cognito_sub=user_info['sub']).first()

            if not user:
                user = User(
                    cognito_sub=user_info['sub'],
                    fname=user_info.get('given_name', ''),
                    lname=user_info.get('family_name', ''),
                    email=user_info.get('email', '')
                )
                db.session.add(user)
                db.session.commit()

            session['user_db_id'] = user.id  # store the local DB id for later lookups

            # Check if they've completed the questionnaire
            has_questionnaire = QuestionaireRating.query.filter_by(user_id=user.id).first()

            if not has_questionnaire:
                flash("Congrats you have an account now let's build your bio")
                return redirect(url_for('formpage'))

        return redirect(url_for('home'))

    @application.route("/logout")
    def logout():
        session.clear()
        
        # It should look something like: https://<your-domain-prefix>.auth.us-west-2.amazoncognito.com
        cognito_domain = "https://us-west-24lor5bvyc.auth.us-west-2.amazoncognito.com"
        
        client_id = "6luip31388jlngdepqlv2oq8h5"
        logout_redirect = url_for('home', _external=True, _scheme='https')
        print(f"DEBUG: logout_redirect = {logout_redirect}")
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
    def ratearoommate():
        form = RoommateRatingForm()
        return render_template('roommaterate.html', form=form, user=session.get('user'))
    @application.route("/bio")
    @login_required  
    def bio():
        return render_template('bio-page.html', user=session.get('user'))

    @application.route("/formpage")
    @login_required
    def formpage():
        form = QuestionaireForm()
        return render_template('questionaireformpage.html', form=form, user=session.get('user'))
    

    return application



application = create_app()

if __name__ == '__main__':
    application.run(debug=True)

