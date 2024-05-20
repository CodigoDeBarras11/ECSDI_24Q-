from os import getcwd, path
import sys
sys.path.append(path.dirname(getcwd()))
from formularios import formbusca, formcompra, formlogin
from flask import Flask, render_template, request, redirect, url_for,Blueprint
import requests
import socket
from docs.ecsdi import ECSDI
from rdflib import Namespace, Graph, RDF, Literal, XSD
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import *
from AgentUtil.Agent import Agent
hostname = socket.gethostname()
agn = Namespace("http://www.agentes.org#")
users = ECSDI.Cliente
AgenteBusqueda = Agent('AgenteBusqueda',
                       agn.AgenteBusqueda,
                       'http://%s:9010/comm' % hostname,
                       'http://%s:9010/Stop' % hostname)

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)


app = Flask(__name__)
usuario = None
mss_cnt = 0
@app.route('/compra', methods=['GET', 'POST'])
def compra():
    form = formcompra.BuyForm(request.form)
    if request.method == 'POST' and form.validate():
        hostname = socket.gethostname()
        address = 'http://{}:{}/comm'.format(hostname, 9010)
        productos = requests.get(address, params=form.data).json()
    return render_template('compra.html', form = form)

@app.route('/busca', methods=['GET', 'POST'])
def busca():
    if not usuario: redirect(url_for(login))
    form = formbusca.SearchForm(request.form)
    if request.method == 'POST' and form.validate():
        product_type = form.data.get('product_class')
        min_price = form.data.get('min_price')
        if(min_price): min_price = float(min_price)
        max_price = form.data.get('max_price')
        if(max_price): max_price = float(max_price)
        min_weight = form.data.get('min_weight')
        if(min_weight): min_weight = float(min_weight)
        max_weight = form.data.get('max_weight')
        if(max_weight): max_weight = float(max_weight)
        gm = Graph()
        gm.bind('ECSDI', ECSDI)
        print(form.data)
        peticionbusquda =  agn.peticionbusqueda
        gm.add((peticionbusquda, RDF.type, ECSDI.PeticionBusqueda))
        gm.add((peticionbusquda, ECSDI.tipoproducto, Literal(product_type)))
        gm.add((peticionbusquda, ECSDI.max_precio, Literal(max_price)))
        gm.add((peticionbusquda, ECSDI.min_precio, Literal(min_price)))
        gm.add((peticionbusquda, ECSDI.max_peso, Literal(max_weight)))
        gm.add((peticionbusquda, ECSDI.min_peso, Literal(min_weight)))
        gm.add((peticionbusquda, ECSDI.buscado_por, usuario))
        msg = build_message(gm, ACL.request, sender=agn.AsistenteUsuario, receiver=AgenteBusqueda.uri, content=peticionbusquda, msgcnt=mss_cnt)
        productos = send_message(msg,AgenteBusqueda.address, False) 
        #requests.get(address, params=form.data).json()
        return render_template('products.html', products=productos.json())
    return render_template('search.html', form=form)
    

@app.route('/options')
def index():
    return render_template('index.html')

def getuserref(username:str):
    users_graph = Graph()
    us = None
    if path.exists("usuarios.ttl"):
        users_graph.parse("usuarios.ttl", format="turtle")
        us = users_graph.value(predicate=ECSDI.nombre, object= Literal(username))
    else:
        users_graph.bind('ECSDI', ECSDI)
        users_graph.add((agn.userid, XSD.positiveInteger, Literal(0)))
    if not us:
        userid = users_graph.value(subject=agn.userid, predicate=XSD.positiveInteger)
        us = users + '/'+str(userid)
        users_graph.add((us, RDF.type, ECSDI.Cliente))
        users_graph.add((us, ECSDI.id, Literal(userid)))
        users_graph.add((us, ECSDI.nombre, Literal(username)))
        users_graph.set((agn.userid, XSD.positiveInteger,Literal(userid+1)))
    users_graph.serialize("usuarios.ttl", format="turtle")
    return us

def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass

@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"

@app.route('/', methods=['GET', 'POST'])
def login():
    form = formlogin.LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.data.get('name')
        global usuario
        usuario = getuserref(name)
        print(usuario)
        return redirect(url_for('index'))
    return render_template('login.html', form = form)

app.run()

