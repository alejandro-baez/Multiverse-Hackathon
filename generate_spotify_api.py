import requests
from dotenv import load_dotenv
import os
from apscheduler.schedulers.background import BackgroundScheduler
from token_class import Token

load_dotenv()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
url = 'https://accounts.spotify.com/api/token'

data = {
    'grant_type': 'client_credentials',
    'client_id': client_id,
    'client_secret': client_secret,
}



def generate_token():
    response = requests.post(url, data=data)
    response_json = response.json()
    print("Obtaining Access Token ...")
    print(response_json['access_token'])
    print(type(response_json.get('access_token')))
    Token.api_token_val = response_json.get('access_token')

scheduler = BackgroundScheduler(daemon=True)


