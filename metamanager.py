from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import musicbrainzngs as mb
import lib_db as datab
from pathlib import Path

mb.set_useragent("Aestr", "0.1", "khachani.a.a@gmail.com")

def extract_meta(candidate):
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

        metadata = [title, artist, album, year, track_num]
        if metadata: return metadata
        else: return None

def extract_art(file_path, album, art_dir):
    try:
        audio = MP3(file_path.uri)
        if audio.tags is None:
            return False

        apics = audio.tags.getall("APIC")
        if not apics:
            return False

        art = next((a for a in apics if a.type == 3), apics[0])

        ext = "jpg" if "jpeg" in art.mime else "png"
        save_path = Path(f"{art_dir}{album.id}.{ext}")
        save_path.write_bytes(art.data)
        album.cover=True
        return True
    except Exception as e:
        print(f"Couldn't get {file_path} album art -- {e}")
        return None

def fix(candidate):
    ...
    
def get_album_art(album_title, artist_name, album_id):
    _ART_PATH = datab.get_art_path()
    try:
        result = mb.search_releases(
            artist=artist_name,
            release=album_title,
            status="official",
            limit=5
        )
    except mb.WebServiceError as e:
        print(f"  Search failed: {e}")
        return False
    
    rg_list = result.get("release-list", [])
    if not rg_list:
        print(f"  No results for '{artist_name} — {album_title}'")
        return False
    
    best = rg_list[0]
    
    try:
        image_data = mb.get_image_front(best["id"], size=1200)
    except mb.ResponseError:
        releases = best.get("release-list", [])
        if not releases:
            print(f"  No cover art found on release")
            return False
    else:
        save_path = f"{_ART_PATH}{album_id}.jpg"
        Path(save_path).write_bytes(image_data)
        print(f"  Saved: {save_path}  ({len(image_data)} bytes)")
        return True