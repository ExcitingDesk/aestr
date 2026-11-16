from mutagen.mp3 import MP3
from interfaces.library_source import LibrarySource, TrackCandidate
import meta
import lib_db as datab
from lib_db import Album, Track, Artist
import hashlib
import re
import uuid

from logger import get_logger

log = get_logger(__name__)

def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9àâæçéèêëïîôœùûüÿäößñ ]", "", name)
    return name

def _gen_audio_hash(file_path) -> str:
    try:
        audio = MP3(file_path)
    except Exception as e:
        print(f"Audio hash generation failed - {e}")
    else:
        offset = audio.info.frame_offset
        with open(file_path, "rb") as f:
            f.seek(offset)
            chunk = f.read(64_000)
        file_hash = hashlib.sha256(chunk).hexdigest()[:12]
        return file_hash
    return None

def stage_meta(candidate: TrackCandidate, cache, audio_hash=None):
    metadata = meta.extract_meta(candidate)

    if metadata:
        if audio_hash is None:
            audio_hash = _gen_audio_hash(candidate)

        title = metadata["title"]
        artist = metadata["artist"]
        album = metadata["album"]
        year = metadata["year"]
        length = metadata["length"]
        track_num = metadata["track_num"]

        artist_norm = _normalize(artist)
        album_norm = _normalize(album)

        track_id = uuid.uuid4().hex[:16]

        if artist_norm in cache["artists"]:
            artist_id = cache["artists"][artist_norm]
            album_id = cache["albums"].get((album_norm, artist_norm))
            if album_id is None:
                album_id = uuid.uuid4().hex[:16]
        else:
            artist_id = uuid.uuid4().hex[:16]
            album_id = uuid.uuid4().hex[:16]

        return (Artist(id=artist_id, name=artist_norm, display_name=artist),
                Album(id=album_id, title=album_norm, display_title=album, year=year, artist_id=artist_id, cover=False),
                Track(id=track_id, title=title, path=str(candidate), length=length, album_id=album_id, audio_hash=audio_hash, track_number=track_num))
    return None

def sync_library(source: LibrarySource):
    cache = datab.build_sync_cache()
    known_paths = cache["track_paths"]
    known_hashes = cache["track_hashes"]

    artists, albums, tracks = {}, {}, {}
    path_repairs = []

    for candidate in source.discover():
        path = candidate.uri

        if path in known_paths:
            continue

        h = _gen_audio_hash(path)
        if h and h in known_hashes:
            path_repairs.append((path, known_hashes[h]))
            continue

        data = stage_meta(path, cache, audio_hash=h)
        if data is None: continue
        artist, album, track = data[0], data[1], data[2]

        cache["artists"][artist.name] = artist.id
        cache["albums"][(album.title, artist.name)] = album.id

        if not artist.id in artists.keys(): artists[artist.id]=artist
        if not album.id in albums.keys(): albums[album.id]=album
        if not track.id in tracks.keys(): tracks[track.id]=track

    for track in tracks.values():
        source.stage(track, albums[track.album_id].display_title, artists[albums[track.album_id].artist_id].display_name)

    artists=[(i.id, i.name, i.display_name) for i in artists.values()]
    albums=[(i.id, i.title, i.display_title, i.year, i.artist_id, i.cover) for i in albums.values()]
    tracks=[(i.id, i.title, i.path, i.album_id, i.audio_hash, i.track_number) for i in tracks.values()]

    datab.add_batch_artists(artists)
    datab.add_batch_albums(albums)
    datab.add_batch_tracks(tracks)

    for new_path, track_id in path_repairs:
        datab.update_lib_table("tracks", track_id, {"path": new_path})

# REDUNDANT FUNCTION USE - WRONG PLUG POSITION ?###################################
        #art_dir = datab.get_art_path()
        #album_inf = datab.get_album_info(album.id)
        #if album and not datab.get_album_covered(album.id): meta.extract_art(candidate, album, art_dir)
        #####################################################
