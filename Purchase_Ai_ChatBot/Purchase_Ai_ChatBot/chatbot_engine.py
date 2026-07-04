# import re
# import ollama
# from indexer import load_data, build_index
# from retriever import retrieve

# LLM_MODEL = "llama3.1"

# data = load_data("data.json")
# index = build_index(data)

# def extract_po_id(query):
#     match = re.search(r"PO/\d+/\d+/\d{4}-\d{2}", query)
#     return match.group(0) if match else None


# def chat():
#     print("📊 PO Chatbot Ready\n")

#     while True:
#         query = input("You: ")
#         if query.lower() == "exit":
#             break

#         po_id = extract_po_id(query)

#         # 🔥 HYBRID RETRIEVAL (IMPORTANT FIX)
#         if po_id:
#             context_items = [item for item in index if item["po_id"] == po_id]
#         else:
#             context_items = retrieve(query, index)

#         context = "\n\n---\n\n".join([c["text"] for c in context_items])

#         prompt = f"""
# You are a Purchase Order Invoice verification assistant.

# Use ONLY the context below.

# CONTEXT:
# {context}

# QUESTION:
# {query}

# Rules:
# - If PO is present, explain all its checks clearly
# - If GSTIN mismatch exists, highlight it
# - If not found, say "Not found in records"
# """

#         response = ollama.chat(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "user", "content": prompt}
#             ]
#         )

#         print("\nAI:", response["message"]["content"], "\n")


# if __name__ == "__main__":
#     chat()

# import ollama
# from faiss_indexer import FAISSIndex

# LLM_MODEL = "llama3.1"

# # Build FAISS index
# faiss_index = FAISSIndex()
# data = faiss_index.load_data("data.json")
# faiss_index.build(data)

# def chat():
#     print("\n📊 FAISS PO Invoice Chatbot Ready\n")

#     while True:
#         query = input("You: ")
#         if query.lower() == "exit":
#             break

#         # 🔥 FAISS retrieval
#         results = faiss_index.smart_search(query, top_k=3)

#         context = "\n\n---\n\n".join([r["text"] for r in results])

#         prompt = f"""
# You are a Purchase Order Invoice assistant.

# Use ONLY this context:

# {context}

# Question: {query}

# Rules:
# - Be precise
# - Highlight mismatches clearly
# - If not found, say "Not found in records"
# """

#         response = ollama.chat(
#             model=LLM_MODEL,
#             messages=[
#                 {"role": "user", "content": prompt}
#             ]
#         )

#         print("\nAI:", response["message"]["content"], "\n")


# if __name__ == "__main__":
#     chat()

import ollama

class ChatEngine:
    def __init__(self, faiss_index):
        self.faiss = faiss_index
        self.model = "llama3.1"

    def ask(self, query):

        docs = self.faiss.smart_search(query)

        context = "\n\n".join([d["text"] for d in docs])

        prompt = f"""
You are a PO Invoice assistant.

Use ONLY this context:

{context}

Question: {query}

Rules:
- Be precise
- Highlight mismatches
- If not found, say "Not found in records"
"""

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]