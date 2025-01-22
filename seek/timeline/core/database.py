# core/database.py
import os
from mysql.connector import pooling, Error
from dotenv import load_dotenv

load_dotenv()

db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'pool_size': int(os.getenv('DB_POOL_SIZE', 5)),  # Default pool size is 5
    'pool_name': 'my_pool',
    'pool_reset_session': True,
}

def get_db_connection():
    try:
        connection_pool = pooling.MySQLConnectionPool(**db_config)
        return connection_pool.get_connection()
    except Error as e:
        print(f"Error while connecting to MySQL using Connection Pool: {e}")
        raise
