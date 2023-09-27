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
    "CREATE TABLE IF NOT EXISTS album (id SERIAL PRIMARY KEY, title TEXT, release_date DATE, total_tracks INTEGER, artist_id INTEGER ,FOREIGN KEY(artist_id) REFERENCES artist(id) ON DELETE CASCADE);"
)

CREATE_SONG_TABLE = """ CREATE TABLE IF NOT EXISTS song (
                        id SERIAL PRIMARY KEY,
                        title TEXT,
                        duration_ms INTEGER,
                        preview_url TEXT,
                        artist_id INTEGER ,
                        album_id INTEGER,
                        FOREIGN KEY(artist_id) REFERENCES artist(id) ON DELETE CASCADE,
                        FOREIGN KEY(album_id) REFERENCES album(id) ON DELETE CASCADE
                    );"""

INSERT_INTO_ARTIST = ("INSERT INTO artist (name) VALUES (%s)")

SELECT_ARTIST = ("SELECT id FROM artist WHERE name = (%s)")

SELECT_ALBUM = ('SELECT id FROM album WHERE title = (%s)')

INSERT_INTO_ALBUM = ('INSERT INTO album (title,release_date,total_tracks,artist_id) VALUES (%s,%s,%s,%s)')

INSERT_INTO_SONG = 'INSERT INTO song (title,duration_ms, preview_url,artist_id,album_id) VALUES (%s,%s, %s,%s,%s);'


scheduler.add_job(generate_token, 'interval', minutes =30 ,start_date=datetime.now()+timedelta(0,5))
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
def single_artist():
    artist1_endpoint = 'artists/0TnOYISbd1XYRBk9myaseg'
    artist2_endpoint = "artists/4LLpKhyESsyAXpc4laK94U"
    artist_url = "".join([base_url,artist2_endpoint])
    response = requests.get(artist_url,headers=headers)
    data = response.json()
    print(data['name'])

    with conn:
        with conn.cursor() as cur:
            cur.execute(INSERT_INTO_ARTIST,(data['name'],))

    return data

@app.get("/api/get-many-artists")
def many_artists():
    many_artists_url = 'artists?ids={}'
    many_artists_uri_list = ["4LLpKhyESsyAXpc4laK94U",'0TnOYISbd1XYRBk9myaseg']
    chunk = ",".join(many_artists_uri_list)
    response = requests.get(base_url+many_artists_url.format(chunk),headers=headers)
    data = response.json()

    return data

@app.get("/api/get-artist-albums")
def get_artist_albums():
    albums_url = 'artists/{}/albums'
    artist_uri = '4LLpKhyESsyAXpc4laK94U'
    response = requests.get(base_url+albums_url.format(artist_uri),headers=headers)
    data = response.json()

    # can run a for loop for the data returned and for each album, grab the artist and match it with the artist in the db
    for res in data['items']:
        album_name = res['name']
        release_date = res['release_date']
        total_tracks = res['total_tracks']
        artist_list = res['artists']


        if len(artist_list) == 1 and total_tracks > 1:
            artist = artist_list[0]['name']
            with conn:
                with conn.cursor() as cur:
                    cur.execute(SELECT_ARTIST,(artist,))

                    for info in cur:
                        artist_id = list(info)[0]



                    cur.execute(INSERT_INTO_ALBUM,(album_name,release_date,total_tracks,artist_id))
    return data


@app.get("/api/search-feature/<query>/<type>")
def search(query,type):
    search_url = f'search?q={query}&type={type}'
    response = requests.get(base_url+search_url,headers=headers)
    data = response.json()

    if type == 'track':
        all_tracks = data['tracks']['items']
        for res in all_tracks:
            album_section = res['album']
            album_name = album_section['name']

            artist_section = res['artists'][0]
            artist_name = artist_section['name']

            song_name = res['name']
            song_duration = res['duration_ms']
            song_preview_link = res['preview_url']

            print(song_name)
            print(song_preview_link)


            with conn:
                with conn.cursor() as cur:
                    cur.execute(SELECT_ALBUM,(album_name,))
                    for info in cur:
                        album_id = list(info)[0]

                    cur.execute(SELECT_ARTIST,(artist_name,))
                    for info in cur:
                        artist_id = list(info)[0]

                    cur.execute(INSERT_INTO_SONG,(song_name,song_duration,song_preview_link,artist_id,album_id))

    if type == 'artist':
        all_artists = data['artists']['items']
        single_artist_section = all_artists[0]
        artist_name = single_artist_section['name']

        with conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_INTO_ARTIST, (artist_name,))

    if type == 'album':
        all_albums = data['albums']['items']

        for res in all_albums:
            album_name = res['name']
            release_date = res['release_date']
            total_tracks = res['total_tracks']
            artist_list = res['artists']
            artist_name = artist_list[0]['name']

            if total_tracks > 1:
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(SELECT_ARTIST, (artist_name,))

                        for info in cur:
                            artist_id = list(info)[0]

                        cur.execute(INSERT_INTO_ALBUM, (album_name, release_date, total_tracks, artist_id))


    return data

@app.get("/api/get-album-songs")
def get_album_songs():
    album_tracks_url = 'albums/{}/tracks'
    album_uri = "5SKnXCvB4fcGSZu32o3LRY"
    response = requests.get(base_url + album_tracks_url.format(album_uri),headers=headers)
    data = response.json()
    return data


if __name__ == "__main__":
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_ARTIST_TABLE)
            cursor.execute(CREATE_ALBUM_TABLE)
            cursor.execute(CREATE_SONG_TABLE)


    app.run(debug=True)


