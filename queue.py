class Queue:
    def __init__(self):
        self.current_queue = []
        self.playing = ""

    def set_queue(self, queue:list):
        self.current_queue = queue
    
    def add_queue(self, trackID_list:list):
        for id in trackID_list: self.current_queue.append(i) 
    
    def play_next(self, trackID_list:list):
        playing = self.current_queue.index(self.playing)+1
        for id in trackID_list:
            self.current_queue.insert(playing, id)
            playing+=1
    
    def shuffle(self):
        #   Fisher-Yates shuffle algorithm
        pass