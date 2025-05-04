from flask import Flask, request, jsonify
import fitz
import os
import requests

# Initialize the Flask app
app = Flask(__name__)

# Set the folder for uploading files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/query', methods=['POST'])
def query():
    file = request.files.get('file')
    question = request.form.get('question')

    if not question:
        return jsonify({"Error": "Question must be given"}), 400

    files_to_search = []

    if file:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        files_to_search.append(filepath)
    else:
        for filename in os.listir(UPLOAD_FOLDER):
            if filename.endswith('.pdf'):
                files_to_search.append(os.path.join(UPLOAD_FOLDER, filename))

    if not files_to_search:
        return jsonify({"ERROR": "There are no pdf files identified."}), 400

    results = []

    for pdf_file in files_to_search:
        text = ""
        with fitz.open(pdf_file) as doc:
            for page in doc:
                text += page.get_text()

        limited_text = text[:3000]

        keyword_prompt = f"From the pdf, obtain the main idea:\n\n{limited_text}"
        keyword_response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": keyword_prompt,
            "stream": False
        })
                    
        if keyword_response.status_code != 200:
            return jsonify({"ERROR": "Failed to generate any keywords"}), 500
        keyword = keyword_response.json().get("response", "").strip()

        question_prompt = f"From the document, answer the question:\n\n{limited_text}\n\nQuestion: {question}"
        answer_response = requests.post("http://localhost:11434/api/generate", json = {
            "model": "llama3",
            "prompt": question_prompt,
            "stream": False
        })
        if answer_response.status_code != 200:
            return jsonify({"Error": "Failed to create a response or answer"}), 500
        answer = answer_response.json().get("response", "").strip()

        results.append({
            "file": os.path.basename(pdf_file),
            "keyword": keyword,
            "answer": answer
        })
            
        

        results.append({
            "file": os.path.basename(pdf_file),
            "text_excerpt": text[:500]
        })
    return jsonify({
        "question": question,
        "results": results
    })

if __name__ == '__main__':
    app.run(debug=True)
