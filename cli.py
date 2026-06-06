import library
import global_var as gb
from player import Player
import random

lauf = Player()
library.sync_library()
library.organize_folder()
track_ids = list(gb.lib.tracks.keys())
random.shuffle(track_ids)
lauf.queue.set_queue(track_ids)


# SEARCH PROTOTYPE -
# for i in gb.lib.tracks.keys():
#     if gb.lib.tracks[i].title == "Mon mal persiste":
#         print(i) 


# TO FIX : WHEN LAUNCHED WITH A LOADED QUEUE MUSIC 
# STARTS PLAYING AUTOMATICALLY

while True:
    cmd = input()
    if cmd == "show":
        for i in track_ids:
            print(i)

    if cmd == "next":
        lauf.queue.enqueue(["7bc0dcd7f6fde3b0"])

    if cmd == "play":
        lauf.queue.playing = lauf.queue.current_queue[-1]
        lauf.play(lauf.queue.playing)

    if cmd == "queue":
        lauf.play(lauf.queue.playing)
    
    if cmd == "pause":
        lauf.pause()

    if cmd == "resume":
        lauf.unpause()
    
    if cmd == "skip":
        lauf.skip()
