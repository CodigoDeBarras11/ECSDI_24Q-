from wtforms import Form, FloatField, validators, StringField, SelectField

class ProductForm(Form):
    product_name = StringField("Name", validators= [validators.DataRequired()])
    product_type =  SelectField('Type of Product', choices=['Blender', 'Computer', 'Phone'])
    product_price = FloatField('Price')
    product_weight = FloatField('Weight')
    product_brand= StringField("Brand")