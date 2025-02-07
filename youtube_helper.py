import requests
import re
import os
import helper

API_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_PLAYLIST_URL = "https://www.googleapis.com/youtube/v3/playlists"


#For fetching Youtube Playlist videos with user logged in
def fetch_yt_playlist_videos(playlist_id, headers):
    playlist_details_url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&id={playlist_id}"
    playlist_response = requests.get(playlist_details_url, headers=headers)

    if playlist_response.status_code != 200:
        return False, "Failed to fetch playlist details"

    playlist_data = playlist_response.json()
    if not playlist_data.get('items'):
        return False, "Playlist not found"

    playlist_name = playlist_data['items'][0]['snippet']['title']
    videos = [] 
    next_page_token = None
    while True:
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={playlist_id}&maxResults=50"
        if next_page_token:
            url += f"&pageToken={next_page_token}"

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return False

        data = response.json()
        videos.extend(data.get('items', []))

        # Check if there's another page of results
        next_page_token = data.get('nextPageToken')
        if not next_page_token:
            break
    return [videos, playlist_name]

#For cleaning youtube video title
def clean_song_title(title):
    # Remove common words like 'Official Video', 'Full Video', 'Lyrics', etc.
    title = re.sub(r'\|.*', ' ', title)
    title = re.sub(r'\[.*?\]|\(.*?\)', ' ', title)
    
    # Remove common keywords
    keywords = [
        "official video", "official audio", "lyric", "lyrics", "full song", "full video", 
        "music video", "remix", "karaoke", "trailer", "movie", "HD", "4K",
        "official", "by", "audio", "live performance", "video", "ft", "lyrical", "songs",
        "slowed", "bass", "ft.", "-", "song", "live"
    ]
    
    pattern = r'\b(?:' + '|'.join(keywords) + r')\b'
    title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    # Remove extra spaces and special characters
    title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title).strip()
    title = re.sub(r'\s+', ' ',title)
    return title

#For cleaning youtube channel name
def clean_artist_name(artist_name):
    # List of unwanted keywords that might be present in the artist's name
    unwanted_keywords = [
        'Vevo', 'Official', 'Remix', 'Remixed', 'Fanpage', 'Community', 
        'Vivo',  'Topic', 'Channel', 'Show', 'Playlist', 
        'TV', 'Television', 'Mix', 'ArtistName', 'Music Videos', 'Vevo Official', '-'
    ]
    
    # Remove unwanted keywords using regex
    for keyword in unwanted_keywords:
        # Remove keyword and surrounding spaces (case insensitive)
        artist_name = re.sub(re.escape(keyword), '', artist_name, flags=re.IGNORECASE)
    
    artist_name = re.sub(r'\s+', ' ',artist_name).strip()
    return artist_name

#For extracting public playlists with url
def extract_youtube_playlist_videos(playlist_url):
    match = re.search(r"list=([a-zA-Z0-9_-]+)", playlist_url)
    if not match:
        raise ValueError("Invalid YouTube playlist URL")
    
    playlist_id = match.group(1)
    
    params = {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": 50, 
        "key": API_KEY
    }

    videos = []

    while True:
        response = requests.get(YOUTUBE_PLAYLIST_ITEMS_URL, params=params)
        data = response.json()

        if "items" not in data:
            raise Exception("Error fetching playlist data: " + str(data))

        # Extract video details
        video_ids = [item["snippet"]["resourceId"]["videoId"] for item in data["items"]]
        
        video_details = get_video_details(video_ids)

        for video_id, details in video_details.items():
            videos.append({
                "song_name": details["title"],
                "song_id": video_id,
                "artist_name": details["uploader_channel"],
                # "video_url": f"https://www.youtube.com/watch?v={video_id}"
            })
    
        # Check if there are more pages
        if "nextPageToken" in data:
            params["pageToken"] = data["nextPageToken"]
        else:
            break  # No more pages
    
    playlist_name = get_playlist_name(playlist_id)
    if not playlist_name:
        playlist_name = "Youtube Playlist"
    
    helper.upload_metadata(videos, playlist_name)
    
#Getting video details (Title, Channel Name)
def get_video_details(video_ids):
    video_details = {}
    params = {
        "part": "snippet",
        "id": ",".join(video_ids),
        "key": API_KEY
    }
    
    response = requests.get(YOUTUBE_VIDEOS_URL, params=params)
    data = response.json()

    for item in data.get("items", []):
        video_id = item["id"]
        video_details[video_id] = {
            "title": item["snippet"]["title"],
            "uploader_channel": item["snippet"]["channelTitle"],
        }
    
    return video_details

#Getting Playlist name from Playlist ID
def get_playlist_name(playlist_id):
    params = {
        "part": "snippet",
        "id": playlist_id,  # Fetch details of this playlist
        "key": API_KEY
    }
    response = requests.get(YOUTUBE_PLAYLIST_URL, params=params)
    data = response.json()

    # Extract and return playlist name
    if "items" in data and len(data["items"]) > 0:
        return data["items"][0]["snippet"]["title"]
    else:
        return None
    
#Searching Video ID from query
def search_song_on_youtube(song_name, artist_name, youtube_service):
    search_request = youtube_service.search().list(
        q=f"Song {song_name} by {artist_name}",
        part="snippet",
        type="video",
        maxResults=1  # You can adjust the number of search results
    )
    
    search_response = search_request.execute()
    
    if 'items' not in search_response or len(search_response['items']) == 0:
        search_request = youtube_service.search().list(
            q=f"Song {song_name}",
            part="snippet",
            type="video",
            maxResults=1  # You can adjust the number of search results
        )
        search_response = search_request.execute()
    
        if 'items' not in search_response or len(search_response['items']) == 0:
            return "NO_VIDEO_FOUND"  # No results found
    
    
    video_id = search_response['items'][0]['id']['videoId']
    return video_id