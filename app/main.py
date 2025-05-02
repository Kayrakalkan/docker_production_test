from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)

# es = Elasticsearch("http://elasticsearch:9200", basic_auth=("elastic", "admin123"))
es = Elasticsearch("http://elasticsearch:9200")

@app.route('/')
def hello_world():
    return "Hello, World!"

@app.route("/add", methods=["POST"])
def add_document():
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data sent"}), 400

    if isinstance(data, dict):
        data = [data]

    indexed_ids = []
    for doc in data:
        if "id" not in doc or "index_name" not in doc:
            return jsonify({"error": "Each document must have 'id' and 'index_name' fields"}), 400

        index_name = doc["index_name"]

        # Check if index exists, create if not
        if not es.indices.exists(index=index_name):
            try:
                es.indices.create(index=index_name)
            except Exception as e:
                return jsonify({"error": f"Error creating index '{index_name}': {str(e)}"}), 500

        try:
            es_response = es.index(index=index_name, id=doc["id"], document=doc)
            indexed_ids.append({"id": doc["id"], "index_name": index_name})
        except Exception as e:
            return jsonify({"error": f"Error indexing document with ID {doc.get('id', 'unknown')} in index '{index_name}': {str(e)}"}), 500

    return jsonify({"message": "Documents indexed successfully", "indexed": indexed_ids}), 201

@app.route("/search", methods=["GET"])
def search_documents():
    query = request.args.get("q", "")
    index_name = request.args.get("index")
    if not index_name:
        return jsonify({"error": "Missing 'index' query parameter"}), 400

    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["title", "content"]
            }
        }
    }

    try:
        results = es.search(index=index_name, body=search_body)
        return jsonify(results["hits"]["hits"])
    except Exception as e:
        return jsonify({"error": f"Error searching index '{index_name}': {str(e)}"}), 500

@app.route("/all", methods=["GET"])
def get_all_documents():
    index_name = request.args.get("index")
    if not index_name:
        return jsonify({"error": "Missing 'index' query parameter"}), 400

    try:
        results = es.search(
            index=index_name,
            body={"query": {"match_all": {}}},
            size=10000  # adjust as needed; ES default is 10
        )
        docs = [hit["_source"] for hit in results["hits"]["hits"]]
        return jsonify(docs)
    except Exception as e:
        return jsonify({"error": f"Error fetching documents: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
