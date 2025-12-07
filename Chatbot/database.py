import mysql.connector
from mysql.connector import pooling
from sqlalchemy import create_engine
import pandas as pd
from openpyxl import load_workbook
from openpyxl.chart import BarChart, PieChart, LineChart, Reference
import warnings
from datetime import datetime
import os
from statsmodels.tsa.statespace.sarimax import SARIMAX

# Importación local de configuración
from config import DB_CONFIG, SQLALCHEMY_DATABASE_URI, EXPORT_DIR

# --- CONEXIÓN SQLALCHEMY ---
# Usada para operaciones con Pandas (Predicciones y Excel)
db_engine = create_engine(SQLALCHEMY_DATABASE_URI, pool_size=5, max_overflow=10)

# --- MYSQL CONNECTION POOL ---
try:
    db_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
    print("✅  Pool de conexiones MySQL inicializado correctamente.")
except Exception as e:
    print(f"❌  Error al crear el pool de conexiones: {e}")
    db_pool = None

def conectar_db():
    """
    Obtiene una conexión del pool gestionado.
    Es mucho más eficiente que abrir/cerrar conexiones reales cada vez.
    """
    if not db_pool:
        # Fallback si el pool falló (intenta conectar directo)
        try:
            return mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as err:
            print(f"Error Crítico DB (Fallback): {err}")
            return None
            
    try:
        connection = db_pool.get_connection()
        if connection.is_connected():
            return connection
    except Exception as err:
        print(f"Error al obtener conexión del pool: {err}")
        return None
    return None

# ======================================================================
# FUNCIONES DE BASE DE DATOS
# ======================================================================

def recomendar_productos():
    conn = conectar_db()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id_producto AS id, nombre, precio, imagen_principal FROM producto WHERE stock > 0 AND imagen_principal IS NOT NULL AND activo = 1 ORDER BY RAND() LIMIT 3"
        cursor.execute(query)
        productos = cursor.fetchall()
        for p in productos:
            if p.get('precio'): p['precio'] = float(p['precio'])
        return productos
    finally:
        if conn and conn.is_connected(): conn.close()

def buscar_productos_por_nombre(termino_busqueda):
    conn = conectar_db()
    if not conn: return []
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT id_producto AS id, nombre, precio, imagen_principal
            FROM producto
            WHERE (nombre LIKE %s OR categoria LIKE %s)
              AND activo = 1
            LIMIT 3
        """
        like_term = f"%{termino_busqueda}%"
        cursor.execute(query, (like_term, like_term))
        productos = cursor.fetchall()
        processed_productos = []
        for p in productos:
            try:
                if p.get('precio') is not None:
                    p['precio'] = float(p['precio'])
                processed_productos.append(p)
            except Exception as e:
                print(f"!!! ERROR: Procesando producto {p.get('id')}: {e}")
        return processed_productos
    except Exception as e:
        print(f"!!! ERROR inesperado en buscar_productos_por_nombre: {e}")
        return []
    finally:
        if conn and conn.is_connected():
            conn.close()

def generar_excel_ventas(id_vendedor, base_url, es_admin=False):
    try:
        # --- 1. CONSULTA SQL ---
        if es_admin:
            query = """
                SELECT 
                    DATE(p.fecha_pedido) AS 'Fecha',
                    p.id_pedido AS 'ID Pedido',
                    pr.nombre AS 'Producto',
                    pr.categoria AS 'Categoria', 
                    pp.cantidad AS 'Cantidad',
                    pp.precio_unitario AS 'Precio Unitario',
                    (pp.cantidad * pp.precio_unitario) AS 'Total Venta',
                    p.estado AS 'Estado Pedido',
                    u.nombre AS 'Cliente',
                    u.email AS 'Email Cliente',
                    u.region AS 'Region',
                    pr.id_vendedor AS 'ID Vendedor'
                FROM pedidos_productos pp
                JOIN pedidos p ON pp.id_pedido = p.id_pedido
                JOIN producto pr ON pp.id_producto = pr.id_producto
                JOIN usuario u ON p.id_usuario = u.id_usuario
                WHERE p.estado IN ('Pagado', 'Enviado', 'Entregado')
                ORDER BY p.fecha_pedido DESC
            """
            params = None
        else:
            query = """
                SELECT 
                    DATE(p.fecha_pedido) AS 'Fecha',
                    p.id_pedido AS 'ID Pedido',
                    pr.nombre AS 'Producto',
                    pr.categoria AS 'Categoria',
                    pp.cantidad AS 'Cantidad',
                    pp.precio_unitario AS 'Precio Unitario',
                    (pp.cantidad * pp.precio_unitario) AS 'Total Venta',
                    p.estado AS 'Estado Pedido',
                    u.nombre AS 'Cliente',
                    u.email AS 'Email Cliente',
                    u.region AS 'Region'
                FROM pedidos_productos pp
                JOIN pedidos p ON pp.id_pedido = p.id_pedido
                JOIN producto pr ON pp.id_producto = pr.id_producto
                JOIN usuario u ON p.id_usuario = u.id_usuario
                WHERE pr.id_vendedor = %s
                  AND p.estado IN ('Pagado', 'Enviado', 'Entregado')
                ORDER BY p.fecha_pedido DESC
            """
            params = (id_vendedor,)

        # --- 2. PROCESAR DATOS ---
        df = pd.read_sql(query, db_engine, params=params)
        if df.empty: return "empty"

        fecha_hora = datetime.now().strftime("%Y-%m-%d_%H-%M")
        prefix = "Reporte_Global" if es_admin else f"Ventas_Vendedor_{id_vendedor}"
        filename = f"{prefix}_{fecha_hora}.xlsx"
        filepath = os.path.join(EXPORT_DIR, filename)

        # --- 3. CREAR TABLAS RESUMEN ---
        # Tabla A: Productos (Columna A=1, B=2)
        res_prod = df.groupby('Producto')[['Total Venta']].sum().sort_values('Total Venta', ascending=False).reset_index()
        # Tabla B: Categorías (Columna D=4, E=5)
        res_cat = df.groupby('Categoria')[['Total Venta']].sum().reset_index()
        # Tabla C: Regiones (Columna G=7, H=8)
        res_reg = df.groupby('Region')[['Total Venta']].sum().sort_values('Total Venta', ascending=False).head(10).reset_index()
        # Tabla D: Fechas (Columna J=10, K=11)
        res_date = df.groupby('Fecha')[['Total Venta']].sum().reset_index()

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Detalle', index=False)
            
            # Ubicamos las tablas separadas por una columna vacía
            res_prod.to_excel(writer, sheet_name='Dashboard', startcol=0, index=False)  # Cols A, B
            res_cat.to_excel(writer, sheet_name='Dashboard', startcol=3, index=False)   # Cols D, E
            res_reg.to_excel(writer, sheet_name='Dashboard', startcol=6, index=False)   # Cols G, H
            res_date.to_excel(writer, sheet_name='Dashboard', startcol=9, index=False)  # Cols J, K

        # --- 4. GENERAR GRÁFICOS (CORREGIDO) ---
        wb = load_workbook(filepath)
        ws = wb['Dashboard']
        
        # --- GRÁFICO 1: BARRAS (Productos) ---
        chart1 = BarChart()
        chart1.type = "col"
        chart1.style = 10
        chart1.title = "Top Productos (Ingresos)"
        chart1.y_axis.title = "$"
        chart1.x_axis.title = "Producto"
        
        filas_prod = len(res_prod) + 1
        data1 = Reference(ws, min_col=2, min_row=1, max_row=filas_prod, max_col=2)
        cats1 = Reference(ws, min_col=1, min_row=2, max_row=filas_prod)
        chart1.add_data(data1, titles_from_data=True)
        chart1.set_categories(cats1)
        chart1.width = 18
        chart1.height = 10
        ws.add_chart(chart1, "A20") 

        # --- GRÁFICO 2: TORTA (Categorías) ---
        chart2 = PieChart()
        chart2.title = "Ventas por Categoría"
        
        filas_cat = len(res_cat) + 1
        data2 = Reference(ws, min_col=5, min_row=1, max_row=filas_cat, max_col=5)
        cats2 = Reference(ws, min_col=4, min_row=2, max_row=filas_cat)
        chart2.add_data(data2, titles_from_data=True)
        chart2.set_categories(cats2)
        ws.add_chart(chart2, "F20") 

        # --- GRÁFICO 3: TORTA (Regiones) ---
        chart3 = PieChart()
        chart3.title = "Ventas por Región"
        
        filas_reg = len(res_reg) + 1
        data3 = Reference(ws, min_col=8, min_row=1, max_row=filas_reg, max_col=8)
        cats3 = Reference(ws, min_col=7, min_row=2, max_row=filas_reg)
        chart3.add_data(data3, titles_from_data=True)
        chart3.set_categories(cats3)
        ws.add_chart(chart3, "K20")

        # --- GRÁFICO 4: LÍNEA (Tendencia) ---
        chart4 = LineChart()
        chart4.title = "Tendencia de Ventas (Diaria)"
        chart4.style = 12
        chart4.y_axis.title = "$"
        chart4.x_axis.title = "Fecha"
        
        filas_date = len(res_date) + 1
        data4 = Reference(ws, min_col=11, min_row=1, max_row=filas_date, max_col=11)
        cats4 = Reference(ws, min_col=10, min_row=2, max_row=filas_date)
        chart4.add_data(data4, titles_from_data=True)
        chart4.set_categories(cats4)
        chart4.width = 30
        chart4.height = 10
        ws.add_chart(chart4, "A40")

        wb.save(filepath)
        return f"{base_url}static/exports/{filename}"

    except Exception as e:
        print(f"Error generando Excel Dashboard: {e}")
        return None

def solicitar_devolucion_db(id_usuario):
    conn = conectar_db()
    if not conn: 
        return {"elegible": False, "mensaje": "No pude conectarme a la base de datos para verificar tus pedidos."}
    try:
        cursor = conn.cursor(dictionary=True)
        query_elegible = """
            SELECT id_pedido
            FROM pedidos 
            WHERE id_usuario = %s 
              AND estado IN ('Entregado', 'Completado')
            LIMIT 1
        """
        cursor.execute(query_elegible, (id_usuario,))
        pedido_elegible = cursor.fetchone()
        
        if pedido_elegible:
            return {
                "elegible": True, 
                "mensaje": (
                    "¡Claro! He verificado que tienes pedidos **entregados** que son elegibles para devolución.\n\n"
                    "Para iniciar la solicitud de forma segura (y adjuntar fotos si es necesario), "
                    "por favor ve a **Mi Cuenta > Mis Pedidos**.\n\n"
                    "Ahí­ verás el botón **'Solicitar Devolución'** junto a los pedidos que aplican."
                )
            }
        
        query_otros = "SELECT estado FROM pedidos WHERE id_usuario = %s ORDER BY fecha_pedido DESC LIMIT 1"
        cursor.execute(query_otros, (id_usuario,))
        ultimo_pedido = cursor.fetchone()
        
        if ultimo_pedido:
            return {
                "elegible": False, 
                "mensaje": f"Revisé tu cuenta y veo que tu último pedido está en estado **'{ultimo_pedido['estado']}'**. \n\nSolo puedes iniciar una devolución **después de que el pedido haya sido 'Entregado'**."
            }
        else:
            return {
                "elegible": False, 
                "mensaje": "Revisé tu cuenta, pero no encontré ningún pedido registrado."
            }
    except Exception as e:
        print(f"!!! ERROR en solicitar_devolucion_db: {e}")
        return {"elegible": False, "mensaje": "Tuve un problema al consultar tus pedidos."}
    finally:
        if conn and conn.is_connected(): conn.close()

def solicitar_notificacion_db(id_usuario, email_usuario, nombre_producto):
    conn = conectar_db()
    if not conn: return "No pude procesar tu solicitud."
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_producto, stock, nombre FROM producto WHERE nombre LIKE %s LIMIT 1", (f"%{nombre_producto}%",))
        producto = cursor.fetchone()
        if not producto:
            return f"No encontré el producto '{nombre_producto}'."
        if producto['stock'] > 0:
            return f"¡Buenas noticias! El producto '{producto['nombre']}' ya se encuentra en stock."
        id_producto = producto['id_producto']
        cursor.execute("INSERT INTO notificaciones_stock (id_usuario, id_producto, email_usuario) VALUES (%s, %s, %s)", (id_usuario, id_producto, email_usuario))
        conn.commit()
        return f"¡Entendido! Te enviaré un correo a {email_usuario} tan pronto como '{producto['nombre']}' vuelva a estar disponible."
    finally:
        if conn and conn.is_connected(): conn.close()

def comparar_productos_db(producto1_nombre, producto2_nombre):
    conn = conectar_db()
    if not conn: return "No pude obtener la información de los productos."
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT nombre, precio, descripcion FROM producto WHERE nombre LIKE %s OR nombre LIKE %s LIMIT 2"
        cursor.execute(query, (f"%{producto1_nombre}%", f"%{producto2_nombre}%"))
        productos = cursor.fetchall()
        if len(productos) < 2:
            return "No pude encontrar uno o ambos productos para comparar."
        p1, p2 = productos[0], productos[1]
        respuesta = (f"**Comparando {p1['nombre']} vs {p2['nombre']}:**\n"
                     f"- **Precio {p1['nombre']}**: ${p1['precio']:,.0f}\n"
                     f"- **Precio {p2['nombre']}**: ${p2['precio']:,.0f}\n")
        if p1['precio'] < p2['precio']:
            respuesta += f"**Conclusión:** {p1['nombre']} es más económico."
        else:
            respuesta += f"**Conclusión:** {p2['nombre']} es más económico."
        return respuesta
    finally:
        if conn and conn.is_connected(): conn.close()

def actualizar_direccion_db(id_usuario, nueva_direccion):
    conn = conectar_db()
    if not conn: return "No pude actualizar tu dirección."
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE usuario SET direccion = %s WHERE id_usuario = %s", (nueva_direccion, id_usuario))
        conn.commit()
        return "¡Listo! He actualizado tu dirección de enví­o principal."
    finally:
        if conn and conn.is_connected(): conn.close()
        
def estado_ultimo_pedido(id_usuario):
    conn = conectar_db()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id_pedido, fecha_pedido, estado FROM pedidos WHERE id_usuario = %s ORDER BY fecha_pedido DESC LIMIT 1", (id_usuario,))
        return cursor.fetchone()
    finally:
        if conn and conn.is_connected(): conn.close()

# --- Funciones de Administrador ---
def get_proactive_alerts():
    conn = conectar_db()
    if not conn: return ""
    try:
        cursor = conn.cursor()
        alerts = []
        cursor.execute("SELECT COUNT(*) FROM producto WHERE stock < 10 AND activo = 1")
        low_stock = cursor.fetchone()[0]
        if low_stock > 0: alerts.append(f"Tienes **{low_stock} productos con bajo stock**.")
        cursor.execute("SELECT COUNT(*) FROM solicitudes_servicio WHERE estado = 'Pendiente'")
        pending_services = cursor.fetchone()[0]
        if pending_services > 0: alerts.append(f"Hay **{pending_services} solicitudes de servicio** pendientes.")
        return " ".join(alerts)
    finally:
        if conn and conn.is_connected(): conn.close()

def cambiar_estado_pedido_db(id_pedido, nuevo_estado):
    conn = conectar_db()
    if not conn: return "No pude actualizar el pedido."
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pedidos SET estado = %s WHERE id_pedido = %s", (nuevo_estado, id_pedido))
        if cursor.rowcount > 0:
            conn.commit()
            return f"¡Hecho! El pedido #{id_pedido} ha sido actualizado a **{nuevo_estado}**."
        else:
            return f"No encontré el pedido #{id_pedido}."
    finally:
        if conn and conn.is_connected(): conn.close()
        
def get_category_growth_analysis():
    conn = conectar_db()
    if not conn: return "No pude realizar el análisis."
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT pr.categoria, SUM(p.total) as ventas_mes_actual
            FROM pedidos p JOIN producto pr ON p.id_producto = pr.id_producto
            WHERE p.estado = 'Pagado' AND p.fecha_pedido >= DATE_FORMAT(NOW(), '%Y-%m-01')
            GROUP BY pr.categoria ORDER BY ventas_mes_actual DESC LIMIT 1;
        """
        cursor.execute(query)
        top_category = cursor.fetchone()
        if not top_category:
            return "No hay ventas este mes para analizar."
        return f"La categorí­a con mayores ingresos este mes es **{top_category['categoria'].upper()}**."
    finally:
        if conn and conn.is_connected(): conn.close()

def buscar_cliente_por_email_o_nombre(termino):
    conn = conectar_db()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        query_user = "SELECT id_usuario, nombre, email, region FROM usuario WHERE email = %s OR nombre LIKE %s LIMIT 1"
        cursor.execute(query_user, (termino, f"%{termino}%"))
        cliente = cursor.fetchone()
        if cliente:
            query_pedidos = "SELECT COUNT(id_pedido) as total_pedidos FROM pedidos WHERE id_usuario = %s"
            cursor.execute(query_pedidos, (cliente['id_usuario'],))
            cliente['total_pedidos'] = cursor.fetchone()['total_pedidos']
        return cliente
    finally:
        if conn and conn.is_connected(): conn.close()

def obtener_estadisticas_admin():
    conn = conectar_db()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contacto_mensajes WHERE leido = 0")
        nuevos_mensajes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM solicitudes_servicio WHERE estado = 'Pendiente'")
        servicios_pendientes = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM producto WHERE stock < 10 AND activo = 1")
        bajo_stock = cursor.fetchone()[0]
        return { "nuevos_mensajes": nuevos_mensajes, "servicios_pendientes": servicios_pendientes, "bajo_stock": bajo_stock }
    finally:
        if conn and conn.is_connected(): conn.close()

def find_product_id_by_name(product_name, id_vendedor=None):
    conn = conectar_db()
    if not conn: return None
    try:
        cursor = conn.cursor(dictionary=True)
        # 1. Usamos LOWER() en la BD y en Python para ignorar mayúsculas.
        # 2. Comparamos con LIKE para ser más flexibles.
        sql = "SELECT id_producto, nombre, id_vendedor FROM producto WHERE LOWER(nombre) LIKE LOWER(%s)"
        params = [f"%{product_name}%"]

        if id_vendedor:
            sql += " AND id_vendedor = %s"
            params.append(id_vendedor)
        sql += " LIMIT 1"
        cursor.execute(sql, tuple(params))
        producto = cursor.fetchone()
        return producto
    finally:
        if conn and conn.is_connected(): conn.close()

def get_prediction_data(product_id):
    try:
        # Usamos db_engine y read_sql normal para evitar warning
        query = """
            SELECT DATE(p.fecha_pedido) as dia, SUM(pp.cantidad) as total_vendido
            FROM pedidos p
            JOIN pedidos_productos pp ON p.id_pedido = pp.id_pedido
            WHERE pp.id_producto = %s
              AND p.estado IN ('Pagado', 'Enviado', 'Entregado')
              AND p.fecha_pedido >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
            GROUP BY DATE(p.fecha_pedido)
            ORDER BY dia ASC;
        """
        sales_data = pd.read_sql(query, db_engine, params=(product_id,))
        
        if sales_data.empty or len(sales_data) < 15:
            return {"success": False, "error": "Datos insuficientes para la predicción (se necesitan al menos 15 dí­as de ventas)."}

        # Procesamiento del DataFrame
        sales_data['dia'] = pd.to_datetime(sales_data['dia'])
        sales_data = sales_data.set_index('dia')
        sales_data['total_vendido'] = pd.to_numeric(sales_data['total_vendido'])
        df_resampled = sales_data.resample('D').sum().fillna(0).astype(float)
        
        order = (1, 1, 1)
        seasonal_order = (1, 1, 1, 7)
        warnings.filterwarnings("ignore") 
        
        model = SARIMAX(df_resampled['total_vendido'],
                        order=order,
                        seasonal_order=seasonal_order,
                        enforce_stationarity=False,
                        enforce_invertibility=False)
        
        model_fit = model.fit(disp=False) 
        forecast = model_fit.forecast(steps=30)
        
        forecast_dates = pd.date_range(start=df_resampled.index.max() + pd.Timedelta(days=1), periods=30).strftime('%Y-%m-%d').tolist()
        forecast_values = [round(val) if val > 0 else 0 for val in forecast.tolist()]

        return {
            "success": True,
            "forecast_labels": forecast_dates,
            "forecast_data": forecast_values,
            "total_forecast": sum(forecast_values) 
        }
    except Exception as e:
        print(f"Error en get_prediction_data: {e}")
        return {"success": False, "error": str(e)}
