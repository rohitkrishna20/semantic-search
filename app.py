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
        for filename in os.listedir(UPLOAD_FOLDER):
            if filename.ednswith('.pdf'):
                files_to_search.append(os.path.join(UPLOAD_FOLDER, filename))

    if not files_to_search:
        return jsonify({"ERROR": "There are no pdf files identified."}), 400

    results = []

    for pdf_file in files_to_search:
        text = ""
        with fitz.open(pdf_file) as doc:
            for page in doc:
                text += page.get_text()

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
