from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import pandas as pd
import os
import json

app = Flask(__name__)

# File categories
FILE_CATEGORIES = {
    "correspondence": [".pdf", ".docx", ".doc",".jpg"],
    "audits": [".txt", ".csv",".xlsx",".docx"],
    "reports": [".xlsx",".docx",".xls"]
}

STATUS_FILE = "file_status.json"


# -----------------------------
# Status Functions
# -----------------------------
def load_statuses():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                data = json.load(f)
                # Auto-migrate old format (string) to new format (dictionary)
                for key, value in data.items():
                    if isinstance(value, str):
                        data[key] = {"status": value, "cleared": False}
                return data
        except:
            return {}
    return {}


def save_statuses(statuses):
    with open(STATUS_FILE, "w") as f:
        json.dump(statuses, f, indent=4)


# -----------------------------
# Summary Function
# -----------------------------
def get_summary(category=None, status_filter=None):

    reports_dir = os.path.join(app.root_path, "static", "reports")

    if not os.path.exists(reports_dir):
        print(f"Folder not found: {reports_dir}")
        return 0, 0, []

    files = os.listdir(reports_dir)

    # Filter by category if selected
    if category and category in FILE_CATEGORIES:
        extensions = FILE_CATEGORIES[category]
        files = [
            f for f in files
            if os.path.splitext(f)[1].lower() in extensions
        ]

    total_revenue = 0
    total_transactions = 0
    stations = []

    statuses = load_statuses()

    for file in files:

        file_path = os.path.join(reports_dir, file)
        ext = os.path.splitext(file)[1].lower()
        
        # Get the current status and cleared state of the file
        file_info = statuses.get(file, {"status": "Ongoing", "cleared": False})
        current_status = file_info.get("status", "Ongoing")
        is_cleared = file_info.get("cleared", False)

        # If the file has been cleared, skip it entirely so it doesn't show up
        if is_cleared:
            continue

        # Filter by status if selected
        if status_filter and current_status != status_filter:
            continue

        file_data = {
            "File": file,
            "Link": url_for("view_file", filename=file),
            "status": current_status
        }

        # Process Excel files
        if ext in [".xlsx", ".xls"]:

            try:
                df = pd.read_excel(file_path)

                if "Revenue" in df.columns:
                    total_revenue += df["Revenue"].fillna(0).sum()

                if "Transactions" in df.columns:
                    total_transactions += df["Transactions"].fillna(0).sum()

                file_data["Preview"] = (
                    df.head(5)
                    .fillna("")
                    .to_dict(orient="records")
                )

            except Exception as e:
                file_data["Error"] = str(e)

        stations.append(file_data)

    return total_revenue, total_transactions, stations


# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def dashboard():

    category = request.args.get("category")
    status_filter = request.args.get("status_filter")

    revenue, transactions, stations = get_summary(category, status_filter)

    return render_template(
        "index.html",
        revenue=revenue,
        transactions=transactions,
        stations=stations,
        category=category,
        status_filter=status_filter
    )


@app.route("/view/<path:filename>")
def view_file(filename):

    reports_dir = os.path.join(app.root_path, "static", "reports")

    return send_from_directory(
        reports_dir,
        filename,
        as_attachment=False
    )


@app.route("/update_status", methods=["POST"])
def update_status():

    file = request.form.get("file")
    status = request.form.get("status")

    category = request.form.get("category", "")
    status_filter = request.form.get("status_filter", "")

    statuses = load_statuses()
    
    # Update status while preserving the 'cleared' flag
    if file not in statuses:
        statuses[file] = {"status": status, "cleared": False}
    else:
        statuses[file]["status"] = status
        
    save_statuses(statuses)

    return redirect(url_for("dashboard", category=category, status_filter=status_filter))


@app.route("/clear_file", methods=["POST"])
def clear_file():

    file = request.form.get("file")
    category = request.form.get("category", "")
    status_filter = request.form.get("status_filter", "")

    statuses = load_statuses()
    
    # Mark the file as cleared
    if file not in statuses:
        statuses[file] = {"status": "Processed", "cleared": True}
    else:
        statuses[file]["cleared"] = True
        
    save_statuses(statuses)

    return redirect(url_for("dashboard", category=category, status_filter=status_filter))


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)