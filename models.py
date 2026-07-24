from application import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    
    cognito_sub = db.Column(db.String(255), unique=True, nullable=False)
    
    fname = db.Column(db.String(50), nullable=False)
    
    lname = db.Column(db.String(50), nullable=False)

    email = db.Column(db.String(120), unique=True, nullable=False)

class QuestionaireRating(db.Model):
    __tablename__ = 'questionaire_ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    age = db.Column(db.Integer, nullable=False)
    
    gender = db.Column(db.String(10), nullable=False)
    
    cleanliness = db.Column(db.Integer, nullable=False)
    
    noise = db.Column(db.Integer, nullable=False)
    
    smoker = db.Column(db.Boolean, nullable=False)
    
    night_owl = db.Column(db.Boolean, nullable=False)
    
    early_riser = db.Column(db.Boolean, nullable=False)
    
    bio = db.Column(db.Text, nullable=True)
    
    profile_pic = db.Column(db.String(500), nullable=True)  # Store the filename or path of the uploaded profile picture

class RoommateRating(db.Model):
    __tablename__ = 'roommate_ratings'

    id = db.Column(db.Integer, primary_key=True)

    rater_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    rated_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    cleanliness = db.Column(db.Integer, nullable=False)

    communication = db.Column(db.Integer, nullable=False)

    noise = db.Column(db.Integer, nullable=False)

    rater = db.relationship('User', foreign_keys=[rater_id])
    rated_user = db.relationship('User', foreign_keys=[rated_user_id])

class ProfileVote(db.Model):
    __tablename__ = 'profile_votes'

    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    profile_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    vote = db.Column(db.Boolean, nullable=False)  # True = agree, False = disagree

    __table_args__ = (
        db.UniqueConstraint('voter_id', 'profile_user_id', name='one_vote_per_voter_per_profile'),
    )