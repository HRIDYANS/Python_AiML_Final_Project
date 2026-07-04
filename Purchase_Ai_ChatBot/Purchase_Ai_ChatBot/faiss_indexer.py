# import json
# import faiss
# import numpy as np
# from embedder import get_embedding

# class FAISSIndex:
#     def __init__(self):
#         self.dim = 768  # nomic-embed-text dimension
#         self.index = faiss.IndexFlatL2(self.dim)
#         self.metadata = []
#         self.po_map = {}   # ✅ FIXED (correct place)

#     def load_data(self, path="data.json"):
#         with open(path, "r", encoding="utf-8") as f:
#             return json.load(f)

#     def build(self, data):
#         print("🔄 Building FAISS index...")

#         for record in data["records"]:
#             po_id = record["purchase_order_id"]

#             checks_text = "\n".join([
#                 f"{c['field']} | PO: {c['po_details']} | INV: {c['invoice_details']} | STATUS: {c['status']}"
#                 for c in record["checks"]
#             ])

#             text = f"PO ID: {po_id}\n{checks_text}"

#             emb = get_embedding(text)
#             emb = np.array([emb]).astype("float32")

#             self.index.add(emb)

#             self.metadata.append({
#                 "po_id": po_id,
#                 "text": text
#             })

#             # ✅ FAST LOOKUP MAP
#             self.po_map[po_id] = text

#         print(f"✅ FAISS index ready with {len(self.metadata)} items")

#     def search(self, query, top_k=5):
#         query_emb = get_embedding(query).astype("float32")
#         query_emb = np.array([query_emb])

#         distances, indices = self.index.search(query_emb, top_k)

#         results = []
#         for idx in indices[0]:
#             if idx < len(self.metadata):
#                 results.append(self.metadata[idx])

#         return results

#     # 🔥 FIXED: now inside class
#     def smart_search(self, query, top_k=3):

#         # CASE 1: EXACT PO MATCH
#         if "PO/" in query:
#             for po_id in self.po_map:
#                 if po_id in query:
#                     return [{
#                         "po_id": po_id,
#                         "text": self.po_map[po_id]
#                     }]

#         # CASE 2: FAISS SEARCH
#         return self.search(query, top_k)

import json
import faiss
import numpy as np
from embedder import get_embedding

class FAISSIndex:
    def __init__(self):
        self.dim = 768
        self.index = faiss.IndexFlatL2(self.dim)
        self.metadata = []
        self.po_map = {}

    def build(self, data):
        for record in data["records"]:
            po_id = record["purchase_order_id"]

            text = f"""
PO ID: {po_id}
""" + "\n".join([
                f"{c['field']} | PO: {c['po_details']} | INV: {c['invoice_details']} | STATUS: {c['status']}"
                for c in record["checks"]
            ])

            emb = np.array([get_embedding(text)]).astype("float32")

            self.index.add(emb)

            self.metadata.append({
                "po_id": po_id,
                "text": text
            })

            self.po_map[po_id] = text

    def smart_search(self, query, top_k=3):

        # EXACT MATCH
        import re
        match = re.search(r"PO/\d+/\d+/\d{4}-\d{2}", query)

        if match:
            po_id = match.group(0)
            return [{
                "po_id": po_id,
                "text": self.po_map.get(po_id, "Not found")
            }]

        # FAISS SEARCH
        q_emb = np.array([get_embedding(query)]).astype("float32")
        distances, indices = self.index.search(q_emb, top_k)

        results = []
        for i in indices[0]:
            if i < len(self.metadata):
                results.append(self.metadata[i])

        return results