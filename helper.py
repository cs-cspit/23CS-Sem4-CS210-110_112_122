from flask import session
import os
import uuid
from pymongo import MongoClient
from datetime import datetime
import spotify_helper
import ytmusic_helper

client = MongoClient(os.getenv("MONGODB_URL"))
db = client["Playlist_Conversion"]
collection = db["metadata"]

#For adding MongoDB index if it doesn't already exist
def add_index():
    field_name = "createdAt"
    expire_after_seconds = 86400
    for index in collection.list_indexes():
        if field_name in index["key"]:  # Check if the field is part of the index
            if "expireAfterSeconds" in index:
                return
    collection.create_index(field_name, expireAfterSeconds=expire_after_seconds)

#For uploading the metadata to database
def upload_metadata(metadata, playlist_name, url, source=None):
    print("Url in helper",url)
    if 'meta_uuid' not in session:
        temp_uid = str(uuid.uuid4())
        session['meta_uuid'] = temp_uid
    else:
        temp_uid = session.get('meta_uuid')
    if not source:
        source = session.get('source-service')
    playlist_data = {
        "_id": temp_uid,
        "playlist_name": playlist_name,
        "url": url,
        "metadata": metadata,  
        "source": source,
        "createdAt": datetime.utcnow()
    }
    collection.delete_one({'_id':temp_uid})
    collection.insert_one(playlist_data)

#Returns Current Metadata stored in Database
def get_current_metadata():
    return collection.find_one({'_id': session['meta_uuid']}) if 'meta_uuid' in session else None

#Deleted Database records mapped to current session
def delete_current_metadata():
    if 'meta_uuid' in session:
        collection.delete_one({'_id': session['meta_uuid']})
        
#Deletes cache files (Spotify)
def delete_cache_files():
    cache_paths = [spotify_helper.get_cache_path('source'), spotify_helper.get_cache_path('target')]
    for cache_path in cache_paths:
        if cache_path and os.path.exists(cache_path):
            os.remove(cache_path)
            
#Deleting auth Files (YT Music)
def delete_auth_files():
    auth_paths = [ytmusic_helper.get_auth_file('source'), ytmusic_helper.get_auth_file('target')]
    for auth_path in auth_paths:
        if auth_path and os.path.exists(auth_path):
            os.remove(auth_path)