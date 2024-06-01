"""
.. module:: ecsdi

 Translated by owl2rdflib

 Translated to RDFlib from ontology urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8

 :Date 01/06/2024 13:25:42
"""
from rdflib import URIRef
from rdflib.namespace import ClosedNamespace

ECSDI =  ClosedNamespace(
    uri=URIRef('urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8'),
    terms=[
        # Classes
        'Busqueda',
        'CentroLogistico',
        'Cliente',
        'Compra',
        'Feedback',
        'InfoEnvio',
        'InfoUsuarioEntrega',
        'InformacionProvisionalEntrega',
        'Mensajes',
        'Pedido',
        'PeticionBusqueda',
        'PeticionDevolucion',
        'PeticionFeedback',
        'PeticionRegistrarProducto',
        'PeticionTransporte',
        'Producto',
        'ProductoEnviado',
        'ProductosEntregables',
        'ProductosEnviar',
        'ProductosRecomendados',
        'RecordatorioOrganizarLotes',
        'RecordatorioPedirFeedback',
        'RecordatorioRecomendarProductos',
        'RespuestaDevolucion',
        'RespuestaFeedback',
        'RespuestaTransporte',
        'Tienda',
        'Transaccion',
        'Transportista',
        'Usuario',
        'Compra_procesada',
        'Lote',
        'PeticionCompra',
        'Peticion_agente',
        'ResultadoBusqueda',

        # Object properties
        'buscado_por',
        'compra_a_enviar',
        'destinatario',
        'emisor',
        'feedback_de',
        'info_entrega',
        'valorada_por',
        'vendido_por',
        'centro_logistico',
        'comprado_por',
        'productos',
        'transportista',

        # Data properties
        'acceptado',
        'cantidadDinero',
        'entrega_delegada',
        'enviado',
        'fechaHora',
        'id',
        'latitud',
        'metodoDevolucion',
        'metodoPago',
        'nombre',
        'peso',
        'precio',
        'prioridadEntrega',
        'valoracion',
        'tieneMarca',
        'longitud',
        'max_peso',
        'max_precio',
        'min_peso',
        'min_precio',
        'tipoproducto'

        # Named Individuals
    ]
)