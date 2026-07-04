from utils import cosine_similarity
from embedder import get_embedding

# def retrieve(query, index, top_k=3):
#     query_emb = get_embedding(query)

#     scored = []
#     for item in index:
#         score = cosine_similarity(query_emb, item["embedding"])
#         scored.append((score, item))

#     scored.sort(reverse=True, key=lambda x: x[0])

#     return [item for _, item in scored[:top_k]]

def retrieve(query, faiss_index, top_k=5):
    return faiss_index.search(query, top_k)