# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
from flask_cors import CORS
import random
import re
import os

# --- IMPORTACIONES DE MÓDULOS PROPIOS ---
from config import FLASK_DEBUG, BASE_DIR
import database as db
import nlp_engine as nlp

app = Flask(__name__, static_folder='static')
CORS(app)
app.json.ensure_ascii = False
app.config['JSON_AS_ASCII'] = False

# ======================================================================
# ENDPOINTS
# ======================================================================

@app.route("/predict_demand", methods=["POST"])
def predict_demand():
    data = request.json
    product_id = data.get("id_producto")
    if not product_id:
        return jsonify({"error": "Falta id_producto"}), 400

    result = db.get_prediction_data(product_id)
    
    if result["success"]:
        return jsonify(result)
    else:
        status_code = 404 if "Datos insuficientes" in result["error"] else 500
        return jsonify({"error": result["error"]}), status_code


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    mensaje = data.get("message", "").lower()
    permisos = data.get("permisos")
    id_usuario = data.get("userId")
    email_usuario = data.get("email_usuario", "") 
    nombre_usuario = data.get("nombre_usuario", "Invitado")
    
    # URL base
    base_url = "https://bitware.site:5000/"
    
    respuesta, productos_recomendados = "No te entendí.", []
    intencion = nlp.clasificar_intencion(mensaje)

    # =================================================================
    # 1. LÓGICA PARA ADMINISTRADORES ('A')
    # =================================================================
    if permisos == 'A':
        if intencion == "saludo":
            alerts = db.get_proactive_alerts()
            
            if alerts:
                frases_alerta = [
                    f"Hola, Admin **{nombre_usuario}**. Atención: {alerts}",
                    f"Bienvenido de nuevo. Tengo novedades importantes: {alerts}",
                    f"¡Hola! Antes de empezar, revisa esto: {alerts}"
                ]
                respuesta = random.choice(frases_alerta)
            else:
                frases_ok = [
                    f"Hola, Admin **{nombre_usuario}**. Todo el sistema opera al 100%.",
                    f"¡Bienvenido, **{nombre_usuario}**! No hay alertas pendientes por ahora."
                ]
                respuesta = random.choice(frases_ok)

        elif intencion == "prediccion_stock":
            match = re.search(r'(?:de|del)\s(.+)', mensaje)
            if not match: match = re.search(r'stock\s(.+)', mensaje)
            termino_busqueda = match.group(1).strip() if match else ""
            
            if not termino_busqueda:
                respuesta = "Claro, dime el nombre del producto que quieres predecir. Ej: 'Predice el stock de RTX 3060'"
            else:
                producto = db.find_product_id_by_name(termino_busqueda) 
                if not producto:
                    respuesta = f"No encontré el producto '{termino_busqueda}'."
                else:
                    respuesta = f"Analizando la demanda de '{producto['nombre']}', por favor espera..."
                    prediccion_resultado = db.get_prediction_data(producto['id_producto'])
                    
                    if prediccion_resultado["success"]:
                        total_unidades = prediccion_resultado['total_forecast']
                        respuesta = f"La demanda pronosticada para '{producto['nombre']}' en los próximos 30 días es de **{total_unidades} unidades**."
                    else:
                        respuesta = f"No pude predecir '{producto['nombre']}': {prediccion_resultado['error']}"

        elif intencion == "exportar_ventas":
            respuesta = "Generando reporte GLOBAL de ventas..."
            resultado_url = db.generar_excel_ventas(id_usuario, base_url, es_admin=True)
            
            if resultado_url == "empty":
                respuesta = "No encontré ventas registradas en el sistema."
            elif resultado_url:
                respuesta = f"✅ Reporte Global Generado.<br><br>👉 <a href='{resultado_url}' target='_blank' style='color: #0d6efd; font-weight: bold;'>Descargar Excel Global</a>"
            else:
                respuesta = "Hubo un error al generar el reporte."
        
        elif intencion == "stats_admin":
            if "total usuarios" in mensaje or "cuantos usuarios" in mensaje:
                conn = db.conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) as total FROM usuario")
                count = cursor.fetchone()[0]
                conn.close()
                respuesta = f"Actualmente hay <strong>{count}</strong> usuarios registrados en total."
            elif "reporte de ventas hoy" in mensaje or "ventas hoy" in mensaje:
                conn = db.conectar_db()
                cursor = conn.cursor()
                sql = "SELECT SUM(total) FROM pedidos WHERE estado IN ('Pagado', 'Enviado', 'Entregado') AND DATE(fecha_pedido) = CURDATE()"
                cursor.execute(sql)
                total_hoy = cursor.fetchone()[0] or 0
                conn.close()
                respuesta = f"Los ingresos totales de hoy (pedidos pagados) son: <strong>${total_hoy:,.0f}</strong>."
            else:
                stats = db.obtener_estadisticas_admin()
                if stats:
                    respuesta = (f"**Resumen Rápido del Sistema:**\n"
                                 f"- **Mensajes Nuevos:** {stats['nuevos_mensajes']}\n"
                                 f"- **Servicios Pendientes:** {stats['servicios_pendientes']}\n"
                                 f"- **Productos con Bajo Stock:** {stats['bajo_stock']}")
                else:
                    respuesta = "No pude obtener las estadísticas en este momento."
        
        elif intencion == "cambiar_estado_pedido":
            match = re.search(r'pedido\s#?(\d+)\s(?:a|como)\s(\w+)', mensaje)
            if match:
                id_pedido, nuevo_estado = match.groups()
                respuesta = db.cambiar_estado_pedido_db(id_pedido, nuevo_estado.capitalize())
            else:
                respuesta = "Claro. Dime el número de pedido y el nuevo estado. Ej: 'Actualiza el pedido 123 a Enviado'."
        
        elif intencion == "analisis_admin":
            respuesta = db.get_category_growth_analysis()

        elif intencion == "buscar_cliente_admin":
            match = re.search(r'(?:busca al cliente|datos de cliente|info de|encuentra a|cliente)\s(.+)', mensaje)
            termino_cliente = match.group(1).strip() if match else mensaje
            if termino_cliente:
                cliente = db.buscar_cliente_por_email_o_nombre(termino_cliente)
                if cliente:
                    respuesta = f"**Cliente Encontrado:**\n- **Nombre:** {cliente['nombre']}\n- **Email:** {cliente['email']}\n- **Región:** {cliente['region'] or 'N/A'}\n- **Pedidos:** {cliente['total_pedidos']}"
                else:
                    respuesta = f"No encontré al cliente '{termino_cliente}'."
            else:
                respuesta = "Dime el nombre o email del cliente que buscas."

        elif intencion == "funciones" or "ayuda" in mensaje:
            respuesta = (
                "**Comandos de Administrador:**\n"
                "* **'Exportar ventas'**: Descarga un reporte global de todas las ventas.\n"
                "* **'Estadísticas'**: Muestra el resumen rápido del sistema.\n"
                "* **'Total usuarios'**: Muestra el conteo total de usuarios registrados.\n"
                "* **'Reporte de ventas hoy'**: Calcula los ingresos del día.\n"
                "* **'Busca al cliente [dato]'**: Encuentra información de un cliente.\n"
                "* **'Actualiza pedido [ID] a [estado]'**: Cambia estado (Ej: 'pedido 105 a Enviado').\n"
                "* **'Predice stock de [producto]'**: Pronóstico de demanda."
            )
        else:
            respuesta = "No entendí ese comando de Admin. Escribe 'ayuda' para ver las opciones."

    # =================================================================
    # 2. LÓGICA PARA VENDEDORES ('V')
    # =================================================================
    elif permisos == 'V':
        if intencion == "saludo":
            frases_vendedor = [
                f"¡Hola, Vendedor **{nombre_usuario}**. ¿Listo para vender más hoy?",
                f"Bienvenido a tu panel, **{nombre_usuario}**."
            ]
            respuesta = random.choice(frases_vendedor)
        
        elif intencion == "prediccion_stock":
            palabras_a_quitar = ["predice stock de", "predice el stock de", "predice stock", "predicción de", "demanda de", "pronostica"]
            termino_busqueda = mensaje
            for frase in palabras_a_quitar:
                if termino_busqueda.startswith(frase):
                    termino_busqueda = termino_busqueda[len(frase):].strip() 
                    break
            
            if not termino_busqueda:
                respuesta = "Claro, dime el nombre de tu producto que quieres predecir. Ej: 'Predice el stock de AdoLuche'"
            else: 
                producto = db.find_product_id_by_name(termino_busqueda, id_vendedor=id_usuario) 
                if not producto:
                    respuesta = f"No encontré el producto '{termino_busqueda}' en tu inventario."
                else:
                    respuesta = f"Analizando la demanda de '{producto['nombre']}', por favor espera..."
                    prediccion_resultado = db.get_prediction_data(producto['id_producto'])
                    
                    if prediccion_resultado["success"]:
                        total_unidades = prediccion_resultado['total_forecast']
                        respuesta = f"La demanda pronosticada para tu producto '{producto['nombre']}' en los próximos 30 días es de **{total_unidades} unidades**."
                    else:
                        respuesta = f"No pude predecir '{producto['nombre']}': {prediccion_resultado['error']}"
        
        elif intencion == "exportar_ventas":
            respuesta = "Generando tu reporte de ventas seguro, dame un momento..."
            resultado_url = db.generar_excel_ventas(id_usuario, base_url)
            
            if resultado_url == "empty":
                respuesta = "Revisé tus registros y no encontré ventas pagadas o finalizadas para exportar."
            elif resultado_url:
                respuesta = f"¡Listo! He generado tu archivo Excel.<br><br><a href='{resultado_url}' target='_blank' style='color: #0d6efd; font-weight: bold;'>Descargar Reporte</a>"
            else:
                respuesta = "Hubo un error interno al generar el archivo. Por favor intenta más tarde."

        elif intencion == "stats_admin" or intencion == "stock_admin" or "productos" in mensaje or "ventas" in mensaje:
             conn = db.conectar_db()
             sql_prod = "SELECT COUNT(*) as num_productos, SUM(stock) as total_stock FROM producto WHERE id_vendedor = %s"
             cursor = conn.cursor(dictionary=True)
             cursor.execute(sql_prod, (id_usuario,))
             result_prod = cursor.fetchone()
             num_productos = result_prod.get('num_productos') or 0
             total_stock = result_prod.get('total_stock') or 0
             
             sql_ventas = "SELECT COUNT(DISTINCT p.id_pedido) as num_ventas, SUM(pp.cantidad * pp.precio_unitario) as total_revenue FROM producto pr JOIN pedidos_productos pp ON pr.id_producto = pp.id_producto JOIN pedidos p ON pp.id_pedido = p.id_pedido WHERE pr.id_vendedor = %s AND p.estado IN ('Pagado', 'Enviado', 'Entregado')"
             cursor.execute(sql_ventas, (id_usuario,))
             result_ventas = cursor.fetchone()
             num_ventas = result_ventas.get('num_ventas') or 0
             total_revenue = result_ventas.get('total_revenue') or 0
             conn.close()

             if "ventas" in mensaje:
                 respuesta = f"Hasta ahora, has realizado <strong>{num_ventas}</strong> ventas, generando un total de <strong>${total_revenue:,.0f}</strong>."
             else:
                 respuesta = f"Actualmente tienes <strong>{num_productos}</strong> productos listados, con un stock total de <strong>{total_stock}</strong> unidades."
        
        elif intencion == "funciones" or "ayuda" in mensaje:
            respuesta = (
                "**Comandos de Vendedor:**\n"
                "* **'Exportar ventas'**: Descarga un Excel seguro con tus transacciones.\n"
                "* **'Mis ventas'**: Muestra el total de ventas e ingresos.\n"
            )
        else:
            respuesta = "No entendí ese comando. Escribe 'ayuda' para ver tus opciones."

    # =================================================================
    # 3. LÓGICA PARA CLIENTES / INVITADOS ('U' o None)
    # =================================================================
    else:
        if intencion == "prediccion_stock" or intencion == "exportar_ventas":
            respuesta = "Lo siento, esa función es exclusiva para Vendedores y Administradores."
            
        elif not id_usuario and intencion in ["pedido", "solicitar_devolucion", "solicitar_notificacion", "actualizar_direccion"]:
            respuesta = "Para esa función, primero debes **iniciar sesión** en tu cuenta."
        
        elif intencion == "saludo":
            if id_usuario:
                frases_cliente = [
                    f"¡Hola de nuevo, **{nombre_usuario}**. ¿Buscas algo especial hoy?",
                    f"Bienvenido a Bitware, **{nombre_usuario}**. ¿En qué te ayudo?"
                ]
                respuesta = random.choice(frases_cliente)
            else:
                frases_invitado = [
                    "¡Hola! Bienvenido a Bitware. Inicia sesión para sacar el máximo provecho.",
                    "¡Bienvenido! Soy tu asistente virtual. Escribe 'ayuda' para ver qué puedo hacer."
                ]
                respuesta = random.choice(frases_invitado)
            
        elif intencion == "funciones" or "ayuda" in mensaje:
            respuesta_basica = (
                "* **'Busca [producto]'**: Para encontrar productos (Ej: 'Busca RTX 3060').\n"
                "* **'Compara [A] con [B]'**: Muestra una comparativa de precios.\n"
                "* **'Horarios de atención'**: Muestra los horarios de la tienda.\n"
                "* **'Soporte'**: Te indica cómo contactar a soporte técnico."
            )
            
            if not id_usuario:
                respuesta = (
                    "**Hola, Invitado. Esto es lo que puedes hacer:**\n"
                    f"{respuesta_basica}\n"
                    "\n¡**Inicia sesión** para ver tu pedido, actualizar tu dirección y más!"
                )
            else:
                respuesta = (
                    f"**Hola, {nombre_usuario}. ¡Puedes pedirme todo esto!:**\n\n"
                    "**SOBRE TUS PEDIDOS:**\n"
                    "* **'Estado de mi pedido'**: Revisa dónde está tu última compra.\n"
                    "* **'Quiero devolver [motivo]'**: Inicia una solicitud de devolución para tu último pedido.\n\n"
                    "**SOBRE PRODUCTOS:**\n"
                    "* **'Avísame de [producto]'**: Te notificaré cuando un producto vuelva a estar disponible.\n"
                    f"{respuesta_basica}"
                )
        
        elif intencion == "producto":
            productos_recomendados = db.recomendar_productos()
            respuesta = "¡Claro! Aquí tienes algunas recomendaciones:"

        elif intencion == "busqueda_producto":
            frases_activadoras = ["buscar producto", "busca producto", "encontrar producto"]
            if mensaje in frases_activadoras:
                respuesta = "¿Qué producto te gustaría buscar?"
            else:
                termino_busqueda = mensaje
                palabras_clave_iniciales = ["busca", "búscame", "encuentra", "tienes", "precio de", "cotiza", "buscar", "quiero buscar"]
                for palabra in palabras_clave_iniciales:
                    if termino_busqueda.startswith(palabra + " "):
                        termino_busqueda = termino_busqueda[len(palabra)+1:].strip()
                        break 
                if not termino_busqueda:
                    respuesta = "¿Qué producto te gustaría buscar?"
                else:
                    productos_encontrados = db.buscar_productos_por_nombre(termino_busqueda)
                    if productos_encontrados:
                        respuesta = f"Encontré esto relacionado con **'{termino_busqueda}'**:"
                        productos_recomendados = productos_encontrados
                    else:
                        respuesta = f"Lo siento, no encontré nada relacionado con **'{termino_busqueda}'**."
        
        elif intencion == "pedido":
            pedido = db.estado_ultimo_pedido(id_usuario)
            respuesta = f"Tu último pedido es el #{pedido['id_pedido']} y su estado es: **{pedido['estado']}**." if pedido else "Aún no tienes pedidos."
        
        elif intencion == "solicitar_devolucion":
            check = db.solicitar_devolucion_db(id_usuario)
            respuesta = check["mensaje"]
        
        elif intencion == "solicitar_notificacion":
            match = re.search(r'(?:avísame de|notifícame de|disponible)\s(?:el|la)\s(.+)', mensaje)
            producto_nombre = match.group(1).strip() if match else ""
            respuesta = db.solicitar_notificacion_db(id_usuario, email_usuario, producto_nombre)
        
        elif intencion == "comparar_productos":
            match = re.search(r'compara\s(.+)\s(?:con|y)\s(.+)', mensaje)
            if match:
                p1, p2 = match.groups()
                respuesta = db.comparar_productos_db(p1.strip(), p2.strip())
            else:
                respuesta = "Dime los dos productos que quieres comparar. Ej: 'Compara RTX 3060 con RX 6600'."
        
        elif intencion == "actualizar_direccion":
            match = re.search(r'dirección\s(?:a|es)\s(.+)', mensaje)
            nueva_dir = match.group(1).strip() if match else ""
            respuesta = db.actualizar_direccion_db(id_usuario, nueva_dir) if nueva_dir else "Dime cuál es tu nueva dirección. Ej: 'Actualizar mi dirección a Calle Falsa 123'."

        elif intencion == "horarios":
            respuesta = "Nuestros horarios de atención son de **Lunes a Viernes de 9:00 a 18:00 hrs**."
        
        elif intencion == "pagos":
            respuesta = "Aceptamos pagos a través de **Webpay (Tarjetas de Crédito/Débito)**"
        
        elif intencion == "soporte":
            respuesta = "Para soporte técnico, visita nuestra sección de **Ayuda** o envíanos un mensaje desde **Soporte** en el pie de página."
        
        else:
            respuesta = "Lo siento, no entendí. Puedes pedirme que **busque un producto** o que revise el **estado de tu pedido**."

    # ESTE ES EL ÚNICO RETURN QUE DEBE HABER AL FINAL
    return jsonify({"respuesta": respuesta, "productos": productos_recomendados})

if __name__ == "__main__":
    print("--- 🚀 VERSION 3.1: CORRECCION BASE_DIR 🚀 ---")
    print("--- INICIANDO CHATBOT BITWARE ---")
    
    # 1. Definir posibles ubicaciones de certificados
    #    Prioridad 1: Carpeta local 'certs' (Solución para permisos de usuario)
    #    Prioridad 2: Ruta estándar de Let's Encrypt (Solo funciona si es root)
    posibles_rutas = [
        {
            'cert': 'certs/fullchain.pem',
            'key': 'certs/privkey.pem',
            'desc': 'Carpeta Local (certs/)'
        },
        {
            'cert': '/etc/letsencrypt/live/bitware.site/fullchain.pem',
            'key': '/etc/letsencrypt/live/bitware.site/privkey.pem',
            'desc': 'Sistema (Let\'s Encrypt)'
        }
    ]

    context = None
    ssl_encontrado = False

    for ruta in posibles_rutas:
        c_path = ruta['cert']
        k_path = ruta['key']
        
        # Convertir a absoluta si es relativa
        if not c_path.startswith('/'):
            c_path = os.path.join(BASE_DIR, c_path)
        if not k_path.startswith('/'):
            k_path = os.path.join(BASE_DIR, k_path)

        if os.path.exists(c_path) and os.path.exists(k_path):
            print(f"✅ Certificados encontrados en: {ruta['desc']}")
            context = (c_path, k_path)
            ssl_encontrado = True
            break
        else:
            print(f"❌ No encontrados en: {ruta['desc']}")

    # 2. Iniciar Servidor
    if ssl_encontrado and context:
        print("🔒 Iniciando servidor en MODO SEGURO (HTTPS)...")
        try:
            app.run(host='0.0.0.0', port=5000, ssl_context=context, debug=FLASK_DEBUG)
        except Exception as e:
            print(f"!!! Error al iniciar HTTPS: {e}")
            print("⚠️ Forzando inicio en HTTP simple (Inseguro)...")
            app.run(host='0.0.0.0', port=5000, debug=FLASK_DEBUG)
    else:
        print("⚠️ ADVERTENCIA: No se encontraron certificados válidos.")
        print("🔓 Iniciando servidor en MODO INSEGURO (HTTP)...")
        app.run(host='0.0.0.0', port=5000, debug=FLASK_DEBUG)
