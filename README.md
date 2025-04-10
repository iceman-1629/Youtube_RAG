# YouTubeRAG: OpenAI-Powered Video Analysis

This project is a specialized fork of [LightRAG](https://github.com/HKUDS/LightRAG) focused on YouTube video analysis using OpenAI's language models. It provides an end-to-end pipeline for extracting, processing, and analyzing YouTube video content.

## Features

- Extract transcripts from YouTube videos
- Process video content using OpenAI's language models
- Interactive querying of processed video content
- Support for both individual videos and playlists
- Automatic transcript extraction with fallback methods
- Knowledge graph generation from video content

## Installation

1. Clone this repository and install dependencies:
```bash
git clone https://github.com/iceman-1629/Youtube_RAG.git
cd Youtube_RAG
pip install -r requirements.txt
```

2. Set up your OpenAI API key in environment variables:
```bash
# Linux/Mac
export OPENAI_API_KEY="your-key-here"

# Windows (PowerShell)
$env:OPENAI_API_KEY="your-key-here"
```

## Usage

The project provides a streamlined interface through `main.py` that guides you through the entire process:

1. Run the main script:
```bash
python main.py
```

2. Choose your operation:
   - Add new videos and process them
   - Query existing database
   - Exit all

When adding new videos, you can:
- Add individual video URLs
- Add videos from a playlist
- Clear existing data and start fresh

The processed video content is stored in the `yrag/` directory, which contains:
- Knowledge graph data
- Vector embeddings
- Cache files

## Limitations

- Requires valid OpenAI API key
- Processes only videos with available captions/transcripts
- API rate limits may apply
- Processing time varies with video length

## Credits

This project is based on [LightRAG](https://github.com/HKUDS/LightRAG) by HKUDS, modified to work specifically with OpenAI's models for video content analysis.
