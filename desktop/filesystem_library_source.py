from interfaces.library_source import LibrarySource, TrackCandidate
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from pathlib import Path
from dataclasses import dataclass
import shutil

class FileSysLibSource(LibrarySource):
    def __init__(self, lib_path, local_path):
        self.lib_path = lib_path
        self.local_path = local_path

    def discover(self):
        for file in Path(self.lib_path).rglob("*"):
            if file.is_file() and file.suffix in [".mp3", ".wav"]:
                yield TrackCandidate(uri=f"{file}")
    
    def stage(self, track, album_title, artist_name):
        dst_dir = Path(self.local_path) / artist_name / album_title
        dst_file = dst_dir / Path(track.path).name

        if Path(track.path).parent != dst_dir:
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(track.path, dst_file)
            track.path = str(dst_file)