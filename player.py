from interfaces.audio_backend import AudioBackend
import lib_db as datab
from track_queue import Queue
import threading

class Player:
    def __init__(self, backend: AudioBackend):
        self.queue = Queue()
        self.paused = False

        self.audioBackend = backend
        threading.Thread(target=self._event_loop, daemon=True).start()

    def _event_loop(self):
        import time
        while True:
            if not self.paused and self.queue.playing != "" and not self.audioBackend.is_busy():
                self.skip()
            time.sleep(0.1)

    def play(self, track_id):
        track = datab.get_track_info(track_id)
        if track is None:
            return

        self.audioBackend.load(track["path"])
        self.audioBackend.play()

        self.queue.playing = track_id
        self.paused = False

    def skip(self):
        if self.queue.playing != "" and self.queue.current_queue != []:
            curr_queue = self.queue.current_queue
            try:
                playing_ind = curr_queue.index(self.queue.playing)
            except ValueError:
                self.stop()
                return
            try:
                self.queue.playing = curr_queue[playing_ind+1]
            except IndexError:
                self.stop()
            else:
                self.play(self.queue.playing)

    def previous(self):
        if self.queue.playing != "" and self.queue.current_queue != []:
            curr_queue = self.queue.current_queue
            try:
                playing_ind = curr_queue.index(self.queue.playing)
            except ValueError:
                return
            if playing_ind > 0:
                self.queue.playing = curr_queue[playing_ind - 1]
                self.play(self.queue.playing)
        
    def pause(self):
        if not self.paused and self.audioBackend.is_busy():
            self.audioBackend.pause()
            self.paused = True

    def unpause(self):
        if self.paused:
            self.audioBackend.unpause()
            self.paused = False

    def play_album(self, track_ids):
        """Start playing an album, inserting its tracks in place of the current song."""
        if not track_ids:
            return
        first, rest = track_ids[0], track_ids[1:]
        q = self.queue.current_queue
        if self.queue.playing and self.queue.playing in q:
            pos = q.index(self.queue.playing)
            q[pos] = first
            for i, tid in enumerate(rest, start=1):
                q.insert(pos + i, tid)
        else:
            self.queue.current_queue = list(track_ids) + q
        self.play(first)

    def stop(self):
        self.audioBackend.stop()
        self.queue.playing = ""
        self.paused = False
    