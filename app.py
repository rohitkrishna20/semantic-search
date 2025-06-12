from functools import lru_cache
from flask import Flask, request, jsonify, render_template
import fitz  # PyMuPDF
import os
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@lru_cache(maxsize=10)
def get_cached_text_cached(filename_with_mtime):
    filename, mtime = filename_with_mtime
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with fitz.open(filepath) as doc:
        return "".join(page.get_text() for page in doc)

def generate_prompt(text, question, delimiter="*"):
    return (
        f"You are a document assistant.\n\n"
        f"Document:\n{text}\n\n"
        f"User Question:\n{question}\n\n"
        f"Instructions:\n"
        f"- Only return information copied directly from the document.\n"
        f"- Do not paraphrase, summarize, or add notes.\n"
        f"- If a list is needed, use '{delimiter}' as the bullet.\n"
        f"- If the answer is not in the document, say: 'No exact match found.'"
    )

def parse_llm_response(response):
    try:
        raw = response.json().get("response", "").strip()
        if not raw:
            return 0.0, "Error from LLM"

        data = eval(raw) if raw.startswith("{") else None
        if data and isinstance(data, dict):
            return float(data.get("score", 0.0)), data.get("answer", "No answer given.")
        return 0.0, raw
    except Exception:
        return 0.0, "Error parsing LLM response"

@app.route("/", methods=["GET", "POST"])
def home():
    answer = None
    score = None
    question = None
    best_file = None
    uploaded_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]

    if request.method == "POST":
        question = request.form.get("question")
        delimiter = request.form.get("delimiter", "*")
        ranked_results = []

        filtered_files = uploaded_files
        for file in uploaded_files:
            if file.lower() in question.lower():
                filtered_files = [file]
                break

        for filename in filtered_files:
            try:
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                mtime = os.path.getmtime(filepath)
                text = get_cached_text_cached((filename, mtime))
                limited_text = text[:3000]

                prompt = generate_prompt(limited_text, question, delimiter)

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3:3.2",
                        "prompt": prompt,
                        "format": "json",
                        "stream": False,
                        "functions": [
                            {
                                "name": "document_answer",
                                "description": "Return the exact answer with a confidence score",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "score": {"type": "number"},
                                        "answer": {"type": "string"}
                                    },
                                    "required": ["score", "answer"]
                                }
                            }
                        ]
                    }
                )

                if response.status_code != 200:
                    continue

                score_val, answer_text = parse_llm_response(response)
                ranked_results.append({
                    "file": filename,
                    "score": score_val,
                    "answer": answer_text
                })

            except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0,
                    "answer": f"Error processing {filename}: {str(e)}"
                })

        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        if ranked_results:
            best = ranked_results[0]
            answer = best["answer"]
            score = best["score"]
            best_file = best["file"]
        else:
            answer = "No relevant result found."
            score = 0.0

    return render_template("index.html", files=uploaded_files, question=question, score=score, answer=answer, best_file=best_file)

@app.route("/query", methods=["POST"])
def query_api():
    file = request.files.get("file")
    question = request.form.get("question")
    delimiter = request.form.get("delimiter", "*")

    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400
    if not question:
        return jsonify({"error": "Question is required"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    mtime = os.path.getmtime(filepath)
    text = get_cached_text_cached((file.filename, mtime))
    limited_text = text[:3000]

    prompt = generate_prompt(limited_text, question, delimiter)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3:3.2",
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "functions": [
                {
                    "name": "document_answer",
                    "description": "Return the exact answer with a confidence score",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "score": {"type": "number"},
                            "answer": {"type": "string"}
                        },
                        "required": ["score", "answer"]
                    }
                }
            ]
        }
    )

    if response.status_code != 200:
        return jsonify({"error": "LLM failed"}), 500

    score, answer = parse_llm_response(response)

    return jsonify({
        "question": question,
        "file": file.filename,
        "score": score,
        "answer": answer
    })

if __name__ == "__main__":
    app.run(debug=True)