from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# --- Intenciones de Usuario ---
saludos = ["hola", "buenas", "qué tal", "hey", "saludos"]
productos_frases = [
    "componentes", "productos", "recomiéndame algo", "hardware", "accesorios", "recomendaciones",
    "recomendar producto", "recomiéndame un producto", "dame una recomendación", "muéstrame productos"
]
pedidos_frases = ["mi pedido", "mi orden", "mi compra", "dónde está mi pedido", "estado de mi orden"]
soportes_frases = ["soporte", "ayuda", "problema técnico", "mi pc no prende", "pantalla azul"]
funciones_frases = ["funciones", "qué puedes hacer", "qué haces", "cuáles son tus funciones", "menú de opciones"]
busqueda_frases = ["busca", "búscame", "encuentra", "tienes", "precio de", "cotiza", "buscar producto", "quiero buscar"]
devolucion_frases = ["devolucion", "quiero devolver", "iniciar una devolución", "mi producto llegó dañado", "devolver pedido"]
notificacion_stock_frases = ["aví­same cuando llegue", "notifí­came del stock", "cuando vuelve a estar disponible"]
comparar_frases = [
    "compara", "cuál es mejor", "diferencia entre", 
    "compara a con b", "comparar", "comparativa", "vs",
    "compara este producto con este otro"
]
actualizar_direccion_frases = ["actualizar mi dirección", "cambiar dirección de enví­o", "modificar dirección"]

# --- Intenciones de Administrador ---
stats_admin_frases = ["estadí­sticas", "stats", "resumen", "reporte", "cómo van las ventas", "total usuarios", "reporte de ventas hoy"]
stock_admin_frases = ["stock de", "cuánto stock queda de", "inventario de", "revisar stock", "consultar stock"]
buscar_cliente_frases = ["busca al cliente", "datos de cliente", "info de", "quién es el cliente", "encuentra a", "cliente"]
cambiar_estado_pedido_frases = ["cambia el estado del pedido", "actualiza el pedido", "marcar como enviado"]
analisis_frases = ["análisis", "analisis", "análisis de crecimiento", "qué categorí­a vende más", "clientes inactivos"]
prediccion_frases = ["predice el stock", "predicción de", "pronostica", "cuánto se venderá de", "demanda de", "predecir stock"]

# ---- Intenciones Invitados ----
horarios_frases = ["horarios de atención", "cuál es su horario", "a qué hora abren", "atienden los sábados", "horario"]
pagos_frases = ["métodos de pago", "cómo puedo pagar", "aceptan tarjeta", "se puede pagar con transferencia", "formas de pago"]

# ---- Intenciones Vendedor (NUEVO) ----
exportar_frases = ["exportar ventas", "descargar ventas", "dame un excel con mis ventas", "generar excel", "ventas en excel", "reporte excel"]

# Combinamos todas las frases e intenciones
frases = (saludos + productos_frases + pedidos_frases + soportes_frases + funciones_frases + busqueda_frases +
          devolucion_frases + notificacion_stock_frases + comparar_frases + actualizar_direccion_frases +
          horarios_frases + pagos_frases +
          stats_admin_frases + stock_admin_frases + buscar_cliente_frases + cambiar_estado_pedido_frases + analisis_frases +
          prediccion_frases + exportar_frases)

intenciones = (
    ["saludo"] * len(saludos) + ["producto"] * len(productos_frases) + ["pedido"] * len(pedidos_frases) +
    ["soporte"] * len(soportes_frases) + ["funciones"] * len(funciones_frases) + ["busqueda_producto"] * len(busqueda_frases) +
    ["solicitar_devolucion"] * len(devolucion_frases) + ["solicitar_notificacion"] * len(notificacion_stock_frases) +
    ["comparar_productos"] * len(comparar_frases) + ["actualizar_direccion"] * len(actualizar_direccion_frases) +
    ["horarios"] * len(horarios_frases) + ["pagos"] * len(pagos_frases) +
    ["stats_admin"] * len(stats_admin_frases) + ["stock_admin"] * len(stock_admin_frases) +
    ["buscar_cliente_admin"] * len(buscar_cliente_frases) + ["cambiar_estado_pedido"] * len(cambiar_estado_pedido_frases) +
    ["analisis_admin"] * len(analisis_frases) +
    ["prediccion_stock"] * len(prediccion_frases) +
    ["exportar_ventas"] * len(exportar_frases)
)

# Inicializar y entrenar el modelo al cargar el módulo
vectorizer = CountVectorizer()
X = vectorizer.fit_transform(frases)
modelo = MultinomialNB()
modelo.fit(X, intenciones)

def clasificar_intencion(mensaje):
    """
    Clasifica el mensaje del usuario en una de las intenciones conocidas.
    """
    X_new = vectorizer.transform([mensaje])
    return modelo.predict(X_new)[0]
