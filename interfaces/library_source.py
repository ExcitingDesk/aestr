from abc import ABC, abstractmethod

class LibrarySource(ABC):

    @abstractmethod
    def discover(self):
        ...

    @abstractmethod
    def stage(self):
        ...