# semantic-search Flask Use

## Summary
This app allows the user to upload a pdf and ask a question about the contents within that file. Postman will extract that text and return a response using semantic search.

## Requirements
- Python 3.x
- Flask
- PyMuPDF (fitz)

## Setup in Terminal and Postman
1. Clone the repository:
   - 'git clone https://github.com/YOUR_USERNAME/semantic-search.git'
   - 'cd semantic-search'
2. Install dependencies:
   - 'pip install -r requirements.txt'
3. Run the app:
   - 'python app.py' -- the server will start on http://127.0.0.1:5000
   - Use Postman to send a POST request to: http://127.0.0.1:5000/query
   - Set the **body** to 'form-data' and include:
     - **key** 'file' (Type: File) - upload your pdf
     - **key** 'question' (Type: Text) - enter your question.
4. Send the Request:
   - Click the send button on Postman 
