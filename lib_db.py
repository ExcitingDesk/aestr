import sqlite3
import os

def init_db(lib_path):
    _LOCAL_PATH = f"{lib_path}aestr/"
    _DB_PATH = f"{_LOCAL_PATH}aestr.db"
    _ART_PATH = f"{_LOCAL_PATH}.art/"
    
    os.makedirs(os.path.dirname(_LOCAL_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(_ART_PATH), exist_ok=True)
    
    global conn
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS artists
                        (id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        display_name TEXT NOT NULL UNIQUE);

                        CREATE TABLE IF NOT EXISTS albums
                        (id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        display_title TEXT NOT NULL,
                        year INTEGER,
                        artist_id TEXT NOT NULL,
                        covered BOOLEAN NOT NULL DEFAULT FALSE,
                        FOREIGN KEY (artist_id) REFERENCES artists(id));

                        CREATE TABLE IF NOT EXISTS tracks
                        (id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        track_number INTEGER,
                        path TEXT NOT NULL UNIQUE,
                        album_id TEXT NOT NULL,
                        FOREIGN KEY (album_id) REFERENCES albums(id));

                        CREATE TABLE IF NOT EXISTS user_conf
                        (local_path TEXT NOT NULL,
                        lib_path TEXT NOT NULL,
                        art_path TEXT NOT NULL)
                    """)
    
    cursor = conn.cursor()
    cursor.execute("""INSERT OR REPLACE INTO 
                          user_conf (local_path, lib_path, art_path) VALUES (?, ?, ?)"""
                          ,(_LOCAL_PATH, lib_path, _ART_PATH))
    conn.commit()

def shut_conn():
    conn.close()  

def get_local_path():
    cursor = conn.cursor()
    local_path_row = cursor.execute("SELECT local_path FROM user_conf").fetchone()
    return local_path_row["local_path"] if local_path_row else ""

def get_art_path():
    cursor = conn.cursor()
    art_path_row = cursor.execute("SELECT art_path FROM user_conf").fetchone()
    return art_path_row["art_path"] if art_path_row else ""

def get_lib_path():
    cursor = conn.cursor()
    lib_path_row = cursor.execute("SELECT lib_path FROM user_conf").fetchone()
    return lib_path_row["lib_path"] if lib_path_row else ""

def build_cache():
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, display_name FROM artists")
    artists_cache = {row["id"]: row["display_name"] for row in cursor}

    cursor.execute("SELECT id, display_title FROM albums")
    albums_cache = {row["id"]: row["display_title"] for row in cursor}

    cursor.execute("SELECT id, title FROM tracks")
    tracks_cache = {row["id"]: row["title"] for row in cursor}

    return {"artists": artists_cache, "albums": albums_cache, "tracks": tracks_cache}

def add_batch_artists(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR REPLACE INTO 
                        artists (id, name, display_name) VALUES (?, ?, ?)"""
                       , content)
    conn.commit()

def add_batch_albums(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR REPLACE INTO 
                            albums (id, title, display_title, year, covered, artist_id) VALUES (?, ?, ?, ?, ?, ?)"""
                            ,content)
    conn.commit()

def add_batch_tracks(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR REPLACE INTO 
                            tracks (id, title, track_number, path, album_id) VALUES (?, ?, ?, ?, ?)"""
                            ,content)
    conn.commit()



def get_track_info(track_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return {"title": row["title"], "num": row["track_number"], "path": row["path"], "album": row["album_id"]}


def get_album_info(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM albums WHERE id = ?", (album_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return {"title": row["title"], "display_title": row["display_title"],"year": row["year"], "artist": row["artist_id"]}

def get_album_covered(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT covered FROM albums WHERE id = ?", (album_id,))
    row = cursor.fetchone()
    return row["covered"] if row else False

def get_artist_info(artist_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM artists WHERE id = ?", (artist_id,))
    row = cursor.fetchone()
    if row is None:
        return None
    return {"name": row["name"], "display_name": row["display_name"]}


def list_artist_albums(artist_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_title, year FROM albums WHERE artist_id = ? ORDER BY year DESC", (artist_id,))
    return {row["id"]: [row["display_title"], row["year"]] for row in cursor}


def list_album_tracks(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM tracks WHERE album_id = ? ORDER BY track_number ASC", (album_id,))
    return {row["id"]: row["title"] for row in cursor}

def nuke():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM artists")
    cursor.execute("DELETE FROM albums")
    cursor.execute("DELETE FROM tracks")
    conn.commit()