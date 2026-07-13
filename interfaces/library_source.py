from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TrackCandidate:
    uri: str

class LibrarySource(ABC):

    @abstractmethod
    def discover(self):
        ...

    @abstractmethod
    def stage(self, track, album_title, artist_name):
        ...