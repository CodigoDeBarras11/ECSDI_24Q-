from wtforms import Form, StringField, validators, IntegerField, SelectField

class BuyForm(Form):
    shiping_adress = StringField('Shipping Adress',[validators.length(min=5, max=95)])
    payment_method = SelectField('Payment Method', choices=['Credit Card', 'Debit Card', 'Bank Transfer', 'PayPal'])
    payment_account= StringField('Payment acount')
    shiping_priority = IntegerField('Shipping Priority(in days)',[validators.number_range(min= 1)])