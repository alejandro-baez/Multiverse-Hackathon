from flask import Flask
import psycopg2
import psycopg2.extras
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


SELECT_ARTIST = ("SELECT id FROM artist WHERE name = (%s)")

SELECT_ALBUM = ('SELECT id FROM album WHERE title = (%s)')

SELECT_ALL_ARTISTS_SONGS = ("SELECT artist.name, song.title FROM artist INNER JOIN song ON artist.id = song.artist_id")

SELECT_ARTIST_AND_SONGS = ("SELECT artist.name, song.title FROM artist, song WHERE artist.id = song.artist_id and artist.name = (%s)")

SELECT_ARTIST_ALBUMS_SONGS = ("SELECT artist.name, album.title, album.release_date, album.total_tracks, song.title, song.duration_ms , song.preview_url FROM artist INNER JOIN song ON artist.id = song.artist_id INNER JOIN album ON album.id = song.album_id WHERE artist.name = (%s) ")

INSERT_INTO_ARTIST = ("INSERT INTO artist (name) VALUES (%s)")

INSERT_INTO_ALBUM = ('INSERT INTO album (title,release_date,total_tracks,artist_id) VALUES (%s,%s,%s,%s)')

INSERT_INTO_SONG = 'INSERT INTO song (title,duration_ms, preview_url,artist_id,album_id) VALUES (%s,%s, %s,%s,%s);'


scheduler.add_job(generate_token, 'interval', minutes =59 ,start_date=datetime.now()+timedelta(0,5))
scheduler.start()
sleep(10)

app = Flask(__name__)

conn = psycopg2.connect(f'dbname=hackathon_db user=postgres password={my_db_pw}')


@app.get("/api/search-feature/<query>/<type>")
def search(query,type):
    search_url = f'search?q={query}&type={type}'
    headers = {
        'Authorization': 'Bearer {}'.format(Token.api_token_val)
    }
    response = requests.get(base_url+search_url,headers=headers)
    data = response.json()

    if type == 'artist':
        all_artists = data['artists']['items']
        single_artist_section = all_artists[0]
        artist_name = single_artist_section['name']

        with conn:
            with conn.cursor() as cur:
                cur.execute(INSERT_INTO_ARTIST, (artist_name,))


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

            with conn:
                with conn.cursor() as cur:
                    cur.execute(SELECT_ALBUM,(album_name,))
                    for info in cur:
                        album_id = list(info)[0]

                    cur.execute(SELECT_ARTIST,(artist_name,))
                    for info in cur:
                        artist_id = list(info)[0]

                    cur.execute(INSERT_INTO_SONG,(song_name,song_duration,song_preview_link,artist_id,album_id))


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


@app.get('/db/<artist_name>/all-songs')
def artist_all_songs(artist_name):

    data = {"artist" : artist_name,
            'songs' : []
            }
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:

            curs.execute(SELECT_ARTIST_AND_SONGS,(artist_name,))

            rows = curs.fetchall()

            for row in rows:
                data['songs'].append({'title':row[1]})

    return data

@app.get('/db/<artist_name>/all-songs-albums')
def artist_all_songs_albums(artist_name):
    data = {
        'artist' : artist_name,
        'album' : []
    }
    with conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            curs.execute(SELECT_ARTIST_ALBUMS_SONGS,(artist_name,))

            rows = curs.fetchall()

            for row in rows:
                album_name = row[1]
                album_release = row[2]
                album_track_number = row[3]
                song_title = row[4]
                song_duration = row[5]
                song_preview = row[6]
                global has_been_added
                has_been_added = False


                all_albums_dictionary = data['album']

                if len(all_albums_dictionary) == 0:
                    all_albums_dictionary.append({album_name:{"total_tracks": album_track_number,
                                                              "release_date":album_release,
                                                              'song': [{'song_title' : song_title,
                                                                        'song_duration': song_duration,
                                                                        'song_preview': song_preview}
                                                                       ]}})

                else:
                    for album in all_albums_dictionary:
                        if album_name == list(album.keys())[0]:
                            song_to_add = {'song_title' : song_title, 'song_duration': song_duration, 'song_preview': song_preview}
                            album[album_name]['song'].append(song_to_add)
                            has_been_added = True

                    if has_been_added == False:
                        all_albums_dictionary.append({album_name: {"total_tracks": album_track_number,
                                                                   "release_date": album_release,
                                                                   'song': [
                                                                             {'song_title': song_title,
                                                                              'song_duration': song_duration,
                                                                              'song_preview': song_preview}
                                                                   ]}})

    return data


if __name__ == "__main__":
    with conn:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_ARTIST_TABLE)
            cursor.execute(CREATE_ALBUM_TABLE)
            cursor.execute(CREATE_SONG_TABLE)

    app.run(debug=True)


