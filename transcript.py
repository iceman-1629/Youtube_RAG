import json
import re
import time
import requests
import xml.etree.ElementTree as ET
from pytube import YouTube
from typing import Dict, List, Optional, Union
from urllib.parse import parse_qs, urlparse
import html
import os
import csv

class AlternativeTranscriptExtractor:
    def __init__(self, txt_file="youtube_urls.txt"):
        self.txt_file = txt_file
        self.max_retries = 3
        self.retry_delay = 2
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL"""
        try:
            # Handle youtube.com URLs
            if "youtube.com" in url:
                query = urlparse(url).query
                return parse_qs(query)["v"][0]
            # Handle youtu.be URLs
            elif "youtu.be" in url:
                return urlparse(url).path.lstrip("/")
            else:
                return ""
        except Exception:
            return ""

    def _get_captions_from_pytube(self, video_id: str) -> str:
        """Attempt to get captions using pytube"""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            yt = YouTube(url)
            
            # Try to get English captions first
            caption_tracks = yt.captions
            
            if not caption_tracks:
                print(f"  ⚠️ No captions available via pytube")
                return ""
            
            # Try English captions first (both 'en' and 'a.en')
            en_caption = caption_tracks.get('en') or caption_tracks.get('a.en')
            
            if en_caption:
                caption_xml = en_caption.xml_captions
                return self._parse_caption_xml(caption_xml)
            
            # If no English captions, try the first available caption
            for lang_code, caption in caption_tracks.items():
                try:
                    caption_xml = caption.xml_captions
                    return self._parse_caption_xml(caption_xml)
                except Exception:
                    continue
                
            return ""
        except Exception as e:
            print(f"  ⚠️ Error in pytube extraction: {str(e)}")
            return ""

    def _parse_caption_xml(self, caption_xml: str) -> str:
        """Parse caption XML and convert to plain text"""
        try:
            root = ET.fromstring(caption_xml)
            transcript_pieces = []
            
            for element in root.findall('.//text'):
                if element.text:
                    transcript_pieces.append(html.unescape(element.text))
            
            return ' '.join(transcript_pieces)
        except Exception as e:
            print(f"  ⚠️ Error parsing caption XML: {str(e)}")
            return ""

    def _get_captions_from_direct_request(self, video_id: str) -> str:
        """Attempt to get captions using direct HTTP requests"""
        try:
            # First, get the video page to extract timedtext URL
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = self.session.get(url)
            
            if response.status_code != 200:
                return ""
            
            # Try to find the caption track URL
            # Look for playerCaptionsTracklistRenderer
            pattern = r'"captionTracks":\s*(\[.*?\])'
            matches = re.search(pattern, response.text)
            
            if not matches:
                return ""
            
            caption_tracks_json = matches.group(1)
            # Replace backslashes and clean up the JSON
            caption_tracks_json = caption_tracks_json.replace('\\u0026', '&')
            
            # Try to extract the first English caption URL
            en_pattern = r'"baseUrl":\s*"(.*?)".*?"languageCode":\s*"en"'
            en_matches = re.search(en_pattern, caption_tracks_json)
            
            if en_matches:
                caption_url = en_matches.group(1)
            else:
                # If no English captions, get the first available caption URL
                base_url_pattern = r'"baseUrl":\s*"(.*?)"'
                base_url_matches = re.search(base_url_pattern, caption_tracks_json)
                if not base_url_matches:
                    return ""
                caption_url = base_url_matches.group(1)
            
            # Fetch the caption file
            caption_response = self.session.get(caption_url)
            if caption_response.status_code != 200:
                return ""
            
            # Parse the XML
            return self._parse_caption_xml(caption_response.text)
            
        except Exception as e:
            print(f"  ⚠️ Error in direct request extraction: {str(e)}")
            return ""

    def _load_txt_data(self) -> list:
        """Load data from TXT file"""
        try:
            if not os.path.exists(self.txt_file):
                print(f"Error: TXT file '{self.txt_file}' not found!")
                return []

            entries = []
            current_entry = {}
            
            with open(self.txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                sections = content.split("\n---\n")
                
                for section in sections:
                    if not section.strip():
                        continue
                    
                    lines = section.strip().split("\n")
                    current_entry = {}
                    
                    for line in lines:
                        if line.startswith("Title: "):
                            current_entry["title"] = line[7:]
                        elif line.startswith("URL: "):
                            current_entry["url"] = line[5:]
                        elif line.startswith("Transcript: "):
                            current_entry["transcript"] = line[12:]
                    
                    if current_entry:
                        entries.append(current_entry)
                        
            return entries
        except Exception as e:
            print(f"Error loading TXT file: {e}")
            return []

    def get_transcript(self, video_id: str) -> str:
        """Get transcript using multiple methods"""
        for attempt in range(self.max_retries):
            try:
                # Try pytube method first
                transcript = self._get_captions_from_pytube(video_id)
                if transcript:
                    return transcript
                
                # If pytube fails, try direct request method
                transcript = self._get_captions_from_direct_request(video_id)
                if transcript:
                    return transcript
                
                if attempt < self.max_retries - 1:
                    print(f"  ⚠️ Retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                else:
                    return "NO_SUBTITLES_AVAILABLE"
                    
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"  ⚠️ Retry {attempt + 1}/{self.max_retries}")
                    time.sleep(self.retry_delay)
                else:
                    return f"ERROR_{str(e).replace(chr(10), ' ')}"
        
        return "NO_SUBTITLES_AVAILABLE"

    def update_json_with_transcripts(self):
        """Update TXT file with transcripts for all videos"""
        try:
            data = self._load_txt_data()
            if not data:
                return

            total = len(data)
            success = 0
            failed = 0
            no_subs = 0
            skipped = 0

            print(f"\nProcessing {total} videos...")
            print("-" * 50)

            for i, entry in enumerate(data, 1):
                # Check if entry already has a valid transcript
                has_valid_transcript = (
                    'transcript' in entry and 
                    isinstance(entry['transcript'], str) and 
                    entry['transcript'] and 
                    not entry['transcript'].startswith(("ERROR_", "NO_"))
                )
                
                if has_valid_transcript:
                    skipped += 1
                    print(f"[{i}/{total}] Skipping (already has transcript): {entry['title'][:70]}")
                    continue

                print(f"[{i}/{total}] Processing: {entry['title'][:70]}...")
                
                # Extract video ID
                if 'url' in entry and entry['url']:
                    video_id = self._extract_video_id(entry['url'])
                    if not video_id:
                        print(f"  ❌ Failed: Could not extract video ID from URL: {entry['url']}")
                        failed += 1
                        entry['transcript'] = "ERROR_INVALID_URL"
                        continue
                else:
                    print(f"  ❌ Failed: No URL provided for video")
                    failed += 1
                    entry['transcript'] = "ERROR_NO_URL"
                    continue
                
                # Get transcript
                transcript = self.get_transcript(video_id)
                
                if transcript.startswith("ERROR_"):
                    print(f"  ❌ Failed: {transcript[6:]}")
                    failed += 1
                elif transcript == "NO_SUBTITLES_AVAILABLE":
                    print(f"  ⚠️ No subtitles available")
                    no_subs += 1
                else:
                    word_count = len(transcript.split())
                    print(f"  ✓ Success ({word_count} words)")
                    success += 1
                
                entry['transcript'] = transcript

            # Save the updated data back to the file
            with open(self.txt_file, 'w', encoding='utf-8') as f:
                for entry in data:
                    f.write(f"Title: {entry.get('title', '')}\n")
                    f.write(f"URL: {entry.get('url', '')}\n")
                    f.write(f"Transcript: {entry.get('transcript', '')}\n")
                    f.write("\n---\n\n")

            print("\nSummary:")
            print(f"Total videos: {total}")
            print(f"Skipped (already had transcripts): {skipped}")
            print(f"Successfully extracted: {success}")
            print(f"No subtitles available: {no_subs}")
            print(f"Failed to extract: {failed}")

        except Exception as e:
            print(f"Error updating transcripts: {e}")

    def export_to_txt(self) -> None:
        """Export data to TXT file in youtubeRag directory"""
        try:
            data = self._load_txt_data()

            # Create youtubeRag directory if it doesn't exist
            output_dir = os.path.join(os.path.dirname(self.txt_file), 'youtubeRag')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create TXT file path in youtubeRag directory
            txt_filename = os.path.basename(self.txt_file)
            txt_file = os.path.join(output_dir, txt_filename)
            
            # Write to TXT
            with open(txt_file, 'w', encoding='utf-8') as f:
                for entry in data:
                    f.write(f"Title: {entry.get('title', '')}\n")
                    f.write(f"URL: {entry.get('url', '')}\n")
                    f.write(f"Transcript: {entry.get('transcript', '')}\n")
                    f.write("\n---\n\n")
            
            print(f"\nText file created: {txt_file}")
            
        except Exception as e:
            print(f"Error creating text file: {e}")

def main():
    # Make sure you have these libraries installed:
    # pip install pytube requests
    extractor = AlternativeTranscriptExtractor()
    extractor.update_json_with_transcripts()
    extractor.export_to_txt()

if __name__ == "__main__":
    main()