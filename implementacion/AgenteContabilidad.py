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
import os
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
   
    grafo_banco = Graph()

    file_path = "bd/banco.ttl"
    if not os.path.exists(file_path):
        grafo_banco.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        grafo_banco.serialize(file_path, format="turtle")

    grafo_banco.parse("bd/banco.ttl", format="ttl")
    grafo_banco.bind('ECSDI', ECSDI)

    user_exists = False
    for s, p, o in grafo_banco.triples((None, RDF.type, ECSDI.Transaccion)): #usar transaccion
        vendido_por = grafo_banco.value(subject=s, predicate=ECSDI.vendido_por)
        vendido_por = str(vendido_por).split('/')[-1]
        if vendido_por == str(user_id):
            user_exists = True
            cuenta = grafo_banco.value(subject=s, predicate=ECSDI.precio)
            cuenta_int = int(cuenta)
            if accion == "compra": new_amount = cuenta_int + amount
            else: new_amount = cuenta_int - amount
            grafo_banco.remove((s, ECSDI.precio, cuenta))
            grafo_banco.add((s, ECSDI.precio, Literal(str(new_amount))))
            break

    if not user_exists:
        last_id = grafo_banco.value(subject=agn.last_id, predicate=XSD.positiveInteger) 
        banco = ECSDI.Compra +'/'+ str(last_id+1) #cambiar por banco
        grafo_banco.add((banco, RDF.type, ECSDI.Compra)) 
        grafo_banco.add((banco, ECSDI.id, Literal(last_id+1)))
        comprador = ECSDI.Cliente + '/'+ str(user_id)
        grafo_banco.add((banco, ECSDI.vendido_por, comprador)) #cambiar, añadir en ontologia cuenta
        grafo_banco.add((banco, ECSDI.precio, Literal(amount)))
        grafo_banco.set((agn.last_id, XSD.positiveInteger, Literal(last_id+1)))

    grafo_banco.serialize("bd/banco.ttl", format="ttl")


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
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro
            receiver_uri = msgdic['receiver'] #receiver_uri
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=receiver_uri, predicate=RDF.type)
            
            if accion == ECSDI.ProductoEnviado:
                user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
                retirar = gm.value(subject=receiver_uri, predicate=ECSDI.precio)
                update_money(user_id, retirar, "compra")
                return Response(status=200)
                

            elif accion == ECSDI.RespuestaDevolucion:
                user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
                ingresar = gm.value(subject=receiver_uri, predicate=ECSDI.precio)
                update_money(user_id, ingresar, "reembolso")
                return Response(status=200)
                
            # No habia ninguna accion en el mensaje
            else:
                gr = build_message(Graph(),
                        ACL['not-understood'],
                        sender=AgenteContabilidad.uri,
                        msgcnt=get_count())
                

    return Response(status=400)


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



if __name__ == '__main__':
    
    hostaddr = hostname = socket.gethostname()
    AgenteContabilidadAdd = f'http://{hostaddr}:{port}'
    AgenteContabilidadId = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{AgenteContabilidadId},CONTABILIDAD,{AgenteContabilidadAdd}'

    diraddress = "http://localhost:9000"
    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass
    print('DS Hostname =', hostaddr)

    if 'OK' in resp:
        print(f'CONTABILIDAD {AgenteContabilidadId} successfully registered')
        
        # Buscamos el logger si existe en el registro
        loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in loggeradd:
            logger = loggeradd[4:]

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteContabilidadId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')


    print('The End')
