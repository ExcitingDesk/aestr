from mutagen.mp3 import MP3
from interfaces.library_source import LibrarySource, TrackCandidate
import metamanager as meta          # still used by stage_meta (extract_meta / extract_art)
import new_metamanager as new_meta    # voting-based resolver + tag repair, used by metafixer()
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

def metafixer():
    albums = datab.build_fixer_objects()
    unresolved=[]
    def _translate_tags(table, tags):
        translation = {
            "tracks": {
                "track_title": "display_title",
                "track_number": "track_number",
                "check_state": "check_state",
            },
            "albums": {
                "album_title": "title",
                "year": "year",
                "check_state": "check_state",
            },
            "artists": {
                "artist_name": "display_name",
            },
        }
        mapping = translation.get(table, {})
        return {mapping[tag]: value for tag, value in tags.items() if tag in mapping}

    def _tag_organizer(tags):
        album_tags = {"album_title", "year", "check_state"}
        artist_tags = {"artist_name"}
        track_tags = {"track_title", "track_number", "check_state"}

        album_changes = {}
        artist_changes = {}
        track_changes = {}

        for key, value in tags.items():
            if isinstance(value, dict):
                file_changes = {}
                for tag, val in value.items():
                    if tag in track_tags:
                        file_changes[tag] = val
                    elif tag in album_tags:
                        album_changes[tag] = val
                    elif tag in artist_tags:
                        artist_changes[tag] = val
                if file_changes:
                    track_changes[key] = file_changes
            elif key in album_tags:
                album_changes[key] = value
            elif key in artist_tags:
                artist_changes[key] = value

        return {
            "album_changes": _translate_tags("albums", album_changes),
            "artist_changes": _translate_tags("artists", artist_changes),
            "track_changes": {f: _translate_tags("tracks", tags) for f, tags in track_changes.items()},
        }

    for i in albums:
        log.info(f"Fixing Album : {i.album.title} by {i.artist_name}")

        changed, unresolved_in_album = meta.fix(i.album, i.artist_name, i.track_paths)
            
        unresolved.extend(unresolved_in_album)
        changed = _tag_organizer(changed)
        
        if unresolved_in_album == []:
            changed["album_changes"]["check_state"] = 1
        
        for track in changed["track_changes"].keys():
            track_id = datab.get_track_id_from_path(track)
            datab.update_lib_table("tracks", track_id, changed["track_changes"][track])
            
        datab.update_lib_table("albums", i.album.id, changed["album_changes"])
        datab.update_lib_table("artists", i.album.artist_id, changed["artist_changes"])
    
    return unresolved



