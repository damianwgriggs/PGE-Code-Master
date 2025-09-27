# vector_db_manager.py
# Manages the local, on-disk Qdrant vector database.

import logging
import uuid
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
import streamlit as st

class VectorDBManager:
    """Handles all interactions with the local Qdrant vector database."""
    def __init__(self, db_path="./qdrant_data"):
        """
        Initializes the VectorDBManager.
        
        Args:
            db_path (str): The local directory to store the database files.
        """
        try:
            # This tells Qdrant to use a local folder, not a server.
            self.client = QdrantClient(path=db_path)
            
            # Use a pre-trained model to turn text into vector embeddings
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            logging.info(f"Successfully connected to local Qdrant DB at path: {db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize local Qdrant client: {e}")
            st.error(f"Could not set up local vector database. Error: {e}")
            st.stop()

    async def initialize_collection(self, collection_name: str):
        """Creates a new collection in the database if it doesn't already exist."""
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.encoder.get_sentence_embedding_dimension(),
                    distance=models.Distance.COSINE
                )
            )
            logging.info(f"Collection '{collection_name}' created or already exists.")
        except Exception as e:
            # This can happen if multiple processes try to create at once; usually safe to ignore.
            logging.warning(f"Could not create collection '{collection_name}' (it may already exist): {e}")

    async def add(self, collection_name: str, documents: list, metadata: list):
        """Adds documents and their metadata to a specified collection."""
        if not documents:
            return
        try:
            vectors = self.encoder.encode(documents).tolist()
            
            # Generate unique IDs for each point
            ids = [str(uuid.uuid4()) for _ in documents]

            self.client.upsert(
                collection_name=collection_name,
                points=models.Batch(
                    ids=ids,
                    vectors=vectors,
                    payloads=metadata
                ),
                wait=True
            )
            logging.info(f"Successfully added {len(documents)} documents to '{collection_name}'.")
        except Exception as e:
            logging.error(f"Failed to add documents to '{collection_name}': {e}")
            
    async def search(self, collection_name: str, query_text: str, limit: int = 5):
        """Queries a collection to find the most similar documents."""
        try:
            query_vector = self.encoder.encode(query_text).tolist()
            hits = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit
            )
            # Return the full search result objects
            return [hit.dict() for hit in hits]
        except Exception as e:
            logging.error(f"Failed to query '{collection_name}': {e}")
            return []

    async def delete_collection(self, collection_name: str):
        """Deletes a collection from the database."""
        try:
            self.client.delete_collection(collection_name=collection_name)
            logging.info(f"Successfully deleted collection '{collection_name}'.")
        except Exception as e:
            logging.error(f"Failed to delete collection '{collection_name}': {e}")

