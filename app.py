from flask import Flask, request, jsonify
import fitz
import os
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/query', methods=['POST'])
def query_pdf():
    file = request.files.get('file')
    question = request.form.get('question')

    if not file or not question:
        return jsonify({"ERROR": "There is no file or question"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    text = ""
    with fitz.open(filepath) as doc:
        for page in doc:
            text += page.get_text()

    limited_text = text[:3000]

    # Get important idea
    keyword_prompt = f"From the document, obtain the most important idea:\n\n{limited_text}"
    keyword_response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": keyword_prompt,
        "stream": False
    })
    if keyword_response.status_code != 200:
        return jsonify({"ERROR": "Failed to generate keyword"}), 500
    keyword = keyword_response.json().get("response", "").strip()

    # Answer the question
    question_prompt = f"From the document, answer the question:\n\n{limited_text}\n\nQuestion: {question}"
    answer_response = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3",
        "prompt": question_prompt,
        "stream": False
    })
    if answer_response.status_code != 200:
        return jsonify({"ERROR": "Failed to generate answer"}), 500
    answer = answer_response.json().get("response", "")

    return jsonify({
        "extracted keyword": keyword,
        "answer": answer
    })

if __name__ == '__main__':
    app.run(debug=True)
