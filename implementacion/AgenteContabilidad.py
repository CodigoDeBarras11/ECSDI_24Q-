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
import argparse



__author__ = 'Pepe'

# Configuration stuff
hostname = socket.gethostname()
port = 9012

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

parser = argparse.ArgumentParser()
parser.add_argument('--open', help="Define si el servidor esta abierto al exterior o no", action='store_true',
                    default=False)
parser.add_argument('--verbose', help="Genera un log de la comunicacion del servidor web", action='store_true',
                    default=False)
parser.add_argument('--port', type=int, help="Puerto de comunicacion del agente")
parser.add_argument('--dir', default=None, help="Direccion del servicio de directorio")

args = parser.parse_args()
if args.dir is None:
    diraddress =  'http://'+hostname+':9000'
else:
    diraddress = args.dir

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

def update_money(cliente, tienda, cantidad, accion):
   
    grafo_banco = Graph()
    #cliente = URIRef(cliente)
    #tienda = URIRef(tienda)
    file_path = "bd/banco.ttl"
    if not os.path.exists(file_path):
        grafo_banco.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        grafo_banco.serialize(file_path, format="turtle")

    grafo_banco.parse("bd/banco.ttl", format="ttl")
    grafo_banco.bind('ECSDI', ECSDI)

    cliente_existe = False
    tienda_existe = False
    
    for cuenta in grafo_banco.subjects(ECSDI.pertenece_a, None):
        pertenece_a = grafo_banco.value(cuenta, ECSDI.pertenece_a)
        balance = grafo_banco.value(cuenta, ECSDI.balance)

        if pertenece_a == cliente:
            cliente_existe = True
            cantidad_previa = float(balance)
            if accion == "compra":
                nuevo_balance = cantidad_previa - float(cantidad)
            else:
                nuevo_balance = cantidad_previa + float(cantidad)
            #grafo_banco.remove((cuenta, ECSDI.balance, balance))
            grafo_banco.set((cuenta, ECSDI.balance, Literal(str(nuevo_balance))))

        if pertenece_a == tienda:
            tienda_existe = True
            cantidad_previa = float(balance)
            if accion == "compra":
                nuevo_balance = cantidad_previa + float(cantidad)
            else:
                nuevo_balance = cantidad_previa - float(cantidad)
            #grafo_banco.remove((cuenta, ECSDI.balance, balance))
            grafo_banco.set((cuenta, ECSDI.balance, Literal(str(nuevo_balance))))

        if cliente_existe and tienda_existe:
            break

    last_id = grafo_banco.value(subject=agn.last_id, predicate=XSD.positiveInteger) 
    if not cliente_existe:
        banco = ECSDI.CuentaBancaria +'/'+ str(last_id+1) 
        cuenta_usuario = cliente
        grafo_banco.add((banco, ECSDI.pertenece_a, cuenta_usuario)) 
     
        cantidad_negativa = "-" + cantidad
        grafo_banco.add((banco, ECSDI.balance, Literal(cantidad_negativa)))
    if not tienda_existe:
        if not cliente_existe: last_id = last_id + 1
        cuenta_tienda = tienda
        banco = ECSDI.CuentaBancaria +'/'+ str(last_id+1) 
        grafo_banco.add((banco, ECSDI.pertenece_a, cuenta_tienda)) 
        grafo_banco.add((banco, ECSDI.balance, Literal(cantidad)))
    grafo_banco.set((agn.last_id, XSD.positiveInteger, Literal(last_id+1)))

    grafo_banco.serialize("bd/banco.ttl", format="ttl")


@app.route("/comm")
def comunicacion():
    """
    Communication Entrypoint
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
            receiver_uri = msgdic['receiver']
            print(receiver_uri)
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=receiver_uri, predicate=RDF.type)
            
            if accion == ECSDI.ProductoEnviado:
                print("compra")
                cliente = gm.value(subject=receiver_uri, predicate=ECSDI.comprado_por)
                tienda = gm.value(subject=receiver_uri, predicate=ECSDI.vendido_por)
                cantidad = gm.value(subject=receiver_uri, predicate=ECSDI.precio)

                print(cliente)
                print(tienda)
                print(cantidad)
                update_money(cliente, tienda, cantidad, "compra")
                r_graph = build_message(
                    gmess=Graph(),
                    perf=ACL.agree,
                    sender=AgenteContabilidad.uri,
                    receiver=agn.AgenteDevolucion,
                    content=ECSDI.RespuestaDevolucion,
                    msgcnt=mss_cnt
                )
                mss_cnt += 1
                return r_graph.serialize(format='xml')
                

            elif accion == ECSDI.RespuestaDevolucion:
                print("reembolso")
                cliente = gm.value(subject=receiver_uri, predicate=ECSDI.comprado_por)
                tienda = gm.value(subject=receiver_uri, predicate=ECSDI.vendido_por)
                cantidad = gm.value(subject=receiver_uri, predicate=ECSDI.precio)

                print(cliente)
                print(tienda)
                print(cantidad)
                update_money(cliente, tienda, cantidad, "reembolso")
                r_graph = build_message(
                    gmess=Graph(),
                    perf=ACL.agree,
                    sender=AgenteContabilidad.uri,
                    receiver=agn.AgenteDevolucion,
                    content=ECSDI.RespuestaDevolucion,
                    msgcnt=mss_cnt
                )
                mss_cnt += 1
                return r_graph.serialize(format='xml')
                
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
        #cliente = "urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8Cliente/2"
        #tienda = "urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8Tienda/0"
        #cantidad = "90.0"
        #accion = "reembolsar"
        #update_money(cliente, tienda, cantidad, accion)
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
