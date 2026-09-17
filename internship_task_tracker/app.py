from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

DATA_FILE = "data/tracker.json"

# JSON FILE FUNCTIONS

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "interns": [],
            "tasks": []
        }

    with open(DATA_FILE, "r") as file:
        return json.load(file)


def save_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


# HOME PAGE

@app.route("/")
def home():
    return render_template("index.html")


# ADD INTERN

@app.route("/api/interns", methods=["POST"])
def add_intern():

    data = load_data()
    intern = request.json

    new_intern = {
        "id": len(data["interns"]) + 1,
        "name": intern["name"],
        "email": intern["email"],
        "department": intern["department"],
        "joining_date": intern["joining_date"]
    }

    data["interns"].append(new_intern)

    save_data(data)

    return jsonify({
        "message": "Intern added successfully",
        "intern": new_intern
    })


# GET ALL INTERNS

@app.route("/api/interns", methods=["GET"])
def get_interns():

    data = load_data()

    return jsonify(data["interns"])


# ASSIGN TASK

@app.route("/api/tasks", methods=["POST"])
def assign_task():

    data = load_data()
    task = request.json

    new_task = {
        "id": len(data["tasks"]) + 1,
        "assigned_to": task["assigned_to"],
        "title": task["title"],
        "description": task["description"],
        "type": task["type"],
        "deadline": task["deadline"],
        "status": "Pending"
    }

    data["tasks"].append(new_task)

    save_data(data)

    return jsonify({
        "message": "Task assigned successfully",
        "task": new_task
    })


# GET ALL TASKS

@app.route("/api/tasks", methods=["GET"])
def get_tasks():

    data = load_data()

    return jsonify(data["tasks"])

# UPDATE TASK STATUS

@app.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):

    data = load_data()
    request_data = request.json

    for task in data["tasks"]:

        if task["id"] == task_id:

            task["status"] = request_data["status"]

            save_data(data)

            return jsonify({
                "message": "Task status updated",
                "task": task
            })

    return jsonify({
        "error": "Task not found"
    }), 404

# INTERN PROGRESS


@app.route("/api/interns/<int:intern_id>/progress")
def get_progress(intern_id):

    data = load_data()

    total = 0
    completed = 0
    pending = 0
    in_progress = 0

    for task in data["tasks"]:

        # Check if this task belongs to the intern
        if intern_id in task.get("assigned_to", []):

            total += 1

            if task["status"] == "Completed":
                completed += 1

            elif task["status"] == "Pending":
                pending += 1

            elif task["status"] == "In Progress":
                in_progress += 1

    progress = 0

    if total > 0:
        progress = (completed / total) * 100

    return jsonify({
        "total": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress,
        "progress": round(progress, 2)
    })

# RUN APPLICATION

if __name__ == "__main__":
    app.run(debug=True)