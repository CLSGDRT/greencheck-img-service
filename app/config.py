import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def get_database_path():
        # Utilise le répertoire du fichier config comme base
        base_dir = os.path.abspath(os.path.dirname(__file__))
        return os.path.join(base_dir, '..', 'database', 'img-service.db')
    
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{get_database_path()}"
    )

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL", 
        "sqlite:///:memory:"
    )

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, config['default'])