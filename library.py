from mutagen.easyid3 import EasyID3
from pathlib import Path
import global_var as gb
import os
import shutil

path = gb.path
lib = gb.library

def sync_library():
    for file in Path(path).rglob("*"):
        if file.is_file() and file.suffix in [".mp3"]:
            try:
                audio = EasyID3(file)
            except Exception:
                continue

            artist = audio.get("artist", [None])[0]
            album = audio.get("album", [None])[0]
            title = audio.get("title", [None])[0]

            if not artist in lib.keys():
                lib.update({artist : {album : [title]}})
            elif not album in lib[artist].keys():
                lib[artist].update({album : [title]})
            elif not title in lib[artist][album]:
                lib[artist][album].append(title)
                lib[artist][album].append(file)

def organize_folder():
    if not Path(gb.local_path).exists() : Path(gb.local_path).mkdir()
    for i in lib.keys():
       Path(gb.local_path+"/"+i).mkdir()
       


sync_library()
organize_folder()