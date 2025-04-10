from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
import time
import json
import os
import re
from urllib.parse import parse_qs, urlparse, urlencode

class YouTubeExtractor:
    def __init__(self):
        """Initialize the YouTubeExtractor with Chrome in headless mode"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Use Chrome Service directly
            service = ChromeService()
            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            
            self.wait = WebDriverWait(self.driver, 10)
            self.urls_file = "youtube_urls.txt"  # Changed from .json to .txt
            
        except Exception as e:
            print(f"Error initializing Chrome driver: {e}")
            raise

    def clean_url(self, url: str) -> str:
        """Clean YouTube URL by removing unnecessary parameters"""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Keep only essential parameters
        essential_params = {'v': query_params.get('v', [''])[0]}
        if 'list' in query_params:
            essential_params['list'] = query_params.get('list', [''])[0]
            
        clean_query = urlencode(essential_params)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_query}"

    def clean_title(self, title: str) -> str:
        """Clean title by removing duplicate numbers and extra spaces"""
        # Remove duplicate numbering (e.g., "1. 1." becomes "1.")
        title = re.sub(r'(\d+\.)\s*\1', r'\1', title)
        # Remove extra whitespace
        title = ' '.join(title.split())
        return title

    def save_results_to_file(self, results: list[dict]) -> None:
        """Save results to the URLs file"""
        try:
            # Load existing URLs
            existing_urls = self._load_urls()
            
            # Add new URLs if they don't exist
            for result in results:
                if not any(entry["url"] == result["url"] for entry in existing_urls):
                    existing_urls.append(result)
            
            # Save back to file in text format
            with open(self.urls_file, 'w', encoding='utf-8') as f:
                for entry in existing_urls:
                    f.write(f"Title: {entry['title']}\n")
                    f.write(f"URL: {entry['url']}\n")
                    if 'transcript' in entry:
                        f.write(f"Transcript: {entry['transcript']}\n")
                    f.write("\n---\n\n")  # Separator between entries
            
            print(f"Successfully saved {len(results)} new URLs")
        except Exception as e:
            print(f"Error saving URLs: {e}")

    def search_mode(self, query: str, max_results: int = 3) -> list[dict]:  # Changed default from 10 to 3
        """Search YouTube and return video information"""
        try:
            self.driver.get("https://www.youtube.com/results?search_query=" + query)
            time.sleep(2)
            
            videos = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-video-renderer")
            ))
            
            results = []
            for video in videos[:max_results]:  # This will now only process first 3 videos
                try:
                    title_element = video.find_element(By.CSS_SELECTOR, "#video-title")
                    title = self.clean_title(title_element.get_attribute("title"))
                    url = self.clean_url(title_element.get_attribute("href"))
                    
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url
                        })
                except Exception:
                    continue
            
            # Save results to file
            if results:
                self.save_results_to_file(results)
                    
            return results
            
        except Exception as e:
            print(f"An error occurred in search mode: {str(e)}")
            return []

    def playlist_mode(self, playlist_url: str) -> list[dict]:
        """Extract all video URLs from a YouTube playlist"""
        try:
            self.driver.get(playlist_url)
            time.sleep(3)
            
            # Scroll to load all videos
            last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                time.sleep(2)
                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            playlist_items = self.wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "ytd-playlist-video-renderer")
            ))
            
            results = []
            for item in playlist_items:
                try:
                    title_element = item.find_element(By.CSS_SELECTOR, "#video-title")
                    title = self.clean_title(title_element.get_attribute("title"))
                    url = self.clean_url(title_element.get_attribute("href"))
                    
                    if title and url:
                        results.append({
                            "title": title,
                            "url": url
                        })
                except Exception:
                    continue

            # Save results to file
            if results:
                self.save_results_to_file(results)

            return results

        except Exception as e:
            print(f"An error occurred in playlist mode: {str(e)}")
            return []

    def url_mode(self, url: str) -> None:
        """Add a single URL to the saved URLs list"""
        try:
            if not self._is_valid_youtube_url(url):
                print("Invalid YouTube URL!")
                return

            clean_url = self.clean_url(url)
            print(f"Processing URL: {clean_url}")

            self.driver.get(clean_url)
            # Wait longer for dynamic content to load
            time.sleep(3)

            # Try multiple modern YouTube title selectors with explicit waits
            title = None
            selectors = [
                "#title h1.ytd-video-primary-info-renderer",  # Modern layout
                "#container h1.ytd-video-primary-info-renderer",  # Alternative modern
                "h1.title.style-scope.ytd-video-primary-info-renderer"  # Full path
            ]

            for selector in selectors:
                try:
                    element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    title = element.get_attribute('innerText')
                    if title and title.strip():
                        break
                except:
                    continue

            if not title or not title.strip():
                # Try JavaScript as fallback
                try:
                    title = self.driver.execute_script(
                        'return document.querySelector("#title h1").innerText'
                    )
                except:
                    print("Could not extract video title!")
                    return

            title = self.clean_title(title.strip())
            if not title:
                print("Could not extract valid title!")
                return

            result = {"title": title, "url": clean_url}
            self.save_results_to_file([result])
            print(f"Added: {title}")

        except Exception as e:
            print(f"Error in URL mode: {e}")

    def _is_valid_youtube_url(self, url: str) -> bool:
        """Validate if the URL is a valid YouTube video URL"""
        try:
            parsed = urlparse(url)
            if parsed.netloc not in ['www.youtube.com', 'youtube.com']:
                return False
            if parsed.path not in ['/watch', '/playlist']:
                return False
            query_params = parse_qs(parsed.query)
            return 'v' in query_params or 'list' in query_params
        except:
            return False

    def _load_urls(self) -> list:
        """Load saved URLs from file"""
        try:
            if os.path.exists(self.urls_file):
                urls = []
                current_entry = {}
                
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    entries = content.split("\n---\n")
                    
                    for entry in entries:
                        if not entry.strip():
                            continue
                        
                        lines = entry.strip().split("\n")
                        current_entry = {}
                        
                        for line in lines:
                            if line.startswith("Title: "):
                                current_entry["title"] = line[7:]
                            elif line.startswith("URL: "):
                                current_entry["url"] = line[5:]
                            elif line.startswith("Transcript: "):
                                current_entry["transcript"] = line[12:]
                        
                        if current_entry:
                            urls.append(current_entry)
                return urls
            return []
        except Exception as e:
            print(f"Error loading URLs: {e}")
            return []

    def _save_urls(self, urls: list) -> None:
        """Save URLs to file"""
        with open(self.urls_file, 'w') as f:
            json.dump(urls, f, indent=2)

    def clear_all_data(self) -> None:
        """Clear all saved URLs and titles"""
        try:
            with open(self.urls_file, 'w') as f:
                json.dump([], f)
            print("Successfully cleared all saved data!")
        except Exception as e:
            print(f"Error clearing data: {e}")

    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    print("\033[2J\033[H", end="")  # Clear screen
    extractor = YouTubeExtractor()
    
    try:
        while True:
            print("\nYouTube Link Extractor")
            print("1. Search Mode (Get top 3 videos for a topic)")  # Updated text
            print("2. Playlist Mode (Extract all videos from a playlist)")
            print("3. URL Mode (Add specific video URLs)")
            print("4. View Saved URLs")
            print("5. Delete All Saved Data")
            print("6. Lets move to next stage")
            
            choice = input("\nSelect mode (1-6): ").strip()
            
            if choice == "1":
                query = input("Enter search query: ").strip()
                if query:
                    print("\nSearching...")
                    results = extractor.search_mode(query)  # Using new default of 3
                    if results:
                        print(f"\nFound top {len(results)} results:")  # Updated message
                        for i, video in enumerate(results, 1):
                            print(f"\n{i}. {video['title']}")
                            print(f"   URL: {video['url']}")
                    else:
                        print("No results found.")
                        
            elif choice == "2":
                playlist_url = input("Enter playlist URL: ").strip()
                if playlist_url:
                    print("\nExtracting playlist videos...")
                    results = extractor.playlist_mode(playlist_url)
                    if results:
                        print(f"\nFound {len(results)} videos in playlist:")
                        for i, video in enumerate(results, 1):
                            print(f"\n{i}. {video['title']}")
                            print(f"   URL: {video['url']}")
                    else:
                        print("No videos found in playlist.")
                        
            elif choice == "3":
                url = input("Enter YouTube video URL: ").strip()
                if url:
                    extractor.url_mode(url)
                    
            elif choice == "4":
                urls_list = extractor._load_urls()
                if urls_list:
                    print("\nSaved URLs:")
                    for i, entry in enumerate(urls_list, 1):
                        print(f"\n{i}. {entry['title']}")
                        print(f"   URL: {entry['url']}")
                else:
                    print("\nNo saved URLs found.")
                    
            elif choice == "5":
                confirm = input("Are you sure you want to delete all saved data? (y/n): ").strip().lower()
                if confirm == 'y':
                    extractor.clear_all_data()
                else:
                    print("Operation cancelled.")

            elif choice == "6":
                print("Moving to Next Stage!")
                break
                
            else:
                print("Invalid choice. Please select 1-6.")
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
    finally:
        extractor.close()

if __name__ == "__main__":
    main()
