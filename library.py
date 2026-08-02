from mutagen.mp3 import MP3
from dataclasses import dataclass, field
from interfaces.library_source import LibrarySource, TrackCandidate
import metamanager as meta
import lib_db as datab
from lib_db import Album, Track, Artist
import hashlib
import re

def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9àâæçéèêëïîôœùûüÿäößñ]", "", name)
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
    metadata = meta.extract_meta(candidate)
    if metadata:
        title = metadata["title"]
        artist = metadata["artist"]
        album = metadata["album"]
        year = metadata["year"]
        track_num = metadata["track_num"]

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

        # REDUNDANT FUNCTION USE - WRONG PLUG POSITION ?###################################
        #album_inf = datab.get_album_info(album.id)
        #if album and not datab.get_album_covered(album.id): meta.extract_art(candidate, album, art_dir)
        #####################################################

    for track in tracks.values():
        source.stage(track, albums[track.album_id].display_title, artists[albums[track.album_id].artist_id].display_name)

    artists=[(i.id, i.name, i.display_name) for i in artists.values()]
    albums=[(i.id, i.title, i.display_title, i.year, i.cover, i.artist_id) for i in albums.values()]
    tracks=[(i.id, i.title, i.track_number, i.path, i.album_id) for i in tracks.values()]

    datab.add_batch_artists(artists)
    datab.add_batch_albums(albums)
    datab.add_batch_tracks(tracks)

def metafixer():
    albums = datab.build_fixer_objects()

    def _translate_tags(table, tags):
        translation = {
            "tracks": {
                "track_title": "title",
                "track_number": "track_number",
                "check_state": "check_state",
            },
            "albums": {
                "album_title": "title",
                "year": "year",
                "check_state": "check_state",
            },
            "artists": {
                "artist_name": "name",
            },
        }
        mapping = translation.get(table, {})
        return {mapping[tag]: value for tag, value in tags.items() if tag in mapping}

    def _tag_organizer(tags):
        album_tags = {"album_title", "year"}
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
        changed, unresolved = meta.fix(i.album, i.artist_name, i.track_paths)
        sample_track = next(iter(changed), None)
        changed = _tag_organizer(changed)
        if sample_track:
            for track in changed["track_changes"].keys():
                track_id = datab.get_track_id_from_path(track)
                datab.update_lib_table("tracks", track_id, changed["track_changes"][track])

            datab.update_lib_table("albums", i.album.id, changed["album_changes"])
            datab.update_lib_table("artists", i.album.artist_id, changed["artist_changes"])




