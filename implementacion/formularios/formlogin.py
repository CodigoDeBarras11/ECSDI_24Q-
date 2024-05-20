from wtforms import Form, StringField, validators, IntegerField, PasswordField

class LoginForm(Form):
   name = StringField("Name")
   password = PasswordField('Password')