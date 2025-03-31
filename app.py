from flask import Flask, redirect, url_for, session, render_template, request, flash, jsonify
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from ytmusicapi import YTMusic
import re
import os
import json
import uuid
from dotenv import load_dotenv
import asyncio
import helper
import spotify_helper
import youtube_helper
import ytmusic_helper
import jiosaavn_helper

load_dotenv()

app = Flask(__name__)
app.secret_key = 'Harshil_is_a_noob_coder_boooooo!!!' 

with app.app_context():
    helper.add_index()
 
#Spotify credentials !
SPOTIPY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")  
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SPOTIFY_SCOPE1 = "playlist-read-private user-library-read playlist-read-collaborative"
SPOTIFY_SCOPE2 = "playlist-modify-private playlist-modify-public"

#Youtube variables
CLIENT_SECRETS_FILE = 'client_secret.json' 
YT_SCOPES1 = ['https://www.googleapis.com/auth/youtube.readonly']
YT_SCOPES2 = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl']

#YT Music Scopes
YT_MUSIC_SCOPES = ['https://www.googleapis.com/auth/youtube.readonly', 'https://www.googleapis.com/auth/youtube.force-ssl', 'https://www.googleapis.com/auth/youtube']

#Error Handler for Server Side Internal Error
@app.errorhandler(Exception)
def handle_exception(e):
    error = str(e)
    return render_template("exception.html", error=error), 500

#Error Handler for page not found
@app.errorhandler(404)
def page_not_found(e):
    return render_template("notfound.html"), 404

#Homepage
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/source")
def source():
    return render_template("source.html")

@app.route("/destination")
def destination():
    return render_template("destination.html")

#Spotify Home Page
@app.route("/spotify")
def spotify():
    session['source-service'] = 'spotify'
    session['curr_user'] = 'source'
    return render_template("spotify/index.html")

#Spotify Login Page
@app.route("/spotify/<user>")
def spotifylogin(user):
    if user not in ['source', 'target']:
        return redirect('/spotify/source')
    session[f'{user}-service'] = 'spotify'
    session['curr_user'] = user
    
    #Check if an user is already logged in
    temp_uid = session.get(user)
    if temp_uid:
        cache_path = 'cache_files/.cache-'+ user + '-' + temp_uid
        if cache_path and os.path.exists(cache_path):
            if user == 'source':
                #Returns to playlist page if user is source to see playlists
                return redirect('/spotify/playlists')
            else:
                #Returns to transfer page if user is target to transfer playlists
                return redirect('/transfer/spotify')
    
    session[user] = str(uuid.uuid4())
    
    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE1 if user == 'source' else SPOTIFY_SCOPE2,
    )
    auth_url = auth_manager.get_authorize_url()
    #User will be redirected to Spotify Page to login
    return redirect(auth_url)

#Spotify Callback
@app.route('/spotifycallback')
def spotiifycallback():
    user = session.get('curr_user')
    
    #For session issues, we need to refresh the page
    if not user:
        return render_template("refresh.html")

    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE1 if user == 'source' else SPOTIFY_SCOPE2,
        cache_path=spotify_helper.get_cache_path(user),
    )
    token_info = auth_manager.get_access_token(request.args.get("code"))
    session['token_info'] = token_info
    session['spotify_logged_in'] = 'True'
    if user=='source':
        return redirect(url_for('spotifyplaylists'))
    return redirect(url_for('transfer_spotify'))

#Spotify Playlists from User Login
@app.route("/spotify/playlists", methods=['POST', 'GET'])
def spotifyplaylists():
    
    cache_path = spotify_helper.get_cache_path('source')

    #Check if cache file exists or not for logged in user
    if not cache_path or not os.path.exists(cache_path):
        return redirect('/spotify/source')

    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=SPOTIPY_REDIRECT_URI,
        scope=SPOTIFY_SCOPE1,
        cache_path=cache_path,
    )
    sp = Spotify(auth_manager=auth_manager)
    
    if request.method == "POST":
        #Get the playlist id from the form
        playlist_id = request.form.get("playlist_id")
        if not playlist_id:
            return redirect(url_for("spotifyplaylists"))
        if playlist_id == "liked_songs":
            # Fetch Liked Songs
            metadata = spotify_helper.get_liked_songs(auth_manager)
            playlist_name = "Liked Songs"
            playlist_image_url = "https://image-cdn-ak.spotifycdn.com/image/ab67706c0000da8470d229cb865e8d81cdce0889"
        else:
            # Fetch tracks from playlist
            metadata_data = spotify_helper.get_spotify_tracks(sp, playlist_id)
            metadata = metadata_data[0]
            playlist_name = metadata_data[1]
            playlist_image_url = metadata_data[2]        
        helper.upload_metadata(metadata, playlist_name, playlist_image_url)
        return redirect(url_for("playlist_metadata"))
    
    #Fetch User Playlists    
    playlists = spotify_helper.get_spotify_playlists(sp)
    if not playlists:
        flash("Some error occurred while fetching your playlists", "error")
        return redirect('/spotify')

    return render_template("spotify/playlists.html", playlists=playlists)

#Spotify metadata from playlist url
@app.route('/extract/spotify', methods=['POST'])
def extract_from_spotify():
    
    playlist_url = request.form.get('url')
    playlist_id = spotify_helper.extract_playlist_id(playlist_url)
    if not playlist_id:
        flash("Invalid Spotify URL", "error")
        return redirect(url_for("spotify"))
    
    auth_manager = SpotifyClientCredentials(
        client_id=SPOTIPY_CLIENT_ID, 
        client_secret=SPOTIPY_CLIENT_SECRET,
        cache_handler=None
    )
    sp = Spotify(auth_manager=auth_manager) 
    
    try:
        not_found = spotify_helper.extract_tracks_from_url(sp, playlist_id)
        if not_found:
            flash("Your playlist seems to be empty !!", "error")
            return redirect(url_for("spotify"))
        session['spotify_logged_in'] = 'False'
        return redirect("/playlist/preview")

    except Exception as e:
        flash("There was an error while fetching your playlist. It is either a private playlist or cannot be accessed by us", "error")
        return redirect(url_for("spotify"))

#Youtube Homepage
@app.route("/youtube")
def youtube():
    session['source-service'] = 'youtube'
    session['curr_user'] = 'source'
    return render_template("youtube/index.html")

#Youtube Login Page
@app.route('/youtube/<user>')
def youtubelogin(user):
    if user not in ['source', 'target']:
        return redirect('/youtube/source')
    
    session[f'{user}-service'] = 'youtube'
    session['curr_user'] = user
    
    #Check if an user is already logged in
    if f'{user}-credentials' in session:
        if user=='source':
            return redirect(url_for('youtubeplaylists'))
        else:
            return redirect(url_for('transfer_youtube'))
            
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=YT_SCOPES1 if user=='source' else YT_SCOPES2,
        redirect_uri=url_for('youtubecallback', _external=True)
    )
    auth_url, _ = flow.authorization_url(prompt='consent')
    #User will be redirected to Google Page to login
    return redirect(auth_url)

#Youtube Callback
@app.route('/youtubecallback')
def youtubecallback():
    user = session.get("curr_user")
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=YT_SCOPES1 if user=='source' else YT_SCOPES2,
        redirect_uri=url_for('youtubecallback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    print("User in callback : ", user)
    session[f'{user}-credentials'] = json.dumps({
    'token': flow.credentials.token,
    'refresh_token': flow.credentials.refresh_token,
    'token_uri': flow.credentials.token_uri,
    'client_id': flow.credentials.client_id,
    'client_secret': flow.credentials.client_secret,
    'scopes': flow.credentials.scopes
    })
    session['youtube_logged_in'] = True
    if user == 'source':
        return redirect(url_for('youtubeplaylists'))
    return redirect(url_for('transfer_youtube'))

# Youtube Playlists from User Login
@app.route('/youtube/playlists', methods=['POST', 'GET'])
def youtubeplaylists():
    if 'source-credentials' not in session:
        return redirect(url_for('youtube'))
    
    credentials_data = json.loads(session['source-credentials'])
    credentials = Credentials(
    token=credentials_data['token'],
    refresh_token=credentials_data.get('refresh_token'),
    token_uri=credentials_data['token_uri'],
    client_id=credentials_data['client_id'],
    client_secret=credentials_data['client_secret'],
    scopes=credentials_data['scopes']
    )
    youtube = build('youtube', 'v3', credentials=credentials)
    all_playlists = youtube_helper.get_all_playlists(youtube)    

    playlists = []
    for item in all_playlists:
        thumbnails = item['snippet'].get('thumbnails', {})
        # Check for 'high' quality thumbnail, fallback to 'default'
        playlist_image = thumbnails.get('high', thumbnails.get('default', {})).get('url', None)
        playlists.append({
            'title': item['snippet']['title'],
            'id': item['id'],
            'image': playlist_image 
        })
    
    if request.method == 'POST':
        playlist_id = request.form.get('playlist_id')
        if 'source-credentials' not in session:
            return redirect(url_for('youtubelogin', user='source'))

        credentials = json.loads(session['source-credentials'])
        headers = {'Authorization': f"Bearer {credentials['token']}"}
        video_data = youtube_helper.fetch_yt_playlist_videos(playlist_id, headers)
        videos = video_data[0]
        playlist_name = video_data[1]
        playlist_image_url = video_data[2]
        if not videos:
            return "There was some error fetching playlist details"
        video_data = []

        # Collect video details (title and channel name)
        for v in videos:
            snippet = v.get('snippet', {})
            video_id = snippet.get('resourceId', {}).get('videoId')  
            video_title = snippet.get('title')  
            channel_name = snippet.get('videoOwnerChannelTitle')  
            video_image_url = snippet.get('thumbnails', {}).get('default', {}).get('url')
            if video_title and channel_name and video_title:
                video_data.append({'song_name': video_title, 'artist_name': channel_name, 'song_id': video_id, 'image_url': video_image_url})

        helper.upload_metadata(video_data, playlist_name, playlist_image_url)
        return redirect(url_for("playlist_metadata"))

    return render_template('youtube/playlists.html', playlists=playlists)

#Youtube metadata from playlist url
@app.route('/extract/youtube', methods=['POST'])
def extract_from_youtube():
    playlist_url = request.form.get('url')
    try:
        youtube_helper.extract_youtube_playlist_videos(playlist_url)
    except ValueError:
        flash("Invalid YouTube URL", "error")
        return redirect(url_for("youtube"))
    except Exception as e:
        flash("There was an error while fetching your playlist. It is either a private playlist or cannot be accessed by us", "error")
        return redirect(url_for("youtube"))
    session['youtube_logged_in'] = False
    return redirect(url_for('playlist_metadata'))

#Youtube Music Homepage
@app.route("/youtubemusic")
def youtubemusic():
    session['source-service'] = 'youtubemusic'
    session['curr_user'] = 'source'
    return render_template('youtubemusic/index.html')

#YoutubeMusic Login Page
@app.route('/youtubemusic/<user>')
def youtubemusiclogin(user):
    if user not in ['source', 'target']:
        return redirect('/youtubemusic/source')
    
    session[f'{user}-service'] = 'youtubemusic'
    session['curr_user'] = user
    
    #Check if an user is already logged in
    if f'{user}-ytmusic-credentials' in session:
        auth_file = ytmusic_helper.get_auth_file(user)
        if os.path.exists(auth_file):
            if user=='source':
                return redirect(url_for('youtubemusicplaylists'))
            else:
                return redirect(url_for('transfer_youtubemusic'))

    session[user] = str(uuid.uuid4())
    
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=YT_MUSIC_SCOPES,
        redirect_uri=url_for('youtubemusiccallback', _external=True)
    )
    auth_url, _ = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt="consent")
    #User will be redirected to Google Page to login
    return redirect(auth_url)

#Youtube Music Callback
@app.route('/youtubemusiccallback')
def youtubemusiccallback():
    user = session.get('curr_user')
    if not user:
        return render_template('refresh.html')
    #Get authorization code
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=YT_MUSIC_SCOPES,
        redirect_uri=url_for('youtubemusiccallback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    session[f'{user}-ytmusic-credentials'] = ytmusic_helper.credentials_to_dict(credentials)

    ytmusic_helper.generate_ytmusic_auth_headers(credentials)
    session['youtube_music_logged_in'] = True
    if user=='source':
        return redirect(url_for('youtubemusicplaylists'))
    return redirect(url_for('transfer_youtubemusic'))

#Youtube Music playlists from User Login
@app.route('/youtubemusic/playlists', methods = ['GET', 'POST'])
def youtubemusicplaylists():
    auth_file = ytmusic_helper.get_auth_file('source')
    if not os.path.exists(auth_file):
        flash("No auth file found")
        return(redirect('/youtubemusic'))

    ytmusic = YTMusic(auth_file)
        
    if request.method == 'POST':
        try:
            #Get the playlist id from the form
            playlist_id = request.form['playlist_id']
            print(playlist_id)
            # ytmusic_helper.extract_tracks_from_playlist(ytmusic, playlist_id)
            playlist_details = ytmusic.get_playlist(playlist_id)
            print(playlist_details)
            playlist_name = playlist_details['title'] if playlist_details['title'] else "Playlist"
            playlist_image_url = playlist_details.get('thumbnails', [{}])[-1].get('url', None)
            songs = []
            print("Length  of ", playlist_name ," : " , len(playlist_details['tracks']))

            for track in playlist_details['tracks']:
                songs.append({
                    'song_name': track['title'],
                    'artist_name': ', '.join([artist['name'] for artist in track['artists']]),
                    'song_id' : track['videoId'],
                    'image_url': track.get('thumbnails', [{}])[-1].get('url', None)
                })
        
            helper.upload_metadata(songs, playlist_name, playlist_image_url)
            return redirect(url_for('playlist_metadata'))
        except Exception as e:
            return jsonify({"error": str(e)})
            
    try:
        playlists = ytmusic.get_library_playlists()
        return render_template('youtubemusic/playlists.html', playlists=playlists)

    except Exception as e:
        return jsonify({"error": str(e)})

#Youtube Music Metadata from Playlist URL
@app.route('/extract/youtubemusic', methods=['POST'])
def extract_from_ytmusic():
    ytmusic = YTMusic()
    playlist_url = request.form.get('url')
    match = re.search(r"list=([a-zA-Z0-9_-]+)", playlist_url)
    if not match:
        flash("Invalid YT Music URL", "error")
        return redirect(url_for("youtubemusic"))
            
    playlist_id = match.group(1)
    try:
        ytmusic_helper.extract_tracks_from_playlist(ytmusic, playlist_id)
    except Exception as e:
        flash("There was an error while fetching your playlist. It is either a private playlist or cannot be accessed by us", "error")
        return redirect(url_for("youtubemusic"))
    session['youtube_music_logged_in'] = False
    return redirect(url_for('playlist_metadata'))

#JioSaavn Homepage
@app.route("/jiosaavn", methods = ['GET', 'POST'])
def jiosaavn():
    
    session['source-service'] = 'jiosaavn'
    session['curr_user'] = 'source'
    
    if request.method == 'POST':
        playlist_url = request.form.get('url')
        if not playlist_url:
            flash("No playlist URL found", "error")
            return redirect(url_for('jiosaavn'))
        metadata = []
        try:
            print(playlist_url)
            id = jiosaavn_helper.get_playlist_id(playlist_url)
            print(id)
            songs = jiosaavn_helper.get_playlist(id)
            if songs:
                name = songs['listname']
                for song in songs['songs']:
                    metadata.append({'artist_name': song['primary_artists'], 'song_name' : song['song'], 'image_url': song['image']})
                helper.upload_metadata(metadata, name, 0)
                return redirect(url_for('playlist_metadata'))
            else:
                flash("Playlist does not exist or there was some error in fetching the tracks.", "error")
                return redirect(url_for('jiosaavn'))
    
        except Exception as e:
            flash(f"Playlist does not exist or there was some error in fetching the tracks. {str(e)}", "error")
            return redirect(url_for('jiosaavn'))
    
    return render_template('others/jiosaavn.html')

#View Metadata
@app.route("/playlist/preview")
def playlist_metadata():
    playlist_data = helper.get_current_metadata()
    metadata = playlist_data['metadata'] if playlist_data else []
    playlist_name = playlist_data['playlist_name'] if playlist_data else "Unknown"
    playlist_image_url = playlist_data['url'] if playlist_data else 0
    print(playlist_image_url)
    return render_template("preview.html", metadata=metadata, playlist_name=playlist_name, url=playlist_image_url)

#For Spotify transfer page
@app.route("/transfer/spotify", methods=['POST', 'GET'])
def transfer_spotify():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('playlist_metadata'))
    playlist_data = helper.get_current_metadata()
    metadata = playlist_data['metadata'] if playlist_data else []
    playlist_name = playlist_data['playlist_name'] if playlist_data else "Unknown"
    source_platform = playlist_data['source']
    
    if request.method == 'POST':
        
        token_info = session.get('token_info', None)
        if not token_info:
            return redirect(url_for('playlist_metadata'))
        
        sp = Spotify(auth=token_info['access_token'])
        user_id = sp.me()['id']
        
        # Create a new playlist
        playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=True, description="This playlist was created by Music Link !!")

        playlist_id = playlist['id']
        playlist_url = playlist['external_urls']['spotify']
        session['playlist_url'] = playlist_url
        session['playlist_name'] = playlist_name

        # Search and add songs to the playlist
        not_found = []
        track_uris = []
        
        if source_platform == 'spotify':
            track_uris = [track_uri['song_id'] for track_uri in metadata]
            print("We can directly transfer from spotify to spotify")
        
        elif source_platform in ['youtube', 'youtubemusic']:
            
            print("Searching with noisy data")
            async def process_tracks(metadata):
                tasks = []
                i=1
                for song in metadata:
                    tasks.append( spotify_helper.search_with_noise_data(i, sp, song['song_name'], song['artist_name']))
                    i+=1
    
                results = await asyncio.gather(*tasks)

                for i, (uri, song) in enumerate(zip(results, metadata), 1):
                    if uri != "no_result_found":
                        track_uris.append(uri)
                    else:
                        not_found.append(song['song_name'])
            
            asyncio.run(process_tracks(metadata))

        else:            
            print("Searching with clean data")
            
            async def process_tracks(metadata):
                tasks = []
                i=1
                for song in metadata:
                    tasks.append( spotify_helper.search_with_clean_data(i, sp, song['song_name'], song['artist_name']))
                    i+=1
    
                results = await asyncio.gather(*tasks)

                for i, (uri, song) in enumerate(zip(results, metadata), 1):
                    if uri != "no_result_found":
                        print(f"{i}. Found: {song['song_name']}")
                        track_uris.append(uri)
                    else:
                        print(f"{i}. Not found: {song['song_name']}")
                        not_found.append(song['song_name'])
            asyncio.run(process_tracks(metadata))

        if track_uris:
            for i in range(0, len(track_uris), 100):
                temp_batch = track_uris[i:i+100]
                sp.playlist_add_items(playlist_id, temp_batch)

        return render_template("final.html", not_found=not_found)
    
    return render_template("transfer.html", metadata=metadata, playlist_name=playlist_name)

#For Youtube transfer page
@app.route('/transfer/youtube', methods = ['GET', 'POST'])
def transfer_youtube():
    if 'target-credentials' not in session:
        return redirect('/youtube/target')
    
    playlist_data = helper.get_current_metadata()
    metadata = playlist_data['metadata'] if playlist_data else []
    playlist_name = playlist_data['playlist_name'] if playlist_data else "Unknown"
    source_platform = playlist_data['source']
    
    if request.method == 'POST':
        credentials_data = json.loads(session['target-credentials'])
        credentials = Credentials(
            token=credentials_data['token'],
            refresh_token=credentials_data.get('refresh_token'),
            token_uri=credentials_data['token_uri'],
            client_id=credentials_data['client_id'],
            client_secret=credentials_data['client_secret'],
            scopes=credentials_data['scopes']
        )
        youtube = build('youtube', 'v3', credentials=credentials)
        
        #Creating a new playlist
        ytrequest = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                "title": playlist_name,
                "description": "This playlist is created by Music Link !!"
                },
                "status": {
                "privacyStatus": "public"  
                }
            }
        )
        response = ytrequest.execute() 
        playlist_id = response.get("id") 
        
        ids = []
        not_found = []
        
        if source_platform in ['youtube', 'youtubemusic']:
            #We already have the video ids in our database
            for song in metadata:
                video_id = song['song_id']
                if video_id is not None:
                    ids.append({'song_name' : song['song_name'] ,'id' : video_id})
                else:
                    not_found.append(song['song_name'])
        
        else:
            for song in metadata:
                id = youtube_helper.search_song_on_youtube(song['song_name'], song['artist_name'], youtube)
                if id != "NO_VIDEO_FOUND":
                    print(f"{song['song_name']} found on YouTube")
                    ids.append({'song_name': song['song_name'], 'id': id})
                else:
                    not_found.append(song['song_name'])
                    
        if ids:
            for id in ids:
                try:
                    yt_request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": id['id']
                                }
                            }
                        }
                    )
                    response = yt_request.execute()
                    playlist_item_id = response.get("id")

                    if playlist_item_id:
                        print(f"{id['song_name']} added successfully! Playlist Item ID")
                    else:
                        not_found.append(id['song_name'])
                        print(f"{id['song_name']} could not be added.")

                except HttpError as e:
                    not_found.append(id['song_name'])
                    error_details = e.content.decode("utf-8")
                    print(f"Error adding video {id['song_name']}: {error_details}")
            
            session['playlist_name'] = playlist_name
            session['playlist_url'] = f"https://www.youtube.com/playlist?list={playlist_id}"
            
            return render_template('final.html', not_found=not_found)
        
        else:
            return "No songs to add"
        
    return render_template('transfer.html',  metadata=metadata, playlist_name=playlist_name)

#For Youtube Music transfer page
@app.route('/transfer/youtubemusic', methods = ['GET', 'POST'])
def transfer_youtubemusic():
    
    auth_file = ytmusic_helper.get_auth_file('target')
    if not auth_file:
        return redirect('/youtubemusic/target')
    
    playlist_data = helper.get_current_metadata()
    metadata = playlist_data['metadata'] if playlist_data else []
    playlist_name = playlist_data['playlist_name'] if playlist_data else "Unknown"
    source_platform = playlist_data['source']

    if request.method == 'POST':
        ids = []
        not_found = []
        if source_platform in ['youtube', 'youtubemusic']:
            for song in metadata:
                if song['song_id'] is not None:
                    ids.append(song['song_id'])
                else:
                    not_found.append(song['song_name'])
        else:
            #To-do : Add logic so it searches the ID from YT Music -----------------------------------------------------------------------------------
            async def process_tracks(metadata):
                tasks = []

                ytmusic = YTMusic()
                for song in metadata:
                    tasks.append(ytmusic_helper.search_for_song(ytmusic, song['song_name'], song['artist_name']))
    
                results = await asyncio.gather(*tasks)

                for i, (uri, song) in enumerate(zip(results, metadata), 1):
                    if uri != "no_result_found":
                        print(f"{i}. Found: {song['song_name']}")
                        ids.append(uri)
                    else:
                        print(f"{i}. Not found: {song['song_name']}")
                        not_found.append(song['song_name'])
            
            asyncio.run(process_tracks(metadata))
        
        if ids:
            ytmusic = YTMusic(auth_file)
            playlist_id = ytmusic.create_playlist(title=playlist_name, description="This playlist was created using Music Link !", privacy_status="PUBLIC", video_ids=ids)
            session['playlist_name'] = playlist_name
            session['playlist_url'] = f"https://music.youtube.com/playlist?list={playlist_id}"

            return render_template('final.html', not_found=not_found)

        return "No songs to add"

    return render_template('transfer.html', metadata=metadata, playlist_name=playlist_name)

@app.route("/logout")
def logout():
    helper.delete_current_metadata()    #Deleting Database Documents
    helper.delete_cache_files()         #Deleting cache files
    helper.delete_auth_files()          #Deleting Auth Files
    session.clear()                     #Clearing session
    return redirect(url_for("index"))

if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)