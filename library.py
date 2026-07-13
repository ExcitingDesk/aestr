from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path
from dataclasses import dataclass, field
from interfaces.library_source import LibrarySource, TrackCandidate
import shutil
import lib_db as datab
import hashlib

@dataclass
class Artist:
    id: str
    name: str

@dataclass
class Album:
    id: str
    title: str
    artist_id: str
    year: int = field(default=2000)

@dataclass
class Track:
    id: str
    title: str
    path: str
    album_id : str
    track_number: int = field(default=0)

def gen_id(kind: str, *, file_path=None, artist="", album="") -> str:

    def _hash(data: bytes, n: int = 12) -> str:
        return hashlib.sha256(data).hexdigest()[:n]

    match kind:
        case "track":
            audio = MP3(file_path)
            offset = audio.info.frame_offset
            with open(file_path, "rb") as f:
                f.seek(offset)
                chunk = f.read(64_000)
            audio_hash = hashlib.sha256(chunk).hexdigest()[:12]
            album_hash = hashlib.sha256(album.strip().lower().encode()).hexdigest()[:4]
            return audio_hash + album_hash
        case "album":
            key = f"{artist.strip().lower()}|{album.strip().lower()}"
            return _hash(key.encode())
        case "artist":
            return _hash(artist.strip().lower().encode())
        case _:
            raise ValueError(f"Unknown id kind: {kind!r}")

def meta_extract(candidate: TrackCandidate):
    file = candidate.uri
    try:
        audio = EasyID3(file)
    except Exception as e:
        print(f"Skipped {file} -- {e}")
        return None
    else:
        title = audio.get("title", ["Unknown"])[0]
        artist = audio.get("artist", ["Unknown"])[0]
        album = audio.get("album", ["Unknown"])[0]
        year = audio.get("date", [2000])[0]
        track_num = audio.get("tracknumber", [0])[0]

        track_id = gen_id("track", file_path=file, album=album)
        artist_id = gen_id("artist", artist=artist)
        album_id = gen_id("album", artist=artist, album=album)

        return (Artist(artist_id, artist), Album(album_id, album, artist_id, year), Track(track_id, title, str(file), album_id, track_num))

def sync_library(source: LibrarySource):
    artists, albums, tracks = {}, {}, {}

    for candidate in source.discover():
        data = meta_extract(candidate)

        if data != None:
            artist, album, track = data[0], data[1], data[2]

            if not artist.id in artists.keys(): artists[artist.id] = artist
            if not album.id in albums.keys(): albums[album.id] = album
            if not track.id in tracks.keys(): tracks[track.id] = track

            source.stage(track, album.title, artist.name) 

        else: continue

    artists = [(i.id, i.name) for i in artists.values()]
    albums = [(i.id, i.title, i.year, i.artist_id) for i in albums.values()]
    tracks = [(i.id, i.title, i.track_number, i.path, i.album_id) for i in tracks.values()]

    datab.add_batch("artists", artists)
    datab.add_batch("albums", albums)
    datab.add_batch("tracks", tracks)