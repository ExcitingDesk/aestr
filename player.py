import pygame
import global_var as gb

class Player:
    def __init__(self):
        self.queue = []
        self.playing = ""

        try:
            pygame.mixer.init()
        except pygame.error as e:
            print("Audio init failed! : ", e)
            return

    def play(track_id):
        track = gb.lib.tracks[track_id]

        pygame.mixer.music.load(track.path)
        pygame.mixer.music.play()

        self.playing = track_id
    