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

from rdflib import Namespace, Graph, RDF, Literal
from flask import Flask, request
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
if args.port is None:
    port = 9010
else:
    port = args.port

if args.dir is None:
    raise NameError('A Directory Service addess is needed')
else:
    diraddress = args.dir

if args.open:
    hostname = '0.0.0.0'
    hostaddr = gethostname()
else:
    hostaddr = hostname = socket.gethostname()

print('DS Hostname =', hostaddr)


#ATRIBUTOS DEL AGENTE ------------------------------------------------------


agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteBusqueda = Agent('AgenteBusqueda',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)


#FUNCIONES DEL AGENTE ------------------------------------------------------




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

    logger.info('Peticion de informacion recibida')

    # Extraemos el mensaje y creamos un grafo con el
    message = request.args['content']
    gm = Graph()
    b1 = ECSDI.Busqueda
    products = search_products("Blender", min_price=None, max_price=None, min_weight=None, max_weight=None)
    send_message_custom(products)
    msgdic = get_message_properties(gm)
    logger.info(msgdic)
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
                accion = gm.value(subject=content, predicate=RDF.type)

            # Aqui realizariamos lo que pide la accion
            # Por ahora simplemente retornamos un Inform-done
            gr = build_message(Graph(),
                               ACL['inform'],
                               sender=AgenteBusqueda.uri,
                               msgcnt=mss_cnt,
                               receiver=msgdic['sender'], )
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


def agentbehavior1(cola):
    """
    Un comportamiento del agente

    :return:
    """
    global dsgraph
    dsgraph.parse('product.ttl',format='turtle')
    pass



def search_products(product_class, min_price:float=None, max_price:float=None, min_weight:float=None, max_weight:float=None):
    
    products_graph = Graph()
    products_graph.parse("product.ttl", format="turtle")


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

    results = products_graph.query(query)

    products = []
    for row in results:
        product = {
            "name": str(row.name),
            "price": float(row.price),
            "weight": float(row.weight),
            "brand": str(row.brand)
        }
        products.append(product)

    '''print("Products:")
    for product in products:
        print(product)'''

    return products


def send_message_custom(products):
   
    global mss_cnt
    content = Graph()
    content.bind('pontp', Namespace("http://www.products.org/ontology/property/"))
    for product in products:
        product_uri = agn[product['name']]  
        content.add((product_uri, RDF.type, agn.Product))
        content.add((product_uri, agn.nombre, Literal(product['name'])))
        content.add((product_uri, agn.precio, Literal(product['price'])))
        content.add((product_uri, agn.peso, Literal(product['weight'])))
        content.add((product_uri, agn.tieneMarca, Literal(product['brand'])))  


    msg = build_message(Graph(), ACL.inform, sender=AgenteBusqueda.uri, receiver=agn.AgenteSimple, content=content, msgcnt=mss_cnt)
    
    port2 = 9011
    address = 'http://{}:{}/comm'.format(hostname, port2)
    #msg = "hola"
    logger.info(type(msg))
    r = requests.get(address, params={'content': msg})
    
    mss_cnt += 1


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()
    # Registramos el solver en el servicio de directorio
    app.run(host=hostname, port=port, debug=True)
    '''solveradd = 'http://'+hostaddr+':'+str(port)
    solverid = hostaddr.split('.')[0] + '-' + str(port)
    mess = 'REGISTER|'+solverid+',BUSQUEDA,'+solveradd
    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass
    
    if 'OK' in resp:
        print(f'SOLVER {solverid} successfully registered')
    # Ponemos en marcha el servidor'''
    
   
    
    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')