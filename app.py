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
    f"Given the document content below:\n\n{limited_text}\n\n"
    f"The user asks:\n\n{question}\n\n"
    f"Instructions:\n"
    f"- Search only this document. Do not use any outside knowledge.\n"
    f"- Do NOT explain anything. Do NOT include notes, reasoning, or score explanation.\n"
    f"- Only copy the exact matching sentence(s) or bullet list from the document.\n"
    f"- If it is a list of items, extract them directly and present them as '{delimiter} Item1 {delimiter} Item2 {delimiter} Item3'.\n"
    f"- Do not include HTML tags.\n"
    f"- If no answer exists, respond exactly: No exact match found.\n\n"
    f"Format: <score>: <exact answer>"
)

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": prompt, "stream": False}
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
    f"Given the document content below:\n\n{limited_text}\n\n"
    f"The user asks:\n\n{question}\n\n"
    f"Instructions:\n"
    f"- Search only this document. Do not use any outside knowledge.\n"
    f"- Do NOT explain anything. Do NOT include notes, reasoning, or score explanation.\n"
    f"- Only copy the exact matching sentence(s) or bullet list from the document.\n"
    f"- If it is a list of items, extract them directly and present them as '{delimiter} Item1 {delimiter} Item2 {delimiter} Item3'.\n"
    f"- Do not include HTML tags.\n"
    f"- If no answer exists, respond exactly: No exact match found.\n\n"
    f"Format: <score>: <exact answer>"
)

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
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
