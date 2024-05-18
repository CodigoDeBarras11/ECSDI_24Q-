from formularios.formbusca import SearchForm
from formularios.formcompra import BuyForm
from flask import Flask, render_template, request, redirect, url_for
import requests
import socket
app = Flask(__name__)
@app.route('/compra', methods=['GET', 'POST'])
def compra():
    form = BuyForm(request.form)
    return render_template('compra.html', form = form)

@app.route('/busca', methods=['GET', 'POST'])
def busca():
    form = SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        hostname = socket.gethostname()
        address = 'http://{}:{}/comm'.format(hostname, 9010)
        productos = requests.get(address, params=form.data).json()
        return render_template('products.html', products = productos)
    return render_template('search.html', form=form)
    

@app.route('/')
def index():
    return render_template('index.html')

app.run()

