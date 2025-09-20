#!/usr/bin/env python3
"""
Test script to see which 2025 shows will be processed.
"""

import csv

def preview_2025_shows():
    """Preview which shows from 2025 will be processed."""
    shows_2025 = []
    
    with open('shows_data.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            pub_date = row['pubDate']
            spotify_url = row['spotify']
            title = row['title']
            
            if pub_date.startswith('2025') and spotify_url:
                shows_2025.append({
                    'title': title,
                    'pubDate': pub_date,
                    'spotify': spotify_url
                })
    
    print(f"Found {len(shows_2025)} shows from 2025 with Spotify playlists:")
    print()
    
    for show in shows_2025:
        print(f"- {show['title']} ({show['pubDate']})")
        print(f"  Playlist: {show['spotify']}")
        print()

if __name__ == "__main__":
    preview_2025_shows()