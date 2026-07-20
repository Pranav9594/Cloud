import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE_PATH = os.path.join(BASE_DIR, "college_storage.db")
ALLOWED_EXTENSIONS = {"pdf", "docx", "ppt", "pptx", "png", "jpg", "jpeg", "gif", "webp"}
SUBJECT_OPTIONS = ["PYTHON", "DOT NET", "ED", "R PROG", "HR", "IT APTI"]
LAB_OPTIONS = ["LAB ON PYTHON", "LAB ON DOT NET"]
CATEGORY_OPTIONS = ["Syllabus", "Notes", "Previous Papers", "Assignments"]
LAB_CATEGORY_OPTIONS = ["Syllabus", "Code", "Output"]


app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024
app.secret_key = "college-storage-secret-key"


def get_db_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    # Create the uploads folder and database table the first time the app starts.
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                file_size INTEGER NOT NULL,
                upload_date TEXT NOT NULL,
                semester TEXT NOT NULL,
                subject TEXT NOT NULL,
                category TEXT NOT NULL,
                file_extension TEXT NOT NULL
            )
            """
        )
        connection.commit()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def fetch_files(search_term=None):
    query = "SELECT * FROM files"
    params = []

    if search_term:
        query += " WHERE original_name LIKE ?"
        params.append(f"%{search_term}%")

    query += " ORDER BY datetime(upload_date) DESC, id DESC"

    with get_db_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    files = []
    for row in rows:
        # Add display-friendly values for the dashboard cards.
        file_data = dict(row)
        file_data["pretty_size"] = format_size(file_data["file_size"])
        file_data["display_date"] = datetime.fromisoformat(file_data["upload_date"]).strftime("%d %b %Y, %I:%M %p")
        file_data["icon"] = {
            "pdf": "📄",
            "docx": "📝",
            "ppt": "📊",
            "pptx": "📊",
            "png": "🖼️",
            "jpg": "🖼️",
            "jpeg": "🖼️",
            "gif": "🖼️",
            "webp": "🖼️",
        }.get(file_data["file_extension"].lower(), "📁")
        files.append(file_data)

    return files


def group_files_by_subject(files):
    grouped_files = {subject: [] for subject in SUBJECT_OPTIONS}
    grouped_files["OTHER"] = []

    for file_data in files:
        subject = file_data.get("subject", "")
        if subject in grouped_files:
            grouped_files[subject].append(file_data)
        else:
            grouped_files["OTHER"].append(file_data)

    return grouped_files


def group_files_by_category(files):
    grouped_files = {category: [] for category in CATEGORY_OPTIONS}
    grouped_files["OTHER"] = []

    for file_data in files:
        category = file_data.get("category", "")
        if category in grouped_files:
            grouped_files[category].append(file_data)
        else:
            grouped_files["OTHER"].append(file_data)

    return grouped_files


@app.route("/", methods=["GET"])
def index():
    search_term = request.args.get("search", "").strip()
    files = fetch_files(search_term if search_term else None)
    return render_template("index.html", files=files, search_term=search_term, subject_options=SUBJECT_OPTIONS, lab_options=LAB_OPTIONS)


@app.route("/dashboard", methods=["GET"])
def dashboard():
    search_term = request.args.get("search", "").strip()
    selected_subject = request.args.get("subject", "").strip()
    selected_category = request.args.get("category", "All categories").strip()

    if selected_subject not in SUBJECT_OPTIONS:
        selected_subject = SUBJECT_OPTIONS[0]

    category_filter_options = ["All categories", *CATEGORY_OPTIONS]
    if selected_category not in category_filter_options:
        selected_category = "All categories"

    files = fetch_files(search_term if search_term else None)
    subject_files = [
        file_data
        for file_data in files
        if file_data.get("subject") == selected_subject
        and (selected_category == "All categories" or file_data.get("category") == selected_category)
    ]
    grouped_by_category = group_files_by_category(subject_files)
    display_categories = CATEGORY_OPTIONS if selected_category == "All categories" else [selected_category]

    return render_template(
        "dashboard.html",
        files=files,
        subject_files=subject_files,
        search_term=search_term,
        selected_subject=selected_subject,
        selected_category=selected_category,
        subject_options=SUBJECT_OPTIONS,
        category_options=category_filter_options,
        display_categories=display_categories,
        grouped_by_category=grouped_by_category,
    )


@app.route("/labs", methods=["GET"])
def labs():
    search_term = request.args.get("search", "").strip()
    selected_subject = request.args.get("subject", "").strip()
    selected_category = request.args.get("category", "All categories").strip()

    if selected_subject not in LAB_OPTIONS:
        selected_subject = LAB_OPTIONS[0]

    category_filter_options = ["All categories", *LAB_CATEGORY_OPTIONS]
    if selected_category not in category_filter_options:
        selected_category = "All categories"

    files = fetch_files(search_term if search_term else None)
    subject_files = [
        f for f in files
        if f.get("subject") == selected_subject
        and (selected_category == "All categories" or f.get("category") == selected_category)
    ]
    grouped_by_category = {cat: [] for cat in LAB_CATEGORY_OPTIONS}
    grouped_by_category["OTHER"] = []
    for f in subject_files:
        cat = f.get("category", "")
        if cat in grouped_by_category:
            grouped_by_category[cat].append(f)
        else:
            grouped_by_category["OTHER"].append(f)
    display_categories = LAB_CATEGORY_OPTIONS if selected_category == "All categories" else [selected_category]

    return render_template(
        "labs.html",
        files=files,
        subject_files=subject_files,
        search_term=search_term,
        selected_subject=selected_subject,
        selected_category=selected_category,
        lab_options=LAB_OPTIONS,
        category_options=category_filter_options,
        display_categories=display_categories,
        grouped_by_category=grouped_by_category,
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    # Read the form fields and validate the uploaded file.
    uploaded_file = request.files.get("file")
    semester = request.form.get("semester", "").strip()
    subject = request.form.get("subject", "").strip()
    category = request.form.get("category", "").strip()

    if not uploaded_file or uploaded_file.filename == "":
        flash("Please choose a file to upload.", "error")
        return redirect(url_for("index"))

    if not semester or not subject or not category:
        flash("Semester, subject, and category are required.", "error")
        return redirect(url_for("index"))

    if subject not in SUBJECT_OPTIONS and subject not in LAB_OPTIONS:
        flash("Please choose a valid subject.", "error")
        return redirect(url_for("index"))

    valid_categories = LAB_CATEGORY_OPTIONS if subject in LAB_OPTIONS else CATEGORY_OPTIONS
    if category not in valid_categories:
        flash("Please choose a valid category.", "error")
        return redirect(url_for("index"))

    if not allowed_file(uploaded_file.filename):
        flash("Only PDF, DOCX, PPT, and image files are allowed.", "error")
        return redirect(url_for("index"))

    original_name = secure_filename(uploaded_file.filename)
    file_extension = original_name.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}_{original_name}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
    uploaded_file.save(file_path)
    file_size = os.path.getsize(file_path)
    upload_date = datetime.now().isoformat(timespec="seconds")

    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO files (original_name, stored_name, file_size, upload_date, semester, subject, category, file_extension)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (original_name, unique_name, file_size, upload_date, semester, subject, category, file_extension),
        )
        connection.commit()

    flash(f"{original_name} uploaded successfully.", "success")
    return redirect(url_for("index"))


@app.route("/download/<int:file_id>")
def download_file(file_id):
    with get_db_connection() as connection:
        file_row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()

    if file_row is None:
        flash("File not found.", "error")
        return redirect(url_for("index"))

    return send_from_directory(app.config["UPLOAD_FOLDER"], file_row["stored_name"], as_attachment=True, download_name=file_row["original_name"])


@app.route("/view/<int:file_id>")
def view_file(file_id):
    with get_db_connection() as connection:
        file_row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()

    if file_row is None:
        flash("File not found.", "error")
        return redirect(url_for("index"))

    return send_from_directory(app.config["UPLOAD_FOLDER"], file_row["stored_name"], as_attachment=False)


@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    # Remove the file from both SQLite and the uploads folder.
    next_url = request.form.get("next", "").strip()
    with get_db_connection() as connection:
        file_row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()

        if file_row is None:
            flash("File not found.", "error")
            return redirect(next_url if next_url.startswith("/") else url_for("dashboard"))

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file_row["stored_name"])
        if os.path.exists(file_path):
            os.remove(file_path)

        connection.execute("DELETE FROM files WHERE id = ?", (file_id,))
        connection.commit()

    flash(f"{file_row['original_name']} deleted successfully.", "success")
    return redirect(next_url if next_url.startswith("/") else url_for("dashboard"))


initialize_database()


if __name__ == "__main__":
    app.run(debug=True)