from mutagen.mp3 import MP3
from dataclasses import dataclass, field
from interfaces.library_source import LibrarySource, TrackCandidate
import metamanager
import lib_db as datab
import hashlib
import re

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
    year: int=field(default=2000)
    cover: bool=field(default=False)

@dataclass
class Track:
    id: str
    title: str
    path: str
    album_id : str
    track_number: int=field(default=0)

def _normalize(name: str) -> str:
        name = name.lower()
        name = re.sub(r"[^a-z0-9\s]", "", name)
        name = re.sub(r"\s+", " ", name).strip()
        return name
    
def gen_id(kind: str, *, file_path=None, artist="", album="") -> str:

    def _hash(data: bytes, n: int=12) -> str:
        return hashlib.sha256(data).hexdigest()[:n]

    match kind:
        case "track":
            audio=MP3(file_path)
            offset=audio.info.frame_offset
            with open(file_path, "rb") as f:
                f.seek(offset)
                chunk=f.read(64_000)
            audio_hash=hashlib.sha256(chunk).hexdigest()[:12]
            album_hash=hashlib.sha256(album.strip().lower().encode()).hexdigest()[:4]
            return audio_hash + album_hash
        case "album":
            key=f"{artist.strip().lower()}|{album.strip().lower()}"
            return _hash(key.encode())
        case "artist":
            return _hash(artist.strip().lower().encode())
        case _:
            raise ValueError(f"Unknown id kind: {kind!r}")
    
def stage_meta(candidate: TrackCandidate):
    metadata = metamanager.extract_meta(candidate)
    if metadata:
        title, artist, album, year, track_num = metadata[0], metadata[1], metadata[2], metadata[3], metadata[4]
        track_id=gen_id("track", file_path=candidate.uri, album=_normalize(album))
        artist_id=gen_id("artist", artist=_normalize(artist))
        album_id=gen_id("album", artist=_normalize(artist), album=_normalize(album))

        return Artist(artist_id, _normalize(artist), artist), Album(album_id, _normalize(album), album, artist_id, year), Track(track_id, title, str(candidate.uri), album_id, track_num)
    return None

def sync_library(source: LibrarySource):
    artists, albums, tracks={}, {}, {}

    art_dir = datab.get_art_path()
    
    for candidate in source.discover():
        data=stage_meta(candidate)
        artist, album, track = None, None, None

        if data is not None:
            artist, album, track=data[0], data[1], data[2]

            if not artist.id in artists.keys(): artists[artist.id]=artist
            if not album.id in albums.keys(): albums[album.id]=album
            if not track.id in tracks.keys(): tracks[track.id]=track

        if album and not datab.get_album_covered(album.id): metamanager.extract_art(candidate, album, art_dir)

    for track in tracks.values():
        source.stage(track, albums[track.album_id].title, artists[albums[track.album_id].artist_id].name)

    artists=[(i.id, i.name, i.display_name) for i in artists.values()]
    albums=[(i.id, i.title, i.display_title, i.year, i.cover, i.artist_id) for i in albums.values()]
    tracks=[(i.id, i.title, i.track_number, i.path, i.album_id) for i in tracks.values()]

    datab.add_batch_artists(artists)
    datab.add_batch_albums(albums)
    datab.add_batch_tracks(tracks)