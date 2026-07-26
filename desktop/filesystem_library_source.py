from interfaces.library_source import LibrarySource, TrackCandidate
from pathlib import Path
import shutil

class FileSysLibSource(LibrarySource): 
    def __init__(self, lib_path, local_path):
        self.lib_path = lib_path
        self.local_path = local_path

    def discover(self):
        for file in Path(self.lib_path).rglob("*"):
            if file.is_file() and file.suffix in [".mp3", ".wav"]:
                yield TrackCandidate(uri=f"{file}")
    
    def stage(self, track, album_title, artist_name, del_safe='N'):
        dst_dir = Path(self.local_path) / artist_name / album_title
        dst_file = dst_dir / Path(track.path).name
        
        if Path(track.path).parent != dst_dir: 
            src_dir = Path(track.path).parent
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(track.path, dst_file)
            track.path = str(dst_file)

            if del_safe == 'Y':
                lib_root = Path(self.lib_path).resolve()
                current = src_dir.resolve()
                while current != lib_root and lib_root in current.parents and not any(current.iterdir()):
                    current.rmdir()
                    print(f"Empty folder {current} deleted")
                    current = current.parent
                    
    def flag(self):
        flagged_files = []
        lib_root = Path(self.lib_path)

        for folder in [lib_root, *lib_root.rglob("*")]:
            if not folder.is_dir():
                continue
            audio_files = [f for f in folder.iterdir()
                           if f.is_file() and f.suffix in [".mp3", ".wav"]]
            if len(audio_files) < 4:
                flagged_files.extend(f"{f}" for f in audio_files)

        return flagged_files