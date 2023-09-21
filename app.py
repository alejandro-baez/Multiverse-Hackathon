from flask import Flask
import psycopg2
from dotenv import load_dotenv
import os
from time import sleep
from generate_spotify_api import generate_token, scheduler
from token_class import Token
import requests
from datetime import datetime, timedelta

load_dotenv()

base_url = 'https://api.spotify.com/v1/'


my_db_pw = os.getenv("DB_PASSWORD")


CREATE_ARTIST_TABLE = (
    "CREATE TABLE IF NOT EXISTS artist (id SERIAL PRIMARY KEY, name TEXT);"
)

CREATE_ALBUM_TABLE = (
    "CREATE TABLE IF NOT EXISTS album (id SERIAL PRIMARY KEY, title TEXT, genre TEXT, release_date DATE, artist_id INTEGER ,FOREIGN KEY(artist_id) REFERENCES artist(id) ON DELETE CASCADE);"
)

CREATE_SONG_TABLE = """ CREATE TABLE IF NOT EXISTS song (
                        id SERIAL PRIMARY KEY
                    );"""



scheduler.add_job(generate_token, 'interval', hours = 1,start_date=datetime.now()+timedelta(0,5))
scheduler.start()
sleep(10)


headers = {
        'Authorization': 'Bearer {}'.format(Token.api_token_val)
    }

print('This is the token '+Token.api_token_val)


app = Flask(__name__)

conn = psycopg2.connect(f'dbname=hackathon_db user=postgres password={my_db_pw}')

@app.get("/")
def home():
    return 'Welcome'

@app.get("/api/get-artist")
def index():
    artist1_endpoint = 'artists/0TnOYISbd1XYRBk9myaseg'
    artist2_endpoint = "artists/4LLpKhyESsyAXpc4laK94U"
    artist_url = "".join([base_url,artist2_endpoint])
    response = requests.get(artist_url,headers=headers)
    data = response.json()
    print(data)

    return data

if __name__ == "__main__":
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_ARTIST_TABLE)
            cursor.execute(CREATE_ALBUM_TABLE)


    app.run(debug=True)


