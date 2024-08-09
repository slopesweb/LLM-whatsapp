from typing import List, Dict, Any, Iterable
from openai import OpenAI
from unidecode import unidecode
import os
import re
from .embeddings import translate
from .auth_whats import get_conn

client = OpenAI()

def LLM_chat(history: List[Dict[str, str]]) -> Iterable[str]:
    """
    Uses the ChatCompletion API with the given messages.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        stream=False    #desactivamos el streaming
    )
    return response.choices[0].message.content

def respuesta_emoji(emoji:str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
           {"role": "system", "content": "Genera una respuesta al emoticono."},
        {"role": "user", "content": emoji}
       ]
    )
    return response.choices[0].message.content

def get_embedding(txt: str) -> List[float]:
    """
    Preprocess the query with chatgpt and translate to english before embedding it.
    """
    text = txt.replace("\n", " ")
    hyde_prompt = """You will be given a sentence.
If the sentence is a question, convert it to a plausible answer.
If the sentence does not contain a question,
just repeat the sentence as is without adding anything to it.

Examples:
- what furniture there is in my room? --> In my room there is a bed,
a wardrobe and a desk with my computer
- where did you go today --> today I was at school
- I like ice cream --> I like ice cream
- how old is Jack --> Jack is 20 years old"""
    prompt = """
Sentence:
- {input} --> """ + text
    history = [
        {"role": "system", "content": hyde_prompt},
        {"role": "user", "content": prompt},
    ]
   
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        temperature=0.2
    )
    response = response.choices[0].message.content
    query = text + ' ' + response

    translated_query = translate(query)
   
    return_response = client.embeddings.create(input=[translated_query], model='text-embedding-ada-002').data[0].embedding
    return return_response

def get_context(prompt: str, history: List[Dict[str, str]], lng=None) -> Dict[str, Any]:
    """
    Retrieves the most similar document chunk with its metadata in a dictionary.
    """
    conn = get_conn()
    cursor = conn.cursor()
   
    try:
        new_prompt = prompt
        query_emb = get_embedding(new_prompt)

        command = f"SELECT * FROM docs ORDER BY embedding <-> '{query_emb}' LIMIT 5;"
        cursor.execute(command)
        
        colnames = [desc[0] for desc in cursor.description]
        results = cursor.fetchall()
             
        nearests = [{k: v for k, v in zip(colnames, result)} for result in results]
        nearests_txt = '\n\n'.join([row['content'] + ' La URL / enlace es: ' + to_url(row['name'], row['page']) for row in nearests])

    finally:
        cursor.close()
        conn.close()  
    return nearests_txt

def normalize_str(a: str) -> str:
    """Removes all non-alphanumerical characters"""
    pattern = re.compile('[\W_]+')
    return unidecode(pattern.sub('', a))

def to_url(name: str, page: int) -> str:
    """Parses name and page into url from http server of pdfs."""
    name = name.replace(" ", "%20")
    
    pdf_ip = os.environ.get('HTTP_HOST', 'localhost')
    access_url = f'http://' + pdf_ip + name + '#page=' + str(page)
    return access_url

def get_user_chats(user: str):
    """Retrieves all the previous chats. Just the saved title and chat id."""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        query = "SELECT DISTINCT title, chat_id FROM history WHERE username=%s ORDER BY chat_id DESC"
        cursor.execute(query, (user,))
        results = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return [{'title': x[0], 'chat_id': x[1]} for x in results]

def get_messages_from_chat_id(user: str, chat_id: int):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        query = "SELECT query, answer FROM history WHERE username=%s AND chat_id=%s ORDER BY timestamp ASC LIMIT 10"
        cursor.execute(query, (user, chat_id,))
        results = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    messages = []
    for q, a in results:
        messages.append({'content': q, 'role': 'user'})
        messages.append({'content': a, 'role': 'assistant'})
    return messages

def check_command(message: str):
    """Checks if the message starts with '/' and determines if it's '/new' or '/sign', case insensitive."""
    if message.startswith('/'):
        command = message.split('=', 1)[0].lower()  # Extract the command part before '=' and convert to lowercase
        if command == '/new':
            return "new"
        elif command == '/sign':
            return "sign"
        else:
            return ""
    return "not_a_command"