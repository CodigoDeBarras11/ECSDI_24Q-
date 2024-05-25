from wtforms import Form, StringField, validators, BooleanField

class ShopForm(Form):
   shop_name = StringField("Name", validators= [validators.DataRequired()])
   entrega_delegada = BooleanField("Quieres que nuestra tienda haga la entrega?", validators= [validators.InputRequired()])
   #password = PasswordField('Password', validators= validators.optional)