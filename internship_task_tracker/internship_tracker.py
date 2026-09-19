from datetime import datetime

# -----------------------------
# Data Storage
# -----------------------------
interns = {}
tasks = []


# -----------------------------
# Add Intern
# -----------------------------
def add_intern():
    intern_id = input("Enter Intern ID: ")
    name = input("Enter Intern Name: ")
    email = input("Enter Email: ")

    interns[intern_id] = {
        "name": name,
        "email": email
    }

    print("✅ Intern added successfully!\n")


# -----------------------------
# View Interns
# -----------------------------
def view_interns():
    if not interns:
        print("No interns found.\n")
        return

    print("\n----- Intern List -----")
    for intern_id, details in interns.items():
        print(f"ID: {intern_id}")
        print(f"Name: {details['name']}")
        print(f"Email: {details['email']}")
        print("-" * 30)
    print()


# -----------------------------
# Assign Task
# -----------------------------
def assign_task():
    intern_id = input("Enter Intern ID: ")

    if intern_id not in interns:
        print("❌ Intern not found.\n")
        return

    title = input("Enter Task Title: ")
    deadline = input("Enter Deadline (YYYY-MM-DD): ")

    task = {
        "intern_id": intern_id,
        "title": title,
        "deadline": deadline,
        "status": "Pending"
    }

    tasks.append(task)

    print("✅ Task assigned successfully!\n")


# -----------------------------
# View All Tasks
# -----------------------------
def view_tasks():
    if not tasks:
        print("No tasks available.\n")
        return

    print("\n----- Task List -----")
    for i, task in enumerate(tasks, start=1):
        print(f"Task No: {i}")
        print(f"Intern: {interns[task['intern_id']]['name']}")
        print(f"Task: {task['title']}")
        print(f"Deadline: {task['deadline']}")
        print(f"Status: {task['status']}")
        print("-" * 30)
    print()


# -----------------------------
# Update Task Status
# -----------------------------
def update_task_status():
    view_tasks()

    if not tasks:
        return

    try:
        task_no = int(input("Enter Task Number: ")) - 1

        if task_no < 0 or task_no >= len(tasks):
            print("❌ Invalid Task Number\n")
            return

        print("\n1. Pending")
        print("2. In Progress")
        print("3. Completed")

        choice = input("Select Status: ")

        if choice == "1":
            tasks[task_no]["status"] = "Pending"
        elif choice == "2":
            tasks[task_no]["status"] = "In Progress"
        elif choice == "3":
            tasks[task_no]["status"] = "Completed"
        else:
            print("❌ Invalid Choice")
            return

        print("✅ Status Updated Successfully!\n")

    except ValueError:
        print("❌ Enter valid number.\n")


# -----------------------------
# Check Overdue Tasks
# -----------------------------
def check_overdue_tasks():
    today = datetime.today().date()

    print("\n----- Overdue Tasks -----")

    found = False

    for task in tasks:
        deadline = datetime.strptime(
            task["deadline"], "%Y-%m-%d"
        ).date()

        if deadline < today and task["status"] != "Completed":
            found = True

            print(f"Intern: {interns[task['intern_id']]['name']}")
            print(f"Task: {task['title']}")
            print(f"Deadline: {task['deadline']}")
            print(f"Status: {task['status']}")
            print("-" * 30)

    if not found:
        print("No overdue tasks found.")

    print()


# -----------------------------
# Generate Progress Report
# -----------------------------
def generate_report():
    if not interns:
        print("No interns available.\n")
        return

    print("\n========== INTERN REPORT ==========")

    for intern_id, details in interns.items():

        intern_tasks = [
            task for task in tasks
            if task["intern_id"] == intern_id
        ]

        total = len(intern_tasks)

        completed = sum(
            1 for task in intern_tasks
            if task["status"] == "Completed"
        )

        pending = sum(
            1 for task in intern_tasks
            if task["status"] == "Pending"
        )

        in_progress = sum(
            1 for task in intern_tasks
            if task["status"] == "In Progress"
        )

        progress = (
            (completed / total) * 100
            if total > 0 else 0
        )

        print("\n----------------------------------")
        print(f"Intern ID : {intern_id}")
        print(f"Name      : {details['name']}")
        print(f"Email     : {details['email']}")

        print("\nTask Summary")
        print(f"Total Tasks       : {total}")
        print(f"Completed Tasks   : {completed}")
        print(f"Pending Tasks     : {pending}")
        print(f"In Progress Tasks : {in_progress}")
        print(f"Progress          : {progress:.2f}%")

        print("\nAssigned Tasks")

        if not intern_tasks:
            print("No tasks assigned.")

        for task in intern_tasks:
            print(
                f"- {task['title']} | "
                f"{task['status']} | "
                f"Deadline: {task['deadline']}"
            )

    print("\n==================================\n")


# -----------------------------
# Main Menu
# -----------------------------
def main():
    while True:
        print("===== Internship Task Tracker =====")
        print("1. Add Intern")
        print("2. View Interns")
        print("3. Assign Task")
        print("4. View Tasks")
        print("5. Update Task Status")
        print("6. Check Overdue Tasks")
        print("7. Generate Progress Report")
        print("8. Exit")

        choice = input("Enter Choice: ")

        if choice == "1":
            add_intern()

        elif choice == "2":
            view_interns()

        elif choice == "3":
            assign_task()

        elif choice == "4":
            view_tasks()

        elif choice == "5":
            update_task_status()

        elif choice == "6":
            check_overdue_tasks()

        elif choice == "7":
            generate_report()

        elif choice == "8":
            print("Thank You!")
            break

        else:
            print("❌ Invalid Choice\n")


# Run Program
if __name__ == "__main__":
    main()