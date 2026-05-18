# Modelos de la base de datos del sistema de subastas
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

# Aquí vas a definir todas tus tablas