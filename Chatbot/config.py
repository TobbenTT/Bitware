import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- DIRECTORIOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Aseguramos que static/exports exista, ya que se usa en database.py
EXPORT_DIR = os.path.join(BASE_DIR, 'static', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

# --- BASE DE DATOS ---
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'bitware_user')
DB_PASS = os.getenv('DB_PASS', 'Rocky25..')
DB_NAME = os.getenv('DB_NAME', 'bitware')

DB_CONFIG = {
    'pool_name': "bitware_pool",
    'pool_size': 10,
    'pool_reset_session': True,
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASS,
    'database': DB_NAME
}

SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}'

# --- FLASK ---
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
