"""
.. module:: ecsdi

 Translated by owl2rdflib

 Translated to RDFlib from ontology urn:webprotege:ontology:ed5d344b-0a9b-49ed-9f57-1677bc1fcad8

 :Date 08/05/2024 11:08:34
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
        'CompraAceptada',
        'Devolucion',
        'Feedback',
        'InfoEnvio',
        'InfoUsuarioEntrega',
        'InformacionProvisionalEntrega',
        'InformacionTienda',
        'Lista_Productos',
        'Mensajes',
        'Pedido',
        'PedirInfoTienda',
        'PeticionDevolucion',
        'PeticionFeedback',
        'PeticionProductosComprar',
        'PeticionRegistrarProducto',
        'PeticionTransporte',
        'PreguntaUsuarioInfoEntrega',
        'Producto',
        'ProductoCobrado',
        'ProductoEnviado',
        'ProductoRecoger',
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
        'Stock',
        'Tienda',
        'Transaccion',
        'Transportista',
        'Usuario',
        'buscado',

        # Object properties
        'buscado',
        'buscado_por',
        'busqueda_comprada',
        'compra_a_enviar',
        'destinatario',
        'emisor',
        'envio_devuelto',
        'feedback_de',
        'infoTienda',
        'info_entrega',
        'producto_almacen',
        'producto_devuelto',
        'producto_enviado',
        'productos_comprar',
        'stock_de',
        'valorada_por',
        'vendido_por',

        # Data properties
        'acceptado',
        'cantidadDinero',
        'cantidadProducto',
        'caracteristicas',
        'descripcion',
        'direccion',
        'direccionEntrega',
        'entrega_delegada',
        'enviado',
        'fechaHora',
        'id',
        'id_busqueda',
        'id_usuario',
        'metodoDevolucion',
        'metodoPago',
        'motivo_devolucion',
        'nombre',
        'precio',
        'prioridadEntrega',
        'valoracion'

        # Named Individuals
    ]
)
