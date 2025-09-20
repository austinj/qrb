#!/usr/bin/env python3
"""
Unified script to export Spotify playlists from all shows directly from markdown files
to individual CSV files with track details (artist, song, release, duration, released year, label).
"""

import os
import csv
import re
from datetime import datetime
from pathlib import Path
import requests
import time
from dotenv import load_dotenv
import base64
import yaml


def extract_frontmatter(file_path):
    """Extract YAML frontmatter from a markdown file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Match YAML frontmatter between --- delimiters (handle both \n and \r\n line endings)
    frontmatter_match = re.match(r'^---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)', content, re.DOTALL)
    
    if frontmatter_match:
        frontmatter_content = frontmatter_match.group(1)
        try:
            return yaml.safe_load(frontmatter_content)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {file_path}: {e}")
            return None
    else:
        print(f"No frontmatter found in {file_path}")
        return None


class SpotifyPlaylistExporter:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify API credentials not found in .env file")
        
        self.access_token = None
        self.token_expires_at = 0
        
    def get_access_token(self):
        """Get Spotify access token using client credentials flow."""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        # Encode client credentials
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {'grant_type': 'client_credentials'}
        
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            headers=headers,
            data=data
        )
        
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            # Set expiration time (subtract 60 seconds for safety)
            self.token_expires_at = time.time() + token_data['expires_in'] - 60
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.status_code} {response.text}")
    
    def extract_playlist_id(self, spotify_url):
        """Extract playlist ID from Spotify URL."""
        # Handle both embed and regular playlist URLs
        match = re.search(r'playlist/([a-zA-Z0-9]+)', spotify_url)
        return match.group(1) if match else None
    
    def get_album_details(self, album_ids):
        """Get detailed album information including labels for multiple albums."""
        if not album_ids:
            return {}
        
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        album_details = {}
        
        # Process albums in batches of 20 (Spotify API limit)
        for i in range(0, len(album_ids), 20):
            batch_ids = album_ids[i:i+20]
            ids_param = ','.join(batch_ids)
            
            url = f'https://api.spotify.com/v1/albums?ids={ids_param}'
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                for album in data.get('albums', []):
                    if album:  # Album can be None if not found
                        album_details[album['id']] = {
                            'label': album.get('label', ''),
                            'copyrights': album.get('copyrights', [])
                        }
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 1))
                print(f"Rate limited on albums, waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Error fetching album details: {response.status_code}")
            
            time.sleep(0.1)  # Rate limiting
        
        return album_details

    def get_playlist_tracks(self, playlist_id):
        """Get all tracks from a Spotify playlist."""
        token = self.get_access_token()
        headers = {'Authorization': f'Bearer {token}'}
        
        tracks = []
        album_ids = set()
        url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
        
        # First pass: collect all tracks and album IDs
        while url:
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data['items']:
                    track = item.get('track')
                    if track and track['type'] == 'track':
                        # Extract basic track information
                        artists = ', '.join([artist['name'] for artist in track['artists']])
                        song = track['name']
                        album_name = track['album']['name']
                        album_id = track['album']['id']
                        duration_ms = track['duration_ms']
                        release_date = track['album']['release_date']
                        
                        # Convert duration from milliseconds to MM:SS format
                        duration_seconds = duration_ms // 1000
                        duration_formatted = f"{duration_seconds // 60}:{duration_seconds % 60:02d}"
                        
                        # Extract release year
                        release_year = release_date.split('-')[0] if release_date else ''
                        
                        tracks.append({
                            'artist': artists,
                            'song': song,
                            'release': album_name,
                            'duration': duration_formatted,
                            'released': release_year,
                            'album_id': album_id,
                            'label': ''  # Will be filled in later
                        })
                        
                        album_ids.add(album_id)
                
                # Get next page URL
                url = data.get('next')
                
                # Rate limiting
                time.sleep(0.1)
                
            elif response.status_code == 429:
                # Rate limited, wait and retry
                retry_after = int(response.headers.get('Retry-After', 1))
                print(f"Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Error fetching playlist {playlist_id}: {response.status_code} {response.text}")
                break
        
        # Second pass: get detailed album information including labels
        if album_ids:
            print(f"Fetching label information for {len(album_ids)} unique albums...")
            album_details = self.get_album_details(list(album_ids))
            
            # Third pass: update tracks with label information
            for track in tracks:
                album_id = track['album_id']
                if album_id in album_details:
                    track['label'] = album_details[album_id]['label']
                del track['album_id']  # Remove temporary field
        
        return tracks
    
    def export_playlist_to_csv(self, playlist_id, show_title, pub_date):
        """Export a playlist to CSV file."""
        # Create filename based on pub_date and show_title
        safe_title = re.sub(r'[^\w\s-]', '', show_title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        filename = f"{pub_date}_{safe_title}_playlist.csv"
        
        # Create output directory if it doesn't exist
        output_dir = Path("playlist_exports")
        output_dir.mkdir(exist_ok=True)
        
        filepath = output_dir / filename
        
        # Check if file already exists
        if filepath.exists():
            print(f"Skipping {show_title} ({pub_date}) - file already exists: {filename}")
            return
        
        print(f"Fetching tracks for {show_title} ({pub_date})...")
        
        tracks = self.get_playlist_tracks(playlist_id)
        
        if not tracks:
            print(f"No tracks found for {show_title}")
            return
        
        # Write to CSV
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['artist', 'song', 'release', 'duration', 'released', 'label']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(tracks)
        
        print(f"Exported {len(tracks)} tracks to {filepath}")
    
    def process_markdown_files(self):
        """Process markdown files directly and export 2025 playlists."""
        # Path to the shows directory
        shows_dir = Path("src/shows")
        
        if not shows_dir.exists():
            print(f"Directory {shows_dir} does not exist!")
            return
        
        processed_count = 0
        skipped_count = 0
        
        # Process all .md files in the shows directory
        for md_file in shows_dir.glob("*.md"):
            frontmatter = extract_frontmatter(md_file)
            
            if frontmatter:
                pub_date = frontmatter.get('pubDate', '')
                spotify_url = frontmatter.get('spotify', '')
                title = frontmatter.get('title', '')
                
                # Filter for shows with Spotify URLs
                if spotify_url:
                    playlist_id = self.extract_playlist_id(spotify_url)
                    
                    if playlist_id:
                        # Check if already processed
                        safe_title = re.sub(r'[^\w\s-]', '', title).strip()
                        safe_title = re.sub(r'[-\s]+', '-', safe_title)
                        filename = f"{pub_date}_{safe_title}_playlist.csv"
                        filepath = Path("playlist_exports") / filename
                        
                        if filepath.exists():
                            skipped_count += 1
                            print(f"Skipping {title} ({pub_date}) - already processed")
                        else:
                            self.export_playlist_to_csv(playlist_id, title, pub_date)
                            processed_count += 1
                    else:
                        print(f"Could not extract playlist ID from: {spotify_url}")
        
        print(f"\nProcessing completed!")
        print(f"New playlists exported: {processed_count}")
        print(f"Previously processed (skipped): {skipped_count}")


def main():
    try:
        exporter = SpotifyPlaylistExporter()
        exporter.process_markdown_files()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure to:")
        print("1. Set your Spotify API credentials in the .env file")
        print("2. Install required packages: pip install requests python-dotenv pyyaml")


if __name__ == "__main__":
    main()