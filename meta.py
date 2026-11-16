from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from pathlib import Path
import mimetypes

from logger import get_logger

log = get_logger(__name__)


def extract_meta(file):
    try:
        audio = EasyID3(file)
    except Exception as e:
        log.info(f"Skipped {file} -- {e}")
        return None

    metadata = {
        "title": audio.get("title", ["Unknown"])[0],
        "artist": audio.get("artist", ["Unknown"])[0],
        "album": audio.get("album", ["Unknown"])[0],
        "year": audio.get("date", [None])[0],
        "track_num": audio.get("tracknumber", ["0"])[0],
    }

    if metadata["year"] is None: metadata["year"]=ID3(file).getall("TYER")[0] if ID3(file).getall("TYER")!=[] else None
    metadata['length'] = MP3(file).info.length

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
