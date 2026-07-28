import sqlite3
import os
from dataclasses import dataclass, field

"""
CHECK STATES :
0 : UNCHECKED
1 : CHECKED AND COMPLETE
2 : REQUIRE USER ATTENTION
"""

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
    track_number: int=field(default=0)

@dataclass
class FixerJob:
    album: Album
    artist_name: str
    track_paths: list[str]

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
                        path TEXT NOT NULL UNIQUE,
                        album_id TEXT NOT NULL,
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

def build_artist_cache():
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, display_name FROM artists")
    artists_cache = {row["id"]: row["display_name"] for row in cursor}

    return artists_cache

def build_album_cache():
    cursor = conn.cursor()

    cursor.execute("SELECT id, display_title FROM albums")
    albums_cache = {row["id"]: row["display_title"] for row in cursor}

    return albums_cache

def build_track_cache():
    cursor = conn.cursor()

    cursor.execute("SELECT id, title FROM tracks")
    tracks_cache = {row["id"]: row["title"] for row in cursor}

    return tracks_cache

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

def build_fixer_objects():
    def _get_tracks_from_album(alb_id):
        _cursor = conn.cursor()
        _cursor.execute("SELECT id, path, track_number FROM tracks WHERE album_id=? ORDER BY track_number", (alb_id,))
        return [r["path"] for r in _cursor.fetchall()]

    def _get_artist_name(art_id):
        _cursor = conn.cursor()
        _cursor.execute("SELECT name FROM artists WHERE id=?", (art_id,))
        _row = _cursor.fetchone()
        if _row:
            return _row["name"]
        return None

    cursor = conn.cursor()
    cursor.execute("SELECT id, title, display_title, artist_id, year FROM albums WHERE check_state=?", (0,))
    rows = cursor.fetchall()
    if not rows:
        return None
    return [FixerJob(
        album=Album(r["id"], r["title"], r["display_title"], r["artist_id"], r["year"]),
        artist_name=_get_artist_name(r["artist_id"]),
        track_paths=_get_tracks_from_album(r["id"])) for r in rows]

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

def get_track_from_path(path):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tracks WHERE path = ?", (path,))
    row = cursor.fetchone()
    if row is None:
        return None
    return {"id": row["id"], "title": row["title"], "num": row["track_number"], "path": row["path"], "album": row["album_id"]}

def mod_track_info(id, title, track_number, path, album_id):
    cursor = conn.cursor()
    cursor.execute("""
                   UPDATE tracks
                   SET title        = ?,
                       track_number = ?,
                       path         = ?,
                       album_id     = ?
                   WHERE id = ?
                   """, (title, track_number, path, album_id, id))
    conn.commit()

def mod_album_info(id, display_title, year):
    cursor = conn.cursor()
    cursor.execute("""
                    UPDATE albums
                    SET display_title = ?,
                        year        = ?
                    WHERE id = ?
                    """, (display_title, year, id))
    conn.commit()

def mod_artist_info(id, display_name):
    cursor = conn.cursor()
    cursor.execute("""
                    UPDATE artists
                    SET display_name = ?
                    WHERE id = ?
                    """, (display_name, id, ))
    conn.commit()

def nuke():
    cursor = conn.cursor()
    cursor.execute("DELETE FROM artists")
    cursor.execute("DELETE FROM albums")
    cursor.execute("DELETE FROM tracks")
    conn.commit()