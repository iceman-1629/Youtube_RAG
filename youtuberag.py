import os
import asyncio
import shutil
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

WORKING_DIR = "./yrag"

# Delete working directory if it exists
if os.path.exists(WORKING_DIR):
    try:
        shutil.rmtree(WORKING_DIR)
        print(f"Cleaned up existing {WORKING_DIR} directory")
    except Exception as e:
        print(f"Error cleaning up directory: {e}")

# Create fresh working directory
os.makedirs(WORKING_DIR, exist_ok=True)


async def initialize_rag():
    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
        # llm_model_func=gpt_4o_complete
    )

    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag


def main():
    # Initialize RAG instance
    rag = asyncio.run(initialize_rag())

    with open("./youtube_urls.txt", "r", encoding="utf-8") as f:
        rag.insert(f.read())

    # Perform mix search
    print(
        rag.query(
            "give summary of transcript", param=QueryParam(mode="mix")
        )
    )


if __name__ == "__main__":
    main()
