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
port = 9013

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentePersonal = Agent('AgenteSimple',
                       agn.AgenteSimple,
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


@app.route("/comm")
def comunicacion():
    """
    Entrypoint for communication
    """
    global dsgraph
    global mss_cnt


    message = request.args.get('content', '')  #
    print(message)

    return "p"

@app.route("/request_feedback")
def request_feedback():
    user = //request.args.get('user') obtener el usuario
    products = //get_user_products(user) obtener los productos comprados por el usuario en x días y no tienen feedback
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
    compra_graph = Graph()
    if path.exists("compra.ttl"):
        purchases_graph.parse("compra.ttl", format="turtle")

    query = """
    PREFIX ecsdi: <http://www.agentes.org#>
    SELECT ?product ?name
    WHERE {
        ?purchase ecsdi:comprado_por <""" + user + """> .
        ?purchase ecsdi:contieneProducto ?product .
        ?product ecsdi:nombre ?name .
    }
    """
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
    form_html = """
    <h1>Product Feedback</h1>
    <form action="/submit_feedback" method="POST">
    """
    for product in products:
        form_html += """
        <h3>{}</h3>
        <input type="hidden" name="product_uri" value="{}">
        <label for="rating_{}">Rating (1-5):</label>
        <input type="number" id="rating_{}" name="rating_{}" min="1" max="5" required><br>
        """.format(product["name"], product["uri"], product["uri"], product["uri"], product["uri"])

    form_html += """
        <input type="submit" value="Submit Feedback">
    </form>
    """
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
