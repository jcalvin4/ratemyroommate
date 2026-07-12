from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, 
                     RadioField, BooleanField, DateField, 
                     PasswordField,SubmitField
                     )
from wtforms.validators import DataRequired
from flask_wtf.file import FileField, FileAllowed, FileRequired


class QuestionaireForm(FlaskForm):
    age = StringField('Age', validators=[DataRequired()])
    gender = SelectField('Gender', choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], default='other', validators=[DataRequired()])
    cleanliness = RadioField('Cleanliness', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], validators=[DataRequired()])
    noise = RadioField('Noise Level', choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')], validators=[DataRequired()])
    smoker = BooleanField('Smoker')
    night_owl = BooleanField('Night Owl')
    early_riser = BooleanField('Early Riser')
    bio = TextAreaField('Bio')
    profile_pic = FileField('Profile Picture', validators=[FileAllowed(['jpg', 'png'], 'Images only!')])
    submit = SubmitField('Submit')