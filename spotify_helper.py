from flask import session
from spotipy import Spotify
import uuid
import re
import helper
import os
import youtube_helper
import asyncio
from spotipy.exceptions import SpotifyException

#For Spotify Cache File
def get_cache_path(user):
    
    uid = session.get(user)
    if not uid:
        uid = str(uuid.uuid4())        
    session[user] = uid
    file = 'cache_files/.cache-'+ user + '-' + uid
    return file

#Spotify Liked songs
def get_liked_songs(auth_manager):

    sp = Spotify(auth_manager=auth_manager)
    liked_songs = []
    results = sp.current_user_saved_tracks()

    while results:

        liked_songs.extend(
            [
                {
                    "song_name": track["track"]["name"], 
                    "artist_name": track["track"]["artists"][0]["name"], 
                    "song_id": track['track']['uri'],
                    "image_url": track["track"]["album"]["images"][0]["url"]
                } 
                for track in results["items"] 
                if track.get("track") and track["track"].get("name") and track["track"].get("artists")
            ]
        )

        results = sp.next(results) if results["next"] else None
    return liked_songs

# Function to extract Spotify playlist ID from URL
def extract_playlist_id(url):

    match = re.search(r'playlist/([a-zA-Z0-9]+)', url)
    return match.group(1) if match else None

#For fetching spotify playlists from an account
def get_spotify_playlists(sp):

    try:
        playlists = sp.current_user_playlists()["items"]
        playlists.append({"id": "liked_songs", "name": "Liked Songs", "images": [{'url':'https://image-cdn-ak.spotifycdn.com/image/ab67706c0000da8470d229cb865e8d81cdce0889'}]})

    except Exception as e:
        playlists = []

    return playlists

#For fetching tracks from a user Spotify playlist
def get_spotify_tracks(sp, playlist_id):

    tracks = []
    playlist_data = sp.playlist(playlist_id)
    playlist_name = playlist_data["name"]
    if playlist_data["images"] and len(playlist_data["images"]) > 0:
        playlist_image_url = playlist_data["images"][0]["url"]
    else:
        playlist_image_url = 0
    results = sp.playlist_tracks(playlist_id, limit=100, offset=0) 

    # Add tracks from the first page
    tracks.extend(results["items"])
   
    #Handles pagination 
    while results.get("next"):
        results = sp.next(results) 
        tracks.extend(results["items"])  

    # Filter metadata for valid tracks
    metadata = [
        {
            "song_name": track["track"]["name"], 
            "artist_name": track["track"]["artists"][0]["name"], 
            "song_id": track['track']['uri'],
            "image_url": track["track"]["album"]["images"][0]["url"]
        }
        for track in tracks
        if track.get("track") and track["track"].get("name") and track["track"].get("artists")
    ]
    
    return [metadata, playlist_name, playlist_image_url]

#For fetching tracks from Spotify Playlist link
def extract_tracks_from_url(sp, playlist_id):

    playlist_data = sp.playlist(playlist_id)
    playlist_name = playlist_data["name"]
    if playlist_data["images"] and len(playlist_data["images"]) > 0:
        playlist_image_url = playlist_data["images"][0]["url"]
    else:
        playlist_image_url = 0
    results = sp.playlist_tracks(playlist_id, limit=100, offset=0)  

    if not results:
        return True
        
    tracks = []
    tracks.extend(results["items"])
   
    #Handles Pagination
    while results.get("next"):
        results = sp.next(results)  
        tracks.extend(results["items"])  

    # Filter metadata for valid tracks 
    metadata = [
        {
            "song_name": track["track"]["name"], 
            "artist_name": track["track"]["artists"][0]["name"], 
            "song_id": track['track']['uri'],
            "image_url": track["track"]["album"]["images"][0]["url"]
        }
        for track in tracks
        if track.get("track") and track["track"].get("name") and track["track"].get("artists")
    ]
    
    session['spotify_logged_in'] = False

    helper.upload_metadata(metadata, playlist_name, playlist_image_url)

    if os.path.exists('./.cache'):
        os.remove('./.cache')

    return False

#Gets the best spotify match track when source platforms are youtube or youtube music
async def search_with_noise_data(i, sp, track_name, artist_name):

    cleaned_artist = youtube_helper.clean_artist_name(artist_name)
    print(cleaned_artist)
    cleaned_track = remove_artist_from_title(track_name, cleaned_artist)
    if not cleaned_track:
        cleaned_track = track_name
    query_with_artist = f"track:{cleaned_track} artist:{cleaned_artist}"
    results = await async_search(sp, query_with_artist)

    #If we don not get result, then we search using only song name
    if not results or not results["tracks"]["items"] or len(results["tracks"]["items"]) < 1:
        query_without_artist = f"track:{cleaned_track}"
        results = await async_search(sp, query_without_artist)

    #If stil no results, we return None
    if not results or not results["tracks"]["items"] or len(results["tracks"]["items"]) < 1:
        print(f"{track_name} -> {cleaned_track}")
        print(f"{artist_name} -> {cleaned_artist}")
        print("Not Found \n")
        # print(i, "No results found")
        return "no_result_found"

    # Select the track with the highest popularity
    best_track = max(results["tracks"]["items"], key=lambda x: x["popularity"])

    track_uri = best_track["uri"]
    # print(i)
    print(f"{track_name} -> {cleaned_track}")
    print(f"{artist_name} -> {cleaned_artist}")
    print("Yay Hurray! Found \n")

    return track_uri

#Removes artist name if it is in the title of song
def remove_artist_from_title(track_name, artist_name):
    track_name = youtube_helper.clean_song_title(track_name)

    # Allow optional spaces between characters in artist_name
    artist_pattern = r'\s*'.join(re.escape(artist_name))  # Adds \s* between each character
    pattern = re.compile(rf"\b{artist_pattern}\b", re.IGNORECASE)

    # Replace the matched pattern with an empty string
    track_name = pattern.sub("", track_name).strip()

    return track_name

#Used when we have clean metadata (Not from YT or YT Music)
async def search_with_clean_data(i, sp, song_name, artist_name):

    #First we search with song name and artist name both
    query_with_artist = f"track:{song_name} artist:{artist_name}"
    results = await async_search(sp, query_with_artist)

    #If we don not get result, then we search using only song name
    if not results or not results["tracks"]["items"] or len(results["tracks"]["items"]) < 1:
        query_without_artist = f"track:{song_name}"
        results = await async_search(sp, query_without_artist)

    #If stil no results, we return None
    if not results or not results["tracks"]["items"] or len(results["tracks"]["items"]) < 1:
        print(i, "No results found")
        return "no_result_found"

    # Select the track with the highest popularity
    best_track = max(results["tracks"]["items"], key=lambda x: x["popularity"])

    track_uri = best_track["uri"]
    print(i)
    return track_uri

async def async_search(sp, query):

    loop = asyncio.get_event_loop()
    retries = 3
    delay = 5 
    
    for _ in range(retries):

        try:

            result = await loop.run_in_executor(None, lambda: sp.search(q=query, type="track", limit=5))

            if result:
                return result
            else:
                return None        

        except SpotifyException as e:
            pass

        except Exception as e:
            pass

        await asyncio.sleep(delay)

    return None