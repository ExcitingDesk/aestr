from interfaces.library_source import LibrarySource, TrackCandidate
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
    
    def stage(self, track, album_title, artist_name, del_safe):
        dst_dir = Path(self.local_path) / artist_name / album_title
        dst_file = dst_dir / Path(track.path).name
        
        if Path(track.path).parent != dst_dir:
            src_dir = Path(track.path).parent
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(track.path, dst_file)
            track.path = str(dst_file)

            if not any(src_dir.iterdir()) and del_safe=='Y':
                src_dir.rmdir()
                print(f"Empty folder {src_dir} deleted")