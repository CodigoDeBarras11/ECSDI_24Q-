from os import getcwd, path
import sys
sys.path.append(path.dirname(getcwd()))
from formularios import formbusca, formcompra, formlogin, formproduct, shopform
from flask import Flask, render_template, request, redirect, url_for,Blueprint
import requests
import socket
from docs.ecsdi import ECSDI
from rdflib import Namespace, Graph, RDF, Literal, XSD
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import *
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
import argparse
from AgentUtil.Logging import config_logger

parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web", action='store_true',
                    default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dir', default=None, help="Direccion del servicio de directorio")


# parsing de los parametros de la linea de comandos
args = parser.parse_args()
if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

if args.dir is None:
    diraddress =  'http://'+hostname+':9000'
else:
    diraddress = args.dir

#if not args.verbose: logger = config_logger(1, 'busqueda')

agn = Namespace("http://www.agentes.org#")
AssistenteUsuario = Agent('AssistenteUsuario',
                       agn.AssistenteUsuario,
                       'http://%s:5000/comm' % hostname,
                       'http://%s:5000/Stop' % hostname)


app = Flask(__name__)
usuario = None
mss_cnt = 0
port = 5000
def createorUpdateproduct(product):
    product_graph = Graph()
    product_graph.parse("product.ttl", format="turtle")
    prod = product_graph.value(predicate=ECSDI.nombre, object= Literal(product['product_name']))
    if not prod:
        productid = int(product_graph.value(subject=agn.productid, predicate=XSD.positiveInteger))
        prod = ECSDI.Producto + '/' + str(productid)
        product_graph.add((prod, RDF.type, ECSDI.Producto))
        product_graph.add((prod, ECSDI.id, Literal(productid)))
        product_graph.add((prod, ECSDI.nombre, Literal(product['product_name'])))
        if product['product_type']:
            product_graph.add((prod, ECSDI.tipoproducto, Literal(product['product_type'])))
        if product['product_price']:
            product_graph.add((prod, ECSDI.precio, Literal(product['product_price'])))
        if  product['product_weight']:
            product_graph.add((prod, ECSDI.peso, Literal(product['product_weight'])))
        if  product['product_brand']:
            product_graph.add((prod, ECSDI.tieneMarca, Literal(product['product_brand'])))
        product_graph.add((prod, ECSDI.vendido_por, usuario))
        product_graph.set((agn.productid, XSD.positiveInteger, Literal(productid+1)))
    else:
        if product['product_type']:
            product_graph.set((prod, ECSDI.tipoproducto, Literal(product['product_type'])))
        if product['product_price']:
            product_graph.set((prod, ECSDI.precio, Literal(product['product_price'])))
        if  product['product_weight']:
            product_graph.set((prod, ECSDI.peso, Literal(product['product_weight'])))
        if  product['product_brand']:
            product_graph.set((prod, ECSDI.tieneMarca, Literal(product['product_brand'])))
    product_graph.serialize("product.ttl", format="turtle")

@app.route('/addProduct', methods=['GET', 'POST'])
def anadirProducto():
    if not usuario: return redirect(url_for('loginShop'))
    form = formproduct.ProductForm(request.form)
    print(form.data)
    if request.method == 'POST' and form.validate():
        createorUpdateproduct(form.data)
        return redirect(url_for('index'))
    return render_template('addProduct.html', form = form)
    
@app.route('/devolucion', methods=['GET', 'POST'])
def devolucion():
    if not usuario: return redirect(url_for('loginUser'))
    form = formproduct.ProductForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.data['product_name']
        product_graph = Graph()
        product_graph.parse("product.ttl", format="turtle")
        prod = product_graph.value(predicate=ECSDI.nombre, object=Literal(name))
        grafo_devolucion = Graph()
        peticiondevolucion =agn.peticiondevolucion
        grafo_devolucion.add((peticiondevolucion, RDF.type, ECSDI.PeticionDevolucion))
        grafo_devolucion.add((prod, RDF.type, ECSDI.Producto))
        grafo_devolucion.add((peticiondevolucion, ECSDI.comprado_por, usuario))
        msg = build_message(product_graph, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.Agentedevolucion, content=peticiondevolucion, msgcnt=mss_cnt)
        devoladr = requests.get(diraddress + '/message', params={'message': 'SEARCH|DEVOLUCION'}).text
        if 'OK' in devoladr:
            devol = devoladr[4:]
            response = send_message(msg, devol + '/comm')
            return redirect(url_for('index'))
    return render_template('devolucion.html', form = form)

@app.route('/compra', methods=['GET', 'POST'])
def compra():
    if not usuario: return redirect(url_for('loginUser'))
    form = request.form
    products = None
    if request.method == 'POST':
        products = form.getlist('products')
        product_graph = Graph()
        n = len(products)
        for i in range(n):
            products[i] = products[i].split(sep=',')
            if(len(products[i]) > 5): 
                vendedor = products[i][5]
            else: vendedor = ECSDI.Tienda + '/0'
            products[i] = {"name": str(products[i][0]), "price": float(products[i][1]),"weight": float(products[i][2]),"brand": str(products[i][3]), "id": products[i][4]}
            prod = ECSDI.Producto + '/' + str(products[i]['id'])
            product_graph.add((prod, RDF.type, ECSDI.Producto))
            if products[i]['name']:
                product_graph.add((prod, ECSDI.nombre, Literal(products[i]['name'])))
            if products[i]['id']:
                product_graph.add((prod, ECSDI.id, Literal(products[i]['id'])))
            else: 
                products[i]['id'] = 0
                product_graph.add((prod, ECSDI.id, Literal(0)))
            if products[i]['price']:
                product_graph.add((prod, ECSDI.precio, Literal(products[i]['price'])))
            if  products[i]['weight']:
                product_graph.add((prod, ECSDI.peso, Literal(products[i]['weight'])))
            if  products[i]['brand']:
                product_graph.add((prod, ECSDI.tieneMarca, Literal(products[i]['brand'])))
            product_graph.add((prod, ECSDI.vendido_por, vendedor))
        #return products
        peticionCompra = agn.peticionCompra
        product_graph.add((peticionCompra, RDF.type, ECSDI.PeticionCompra))
        product_graph.add((peticionCompra, ECSDI.comprado_por, usuario))
        msg = build_message(product_graph, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.AgenteCompra, content=peticionCompra, msgcnt=mss_cnt)
        compraadd = requests.get(diraddress + '/message', params={'message': 'SEARCH|COMPRA'}).text
        if 'OK' in compraadd:
            compra = compraadd[4:]
            response = send_message(msg, compra + '/comm')
            return render_template(url_for("envio"))
    return render_template('products.html', products=products)


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion del agente
    Simplemente retorna un objeto fijo que representa una
    respuesta a una busqueda de hotel

    Asumimos que se reciben siempre acciones que se refieren a lo que puede hacer
    el agente (buscar con ciertas restricciones, reservar)
    Las acciones se mandan siempre con un Request
    Prodriamos resolver las busquedas usando una performativa de Query-ref
    """
    global dsgraph
    global mss_cnt
    # Extraemos el mensaje y creamos un grafo con el
    grafo = Graph()
    grafo = grafo.parse(data=request.args.get('content'), format='xml')
    msgdic = get_message_properties(grafo)
    #print(msgdic)
    # Comprobamos que sea un mensaje FIPA ACL
    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(
            Graph(), ACL['not-understood'], sender=AssistenteUsuario.uri, msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        perf = msgdic['performative']

        if perf != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(
                Graph(), ACL['not-understood'], sender=AssistenteUsuario.uri, msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro

            # Averiguamos el tipo de la accion
            if 'content' in msgdic:
                content = msgdic['content']
                accion = grafo.value(subject=content, predicate=RDF.type)
                if accion == ECSDI.PeticionBusqueda:
                   gr = build_message(Graph(),
                        ACL['inform'],
                        sender=AssistenteUsuario.uri,
                        msgcnt=mss_cnt,
                        receiver=msgdic['sender'])
                else: gr = build_message(Graph(), ACL['not-understood'], sender=AssistenteUsuario.uri, msgcnt=mss_cnt)
            else: gr = build_message(Graph(), ACL['not-understood'], sender=AssistenteUsuario.uri, msgcnt=mss_cnt)

    # Aqui realizariamos lo que pide la accion
    # Por ahora simplemente retornamos un Inform-done
    
    mss_cnt += 1

    #logger.info('Respondemos a la peticion')

    return gr.serialize(format='xml')

@app.route('/envio', methods=['GET', 'POST'])
def envio():
    form = formcompra.BuyForm(request.form)
    if request.method == 'POST' and form.validate():
        infoentrega = agn.infoentrega
        grafo_entrega = Graph()
        grafo_entrega.add((infoentrega, RDF.type, ECSDI.InfoUsuarioEntrega))
        grafo_entrega.add((infoentrega, ECSDI.latitud, Literal(form.data.get('shiping_latitude'))))
        grafo_entrega.add((infoentrega, ECSDI.longitud, Literal(form.data.get('shiping_longitude'))))
        grafo_entrega.add((infoentrega, ECSDI.metodoPago, Literal(form.data.get('payment_method'))))
        grafo_entrega.add((infoentrega, ECSDI.prioridadEntrega, Literal(form.data.get('shiping_priority'))))
        msg = build_message(grafo_entrega, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.AgenteCompra, content=infoentrega, msgcnt=mss_cnt)
        compraadd = requests.get(diraddress + '/message', params={'message': 'SEARCH|COMPRA'}).text
        if 'OK' in compraadd:
            compra = compraadd[4:]
            response = send_message(msg, compra + '/comm')
            response
            render_template('InfoEntrega.html', form = form)

        #productos = requests.get(AgenteCompra.address, params=form.data).json()
    return render_template('envio.html', form = form)

@app.route('/busca', methods=['GET', 'POST'])
def busca():
    if not usuario: return redirect(url_for('loginUser'))
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
        peticionbusquda =  agn.peticionbusqueda
        gm.add((peticionbusquda, RDF.type, ECSDI.PeticionBusqueda))
        gm.add((peticionbusquda, ECSDI.tipoproducto, Literal(product_type)))
        gm.add((peticionbusquda, ECSDI.max_precio, Literal(max_price)))
        gm.add((peticionbusquda, ECSDI.min_precio, Literal(min_price)))
        gm.add((peticionbusquda, ECSDI.max_peso, Literal(max_weight)))
        gm.add((peticionbusquda, ECSDI.min_peso, Literal(min_weight)))
        gm.add((peticionbusquda, ECSDI.buscado_por, usuario))
        msg = build_message(gm, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.AgenteBusqueda, content=peticionbusquda, msgcnt=mss_cnt)
        searchadd = requests.get(diraddress + '/message', params={'message': 'SEARCH|BUSCA'}).text
        if 'OK' in searchadd:
            busqueda = searchadd[4:]
            productos = send_message(msg,busqueda + '/comm')
            products = []
            #print(len(productos.subjects(predicate=RDF.type, object=ECSDI.Producto)))
            for prod in productos.subjects(predicate=RDF.type, object=ECSDI.Producto):
                product = {
                    "id": str(productos.value(subject=prod, predicate=ECSDI.id)),
                    "name": str(productos.value(subject=prod, predicate=ECSDI.nombre)),
                    "price": str(productos.value(subject=prod, predicate=ECSDI.precio)),
                    "weight": productos.value(subject=prod, predicate=ECSDI.peso).split(',')[0][1:],
                    "brand": str(productos.value(subject=prod, predicate=ECSDI.tieneMarca)),
                    "vendedor": productos.value(subject=prod, predicate=ECSDI.vendido_por)
                }
                product['data'] =  product['name'] + ','+ str(product['price'])+ ',' + str(product['weight']) + ','+product['brand'] + ','+ product['id'] 
                if(product['vendedor']): product['data'] +=',' + product['vendedor']
                products.append(product)
            return render_template('products.html', products=products)
    return render_template('search.html', form=form)

@app.route('/userOptions')
def userIndex():
    return render_template('user.html')

@app.route('/')
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
        us = ECSDI.Cliente + '/'+str(userid)
        users_graph.add((us, RDF.type, ECSDI.Cliente))
        users_graph.add((us, ECSDI.id, Literal(userid)))
        users_graph.add((us, ECSDI.nombre, Literal(username)))
        users_graph.set((agn.userid, XSD.positiveInteger,Literal(userid+1)))
    users_graph.serialize("usuarios.ttl", format="turtle")
    return us

def getshopref(shopname:str, delegado:bool = True):
    shop_graph = Graph()
    shop = None
    if path.exists("tienda.ttl"):
        shop_graph.parse("tienda.ttl", format="turtle")
        shop = shop_graph.value(predicate=ECSDI.nombre, object= Literal(shopname))
    else:
        shop_graph.bind('ECSDI', ECSDI)
        shop_graph.add((agn.shopid, XSD.positiveInteger, Literal(0)))
    if not shop:
        shopid = shop_graph.value(subject=agn.shopid, predicate=XSD.positiveInteger)
        shop = ECSDI.Tienda + '/'+str(shopid)
        shop_graph.add((shop, RDF.type, ECSDI.Tienda))
        shop_graph.add((shop, ECSDI.id, Literal(shopid)))
        shop_graph.add((shop, ECSDI.entrega_delegada, Literal(delegado)))
        shop_graph.add((shop, ECSDI.nombre, Literal(shopname)))
        shop_graph.set((agn.shopid, XSD.positiveInteger,Literal(shopid+1)))
    shop_graph.serialize("tienda.ttl", format="turtle")
    return shop

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

@app.route('/userlogin', methods=['GET', 'POST'])
def loginUser():
    form = formlogin.LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.data.get('name')
        global usuario
        usuario = getuserref(name)
        print(usuario)
        return redirect(url_for('userIndex'))
    return render_template('login.html', form = form)

@app.route('/shoplogin', methods=['GET', 'POST'])
def loginShop():
    form = shopform.ShopForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.data.get('shop_name')
        delegado = form.data.get('entrega_delegada')
        global usuario
        usuario = getshopref(name, delegado)
        print(usuario)
        return redirect(url_for('anadirProducto'))
    return render_template('shoplogin.html', form = form)

solveradd = f'http://{hostaddr}:{port}'
solverid = hostaddr.split('.')[0] + '-' + str(port)
mess = f'REGISTER|{solverid},ASSISTANT,{solveradd}'

done = False
while not done:
    try:
        resp = requests.get(str(diraddress) + '/message', params={'message': mess}).text
        done = True
    except ConnectionError:
        pass
#print('DS Hostname =', hostaddr)

if 'OK' in resp:
    #print('adress:'+solveradd)
    print(f'ASSISTANT {solverid} successfully registered')
    # Buscamos el logger si existe en el registro
    '''loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
    if 'OK' in loggeradd:
        logger = loggeradd[4:]'''

    # Ponemos en marcha el servidor Flask
    app.run(host=hostname, port=port, debug=False, use_reloader=False)

    mess = f'UNREGISTER|{solverid}'
    requests.get(diraddress + '/message', params={'message': mess})
else:
    print('Unable to register')

