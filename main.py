import os
import sys
import asyncio
from typing import List, Optional

def print_step_header(step: str):
    """Print a formatted step header"""
    print("\n" + "="*50)
    print(f"Step: {step}")
    print("="*50 + "\n")

async def run_step(step_name: str, command: str) -> bool:
    """Run a pipeline step and handle errors"""
    print_step_header(step_name)
    try:
        if os.system(command) == 0:
            print(f"\n✅ {step_name} completed successfully!")
            return True
        else:
            print(f"\n❌ {step_name} failed. Would you like to retry? (y/n): ")
            if input().lower().strip() == 'y':
                return await run_step(step_name, command)
            return False
    except Exception as e:
        print(f"\n❌ Error in {step_name}: {e}", file=sys.stderr)
        return False

async def process_new_videos():
    """Process pipeline for adding new videos"""
    print("\nStarting pipeline to add new videos...")
    
    # Step 1: YouTube Link Extraction
    if await run_step("YouTube Link Extraction", "python ylink_extract.py"):
        # Verify youtube_urls.txt exists
        if not os.path.exists("youtube_urls.txt"):
            print("❌ Error: youtube_urls.txt not found. Cannot continue.", file=sys.stderr)
            return

        # Step 2: Transcript Extraction
        print("\nProceeding with transcript extraction...")
        if await run_step("Transcript Extraction", "python transcript.py"):
            # Step 3: RAG Processing
            print("\nProceeding with RAG processing...")
            if await run_step("RAG Processing", "python youtuberag.py"):
                print("\n🎉 Pipeline completed successfully!")
                print("You can now query the database.")
                return True
            else:
                print("\n⚠️ RAG processing failed. Cannot proceed.")
        else:
            print("\n⚠️ Transcript extraction failed. Cannot proceed with RAG processing.")
    return False

async def query_existing_data():
    """Query existing RAG database"""
    if not os.path.exists("yrag"):
        print("\n❌ Error: No existing database found. Please add videos first.", file=sys.stderr)
        return False
    
    print("\nStarting query interface...")
    if await run_step("Query Interface", "python yrag_query.py"):
        return True
    else:
        print("\n⚠️ Failed to start query interface.")
        return False

async def main():
    print("\nWelcome to YouTubeRAG Pipeline!")
    
    while True:
        print("\nWhat would you like to do?")
        print("1. Add new videos and process them")
        print("2. Query existing database")
        print("3. Exit all")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            await process_new_videos()
        elif choice == "2":
            await query_existing_data()
        elif choice == "3":
            print("\nGoodbye!")
            break
        else:
            print("\nInvalid choice. Please select 1-3.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)