from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
  """User creation schema"""
  email: EmailStr
  password: str
  confirm_password: str

  @field_validator('password')
  @classmethod
  def validate_password(cls, v):
    if len(v) < 6:
      raise ValueError('Password must be at least 6 characters long')
    return v

  @field_validator('confirm_password')
  @classmethod
  def passwords_match(cls, v, info):
    if 'password' in info.data and v != info.data['password']:
      raise ValueError('Passwords do not match')
    return v

class UserLogin(BaseModel):
  """User login schema"""
  email: EmailStr
  password: str
