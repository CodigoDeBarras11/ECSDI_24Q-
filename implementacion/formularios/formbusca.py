from wtforms import Form, BooleanField, StringField, FloatField, validators

class SearchForm(Form):
    product_class = StringField('Type of Product', validators= [validators.Optional(),validators.any_of("Blender", "Computer", "Phone")])
    min_price = FloatField('Min Price', validators= [validators.Optional(), validators.number_range(min=0)], default= 0)
    max_price = FloatField('Max price', validators= [validators.Optional(), validators.number_range(min=min_price)])
    min_weight = FloatField('Min Weight', validators= [validators.Optional(), validators.number_range(min=0)], default= 0)
    max_weight = FloatField('Max Weight', validators= [validators.Optional(), validators.number_range(min=min_weight)])