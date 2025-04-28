# MusicLink: Playlist Transfer Tool

**MusicLink** is a web application that allows users to seamlessly transfer their music playlists across multiple platforms like **Spotify**, **YouTube Music**, and more. With optimized performance and smart caching mechanisms, MusicLink provides an efficient way to move playlists even between different accounts on the same platform.

---

## 🚀 Features

- **Cross-Platform Playlist Transfer**: Transfer your playlists between Spotify, YouTube Music, and other platforms (more to be added soon).
- **Account-to-Account Transfers**: Transfer playlists between different accounts on the **same platform** (e.g., from one Spotify account to another).
- **Fast Transfer**: Async API calls for faster playlist processing.
- **Smart Caching**: Platform-specific unique hashes are stored in the database for faster future transfers. This eliminates the need to re-search playlists and speeds up repeat transfers.
- **Simple User Authentication**: Secure login with OAuth 2.0 for Spotify integration.

---

## 🔧 Tech Stack

- **Backend**: Python, Flask
- **Database**: MongoDB
- **Authentication**: OAuth 2.0 and other platform specific APIs
- **Frontend**: HTML, CSS, Tailwind, JS
- **Async Handling**: Async API calls for faster performance

---

## 🌐 Live Version

The project will soon be hosted live for public use. Stay tuned for updates!

---

## 💻 Setup and Installation

### Clone this repository:
```bash
git clone https://github.com/harshil-mistry/musiclink-playlist-converter.git
```

### Install Dependencies
```bash
cd musiclink-playlist-converter
pip install -r requirements.txt
```

### Set up environment variables:
Create a `.env` file in the root directory and add the following:
```bash
SPOTIPY_CLIENT_ID = ''
SPOTIPY_CLIENT_SECRET = '' 
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:5000/spotifycallback'
MONGODB_URL = ""
YOUTUBE_API_KEY = ""
```

> Note: You will have to setup spotify and Google Projects and add your accounts for demo usage

### Set up MongoDB:
- Create a Database named 'Playlist_Conversion'.
- Create a collection in that Databse named 'metadata'.

---

## 📝 Usage

1. **Log in**: Use your Source platform account to authenticate and access your playlists.
2. **Select your playlists**: Choose the playlist you want to transfer.
3. **Choose your destination**: Pick the platform or account where you want the playlist transferred.
4. **Track progress**: Watch your playlists being transferred in real time!
