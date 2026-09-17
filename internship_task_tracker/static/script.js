// =====================================
// SHOW PAGE
// =====================================

function showPage(pageName) {

    let pages =
        document.getElementsByClassName("page");


    for (let page of pages) {

        page.style.display = "none";

    }


    document.getElementById(pageName)
        .style.display = "block";


    if (pageName == "interns") {

        loadInterns();

    }


    if (pageName == "tasks") {

        loadTasks();

    }


    if (pageName == "progress") {

        loadProgress();

    }

}


// =====================================
// CHANGE TASK TYPE
// =====================================

function changeTaskType() {

    let type =
        document.getElementById("taskType").value;


    let individualBox =
        document.getElementById("individualBox");


    let teamBox =
        document.getElementById("teamBox");


    if (type == "Individual") {

        individualBox.style.display = "block";

        teamBox.style.display = "none";

    }


    else if (type == "Team") {

        individualBox.style.display = "none";

        teamBox.style.display = "block";

        loadTeamMembers();

    }


    else {

        individualBox.style.display = "none";

        teamBox.style.display = "none";

    }

}


// =====================================
// LOAD TEAM MEMBERS
// =====================================

async function loadTeamMembers() {

    let response =
        await fetch("/api/interns");


    let interns =
        await response.json();


    let teamMembers =
        document.getElementById("teamMembers");


    teamMembers.innerHTML = "";


    for (let intern of interns) {

        teamMembers.innerHTML += `

            <div class="member">

                <input
                    type="checkbox"
                    value="${intern.id}"
                    name="teamMember"
                >

                ${intern.name}

            </div>

        `;

    }

}


// =====================================
// ADD INTERN
// =====================================

document
    .getElementById("internForm")
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            let intern = {

                name:
                    document.getElementById(
                        "internName"
                    ).value,

                email:
                    document.getElementById(
                        "internEmail"
                    ).value,

                department:
                    document.getElementById(
                        "department"
                    ).value,

                joining_date:
                    document.getElementById(
                        "joiningDate"
                    ).value

            };


            let response =
                await fetch(
                    "/api/interns",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(intern)

                    }
                );


            let result =
                await response.json();


            alert(result.message);


            document
                .getElementById("internForm")
                .reset();


            loadInterns();

        }
    );


// =====================================
// LOAD INTERNS
// =====================================

async function loadInterns() {

    let response =
        await fetch("/api/interns");


    let interns =
        await response.json();


    let table =
        document.getElementById(
            "internTable"
        );


    let select =
        document.getElementById(
            "taskIntern"
        );


    table.innerHTML = "";

    select.innerHTML =
        `<option value="">
            Select Intern
        </option>`;


    for (let intern of interns) {

        // TABLE

        table.innerHTML += `

            <tr>

                <td>
                    ${intern.id}
                </td>

                <td>
                    ${intern.name}
                </td>

                <td>
                    ${intern.email}
                </td>

                <td>
                    ${intern.department}
                </td>

                <td>
                    ${intern.joining_date}
                </td>

            </tr>

        `;


        // INDIVIDUAL TASK DROPDOWN

        select.innerHTML += `

            <option value="${intern.id}">
                ${intern.name}
            </option>

        `;

    }

}


// =====================================
// ASSIGN TASK
// =====================================

document
    .getElementById("taskForm")
    .addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();


            let type =
                document.getElementById(
                    "taskType"
                ).value;


            let assignedTo = [];


            // INDIVIDUAL TASK

            if (type == "Individual") {

                let intern =
                    document.getElementById(
                        "taskIntern"
                    ).value;


                if (intern == "") {

                    alert(
                        "Please select an intern"
                    );

                    return;

                }


                assignedTo.push(
                    parseInt(intern)
                );

            }


            // TEAM TASK

            if (type == "Team") {

                let members =
                    document.querySelectorAll(
                        'input[name="teamMember"]:checked'
                    );


                for (let member of members) {

                    assignedTo.push(
                        parseInt(member.value)
                    );

                }


                if (assignedTo.length == 0) {

                    alert(
                        "Please select team members"
                    );

                    return;

                }

            }


            let task = {

                assigned_to: assignedTo,

                title:
                    document.getElementById(
                        "taskTitle"
                    ).value,

                description:
                    document.getElementById(
                        "taskDescription"
                    ).value,

                type: type,

                deadline:
                    document.getElementById(
                        "deadline"
                    ).value

            };


            let response =
                await fetch(
                    "/api/tasks",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(task)

                    }
                );


            let result =
                await response.json();


            alert(result.message);


            document
                .getElementById("taskForm")
                .reset();


            document.getElementById(
                "individualBox"
            ).style.display = "none";


            document.getElementById(
                "teamBox"
            ).style.display = "none";


            loadTasks();

        }
    );


// =====================================
// LOAD TASKS
// =====================================

async function loadTasks() {

    let response =
        await fetch("/api/tasks");


    let tasks =
        await response.json();


    let internResponse =
        await fetch("/api/interns");


    let interns =
        await internResponse.json();


    let list =
        document.getElementById(
            "taskList"
        );


    list.innerHTML = "";


    let completed = 0;

    let pending = 0;


    for (let task of tasks) {

        if (task.status == "Completed") {

            completed++;

        }


        if (task.status == "Pending") {

            pending++;

        }


        // FIND ALL ASSIGNED PEOPLE

        let names = [];


        for (
            let internId of task.assigned_to
        ) {

            let intern =
                interns.find(
                    i => i.id == internId
                );


            if (intern) {

                names.push(intern.name);

            }

        }


        list.innerHTML += `

            <div class="task">

                <h3>
                    ${task.title}
                </h3>

                <p>
                    Assigned To:
                    <b>
                        ${names.join(", ")}
                    </b>
                </p>

                <p>
                    Type:
                    <b>${task.type}</b>
                </p>

                <p>
                    Description:
                    ${task.description}
                </p>

                <p>
                    Deadline:
                    ${task.deadline}
                </p>

                <p>
                    Status:
                    <b>${task.status}</b>
                </p>


                <select
                    onchange="
                    updateStatus(
                        ${task.id},
                        this.value
                    )"
                >

                    <option
                        value="Pending"
                        ${
                            task.status ==
                            "Pending"
                            ? "selected"
                            : ""
                        }
                    >
                        Pending
                    </option>


                    <option
                        value="In Progress"
                        ${
                            task.status ==
                            "In Progress"
                            ? "selected"
                            : ""
                        }
                    >
                        In Progress
                    </option>


                    <option
                        value="Completed"
                        ${
                            task.status ==
                            "Completed"
                            ? "selected"
                            : ""
                        }
                    >
                        Completed
                    </option>

                </select>

            </div>

        `;

    }


    document.getElementById(
        "totalTasks"
    ).innerText = tasks.length;


    document.getElementById(
        "completedTasks"
    ).innerText = completed;


    document.getElementById(
        "pendingTasks"
    ).innerText = pending;


    loadOverdue();

}


// =====================================
// UPDATE STATUS
// =====================================

async function updateStatus(
    taskId,
    status
) {

    let response =
        await fetch(
            `/api/tasks/${taskId}`,
            {

                method: "PUT",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    status: status
                })

            }
        );


    let result =
        await response.json();


    alert(result.message);


    loadTasks();

}


// =====================================
// OVERDUE
// =====================================

async function loadOverdue() {

    let response =
        await fetch(
            "/api/tasks/overdue"
        );


    let overdue =
        await response.json();


    document.getElementById(
        "overdueTasks"
    ).innerText =
        overdue.length;

}


// =====================================
// PROGRESS
// =====================================

async function loadProgress() {

    let response =
        await fetch("/api/interns");


    let interns =
        await response.json();


    let report =
        document.getElementById(
            "progressReport"
        );


    report.innerHTML = "";


    for (let intern of interns) {

        let response =
            await fetch(
                `/api/interns/${intern.id}/progress`
            );


        let data =
            await response.json();


        report.innerHTML += `

            <div class="task">

                <h3>
                    ${intern.name}
                </h3>

                <p>
                    Total Tasks:
                    ${data.total}
                </p>

                <p>
                    Completed:
                    ${data.completed}
                </p>

                <p>
                    Pending:
                    ${data.pending}
                </p>

                <p>
                    In Progress:
                    ${data.in_progress}
                </p>

                <p>
                    Progress:
                    ${data.progress}%
                </p>


                <div class="progress">

                    <div
                        class="progress-bar"
                        style="
                        width:${data.progress}%
                        "
                    >

                        ${data.progress}%

                    </div>

                </div>

            </div>

        `;

    }

}


// =====================================
// START APPLICATION
// =====================================

window.onload = function() {

    loadInterns();

    loadTasks();

    showPage("dashboard");

};