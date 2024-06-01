from wtforms import Form, StringField, validators, IntegerField, SelectField, FloatField

class BuyForm(Form):
    shiping_latitude = FloatField('Shipping Adress latitude',[validators.data_required])
    shiping_longitude = FloatField('Shipping Adress latitude',[validators.data_required])
    payment_method = SelectField('Payment Method', choices=['Credit Card', 'Debit Card', 'Bank Transfer', 'PayPal'])
    #payment_account= StringField('Payment acount')
    shiping_priority = IntegerField('Shipping Priority(in days)',[validators.number_range(min= 1)])