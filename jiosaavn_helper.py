import requests
import json
from pyDes import *

JIOSAAVN_BASE_URL = "https://www.jiosaavn.com/api.php?__call=playlist.getDetails&_format=json&cc=in&_marker=0%3F_marker%3D0&listid="

def get_playlist_id(input_url):
    res = requests.get(input_url).text
    try:
        return res.split('"type":"playlist","id":"')[1].split('"')[0]
    except IndexError:
        try:
            return res.split('"page_id","')[1].split('","')[0]
        except:
            return None
        
def get_playlist(listId):
    try:
        response = requests.get(JIOSAAVN_BASE_URL + listId)
        if response.status_code == 200:
            songs_json = response.text.encode().decode('unicode-escape')
            songs_json = json.loads(songs_json)
            return format_playlist(songs_json)
        return None
    except Exception:
        return None
    
def format_playlist(data):
    data['listname'] = format(data['listname'])
    for song in data['songs']:
        song = format_song(song)
    return data

def format_song(data):
    data['song'] = format(data['song'])
    data["primary_artists"] = format(data["primary_artists"])
    data['image'] = data['image'].replace("150x150", "500x500")
    return data

def format(string):
    return string.encode().decode().replace("&quot;", "'").replace("&amp;", "&").replace("&#039;", "'")