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
from flask import Flask, request, render_template_string, Response
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI



__author__ = 'Pepe'

# Configuration stuff
hostname = socket.gethostname()
port = 9012

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteContabilidad = Agent('AgenteContabilidad',
                       agn.AgenteContabilidad,
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


def update_money(user_id, amount, accion):
   
    g = Graph()
    ns = Namespace("http://example.org/") #cambiar
    g.bind("ex", ns)
    g.parse("bd/banco.ttl", format="ttl")

    user_exists = False
    for s, p, o in g:
        if str(s) == str(ns[user_id]):
            user_exists = True
            existing_amount = int(o)
            if existing_amount is not None:
                amount = int(amount)
                if accion == "compra": new_amount = existing_amount + amount
                else: new_amount = existing_amount - amount
                g.remove((s, p, o))
                g.add((s, p, Literal(str(new_amount))))
                break

    if not user_exists:
        subject = ns[user_id]
        predicate = ECSDI.precio
        object_value = Literal(amount)
        g.add((subject, predicate, object_value))

    g.serialize("bd/banco.ttl", format="ttl")


def get_graph_data(gm, receiver_uri):
    user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
    money = gm.value(subject=receiver_uri, predicate=ECSDI.precio)

    return user_id, money

@app.route("/comm")
def comunicacion():
    """
    Communication Entrypoint
    """

    global dsGraph

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml') 
    msgdic = get_message_properties(gm)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteContabilidad.uri, msgcnt=get_count())
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
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteContabilidad.uri, msgcnt=get_count())
            else:
                # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
                # de registro
                receiver_uri = msgdic['receiver'] #receiver_uri
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=receiver_uri, predicate=RDF.type)
            
                if accion == ECSDI.ProductoEnviado:
                    user_id, retirar = get_graph_data(gm, receiver_uri)
                    update_money(user_id, retirar, "compra")
                

                elif accion == ECSDI.DevolucionAceptada: #añair a la ontologia
                    user_id, ingresar = get_graph_data(gm, receiver_uri)
                    update_money(user_id, ingresar, "reembolso")
                
                # No habia ninguna accion en el mensaje
                else:
                    gr = build_message(Graph(),
                                ACL['not-understood'],
                                sender=AgenteContabilidad.uri,
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
    pass


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')
