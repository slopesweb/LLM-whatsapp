import psycopg2
from psycopg2._psycopg import connection
import os
from datetime import datetime, timedelta
from pydantic import BaseModel
from .hasher import Hasher

def get_conn() -> connection:
    """
    Connection to documents database.
    """
    return psycopg2.connect(
        host=os.environ.get('DOCS_HOST', ''),
        database=os.environ.get('DOCS_NAME', ''),
        user=os.environ.get('DOCS_USER',''),
        password=os.environ.get('DOCS_PASSWORD', '')
    )

def get_users_conn() -> connection:
    """
    Connection to documents database.
    """
    return psycopg2.connect(
        host=os.environ.get('USERS_HOST', ''),
        database=os.environ.get('USERS_NAME', ''),
        user=os.environ.get('USERS_USER',''),
        password=os.environ.get('USERS_PASSWORD', '')
    )

class UserCheck(BaseModel):
    username: str

async def check_user_exists(phone: str):
    conn = get_users_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT username, role , language FROM users WHERE phone = %s", (phone,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return {"username": user[0], "exists": True, "name": user[0], "role": user[1], "language": user[2]}
    else:
        return {"username": phone, "exists": False}
    
def get_chat_id(user: str):
    """Gets latest chat id of that user from table history"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sqlquery = "SELECT max(chat_id), max(timestamp) FROM history WHERE username=%s;"
        cursor.execute(sqlquery, (user,))
        result = cursor.fetchone()
        last_id = result[0]
        last_timestamp = result[1]
        if last_id is None:
            last_id = 0
            last_timestamp = None
        last_timestamp = result[1]
    finally:
        cursor.close()
        conn.close()
    return last_id, last_timestamp

def insert_QA(query: str, answer: str, user: str, chat_id: int):
    """Inserts query into table history"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sqlquery = """
            INSERT INTO history (query, answer, username, chat_id)
            VALUES (%s, %s, %s, %s)
        """
        print(f"------------------------------------")
        print(f"Inserting into history: query={query}, answer={answer}, user={user}, chat_id={chat_id}")
        cursor.execute(sqlquery, (query, answer, user, chat_id))
        conn.commit()
    except Exception as e:
        print(f"Error inserting data: {e}")     
    finally:
        cursor.close()
        conn.close()

def update_feedback(feedback: str, user: str, chat_id: int):
    """Adds feedback to message in history database"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sqlquery = """
            SELECT id
            FROM history
            WHERE chat_id = %s AND username = %s
            ORDER BY timestamp ASC
            LIMIT 1;
        """
        cursor.execute(sqlquery, (chat_id, user))
        msg_id = cursor.fetchone()[0]
        # Then update the message
        sqlquery = """
            UPDATE history
            SET feedback = %s
            WHERE id = %s;
        """
        mapping = {'👍': 1, '👎': -1}
        cursor.execute(sqlquery, (mapping[feedback], msg_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

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