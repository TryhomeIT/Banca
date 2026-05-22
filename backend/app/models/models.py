from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    reading_progress = relationship("ReadingProgress", back_populates="user")

class Publication(Base):
    __tablename__ = "publications"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    thumbnail_path = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=False)
    page_count = Column(Integer, default=0)
    file_size = Column(Integer, default=0)  # in bytes
    category = Column(String(100), nullable=True)  # newspaper, magazine, book, etc.
    collection_name = Column(String(255), nullable=True) # group for comic books
    publication_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reading_progress = relationship("ReadingProgress", back_populates="publication")

class ReadingProgress(Base):
    __tablename__ = "reading_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    publication_id = Column(Integer, ForeignKey("publications.id"), nullable=False)
    current_page = Column(Integer, default=1)
    last_read_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="reading_progress")
    publication = relationship("Publication", back_populates="reading_progress")
class SystemSettings(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(String(500), nullable=True)
    description = Column(String(255), nullable=True)
    category = Column(String(50), default="general") # general, telegram, ai
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserFavorite(Base):
    """Stores user's favorite publication titles (not IDs, since daily publications create new records)."""
    __tablename__ = "user_favorites"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    publication_title = Column(String(255), nullable=False)  # Title like "Público LX", "DN"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="favorites")

# Add favorites relationship to User model
User.favorites = relationship("UserFavorite", back_populates="user", cascade="all, delete-orphan")
