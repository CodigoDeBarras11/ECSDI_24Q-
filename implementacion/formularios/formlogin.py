from wtforms import Form, StringField, validators, PasswordField

class LoginForm(Form):
   name = StringField("Name", validators= [validators.DataRequired()])
   password = PasswordField('Password', validators= [validators.Optional()])