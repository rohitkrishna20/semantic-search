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

def generate_prompt(text, question, delimiter):
    return (
        f"DOCUMENT:\n{text}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"INSTRUCTIONS:\n"
        f"- Only respond using the exact words from the DOCUMENT.\n"
        f"- Do not summarize or explain anything.\n"
        f"- If the answer is a list, use '{delimiter}' before each item.\n"
        f"- If the answer doesn't exist in the document, say: No exact match found.\n"
        f"- FORMAT: <score>: <exact answer>\n"
    )

def parse_llm_response(raw):
    try:
        score, answer = raw.split(":", 1)
        return float(score.strip()), answer.strip()
    except:
        return 0.0, "Error from LLM"

@app.route('/', methods=['GET', 'POST'])
def home():
    answer = None
    question = None
    score = None
    best_file = None
    uploaded_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith('.pdf')]

    if request.method == 'POST':
        question = request.form.get('question')
        delimiter = request.form.get("delimiter", "*")
        ranked_results = []

        # Check if question refers to specific file
        filtered_files = uploaded_files
        for f in uploaded_files:
            if f.lower() in question.lower():
                filtered_files = [f]
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
                    json={"model": "llama3.2", "prompt": prompt, "stream": False}
                )

                if response.status_code != 200:
                    continue

                raw = response.json().get("response", "")
                score_val, answer_text = parse_llm_response(raw)

                ranked_results.append({
                    "file": filename,
                    "score": score_val,
                    "answer": answer_text
                })

            except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0.0,
                    "answer": f"Error: {str(e)}"
                })

        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        if ranked_results:
            best_result = ranked_results[0]
            answer = best_result["answer"]
            score = best_result["score"]
            best_file = best_result["file"]

    return render_template('index.html', files=uploaded_files, question=question, score=score, answer=answer, best_file=best_file)

@app.route("/query", methods=["POST"])
def query_api():
    file = request.files.get("file")
    question = request.form.get("question")
    delimiter = request.form.get("delimiter", "*")

    if not file or not file.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400
    if not question:
        return jsonify({"error": "Question is necessary"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    mtime = os.path.getmtime(filepath)
    text = get_cached_text_cached((file.filename, mtime))
    limited_text = text[:3000]
    prompt = generate_prompt(limited_text, question, delimiter)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )

    if response.status_code != 200:
        return jsonify({"error": "LLM failed"}), 500

    raw = response.json().get("response", "")
    score, answer = parse_llm_response(raw)

    return jsonify({
        "question": question,
        "file": file.filename,
        "score": score,
        "answer": answer
    })

if __name__ == '__main__':
    app.run(debug=True)
