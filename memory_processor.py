# memory_processor.py

import asyncio
import logging
from datetime import datetime
from vector_db_manager import VectorDBManager 

async def save_to_memory_async(document: str, metadata: dict, vector_db_manager: VectorDBManager, collection_name: str):
    """
    Asynchronously processes and saves a single document and its metadata to the vector database.
    This function ensures the document text is stored in the payload for RAG.
    """
    if not document:
        return

    logging.info(f"Saving artifact of type '{metadata.get('type', 'N/A')}' to memory...")

    # Add the document's text and a timestamp to the metadata payload. 
    # This is what allows the RAG system to retrieve the full content of past work.
    metadata['text'] = document
    metadata['timestamp'] = datetime.utcnow().isoformat()
    
    try:
        # The .add() method expects lists, so we wrap our single items in a list.
        await vector_db_manager.add(collection_name, [document], [metadata])
        
        # Yield control back to the event loop to keep the UI responsive
        await asyncio.sleep(0) 
        
        logging.info(f"Successfully saved artifact to '{collection_name}'.")
    except Exception as e:
        logging.error(f"Failed to save artifact to memory: {e}")

