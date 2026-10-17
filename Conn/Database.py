import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self._db_user = os.getenv("DB_USERNAME", "local").strip()
        self._db_password = os.getenv("DB_PASSWORD", "").strip()
        self._db_host = os.getenv("DB_HOST", "localhost").strip()
        self._db_port = os.getenv("DB_PORT", "5432").strip()
        self._db_database = os.getenv("DB_DATABASE", "sistemas").strip()
        self._db_schema = os.getenv("DB_SCHEMA", "financeiro").strip()

        pwd_encoded = quote_plus(self._db_password) if self._db_password else ""
        self.database_url = f"postgresql+psycopg2://{self._db_user}:{pwd_encoded}@{self._db_host}:{self._db_port}/{self._db_database}"

        try:
            connect_args = {}
            if self._db_schema:
                connect_args = {'options': f'-csearch_path={self._db_schema}'}

            self.engine = create_engine(
                self.database_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                echo=False
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        except SQLAlchemyError as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def get_session(self):
        return self.SessionLocal()

    def create_tables(self):
        """Cria o schema e as tabelas registradas se nao existirem."""
        if self._db_schema:
            from sqlalchemy import text, create_engine
            temp_engine = create_engine(self.database_url, isolation_level="AUTOCOMMIT")
            with temp_engine.connect() as conn:
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {self._db_schema}"))
            temp_engine.dispose()
        Base.metadata.create_all(bind=self.engine)


class get_db_session:
    """Context manager para sessoes seguras do SQLAlchemy."""
    def __init__(self):
        self.db = Database()
        self.session = self.db.get_session()

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
        else:
            self.session.commit()
        self.session.close()
