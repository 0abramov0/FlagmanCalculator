from pydantic import BaseModel

class User(BaseModel):
    username: str
    role: str = "user"
    is_active: bool = True

class UserCreate(User):
    password: str

class UserInDB(User):
    id: int
    password: str
