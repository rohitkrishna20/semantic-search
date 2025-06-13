from functools import lru_cache
from flask import Flask, request, jsonify, render_template
import fitz
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
        f"You are a helpful assistant strictly answering based only on the document text provided.\n\n"
        f"Document:\n{text}\n\n"
        f"Question: {question}\n\n"
        f"Instructions:\n"
        f"- Only answer using the document content.\n"
        f"- If the answer is a list, prefix each item with '{delimiter}'.\n"
        f"- If no match is found, return exactly: No exact match found.\n"
    )

@app.route('/', methods=['GET', 'POST'])
def home():
    answer = None
    question = None
    best_file = None
    score = None
    uploaded_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]

    if request.method == 'POST':
        question = request.form.get('question')
        delimiter = request.form.get('delimiter', '*')
        ranked_results = []

        for filename in uploaded_files:
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                mtime = os.path.getmtime(filepath)
                text = get_cached_text_cached((filename, mtime))
                limited_text = text[:3000]

                prompt = generate_prompt(limited_text, question, delimiter)
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3.2", "prompt": prompt, "stream": False}
                )

                if response.status_code != 200:
                    ranked_results.append({
                        "file": filename,
                        "score": 0.0,
                        "answer": "Error from LLM"
                    })
                    continue

                answer_raw = response.json().get("response", "").strip()
                score_val = 1.0 if "No exact match found" not in answer_raw else 0.0

                ranked_results.append({
                    "file": filename,
                    "score": score_val,
                    "answer": answer_raw
                })

            except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0.0,
                    "answer": f"Error processing file: {str(e)}"
                })

        ranked_results.sort(key=lambda x: x["score"], reverse=True)

        if ranked_results:
            best = ranked_results[0]
            answer = best["answer"]
            score = best["score"]
            best_file = best["file"]

    return render_template('index.html',
                           files=uploaded_files,
                           question=question,
                           answer=answer,
                           score=score,
                           best_file=best_file)

@app.route('/query', methods=['POST'])
def query_api():
    file = request.files.get('file')
    question = request.form.get('question')
    delimiter = request.form.get('delimiter', '*')

    if not file or not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files allowed"}), 400
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
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )

    if response.status_code != 200:
        return jsonify({"error": "LLM error"}), 500

    answer = response.json().get("response", "").strip()
    score = 1.0 if "No exact match found" not in answer else 0.0

    return jsonify({
        "question": question,
        "file": file.filename,
        "score": score,
        "answer": answer
    })

if __name__ == '__main__':
    app.run(debug=True)