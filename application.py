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

    @application.route("/ratearoommate", methods=['GET', 'POST'])
    @login_required  
    def ratearoommate():
        form = RoommateRatingForm()
        if form.validate_on_submit():
            from models import RoommateRating
            rater_id = session.get('user_db_id')
            rated_user_id = int(form.rated_user_id.data)
            cleanliness = int(form.cleanliness.data)
            communication = int(form.communication.data)
            noise = int(form.noise.data)

            new_rating = RoommateRating(
                rater_id=rater_id,
                rated_user_id=rated_user_id,
                cleanliness=cleanliness,
                communication=communication,
                noise=noise
            )
            db.session.add(new_rating)
            db.session.commit()
            flash("Roommate rating submitted successfully!")
            return redirect(url_for('home'))
        return render_template('roommaterate.html', form=form, user=session.get('user'))
  
    @application.route("/bio")
    @login_required  
    def bio():
        from models import User, QuestionaireRating, RoommateRating
        db_user = User.query.filter_by(cognito_sub=session['user']['sub']).first()
        questionnaire = QuestionaireRating.query.filter_by(user_id=db_user.id).first()
        received_ratings = RoommateRating.query.filter_by(rated_user_id=db_user.id).all()

        all_scores = []

        for rating in received_ratings:
            all_scores.append(rating.cleanliness)
            all_scores.append(rating.communication)
            all_scores.append(6 - rating.noise)  # invert: quiet (low) becomes a high score

        if questionnaire:
            all_scores.append(questionnaire.cleanliness)
            all_scores.append(6 - questionnaire.noise)  # same inversion for self-assigned

        average_rating = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

        return render_template(
            'bio-page.html',
            user=session.get('user'),
            db_user=db_user,
            questionnaire=questionnaire,
            average_rating=average_rating
        )

    @application.route("/formpage", methods=['GET', 'POST'])
    @login_required
    def formpage():
        form = QuestionaireForm()
        if form.validate_on_submit():
            from models import QuestionaireRating
            user_id = session.get('user_db_id')
            age = int(form.age.data)
            gender = form.gender.data
            cleanliness = int(form.cleanliness.data)
            noise = int(form.noise.data)
            smoker = form.smoker.data
            night_owl = form.night_owl.data
            early_riser = form.early_riser.data
            bio = form.bio.data
            

            new_rating = QuestionaireRating(
                user_id=user_id,
                age=age,
                gender=gender,
                cleanliness=cleanliness,
                noise=noise,
                smoker=smoker,
                night_owl=night_owl,
                early_riser=early_riser,
                bio=bio
            )
            db.session.add(new_rating)
            db.session.commit()
            flash("Questionnaire submitted successfully!")
            return redirect(url_for('bio'))

        return render_template('questionaireformpage.html', form=form, user=session.get('user'))
    

    return application



application = create_app()

if __name__ == '__main__':
    application.run(debug=True)

