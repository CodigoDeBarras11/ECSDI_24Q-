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
from flask import Flask, request, render_template_string
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI

__author__ = 'Pepe'

# Configuration stuff
hostname = socket.gethostname()
port = 9011

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteCompra = Agent('AgenteCompra',
                       agn.AgenteCompra,
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


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    global dsgraph
    global mss_cnt
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
    global mss_cnt
    global AgenteCompra

    # Define the receiver agent's URI and address
    agn = Namespace("http://www.agentes.org#")
    receiver_uri = agn.AgenteContabilidad
    receiver_address = "http://DESKTOP-C2NM81C:9012/comm"  # Replace with the actual address
    #poner el hostname, no hardocoded

    # Create a RDF graph for the message content
    action = ECSDI.Compra
    price = "11"
    content_graph = Graph()
    content_graph.add((receiver_uri, RDF.type, action))
    content_graph.add((receiver_uri, ECSDI.precio, Literal(price)))
    #content_graph.add((content, RDF.type, ECSDI.Compra))
    #content_graph.add((receiver_uri, ECSDI.productos_comprar, Literal("11")))
    

    #print(content_graph)
    print('**********************************')
    print("Content Graph:")
    for triple in content_graph:
        print("-------------")
        print(triple)
        print("-------------")
    print('**********************************')

    # Build the message
    msg_graph = build_message(
        gmess=content_graph,
        perf=ACL.request,
        sender=AgenteCompra.uri,
        receiver=receiver_uri,
        msgcnt=mss_cnt
    )
    #print(msg_graph)
    #print('**********************************')
    print("\nMessage Graph:")
    for triple in msg_graph:
        print("-------------")
        print(triple)
        print("-------------")
    print('**********************************')
    # Send the message
    response_graph = send_message(gmess=msg_graph, address=receiver_address)

    # Increment the message counter
    mss_cnt += 1

   


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    
    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
