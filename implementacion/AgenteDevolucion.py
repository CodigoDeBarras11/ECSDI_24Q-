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
from flask import Flask, request, Response
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI

__author__ = 'daniel'

# Configuration stuff
hostname = socket.gethostname()
port = 9013

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

diraddress = "http://localhost:9000"

# Datos del Agente
AgenteDevolucion = Agent('AgenteDevolucion',
                       agn.AgenteDevolucion,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))


app = Flask(__name__)


def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt

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
    Entrypoint for communication
    """

    message = request.args['content']
    gm = Graph()
    gm.parse(data=message, format='xml') 
    msgdic = get_message_properties(gm)

    gr = None

    if msgdic is None:
        # Si no es, respondemos que no hemos entendido el mensaje
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteDevolucion.uri, msgcnt=get_count())
    else:
        # Obtenemos la performativa
        if msgdic['performative'] != ACL.request:
            # Si no es un request, respondemos que no hemos entendido el mensaje
            gr = build_message(Graph(),
                               ACL['not-understood'],
                               sender=AgenteDevolucion.uri,
                               msgcnt=get_count())
        else:
            # Extraemos el objeto del contenido que ha de ser una accion de la ontologia de acciones del agente
            # de registro
            receiver_uri = msgdic['receiver']
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=receiver_uri, predicate=RDF.type)

            if accion == ECSDI.PeticionDevolucion:
                #PeticionCompra recibo del asistente virtual
                #checkear con AgenteCompra cuando se compro
                user_id = gm.value(subject=receiver_uri, predicate=ECSDI.id)
                product_id = gm.value(subject=receiver_uri, predicate=ECSDI.id)

                receiver_uri = agn.AgenteCompra
                receiver_address = get_agent("COMPRA") 

                if receiver_address != "NOT FOUND":
                    content_graph = Graph()
                    content_graph.add((receiver_uri, RDF.type, ECSDI.PeticionDevolucion))
                    content_graph.add((receiver_uri, ECSDI.id_usuario, Literal(user_id)))
                    content_graph.add((receiver_uri, ECSDI.id, Literal(product_id)))
                        
                    msg_graph = build_message(
                        gmess=content_graph,
                        perf=ACL.request,
                        sender=AgenteDevolucion.uri,
                        receiver=receiver_uri,
                        msgcnt=mss_cnt
                    )
                    response_graph = send_message(gmess=msg_graph, address=receiver_address)
                    mss_cnt += 1
                    return Response(status=200)
                
                else:
                    return Response(status=404)

                   
            elif accion == ECSDI.RespuestaDevolucion:
                #comunicar respuest al asisten viertual
                
                respuesta = gm.value(subject=receiver_uri, predicate=ECSDI.acceptado)

                if respuesta == True:
                    buyer_id = gm.value(subject=receiver_uri, predicate=ECSDI.id_usuario)
                    price = gm.value(subject=receiver_uri, predicate=ECSDI.precio)

                    receiver_uri = agn.AgenteContabilidad
                    receiver_address = get_agent("CONTABILIDAD") 

                    if receiver_address != "NOT FOUND":
                        content_graph = Graph()
                        content_graph.add((receiver_uri, RDF.type, ECSDI.RespuestaDevolucion))
                        content_graph.add((receiver_uri, ECSDI.precio, Literal(price)))
                        content_graph.add((receiver_uri, ECSDI.id_usuario, Literal(buyer_id)))

                        #comnunicar al agente virtual que se ha aceptado
                        msg_graph = build_message(
                            gmess=content_graph,
                            perf=ACL.request,
                            sender=AgenteDevolucion.uri,
                            receiver=receiver_uri,
                            msgcnt=mss_cnt
                        )
                        response_graph = send_message(gmess=msg_graph, address=receiver_address)
                        mss_cnt += 1
                        return Response(status=200)
                    
                    else:
                        return Response(status=404)

                else: 
                    print("fewf")
                    #comnunicar al agente virtual que se ha aceptado
                
            # No habia ninguna accion en el mensaje
            else:
                gr = build_message(Graph(),
                            ACL['not-understood'],
                            sender=AgenteDevolucion.uri,
                            msgcnt=get_count())
            
    return Response(status=400)



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

if __name__ == '__main__':

    hostaddr = hostname = socket.gethostname()
    AgenteDevolucionAdd = f'http://{hostaddr}:{port}'
    AgenteDevolucionId = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{AgenteDevolucionId},DEVOLUCION,{AgenteDevolucionAdd}'

    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass
    print('DS Hostname =', hostaddr)

    if 'OK' in resp:
        print(f'DEVOLUCION {AgenteDevolucionId} successfully registered')
        
        # Buscamos el logger si existe en el registro
        loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in loggeradd:
            logger = loggeradd[4:]

        mess = 'SEARCH|COMPRA,1'  
        response = requests.get(f"{diraddress}/message", params={'message': mess})
        print(response.text)

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteDevolucionId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')

    print('The End')
