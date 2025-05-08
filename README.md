# semantic-search Flask Use

## Summary
This app allows the user to upload a pdf and ask a question about the contents within that file. Postman will extract that text and return a response using semantic search.

## Requirements 
_Install dependencies section will take care of these_
- Python 3.x
- Flask
- PyMuPDF (fitz)

## Running LLaMA 3 from OLLAMA
The app uses ollama (LLaMA) 3 to process content on pdf and answer questions that the user gives. To set it up:
1. ** Install ollama: **
   - visit https://ollama.com and download ollama for the user specific interface (Mac, Windows, etc)
2. ** Extract the LLaMA 3 model: **
   - open terminal and run:
     ```ollama pull llama3```
3. ** Start the Ollama server: **
   - run: ```ollama serve``` or ```ollama run llama3```
     - this will start the the API server at 'http://localhost:11434'.

- Make sure the ollama server is running before starting the flask app.
- the flask app send requests to the Ollama API at 'http://localhost:11434/api/generate'.
  

## Setup in Terminal and Postman
- OPEN A NEW TERMINAL DIFFERENT FROM THE OLLAMA TERMINAL
1. Clone the repository:
   - ```git clone https://github.com/YOUR_USERNAME/semantic-search.git```
   - ```cd semantic-search```
2. Install dependencies:
   - ```pip install -r requirements.txt```
3. Run the app:
   - ```python app.py``` -- the server will start on http://127.0.0.1:5000
   - Use Postman to send a POST request to: http://127.0.0.1:5000/query
   - Set the **body** to ```form-data``` and include:
     - **key** ```file``` (```Type: File```) - upload your pdf
       - Upload a pdf ```file``` is optional
       - if upload a ```file```, the search will run only on that specific file
       - without uploading a file, the app will search across all the pdf files within the ```uploads/``` folder
       - if no pdf files are available and no file is then uploaded, an error will be shown.
     - **key** ```question``` (Type: Text) - enter your question.
4. Send the Request:
   - Click the send button on Postman 
5. To run in production mode
   - ```pip install gunicorn``` to install a production-ready WSGI server like Gunicorn
   - ```/Users/dyadmin/Library/Python/3.9/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 app:app``` to start the app
