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
#print("fwefwef")
#print(hostname)
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


def get_term(uri):
    """
    Extracts the term from a given URI.

    :param uri: The URI from which to extract the term.
    :return: The extracted term.
    """
    common_prefix = 'urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8'
    return uri.replace(common_prefix, '').replace(':', '')


def update_money(user_id, amount, accion):
   
    g = Graph()

    ns = Namespace("http://example.org/")
    g.bind("ex", ns)

    g.parse("bd/banco.ttl", format="ttl")

    user_exists = False
    for s, p, o in g:
        #print(f"Triple: {s}, {p}, {o}")
        print("------------------")
        print(str(s))
        print(str(ns[user_id]))
        print("------------------")
        if str(s) == str(ns[user_id]):
            user_exists = True
            print("pppppppppppppppppppp")
            existing_amount = int(o)
            print("aaaaaaaaaaaaaaaaaaaaaaaa")
            if existing_amount is not None:
                amount = int(amount)
                if accion == "compra": new_amount = existing_amount + amount
                else: new_amount = existing_amount - amount
                print(new_amount)
                g.remove((s, p, o))
                g.add((s, p, Literal(str(new_amount))))
                break

    if not user_exists:
        subject = ns[user_id]
        predicate = ECSDI.precio
        object_value = Literal(amount)
        g.add((subject, predicate, object_value))

    g.serialize("bd/banco.ttl", format="ttl")


@app.route("/comm")
def comunicacion():
    """
    Communication Entrypoint
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
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteContabilidad.uri, msgcnt=get_count())
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
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteContabilidad.uri, msgcnt=get_count())
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
                

                if accion == ECSDI.ProductoEnviado:
                    print("AVESTRUZ")
                    print(gm.value(subject=receiver_uri, predicate=ECSDI.precio))
                    print(gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario))
                    user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
                    retirar = gm.value(subject=receiver_uri, predicate=ECSDI.precio)
                    
                    update_money(user_id, retirar, "compra")
                

                elif accion == ECSDI.DevolucionAceptada: #añair a la ontologia
                    print("AVESTRUZ")
                    update_money(user_id, retirar, "reembolso")
                    """# Accion de transferencia
                    if accion == ECSDI.ReembolsarProductos: #esto son clases
                        # Content of the message
                        #hay que cambiar
                        for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                            gm.remove((item, None, None))
                        gr = gm
                    
                    elif accion == ECSDI.ProductosComprar:
                        #hay que cambiar
                        for item in gm.subjects(RDF.type, ACL.FipaAclMessage):
                            gm.remove((item, None, None))
                        gr = gm
                    """
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
