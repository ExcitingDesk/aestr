from rapidfuzz import process, fuzz, utils
import lib_db as db

def init_cache():
    _search_cache = db.build_cache()

    global _artist_cache
    global _album_cache
    global _track_cache

    _artist_cache = _search_cache["artists"]
    _album_cache = _search_cache["albums"]
    _track_cache = _search_cache["tracks"]


def search(query, search_type):
    global _artist_results
    global _album_results
    global _track_results

    #OUTPUT EXAMPLE : [("NAME SEARCHED"), SCORE, SEARCHED ID]

    match search_type:
        case "artist":
            _artist_results = process.extract(query, 
                                            _artist_cache, 
                                            scorer=fuzz.WRatio,
                                            processor=utils.default_process,
                                            limit=5,
                                            score_cutoff=70)
            return _artist_results

        case "album":
            _album_results = process.extract(query, 
                                    _album_cache, 
                                    scorer=fuzz.WRatio,
                                    processor=utils.default_process,
                                    limit=5,
                                    score_cutoff=70)
            return _album_results

        case "track":
            _track_results = process.extract(query, 
                                    _track_cache, 
                                    scorer=fuzz.WRatio,
                                    processor=utils.default_process,
                                    limit=5,
                                    score_cutoff=70)
            return _track_results
    

        case "global":
            _artist_results = search(query, "artist")
            _album_results = search(query, "album")
            _track_results = search(query, "track")

            return (_artist_results, _album_results, _track_results)

        case _:
            raise ValueError(f"Unknown query type: {search_type!r}")


def all_albums():
    return sorted(_album_cache.items(), key=lambda x: x[1].casefold())


def all_tracks():
    return sorted(_track_cache.items(), key=lambda x: x[1].casefold())
    

    
    