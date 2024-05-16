from formularios.formbusca import SearchForm
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
@app.route('/busca')
def busca():
    form = SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        return render_template('products.html')
    return render_template('search.html', form=form)
    

@app.route('/')
def index():
    return render_template('index.html')

app.run()

