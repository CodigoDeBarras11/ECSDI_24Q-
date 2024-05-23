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
import os
import sys

import requests
sys.path.append(path.dirname(getcwd()))
from multiprocessing import Process, Queue
import socket
import argparse
from AgentUtil.Logging import config_logger

from rdflib import Namespace, Graph, RDF, Literal, XSD
from flask import Flask, request, render_template_string, Response
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


def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt


def registrar_fecha_compra(user_id, product_id): #cuandos envia
    grafo_compras = Graph()
    grafo_compras.parse("compras.ttl", format="turtle")


def registrar_compra(user_id, product_id):
    
    grafo_compras = Graph()
    
    file_path = "bd/compras.ttl"
    if not os.path.exists(file_path):
        grafo_compras.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        grafo_compras.serialize(file_path, format="turtle")

    else:    
        grafo_compras.parse("bd/compras.ttl", format="turtle")
        grafo_compras.bind('ECSDI', ECSDI)
        last_id = grafo_compras.value(subject=agn.last_id, predicate=XSD.positiveInteger)
        compra = ECSDI.Compra +'/'+ str(last_id+1)
        grafo_compras.add((compra, RDF.type, ECSDI.Compra))
        grafo_compras.add((compra, ECSDI.id, Literal(last_id+1)))
        comprador = ECSDI.Cliente + '/'+ str(user_id)
        grafo_compras.add((compra, ECSDI.vendido_por, comprador)) #cambiar, añadir en ontologia comprado_por
        producto = ECSDI.Producto + '/' + str(product_id)
        grafo_compras.add((compra, ECSDI.Producto, producto))
        grafo_compras.set((agn.last_id, XSD.positiveInteger, Literal(last_id+1)))
        grafo_compras.serialize("bd/compras.ttl", format="turtle")
        

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    global dsGraph
    global mss_cnt

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml') 
    msgdic = get_message_properties(gm)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCompra.uri, msgcnt=get_count())
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=DirectoryAgent.uri,
                               msgcnt=get_count())
        else:
            # Obtenemos la performativa
            perf = msgdic['performative']

            if perf != ACL.request:
                # Si no es un request, respondemos que no hemos entendido el mensaje
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCompra.uri, msgcnt=get_count())
            else:
                # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
                # de registro
                receiver_uri = msgdic['receiver'] #receiver_uri
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=receiver_uri, predicate=RDF.type)

                if accion == ECSDI.Compra:
                    # Define the receiver agent's URI and address
                    registrar_compra()


                elif accion == ECSDI.PeticionDevolucion:
                    # Define the receiver agent's URI and address
                    agn = Namespace("http://www.agentes.org#")
                    receiver_uri = agn.AgenteDevolucion
                    receiver_address = "http://{hostname}:9013/comm"  

                    devolucion = False
                    #chequear en la base de datos si la devolucion se acepta o no
                    
                    if devolucion == False:
                        # Create a RDF graph for the message content
                        price = "11"
                        buyer_id = "user7"
                        content_graph = Graph()
                        content_graph.add((receiver_uri, RDF.type, ECSDI.DevolucionDenegada))
                        content_graph.add((receiver_uri, ECSDI.precio, Literal(price)))
                        content_graph.add((receiver_uri, ECSDI.id_usuario, Literal(buyer_id)))

                        # Build the message
                        msg_graph = build_message(
                            gmess=content_graph,
                            perf=ACL.request,
                            sender=AgenteCompra.uri,
                            receiver=receiver_uri,
                            msgcnt=mss_cnt
                        )
                        response_graph = send_message(gmess=msg_graph, address=receiver_address)

                        # Increment the message counter
                        mss_cnt += 1

                    else:
                        # Create a RDF graph for the message content
                        price = "11"
                        buyer_id = "user7"
                        content_graph = Graph()
                        content_graph.add((receiver_uri, RDF.type, ECSDI.DevolucionAceptada))
                        content_graph.add((receiver_uri, ECSDI.precio, Literal(price)))
                        content_graph.add((receiver_uri, ECSDI.id_usuario, Literal(buyer_id)))

                        # Build the message
                        msg_graph = build_message(
                            gmess=content_graph,
                            perf=ACL.request,
                            sender=AgenteCompra.uri,
                            receiver=receiver_uri,
                            msgcnt=mss_cnt
                        )
                        response_graph = send_message(gmess=msg_graph, address=receiver_address)

                        # Increment the message counter
                        mss_cnt += 1

                # No habia ninguna accion en el mensaje
                else:
                    gr = build_message(Graph(),
                                ACL['not-understood'],
                                sender=AgenteCompra.uri,
                                msgcnt=get_count())
                
                return Response(status=200)

    return Response(status=200)


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
    registrar_compra(4, 11)


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)
    
    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
