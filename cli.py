import cmd
import lib_db as datab
import library
import search
import bootstrap
from player import Player

PAGE_SIZE = 10
DIVIDER = "─" * 50


class AestrCLI(cmd.Cmd):
    intro = "Type 'help' for commands."
    prompt = "(aestr) "

    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.player = Player(self.ctx.audio_backend)
        self.mode = "main"
        self.current_items = []
        self.page = 0
        self.library_type = None
        self.album_tracks = []


    def _render_main(self):
        playing_id = self.player.queue.playing
        print(DIVIDER)
        if not playing_id:
            print(" Nothing playing.")
        else:
            track = datab.get_track_info(playing_id)
            album = datab.get_album_info(track["album"]) if track else None
            artist = datab.get_artist_info(album["artist"]) if album else None
            if not track or not album or not artist:
                print(" Nothing playing.")
                print(DIVIDER)
                return
            status = "⏸" if self.player.paused else "▶"
            print(f" {status}  {track['title']}")
            print(f"     {album['display_title']} — {artist['display_name']}")
            q = self.player.queue.current_queue
            if playing_id in q:
                idx = q.index(playing_id) + 1
                if idx < len(q):
                    nxt = datab.get_track_info(q[idx])
                    if nxt:
                        print(f"\n     Playing next: {nxt['title']}")
        print(DIVIDER)

    def _render_library_select(self):
        print("\n[albums] or [tracks]\n")

    def _render_library_items(self):
        items = self.current_items
        start = self.page * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(items))
        label = "Albums" if self.library_type == "albums" else "Tracks"
        print(f"\n{label} ({start + 1}–{end} of {len(items)}):")
        for idx in range(start, end):
            _, title, _ = items[idx]
            print(f"  {idx + 1}. {title}")
        print()

    def _render_album_view(self):
        print(f"\nTracks ({len(self.album_tracks)}):")
        for i, (_, title, _) in enumerate(self.album_tracks, start=1):
            print(f"  {i}. {title}")
        print()

    def _render_queue(self):
        q = self.player.queue.current_queue
        playing = self.player.queue.playing
        if not q:
            print("\nQueue is empty.\n")
            return
        start = self.page * PAGE_SIZE
        end = min(start + PAGE_SIZE, len(q))
        print(f"\nQueue ({start + 1}–{end} of {len(q)}):")
        for idx in range(start, end):
            tid = q[idx]
            info = datab.get_track_info(tid)
            title = info["title"] if info else "<unknown>"
            marker = "▶ " if tid == playing else "  "
            print(f"  {marker}{idx + 1}. {title}")
        print()

    def _render_search_results(self):
        if not self.current_items:
            print("\nNo results.\n")
            return
        print(f"\nResults ({len(self.current_items)}):")
        for i, (_, label, kind) in enumerate(self.current_items, start=1):
            print(f"  {i}. {label}  [{kind}]")
        print()

    def _render(self):
        {
            "main": self._render_main,
            "library_select": self._render_library_select,
            "library_items": self._render_library_items,
            "album_view": self._render_album_view,
            "queue_view": self._render_queue,
            "search_results": self._render_search_results,
        }.get(self.mode, self._render_main)()

    def _sync_prompt(self):
        self.prompt = {
            "main": "(aestr) ",
            "library_select": "(library) ",
            "library_items": f"({self.library_type}) ",
            "album_view": "(album) ",
            "queue_view": "(queue) ",
            "search_results": "(search) ",
        }.get(self.mode, "(aestr) ")

    # ── cmd.Cmd overrides ────────────────────────────────────────────────────

    def preloop(self):
        self._render()

    def postcmd(self, stop, line):
        if not stop:
            self._sync_prompt()
            self._render()
        return stop

    def emptyline(self):
        pass

    def onecmd(self, line):
        try:
            return super().onecmd(line)
        except Exception as e:
            print(f"Error: {e}")
            return False

    _HELP = {
        "main": (
            "play     - Play / pause\n"
            "next     - Next track\n"
            "previous - Previous track\n"
            "search   - Search the library  [search <query>]\n"
            "library  - Browse library\n"
            "queue    - View queue\n"
            "shuffle  - Shuffle queue\n"
            "sync     - Resync library\n"
            "exit     - Quit"
        ),
        "library_select": (
            "albums - Browse albums\n"
            "tracks - Browse tracks\n"
            "back   - Go back"
        ),
        "library_items_albums": (
            "play      - Play album        [play <n>]\n"
            "queuenext - Play next         [queuenext <n>]\n"
            "queueadd  - Add to queue      [queueadd <n>]\n"
            "view      - View tracks       [view <n>]\n"
            "np / pp   - Next / prev page\n"
            "back      - Go back"
        ),
        "library_items_tracks": (
            "play      - Play track        [play <n>]\n"
            "queuenext - Play next         [queuenext <n>]\n"
            "queueadd  - Add to queue      [queueadd <n>]\n"
            "np / pp   - Next / prev page\n"
            "back      - Go back"
        ),
        "album_view": (
            "play      - Play track        [play <n>]\n"
            "queuenext - Play next         [queuenext <n>]\n"
            "queueadd  - Add to queue      [queueadd <n>]\n"
            "back      - Go back"
        ),
        "queue_view": (
            "queuenext - Move to next      [queuenext <n>]\n"
            "remove    - Remove track      [remove <n>]\n"
            "np / pp   - Next / prev page\n"
            "back      - Go back"
        ),
        "search_results": (
            "play      - Play item         [play <n>]\n"
            "queuenext - Play next         [queuenext <n>]\n"
            "queueadd  - Add to queue      [queueadd <n>]\n"
            "back      - Go back"
        ),
    }

    def do_help(self, arg):
        key = self.mode
        if self.mode == "library_items":
            key = f"library_items_{self.library_type}"
        print("\n" + self._HELP.get(key, "") + "\n")

    # ── shared helpers ───────────────────────────────────────────────────────

    def _resolve(self, arg, items=None):
        """Parse a 1-based number from arg, return the item tuple or None."""
        if items is None:
            items = self.current_items
        try:
            n = int(arg.strip())
        except ValueError:
            print("Expected a number.")
            return None
        if not (1 <= n <= len(items)):
            print(f"Pick a number between 1 and {len(items)}.")
            return None
        return items[n - 1]

    def _play_item(self, item_id, kind):
        if kind == "track":
            self.player.play(item_id)
            info = datab.get_track_info(item_id)
            if info:
                print(f"Now playing: {info['title']}")
        elif kind == "album":
            track_ids = list(datab.list_album_tracks(item_id).keys())
            if not track_ids:
                print("Album has no tracks.")
                return
            self.player.play_album(track_ids)
            info = datab.get_track_info(track_ids[0])
            if info:
                print(f"Now playing: {info['title']}")

    def _queuenext_item(self, item_id, kind):
        ids = list(datab.list_album_tracks(item_id).keys()) if kind == "album" else [item_id]
        try:
            self.player.queue.play_next(ids)
        except (ValueError, IndexError):
            self.player.queue.enqueue(ids)

    def _queueadd_item(self, item_id, kind):
        ids = list(datab.list_album_tracks(item_id).keys()) if kind == "album" else [item_id]
        self.player.queue.enqueue(ids)

    # ── main screen ──────────────────────────────────────────────────────────

    def do_play(self, arg):
        """play — toggle play/pause on the main screen; play <n> to play an item in submenus"""
        if self.mode == "main":
            if self.player.paused:
                self.player.unpause()
            elif self.player.queue.playing:
                self.player.pause()
            else:
                print("Nothing to play.")
            return
        arg = arg.strip()
        if not arg:
            print("Usage: play <number>")
            return
        if self.mode in ("library_items", "search_results"):
            item = self._resolve(arg)
            if item:
                self._play_item(item[0], item[2])
        elif self.mode == "album_view":
            item = self._resolve(arg, self.album_tracks)
            if item:
                self._play_item(item[0], item[2])
        else:
            print("'play' is not available in this screen.")

    def do_pause(self, arg):
        """pause — pause playback"""
        self.player.pause()

    def do_next(self, arg):
        """next — skip to the next track"""
        self.player.skip()

    def do_previous(self, arg):
        """previous — go back to the previous track"""
        self.player.previous()

    def do_shuffle(self, arg):
        """shuffle — shuffle the current queue"""
        if not self.player.queue.current_queue:
            print("Queue is empty.")
            return
        self.player.queue.shuffle()
        print("Queue shuffled.")

    def do_sync(self, arg):
        """sync — rescan your music library"""
        print("Syncing…")
        library.sync_library(self.ctx.library_source)
        search.init_cache()
        print("Done.")

    def do_search(self, arg):
        """search <query> — search the library"""
        query = arg.strip()
        if not query:
            print("Usage: search <query>")
            return
        artists, albums, tracks = search.search(query, "global")
        seen = set()
        items = []
        for _name, _score, artist_id in artists:
            artist_info = datab.get_artist_info(artist_id)
            if not artist_info:
                continue
            for album_id, (title, _year) in datab.list_artist_albums(artist_id).items():
                if album_id not in seen:
                    seen.add(album_id)
                    items.append((album_id, f"{title} - {artist_info['display_name']}", "album"))
        for title, _score, album_id in albums:
            if album_id not in seen:
                seen.add(album_id)
                album_info = datab.get_album_info(album_id)
                artist_info = datab.get_artist_info(album_info["artist"]) if album_info else None
                label = f"{title} - {artist_info['display_name']}" if artist_info else title
                items.append((album_id, label, "album"))
        for title, _score, track_id in tracks:
            if track_id not in seen:
                seen.add(track_id)
                track_info = datab.get_track_info(track_id)
                album_info = datab.get_album_info(track_info["album"]) if track_info else None
                artist_info = datab.get_artist_info(album_info["artist"]) if album_info else None
                label = f"{title} - {artist_info['display_name']}" if artist_info else title
                items.append((track_id, label, "track"))
        if not items:
            print("No results.")
            return
        self.current_items = items
        self.mode = "search_results"

    def do_library(self, arg):
        """library — browse the music library"""
        self.mode = "library_select"

    def do_queue(self, arg):
        """queue — view and manage the play queue"""
        self.mode = "queue_view"
        self.page = 0

    def do_exit(self, arg):
        """exit — quit Aestr"""
        self.player.stop()
        bootstrap.shutdown()
        print("Goodbye.")
        return True

    # ── library / search submenus ────────────────────────────────────────────

    def do_albums(self, arg):
        """albums — list all albums alphabetically"""
        if self.mode != "library_select":
            print("Type 'library' first.")
            return
        self.current_items = [(aid, title, "album") for aid, title in search.all_albums()]
        self.library_type = "albums"
        self.mode = "library_items"
        self.page = 0

    def do_tracks(self, arg):
        """tracks — list all tracks alphabetically"""
        if self.mode != "library_select":
            print("Type 'library' first.")
            return
        self.current_items = [(tid, title, "track") for tid, title in search.all_tracks()]
        self.library_type = "tracks"
        self.mode = "library_items"
        self.page = 0

    def do_view(self, arg):
        """view <n> — view all tracks in an album (albums screen only)"""
        if self.mode != "library_items" or self.library_type != "albums":
            print("'view' is only available in the albums screen.")
            return
        item = self._resolve(arg)
        if not item:
            return
        album_id = item[0]
        rows = datab.list_album_tracks(album_id)
        if not rows:
            print("Album has no tracks.")
            return
        self.album_tracks = [(tid, title, "track") for tid, title in rows.items()]
        self.mode = "album_view"

    def do_queuenext(self, arg):
        """queuenext <n> — add item to play next; in queue screen: move track to next position"""
        if self.mode in ("library_items", "search_results"):
            item = self._resolve(arg)
            if item:
                self._queuenext_item(item[0], item[2])
        elif self.mode == "album_view":
            item = self._resolve(arg, self.album_tracks)
            if item:
                self._queuenext_item(item[0], item[2])
        elif self.mode == "queue_view":
            q = self.player.queue.current_queue
            item = self._resolve(arg, [(tid, "", "") for tid in q])
            if item:
                self.player.queue.move_to_next(item[0])
        else:
            print("'queuenext' is not available here.")

    def do_queueadd(self, arg):
        """queueadd <n> — add item to the end of the queue"""
        if self.mode in ("library_items", "search_results"):
            item = self._resolve(arg)
            if item:
                self._queueadd_item(item[0], item[2])
        elif self.mode == "album_view":
            item = self._resolve(arg, self.album_tracks)
            if item:
                self._queueadd_item(item[0], item[2])
        else:
            print("'queueadd' is not available here.")

    def do_remove(self, arg):
        """remove <n> — remove a track from the queue"""
        if self.mode != "queue_view":
            print("'remove' is only available in the queue screen.")
            return
        q = self.player.queue.current_queue
        item = self._resolve(arg, [(tid, "", "") for tid in q])
        if not item:
            return
        track_id = item[0]
        if track_id == self.player.queue.playing:
            self.player.stop()
        self.player.queue.remove(track_id)
        if self.page > 0 and self.page * PAGE_SIZE >= len(q):
            self.page -= 1

    def do_np(self, arg):
        """np — next page"""
        if self.mode == "library_items":
            if (self.page + 1) * PAGE_SIZE < len(self.current_items):
                self.page += 1
            else:
                print("Already on the last page.")
        elif self.mode == "queue_view":
            if (self.page + 1) * PAGE_SIZE < len(self.player.queue.current_queue):
                self.page += 1
            else:
                print("Already on the last page.")
        else:
            print("No pages here.")

    def do_pp(self, arg):
        """pp — previous page"""
        if self.mode in ("library_items", "queue_view"):
            if self.page > 0:
                self.page -= 1
            else:
                print("Already on the first page.")
        else:
            print("No pages here.")

    def do_back(self, arg):
        """back — return to the previous screen"""
        if self.mode == "library_select":
            self.mode = "main"
        elif self.mode == "library_items":
            self.mode = "library_select"
            self.current_items = []
            self.library_type = None
        elif self.mode == "album_view":
            self.mode = "library_items"
            self.album_tracks = []
        elif self.mode in ("queue_view", "search_results"):
            self.mode = "main"
        else:
            print("Already on the main screen.")
        self.page = 0


def main():
    ctx = bootstrap.bootstrap()
    try:
        AestrCLI(ctx).cmdloop()
    except KeyboardInterrupt:
        print()
        bootstrap.shutdown()


if __name__ == "__main__":
    main()
