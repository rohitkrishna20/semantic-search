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
def query_pdf():
    # Get the file and question from the request
    file = request.files.get('file')
    question = request.form.get('question')

    # Check if the file and question were provided
    if not file or not question:
        return jsonify({"ERROR": "Both file and question must be provided"}), 400

    # Save the uploaded file to the server
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    try:
        # Extract text from the PDF file
        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()

        # Limit the text to the first 3000 characters
        limited_text = text[:3000]

        # Generate a keyword from the document
        keyword_prompt = f"From the document, obtain the most important idea:\n\n{limited_text}"
        keyword_response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": keyword_prompt,
            "stream": False
        })

        if keyword_response.status_code != 200:
            return jsonify({"ERROR": "Failed to generate keyword"}), 500
        keyword = keyword_response.json().get("response", "").strip()

        # Generate an answer to the provided question
        question_prompt = f"From the document, answer the question:\n\n{limited_text}\n\nQuestion: {question}"
        answer_response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": question_prompt,
            "stream": False
        })

        if answer_response.status_code != 200:
            return jsonify({"ERROR": "Failed to generate answer"}), 500
        answer = answer_response.json().get("response", "")

        # Return the extracted keyword and the answer
        return jsonify({
            "extracted keyword": keyword,
            "answer": answer
        })

    except Exception as e:
        # Catch any unexpected errors
        return jsonify({"ERROR": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
