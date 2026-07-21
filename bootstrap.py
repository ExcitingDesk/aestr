import lib_db as datab
import library
import search
from dataclasses import dataclass
from desktop.pygame_audioBE import pygameAudioBackEnd
from desktop.filesystem_library_source import FileSysLibSource

@dataclass
class AppContext:
    audio_backend : object
    library_source: object

def bootstrap():
    _LIB_PATH = "/home/adam/Music/"

    datab.init_db(_LIB_PATH)
    library.sync_library(FileSysLibSource(datab.get_lib_path(), datab.get_local_path()))
    search.init_cache()

    return AppContext(audio_backend=pygameAudioBackEnd(), library_source=FileSysLibSource(datab.get_lib_path(), datab.get_local_path()))


def shutdown():
    datab.shut_conn()
