import random

class Queue:
    def __init__(self):
        self.current_queue = []
        self.playing = ""

    def set_queue(self, queue:list):
        self.current_queue = queue
        self.playing = queue[0]
    
    def enqueue(self, trackID_list:list):
        for id in trackID_list: self.current_queue.append(id) 
    
    def play_next(self, trackID_list:list):
        playing = self.current_queue.index(self.playing)+1
        for id in trackID_list:
            self.current_queue.insert(playing, id)
            playing+=1
    
    def shuffle(self):
        for i in range(len(self.current_queue) - 1, 0, -1):
            j = random.randint(0, i)
            self.current_queue[i], self.current_queue[j] = self.current_queue[j], self.current_queue[i]

    def remove(self, track_id):
        if track_id in self.current_queue:
            self.current_queue.remove(track_id)

    def move_to_next(self, track_id):
        """Move an existing track to the position immediately after the currently playing one."""
        if track_id in self.current_queue:
            self.current_queue.remove(track_id)
        if self.playing and self.playing in self.current_queue:
            idx = self.current_queue.index(self.playing) + 1
        else:
            idx = 0
        self.current_queue.insert(idx, track_id)