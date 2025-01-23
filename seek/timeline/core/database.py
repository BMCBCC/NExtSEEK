# core/database.py
import os
from mysql.connector import pooling, Error
from django.conf import settings

db = settings.DATABASES['seek']

db_config = {
    'user': db['USER'],
    'password': db['PASSWORD'],
    'host': db['HOST'],
    'database': db['NAME'],
    'pool_size': int(db.get('POOL_SIZE', 5)),  # Default pool size is 5
    'pool_name': 'timeline_pool',
    'pool_reset_session': True,
}

def get_db_connection():
    try:
        connection_pool = pooling.MySQLConnectionPool(**db_config)
        return connection_pool.get_connection()
    except Error as e:
        print(f"Error while connecting to MySQL using Connection Pool: {e}")
        raise
