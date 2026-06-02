import pygame
import global_var as gb
from track_queue import Queue

class Player:
    def __init__(self):
        self.queue = Queue()
        self.paused = False

        try:
            pygame.mixer.init()
        except pygame.error as e:
            print("Audio init failed! : ", e)
            return

    def play(self, track_id):
        track = gb.lib.tracks[track_id]

        pygame.mixer.music.load(track.path)
        pygame.mixer.music.play()

        self.queue.playing = track_id
        self.paused = False

    def skip(self):
        if not self.queue or self.playing not in self.queue:
            self.stop()
            return
        current_index = self.queue.index(self.playing)
        if current_index + 1 >= len(self.queue):
            self.stop()
            return
        self.play(self.queue[current_index + 1])

    def pause(self):
        if not self.paused and pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.paused = True

    def unpause(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

    def stop(self):
        pygame.mixer.music.stop()
        self.playing = ""
        self.paused = False
    