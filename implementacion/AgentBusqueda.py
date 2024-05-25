# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 15:58:13 2013

Esqueleto de agente usando los servicios web de Flask

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

@author: javier
"""
from os import getcwd, path
import sys

import requests
sys.path.append(path.dirname(getcwd()))
from multiprocessing import Process, Queue
import socket
import argparse
from AgentUtil.Logging import config_logger

from rdflib import Namespace, Graph, RDF, Literal, XSD
from flask import Flask, request, jsonify
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI

__author__ = 'javier'
parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web", action='store_true',
                    default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dir', default=None, help="Direccion del servicio de directorio")

# parsing de los parametros de la linea de comandos
args = parser.parse_args()

if not args.verbose:
    logger = config_logger(1, 'busqueda')

# Configuration stuff
    port = 9010



if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

if args.dir is None:
    diraddress = 'http://'+hostname+':9000'
else:
    diraddress = args.dir

print('DS Hostname =', hostaddr)


#ATRIBUTOS DEL AGENTE ------------------------------------------------------


agn = Namespace("http://www.agentes.org#")
busquedas = ECSDI.Busqueda

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteBusqueda = Agent('AgenteBusqueda',
                       agn.AgenteBusqueda,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/message' % diraddress,
                       'http://%s:9000/Stop' % diraddress)

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)


#FUNCIONES DEL AGENTE ------------------------------------------------------

'''@app.route("/accept_purchase", methods=["POST"])
def accept_purchase():
    # Lógica de aceptar la compra
    # Puedes acceder a datos adicionales enviados desde el formulario utilizando request
    # Por ejemplo, request.form['producto_id'] para obtener el ID del producto aceptado
    # Luego, redirigir al AgenteCompra o realizar cualquier otra acción necesaria
    return 'Redirige a agente de compra'
    #return redirect(url_for("agente_compra"))

@app.route("/reject_purchase", methods=["POST"])
def reject_purchase():
    # Lógica de rechazar la compra
    return 'Recarga la página para cercar productos'
    #return "Compra Rechazada"


@app.route("/search")
def comunicacion1():
    
    product_type = request.args.get('product_type')
    min_price = request.args.get('min_price')
    if(min_price): min_price = float(min_price)
    max_price = request.args.get('max_price')
    if(max_price): max_price = float(max_price)
    min_weight = request.args.get('min_weight')
    if(min_weight): min_weight = float(min_weight)
    max_weight = request.args.get('max_weight')
    if(max_weight): max_weight = float(max_weight)
    if product_type or min_price or max_price or  min_weight or max_weight:
        products = search_products(product_type, min_price, max_price, min_weight, max_weight)
        
        return render_template_string("""
        <h1>Productos Encontrados:</h1>
        <table border="1">
            <tr>
                <th>Nombre</th>
                <th>Peso</th>
                <th>Precio</th>
                <th>Marca</th>
            </tr>
            {% for product in products %}
            <tr>
                <td>{{ product['name'] }}</td>
                <td>{{ product['weight'] }}</td>
                <td>{{ product['price'] }}</td>
                <td>{{ product['brand'] }}</td>
            </tr>
            {% endfor %}
        </table>
        <form action="/accept_purchase" method="POST">
            <input type="submit" value="Aceptar Compra para todos los productos">
        </form>
        <form action="/reject_purchase" method="POST">
            <input type="submit" value="Rechazar Compra">
        </form>
    """, products=products)

    else: return "Tienes que poner algun filtro"

def search_products(product_class, min_price:float=None, max_price:float=None, min_weight:float=None, max_weight:float=None):
    
    global dsgraph
    logger.info(product_class)
    if not product_class: product_class = "Product"
    elif product_class not in("Blender", "Product"): return ["El tipo de producto especificado no es valido"] # esto es una solucion provisional
    query = """
    PREFIX pont: <http://www.products.org/ontology/>
    PREFIX pontp: <http://www.products.org/ontology/property/>
    PREFIX pontr: <http://www.products.org/ontology/resource/>

    SELECT ?product ?name ?price ?weight ?brand
    WHERE {
        ?product rdf:type pont:%s .
        ?product pontp:nombre ?name .
        ?product pontp:precio ?price .
        ?product pontp:peso ?weight .
        ?product pontp:tieneMarca ?brand_uri .
        ?brand_uri pontp:nombre ?brand .
    """ % product_class


    if min_price is not None:
        query += f"FILTER(?price >= {min_price})\n"
    if max_price is not None:
        query += f"FILTER(?price <= {max_price})\n"
    if min_weight is not None:
        query += f"FILTER(?weight >= {min_weight})\n"
    if max_weight is not None:
        query += f"FILTER(?weight <= {max_weight})\n"

    query += "}"

    results = dsgraph.query(query)

    products = []
    for row in results:
        product = {
            "name": str(row.name),
            "price": float(row.price),
            "weight": float(row.weight),
            "brand": str(row.brand)
        }
        products.append(product)

    return products    
'''


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
    grafobusquedas = Graph()
    grafobusquedas = grafobusquedas.parse(data=request.args.get('content'), format='xml')
    msgdic = get_message_properties(grafobusquedas)
    #print(msgdic)
    # Comprobamos que sea un mensaje FIPA ACL
    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(
            Graph(), ACL['not-understood'], sender=AgenteBusqueda.uri, msgcnt=mss_cnt)
    else:
        # Obtenemos la performativa
        perf = msgdic['performative']

        if perf != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(
                Graph(), ACL['not-understood'], sender=AgenteBusqueda.uri, msgcnt=mss_cnt)
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro

            # Averiguamos el tipo de la accion
            if 'content' in msgdic:
                content = msgdic['content']
                accion = grafobusquedas.value(subject=content, predicate=RDF.type)
                if accion == ECSDI.PeticionBusqueda:
                    #if (accion, ECSDI.tipoproducto) in grafobusquedas:
                    product_type = str(grafobusquedas.value(subject=content, predicate=ECSDI.tipoproducto))
                    #if (accion, ECSDI.max_precio) in grafobusquedas:
                    max_price= str(grafobusquedas.value(subject=content, predicate=ECSDI.max_precio))
                    #if (accion, ECSDI.min_precio) in grafobusquedas:
                    min_price =str(grafobusquedas.value(subject=content, predicate=ECSDI.min_precio))
                    #if (accion, ECSDI.max_peso) in grafobusquedas:
                    max_weight= str(grafobusquedas.value(subject=content, predicate=ECSDI.max_peso))
                    #if (accion, ECSDI.min_peso) in grafobusquedas:
                    min_weight= str(grafobusquedas.value(subject=content, predicate=ECSDI.min_peso))
                    user = str(grafobusquedas.value(subject=content, predicate=ECSDI.buscado_por))
                    if(min_price != 'None'): min_price = float(min_price)
                    else: min_price = None
                    if(max_price != 'None'): max_price = float(max_price)
                    else: max_price = None
                    if(min_weight != 'None'): min_weight = float(min_weight)
                    else: min_weight = None
                    if(max_weight != 'None'): max_weight = float(max_weight)
                    else: max_weight = None
                    logger.info([product_type,min_price, max_price, min_weight, max_weight, user])
                    products = search_products(product_type, min_price, max_price, min_weight, max_weight)
                    registrar_busqueda(user,product_type,min_price, max_price, min_weight, max_weight)
                    gr = products
                else: gr = build_message(Graph(), ACL['not-understood'], sender=AgenteBusqueda.uri, msgcnt=mss_cnt)
            else: gr = build_message(Graph(), ACL['not-understood'], sender=AgenteBusqueda.uri, msgcnt=mss_cnt)

    # Aqui realizariamos lo que pide la accion
    # Por ahora simplemente retornamos un Inform-done
    '''gr = build_message(Graph(),
                        ACL['inform'],
                        sender=AgenteBusqueda.uri,
                        msgcnt=mss_cnt,
                        receiver=msgdic['sender'], )'''
    mss_cnt += 1

    logger.info('Respondemos a la peticion')

    return gr.serialize(format='xml')



@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass


def cargar_productos():
    """
    Un comportamiento del agente

    :return:
    """
    products_graph = Graph()
    products_graph.parse("product.ttl", format="turtle")
    return products_graph

def registrar_busqueda(user, product_class:str, min_price:float=None, max_price:float=None, min_weight:float=None, max_weight:float=None):
    grafobusquedas = Graph()
    if path.exists("busquedas.ttl"): grafobusquedas.parse("busquedas.ttl", format="turtle")
    else :
        grafobusquedas.add((agn.searchid, XSD.positiveInteger, Literal(0)))
    grafobusquedas.bind('ECSDI', ECSDI)
    search_id = grafobusquedas.value(subject=agn.searchid, predicate=XSD.positiveInteger)
    busqueda = busquedas+'/'+str(search_id)
    grafobusquedas.add((busqueda, RDF.type, ECSDI.Busqueda))
    grafobusquedas.add((busqueda, ECSDI.id, Literal(search_id)))
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
    grafobusquedas.set((agn.searchid, XSD.positiveInteger, Literal(search_id+1)))
    grafobusquedas.serialize("busquedas.ttl", format="turtle")


def search_products(product_class, min_price:float=None, max_price:float=None, min_weight:float=None, max_weight:float=None):
    global dsgraph
    dsgraph=cargar_productos()
    

    query = """
    PREFIX ECSDI: <urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT ?product ?id ?name ?price ?weight ?brand
    WHERE {
        ?product rdf:type ECSDI:Producto .
        ?product ECSDI:tipoproducto ?tipo .
        ?product ECSDI:id ?id .
        ?product ECSDI:nombre ?name .
        ?product ECSDI:precio ?price .
        ?product ECSDI:peso ?weight .
        ?product ECSDI:tieneMarca ?brand .
    """ 

    query += f"FILTER(?tipo = '{product_class}')\n"
    if min_price is not None:
        query += f"FILTER(?price >= {min_price})\n"
    if max_price is not None:
        query += f"FILTER(?price <= {max_price})\n"
    if min_weight is not None:
        query += f"FILTER(?weight >= {min_weight})\n"
    if max_weight is not None:
        query += f"FILTER(?weight <= {max_weight})\n"
    query += "}"

    results = dsgraph.query(query)
    product_graph = Graph()
    print(len(results))
    for row in results:
        prod = row.product
        product_graph.add((prod, RDF.type, ECSDI.Producto))
        nombre = str(row.name)
        if nombre:
            product_graph.add((prod, ECSDI.nombre, Literal(nombre)))
        id = int(row.id)
        if id:
            product_graph.add((prod, ECSDI.id, Literal(id)))
        precio = float(row.price)
        if precio:
            product_graph.add((prod, ECSDI.precio, Literal(precio)))
        peso = float(row.weight),
        if peso:
            product_graph.add((prod, ECSDI.peso, Literal(peso)))
        tieneMarca = str(row.brand)
        if tieneMarca:
            product_graph.add((prod, ECSDI.tieneMarca, Literal(tieneMarca)))
        vendedor = dsgraph.value(subject=prod, predicate=ECSDI.vendido_por)
        if vendedor:
            product_graph.add((prod, ECSDI.vendido_por, vendedor))
    return product_graph


'''def send_message_custom(products):
   
    global mss_cnt
    content = Graph()
    content.bind('pontp', Namespace("http://www.products.org/ontology/property/"))
    for product in products:
        product_uri = agn[product['name']]  
        content.objects((product_uri, RDF.type, agn.Product))
        content.objects((product_uri, agn.nombre, Literal(product['name'])))
        content.objects((product_uri, agn.precio, Literal(product['price'])))
        content.objects((product_uri, agn.peso, Literal(product['weight'])))
        content.objects((product_uri, agn.tieneMarca, Literal(product['brand'])))  


    msg = build_message(Graph(), ACL.inform, sender=AgenteBusqueda.uri, receiver=agn.AgenteSimple, content=content, msgcnt=mss_cnt)
    
    port2 = 9011
    address = 'http://{}:{}/comm'.format(hostname, port2)
    #msg = "hola"
    logger.info(type(msg))
    r = requests.get(address, params={'content': msg})
    
    mss_cnt += 1'''


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    # Registramos el solver en el servicio de directorio
    solveradd = f'http://{hostaddr}:{port}'
    solverid = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{solverid},BUSCA,{solveradd}'
    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass
    print('DS Hostname =', hostaddr)

    if 'OK' in resp:
        print(f'BUSCA {solverid} successfully registered')
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
    # Ponemos en marcha el servidor'''
    
   
    
    # Esperamos a que acaben los behaviors
    
    print('The End')