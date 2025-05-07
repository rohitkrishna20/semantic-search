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
    
        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get.text()
    
        limited_text = text[:3000]
    
        # Keyboard Prompt
        keyword_prompt = f"From the document, extract the main idea of the most important keyword: \n\n{limited_text}"
        keyword_response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": keyword_prompt, "stream": False}
        )
        keyword = keyword_response.json().get("response", "").strip() if keyword_response.status_code == 200 else "None"
    
        # Answer prompt
        question_prompt = f"Answer the questions based on the pdf provided:\n\n{limited_text}\n\nQuestion: {question}"
        answer_response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": question_prompt, "stream": False}
        )
        answer = answer_response.json().get("response", "").strip() if answer_response.status_code == 200 else "None"

        return jsonify({
            "file": file.filename,
            "keyword": keyword,
            "answer": answer
        })

    # Case 2
    else:
        ranked_results = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if not filename.endswith(".pdf"):
                continue
            filepath = os.path.join(UPLOAD_FOLDER, filename) 
            try:
                text = ""
                with fitz.open(filepath) as doc:
                    for page in doc:
                        text += page.get.text()
                limited_text = text[:3000]
                relevance_prompt = (
                    f"Given the document content: \n\n{limited_text}\n\n"
                    f"the user question: \n\n{question}\n\n"
                    "Rate how relevant this document is to the question given on a scale of 0 to 10, "
                    "then explain why. Format: <score>: <reason>"
                )
                response = reuqests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": relevance_prompt, "stream":False}
                )
                if response.status_code != 200:
                    continue
                raw = response.json().get("response", "")
                score_str = raw.split(":", 1)[0]
                try:
                    score = float(score_str.strip())
                except:
                    score = 0.0
                ranked_results.append({
                    "file": filename,
                    "score": score,
                    "explanation": raw.strip()
                })
            except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0,
                    "explanation": f" There was an error processing the file: {e}"
                })
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        return jsonify({
            "question": question,
            "ranked_results": ranked_results
        })
    

if __name__ == '__main__':
    app.run(debug=True)
