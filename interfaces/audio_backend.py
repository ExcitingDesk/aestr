from abc import ABC, abstractmethod

class AudioBackend(ABC):
    @abstractmethod
    def load(self, path):
        ...

    @abstractmethod
    def is_busy(self):
        ...

    @abstractmethod
    def play(self):
        ...

    @abstractmethod
    def pause(self):
        ...    

    @abstractmethod
    def unpause(self):
        ...

    @abstractmethod
    def stop(self):
        ...