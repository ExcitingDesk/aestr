from difflib import SequenceMatcher
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from dotenv import load_dotenv
import os
import re
import musicbrainzngs as mb
import acoustid

from logger import get_logger

log = get_logger(__name__)

mb.set_useragent("Aestr", "0.1", "khachani.a.a@gmail.com")

MB_SCORE_THRESHOLD = 85
ACOUSTID_SCORE_THRESHOLD = 0.90
FUZZY_MATCH_THRESHOLD = 90
MAX_ACOUSTID_CANDIDATES = 10

EXCLUDED_TRACK_NAMES = ['intro', 'interlude']

load_dotenv()
acoustID_key = os.getenv("ACOUSTID_KEY")

def _normalize(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9àâæçéèêëïîôœùûüÿäößñ ]", "", name)
    return name

##############################################
############# EXTRACT FROM FILE ##############
##############################################

def extract_meta(file):
    try:
        audio = EasyID3(file)
    except Exception as e:
        log.info(f"Skipped {file} -- {e}")
        return None
    
    metadata = {
        "title": audio.get("title", ["Unknown"])[0],
        "artist": audio.get("artist", ["Unknown"])[0],
        "album": audio.get("album", ["Unknown"])[0],
        "year": audio.get("date", [None])[0],
        "track_num": audio.get("tracknumber", ["0"])[0],
    }
    
    if metadata["year"] is None: metadata["year"]=ID3(file).getall("TYER")[0] if ID3(file).getall("TYER")!=[] else None
    metadata['length'] = MP3(file).info.length
    
    return metadata

def apply_meta(file, new_data):
    try:
        audio = EasyID3(file)
    except Exception as e:
        log.info(f"Skipped {file} -- {e}")
        return None
    else:
        for i in new_data.keys():
            match i:
                case "album_title":
                    audio["album"] = new_data["album_title"]
                case "artist_name":
                    audio["artist"] = new_data["artist_name"]
                case "track_number":
                    audio["tracknumber"] = str(new_data["track_number"])
                case "track_title":
                    audio["title"] = new_data["track_title"]
                case "year":
                    audio["date"] = new_data["year"]
    audio.save()

##############################################
################ IDENTIFY ####################
##############################################

def find_track_in_tracklist(track, tracklist):
    def _norm(s):
        s = re.sub(r"^\d+[\s._-]+", "", s)
        s = re.sub(r"[\(\[\{].*?[\)\]\}]", "", s)
        s = s.lower()
        return re.sub(r"[^a-z0-9àâæçéèêëïîôœùûüÿäößñ]", "", s)

    def _partial_ratio(a, b):
        if not a or not b:
            return 0
        shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
        match = SequenceMatcher(None, shorter, longer).find_longest_match()
        return (match.size / len(shorter)) * 100

    norm_track = _norm(track)
    best_score = 0
    best_match = None
    for t in tracklist:
        score = _partial_ratio(norm_track, _norm(t))
        if score > best_score:
            best_score = score
            best_match = t
    return best_match if best_score > FUZZY_MATCH_THRESHOLD else None

def release_group_from_acoustid(track_path:str, group_candidates:dict):
    try:
        release_groups =  acoustid.match(acoustID_key, 
                        track_path,
                        meta=["releasegroups"],
                        parse=False)
        
    except acoustid.AcoustidError as e:
        log.info(f"  AcoustID failed for {track_path}: {e}")
        return None
    
    if release_groups:
        for group in release_groups['results']:
            if group['score']>ACOUSTID_SCORE_THRESHOLD:
                for releasegroup in group.get('releasegroups', []):
                    if releasegroup.get('type', "unknown").lower() != "single":
                        if releasegroup['id'] in group_candidates.keys() : group_candidates[releasegroup['id']]['count']+=1
                        else :  
                            group_candidates[releasegroup['id']]={'count':1, 
                                                                'title':releasegroup.get('title'), 
                                                                'type':releasegroup.get('type', "unknown"),
                                                                'score':0}
        return group_candidates
        
    return None

def release_group_from_query(album_title:str, group_candidates:dict, track_name='', artist_name=''):
    q=f"{track_name} {album_title} {artist_name}".strip()
    
    try:
        result = mb.search_release_groups(q)
        
    except mb.WebServiceError as e:
        log.info(f"  Search failed: {e}")
        return None
    
    if result:
        filtered_res = [g for g in result['release-group-list'] if int(g['ext:score']) >= MB_SCORE_THRESHOLD]
        for group in filtered_res:
            if group.get('type', "unknown").lower() != "single":
                if group['id'] in group_candidates.keys(): group_candidates[group['id']]['count'] += 1
                else : group_candidates[group['id']] = {'count':1,
                                                        'title':group.get('title'),
                                                        'type':group.get('type', "unknown"),
                                                        'score':0}
        return group_candidates
    
    return None

##############################################
################## QUERY #####################
##############################################

def get_release_infos_from_rg(rg_id):
    release_ids = []
    def _get_release_ids():
        try:
            releases = mb.get_release_group_by_id(rg_id)
        except Exception as e:
            log.info(f"Error getting releases from RG id : {rg_id}\n{e}")
            return None
        
        for release in releases['release-group']['release-list']:
            release_ids.append(release['id'])
            
    def _get_info_from_release_id(release_id):
        try:
            r_info = mb.get_release_by_id(release_id,
                                          includes=['recordings', 'artist-credits'],
                                          release_status='official')
        except Exception as e:
            log.info(f"Error getting release info from release id : {release_id}\n{e}")
            return None
        r_info = r_info['release']
        return {'title': r_info['id'],
                'artist': r_info['artist-credit'][0]['artist']['name'],
                'tracklist': {track['recording']['title']:track['recording']['length']
                              for track in r_info['medium-list'][0]['track-list']}}
    
    _get_release_ids()
    if release_ids != []: 
        for release in release_ids:
            release_info = _get_info_from_release_id(release)
            yield release_info
        
##############################################
################## SCORE #####################
##############################################

def score_by_tracklist_name(mb_tracklist, tracklist):
    ...
    
def score_by_track_lengths(mb_tracklist, tracklist):
    ...

def score_by_count(candidates, max):
    for candidate in candidates.values():
        count_score = (candidate['count']-1)/(max-1)
        candidate['score'] += count_score*3
        
##############################################
################## WEIGHT ####################
##############################################
    
def collect_candidates(track_paths, track_names, album_title, artist_name):
    group_candidates={}
    best_candidates = {}

    log.info("Collecting release groups with Fingerprint...")
    for track in track_paths: 
        release_groups = release_group_from_acoustid(track_path=track, 
                                                        group_candidates=group_candidates)
        if release_groups : group_candidates = release_groups
    
    log.info("Collecting release groups with track query...")
    for track in track_names:
        release_groups=release_group_from_query(track_name=track, 
                                        album_title=album_title, 
                                        artist_name=artist_name,
                                        group_candidates=group_candidates)
        if release_groups : group_candidates = release_groups
    
    log.info("Collecting Release groups with album query...")
    album_and_artist_query = release_group_from_query(album_title=album_title, 
                                            artist_name=artist_name,
                                            group_candidates=group_candidates)
    if album_and_artist_query : group_candidates = album_and_artist_query
    
    album_only_query = release_group_from_query(album_title=album_title, 
                                                group_candidates=group_candidates)
    if album_only_query : group_candidates = album_only_query
    
    group_candidates = {rgid: info for rgid, info in group_candidates.items() if info["count"] > 1}
    
    log.info(f"\nCOLLECTED RELEASE GROUPS : {group_candidates.keys()}\n")
    return group_candidates

        
def weight_candidates(candidates, tracklist, track_lengths):
    counts = [v["count"] for v in candidates.values()]

    score_by_count(candidates, max(counts))
    
##############################################
################## MAIN ######################
##############################################

def fix(fixerObj):    
    candidates = collect_candidates(fixerObj.track_path, fixerObj.tracklist, fixerObj.album.display_title, fixerObj.artist_name)
    track_lengths = zip(fixerObj.tracklist, fixerObj.track_lengths)
    weight_candidates(candidates, fixerObj.tracklist, track_lengths)
    
    
file_paths = [
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Amor de Loca Juventud.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Buena Vista Social Club.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Candela.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Chan Chan.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/De Camino a la Vereda.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Dos Gardenias.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/El Carretero.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/El Cuarto de Tula.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/La Bayamesa.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Murmullo.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Orgullecida.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Pueblo Nuevo.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/Veinte Años.mp3",
    "/home/adam/music_sample/Buena Vista Social Club/Buena Vista Social Club/¿Y Tú Qué Has Hecho-.mp3",
]

file_names = [
    "Amor de Loca Juventud",
    "Buena Vista Social Club",
    "Candela",
    "Chan Chan",
    "De Camino a la Vereda",
    "Dos Gardenias",
    "El Carretero",
    "El Cuarto de Tula",
    "La Bayamesa",
    "Murmullo",
    "Orgullecida",
    "Pueblo Nuevo",
    "Veinte Años",
    "¿Y Tú Qué Has Hecho-",
]

print(collect_candidates(file_paths, file_names, "Buena Vista Social Club", "Buena Vista Social Club"))

