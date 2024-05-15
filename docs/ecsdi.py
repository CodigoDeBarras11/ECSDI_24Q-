"""
.. module:: ecsdi

 Translated by owl2rdflib

 Translated to RDFlib from ontology urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8

 :Date 15/05/2024 18:18:03
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
        'InformacionTienda',
        'Lista_Productos',
        'Mensajes',
        'Pedido',
        'PedirInfoTienda',
        'PeticionBusqueda',
        'PeticionDevolucion',
        'PeticionFeedback',
        'PeticionRegistrarProducto',
        'PeticionTransporte',
        'PreguntaUsuarioInfoEntrega',
        'Producto',
        'ProductoCobrado',
        'ProductoEnviado',
        'ProductoReembolsado',
        'ProductoRegistrado',
        'ProductosComprar',
        'ProductosEntregables',
        'ProductosEnviar',
        'ProductosRecomendados',
        'RecordatorioOrganizarLotes',
        'RecordatorioPedirFeedback',
        'RecordatorioRecomendarProductos',
        'ReembolsarProductos',
        'RespuestaDevolucion',
        'RespuestaFeedback',
        'RespuestaTransporte',
        'Tienda',
        'Transaccion',
        'Transportista',
        'Usuario',
        'PeticionCompra',
        'Peticion_agente',

        # Object properties
        'buscado',
        'buscado_por',
        'compra_a_enviar',
        'destinatario',
        'emisor',
        'envio_devuelto',
        'feedback_de',
        'infoTienda',
        'info_entrega',
        'producto_devuelto',
        'producto_enviado',
        'productos_comprar',
        'valorada_por',
        'vendido_por',
        'productos',

        # Data properties
        'acceptado',
        'cantidadDinero',
        'descripcion',
        'direccion',
        'direccionEntrega',
        'entrega_delegada',
        'enviado',
        'fechaHora',
        'id',
        'id_usuario',
        'metodoDevolucion',
        'metodoPago',
        'motivo_devolucion',
        'nombre',
        'peso',
        'precio',
        'prioridadEntrega',
        'valoracion',
        'tieneMarca',
        'max_peso',
        'max_precio',
        'min_peso',
        'min_precio',
        'tipoproducto'

        # Named Individuals
    ]
)
