from flask import Flask, render_template, request, jsonify
from chatbot_engine import ChatEngine
import json

from faiss_indexer import FAISSIndex

app = Flask(__name__)

# -------------------------
# INIT RAG SYSTEM
# -------------------------
faiss_index = FAISSIndex()

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

faiss_index.build(data)

chat_engine = ChatEngine(faiss_index)

# -------------------------
# ROUTES
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json["message"]

    reply = chat_engine.ask(user_msg)

    return jsonify({"response": reply})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)