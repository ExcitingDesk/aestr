from difflib import SequenceMatcher
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path
from dotenv import load_dotenv
import os
import musicbrainzngs as mb
import lib_db as datab
import acoustid
import mimetypes

mb.set_useragent("Aestr", "0.1", "khachani.a.a@gmail.com")

MB_SCORE_THRESHOLD = 90
ACOUSTID_SCORE_THRESHOLD = 0.90
FUZZY_MATCH_THRESHOLD = 90

load_dotenv()
acoustID_key = os.getenv("ACOUSTID_KEY")
##############################################
############# EXTRACT FROM FILE ##############
##############################################

def extract_meta(file):
    try:
        audio = EasyID3(file)
    except Exception as e:
        print(f"Skipped {file} -- {e}")
        return None
    else:
        metadata = {
            "title": audio.get("title", ["Unknown"])[0],
            "artist": audio.get("artist", ["Unknown"])[0],
            "album": audio.get("album", ["Unknown"])[0],
            "year": audio.get("date", ["2000"])[0],
            "track_num": audio.get("tracknumber", [0])[0],
        }
        return metadata

def apply_meta(file, new_data):
    try:
        audio = EasyID3(file)
    except Exception as e:
        print(f"Skipped {file} -- {e}")
        return None
    else:
        for i in new_data.keys():
            match i:
                case "album_title":
                    audio["album"] = new_data["album_title"]
                case "artist_name":
                    audio["artist"] = new_data["artist_name"]
                case "track_number":
                    audio["tracknumber"] = new_data["track_number"]
                case "track_title":
                    audio["title"] = new_data["track_title"]
        audio.save()

def extract_art(file_path, album, art_dir):
    try:
        audio = MP3(file_path.uri)
        if audio.tags is None:
            return None

        apics = audio.tags.getall("APIC")
        if not apics:
            return None

        art = next((a for a in apics if a.type == 3), apics[0])

        ext = mimetypes.guess_extension(art.mime)
        if ext is None : return None
        save_path = Path(f"{art_dir}{album.id}{ext}")
        save_path.write_bytes(art.data)
        album.cover=True
        return True
    except Exception as e:
        print(f"Couldn't get {file_path} album art -- {e}")
        return None

##############################################
################ IDENTIFY ####################
##############################################
def get_track_mbid(track_path, track_name, album_title, artist_name):
    try:
        result = mb.search_recordings(
            track_name,
            artist=artist_name,
            release=album_title,
        )
    except mb.WebServiceError as e:
        print(f"  Search failed: {e}")
        return False

    rg_list = result.get("recording-list", [])

    if not rg_list:
        print(f"  No results for '{artist_name} — {album_title}'")
        return False

    score = rg_list[0].get('ext:score', rg_list[0].get('score', 0))
    if score > MB_SCORE_THRESHOLD:
        return rg_list[0]["id"]
    else:
        mbid = fingerprint_id(track_path)
        if mbid:
            return mbid

    return None

def get_album_mbid(album, artist_name, sample_track):
    try:
        result = mb.search_releases(
            artist=artist_name,
            release=album.title,
            status="official",
            limit=5
        )
    except mb.WebServiceError as e:
        print(f"  Search failed: {e}")
        return False

    rg_list = result.get("release-list", [])

    if not rg_list:
        print(f"  No results for '{artist_name} — {album.title}'")
        return False

    score = float(rg_list[0].get('ext:score') or rg_list[0].get('score') or 0)
    if score > MB_SCORE_THRESHOLD:
        return rg_list[0]["id"]
    else:
        mbid = fingerprint_id(sample_track)
        if mbid:
            return mbid

    return None

def fingerprint_id(file_path):
    try:
        for score, recording_id, title, artist in acoustid.match(acoustID_key, file_path):
            if score>ACOUSTID_SCORE_THRESHOLD:
                return recording_id
    except acoustid.AcoustidError as e:
        print(f"  AcoustID failed for {file_path}: {e}")
    return None

def find_match(track, tracklist):
    best_score = 0
    best_match = None
    for t in tracklist:
        score = SequenceMatcher(None, track, t).ratio() * 100
        if score > best_score:
            best_score = score
            best_match = t
    return best_match if best_score > FUZZY_MATCH_THRESHOLD else None
##############################################
################## QUERY #####################
##############################################

def get_album_mbinfo(mbid):
    try:
        result = mb.get_release_by_id(mbid, includes=["recordings", "artist-credits"])

    except mb.WebServiceError as e:
        print(f"  Search failed: {e}")
        return None

    release = result["release"]

    return {
        "title": release["title"],
        "year": release["date"][:4],
        "artist_name": release["artist-credit"][0]["artist"]["name"],
        "tracklist": [r["recording"]["title"] for r in release["medium-list"][0]["track-list"]],
        }

def get_track_mbinfo(mbid):
    try:
        result = mb.get_recording_by_id(mbid)
    except mb.WebServiceError as e:
        print(f"  Search failed: {e}")
        return None

    track = result["recording"]

    return {
        "title": track["title"],
    }

def get_album_art(mbid, album_id):
    _ART_PATH = datab.get_art_path()

    try:
        image_data = mb.get_image_front(mbid, size=1200)
    except mb.ResponseError:
        print(f"  No cover art found on release")
        return False
    else:
        save_path = f"{_ART_PATH}{album_id}.jpg"
        Path(save_path).write_bytes(image_data)
        print(f"  Saved: {save_path}  ({len(image_data)} bytes)")
        return True

##############################################
################## FIX #######################
##############################################
def fix_track_name(file, file_meta, tracklist):
    match = find_match(file_meta["title"], tracklist)
    if match:
        return match
    else :
        track_mbid = get_track_mbid(file, file_meta["title"], file_meta["album"], file_meta["artist"])
        if track_mbid:
            track_meta = get_track_mbinfo(track_mbid)
            return track_meta["title"]
    return None

def fix(album, artist_name, track_paths):
    unresolved = []
    changed = {}
    album_mbid = get_album_mbid(album, artist_name, track_paths[0])

    if not album_mbid:
        unresolved.extend(track_paths)
        return changed, unresolved

    album_meta = get_album_mbinfo(album_mbid)

    if album.title != album_meta["title"]:
        changed["album_title"] = album_meta["title"]
    if album.year != album_meta["year"]: changed["year"] = album_meta["year"]
    if artist_name != album_meta["artist_name"]: changed["artist_name"] = album_meta["artist_name"]

    for file in track_paths:
        metachanges = {}
        file_meta = extract_meta(file)

        if file_meta is None:
            unresolved.append(file)
            continue

        if file_meta["title"] in album_meta["tracklist"]:
            resolved_name = file_meta["title"]
        else:
            resolved_name = fix_track_name(file, file_meta, album_meta["tracklist"])
            if not resolved_name:
                unresolved.append(file)
                continue
        metachanges["track_title"] = resolved_name

        if file_meta["artist"] != album_meta["artist_name"]:
            metachanges["artist_name"] = album_meta["artist_name"]

        if file_meta["album"] != album_meta["title"]:
            metachanges["album_title"] = album_meta["title"]

        if file_meta["track_num"] != album_meta["tracklist"].index(resolved_name)+1:
            metachanges["track_number"] = album_meta["tracklist"].index(resolved_name)+1

        if metachanges:
            apply_meta(file, metachanges)
            metachanges["check_state"] = 1
            changed[file] = metachanges

    return changed, unresolved
