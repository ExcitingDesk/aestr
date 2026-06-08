from rapidfuzz import process, fuzz, utils
import lib_db as db

def init_cache():
    _search_cache = db.build_cache()

    global _artist_cache
    global _albums_cache
    global _tracks_cache

    _artist_cache = _search_cache["artists"]
    _album_cache = _search_cache["albums"]
    _track_cache = _search_cache["tracks"]

def search(query, tracks):
    pass