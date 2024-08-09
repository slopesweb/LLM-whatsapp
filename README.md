# Chatbot

esta app ejecuta una APIREST para un chatbot con whatsapp

el objetivo es que la salida de la consulta se envie via whatsapp
al mismo tiempo permite la recepcion de whatsapp para generar la consulta


## Prerequisites

exportar las variables de entorno antes de ejecutar la aplicacion

## Local testing

crear el entorno y instalar dependencias
```
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Backend

para acceso exterior debemos ejecutar: 

```
uvicorn test_api:app --reload --port 5002 --host 0.0.0.0
```

exportar las variables de entorno correspondientes:
```
export USERS_HOST=
export USERS_USER=
export USERS_PASSWORD=
export USERS_NAME=
export DOCS_HOST=
export DOCS_USER=
export DOCS_PASSWORD=
export DOCS_NAME=
export HTTP_HOST=
export OPENAI_API_KEY=
export WABA=
export token=

```

## acceso webhook whatsapp: 

Para poder proporcionar una url en el proceso de conexion de webhook de whatsapp y recibir los mensages, 
necesitaremos una url publica que debe tener el acceso pot https y un certificado.

Esto requiere instalar en la VM:

1.- crear DDNS tipo A

2.- instalar en la VM proxy inverso mediante NGINX

3.- obtencion de certificado mediante CERTBOT para NGINX


una vez funcionando podemos conectar el Webhook de la cuenta de Whatsapp Business a la url del webhook de la VM


testing local:

1.-http://127.0.0.1:5002/docs


postman 
2.-http://127.0.0.1:5002/status

GET

3.-POST http://127.0.0.1:5002/input

{
  "text": "como mido la presion de aire?"
}

4.-http://127.0.0.1:5002/data
GET

