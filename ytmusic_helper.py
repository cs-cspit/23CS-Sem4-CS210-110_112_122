from flask import session
import uuid
import json
import helper
import asyncio

#The auth File for ytmusicapi
def get_auth_file(user):
    uid = session.get(user)
    if not uid:
        uid = str(uuid.uuid4())        
        session[user] = uid
    file = 'auth_files/'+ user + '-' + uid
    return file

#Formats the credentials
def credentials_to_dict(credentials):
    """Converts the credentials object to a dictionary for saving in the session."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
#Generates the auth file after login
def generate_ytmusic_auth_headers(credentials):
    """Generates authentication headers for YTMusic and saves to file."""
    headers = {
        "Authorization": f"Bearer {credentials.token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    auth_file = get_auth_file(session.get('curr_user'))
    with open(auth_file, "w") as f:
        json.dump(headers, f)

#YT Music metadata from Playlist
def extract_tracks_from_playlist(ytmusic, playlist_id):
    
    playlist_details = ytmusic.get_playlist(playlist_id, 500)
    playlist_name = playlist_details['title']
    playlist_image_url = playlist_details.get('thumbnails', [{}])[-1].get('url', None)
    songs = []
    print("Length  of ", playlist_name ," : " , len(playlist_details['tracks']), " and image url : ", playlist_image_url)
    # Fetch initial batch of songs
    for track in playlist_details['tracks']:
        songs.append({
            'song_name': track['title'],
            'artist_name': ', '.join([artist['name'] for artist in track['artists']]),
            'song_id' : track['videoId'],
            'image_url': track.get('thumbnails', [{}])[-1].get('url', None)
        })
        
    helper.upload_metadata(songs, playlist_name, playlist_image_url)
    
#Search for a song in YT Music
async def search_for_song(ytmusic, song_name, artist_name):
    results = await searching(ytmusic, f"{song_name} {artist_name}")
    if not results or len(results) < 1:
        results = await searching(ytmusic, f"{song_name}")
        if not results or len(results) < 1:
            return "no_result_found"
    
    return results[0].get('videoId')

#Actual searching
async def searching(ytmusic, query):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda : ytmusic.search(query, filter="songs", limit=1))