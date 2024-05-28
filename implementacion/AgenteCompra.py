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
from datetime import datetime, timedelta
import math
import base64


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

def check_date(fechas, precios):
    for fecha, precio in zip(fechas, precios):
        if str(fecha) != "None":
            fecha_time = datetime.strptime(fecha, '%d/%m/%Y')
            hoy = datetime.today()
            diferencia = hoy - fecha_time
            if diferencia.days <= 15: return True, precio
    return False, None


def responder_peticion_devolucion(user_id, product_id):
    grafo_compras = Graph()
    grafo_compras.parse("bd/compras.ttl", format="turtle")
    fechas = []
    precios = []

    for s, p, o in grafo_compras.triples((None, RDF.type, ECSDI.Compra)):
        vendido_por = grafo_compras.value(subject=s, predicate=ECSDI.vendido_por)
        vendido_por = str(vendido_por).split('/')[-1]
        producto = grafo_compras.value(subject=s, predicate=ECSDI.Producto)
        producto = str(producto).split('/')[-1]
        if (vendido_por == str(user_id) and producto == str(product_id)):
            fecha = grafo_compras.value(subject=s, predicate=ECSDI.fechaHora)
            precio = grafo_compras.value(subject=s, predicate=ECSDI.precio)
            fechas.append(str(fecha))
            precios.append(str(precio))

    return check_date(fechas, precios)

def registrar_fecha_compra(compra_id, date): #cuandos envia
    grafo_compras = Graph()
    grafo_compras.parse("bd/compras.ttl", format="turtle")

    for s, p, o in grafo_compras.triples((None, RDF.type, ECSDI.Compra)):
        id = grafo_compras.value(subject=s, predicate=ECSDI.id)
        if str(compra_id) == str(id):
            fecha = grafo_compras.value(subject=s, predicate=ECSDI.fechaHora)
            if str(fecha) == "None":
                grafo_compras.set((s, ECSDI.fechaHora, Literal(date)))
                break

    grafo_compras.serialize("bd/compras.ttl", format="ttl")

def registrar_compra(user_id, product_id): #guardar precio pq puede cambiar

    #enviar al de centro logistico el id de la compra para que cuando lo
    #envie yo me comunique con el de contabilidad
    #añadir precio ya que puede cambiar
    
    grafo_compras = Graph()
    
    file_path = "bd/compras.ttl"
    if not os.path.exists(file_path):
        grafo_compras.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        grafo_compras.serialize(file_path, format="turtle")

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
    grafo_compras.add((compra, ECSDI.fechaHora, Literal(None)))
    grafo_compras.set((agn.last_id, XSD.positiveInteger, Literal(last_id+1)))
        
    grafo_compras.serialize("bd/compras.ttl", format="turtle")
        

def haversine(coord1, coord2):
    # Radius of the Earth in kilometers
    R = 6371.0

    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in kilometers
    distance = R * c

    return distance

def get_agent(agente):
    mess = f'SEARCH|{agente},1'  
    response = requests.get(f"{diraddress}/message", params={'message': mess})
    response = response.text.split(" ")
    if "OK" in response[0]:
        return f'{response[1]}/comm'
    else:
        return "NOT FOUND"

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
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro
            print(msgdic)
            receiver_uri = msgdic['content'] #receiver_uri marcado como conent por el Pablo
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=receiver_uri, predicate=RDF.type)

            if accion == ECSDI.PeticionCompra:
                print("Hola")
                #registrar_compra()
                #enviar mensaje a AgenteCentroLogisticos con la info de cada compra
                mss_cnt += 1
                return Response(status=200)

            elif accion == ECSDI.ProductoEnviado:
                compra_id = gm.value(subject=receiver_uri, predicate=ECSDI.Compra)
                fecha = gm.value(subject=receiver_uri, predicate=ECSDI.fechaHora)
                registrar_fecha_compra(compra_id, fecha)
                mss_cnt += 1
                return Response(status=200)


            elif accion == ECSDI.PeticionDevolucion:
                user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
                product_id = gm.value(subject=receiver_uri, predicate=ECSDI.id)
                devolucion, precio = responder_peticion_devolucion(user_id, product_id)

                receiver_uri = agn.AgenteDevolucion
                receiver_address = get_agent("DEVOLUCION") 

                content_graph = Graph()
                content_graph.add((receiver_uri, RDF.type, ECSDI.RespuestaDevolucion))
                if devolucion == True: 
                    content_graph.add((receiver_uri, ECSDI.acceptado, Literal(True)))
                    content_graph.add((receiver_uri, ECSDI.id, Literal(user_id)))
                    content_graph.add((receiver_uri, ECSDI.precio, Literal(precio)))
                else:
                    content_graph.add((receiver_uri, ECSDI.acceptado, Literal(False)))
                  
                msg_graph = build_message(
                    gmess=content_graph,
                    perf=ACL.request,
                    sender=AgenteCompra.uri,
                    receiver=receiver_uri,
                    msgcnt=mss_cnt
                )
                response_graph = send_message(gmess=msg_graph, address=receiver_address)
                mss_cnt += 1
                return Response(status=200)
    
            # No habia ninguna accion en el mensaje
            else:
                gr = build_message(Graph(),
                        ACL['not-understood'],
                        sender=AgenteCompra.uri,
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


def agentbehavior1(cola):
    """
    Un comportamiento del agente

    :return:
    """
    #registrar_compra(4, 11)
    #registrar_fecha_compra(4, 11, "23/05/2024")
    # Coordinates
    #coord1 = (41.300855, 1.980506)
    #coord2 = (41.317477, 1.991581)

    # Calculate distance
    #distance = haversine(coord1, coord2)
    #print(f"Distance: {distance} km")

    #fechas = ['10/05/2024', '01/01/2024']
    #precios = [100, 200]
    #print(check_date(fechas, precios))
    #registrar_fecha_compra(3, "24/05/2024")

if __name__ == '__main__':
    
    hostaddr = hostname = socket.gethostname()
    AgenteCompraAdd = f'http://{hostaddr}:{port}'
    AgenteCompraId = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{AgenteCompraId},COMPRA,{AgenteCompraAdd}'

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
        print(f'COMPRA {AgenteCompraId} successfully registered')
        
        # Buscamos el logger si existe en el registro
        loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in loggeradd:
            logger = loggeradd[4:]

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteCompraId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')


    print('The End')
