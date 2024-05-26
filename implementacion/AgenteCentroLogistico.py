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
from rdflib.namespace import XSD

__author__ = 'javier'

# Configuration stuff
hostname = socket.gethostname()
port = 9013

#Peso maximo de un lote
MaxPesoLote = 100

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentePersonal = Agent('AgenteSimple',
                       agn.AgenteSimple,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
g = Graph()

cola1 = Queue()


app = Flask(__name__)

#negociar Transportista
#def negociarTransportista():

#    return idTransportista

#Creacion de lotes
#def crearLotes():


def escribirAPedido():
    #crear pedido
    g = Graph()
    # Definir el namespace de tu ontología ECSDI
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")
    g.bind("ECSDI", ECSDI)


    AGN = Namespace("http://www.agentes.org#")
    g.bind("AGN", AGN)

    # Cargar el grafo existente desde el archivo si existe
    try:
        g.parse("pedido.ttl", format="turtle")
    except FileNotFoundError:
        pass  # Si el archivo no existe, continuamos con un grafo vacío

    # Leer el valor actual de searchid
    searchid_value = g.value(subject=AGN.searchid, predicate=XSD.positiveInteger)
    if searchid_value is None:
        searchid = 0
    else:
        searchid = int(searchid_value)

    # Incrementar el valor de searchid
    searchid += 1

    # Actualizar el valor en el grafo
    g.set((AGN.searchid, XSD.positiveInteger, Literal(searchid, datatype=XSD.positiveInteger)))



    # Definir la URI de tu pedido
    pedido_uri = ECSDI[f'Pedido/{searchid}']

    # Añadir triples al grafo
    g.add((pedido_uri, RDF.type, ECSDI.Pedido))
    g.add((pedido_uri, ECSDI.id, Literal(1, datatype=XSD.integer)))  # Id del pedido
    g.add((pedido_uri, ECSDI.latitud, Literal(10.0)))  # Latitud
    g.add((pedido_uri, ECSDI.longitud, Literal(20.0)))  # Longitud
    g.add((pedido_uri, ECSDI.metodoPago, Literal("tarjeta")))  # Método de pago
    g.add((pedido_uri, ECSDI.prioridadEntrega, Literal(1, datatype=XSD.integer)))  # Prioridad de entrega

    # Definir la URI de la compra asociada al pedido
    compra_uri = ECSDI[f'Compra/{searchid}']
    g.add((pedido_uri, ECSDI.compra_a_enviar, compra_uri))
    

    temp_ttl = g.serialize(format="turtle")

    # Reemplazar la línea del searchid con el formato deseado
    temp_ttl_lines = temp_ttl.split('\n')
    with open("pedido.ttl", "r") as f:
        original_lines = f.readlines()

    for i, line in enumerate(original_lines):
        if "AGN:searchid" in line:
            original_lines[i] = f'<http://www.agentes.org#searchid> xsd:positiveInteger {searchid} .\n'
            break
    else:
        # Si no se encuentra, añadir al final
        original_lines.append(f'<http://www.agentes.org#searchid> xsd:positiveInteger {searchid} .\n')


    # Serializar el grafo en formato Turtle y guardarlo en un archivo
    with open("pedido.ttl", "w") as f:
        f.write(g.serialize(format="turtle"))


@app.route("/comm")
def comunicacion():
    """
    Entrypoint for communication
    """
    global dsgraph
    global mss_cnt


    message = request.args.get('content', '')  #
    print(message)
    gm = Graph()
    gm.parse(data=message, format='xml') 
    msgdic = get_message_properties(gm)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCompra.uri, msgcnt=get_count())
    else:
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=DirectoryAgent.uri,
                               msgcnt=get_count())
        else:
            perf = msgdic['performative']

            if perf != ACL.request:
                # Si no es un request, respondemos que no hemos entendido el mensaje
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCompra.uri, msgcnt=get_count())
            
            else:
                receiver_uri = msgdic['receiver'] #receiver_uri
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=receiver_uri, predicate=RDF.type)

                if accion == ECSDI.Pedido:
                    escribirAPedido()
                # Preparar lotes para enviar
                #else: 
                #    crearLotes()
                
    return "p"



@app.route("/Stop")
def stop():
    """
    Entrypoint that stops the agent
    """
    tidyup()
    shutdown_server()
    return "Stopping Server"


def tidyup():
    """
    Actions to be taken before stopping the agent
    """
    pass


def agentbehavior1(cola):
    """
    Agent's behavior
    """
    pass


if __name__ == '__main__':
    escribirAPedido()
    print("Archivo pedido.ttl creado.")

    # Launch the behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Launch the server
    app.run(host=hostname, port=port)

    # Wait for the behaviors to finish
    ab1.join()
    print('The End')