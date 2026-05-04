from dataclasses import dataclass

path = "/home/adam/Music"
local_path = path + "/Aestr"


##  LIBRARY ##
@dataclass
class Track:
    title: str
    artist: str
    album: str
    path: str

def update_log():
    pass
## USE CASES ##
## FILTER : ALL_DAMN_TRACKS = [TRACK FOR TRACK IN LIBRARY IF TRACK.ALBUM = "DAMN."]