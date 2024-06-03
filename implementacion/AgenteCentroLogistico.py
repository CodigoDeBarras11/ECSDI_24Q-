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
import datetime
import schedule
import time
import requests
sys.path.append(path.dirname(getcwd()))
from multiprocessing import Process, Queue
import socket
import argparse
from AgentUtil.Logging import config_logger

from rdflib import Namespace, Graph, RDF, Literal, BNode
from flask import Flask, request
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI
from rdflib.namespace import XSD
from rdflib.collection import Collection

__author__ = 'javier'

# Configuration stuff
hostname = socket.gethostname()
port = 9015

#Peso maximo de un lote
MaxPesoLote = 100

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgenteCentroLogistico = Agent('AgenteCentroLogistico',
                       agn.AgenteCentroLogistico,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
g = Graph()

cola1 = Queue()


app = Flask(__name__)

def get_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt

def schedule_tasks():
    # Programar la tarea diaria a las 8:00 AM
    schedule.every().day.at("08:00").do(send_info_to_accounting)

    # Verificar si es la hora programada
    while True:
        now = time.localtime()
        if now.tm_hour == 8 and now.tm_min == 0 and now.tm_sec == 0:
            # Es la hora programada, ejecutar la tarea
            schedule.run_pending()
        time.sleep(60)

def send_info_to_accounting():
    g = Graph()
    g.parse("bd/pedidos.ttl", format="turtle")

    now = datetime.datetime.now().date()

    current_date = f"{now.tm_year}-{now.tm_mon}-{now.tm_mday}"
    query = """
    PREFIX ECSDI: <urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8>
    SELECT ?compra_id ?productos_enviados
    WHERE {
        ?pedido a ECSDI:Pedido ;
                ECSDI:compra_a_enviar ?compra ;
                ECSDI:productos_enviados ?productos_enviados ;
                ECSDI:fechaEntrega ?fecha_entrega .
        BIND(STRAFTER(str(?compra), "Compra/") as ?compra_id)
        FILTER (?fecha_entrega = "%s"^^xsd:date)
    }
    """ % now

    results = g.query(query)

    compra_ids = [str(row[0]) for row in results]
    productos_enviados = [str(row[1]) for row in results]
    r_gmess = Graph()

    for compra_id, productos in zip(compra_ids, productos_enviados):
        compra_uri = ECSDI[compra_id]
        productos_list = productos.split(',')
        for producto_uri in productos_list:
            r_gmess.add((compra_uri, ECSDI.Producto_Enviado, URIRef(producto_uri.strip())))


    r_graph = build_message(
        gmess=r_gmess,
        perf=ACL.agree,
        sender=AgenteCentroLogistico.uri,
        receiver=agn.AgenteCompra,
        content=ECSDI.Producto_Enviado,
        msgcnt=mss_cnt
    )
    mss_cnt += 1
    return r_graph.serialize(format='xml')


def escribirAPedido(centroLogistico, compra, productos, prioridadEntrega, latitud, longitud, peso):
    # Crear el grafo y namespaces
    
    g = Graph()
    file_path = "bd/pedido.ttl"
    if not os.path.exists(file_path):
        g.add((agn.last_id, XSD.positiveInteger, Literal(0)))
        os.makedirs(os.path.dirname(file_path), exist_ok=True) 
        g.serialize(file_path, format="turtle")

    g.parse("bd/pedido.ttl", format="turtle")
    g.bind('ECSDI', ECSDI)
    last_id = g.value(subject=agn.last_id, predicate=XSD.positiveInteger)
    
    
    
    
    #g = Graph()
    #ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")
    #AGN = Namespace("http://www.agentes.org#")
    #g.bind("ECSDI", ECSDI)

    # Cargar el grafo existente desde el archivo si existe
    #try:
        #g.parse("pedido.ttl", format="turtle")
    #except FileNotFoundError:
        #pass

    # Leer el valor actual de searchid
    #searchid_value = g.value(subject=AGN.searchid, predicate=XSD.positiveInteger)
    #searchid = int(searchid_value) if searchid_value else 0

    # Incrementar el valor de searchid
    last_id += 1

    # Actualizar el valor en el grafo
    g.set((agn.last_id, XSD.positiveInteger, Literal(last_id)))

    # Definir la URI de tu pedido
    #pedido_uri = ECSDI[f'Pedido/{last_id}']
    pedido_uri = ECSDI.Pedido +'/'+ str(last_id+1)

    # Cargar el grafo del centro logístico
    centro_logistico_grafo = Graph()
    centro_logistico_grafo.parse("centros_logisticos.ttl", format="turtle")

    # Verificar productos en el centro logístico
    productos_centro_logistico = centro_logistico_grafo.objects(subject=centroLogistico, predicate=ECSDI.productos)

    # Crear un set de productos disponibles en el centro logístico
    productos_disponibles = set(productos_centro_logistico)
    productos_agregados = []
    pesos_agregados = []
    # Añadir productos verificados al grafo del pedido
    for producto in productos:
        if producto in productos_disponibles:
            g.add((pedido_uri, ECSDI.productos_enviados, producto))
            productos_agregados.append(producto)
            pesos_agregados.append(peso)
    
    if productos_agregados:
        # Añadir triples al grafo para el pedido
        g.add((pedido_uri, RDF.type, ECSDI.Pedido))
        g.add((pedido_uri, ECSDI.id, Literal(last_id, datatype=XSD.integer)))
        g.add((pedido_uri, ECSDI.latitud, Literal(latitud, datatype=XSD.decimal)))
        g.add((pedido_uri, ECSDI.longitud, Literal(longitud, datatype=XSD.decimal)))
        g.add((pedido_uri, ECSDI.prioridadEntrega, Literal(prioridadEntrega, datatype=XSD.integer)))
        fecha_entrega = datetime.datetime.now() + datetime.timedelta(days=prioridadEntrega)
        g.add((pedido_uri, ECSDI.fechaEntrega, Literal(fecha_entrega.isoformat(), datatype=XSD.dateTime)))
        g.add((pedido_uri, ECSDI.compra_a_enviar, Literal(compra, datatype=XSD.string)))
        g.add((pedido_uri, ECSDI.centrologistico, Literal(centroLogistico, datatype=XSD.string)))

    # Serializar el grafo en formato Turtle y guardarlo en un archivo
    with open("bd/pedido.ttl", "w") as f:
        f.write(g.serialize(format="turtle"))
    peso = pesos_agregados
    return productos_agregados


def negociarTransportista(fecha_entrega_dt):
    g = Graph()
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")
    AGN = Namespace("http://www.agentes.org#")

    try:
        g.parse("transportistas.ttl", format="turtle")
    except FileNotFoundError:
        raise Exception("El archivo transportistas.ttl no existe.")

    transportistas = []
    for s in g.subjects(RDF.type, ECSDI.Transportista):
        transportista_id = g.value(s, ECSDI.id)
        if transportista_id:
            transportistas.append((int(transportista_id), s))

    transportista_lotes = {transportista_uri: 0 for _, transportista_uri in transportistas}

    # Cargar el archivo de lotes para contar los lotes asignados a cada transportista en la fecha de entrega
    lote_g = Graph()
    try:
        lote_g.parse("lote.ttl", format="turtle")
    except FileNotFoundError:
        pass  # Si el archivo no existe, continuamos con un grafo vacío

    for s in lote_g.subjects(RDF.type, ECSDI.Lote):
        lote_fecha_entrega = lote_g.value(s, ECSDI.fechahora)
        if lote_fecha_entrega and datetime.datetime.fromisoformat(str(lote_fecha_entrega)) == fecha_entrega_dt:
            transportista_uri = lote_g.value(s, ECSDI.transportista)
            if transportista_uri in transportista_lotes:
                transportista_lotes[transportista_uri] += 1

    # Seleccionar el transportista con menos lotes asignados en esa fecha
    transportista_seleccionado = min(transportista_lotes, key=transportista_lotes.get)

    return transportista_seleccionado.split('/')[-1]  # Devuelve solo el ID del transportista



def escribirALote(centroLogID, prioridadEntrega, productos, pesos):
        #crear pedido
    g = Graph()
    # Definir el namespace de tu ontología ECSDI
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8")
    g.bind("ECSDI", ECSDI)


    AGN = Namespace("http://www.agentes.org#")

    # Cargar el grafo existente desde el archivo si existe
    try:
        g.parse("lote.ttl", format="turtle")
    except FileNotFoundError:
        pass  # Si el archivo no existe, continuamos con un grafo vacío

    # Leer el valor actual de searchid
    searchid_value = g.value(subject=AGN.searchid, predicate=XSD.positiveInteger)
    if searchid_value is None:
        searchid = 0
    else:
        searchid = int(searchid_value)

    # Incrementar el valor de searchid
    searchid += 1

    # Actualizar el valor en el grafo
    g.set((AGN.searchid, XSD.positiveInteger, Literal(searchid)))

    lote_uri = ECSDI[f'Lote/{searchid}']
    fecha_entrega = datetime.datetime.now() + datetime.timedelta(days=int(prioridadEntrega))

    # Añadir triples al grafo
    g.add((lote_uri, RDF.type, ECSDI.Lote))
    g.add((lote_uri, ECSDI.id, Literal(searchid, datatype=XSD.integer)))  
    g.add((lote_uri, ECSDI.fechahora, Literal(fecha_entrega.isoformat(), datatype=XSD.dateTime))) 

    # Asignar id de centroLog, Transp, Productos
    centroLog_uri = ECSDI[f'CentroLogistico/{centroLogID}']
    g.add((lote_uri, ECSDI.centro_logistico, centroLog_uri))
    transpID = negociarTransportista()
    transp_uri = ECSDI[f'Transportista/{transpID}']
    g.add((lote_uri, ECSDI.transportista, transp_uri))
    #Un for para añadir todos los productos al lote
    peso_actual = 0
    while productos and pesos:
        producto_uri = URIRef(productos[0])
        producto_peso = float(pesos[0])
        if peso_actual + producto_peso <= MaxPesoLote:
            peso_actual += producto_peso
            g.add((lote_uri, ECSDI.productos, producto_uri))
            productos.pop(0)
            pesos.pop(0)
        else:
            # Si el producto no cabe en el lote actual, guardamos el lote actual y creamos uno nuevo
            searchid += 1
            g.set((AGN.searchid, XSD.positiveInteger, Literal(searchid)))
            lote_uri = ECSDI[f'Lote/{searchid}']
            g.add((lote_uri, RDF.type, ECSDI.Lote))
            g.add((lote_uri, ECSDI.id, Literal(searchid, datatype=XSD.integer)))
            g.add((lote_uri, ECSDI.fechahora, Literal(fecha_entrega.isoformat(), datatype=XSD.dateTime)))
            g.add((lote_uri, ECSDI.centro_logistico, centroLog_uri))
            peso_actual = producto_peso
            g.add((lote_uri, ECSDI.productos, producto_uri))
            productos.pop(0)
            pesos.pop(0)

    temp_ttl = g.serialize(format="turtle")

    # Reemplazar la línea del searchid con el formato deseado
    temp_ttl_lines = temp_ttl.split('\n')
    with open("lote.ttl", "r") as f:
        original_lines = f.readlines()

    for i, line in enumerate(original_lines):
        if "AGN:searchid" in line:
            original_lines[i] = f'<http://www.agentes.org#searchid> xsd:positiveInteger {searchid} .\n'
            break
    else:
        # Si no se encuentra, añadir al final
        original_lines.append(f'<http://www.agentes.org#searchid> xsd:positiveInteger {searchid} .\n')


    # Serializar el grafo en formato Turtle y guardarlo en un archivo
    with open("lote.ttl", "w") as f:
        f.write(g.serialize(format="turtle"))

def prepararLotes(centroLogID, prioridadEntrega, productos, pesos):
    #consultar MaxPesoLote
    #leer el último lote con la fecha de entrega de no lleno a ver si cabe más productos.
    #en caso que faltan productos para poner a lotes, crear un lote nuevo.
    g = Graph()
    ECSDI = Namespace("urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8#")
    AGN = Namespace("http://www.agentes.org#")

    g.parse("lote.ttl", format="turtle")

    fecha_hoy = datetime.datetime.now()
    fecha_entrega = fecha_hoy + datetime.timedelta(days=int(prioridadEntrega))
    fecha_entrega_dt = fecha_entrega.isoformat()

    lotes = []
    for s in g.subjects(RDF.type, ECSDI.Lote):
        lote_id = g.value(s, ECSDI.id)
        fechahora = g.value(s, ECSDI.fechahora)
        peso = g.value(s, ECSDI.peso)
        if lote_id and fechahora and peso:
            lotes.append((int(lote_id), str(fechahora), float(peso), s))

    lotes.sort(reverse=True, key=lambda x: x[0])

    # Buscar lotes que cumplan con las condiciones
    for lote_id, lote_fechahora, lote_peso, lote_uri in lotes:
        if lote_fechahora == fecha_entrega_dt:
            while productos and pesos and lote_peso < MaxPesoLote:
                producto_uri = URIRef(productos[0])
                producto_peso = float(pesos[0])

                if lote_peso + producto_peso <= MaxPesoLote:
                    g.add((lote_uri, ECSDI.productos, producto_uri))
                    lote_peso += producto_peso
                    productos.pop(0)
                    pesos.pop(0)
                    if lote_peso == MaxPesoLote:
                        break
                else:
                    break
            break


    if productos:
        escribirALote(centroLogID, prioridadEntrega, productos, pesos)
                   
                   
                   #el primero producto que se puede añadir al lote se añade
                   #hasta que el lote ya no se puede añadir más
                   #crear un nuevo lote 

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
        gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCentroLogistico.uri, msgcnt=get_count())
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
                gr = build_message(Graph(), ACL['not-understood'], sender=AgenteCentroLogistico.uri, msgcnt=get_count())
            
            else:
                content = msgdic['content'] 
                # Averiguamos el tipo de la accion
                accion = gm.value(subject=content, predicate=RDF.type)

                if accion == ECSDI.ProductosEnviar: 
                    r_gmess = Graph()
              
                    print(message)

                    centroLogistico = gm.value(subject=content, predicate=ECSDI.CentroLogistico)
                    compra = gm.value(subject=content, predicate=ECSDI.Compra)
                    productos = gm.value(subject=content, predicate=ECSDI.productos)
                    prioridadEntrega = gm.value(subject=content, predicate=ECSDI.prioridadEntrega)
                    peso = gm.value(subject=content, predicate=ECSDI.peso)
                    precio = gm.value(subject=content, predicate=ECSDI.precio)
                    latitud = gm.value(subject=content, predicate=ECSDI.latitud)
                    longitud = gm.value(subject=content, predicate=ECSDI.longitud)
                    print("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")
                    productos_entregables = escribirAPedido(centroLogistico, compra, productos, prioridadEntrega, latitud, longitud, peso)
                    print("DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD")
                    prepararLotes(centroLogistico, prioridadEntrega, productos, peso)

                    productos_node = BNode()
                    Collection(r_gmess, productos_node, productos_entregables)
                    r_gmess.add((agn.ProductosEntregables, ECSDI.productos, productos_node))
                    r_graph = build_message(
                        gmess=r_gmess,
                        perf=ACL.agree, 
                        sender=AgenteCentroLogistico.uri,
                        receiver=agn.AgenteCompra,
                        content=agn.ProductosEntregables,
                        msgcnt=mss_cnt
                    )
                    
                    mss_cnt += 1
                    return r_graph.serialize(format='xml')
                    
                
    return "p"



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
    hostaddr = hostname = socket.gethostname()
    AgenteCentroLogisticoAdd = f'http://{hostaddr}:{port}'
    AgenteCentroLogisticoId = hostaddr.split('.')[0] + '-' + str(port)
    mess = f'REGISTER|{AgenteCentroLogisticoId},CENTROLOGISTICO,{AgenteCentroLogisticoAdd}'

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
        print(f'CENTROLOGISTICO {AgenteCentroLogisticoId} successfully registered')
        
        # Buscamos el logger si existe en el registro
        loggeradd = requests.get(diraddress + '/message', params={'message': 'SEARCH|LOGGER'}).text
        if 'OK' in loggeradd:
            logger = loggeradd[4:]

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteCentroLogisticoId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')