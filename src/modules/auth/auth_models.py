from pydantic import BaseModel, EmailStr, field_validator

class UserCreate(BaseModel):
  """User creation schema"""
  email: EmailStr
  password: str
  confirm_password: str

  @field_validator('username')
  @classmethod
  def validate_username(cls, v):
    if len(v) < 3:
      raise ValueError('Username must be at least 3 characters long')
    if len(v) > 50:
      raise ValueError('Username must be less than 50 characters')
    if not v.replace('_', '').isalnum():
      raise ValueError('Username can only contain letters, numbers, and underscores')
    return v

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
