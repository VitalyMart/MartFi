from dataclasses import dataclass

@dataclass
class User:
    id: int
    email: str
    full_name: str
    hashed_password: str