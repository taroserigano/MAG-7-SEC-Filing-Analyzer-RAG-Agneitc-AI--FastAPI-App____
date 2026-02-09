from pinecone import Pinecone, ServerlessSpec
from typing import Optional, List, Dict, Any
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class PineconeClient:
    """
    Pinecone client for vector database operations with embedding support.
    """
    
    def __init__(self, api_key: str, index_name: str, environment: str, openai_api_key: str = ""):
        """
        Initialize Pinecone client.
        
        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            environment: Pinecone environment (e.g., us-west1-gcp)
            openai_api_key: OpenAI API key for embeddings
        """
        self.api_key = api_key
        self.index_name = index_name
        self.environment = environment
        self.pc: Optional[Pinecone] = None
        self.index = None
        
        # Initialize OpenAI client for embeddings
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
        else:
            self.openai_client = None
        
    def connect(self):
        """
        Connect to Pinecone and initialize or get the index.
        """
        try:
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {self.index_name}")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=1536,  # OpenAI embedding dimension
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"  # Free tier supported region
                    )
                )
            
            self.index = self.pc.Index(self.index_name)
            logger.info(f"Connected to Pinecone index: {self.index_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        """
        Check if connected to Pinecone.
        """
        return self.index is not None
    
    def upsert_vectors(self, vectors: list):
        """
        Upsert vectors to Pinecone index.
        
        Args:
            vectors: List of tuples (id, embedding, metadata)
        """
        if not self.index:
            raise Exception("Pinecone client not connected")
        
        self.index.upsert(vectors=vectors)
        logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts using OpenAI.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not self.openai_client:
            raise Exception("OpenAI client not initialized")
        
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def upsert_chunks(
        self,
        chunks: List[str],
        metadata_list: List[Dict[str, Any]],
        namespace: str = ""
    ) -> Dict[str, int]:
        """
        Upsert text chunks with their embeddings to Pinecone.
        
        Args:
            chunks: List of text chunks
            metadata_list: List of metadata dicts for each chunk
            namespace: Optional namespace for organization
            
        Returns:
            Dict with upsert statistics
        """
        if not self.index:
            raise Exception("Pinecone client not connected")
        
        # Create embeddings
        embeddings = self.create_embeddings(chunks)
        
        # Prepare vectors for upsert
        vectors = []
        for i, (chunk, embedding, metadata) in enumerate(zip(chunks, embeddings, metadata_list)):
            vector_id = f"{metadata.get('ticker', 'unknown')}_{metadata.get('form_type', 'unknown')}_{metadata.get('year', 'unknown')}_{metadata.get('chunk_index', i)}"
            
            # Add chunk text to metadata for hybrid search
            metadata_with_text = {**metadata, "text": chunk}
            
            vectors.append({
                "id": vector_id,
                "values": embedding,
                "metadata": metadata_with_text
            })
        
        # Upsert in batches
        batch_size = 100
        upserted_count = 0
        
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            upserted_count += len(batch)
        
        logger.info(f"Upserted {upserted_count} chunks to Pinecone")
        return {"upserted_count": upserted_count}
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            filter_dict: Metadata filters (e.g., {"ticker": "AAPL"})
            namespace: Optional namespace
            
        Returns:
            List of matching documents with scores and metadata
        """
        if not self.index:
            raise Exception("Pinecone client not connected")
        
        # Create query embedding
        query_embedding = self.create_embeddings([query])[0]
        
        # Search
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter_dict,
            namespace=namespace,
            include_metadata=True
        )
        
        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata,
                "text": match.metadata.get("text", "")
            })
        
        return formatted_results
    
    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        keyword: Optional[str] = None,
        namespace: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword filtering).
        
        Args:
            query: Search query text
            top_k: Number of results
            filter_dict: Metadata filters
            keyword: Optional keyword to filter on (searches in text)
            namespace: Optional namespace
            
        Returns:
            List of matching documents
        """
        # Start with vector search (get more results initially)
        results = self.search(query, top_k=top_k * 2, filter_dict=filter_dict, namespace=namespace)
        
        # Apply keyword filter if provided
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                r for r in results 
                if keyword_lower in r.get("text", "").lower()
            ]
        
        # Return top_k results
        return results[:top_k]
    
    def query(
        self, 
        query_embedding: list, 
        top_k: int = 5,
        filter: Optional[dict] = None
    ):
        """
        Query Pinecone index for similar vectors (low-level method).
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Metadata filter
            
        Returns:
            Query results
        """
        if not self.index:
            raise Exception("Pinecone client not connected")
        
        return self.index.query(
            vector=query_embedding,
            top_k=top_k,
            filter=filter,
            include_metadata=True
        )


# Global Pinecone client instance
_pinecone_client: Optional[PineconeClient] = None


def get_pinecone_client() -> PineconeClient:
    """
    Get or create the global Pinecone client instance.
    """
    global _pinecone_client
    if _pinecone_client is None:
        raise Exception("Pinecone client not initialized")
    return _pinecone_client


def init_pinecone_client(api_key: str, index_name: str, environment: str, openai_api_key: str = "") -> PineconeClient:
    """
    Initialize the global Pinecone client instance.
    """
    global _pinecone_client
    _pinecone_client = PineconeClient(api_key, index_name, environment, openai_api_key)
    _pinecone_client.connect()
    return _pinecone_client
