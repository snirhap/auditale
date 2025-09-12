from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from app.config import Config
from random import choice

class DatabaseManager:
    # Context-managed SQLAlchemy sessions:
    # - get_write_session() for transactional writes with commit/rollback
    # - get_read_session() for read-only queries from random replicas
    def __init__(self, config: Config):
        self.config = config
        if getattr(config, "TESTING", False):
            # Testing configuration needed
            self.write_engine = create_engine(f'sqlite:///{config.TEST_DB}', pool_pre_ping=True)
            self.write_sessionmaker = sessionmaker(bind=self.write_engine)
            self.read_engines = [self.write_engine]
            self.read_sessionsmakers = [self.write_sessionmaker]
        else:
            # Read and Write DBs
            self.write_engine = self._create_engine(config.POSTGRES_USER, 
                                                    config.POSTGRES_PASSWORD, 
                                                    config.POSTGRES_PRIMARY_HOST, 
                                                    config.POSTGRES_PORT, 
                                                    config.POSTGRES_DB_NAME)
            self.write_sessionmaker = sessionmaker(bind=self.write_engine)
            self.read_engines = self._create_read_engines()
            self.read_sessionsmakers = [sessionmaker(bind=read_engine) for read_engine in self.read_engines]

    def _create_engine(self, user, password, host, port, db_name):
        return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db_name}", pool_pre_ping=True)

    def _create_read_engines(self):
        read_engines = []
        for i in range(1, self.config.READING_REPLICAS + 1):
            read_engine = self._create_engine(self.config.POSTGRES_USER, 
                                              self.config.POSTGRES_PASSWORD, 
                                              f'{self.config.POSTGRES_REPLICA_HOST}-{i}', 
                                              self.config.POSTGRES_PORT, 
                                              self.config.POSTGRES_DB_NAME)
            read_engines.append(read_engine)
        return read_engines

    @contextmanager
    def get_write_session(self):
        write_session = self.write_sessionmaker()
        try:
            yield write_session
            write_session.commit()
        except:
            write_session.rollback()
            raise
        finally:
            write_session.close()
    
    @contextmanager
    def get_read_session(self):
        read_session = choice(self.read_sessionsmakers)()
        try:
            yield read_session
        except:
            raise
        finally:
            read_session.close()