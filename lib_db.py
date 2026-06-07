import sqlite3
import global_var as gb

def setup_db():
    conn = sqlite3.connect("aestr.db")
    cursor = conn.cursor()

    conn.execute("PRAGMA foreign_keys = ON")
    
    conn.executescript("""
                        CREATE TABLE IF NOT EXISTS artists
                        (id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE);

                        CREATE TABLE IF NOT EXISTS albums
                        (id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        year INTEGER,
                        artist_id TEXT NOT NULL,
                        FOREIGN KEY (artist_id) REFERENCES artists(id));

                        CREATE TABLE IF NOT EXISTS tracks
                        (id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        track_number INTEGER,
                        path TEXT NOT NULL UNIQUE,
                        album_id TEXT NOT NULL,
                        FOREIGN KEY (album_id) REFERENCES albums(id));
                    """)
                    
    conn.commit()
    conn.close()

def add_batch(cont_type:str, content: list[tuple]) -> None:
    conn = sqlite3.connect("aestr.db")
    cursor = conn.cursor()
    conn.execute("PRAGMA foreign_keys = ON")

    match cont_type:
        case "artists":
            cursor.executemany("""INSERT OR REPLACE INTO 
                                artists (id, name) VALUES (?, ?)"""
                                ,content)

        case "albums":
            cursor.executemany("""INSERT OR REPLACE INTO 
                                albums (id, title, year, artist_id) VALUES (?, ?, ?, ?)"""
                                ,content)

        case "tracks":
            cursor.executemany("""INSERT OR REPLACE INTO 
                                albums (id, title, track_number, path, album_id) VALUES (?, ?, ?, ?, ?)"""
                                ,content)

        case _:
            raise ValueError(f"Unknown id kind: {kind!r}")

    conn.commit()
    conn.close()

def fetch_info(info_type, query):
    result = []
    conn = sqlite3.connect("aestr.db")
    cursor = conn.cursor()

    match info_type:
        case "artist":
            pass

        case "album":
            pass

        case "track":
            pass
        
        case _:
            raise ValueError(f"Unknown id kind: {kind!r}")

    conn.close()
    return result
