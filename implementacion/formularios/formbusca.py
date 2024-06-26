from wtforms import Form, SelectField, FloatField, validators

class SearchForm(Form):
    product_class = SelectField('Type of Product', choices=['Blender', 'Computer', 'Phone'])
    #StringField('Type of Product', validators= [validators.Optional(),validators.any_of("Blender", "Computer", "Phone")], default= "Blender")
    min_price = FloatField('Min Price', validators= [validators.Optional(), validators.number_range(min=0)], default= 0)
    max_price = FloatField('Max price', validators= [validators.Optional()])
    min_weight = FloatField('Min Weight', validators= [validators.Optional(), validators.number_range(min=0)], default= 0)
    max_weight = FloatField('Max Weight', validators= [validators.Optional()])