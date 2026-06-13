from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path
from dataclasses import dataclass, field
import global_var as gb
import shutil
import lib_db as datab
import hashlib

path = gb.path

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

def sync_library():
    artists, albums, tracks = {}, {}, {}

    for file in Path(path).rglob("*"):
        if file.is_file() and file.suffix in [".mp3"]:

            try:
                audio = EasyID3(file)
            except Exception as e:
                print(f"Skipped {file} -- {e}")
                continue

            title = audio.get("title", ["Unknown"])[0]
            artist = audio.get("artist", ["Unknown"])[0]
            album = audio.get("album", ["Unknown"])[0]
            year = audio.get("year", [2000])[0]
            track_num = audio.get("tracknumber", [0])[0]

            track_id = gen_id("track", file_path=file, album=album)
            artist_id = gen_id("artist", artist=artist)
            album_id = gen_id("album", artist=artist, album=album)

            if not artist_id in artists.keys(): artists[artist_id] = Artist(artist_id, artist)
            if not album_id in albums.keys(): albums[album_id] = Album(album_id, album, artist_id, year)
            if not track_id in tracks.keys(): tracks[track_id] = Track(track_id, title, str(file), album_id, track_num)

    for track in tracks.values():
        album = albums[track.album_id]
        artist = artists[album.artist_id]

        dst_dir = Path(gb.local_path) / artist.name / album.title
        dst_file = dst_dir / Path(track.path).name

        if Path(track.path).parent != dst_dir:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(track.path, dst_file)
            track.path = str(dst_file)

    artists = [(i.id, i.name) for i in artists.values()]
    albums = [(i.id, i.title, i.year, i.artist_id) for i in albums.values()]
    tracks = [(i.id, i.title, i.track_number, i.path, i.album_id) for i in tracks.values()]

    datab.add_batch("artists", artists)
    datab.add_batch("albums", albums)
    datab.add_batch("tracks", tracks)
