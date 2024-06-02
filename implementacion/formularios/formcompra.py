from wtforms import Form, StringField, validators, IntegerField, SelectField, FloatField, HiddenField

class BuyForm(Form):
    shiping_latitude = FloatField('Shipping Adress latitude',[validators.DataRequired()])
    shiping_longitude = FloatField('Shipping Adress latitude',[validators.DataRequired()])
    payment_method = SelectField('Payment Method', choices=['Credit Card', 'Debit Card', 'Bank Transfer', 'PayPal'])
    #payment_account= StringField('Payment acount')
    shiping_priority = IntegerField('Shipping Priority(in days)',[validators.number_range(min= 1)])
    envios = HiddenField()