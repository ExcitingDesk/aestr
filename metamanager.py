from difflib import SequenceMatcher
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from pathlib import Path
from dotenv import load_dotenv
import os
import re
import time
import musicbrainzngs as mb
import lib_db as datab
import acoustid
import mimetypes

from logger import get_logger

log = get_logger(__name__)

mb.set_useragent("Aestr", "0.1", "khachani.a.a@gmail.com")

MB_SCORE_THRESHOLD = 90
ACOUSTID_SCORE_THRESHOLD = 0.90
FUZZY_MATCH_THRESHOLD = 90
MAX_ACOUSTID_CANDIDATES = 10

load_dotenv()
acoustID_key = os.getenv("ACOUSTID_KEY")

##############################################
############# EXTRACT FROM FILE ##############
##############################################

def extract_meta(file):
    try:
        audio = EasyID3(file)
    except Exception as e:
        log.info(f"Skipped {file} -- {e}")
        return None
    else:
        metadata = {
            "title": audio.get("title", ["Unknown"])[0],
            "artist": audio.get("artist", ["Unknown"])[0],
            "album": audio.get("album", ["Unknown"])[0],
            "year": audio.get("date", [None])[0],
            "track_num": audio.get("tracknumber", ["0"])[0],
        }
        
        if metadata["year"] is None: metadata["year"]=ID3(file).getall("TYER")[0] if ID3(file).getall("TYER")!=[] else None
        
        return metadata

def apply_meta(file, new_data):
    try:
        audio = EasyID3(file)
    except Exception as e:
        log.info(f"Skipped {file} -- {e}")
        return None
    else:
        for i in new_data.keys():
            match i:
                case "album_title":
                    audio["album"] = new_data["album_title"]
                case "artist_name":
                    audio["artist"] = new_data["artist_name"]
                case "track_number":
                    audio["tracknumber"] = str(new_data["track_number"])
                case "track_title":
                    audio["title"] = new_data["track_title"]
                case "year":
                    audio["date"] = new_data["year"]
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
        log.info(f"Couldn't get {file_path} album art -- {e}")
        return None

##############################################
################## QUERY #####################
##############################################

def get_album_mbinfo(mbid, allow_compilations=False):
    def _safe(fn, default):
        try:
            return fn()
        except Exception:
            return default
    try:
        result = mb.get_release_by_id(mbid, includes=["recordings", "artist-credits", "release-groups"])

    except mb.WebServiceError as e:
        log.info(f"  Search failed: {e}")
        return None

    release = result["release"]
    rg = release.get("release-group", {})
    if rg.get("primary-type") != "Album":
        return None
    if not allow_compilations and "Compilation" in rg.get("secondary-type-list", []):
        return None


    title = _safe(lambda: release["title"], "Unknown")
    year = _safe(lambda: release["date"][:4], "2000")
    artist_name = _safe(lambda: release["artist-credit"][0]["artist"]["name"], "Unknown")
    tracklist = _safe(lambda: {r["recording"]["title"]: r["position"] for r in release["medium-list"][0]["track-list"]}, {})
    recording_mbids = _safe(lambda: {r["recording"]["id"] for r in release["medium-list"][0]["track-list"]}, set())

    info = {
        "title": title,
        "year": year,
        "artist_name": artist_name,
        "tracklist": tracklist,
        "recording_mbids": recording_mbids,
        }

    return info

def get_track_mbinfo(mbid):
    try:
        result = mb.get_recording_by_id(mbid)
    except mb.WebServiceError as e:
        log.info(f"  Search failed: {e}")
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
        log.info(f"  No cover art found on release")
        return False
    else:
        save_path = f"{_ART_PATH}{album_id}.jpg"
        Path(save_path).write_bytes(image_data)
        log.info(f"  Saved: {save_path}  ({len(image_data)} bytes)")
        return True

##############################################
################ IDENTIFY ####################
##############################################
def fingerprint_id(file_path):
    try:
        for score, recording_id, title, artist in acoustid.match(acoustID_key, file_path):
            if score>ACOUSTID_SCORE_THRESHOLD:
                return recording_id
    except acoustid.AcoustidError as e:
        log.info(f"  AcoustID failed for {file_path}: {e}")
    return None

def find_match(track, tracklist):
    def _norm(s):
        s = re.sub(r"^\d+[\s._-]+", "", s)
        s = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s)
        s = s.lower()
        return re.sub(r"[^a-z0-9àâæçéèêëïîôœùûüÿäößñ]", "", s)

    def _partial_ratio(a, b):
        if not a or not b:
            return 0
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        match = SequenceMatcher(None, shorter, longer).find_longest_match()
        return (match.size / len(shorter)) * 100

    norm_track = _norm(track)
    best_score = 0
    best_match = None
    for t in tracklist:
        score = _partial_ratio(norm_track, _norm(t))
        if score > best_score:
            best_score = score
            best_match = t
    return best_match if best_score > FUZZY_MATCH_THRESHOLD else None

def get_track_mbid(medium, track_path="", track_name="", album_title="", artist_name=""):
    match medium:
        case "acoustid":
            mbid = fingerprint_id(track_path)
            if mbid:
                return mbid
            
        case "query":
            try:
                result = mb.search_recordings(
                    track_name,
                    artist=artist_name,
                    release=album_title,
                    )
            except mb.WebServiceError as e:
                log.info(f"  Search failed: {e}")
                return False
            
            rg_list = result.get("recording-list", [])
            
            if not rg_list:
                    log.info(f"  No results for '{artist_name} — {album_title}'")
                    return False
            
            score = rg_list[0].get('ext:score', rg_list[0].get('score', 0))
            if int(score) > MB_SCORE_THRESHOLD:
                    return rg_list[0]["id"]
    return None

def id_and_query_album(album, artist_name, track_paths):
     
    def _longest_tracks(min_duration=30):
        tracks = [(p, MP3(p).info.length) for p in track_paths]
        tracks = [t for t in tracks if t[1] >= min_duration]
        tracks.sort(key=lambda t: t[1], reverse=True)
        for path, _ in tracks:
            yield path
    
    def _tracklists_match(mb_titles, file_names, max_mismatch=0.2):
        if not file_names:
            return False
        mismatches = sum(1 for name in file_names if find_match(Path(name).stem, mb_titles) is None)
        return mismatches / len(file_names) <= max_mismatch
    
    def _query_mbid():
        q=f'artist:{artist_name} AND release:{album.title} AND status:official'
        try:
            result = mb.search_releases(
                query=q,
                limit=3
            )
        
        except mb.WebServiceError as e:
            log.info(f"  Search failed: {e}")
            return False

        rg_list = result.get("release-list", [])
        if not rg_list:
            log.info(f"  No results for '{artist_name} — {album.title}'")
            return False

        score = float(rg_list[0].get('ext:score') or rg_list[0].get('score') or 0)
        if int(score) > MB_SCORE_THRESHOLD:
            log.info(f"RGLIST ################################ {rg_list}")
            return (i["id"] for i in rg_list[:3])

    log.info(f"Identifying album {album.title} with AcoustID...")

    tried_releases = set()
    tried = []
    valid_count = 0
    best_match = None
    for sample_track in _longest_tracks():
        if valid_count >= MAX_ACOUSTID_CANDIDATES:
            break

        try:
            duration, fingerprint = acoustid.fingerprint_file(sample_track)
            response = acoustid.lookup(acoustID_key, fingerprint, duration, meta="releases recordings")
        except acoustid.AcoustidError as e:
            log.info(f"  AcoustID failed for {sample_track}: {e}")
            continue

        candidates = (
            release["id"]
            for result in response.get("results", [])
            if result.get("score", 0) >= ACOUSTID_SCORE_THRESHOLD
            for recording in result.get("recordings", [])
            for release in recording.get("releases", [])
        )

        for release_mbid in candidates:
            if release_mbid in tried_releases:
                continue
            if valid_count >= MAX_ACOUSTID_CANDIDATES:
                break
            tried_releases.add(release_mbid)

            album_meta = get_album_mbinfo(release_mbid)
            if album_meta is None:
                continue
            valid_count += 1
            tried.append(release_mbid)

            if not _tracklists_match(album_meta["tracklist"].keys(), track_paths):
                continue

            if best_match is None or len(album_meta["tracklist"]) > len(best_match[1]["tracklist"]):
                best_match = (release_mbid, album_meta)

    if best_match is not None:
        release_mbid, album_meta = best_match
        log.info(f"SUCCESS - Found {album_meta["title"]} by {album_meta["artist_name"]}")
        log.info(f"Album MBID : {release_mbid}")
        log.info(f"Tried MBIDs: {', '.join(tried)}")
        return album_meta

    log.info(f"AcoustID exhausted after {valid_count} valid candidate(s) - Trying to query...")
    album_mbid = _query_mbid()

    if album_mbid:
        best_match = None
        for mbid in album_mbid:
            album_meta = get_album_mbinfo(mbid)
            if album_meta is None:
                continue
            tried.append(mbid)

            if _tracklists_match(album_meta["tracklist"].keys(), track_paths):
                if best_match is None or len(album_meta["tracklist"]) > len(best_match[1]["tracklist"]):
                    best_match = (mbid, album_meta)

        if best_match is not None:
            mbid, album_meta = best_match
            log.info(f"SUCCESS - Found {album_meta["title"]} by {album_meta["artist_name"]}")
            log.info(f"Album MBID : {mbid}")
            log.info(f"Tried MBIDs: {', '.join(tried)}")
            return album_meta

        log.info(f"Query albums exhausted - retrying with compilations allowed...")
        best_match = None
        for mbid in album_mbid:
            if mbid in tried:
                continue
            album_meta = get_album_mbinfo(mbid, allow_compilations=True)
            if album_meta is None:
                continue
            tried.append(mbid)

            if _tracklists_match(album_meta["tracklist"].keys(), track_paths):
                if best_match is None or len(album_meta["tracklist"]) > len(best_match[1]["tracklist"]):
                    best_match = (mbid, album_meta)

        if best_match is not None:
            mbid, album_meta = best_match
            log.info(f"SUCCESS (compilation) - Found {album_meta["title"]} by {album_meta["artist_name"]}")
            log.info(f"Album MBID : {mbid}")
            log.info(f"Tried MBIDs: {', '.join(tried)}")
            return album_meta

    if tried:
        log.info(f"Tried MBIDs: {', '.join(tried)}")
    return None

##############################################
################## FIX #######################
##############################################
def fix_track_name(file, file_meta, tracklist, recording_mbids=None):
    def _resolve(track_mbid):
            if not track_mbid:
                return None
            tried.append(track_mbid)
            try:
                return get_track_mbinfo(track_mbid)
            except Exception:
                return None
    
    tried = []
    title_name = file_meta["title"] if file_meta["title"].lower()!="unknown" else os.path.splitext(os.path.basename(file))[0].rstrip("-_ ")
    match = find_match(title_name, tracklist)

    if match:
        return match

    track_mbid = get_track_mbid("acoustid", track_path=file)
    if track_mbid and recording_mbids and track_mbid not in recording_mbids:
        track_mbid = None

    track_meta = _resolve(track_mbid)

    if track_meta is None:
        track_mbid = get_track_mbid("query", track_name=title_name, album_title=file_meta["album"], artist_name=file_meta["artist"])
        track_meta = _resolve(track_mbid)

    if tried:
        log.info(f"Tried MBIDs: {', '.join(tried)}")
    return track_meta["title"] if track_meta else None

def fix(album, artist_name, track_paths):
    unresolved = []
    changed = {}
    
    log.info("Getting MBID...")
    album_meta = id_and_query_album(album, artist_name, track_paths)
    
    if album_meta is None:
        log.info(f"UNRESOLVED ALBUM - {album.display_title}")
        changed["check_state"]=2
        unresolved.extend(track_paths)
        return changed, unresolved

    if album.display_title != album_meta["title"]:
        log.info(f"Album title changed : {album.display_title} -> {album_meta["title"]}")
        changed["album_title"] = album_meta["title"]

    if album.year != album_meta["year"]:
        log.info(f"Album year changed : {album.year} -> {album_meta["year"]}")
        changed["year"] = album_meta["year"]
        changed["check_state"] = 1
        
    if artist_name != album_meta["artist_name"]: 
        log.info(f"Artist name changed : {artist_name} -> {album_meta["artist_name"]}")
        changed["artist_name"] = album_meta["artist_name"]

    for file in track_paths:
        log.info(f"Fixing file {file}")
        metachanges = {}
        file_meta = extract_meta(file)

        if file_meta is None:
            log.info(f"UNRESOLVED TRACK - NO METADATA TO WORK WITH")
            unresolved.append(file)
            continue
        
        resolved_name = file_meta["title"]
        
        if file_meta["title"] not in album_meta["tracklist"].keys():
            log.info("Fixing track title...")
            resolved_name = fix_track_name(file, file_meta, album_meta["tracklist"].keys(), album_meta.get("recording_mbids"))
            if not resolved_name:
                log.info(f"UNRESOLVED TRACK - {file_meta["title"]}")
                unresolved.append(file)
                continue
            
            log.info(f"SUCCESS - Track Title changed : {file_meta["title"]} -> {resolved_name}")
            metachanges["track_title"] = resolved_name

        if file_meta["artist"] != album_meta["artist_name"]:
            log.info(f"Track Artist name changed : {file_meta["artist"]} -> {album_meta["artist_name"]}")
            metachanges["artist_name"] = album_meta["artist_name"]

        if file_meta["album"] != album_meta["title"]:
            log.info(f"Track Album title changed : {file_meta["album"]} -> {album_meta["title"]}")
            metachanges["album_title"] = album_meta["title"]

        try:
            position_tracker = {"".join(k.split()): v for k, v in album_meta["tracklist"].items()}
            tracked_track = "".join(resolved_name.split())
        
            if file_meta["track_num"] != position_tracker[tracked_track]:
                log.info(f"Track Number changed : {file_meta["track_num"]} -> {position_tracker[tracked_track]}")
                metachanges["track_number"] = position_tracker[tracked_track]
        except:
            unresolved.append(file)
            log.info(f"UNRESOLVED TRACK - {file_meta["title"]} - MISSING TRACK NUMBER")
            continue

        if file_meta["year"] != album_meta["year"]:
            metachanges["year"] = album_meta["year"]
            
        if metachanges:
            apply_meta(file, metachanges)
            metachanges["check_state"] = 1
            changed[file] = metachanges

    return changed, unresolved
