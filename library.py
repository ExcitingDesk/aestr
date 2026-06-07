from mutagen.easyid3 import EasyID3
from pathlib import Path
from dataclasses import dataclass, field
import global_var as gb
import shutil
import lib_db as datab

# organize_folder depends on sync_library to run first

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
    year: int = field(default_factory=2000)
    artist_id: str

@dataclass
class Track:
    id: str
    title: str
    track_number: int = field(default_factory=0)
    path: str
    album_id : str


def sync_library():
    artists, albums, tracks = {}, {}, {}

    for file in Path(path).rglob("*"):
        # if Path(gb.local_path).name in file.parts: continue
        if file.is_file() and file.suffix in [".mp3"]:

            try:
                audio = EasyID3(file)
            except Exception as e:
                print(f"Skipped {file} -- {e}")
                next

            title = audio.get("title", ["Unknown"])[0]
            artist = audio.get("artist", ["Unknown"])[0]
            album = audio.get("album", ["Unknown"])[0]
            year = audio.get("year", [2000])[0]
            track_num = audio.get("tracknumber", [0])[0]

            track_id = gen_id("track", file_path=file, album=album)
            artist_id = gen_id("artist", artist=artist)
            album_id = gen_id("album", artist=artist, album=album)

            if not artist_id in artists.keys(): artists[artist_id] = Artist(artist_id, artist)
            if not album_id in albums.keys(): albums[album_id] = Album(album_id, album, year, artist_id)
            if not track_id in tracks.keys(): tracks[track_id] = Track(track_id, title, track_num, file, album_id)
            
            artists = [(i.id, i.name) for i in artists.values()]
            albums = [(i.id, i.title, i.year, i.artist_id) for i in albums.values()]
            tracks = [(i.id, i.title, i.track_number, i.path, i.album_id) for i in tracks.values()]

            
            # for artist in artists.values():
            #     datab.add_artist(artist)
            # for album in albums.values():
            #     datab.add_album(album)
            # for track in tracks.values():
            #     datab.add_track(track)

            
def organize_folder():
    # QUERY FROM DB
    for i in lib.albums.items():
        curr_path = gb.local_path + "/" + i[1].artist + "/" + i[1].title
        Path(curr_path).mkdir(parents=True, exist_ok=True)
    
    for i in lib.tracks.items():
        src = Path(i[1].path)
        dst_dir = Path(gb.local_path + "/" + i[1].artist + "/" + i[1].album)
        dst_file = dst_dir / src.name

        if src.parent != dst_dir:
            if dst_file.exists():
                print(f"{src.name} already exists")
            else:
                print(i[1])
                shutil.move(src, dst_dir)
