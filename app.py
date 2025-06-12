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

@app.route('/', methods=['GET', 'POST'])
def home():
    answer = None
    question = None
    score = None
    best_file = None
    uploaded_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.pdf')]

    if request.method == 'POST':
        question = request.form.get('question')
        delimiter = request.form.get('delimiter', '*')
        ranked_results = []

        filtered_files = uploaded_files
        for file in uploaded_files:
            if file.lower() in question.lower():
                filtered_files = [file]
                break

        for filename in filtered_files:
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                mtime = os.path.getmtime(filepath)
                text = get_cached_text_cached((filename, mtime))
                limited_text = text[:3000]

                prompt = (
                    f"You are an intelligent PDF document assistant.\n\n"
                    f"ONLY use the content provided below to answer the question. DO NOT guess or explain anything.\n\n"
                    f"--- DOCUMENT START ---\n{limited_text}\n--- DOCUMENT END ---\n\n"
                    f"User Question:\n{question}\n\n"
                    f"Output Format:\n"
                    f"<score>: <verbatim answer from document>\n\n"
                    f"Rules:\n"
                    f"- Use exact sentences or phrases from the document ONLY.\n"
                    f"- If it's a list, start each item with '{delimiter}' like this: {delimiter} Item1, {delimiter} Item2\n"
                    f"- If no answer is found, respond exactly with: No exact match found."
                )

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3:3.2", "prompt": prompt, "stream": False}
                )

                if response.status_code != 200:
                    continue

                raw = response.json().get("response", "")
                parts = raw.split(":", 1)
                try:
                    score_val = float(parts[0].strip())
                except:
                    score_val = 0.0
                answer_text = parts[1].strip() if len(parts) > 1 else "No answer given."
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
            best_result = ranked_results[0]
            answer = best_result["answer"]
            score = best_result["score"]
            best_file = best_result["file"]
        else:
            answer = "No relevant result found."
            score = 0.0

    return render_template('index.html', files=uploaded_files, question=question, score=score, answer=answer, best_file=best_file)

@app.route('/query', methods=['POST'])
def query_api():
    file = request.files.get('file')
    question = request.form.get('question')
    delimiter = request.form.get('delimiter', '*')

    if not file or not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files are supported"}), 400
    if not question:
        return jsonify({"error": "Question is necessary"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    mtime = os.path.getmtime(filepath)
    text = get_cached_text_cached((file.filename, mtime))
    limited_text = text[:3000]

    prompt = (
        f"You are an intelligent PDF document assistant.\n\n"
        f"ONLY use the content provided below to answer the question. DO NOT guess or explain anything.\n\n"
        f"--- DOCUMENT START ---\n{limited_text}\n--- DOCUMENT END ---\n\n"
        f"User Question:\n{question}\n\n"
        f"Output Format:\n"
        f"<score>: <verbatim answer from document>\n\n"
        f"Rules:\n"
        f"- Use exact sentences or phrases from the document ONLY.\n"
        f"- If it's a list, start each item with '{delimiter}' like this: {delimiter} Item1, {delimiter} Item2\n"
        f"- If no answer is found, respond exactly with: No exact match found."
    )

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3:3.2", "prompt": prompt, "stream": False}
    )

    if response.status_code != 200:
        return jsonify({"error": "LLM failed"}), 500

    raw = response.json().get("response", "")
    parts = raw.split(":", 1)
    try:
        score = float(parts[0].strip())
    except:
        score = 0.0

    answer = parts[1].strip() if len(parts) > 1 else "No answer generated"

    return jsonify({
        "question": question,
        "file": file.filename,
        "score": score,
        "answer": answer
    })

if __name__ == '__main__':
    app.run(debug=True)