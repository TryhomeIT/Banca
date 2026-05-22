from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# User schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Publication schemas
class PublicationBase(BaseModel):
    title: str
    category: Optional[str] = None
    collection_name: Optional[str] = None
    publication_date: Optional[datetime] = None

class PublicationCreate(PublicationBase):
    pass

class PublicationResponse(PublicationBase):
    id: int
    filename: str
    original_filename: str
    thumbnail_path: Optional[str] = None
    page_count: int
    file_size: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class PublicationWithProgress(PublicationResponse):
    current_page: Optional[int] = 1
    last_read_at: Optional[datetime] = None
    is_favorite: Optional[bool] = False

# Reading Progress schemas
class ReadingProgressUpdate(BaseModel):
    current_page: int

class ReadingProgressResponse(BaseModel):
    id: int
    publication_id: int
    current_page: int
    last_read_at: datetime
    
    class Config:
        from_attributes = True
