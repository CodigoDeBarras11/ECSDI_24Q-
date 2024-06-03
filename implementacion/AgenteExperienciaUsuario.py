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
import os
import schedule
import time
import requests
import random
sys.path.append(path.dirname(getcwd()))
from multiprocessing import Process, Queue
import socket
import argparse
from AgentUtil.Logging import config_logger

from rdflib import XSD, Namespace, Graph, RDF, Literal, BNode
from flask import Flask, render_template_string, request
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI
from datetime import datetime, timedelta
from rdflib.collection import Collection

__author__ = 'javier'

# Configuration stuff
hostname = socket.gethostname()
port = 9016

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteExperiencia = Agent('AgenteExperiencia',
                       agn.AgenteExperiencia,
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

def get_agent(agente):
    mess = f'SEARCH|{agente},1'  
    response = requests.get(f"{diraddress}/message", params={'message': mess})
    response = response.text.split(" ")
    if "OK" in response[0]:
        return f'{response[1]}/comm'
    else:
        return "NOT FOUND"

def schedule_tasks():
    # Programar la tarea diaria a las 8:00 AM
    schedule.every().day.at("22:09").do(pedir_feedback_a_asistente)
    #schedule.every().day.at("09:00").do(recomendar_productos_a_asistente)

    # Verificar si es la hora programada
    while True:
        now = time.localtime()
        if now.tm_hour == 8 and now.tm_min == 0 and now.tm_sec == 0:
            # Es la hora programada, ejecutar la tarea
            schedule.run_pending()
        time.sleep(60)

def pedir_feedback_a_asistente():
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")

    g = Graph()
    g.parse("bd/compra.ttl", format="ttl")

    fecha_objetivo = datetime.now().date()
    compras_to_send = []

    for compra in g.subjects(RDF.type, ECSDI.Compra):
        fecha_literal = g.value(compra, ECSDI.fechaHora)
        if fecha_literal:
            fecha_compra = datetime.strptime(fecha_literal, "%Y-%m-%d").date()
            if fecha_compra + timedelta(days=3) == fecha_objetivo:
                compras_to_send.append(compra) 

    ng = Graph()
    ng.add((agn.PeticionFeedback, RDF.type, ECSDI.PeticionFeedback))
    for compra in compras_to_send:
        cliente_uri = g.value(compra, ECSDI.comprado_por)
        producto_uri = g.value(compra, ECSDI.Producto)
        ng.add((agn.PeticionFeedback, ECSDI.Cliente, cliente_uri))
        ng.add((agn.PeticionFeedback, ECSDI.Producto, producto_uri))

    if compras_to_send:
        receiver_address = get_agent("ASSISTENTEUSUARIO")
        if receiver_address != "NOT FOUND":
            graph = build_message(
                gmess=ng,
                perf=ACL.request,
                sender=AgenteExperiencia.uri,
                receiver=agn.AssistenteUsuario,
                content=agn.PeticionFeedback,
                msgcnt=get_count()
            )

            response_graph = send_message(gmess=graph, address=receiver_address)


def recomendar_productos_a_asistente():
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")

    g = Graph()
    g.parse("busqueda.ttl", format="ttl")

    clientes_uris = set()

    for busqueda in g.subjects(RDF.type, ECSDI.Busqueda):
        cliente_uri = g.value(busqueda, ECSDI.buscado_por)
        if cliente_uri:
            clientes_uris.add(cliente_uri)

    max_peso = None
    max_precio = None
    min_precio = None
    min_peso = None
    tipoproducto = None

    for cliente_uri in clientes_uris:
        busquedas_cliente = list(g.subjects(ECSDI.buscado_por, cliente_uri))
        if busquedas_cliente:
            busqueda_aleatoria = random.choice(busquedas_cliente)
            # Obtener los valores de los atributos de la búsqueda aleatoria
            atributos_busqueda = {}
            for predicado, objeto in g.predicate_objects(busqueda_aleatoria):
                # Excluir los atributos 'id' y 'buscado_por'
                if str(predicado) != str(ECSDI.id) and str(predicado) != str(ECSDI.buscado_por):
                    # Guardar cada atributo en una variable separada
                    if str(predicado) == str(ECSDI.max_peso):
                        max_peso = objeto
                    elif str(predicado) == str(ECSDI.max_precio):
                        max_precio = objeto
                    elif str(predicado) == str(ECSDI.min_precio):
                        min_precio = objeto
                    elif str(predicado) == str(ECSDI.min_peso):
                        min_peso = objeto
                    elif str(predicado) == str(ECSDI.tipoproducto):
                        tipoproducto = objeto

                    ng = Graph()
                    ng.add((agn.ProductosRecomendados, RDF.type, ECSDI.ProductosRecomendados))
                    ng.add((agn.ProductosRecomendados, ECSDI.Cliente, cliente_uri))
                    if max_peso:
                        ng.add((agn.ProductosRecomendados, ECSDI.max_peso, max_peso))
                    if max_precio:
                        ng.add((agn.ProductosRecomendados, ECSDI.max_precio, max_precio))
                    if min_peso:
                        ng.add((agn.ProductosRecomendados, ECSDI.min_peso, min_peso))
                    if min_precio:
                        ng.add((agn.ProductosRecomendados, ECSDI.max_precio, max_precio))
                    if tipoproducto:
                        ng.add((agn.ProductosRecomendados, ECSDI.tipoproducto, tipoproducto))


                    receiver_address = get_agent("ASSISTENTEUSUARIO")
                    if receiver_address != "NOT FOUND":

                        graph = build_message(
                            gmess=ng,
                            perf=ACL.request,
                            sender=AgenteExperiencia.uri,
                            receiver=agn.AssistenteUsuario,
                            content=agn.ProductosRecomendados,
                            msgcnt=get_count()
                        )

                        response_graph = send_message(gmess=graph, address=receiver_address)
                


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
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteExperiencia.uri, msgcnt=get_count())
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
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteExperiencia.uri, msgcnt=get_count())
            
            else:
                info = msgdic['info'] 
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=info, predicate=RDF.type)

                if accion == ECSDI.PeticionFeedback:
                    valoraciones = gm.value(subject=info, predicate=ECSDI.valoracion)
                    productos = gm.value(subject=info, predicate=ECSDI.productos)
                    cliente = gm.value(subject=info, predicate=ECSDI.Cliente)
                    store_feedback(valoraciones, productos, cliente)
                
                

def store_feedback(valoraciones, productos, cliente):
    g = Graph()
    file_path = "bd/feedback.ttl"
    if not os.path.exists(file_path):
        g.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        g.serialize(file_path, format="turtle")

    g.parse("bd/feedback.ttl", format="turtle")
    g.bind('ECSDI', ECSDI)
    last_id = g.value(subject=agn.last_id, predicate=XSD.positiveInteger)
    last_id += 1

    # Actualizar el valor en el grafo

    for producto, valoracion in zip(productos, valoraciones):
        g.set((agn.last_id, XSD.positiveInteger, Literal(last_id)))
        feedback_uri = ECSDI.Feedback +'/'+ str(last_id+1)
        g.add((feedback_uri, RDF.type, ECSDI.Feedback))
        g.add((feedback_uri, ECSDI.valorado_por, cliente))
        g.add((feedback_uri, ECSDI.feedback_de, producto))
        g.add((feedback_uri, ECSDI.valoracion, valoracion))
        last_id += 1
    with open("bd/feecback.ttl", "w") as f:
        f.write(g.serialize(format="turtle"))



"""
@app.route("/request_feedback")
def request_feedback():
    user = request.args.get('user') #obtener el usuario
    products = get_user_products(user) #obtener los productos comprados por el usuario en x días y no tienen feedback
    if not products:
        return "No products found for user."

    feedback_form = generate_feedback_form(products)
    return render_template_string(feedback_form)

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    feedback_data = request.form
    store_feedback(feedback_data)
    return "Thank you for your feedback!"

def get_user_products(user):
    purchases_graph = Graph()
    if path.exists("compra.ttl"):
        purchases_graph.parse("compra.ttl", format="turtle")

    query = 
    #PREFIX ecsdi: <http://www.agentes.org#>
    #SELECT ?product ?name
    #WHERE {
    #    ?purchase ecsdi:comprado_por < + user + > .
    #    ?purchase ecsdi:contieneProducto ?product .
    #    ?product ecsdi:nombre ?name .
    #}
    
    results = purchases_graph.query(query)
    

    products = []
    for row in results:
        product = {
            "uri": str(row.product),
            "name": str(row.name)
        }
        products.append(product)
    return products

def generate_feedback_form(products):
    form_html = 
    #<h1>Please give Feedback on the following products</h1>
    #<form action="/submit_feedback" method="POST">
    
    #products = [{"name": "iphone", "uri": "ecsdi"}]
    for product in products:
        form_html += 
        <h4>{}
        <input type="hidden" name="product_uri" value="{}">

        <input type="number" id="rating_{}" name="rating_{}" min="1" max="5" required></h4><br>
        .format(product["name"], product["uri"], product["uri"], product["uri"], product["uri"])

    form_html += 
        <input type="submit" value="Submit Feedback">
    </form>
    
    #<label for="rating_{}">Rating (1-5):</label>
    return form_html

def store_feedback(feedback_data):
    feedback_graph = Graph()
    if path.exists("feedback.ttl"):
        feedback_graph.parse("feedback.ttl", format="turtle")
    
    feedback_graph.bind('ecsdi', ECSDI)
    
    for key, value in feedback_data.items():
        if key.startswith("rating_"):
            product_uri = key.split("rating_")[1]
            rating = int(value)
            feedback_graph.add((ECSDI[product_uri], ECSDI.rating, Literal(rating, datatype=XSD.integer)))

    feedback_graph.serialize("feedback.ttl", format="turtle")

@app.route("/")
def index():
    return render_template_string(generate_feedback_form())
@app.route("/Stop")
def stop():
    tidyup()
    shutdown_server()
    return "Stopping Server"
"""


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
    hostaddr = hostname = socket.gethostname()
    AgenteExperienciaAdd = f'http://{hostaddr}:{port}'
    AgenteExperienciaId = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{AgenteExperienciaId},CENTROLOGISTICO,{AgenteExperienciaAdd}'

    diraddress = "http://"+hostname+":9000"
    done = False
    while not done:
        try:
            resp = requests.get(diraddress + '/message', params={'message': mess}).text
            done = True
        except ConnectionError:
            pass
    print('DS Hostname =', hostaddr)

    if 'OK' in resp:
        print(f'Experiencia {AgenteExperienciaId} successfully registered')
        
        # Buscamos el logger si existe en el registro
        loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in loggeradd:
            logger = loggeradd[4:]

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteExperienciaId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')