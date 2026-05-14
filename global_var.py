from mutagen.mp3 import MP3
import hashlib

path = "/home/adam/Music"
local_path = path + "/Aestr"

lib=None

def gen_track_id(file_path, album: str = "") -> str:
    audio = MP3(file_path)
    offset = audio.info.frame_offset
    
    with open(file_path, "rb") as f:
        f.seek(offset)
        chunk = f.read(64_000)
    
    audio_hash = hashlib.sha256(chunk).hexdigest()[:12]
    album_hash = hashlib.sha256(album.strip().lower().encode()).hexdigest()[:4]
    
    return audio_hash + album_hash

def gen_album_id(artist: str, album: str) -> str: return f"{artist.strip().lower()}|{album.strip().lower()}"