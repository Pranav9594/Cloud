import os
import sqlite3
import uuid
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_BUCKET = "uploads"
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

USE_SUPABASE = False
supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        USE_SUPABASE = True
    except Exception as e:
        print(f"Supabase init error: {e}. Falling back to local SQLite.")
        USE_SUPABASE = False

ALLOWED_EXTENSIONS = {"pdf", "docx", "ppt", "pptx", "png", "jpg", "jpeg", "gif", "webp"}
SUBJECT_OPTIONS = ["PYTHON", "DOT NET", "ED", "R PROG", "HR", "IT APTI"]
LAB_OPTIONS = ["LAB ON PYTHON", "LAB ON DOT NET"]
CATEGORY_OPTIONS = ["Syllabus", "Notes", "Previous Papers", "Assignments"]
LAB_CATEGORY_OPTIONS = ["Syllabus", "Code", "Output"]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024
app.secret_key = "college-storage-secret-key"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "college_storage.db")


def get_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_db():
    conn = get_sqlite_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            upload_date TEXT NOT NULL,
            semester TEXT NOT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL,
            file_extension TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


if not USE_SUPABASE:
    init_sqlite_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def fetch_files(search_term=None):
    if USE_SUPABASE:
        query = supabase.table("files").select("*").order("upload_date", desc=True)
        if search_term:
            query = query.ilike("original_name", f"%{search_term}%")
        rows = query.execute().data
    else:
        conn = get_sqlite_db()
        if search_term:
            cursor = conn.execute("SELECT * FROM files WHERE original_name LIKE ? ORDER BY id DESC", (f"%{search_term}%",))
        else:
            cursor = conn.execute("SELECT * FROM files ORDER BY id DESC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

    icons = {"pdf": "📄", "docx": "📝", "ppt": "📊", "pptx": "📊",
             "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️", "gif": "🖼️", "webp": "🖼️"}

    for f in rows:
        f["pretty_size"] = format_size(f["file_size"])
        try:
            f["display_date"] = datetime.fromisoformat(f["upload_date"]).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            f["display_date"] = str(f["upload_date"])
        f["icon"] = icons.get(str(f["file_extension"]).lower(), "📁")
        if USE_SUPABASE:
            f["file_url"] = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(f["stored_name"])
        else:
            f["file_url"] = url_for("serve_file", filename=f["stored_name"])
    return rows


def group_files_by_category(files, category_options):
    grouped = {cat: [] for cat in category_options}
    grouped["OTHER"] = []
    for f in files:
        cat = f.get("category", "")
        grouped[cat].append(f) if cat in grouped else grouped["OTHER"].append(f)
    return grouped


@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/", methods=["GET"])
def index():
    search_term = request.args.get("search", "").strip()
    files = fetch_files(search_term if search_term else None)
    return render_template("index.html", files=files, search_term=search_term,
                           subject_options=SUBJECT_OPTIONS, lab_options=LAB_OPTIONS)


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
        f for f in files
        if f.get("subject") == selected_subject
        and (selected_category == "All categories" or f.get("category") == selected_category)
    ]
    grouped_by_category = group_files_by_category(subject_files, CATEGORY_OPTIONS)
    display_categories = CATEGORY_OPTIONS if selected_category == "All categories" else [selected_category]

    return render_template("dashboard.html", files=files, subject_files=subject_files,
                           search_term=search_term, selected_subject=selected_subject,
                           selected_category=selected_category, subject_options=SUBJECT_OPTIONS,
                           category_options=category_filter_options,
                           display_categories=display_categories,
                           grouped_by_category=grouped_by_category)


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
    grouped_by_category = group_files_by_category(subject_files, LAB_CATEGORY_OPTIONS)
    display_categories = LAB_CATEGORY_OPTIONS if selected_category == "All categories" else [selected_category]

    return render_template("labs.html", files=files, subject_files=subject_files,
                           search_term=search_term, selected_subject=selected_subject,
                           selected_category=selected_category, lab_options=LAB_OPTIONS,
                           category_options=category_filter_options,
                           display_categories=display_categories,
                           grouped_by_category=grouped_by_category)


@app.route("/upload", methods=["POST"])
def upload_file():
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
    stored_name = f"{uuid.uuid4().hex}_{original_name}"
    file_bytes = uploaded_file.read()
    file_size = len(file_bytes)

    if USE_SUPABASE:
        try:
            supabase.storage.from_(SUPABASE_BUCKET).upload(
                stored_name, file_bytes,
                file_options={"content-type": uploaded_file.content_type}
            )
            supabase.table("files").insert({
                "original_name": original_name,
                "stored_name": stored_name,
                "file_size": file_size,
                "upload_date": datetime.now().isoformat(timespec="seconds"),
                "semester": semester,
                "subject": subject,
                "category": category,
                "file_extension": file_extension,
            }).execute()
        except Exception as e:
            flash(f"Upload error: {e}. Please ensure public bucket 'uploads' exists in Supabase Storage.", "error")
            return redirect(url_for("index"))
    else:
        file_path = os.path.join(UPLOAD_FOLDER, stored_name)
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        conn = get_sqlite_db()
        conn.execute("""
            INSERT INTO files (original_name, stored_name, file_size, upload_date, semester, subject, category, file_extension)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            original_name, stored_name, file_size,
            datetime.now().isoformat(timespec="seconds"),
            semester, subject, category, file_extension
        ))
        conn.commit()
        conn.close()

    flash(f"{original_name} uploaded successfully.", "success")
    return redirect(url_for("index"))


@app.route("/download/<int:file_id>")
def download_file(file_id):
    if USE_SUPABASE:
        row = supabase.table("files").select("*").eq("id", file_id).single().execute().data
        if not row:
            flash("File not found.", "error")
            return redirect(url_for("index"))
        file_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(row["stored_name"])
        return redirect(file_url)
    else:
        conn = get_sqlite_db()
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        conn.close()
        if not row:
            flash("File not found.", "error")
            return redirect(url_for("index"))
        return send_from_directory(UPLOAD_FOLDER, row["stored_name"], as_attachment=True, download_name=row["original_name"])


@app.route("/view/<int:file_id>")
def view_file(file_id):
    if USE_SUPABASE:
        row = supabase.table("files").select("*").eq("id", file_id).single().execute().data
        if not row:
            flash("File not found.", "error")
            return redirect(url_for("index"))
        file_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(row["stored_name"])
        return redirect(file_url)
    else:
        conn = get_sqlite_db()
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        conn.close()
        if not row:
            flash("File not found.", "error")
            return redirect(url_for("index"))
        return send_from_directory(UPLOAD_FOLDER, row["stored_name"])


@app.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    next_url = request.form.get("next", "").strip()
    if USE_SUPABASE:
        row = supabase.table("files").select("*").eq("id", file_id).single().execute().data
        if not row:
            flash("File not found.", "error")
            return redirect(next_url if next_url.startswith("/") else url_for("dashboard"))
        supabase.storage.from_(SUPABASE_BUCKET).remove([row["stored_name"]])
        supabase.table("files").delete().eq("id", file_id).execute()
    else:
        conn = get_sqlite_db()
        row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
        if not row:
            conn.close()
            flash("File not found.", "error")
            return redirect(next_url if next_url.startswith("/") else url_for("dashboard"))
        file_path = os.path.join(UPLOAD_FOLDER, row["stored_name"])
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
        conn.close()

    flash(f"{row['original_name']} deleted successfully.", "deleted")
    return redirect(next_url if next_url.startswith("/") else url_for("dashboard"))


@app.errorhandler(413)
def request_entity_too_large(error):
    flash("File is too large! Maximum allowed size is 30 MB.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
