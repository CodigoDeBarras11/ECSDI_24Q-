from os import getcwd, path
import sys
sys.path.append(path.dirname(getcwd()))
from formularios import formbusca, formcompra, formlogin, formproduct, shopform
from flask import Flask, render_template, render_template_string, request, redirect, url_for
import requests
import socket
from docs.ecsdi import ECSDI
from rdflib import Namespace, Graph, RDF, Literal, XSD
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.ACLMessages import *
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
import argparse
from datetime import datetime

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
    print(request.form)
    if request.method == 'POST' and form.validate():
        createorUpdateproduct(form.data)
        return redirect(url_for('index'), mensaje = "Producto registrado")
    return render_template('addProduct.html', form = form)
    
@app.route('/devolucion', methods=['GET', 'POST'])
def devolucion():
    if not usuario: return redirect(url_for('loginUser'))
    form = formproduct.ProductForm(request.form)
    name = form.data.get('product_name')
    if request.method == 'POST' and name:
        print('hola')
        product_graph = Graph()
        product_graph.parse("product.ttl", format="turtle")
        prod = product_graph.value(predicate=ECSDI.nombre, object=Literal(name))
        grafo_devolucion = Graph()
        peticiondevolucion =agn.peticiondevolucion
        grafo_devolucion.add((peticiondevolucion, RDF.type, ECSDI.PeticionDevolucion))
        grafo_devolucion.add((prod, RDF.type, ECSDI.Producto))
        grafo_devolucion.add((peticiondevolucion, ECSDI.productos, prod))
        grafo_devolucion.add((peticiondevolucion, ECSDI.comprado_por, usuario))
        msg = build_message(grafo_devolucion, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.Agentedevolucion, content=peticiondevolucion, msgcnt=mss_cnt)
        devoladr = requests.get(diraddress + '/message', params={'message': 'SEARCH|DEVOLUCION'}).text
        if 'OK' in devoladr:
            devol = devoladr[4:]
            response = send_message(msg, devol + '/comm')
            content = get_message_properties(response)['content']
            accion = response.value(subject=content, predicate=RDF.type)
            acepted = response.value(subject=content, predicate=ECSDI.acceptado)
            veredicto = "Tu entrega ha sido "
            if(acepted):
                veredicto += "aceptada"
                mensaje_devolucion = response.value(subject=content, predicate=ECSDI.Mensajes)
                return render_template('InfoEntrega.html', titulo = "Resultado devolucion", info1 = veredicto, info2 = mensaje_devolucion)
            else: 
                veredicto += "denegada"
                return render_template('InfoEntrega.html', titulo = "Resultado devolucion", info1 = veredicto)
        
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
            if products[i]['id'] != 'None':
                product_graph.add((prod, ECSDI.id, Literal(products[i]['id'])))
            else: 
                products[i]['id'] = Literal(0)
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
            content = get_message_properties(response)['content']
            accion = response.value(subject=content, predicate=RDF.type)
            araycompras = []
            for rescompra in response.subjects(predicate=RDF.type, object=ECSDI.Compra): araycompras.append(rescompra)
            return render_template("envio.html",  form = formcompra.BuyForm(envios = araycompras))
    return render_template('products.html', products=products)

def cahear_feedback(user, product):
    cache_feedback = Graph()
    if path.exists("feedback_cache.ttl"):
        cache_feedback.parse("feedback_cache.ttl", format="turtle")
    else:
        cache_feedback.bind('ECSDI', ECSDI)
        cache_feedback.add((agn.lastid, XSD.positiveInteger, Literal(0)))

    lastid = cache_feedback.value(subject=agn.lastid, predicate=XSD.positiveInteger)
    feddback = ECSDI.PeticionFeedback + '/'+str(lastid)
    #cache_feedback.add((feddback, ECSDI.id, Literal(lastid)))
    #cache_feedback.add((feddback, RDF.type, ECSDI.PeticionFeedback))
    cache_feedback.add((feddback, ECSDI.feedback_de, product))
    cache_feedback.add((feddback, ECSDI.valorada_por, user))

    cache_feedback.set((agn.lastid, XSD.positiveInteger,Literal(lastid+1)))
    cache_feedback.serialize("feedback_cache.ttl", format="turtle")

def generate_feedback_form(products):
    form_html = """
    <h1>Please give Feedback on the following products</h1>
    <form action="/feedback" method="POST">
    """
    #products = [{"name": "iphone", "uri": "ecsdi"}]
    for product in products:
        form_html += """
        <h4>{}
        <input type="hidden" name="product_uri" value="{}">

        <input type="number" id="rating_{}" name="rating_{}" min="1" max="5" required></h4><br>
        """.format(product["name"], product["uri"], product["uri"], product["uri"], product["uri"])

    form_html += """
        <input type="submit" value="Submit Feedback">
    </form>
    """
    #<label for="rating_{}">Rating (1-5):</label>
    return form_html

@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    valoraciones = None
    cache_feedback = Graph()
    if path.exists("feedback_cache.ttl"):
        cache_feedback.parse("feedback_cache.ttl", format="turtle")
    else: return redirect(url_for('userIndex'), mensaje = "No tienes productos para valorar")

    if request.method == 'POST':
        feedback_data = request.form
        feedback_graph = Graph()
        for val in cache_feedback.subjects(predicate=ECSDI.valorada_por, object=usuario):
            prod = cache_feedback.value(subject=val, predicate=ECSDI.feedback_de)
            feedback_graph.add((val, ECSDI.feedback_de, prod))
            punt = feedback_data.get('rating_'+ prod)
            cache_feedback.remove((val, ECSDI.feedback_de, prod))
            cache_feedback.remove((val, ECSDI.valorada_por, usuario))
            feedback_graph.add((val, ECSDI.valoracion, Literal(punt)))
        feedback_graph.add((agn.RespuestaFeedback, RDF.type, ECSDI.RespuestaFeedback))
        feedback_graph.add((agn.RespuestaFeedback, ECSDI.valorada_por, usuario))
        message = build_message(feedback_graph, ACL['inform'], sender = AssistenteUsuario.uri, receiver=agn.AgenteExperienciaUsuario, content=agn.RespuestaFeedback)
        resp = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in resp:
            feedbackadd = resp[4:]
        resposta = send_message(message,feedbackadd)
        cache_feedback.serialize("feedback_cache.ttl", format="turtle")
        return redirect(url_for('userIndex'), mensaje = "Gracias por tu opinion")
    
    product_graph = Graph()
    product_graph.parse("product.ttl", format="turtle")
    productos = []
    presente = False
    for val in cache_feedback.subjects(predicate=ECSDI.valorada_por, object=usuario):
        presente = True
        prod = cache_feedback.value(subject=val, predicate=ECSDI.feedback_de)
        prodname = product_graph.value(subject=prod, predicate=ECSDI.nombre)
        product_graph.append({"name": prodname, "uri": prod})
    if(presente): return render_template_string(generate_feedback_form(productos))
    else: return redirect(url_for('userIndex'), mensaje = "No tienes productos para valorar")

def registrar_busqueda(user, product_class:str, min_price:float=None, max_price:float=None, min_weight:float=None, max_weight:float=None):
    grafobusquedas = Graph()
    if path.exists("cache_recomendados.ttl"): grafobusquedas.parse("busquedas.ttl", format="turtle")
    else :
        grafobusquedas.add((agn.lastid, XSD.positiveInteger, Literal(0)))
        grafobusquedas.bind('ECSDI', ECSDI)
    search_id = grafobusquedas.value(subject=agn.lastid, predicate=XSD.positiveInteger)
    busqueda = ECSDI.ProductosRecomendados+'/'+str(search_id)
    grafobusquedas.add((busqueda, RDF.type, ECSDI.Busqueda))
    #grafobusquedas.add((busqueda, ECSDI.id, Literal(search_id)))
    if product_class != 'None':
        grafobusquedas.add((busqueda, ECSDI.tipoproducto, Literal(product_class)))
    if max_price:
        grafobusquedas.add((busqueda, ECSDI.max_precio, Literal(max_price)))
    if min_price not in ('None', 0, None):
        grafobusquedas.add((busqueda, ECSDI.min_precio, Literal(min_price)))
    if max_weight:
        grafobusquedas.add((busqueda, ECSDI.max_peso, Literal(max_weight)))
    if min_weight not in ('None', 0, None):
        grafobusquedas.add((busqueda, ECSDI.min_peso, Literal(min_weight)))
    user = ECSDI.Cliente + '/'+ user.split('/')[-1]
    #print(user)
    grafobusquedas.add((busqueda, ECSDI.buscado_por, user))
    grafobusquedas.set((agn.lastid, XSD.positiveInteger, Literal(search_id+1)))
    grafobusquedas.serialize("cache_recomendados.ttl", format="turtle")


@app.route("/recomendados")
def productos_recomendados():
    graforecomendaciones = Graph
    if path.exists("cache_recomendados.ttl"): graforecomendaciones.parse("busquedas.ttl", format="turtle")
    else: return redirect(url_for('userIndex'), mensaje = "No tienes productos recomendados")
    products = {}
    present = False
    for busqueda in graforecomendaciones.subjects(predicate=ECSDI.buscado_por, object=usuario):
        present = True
        gm = Graph()
        gm.bind('ECSDI', ECSDI)
        peticionbusquda =  agn.peticionbusqueda
        gm.add((peticionbusquda, RDF.type, ECSDI.PeticionBusqueda))
        product_type = graforecomendaciones.value(subject=busqueda, predicate= ECSDI.tipoproducto)
        gm.add((peticionbusquda, ECSDI.tipoproducto, Literal(product_type)))
        graforecomendaciones.remove((busqueda, ECSDI.tipoproducto, Literal(product_type)))
        max_price = graforecomendaciones.value(subject=busqueda, predicate= ECSDI.max_precio)
        if max_price:
            gm.add((peticionbusquda, ECSDI.max_precio, Literal(max_price)))
            graforecomendaciones.remove((busqueda, ECSDI.max_precio, Literal(max_price)))
        min_price = graforecomendaciones.value(subject=busqueda, predicate= ECSDI.min_price)
        if min_price:
            gm.add((peticionbusquda, ECSDI.min_precio, Literal(min_price)))
            graforecomendaciones.remove((busqueda, ECSDI.min_precio, Literal(min_price)))
        max_weight = graforecomendaciones.value(subject=busqueda, predicate= ECSDI.max_weight)
        if max_weight:
            gm.add((peticionbusquda, ECSDI.max_peso, Literal(max_weight)))
            graforecomendaciones.remove((busqueda, ECSDI.max_peso, Literal(max_weight)))
        min_weight = graforecomendaciones.value(subject=busqueda, predicate= ECSDI.min_weight)
        if min_weight:
            gm.add((peticionbusquda, ECSDI.min_peso, Literal(min_weight)))
            graforecomendaciones.remove((busqueda, ECSDI.min_peso, Literal(min_weight)))
        gm.add((peticionbusquda, ECSDI.buscado_por, usuario))
        graforecomendaciones.remove((busqueda, ECSDI.buscado_por, usuario))
        msg = build_message(gm, ACL.request, sender=AssistenteUsuario.uri, receiver=agn.AgenteBusqueda, content= peticionbusquda, msgcnt=mss_cnt)
        searchadd = requests.get(diraddress + '/message', params={'message': 'SEARCH|BUSCA'}).text
        if 'OK' in searchadd:
            busqueda = searchadd[4:]
            productos = send_message(msg,busqueda + '/comm')
            
            for prod in productos.subjects(predicate=RDF.type, object=ECSDI.Producto):
                product = {
                    "id": productos.value(subject=prod, predicate=ECSDI.id),
                    "name": str(productos.value(subject=prod, predicate=ECSDI.nombre)),
                    "price": str(productos.value(subject=prod, predicate=ECSDI.precio)),
                    "weight": productos.value(subject=prod, predicate=ECSDI.peso).split(',')[0][1:],
                    "brand": str(productos.value(subject=prod, predicate=ECSDI.tieneMarca)),
                    "vendedor": productos.value(subject=prod, predicate=ECSDI.vendido_por)
                }
                product['data'] =  product['name'] + ','+ str(product['price'])+ ',' + str(product['weight']) + ','+product['brand'] + ','+ product['id'] 
                if(product['vendedor']): product['data'] +=',' + product['vendedor']
                products[prod] =product
    if(present):return render_template('products.html', products=products)
    else: return redirect(url_for('userIndex'), mensaje = "No tienes productos recomendados")
    

@app.route("/comm")
async def comunicacion():
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
                if accion == ECSDI.PeticionFeedback:
                    for client in grafo.subjects(predicate= RDF.type, object= ECSDI.Cliente):
                        for val in grafo.subjects(predicate=ECSDI.valorada_por, object=client):
                            producto = grafo.value(subject=val, predicate=ECSDI.feedback_de)
                            cahear_feedback(client, producto)
                    
                    gr = build_message(Graph(),
                        ACL['confirm'],
                        sender=AssistenteUsuario.uri,
                        msgcnt=mss_cnt,
                        receiver= agn.AgenteExperienciaUsuario
                    )
                elif accion == ECSDI.ProductosRecomendados:
                    product_type = str(grafo.value(subject=content, predicate=ECSDI.tipoproducto))
                    max_price= str(grafo.value(subject=content, predicate=ECSDI.max_precio))
                    min_price =str(grafo.value(subject=content, predicate=ECSDI.min_precio))
                    max_weight= str(grafo.value(subject=content, predicate=ECSDI.max_peso))
                    min_weight= str(grafo.value(subject=content, predicate=ECSDI.min_peso))
                    user = str(grafo.value(subject=content, predicate=ECSDI.buscado_por))
                    registrar_busqueda(user, product_type, min_price, max_price, min_weight, max_weight)
                    gr = build_message(Graph(),
                        ACL['agree'],
                        sender=AssistenteUsuario.uri,
                        msgcnt=mss_cnt,
                        receiver= agn.AgenteExperienciaUsuario
                    )
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
        araycompras = form.data.get('envios')
        araycompras = araycompras.split(',')
        print(araycompras)
        infoentrega = agn.infoentrega
        grafo_entrega = Graph()
        grafo_entrega.bind('ECSDI', ECSDI)
        grafo_entrega.add((infoentrega, RDF.type, ECSDI.InfoUsuarioEntrega))
        grafo_entrega.add((infoentrega, ECSDI.latitud, Literal(form.data.get('shiping_latitude'))))
        grafo_entrega.add((infoentrega, ECSDI.longitud, Literal(form.data.get('shiping_longitude'))))
        grafo_entrega.add((infoentrega, ECSDI.metodoPago, Literal(form.data.get('payment_method'))))
        grafo_entrega.add((infoentrega, ECSDI.prioridadEntrega, Literal(form.data.get('shiping_priority'))))
        for env in  araycompras: 
            env = URIRef(env.split('\'')[1])
            print(env)
            grafo_entrega.add((env, RDF.type, ECSDI.Compra))
            grafo_entrega.add((infoentrega, ECSDI.compra_a_enviar, env))
        msg = build_message(grafo_entrega, ACL.request, sender=agn.AsistenteUsuario, receiver=agn.AgenteCompra, content=infoentrega, msgcnt=mss_cnt)
        compraadd = requests.get(diraddress + '/message', params={'message': 'SEARCH|COMPRA'}).text
        if 'OK' in compraadd:
            compra = compraadd[4:]
            #grafo_entrega.serialize("salida.ttl",format='turtle')
            response = send_message(msg, compra + '/comm')
            content = get_message_properties(response)['content']
            accion = response.value(subject=content, predicate=RDF.type)
            precio = response.value(subject=content, predicate=ECSDI.precio)
            print(precio)
            fecha_entrega = response.value(subject=content, predicate=ECSDI.fechaHora)
            data = fecha_entrega.split('T')
            print(data)
            return render_template('InfoEntrega.html', titulo = "Info entrega Provisional", info1 = "Te va a costar " + precio, info2 = "Va a llegar el " + data[0])

        #productos = requests.get(AgenteCompra.address, params=form.data).json()
    return render_template('envio.html', form = form)

@app.route('/busca', methods=['GET', 'POST'])
async def busca():
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
                    "id": productos.value(subject=prod, predicate=ECSDI.id),
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
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    # Ponemos en marcha el servidor Flask
    app.run(host=hostname, port=port, debug=False, use_reloader=False, threaded = True)
    mess = f'UNREGISTER|{solverid}'
    requests.get(diraddress + '/message', params={'message': mess})
else:
    print('Unable to register')
