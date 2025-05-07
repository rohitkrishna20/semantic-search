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

    if file and file.filename == '':
        file = None

    if not question:
        return jsonify({"Error": "Question must be given"}), 400

    results = []

    # Case 1
    if file and file.filename:
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        files_to_search = [filepath]
    else:
        # Case 2
        files_to_search = [
            os.path.join(UPLOAD_FOLDER, f)
            for f in os.listdir(UPLOAD_FOLDER)
            if f.endswith('.pdf')
        ]
        if not files_to_search:
            return jsonify({"Error": "There are no PDFs in the uploads folder."}), 400

    ranked_results = []

    for path in files_to_search:
        filename = os.path.basename(path)
        try:
            text = ""
            with fitz.open(path) as doc:
                for page in doc:
                    text += page.get_text()
            limited_text = text[:3000]
            relevance_prompt = (
                    f"Given the document content: \n\n{limited_text}\n\n"
                    f"the user question: \n\n{question}\n\n"
                    "Rate how relevant this document is to the question given on a scale of 0 to 10, "
                    "then answer the question based on this document.\n"
                    "Format: <score>: <answer>"
                )
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": relevance_prompt, "stream": False}
            )
            if response.status_code != 200:
                raise Exception("LLM Error")
            raw = response.json().get("response", "")
            parts = raw.split(":", 1)
            try:
                score = float(parts[0].strip())
            except:
                score = 0.0
            answer = parts[1].strip() if len(parts) > 1 else "No answer is given."
            ranked_results.append({
                "file": filename,
                "score": score,
                "answer": answer
            })
        except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0,
                    "explanation": f" There was an error processing the file: {str(e)}"
                })

    ranked_results.sort(key=lambda x: x["score"], reverse=True)

    return jsonify({
    "question": question,
    "ranked_results": ranked_results
    })


if __name__ == '__main__':
    app.run(debug=True)
