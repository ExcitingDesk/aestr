import sqlite3
import os
from dataclasses import dataclass, field
from logger import get_logger

log = get_logger(__name__)

"""
CHECK STATES :
0 : UNCHECKED
1 : CHECKED AND COMPLETE
2 : REQUIRE USER ATTENTION
"""

ALLOWED_COLUMNS = {
    "tracks": {"title", "display_title", "track_number", "path", "check_state", "album_id"},
    "albums": {"title", "display_title", "year", "check_state", "artist_id"},
    "artists": {"name", "display_name"},
    }

@dataclass
class Artist:
    id: str
    name: str
    display_name: str

@dataclass
class Album:
    id: str
    title: str
    display_title: str
    artist_id: str
    year: str=field(default="2000")
    cover: bool=field(default=False)

@dataclass
class Track:
    id: str
    title: str
    path: str
    album_id : str
    audio_hash : str
    track_number: int=field(default=0)

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
                        year TEXT,
                        artist_id TEXT NOT NULL,
                        covered BOOLEAN NOT NULL DEFAULT FALSE,
                        check_state INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (artist_id) REFERENCES artists(id));

                        CREATE TABLE IF NOT EXISTS tracks
                        (id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        track_number INTEGER,
                        length INTEGER,
                        path TEXT NOT NULL UNIQUE,
                        album_id TEXT NOT NULL,
                        audio_hash TEXT,
                        check_state INTEGER NOT NULL DEFAULT 0,
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

##############################################
################ BUILDERS ####################
##############################################

def build_search_artist_cache():
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_name FROM artists")
    artists_cache = {row["id"]: row["display_name"] for row in cursor}

    return artists_cache

def build_search_album_cache():
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_title FROM albums")
    albums_cache = {row["id"]: row["display_title"] for row in cursor}

    return albums_cache

def build_search_track_cache():
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM tracks")
    tracks_cache = {row["id"]: row["title"] for row in cursor}

    return tracks_cache

def build_sync_cache():
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM artists")
    artists_cache = {row["name"]: row["id"] for row in cursor}

    cursor.execute("""
        SELECT albums.id AS id, albums.title AS title, artists.name AS artist_name
        FROM albums JOIN artists ON albums.artist_id = artists.id
    """)
    albums_cache = {(row["title"], row["artist_name"]): row["id"] for row in cursor}

    cursor.execute("SELECT id, path, audio_hash FROM tracks")
    track_paths = {}
    track_hashes = {}
    for row in cursor:
        track_paths[row["path"]] = row["id"]
        if row["audio_hash"]:
            track_hashes[row["audio_hash"]] = row["id"]

    return {
        "artists": artists_cache,
        "albums": albums_cache,
        "track_paths": track_paths,
        "track_hashes": track_hashes,
    }

##############################################
################ GETTERS #####################
##############################################

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

def get_track_info(track_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks WHERE id = ?", (track_id,))
    row = cursor.fetchone()
    return None if not row else {"id": row["id"],
                                 "title": row["title"],
                                 "track_number": row["track_number"],
                                 "path": row["path"],
                                 "length": row["length"],
                                 "album_id": row["album_id"],
                                 "audio_hash": row["audio_hash"],
                                 "check_state": row["check_state"]}


def get_album_info(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM albums WHERE id = ?", (album_id,))
    row = cursor.fetchone()
    return None if not row else { "id" : row["id"],
                                    "title": row["title"],
                                    "display_title": row["display_title"],
                                    "year": row["year"],
                                    "artist_id": row["artist_id"],
                                    "covered": row["covered"],
                                    "check_state": row["check_state"]}

def get_artist_info(artist_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM artists WHERE id = ?", (artist_id,))
    row = cursor.fetchone()
    return None if not row else {"id": row["id"],
                                "name": row["name"],
                                "display_name": row["display_name"]}

def get_track_id_from_path(path):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tracks WHERE path = ?", (path,))
    row = cursor.fetchone()
    return None if not row else row["id"]

##### REDUNDANT - NEEDS RE-WIRING ?
def get_album_covered(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT covered FROM albums WHERE id = ?", (album_id,))
    row = cursor.fetchone()
    return row["covered"] if row else False


def list_artist_albums(artist_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id, display_title, year FROM albums WHERE artist_id = ? ORDER BY year DESC", (artist_id,))
    return {row["id"]: [row["display_title"], row["year"]] for row in cursor}


def list_album_tracks(album_id):
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM tracks WHERE album_id = ? ORDER BY track_number ASC", (album_id,))
    return {row["id"]: row["title"] for row in cursor}

##############################################
################# SETTERS ####################
##############################################

def add_batch_artists(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR IGNORE INTO
                        artists (id, name, display_name) VALUES (?, ?, ?)"""
                       , content)
    conn.commit()

def add_batch_albums(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR IGNORE INTO
                            albums (id, title, display_title, year, artist_id, covered) VALUES (?, ?, ?, ?, ?, ?)"""
                            ,content)
    conn.commit()

def add_batch_tracks(content: list[tuple]) -> None:
    cursor = conn.cursor()
    cursor.executemany("""INSERT OR IGNORE INTO
                            tracks (id, title, path, length, album_id, audio_hash, track_number) VALUES (?, ?, ?, ?, ?, ?, ?)"""
                            ,content)
    conn.commit()

def update_lib_table(table, g_id, changes):
    if table not in ALLOWED_COLUMNS:
        raise ValueError(f"Table not allowed: {table}")

    allowed = ALLOWED_COLUMNS[table]
    columns = []
    values = []

    for tag, value in changes.items():
        if tag not in allowed:
            print(f"{tag} not allowed - ignoring")
            continue
        columns.append(f"{tag} = ?")
        values.append(value)

    if not columns:
        return

    values.append(g_id)
    sql = f"UPDATE {table} SET {', '.join(columns)} WHERE id = ?"
    conn.cursor().execute(sql, values)
    conn.commit()

def merge_artist(old_id, new_id):
    with conn:
        conn.execute("UPDATE albums SET artist_id = ? WHERE artist_id = ?", (new_id, old_id))
        conn.execute("DELETE FROM artists WHERE id = ?", (old_id,))

def clear_orphan_rows():
    with conn:
        fk_tracks = conn.execute(
            "DELETE FROM tracks WHERE album_id NOT IN (SELECT id FROM albums)"
        ).rowcount
        fk_albums = conn.execute(
            "DELETE FROM albums WHERE artist_id NOT IN (SELECT id FROM artists)"
        ).rowcount
        empty_albums = conn.execute(
            "DELETE FROM albums WHERE id NOT IN (SELECT DISTINCT album_id FROM tracks)"
        ).rowcount
        empty_artists = conn.execute(
            "DELETE FROM artists WHERE id NOT IN (SELECT DISTINCT artist_id FROM albums)"
        ).rowcount
    log.info(
        f"Orphan cleanup: {fk_tracks} FK-broken tracks, "
        f"{fk_albums} FK-broken albums, "
        f"{empty_albums} empty albums, "
        f"{empty_artists} empty artists"
    )