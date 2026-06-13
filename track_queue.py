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