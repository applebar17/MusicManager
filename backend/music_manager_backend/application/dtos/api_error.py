from pydantic import BaseModel


class ApiErrorRead(BaseModel):
    code: str
    message: str
