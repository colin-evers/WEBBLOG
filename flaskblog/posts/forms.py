from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired



class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Post')
    teaser_title = StringField('Teaser Title', validators=[DataRequired()])
    teaser_details = StringField('Teaser Details', validators=[DataRequired()])
    teaser_caption = TextAreaField('Teaser Caption', validators=[DataRequired()] )
    teaser_img = StringField('Teaser Image', validators=[DataRequired()] )
    teaser_content = TextAreaField('Teaser Content', validators=[DataRequired()] )
    teaser_wkid = StringField('Teaser Weekly Id', validators=[DataRequired()])
