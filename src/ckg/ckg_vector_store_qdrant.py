from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
import uuid
import numpy as np

HOST = "localhost"
PORT = 6333

class QdrantVectorStore:
    """
    A vector store using Qdrant for storing and querying code embeddings with project-level filtering.

    Attributes:
        collection_name (str): Name of the Qdrant collection.
        dim (int): Dimensionality of the vectors.
    """

    def __init__(self, collection_name: str, dim: int):
        """
        Initialize the QdrantVectorStore and create the collection if it doesn't exist.

        Args:
            collection_name (str): The name of the collection to use.
            dim (int): The dimensionality of the vectors.
        """
        self.collection_name = collection_name
        self.dim = dim

        self.client = QdrantClient(host=HOST, port=PORT)

        # Create the collection if it doesn't exist
        if not self.client.collection_exists(collection_name):
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def add(self, vectors: list[dict]):
        """
        Add a list of vectors to the collection, associating them with a project name.

        Args:
            vectors (list[dict]): A list of vectors, each with optional 'key', 'data' (with 'float32'), and 'metadata'.
        """
        self.client.upsert(
            collection_name=self.collection_name, 
            points=[
                PointStruct(
                    id=vec.get("key") or str(uuid.uuid4()),
                    vector=np.array(vec["data"]["float32"], dtype=np.float32).tolist(),
                    payload=vec.get("metadata", {})
                ) for vec in vectors
            ]
        )

    def query(self, query_vector: list[float], project_name: str, top_k: int = 10):
        """
        Query the collection for the top_k most similar vectors, optionally filtered by project name.

        Args:
            query_vector (list[float]): The query embedding vector.
            top_k (int): Number of top results to return. Defaults to 10.
            project_name (str): Project name to filter the search.

        Returns:
            list: List of matching points with metadata and scores.
        """
        print("project_name", project_name)
        search_filter = None
        if project_name:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="project_name",
                        match=MatchValue(value=project_name)
                    )
                ]
            )

        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
            query_filter=search_filter
        )

        # results = []
        # for hit in search_result:
        #     results.append({
        #         "key": str(hit.id),
        #         "score": hit.score,
        #         "metadata": hit.payload or {}
        #     })
        # return results
        return search_result

    def delete_collection(self):
        """
        Delete the entire Qdrant collection.
        """
        self.client.delete_collection(collection_name=self.collection_name)
