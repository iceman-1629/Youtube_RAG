import os
import asyncio
from typing import List, Dict

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

WORKING_DIR = "./yrag"

class RagSession:
    def __init__(self):
        self.conversation_history: List[Dict[str, str]] = []
    
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        # Keep last 6 messages (3 turns) to maintain context window
        if len(self.conversation_history) > 6:
            self.conversation_history = self.conversation_history[-6:]

async def load_existing_rag():
    """Load existing RAG database without reinitializing"""
    if not os.path.exists(WORKING_DIR):
        raise Exception(f"RAG database not found in {WORKING_DIR}")

    rag = LightRAG(
        working_dir=WORKING_DIR,
        embedding_func=openai_embed,
        llm_model_func=gpt_4o_mini_complete,
    )

    # Initialize storages without recreating
    await rag.initialize_storages()
    await initialize_pipeline_status()

    return rag

async def chat_with_rag(query: str, session: RagSession) -> str:
    """
    Chat with the RAG system while maintaining conversation history
    
    Args:
        query: The question or query to ask
        session: RagSession instance maintaining conversation history
    """
    rag = await load_existing_rag()
    
    param = QueryParam(
        mode="mix",  # Always use mix mode as it combines KG and vector retrieval
        conversation_history=session.conversation_history,
        history_turns=3  # Consider last 3 conversation turns for context
    )
    
    response = await rag.aquery(query, param=param)
    
    # Update conversation history
    session.add_to_history("user", query)
    session.add_to_history("assistant", response)
    
    return response

async def interactive_chat():
    """Run an interactive chat session with the RAG system"""
    session = RagSession()
    
    print("\nWelcome to YouTubeRAG Chat!")
    print("Type your query Or Type 'exit' or 'quit' to go to main menu")
    print("----------------------------------------")
    
    while True:
        try:
            # Get user input
            query = input("\nYou: ").strip()
            
            # Check for exit command
            if query.lower() in ['exit', 'quit']:
                print("\nRouting to Main Menu!")
                break
            
            if not query:
                print("Please enter a question!")
                continue
            
            # Get response from RAG
            print("\nAssistant: ", end='', flush=True)
            response = await chat_with_rag(query, session)
            print(response)
            
        except Exception as e:
            print(f"\nError: {e}")
            print("Please try again.")

if __name__ == "__main__":
    asyncio.run(interactive_chat())