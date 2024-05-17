from wtforms import Form, StringField, validators, IntegerField

class BuyForm(Form):
    shiping_adress = StringField('Shipping Adress',validators=[validators.length(min=5, max=95)])
    payment_method = StringField('Payment Method',validators=[validators.data_required], default= "Credit Card")
    shiping_priority = IntegerField('Shipping Priority(in days)',validators=[validators.data_required, validators.number_range(min= 1)])