# College Storage
### By Om

A clean and responsive college file storage app built with Flask, SQLite, HTML, CSS, and JavaScript.

## Features

- Upload PDF, DOCX, PPT, PPTX, and image files
- Organize files by semester, subject, and category
- Search by file name
- Download and delete files
- Responsive dashboard with cards and metadata

## Project Structure

```text
college-storage/
├─ app.py
├─ college_storage.db
├─ requirements.txt
├─ uploads/
├─ static/
│  ├─ css/
│  │  └─ style.css
│  └─ js/
│     └─ main.js
└─ templates/
   ├─ base.html
   └─ index.html
```

The SQLite database file and the uploads folder are created automatically when the app starts.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python app.py
```

4. Open `http://127.0.0.1:5000` in your browser.

## Notes

- Uploaded files are stored in the `uploads/` folder.
- The database is created automatically with a `files` table on startup.
- You can safely delete the database file to reset the app.