from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# 1. Configurar la conexión a SQLite (creará un archivo llamado 'usuarios.db')
DATABASE_URL = "sqlite:///./usuarios.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Tu tabla tal cual la diseñaste
class UsuarioToken(Base):
    __tablename__ = "usuarios_tokens"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)  # Google solo lo manda la PRIMERA vez
    token_expiry = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# 3. Función para crear la tabla en el archivo .db si no existe
def init_db():
    Base.metadata.create_all(bind=engine)

# 4. Dependencia para usar la DB en tus endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()