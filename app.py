from functools import lru_cache
from flask import Flask, request, jsonify, render_template
import fitz  # PyMuPDF
import os
import requests
import json

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
        f"You are a document reader assistant.\n"
        f"Document content:\n\n{text}\n\n"
        f"Question:\n{question}\n\n"
        f"Instructions:\n"
        f"- ONLY answer using the document content above.\n"
        f"- Do NOT add explanations, do NOT paraphrase, and do NOT say anything that isn't quoted directly from the document.\n"
        f"- If the answer is a list, use '{delimiter}' to start each bullet (e.g., {delimiter} Item1, {delimiter} Item2).\n"
        f"- If the answer does not exist in the document, respond with exactly: No exact match found.\n"
        f"- DO NOT generate anything else.\n"
        f"Return a JSON with 'score' and 'answer'."
    )

def call_llama(prompt):
    body = {
        "model": "llama3:3.2",
        "prompt": prompt,
        "stream": False,
        "functions": [{
            "name": "return_exact_answer",
            "parameters": {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "answer": {"type": "string"}
                }
            }
        }],
        "function_call": "return_exact_answer"
    }

    response = requests.post("http://localhost:11434/api/generate", json=body)
    if response.status_code != 200:
        return 0.0, "Error from LLM"

    try:
        parsed = response.json()
        func_data = parsed.get("message", {}).get("function_call", {}).get("arguments", "{}")
        func_json = json.loads(func_data)
        score = float(func_json.get("score", 0))
        answer = func_json.get("answer", "No answer found.")
    except Exception as e:
        score, answer = 0.0, f"Error parsing LLM response: {e}"

    return score, answer

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
                prompt = generate_prompt(limited_text, question, delimiter)
                score_val, answer_text = call_llama(prompt)
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
    prompt = generate_prompt(limited_text, question, delimiter)
    score, answer = call_llama(prompt)

    return jsonify({
        "question": question,
        "file": file.filename,
        "score": score,
        "answer": answer
    })

if __name__ == '__main__':
    app.run(debug=True)