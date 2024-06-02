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

from rdflib import Namespace, Graph, RDF, Literal, XSD, BNode
from flask import Flask, request, render_template_string, Response
from AgentUtil.FlaskServer import shutdown_server
from AgentUtil.Agent import Agent
from AgentUtil.Util import gethostname
from AgentUtil.ACLMessages import *
from docs.ecsdi import ECSDI
from datetime import datetime, timedelta
import math
import base64
import argparse
from rdflib.collection import Collection

__author__ = 'Pepe'

# Configuration stuff
hostname = socket.gethostname()
port = 9011

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

def check_date(fechas, precios, vendedores, sujetos):
    for fecha, precio, vendedor, sujeto in zip(fechas, precios, vendedores, sujetos):
        if str(fecha) != "None":
            fecha_time = datetime.strptime(fecha, '%d/%m/%Y')
            hoy = datetime.today()
            diferencia = hoy - fecha_time
            if diferencia.days <= 15: return True, precio, vendedor, sujeto
    return False, None, None, None


def responder_peticion_devolucion(comprador, producto):
    grafo_compras = Graph()
    grafo_compras.parse("bd/compras.ttl", format="turtle")
    fechas = []
    precios = []
    vendedores = []
    sujetos = []
    print(comprador)
    print(producto)
    for s, p, o in grafo_compras.triples((None, RDF.type, ECSDI.Compra)):
        comprado_por = grafo_compras.value(subject=s, predicate=ECSDI.comprado_por)
        producto_b = grafo_compras.value(subject=s, predicate=ECSDI.Producto)
        if (comprador == comprado_por and producto == producto_b):
            fecha = grafo_compras.value(subject=s, predicate=ECSDI.fechaHora)
            precio = grafo_compras.value(subject=s, predicate=ECSDI.precio)
            vendedor = grafo_compras.value(subject=s, predicate=ECSDI.vendido_por)
            devuelto = grafo_compras.value(subject=s, predicate=ECSDI.devuelta)
            if int(devuelto) == 0:
                fechas.append(str(fecha))
                precios.append(str(precio))
                vendedores.append(vendedor)
                sujetos.append(s)
    
    devolucion, precio, vendido_por, sujeto = check_date(fechas, precios, vendedores, sujetos)
    if devolucion == True:
        grafo_compras.set((sujeto, ECSDI.devuelta, Literal("1")))
        grafo_compras.serialize("bd/compras.ttl", format="turtle")

    return devolucion, precio, vendido_por

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

def registrar_compra(comprador, producto, precio, vendido_por, peso):
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
    grafo_compras.add((compra, ECSDI.comprado_por, comprador)) 
    grafo_compras.add((compra, ECSDI.Producto, producto))
    grafo_compras.add((compra, ECSDI.vendido_por, vendido_por))
    grafo_compras.add((compra, ECSDI.precio, Literal(str(precio))))
    grafo_compras.add((compra, ECSDI.peso, Literal(str(peso))))
    grafo_compras.add((compra, ECSDI.devuelta, Literal("0")))
    grafo_compras.add((compra, ECSDI.fechaHora, Literal(None)))
    grafo_compras.set((agn.last_id, XSD.positiveInteger, Literal(last_id+1)))
        
    grafo_compras.serialize("bd/compras.ttl", format="turtle")
    return compra
        

def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0

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


def enviar_productos(sujetos, precios, pesos, productos, lat_us, lon_us):
    grafo_centroLogisticos = Graph()
    try:
        grafo_centroLogisticos.parse("centros_logisticos.ttl", format="turtle")
    except Exception as e:
        print("Error parsing Turtle file")
    
    #print("------------")
    centros_ordenados = []
    for s, p, o in grafo_centroLogisticos.triples((None, RDF.type, ECSDI.CentroLogistico)):
        #print(s)
        latitud_cl = grafo_centroLogisticos.value(s, ECSDI.latitud)
        longitud_cl = grafo_centroLogisticos.value(s, ECSDI.longitud)
        distancia = haversine(float(latitud_cl), float(longitud_cl), float(lat_us), float(lon_us))
        centros_ordenados.append((s, distancia))

    #print(centros_ordenados)
    #print("---------------")
    centros_ordenados = sorted(centros_ordenados, key=lambda x: x[1])
    #print("---------------")
    #print(centros_ordenados)

    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    for centro_logistico in centros_ordenados:
        gmess = Graph()
        gmess.add((agn.CentrosLogisticos, RDF.type, ECSDI.ProductosEntregables))
        gmess.add((agn.CentrosLogisticos, ECSDI.CentroLogistico, centro_logistico[0]))

        productos_node = BNode()
        Collection(gmess, productos_node, productos)
        gmess.add((agn.CentrosLogisticos, ECSDI.productos, productos_node))

        sujetos_node = BNode()
        Collection(gmess, sujetos_node, sujetos)
        gmess.add((agn.CentrosLogisticos, ECSDI.Compra, sujetos_node))

        pesos_node = BNode()
        Collection(gmess, pesos_node, pesos)
        gmess.add((agn.CentrosLogisticos, ECSDI.peso, pesos_node))
        
        precios_node = BNode()
        Collection(gmess, precios_node, precios)
        gmess.add((agn.CentrosLogisticos, ECSDI.precio, precios_node))

        print("---------------")
        print(gmess.serialize(format='ttl'))
        print("---------------")
    
        receiver_uri = agn.AgenteCentroLogistico
        receiver_address = get_agent("")
        print(receiver_address)

        msg_graph = build_message(
            gmess=gmess,
            perf=ACL.request,
            sender=AgenteCompra.uri,
            receiver=receiver_uri,
            content=agn.CentrosLogisticos,
            msgcnt=mss_cnt
        )
        response_graph1 = send_message(gmess=msg_graph, address=receiver_address)
        
    print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    """for sujeto, precio, peso, producto in zip(sujetos, precios, pesos, productos):
        print("---------------")
        print(sujeto)
        print(precio)
        print(peso)
        print(producto)
        print("---------------")"""

@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    global dsGraph
    global mss_cnt

    message = request.args['content']
    print(message)
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
            #print(msgdic)
            receiver_uri = msgdic['content'] 
            #print(receiver_uri)
            # Averiguamos el tipo de la accion
            accion = gm.value(subject=receiver_uri, predicate=RDF.type)
            #print(accion)
            if accion == ECSDI.PeticionCompra:
                
                r_gmess = Graph()

                print(receiver_uri)
                print(message)
                comprado_por = gm.value(subject=receiver_uri, predicate=ECSDI.comprado_por)
                r_gmess.add((agn.peticionCompra, ECSDI.comprado_por, comprado_por))
                productos = set(gm.subjects(RDF.type, ECSDI.Producto))
                for producto in productos:
                    print("------------------------")
                    nombre = gm.value(subject=producto, predicate=ECSDI.nombre)
                    precio = gm.value(subject=producto, predicate=ECSDI.precio)
                    peso = gm.value(subject=producto, predicate=ECSDI.peso)
                    marca = gm.value(subject=producto, predicate=ECSDI.tieneMarca)
                    vendido_por = gm.value(subject=producto, predicate=ECSDI.vendido_por)
                    print(nombre)
                    print(precio)
                    print(peso)
                    print(marca)
                    print(vendido_por)
                    print("------------------------")   
                    print(comprado_por)
                    print(producto)
                    print("/////////")
                    compra = registrar_compra(comprado_por, producto, precio, vendido_por, peso)
                    print(compra)
                    r_gmess.add((compra, RDF.type, ECSDI.Compra))
                 
                r_graph = build_message(
                    gmess=r_gmess,
                    perf=ACL.agree,
                    sender=AgenteCompra.uri,
                    receiver=agn.AssistenteUsuario,
                    content=ECSDI.Compra_procesada,
                    msgcnt=mss_cnt
                )
                mss_cnt += 1
                return r_graph.serialize(format='xml')
            
         
            elif accion == ECSDI.InfoUsuarioEntrega:
                print("devolver InformacionProvisionalEntrega")
                
                #con los id de compra que recibo enviar informacion al centro logistic
                #que le toque enviar los productos, del mas cercano al usuario al mas lejano


                latitud = gm.value(subject=receiver_uri, predicate=ECSDI.latitud)
                longitud = gm.value(subject=receiver_uri, predicate=ECSDI.longitud)
                meotodo_de_pago = gm.value(subject=receiver_uri, predicate=ECSDI.metodoPago)
                prioridad_de_entrega = gm.value(subject=receiver_uri, predicate=ECSDI.prioridadEntrega)
                print(latitud)
                print(longitud)
                print(meotodo_de_pago)
                print(prioridad_de_entrega)
                print("-----------")
                grafo_compras = Graph()
                grafo_compras.parse("bd/compras.ttl", format="turtle")
                precio_total = 0
                fecha_de_entrega_provisional = datetime.today() + timedelta(days=int(prioridad_de_entrega))
                n_graph = Graph()#recorrer centros logisticos por cercania, iteras hasta que no me queden productos
                productos = []
                precios = []
                pesos = []
                sujetos = []
                for compra in gm.subjects(predicate=RDF.type, object=ECSDI.Compra):
                    print(compra)
                    for s, p, o in grafo_compras.triples((None, RDF.type, ECSDI.Compra)):
                        print(s)
                        if s == compra:
                            print("hola")
                            precio = grafo_compras.value(subject=s, predicate=ECSDI.precio)
                            peso = grafo_compras.value(subject=s, predicate=ECSDI.peso)
                            producto = grafo_compras.value(subject=s, predicate=ECSDI.Producto)
                            print(precio)
                            print(peso)
                            print(producto)
                            sujetos.append(s)
                            precios.append(precio)
                            pesos.append(peso)
                            productos.append(producto)
                            precio_total += float(precio)
                             
                print("-----------")
                print(precio_total)
                print(fecha_de_entrega_provisional)

                enviar_productos(sujetos, precios, pesos, productos, latitud, longitud)
                
                r_gmess = Graph()
                r_gmess.add((agn.InformacionProvisionalEntrega, RDF.type, ECSDI.InformacionProvisionalEntrega))
                r_gmess.add((agn.InformacionProvisionalEntrega, ECSDI.precio, Literal(precio_total)))
                r_gmess.add((agn.InformacionProvisionalEntrega, ECSDI.fechaHora, Literal(fecha_de_entrega_provisional)))

                r_graph = build_message(
                    gmess=r_gmess,
                    perf=ACL.agree,
                    sender=AgenteCompra.uri,
                    receiver=agn.AsistenteUsuario,
                    content=agn.InformacionProvisionalEntrega,
                    msgcnt=mss_cnt
                )

                return r_graph.serialize(format='xml')


            elif accion == ECSDI.ProductoEnviado:
                #se registra la fecha de compra y se cobra el producto al usuario
                compra_id = gm.value(subject=receiver_uri, predicate=ECSDI.Compra)
                fecha = gm.value(subject=receiver_uri, predicate=ECSDI.fechaHora)
                registrar_fecha_compra(compra_id, fecha)
                mss_cnt += 1
                return Response(status=200)


            elif accion == ECSDI.PeticionDevolucion:
                r_gmess = Graph()

                comprado_por = gm.value(subject=receiver_uri, predicate=ECSDI.comprado_por)
                producto = gm.value(subject=receiver_uri, predicate=ECSDI.productos)
                print(comprado_por)
                print(producto)
                devolucion, precio, vendido_por = responder_peticion_devolucion(comprado_por, producto)
                receiver_uri = agn.AgenteDevolucion
                if devolucion == True: 
                    r_gmess.add((receiver_uri, ECSDI.acceptado, Literal(1)))
                    r_gmess.add((receiver_uri, ECSDI.comprado_por, comprado_por))
                    r_gmess.add((receiver_uri, ECSDI.vendido_por, vendido_por))
                    r_gmess.add((receiver_uri, ECSDI.precio, Literal(precio)))
                else:
                    r_gmess.add((receiver_uri, ECSDI.acceptado, Literal(0)))
                
                r_graph = build_message(
                    gmess=r_gmess,
                    perf=ACL.agree,
                    sender=AgenteCompra.uri,
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

        #responder_peticion_devolucion()

        # Ponemos en marcha el servidor Flask
        app.run(host=hostname, port=port, debug=False, use_reloader=False)

        mess = f'UNREGISTER|{AgenteCompraId}'
        requests.get(diraddress + '/message', params={'message': mess})
    else:
        print('Unable to register')


    print('The End')
