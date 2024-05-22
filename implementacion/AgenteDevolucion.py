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

# Configuration stuff
hostname = socket.gethostname()
port = 9011

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteDevolucion = Agent('AgenteDevolucion',
                       agn.AgenteDevolucion,
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


app = Flask(__name__)

def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt

@app.route("/comm")
def comunicacion():
    """
    Entrypoint for communication
    """
    global dsGraph

    print("CCCCCCCCCCCCCCCCCCCCCCCCCC")
    message = request.args['content']
    print("DDDDDDDDDDDDDDDDDDDDDDDDDDD")
    gm = Graph()
    print("EEEEEEEEEEEEEEEEEEEEEEEEEEE")
    print("------------------------------------")
    print(message)
    print("------------------------------------")
    #message_without_declaration = message.replace('<?xml version="1.0" encoding="utf-8"?>', '')
    #print("------------------------------------")
    #print(message_without_declaration)
    #print("------------------------------------")
    gm.parse(data=message, format='xml') #el mensaje que envio es el problema(el grafo vamos)
    print("FFFFFFFFFFFFFFFFFFFFFFFFFFFFF")

    msgdic = get_message_properties(gm)
    print(msgdic)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteDevolucion.uri, msgcnt=get_count())
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            print("pepepepepepepe")
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=DirectoryAgent.uri,
                               msgcnt=get_count())
        else:
            print("uuuuuuuuuuuuu")
            # Obtenemos la performativa
            perf = msgdic['performative']

            if perf != ACL.request:
                # Si no es un request, respondemos que no hemos entendido el mensaje
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteDevolucion.uri, msgcnt=get_count())
            else:
                # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
                # de registro
                receiver_uri = msgdic['receiver'] #receiver_uri
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=receiver_uri, predicate=RDF.type)
                
                print("///////////////////////////")
                print(receiver_uri)
                print()
                print(accion)
                print("///////////////////////////")
                

                if accion == ECSDI.PeticionDevolucion:
                    print("AVESTRUZ")

                    #checkear con AgenteCompra cuando se compro

                    agn = Namespace("http://www.agentes.org#")
                    receiver_uri = agn.AgenteContabilidad
                    receiver_address = "http://DESKTOP-C2NM81C:9012/comm"  # Replace with the actual address
                    #poner el hostname, no hardocoded

                    # Create a RDF graph for the message content
                    price = "11"
                    buyer_id = "user7"
                    content_graph = Graph()
                    content_graph.add((receiver_uri, RDF.type, ECSDI.DevolucionAceptada))
                    content_graph.add((receiver_uri, ECSDI.precio, Literal(price)))
                    content_graph.add((receiver_uri, ECSDI.id_usuario, Literal(buyer_id)))
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
                        sender=AgenteDevolucion.uri,
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
    # Launch the behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Launch the server
    app.run(host=hostname, port=port)

    # Wait for the behaviors to finish
    ab1.join()
    print('The End')
