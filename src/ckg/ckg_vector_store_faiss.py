import faiss
import numpy as np
import uuid
import pickle

class LocalFAISSVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.metadata_store = {}

    def add(self, vectors: list[dict]):
        all_vecs = []
        ids = []

        for vec in vectors:
            key = vec["key"] or str(uuid.uuid4())
            emb = np.array(vec["data"]["float32"], dtype=np.float32)
            all_vecs.append(emb)
            ids.append(key)
            self.metadata_store[key] = vec["metadata"]

        self.index.add(np.stack(all_vecs))
        self.keys = ids  # maintain order

    def query(self, vector: list[float], top_k: int = 10):
        query_vec = np.array(vector, dtype=np.float32).reshape(1, -1)
        D, I = self.index.search(query_vec, top_k)

        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx >= 0 and idx < len(self.keys):
                key = self.keys[idx]
                metadata = self.metadata_store.get(key, {})
                results.append({
                    "key": key,
                    "score": float(dist),
                    "metadata": metadata
                })
        return results

    def save(self, path: str):
        faiss.write_index(self.index, f"{path}.index")
        with open(f"{path}.meta.pkl", "wb") as f:
            pickle.dump((self.keys, self.metadata_store), f)

    def load(self, path: str):
        self.index = faiss.read_index(f"{path}.index")
        with open(f"{path}.meta.pkl", "rb") as f:
            self.keys, self.metadata_store = pickle.load(f)
