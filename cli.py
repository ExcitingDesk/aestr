import library
import global_var as gb
from player import Player

player = Player()

tracks = list(gb.lib.tracks.keys())
if not tracks:
    print("No tracks found in library.")
    exit()

track_id = tracks[0]
print(f"Playing: {gb.lib.tracks[track_id].title} — {gb.lib.tracks[track_id].artist}")
player.play(track_id)

while True:
    cmd = input("\n[p]ause  [u]npause  [s]top  [q]uit > ").strip().lower()
    if cmd == "p":
        player.pause()
        print("Paused.")
    elif cmd == "u":
        player.unpause()
        print("Resumed.")
    elif cmd == "s":
        player.stop()
        print("Stopped.")
    elif cmd == "q":
        player.stop()
        break
