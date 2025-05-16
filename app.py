from flask import Flask, request, render_template
import fitz
import os
import requests

# Initialize the Flask app
app = Flask(__name__)

# Set the folder for uploading files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def home():
    answer = None
    question = None
    if request.method == 'POST':
        question = request.form.get('question')
        ranked_results = []
        for filename in os.listdir(UPLOAD_FOLDER):
            if not filename.endswith('.pdf'):
                continue
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            try:
                text = ""
                with fitz.open(filepath) as doc:
                    for page in doc:
                        text += page.get_text()
                limited_text = text[:3000]
                prompt = (
                f"Given the document information:\n\n{limited_text}\n\n"
                f"the user question:\n\n{question}\n\n"
                "Rate how relevant this document is to the question on a scale of 0 to 10, "
                "then answer the question based on this document. \n"
                "Format: <score>: <answer>"
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
                    score = float(parts[0].strip())
                except:
                    score = 0.0
                answer_text = parts[1].strip() if len(parts) > 1 else "No answer given."
                ranked_results.append({
                    "file": filename,
                    "score": score,
                    "answer": answer_text
                })
            except Exception as e:
                ranked_results.append({
                    "file": filename,
                    "score": 0,
                    "answer": f" Error processing {filename}: {str(e)}"
                })
        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        best_result = ranked_results[0] if ranked_results else {"answer": "No relevant result found.", "score": 0.0}
        answer = best_result["answer"]
        score = best_result["score"]
    return render_template('index.html', question = question, score= score, answer=answer)

if __name__ == '__main__':
    app.run(debug=True)
                
