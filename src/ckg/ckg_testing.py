import os
import boto3
import json
from dotenv import load_dotenv
from ckg_vector_store_qdrant import QdrantVectorStore
from strands import tool

load_dotenv()

# AWS Setup
VECTOR_BUCKET = "nemo-ai-vector-bucket"
VECTOR_INDEX = "nemo-ai-vector-index"
EMBEDDING_MODEL_ID = "amazon.titan-embed-text-v2:0"

store = QdrantVectorStore(collection_name=VECTOR_INDEX, dim=1024)

# AWS Session
session_bedrock = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="us-east-1"
)
# session = boto3.Session(profile_name="personal-dev")
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID_PERSONAL_DEV"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY_PERSONAL_DEV"),
    region_name="us-east-1"
)

bedrock_runtime = session_bedrock.client("bedrock-runtime")
# s3vectors = session.client("s3vectors")  # vector engine for s3

def embed_query_text(text: str) -> list[float]:
    response = bedrock_runtime.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": text})
    )
    result = json.loads(response["body"].read())
    return result["embedding"]

@tool
def query_vector_store(query_text: str, project_name: str, top_k: int = 5) -> list[dict]:
    """
    Perform a semantic search over the codebase to locate functions, classes, or other implementation details 
    using a natural language query. 

    This tool embeds the query text and searches the Qdrant vector store with cosine similarity, returning 
    the most relevant code snippets or documentation fragments. It is particularly useful for open-ended 
    questions such as:
    - "Where is user authentication handled?"
    - "Where are we logging analytics events?"
    - "Which functions deal with caching?"

    Args:
        query_text (str): A natural language description of what to find in the codebase.
            Examples: "authentication function", "analytics logger", "payment validation class"
        project_name (str): Project name to filter the search.
        top_k (int, optional): Maximum number of results to return. Defaults to 5.
            Use smaller values when you expect a single precise match.

    Returns:
        list[dict]: A ranked list of relevant code elements, each containing:
            - id (str): Unique identifier of the code element.
            - score (float): Similarity score (higher = more relevant).
            - payload (dict):
                - file_path (str): File path of the code element.
                - name (str): Function or class name.
                - type (str): Type of element ("function", "class", "async_function").
                - start_line (int): Start line of the code.
                - end_line (int): End line of the code.
                - parent_class (str | None): Parent class name if applicable.
                - parent_function (str | None): Parent function name if applicable.
                - docstring (str | None): Original docstring if present.
                - llm_summary (str | None): LLM-generated summary of the code.
                - decorators (str | None): Any decorators applied.

    Notes:
        - This tool performs semantic search, so results may include partial or indirect matches.
        - Useful when the exact function/class name is unknown.
        - Best suited for exploratory queries or natural-language style questions.
    """

    print("query_text", query_text)
    vector = embed_query_text(query_text)

    results = store.query(vector, project_name=project_name, top_k=top_k)
    flattened_result = [ {"id": r.id, "score": r.score, **r.payload} for r in results]
    print("flattened_result", flattened_result)
    return flattened_result

    # print(f"==>> results: {results}")
    
    # for idx, item in enumerate(results):
    #     print(f"\n🔹 Result {idx + 1}")
    #     print(f"Key: {item['key']}")
    #     print(f"Score: {item['score']:.4f}")
    #     print("Metadata:")
    #     for k, v in item["metadata"].items():
    #         print(f"  {k}: {v}")

    # response = s3vectors.query_vectors(
    #     vectorBucketName=VECTOR_BUCKET,
    #     indexName=VECTOR_INDEX,
    #     queryVector={"float32": vector},
    #     topK=top_k,
    #     returnDistance=True,
    #     returnMetadata=True
    # )

    # results = response.get("results", [])
    # print(f"==>> results: {results}")
    # for idx, item in enumerate(results):
    #     print(f"\n🔹 Result {idx + 1}")
    #     print(f"Key: {item['key']}")
    #     print(f"Score: {item['score']:.4f}")
    #     print("Metadata:")
    #     for k, v in item["metadata"].items():
    #         print(f"  {k}: {v}")

    # # return results
    # response = s3vectors.list_vectors(
    #     vectorBucketName=VECTOR_BUCKET,
    #     indexName=VECTOR_INDEX,
    #     returnMetadata=True
    # )
    # # print(f"==>> response: {response}")
    # # print(f"==>> response['vectors']: {response['vectors']}")
    # print(f"Total vectors: {len(response.get('vectors', []))}")

# Example Usage
if __name__ == "__main__":
    query = "where are we saving the statistics for the user?"
    query_vector_store(query)

# from ckg_vector_store_faiss import LocalFAISSVectorStore
# import json
# import numpy as np

# store = LocalFAISSVectorStore(dim=1024)
# store.load("faiss_local_store")

# def embed_query_text(text: str) -> list[float]:
#     response = bedrock_runtime.invoke_model(
#         modelId=EMBEDDING_MODEL_ID,
#         body=json.dumps({"inputText": text})
#     )
#     result = json.loads(response["body"].read())
#     return result["embedding"]

# def query_vector_store(query_text: str, top_k: int = 10):
#     vector = embed_query_text(query_text)
#     results = store.query(vector, top_k=top_k)

#     print(f"==>> {len(results)} results")
#     for idx, item in enumerate(results):
#         print(f"\n🔹 Result {idx + 1}")
#         print(f"Key: {item['key']}")
#         print(f"Score: {item['score']:.4f}")
#         print("Metadata:")
#         for k, v in item["metadata"].items():
#             print(f"  {k}: {v}")

# Example Usage
# if __name__ == "__main__":
#     query = "where we fetching the analytics data from the database"
#     query_vector_store(query)
