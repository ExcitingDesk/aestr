import lib_db as datab
import library
import search
from dataclasses import dataclass
from desktop.pygame_audioBE import pygameAudioBackEnd

@dataclass
class AppContext:
    audio_backend : object

def bootstrap():
    datab.init_conn()
    datab.setup_db()
    datab.user_conf()
    library.sync_library()
    search.init_cache()

    return AppContext(audio_backend=pygameAudioBackEnd())


def shutdown():
    datab.shut_conn()
