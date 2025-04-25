from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

OLLAMA_MODEL = "llama3"
OLLAMA_URL = "http://localhost:11434/api/generate"

@app.route('/query', methods=['POST'])
def query_ollama():
    data = request.json
    keyword = data.get("keyword", "")
    prompt = f"Tell me information about {keyword}"
    
    ollama_payload = { 
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    ollama_response = requests.post(OLLAMA_URL, json=ollama_payload)
    result = ollama_response.json()

    print("OLLAMA response:", result)
    
    return jsonify({
        "keyword": keyword,
        "response": result.get("response", "no result")
    })


if __name__ == '__main__':
    app.run(debug=True)
