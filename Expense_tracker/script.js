function showDashboard() {
    document.querySelector(".main-content h1").textContent = "Dashboard";

    fetch("/api/dashboard")
        .then(response => response.json())
        .then(data => {
            document.getElementById("content").innerHTML = `
                <h2>Expenses details</h2>
                <div class="dashboard-summary">
                    <div class="summary-item">
                        <span class="summary-label">Total Spent</span>
                        <strong>₹${Number(data.total || 0).toFixed(2)}</strong>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Today's Spent</span>
                        <strong>₹${Number(data.today || 0).toFixed(2)}</strong>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Highest Expense</span>
                        <strong>₹${Number(data.highest || 0).toFixed(2)}</strong>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Average Expense</span>
                        <strong>₹${Number(data.average || 0).toFixed(2)}</strong>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Number of Expenses</span>
                        <strong>${data.count || 0}</strong>
                    </div>
                </div>
                <p class="spending-status ${data.high_spending ? "warning" : "success"}">
                    ${data.message || ""}
                </p>
            `;
        })
        .catch(() => {
            document.getElementById("content").innerHTML = `
                <h2>Dashboard</h2>
                <p>Unable to load dashboard data.</p>
            `;
        });
}


function showAddExpense() {
    document.querySelector(".main-content h1").textContent = "Add Expense";

    document.getElementById("content").innerHTML = `
        <h2>Add Expense</h2>

        <div style="display:flex; flex-direction:column; gap:10px; max-width:350px;">
            <input type="text" id="expenseName" placeholder="Expense name">
            <input type="number" id="expenseAmount" placeholder="Amount" step="0.01" min="0.01">
            <input type="text" id="expenseCategory" placeholder="Category">
            <button onclick="addExpense()">Add Expense</button>
        </div>
    `;
}


function addExpense() {
    const name = document.getElementById("expenseName").value.trim();
    const amount = document.getElementById("expenseAmount").value;
    const category = document.getElementById("expenseCategory").value.trim();

    if (!name || !category || !amount) {
        alert("Please enter name, amount, and category.");
        return;
    }

    fetch("/api/expenses", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            amount: Number(amount),
            category: category
        })
    })
        .then(async response => {
            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.error || "Failed to add expense");
            }
            alert("Expense added successfully!");
            showDashboard();
        })
        .catch(error => {
            alert(error.message || "Something went wrong while adding the expense.");
        });
}


function showTodaySpent() {
    document.querySelector(".main-content h1").textContent = "Today Spent";

    fetch("/api/expenses/today")
        .then(response => response.json())
        .then(data => {
            if (!data.expenses || data.expenses.length === 0) {
                document.getElementById("content").innerHTML = `
                    <h2>Today's Expenses</h2>
                    <p>No expenses recorded today.</p>
                `;
                return;
            }

            const rows = data.expenses.map(expense => `
                <tr>
                    <td>${expense.date}</td>
                    <td>${expense.name}</td>
                    <td>${expense.category}</td>
                    <td>₹${Number(expense.amount).toFixed(2)}</td>
                </tr>
            `).join("");

            document.getElementById("content").innerHTML = `
                <h2>Today's Expenses</h2>
                <p>Total: ₹${Number(data.total || 0).toFixed(2)}</p>
                <div class="table-container">
                    <table class="expense-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Expense</th>
                                <th>Category</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            `;
        })
        .catch(() => {
            document.getElementById("content").innerHTML = `
                <h2>Today's Expenses</h2>
                <p>Unable to load today's expenses.</p>
            `;
        });
}


function showHistory() {
    document.querySelector(".main-content h1").textContent = "History";

    fetch("/api/expenses")
        .then(response => response.json())
        .then(data => {
            document.getElementById("content").innerHTML = `
                <h2>Expense History</h2>
                <div class="history-filter">
                    <label for="historyDate">Filter by date</label>
                    <input type="date" id="historyDate">
                    <button type="button" id="filterHistoryButton">Filter</button>
                    <button type="button" id="clearHistoryFilterButton">Clear</button>
                </div>
                <p id="historyTotal" class="history-total"></p>
                <p id="historyMessage"></p>
                <div class="table-container">
                    <table class="expense-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Expense</th>
                                <th>Category</th>
                                <th>Amount</th>
                            </tr>
                        </thead>
                        <tbody id="historyRows"></tbody>
                    </table>
                </div>
            `;

            const dateInput = document.getElementById("historyDate");
            const renderHistory = () => {
                const selectedDate = dateInput.value;
                const filteredExpenses = selectedDate
                    ? data.filter(expense => expense.date === selectedDate)
                    : data;
                const total = filteredExpenses.reduce(
                    (sum, expense) => sum + Number(expense.amount || 0),
                    0
                );

                document.getElementById("historyTotal").textContent = selectedDate
                    ? `Total for ${selectedDate}: ₹${total.toFixed(2)}`
                    : `Total expenses: ₹${total.toFixed(2)}`;
                document.getElementById("historyMessage").textContent = filteredExpenses.length
                    ? ""
                    : "No expenses recorded for this date.";
                document.getElementById("historyRows").innerHTML = filteredExpenses.map(expense => `
                    <tr>
                        <td>${expense.date}</td>
                        <td>${expense.name}</td>
                        <td>${expense.category}</td>
                        <td>₹${Number(expense.amount).toFixed(2)}</td>
                    </tr>
                `).join("");
            };

            document.getElementById("filterHistoryButton").addEventListener("click", renderHistory);
            document.getElementById("clearHistoryFilterButton").addEventListener("click", () => {
                dateInput.value = "";
                renderHistory();
            });
            renderHistory();
        })
        .catch(() => {
            document.getElementById("content").innerHTML = `
                <h2>Expense History</h2>
                <p>Unable to load expense history.</p>
            `;
        });
}


function exitApp() {
    alert("Thank you for using Expense Tracker!");
    window.close();
    window.location.replace("about:blank");
}

window.onload = showDashboard;