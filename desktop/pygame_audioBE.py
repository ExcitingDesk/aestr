import pygame
from interfaces.audio_backend import AudioBackend

class pygameAudioBackEnd(AudioBackend):
    def __init__(self):
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print("Audio init failed! : ", e)
            return
        
    
    def load(self, path):
        pygame.mixer.music.load(path)

    def is_busy(self):
        return pygame.mixer.music.get_busy()

    def play(self):
        pygame.mixer.music.play()

    def pause(self):
        pygame.mixer.music.pause()
    
    def unpause(self):
        pygame.mixer.music.unpause()

    def stop(self):
        pygame.mixer.music.stop()