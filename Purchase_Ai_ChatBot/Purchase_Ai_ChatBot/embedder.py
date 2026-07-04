# import ollama
# import numpy as np

# EMBED_MODEL = "nomic-embed-text"

# def get_embedding(text: str):
#     response = ollama.embeddings(
#         model=EMBED_MODEL,
#         prompt=text
#     )
#     return np.array(response["embedding"], dtype=np.float32)
import ollama
import numpy as np

EMBED_MODEL = "nomic-embed-text"

def get_embedding(text: str):
    res = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=text
    )
    return np.array(res["embedding"], dtype=np.float32)