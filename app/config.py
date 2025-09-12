import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    POSTGRES_USER = os.getenv("POSTGRESQL_USERNAME", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRESQL_PASSWORD", "postgres")
    POSTGRES_DB_NAME = os.getenv("POSTGRESQL_DATABASE", "auditale_db")
    POSTGRES_PRIMARY_HOST = os.getenv("POSTGRES_PRIMARY_HOST", "primary-db")
    POSTGRES_REPLICA_HOST = os.getenv("POSTGRES_REPLICA_HOST", "read-replica")
    POSTGRES_PORT = os.getenv("POSTGRESQL_PORT_NUMBER", "5432")
    
    APP_PORT = os.getenv("APP_PORT", "8000")
    
    SQLALCHEMY_DATABASE_URI = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_PRIMARY_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    try:
        READING_REPLICAS = int(os.getenv("READING_REPLICAS", "2"))
    except ValueError:
        READING_REPLICAS = 2

class TestConfig(Config):
    TEST_DB = os.path.abspath('test_temp.db')
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{TEST_DB}"
    TESTING = True
    POSTGRES_PRIMARY_HOST = ""
    POSTGRES_REPLICA_HOST = ""
    READING_REPLICAS = 0