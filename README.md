#Password Strength Analyzer and Wordlist Generator

#Project Overview:
This project implements a web-based Password Strength Analyzer and Custom Wordlist Generator.
It allows users to evaluate the strength of a password and generate customized password wordlists based on user-provided seed inputs.
The project was developed as part of an internship to demonstrate practical understanding of password security concepts, frontend–backend integration, and secure handling of user inputs.

#Key Features
•	Password strength analysis based on multiple parameters
•	Custom wordlist generation using user-defined seed words
•	Web-based user interface
•	Backend processing using Python and Flask
•	No storage or persistence of user passwords

#Technology Stack
Frontend
•	HTML5
•	CSS3
•	JavaScript
Backend
•	Python
•	Flask
Libraries / Dependencies
•	zxcvbn – Password strength estimation
•	nltk – Linguistic analysis support
•	Flask – Backend routing and request handling

#Project Structure
version2/
│
├── app.py                 # Flask application entry point
├── analyzer.py            # Password analysis logic
├── generator.py           # Wordlist generation logic
├── requirements.txt       # Project dependencies
│
├── static/
│   ├── styles.css         # UI styling
│   └── script.js          # Frontend logic
│   └── index.html         # Web interface
│
└── .venv/                 # Python virtual environment

#How the Application Works
Password Strength Analysis
1.	The user enters a password through the web interface.
2.	The password is sent to the backend for analysis.
3.	The backend evaluates:
o	Password length
o	Character diversity
o	Strength score using implemented logic and libraries
4.	The analysis result is returned and displayed on the UI.
Wordlist Generation
1.	The user provides seed words.
2.	The backend generates password variations based on the seeds.
3.	Duplicate entries are avoided.
4.	The generated wordlist is written to an output file.

#Security and Privacy
•	Passwords are processed only in memory.
•	No passwords are stored on the client side.
•	No passwords are stored on the server side.
•	No password data is written to files, logs, or databases.
•	All processing occurs locally for educational purposes.
Passwords submitted for analysis are neither persisted nor logged and exist only for the duration of the request.

#Installation and Setup
1. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate
2. Install dependencies
pip install -r requirements.txt
3. Run the web application
python app.py
Access the application at:
http://127.0.0.1:5000/

#Privacy Disclaimer
This application does not store, log, or transmit user passwords. All password analysis is performed temporarily in memory and discarded immediately after processing.

#Notes
•	This project is intended strictly for educational and internship demonstration purposes.
•	No production authentication or password storage system is implemented.
•	The application does not connect to external services.

