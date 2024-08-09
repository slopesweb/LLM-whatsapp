from auth import get_users_conn
from pydantic import BaseModel
from hasher import Hasher

class UserData(BaseModel):
    username: str
    role: str
    pwd: str
    phone: str

def add_user(data: UserData):
    pwd_hash = Hasher([data.pwd]).generate()[0]
    conn = get_users_conn()
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO users (username, role, password_hash, phone) 
        VALUES (%s, %s, %s, %s) 
        ON CONFLICT (username) 
        DO UPDATE SET phone = excluded.phone;"""
        cursor.execute(query, (data.username, data.role, pwd_hash, data.phone))
        conn.commit()
    except Exception as e:
        print('Error in add-user:', e)
    finally:
        cursor.close()
        conn.close()

add_user(UserData(username='test', role='user', pwd='WHaTSaPP', phone='34'))
add_user(UserData(username='test', role='admin', pwd='WHaTSaPP2', phone='34666'))