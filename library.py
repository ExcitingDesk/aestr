from mutagen.easyid3 import EasyID3
from pathlib import Path
from dataclasses import dataclass, field
import global_var as gb
import shutil

# organize_folder depends on sync_library to run first

path = gb.path

@dataclass
class Track:
    title: str
    artist: str
    album: str
    path: str

@dataclass
class Album:
    title: str
    artist: str
    year: int
    tracks: list

@dataclass
class Lib:
    artists: dict = field(default_factory=dict)
    albums: dict = field(default_factory=dict)
    tracks: dict = field(default_factory=dict)



def sync_library():
    lib = Lib()
    seen_ids = {} 

    for file in Path(path).rglob("*"):
        # if Path(gb.local_path).name in file.parts: continue
        if file.is_file() and file.suffix in [".mp3"]:

            try:
                audio = EasyID3(file)
            except Exception as e:
                print(f"Skipped {file} -- {e}")
                next

            artist = audio.get("artist", ["Unknown"])[0]
            album = audio.get("album", ["Unknown"])[0]
            title = audio.get("title", ["Unknown"])[0]
            year = audio.get("year", ["Unknown"])[0]

            track_id = gb.gen_track_id(file)
            album_id = gb.gen_album_id(artist, album)

            if not artist in lib.artists.keys(): lib.artists[artist]=[album]
            else: lib.artists[artist].append(album) 

            if album_id in lib.albums.keys(): lib.albums[album_id].tracks.append(track_id)
            else : lib.albums[album_id] = Album(album, artist, year, [track_id])

            if not track_id in lib.tracks : lib.tracks[track_id] = Track(title, artist, album, file)
            
    gb.lib = lib    

def organize_folder():
    lib = gb.lib
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
