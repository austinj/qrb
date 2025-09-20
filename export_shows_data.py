#!/usr/bin/env python3
"""
Script to export pubDate and spotify URLs from frontmatter of all .md files 
in src/shows directory to a CSV file.
"""

import os
import csv
import re
from pathlib import Path
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


def main():
    # Path to the shows directory
    shows_dir = Path("src/shows")
    
    if not shows_dir.exists():
        print(f"Directory {shows_dir} does not exist!")
        return
    
    # List to store extracted data
    shows_data = []
    
    # Process all .md files in the shows directory
    for md_file in shows_dir.glob("*.md"):
        print(f"Processing {md_file.name}...")
        
        frontmatter = extract_frontmatter(md_file)
        
        if frontmatter:
            pub_date = frontmatter.get('pubDate', '')
            spotify = frontmatter.get('spotify', '')
            title = frontmatter.get('title', '')
            
            shows_data.append({
                'filename': md_file.name,
                'title': title,
                'pubDate': pub_date,
                'spotify': spotify
            })
    
    # Sort by pubDate for better organization
    shows_data.sort(key=lambda x: x['pubDate'] if x['pubDate'] else '')
    
    # Export to CSV
    output_file = "shows_data.csv"
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['filename', 'title', 'pubDate', 'spotify']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(shows_data)
    
    print(f"\nExported {len(shows_data)} shows to {output_file}")
    print(f"CSV file saved in: {os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()