import jwt
import os
import datetime
from jwt import decode, InvalidTokenError
from jwt import PyJWTError
from jwt.exceptions import PyJWTError
import qrcode
from PIL import Image

# WhatsApp API URL for sending a message
whatsapp_api_url = "https://wa.me/"

# Phone number to send the message to (without '+' and spaces, only digits)
phone_number_matic = ""


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = "HS256"

def decode_token(token_url):
    try:
        decoded_token = jwt.decode(token_url,SECRET_KEY,algorithms=[ALGORITHM])
    except InvalidTokenError as e:  
        print(f"Error TOKEN : {token_url}")

    return decoded_token

def encode_token(data):
    try:
        encoded_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    except PyJWTError as e:
        print(f"Error TOKEN : {data})")
    return encoded_token


  

#creamos un token

datos = {
    "user": "xavierw", 
    "maquina": "ARES", 
    "serie": "67543256",
    "role": "admin",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(days=30*3),       # Tiempo de expiración 3 meses

    "iat": datetime.datetime.utcnow()  # Tiempo de emisión
}
token_new = encode_token(datos) 
print(f"El token es= {token_new}")
print("-------------------------------------------------")

token_url = token_new   


token_whats = f"/sign={token_new}"
print(f"Token para whatsapp=  {token_whats}")
print("-------------------------------------------------")
# Eliminar el prefijo '/sign='
if token_whats.startswith('/sign='):
    token = token_whats.replace('/sign=', '')

#ahora decodificamos el token del whataapp
decoded_whats= decode_token(token)
print("Token decodificado:")
username = decoded_whats.get("user")
maquina = decoded_whats.get("maquina")  
num_serie = decoded_whats.get("serie")
role = decoded_whats.get("role")
print(f"username: {username}")
print(f"maquina: {maquina}")    
print(f"num_serie: {num_serie}")    
print(f"role: {role}")  
print("-------------------------------------------------")


# Combine the WhatsApp API URL with the phone number and the encoded message
full_url = f"{whatsapp_api_url}{phone_number_matic}?text={token_whats}"

# Generate QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=10,
    border=4,
)
qr.add_data(full_url)
qr.make(fit=True)

# Create an image from the QR Code instance
img = qr.make_image(fill='black', back_color='white').convert('RGB')

# Load the logo image
logo = Image.open('nemeda_logo2.png')

# Calculate the size of the logo to be added to the QR code
logo_size = min(img.size) // 3  # Make the logo size one-third of the QR code size
logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

# Calculate the position to paste the logo
logo_position = ((img.size[0] - logo_size) // 2, (img.size[1] - logo_size) // 2)

# Paste the logo image onto the QR code
img.paste(logo, logo_position, mask=logo)

# Save the final image
img.save("whatsapp_qr_with_logo.png")

# Display the image
img.show()
