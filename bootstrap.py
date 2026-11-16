import lib_db as datab
import library
import search
from dataclasses import dataclass
from desktop.pygame_audioBE import pygameAudioBackEnd
from desktop.filesystem_library_source import FileSysLibSource
from interfaces.audio_backend import AudioBackend
from interfaces.library_source import LibrarySource

from clean_aest import clean_aest


@dataclass
class AppContext:
    audio_backend : AudioBackend
    library_source: LibrarySource

def bootstrap():
    _LIB_PATH = "/home/adam/Music/"

    #clean_aest(_LIB_PATH)

    datab.init_db(_LIB_PATH)
    filesyslib = FileSysLibSource(datab.get_lib_path(), datab.get_local_path())
    library.sync_library(filesyslib)
    search.init_cache()

    return AppContext(audio_backend=pygameAudioBackEnd(), library_source=filesyslib)


def shutdown():
    datab.shut_conn()
