document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    loadPendingRequests();
    loadProductionRequests();
}

async function loadPendingRequests() {
    try {
        const response = await fetch("http://localhost:5000/api/material-requests", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load material requests");
        }

        const tbody = document.querySelector(".pending-table tbody");
        if (tbody) {
            tbody.innerHTML = "";
            // Filter only Pending requests to review
            const pendingRequests = data.requests.filter(r => r.status === "Pending");
            if (pendingRequests.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No pending material requests.</td></tr>';
            } else {
                pendingRequests.forEach(req => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>${req.component_id}</td>
                        <td>${req.part_name}</td>
                        <td><strong>${req.requested_qty} units</strong></td>
                        <td>
                            <div class="action-buttons">
                                <button class="approve-btn primary-btn" onclick="approveRequest(${req.request_id})">Approve & Fulfill</button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch (error) {
        console.error("Error loading pending requests:", error);
    }
}

async function loadProductionRequests() {
    try {
        const response = await fetch("http://localhost:5000/api/batches/active", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load production batches");
        }

        const tbody = document.querySelector(".production-table tbody");
        if (tbody) {
            tbody.innerHTML = "";
            const batches = data.batches;
            if (batches.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No active production requests.</td></tr>';
            } else {
                batches.forEach(batch => {
                    const row = document.createElement("tr");
                    const dateStr = new Date(batch.created_at).toLocaleString();
                    const canDispatch = batch.status === "Initialized";
                    const statusClass = canDispatch ? "warning" : "normal";

                    row.innerHTML = `
                        <td>${batch.batch_id}</td>
                        <td>${batch.product_name}</td>
                        <td>${batch.target_qty} units</td>
                        <td>${dateStr}</td>
                        <td>
                            <span class="status ${statusClass}">${batch.status}</span>
                        </td>
                        <td>
                            ${canDispatch 
                                ? `<button class="dispatch-btn primary-btn" onclick="dispatchcomponents('${batch.batch_id}')">Dispatch</button>`
                                : `<button class="dispatch-btn primary-btn" disabled style="background: #ccc; cursor: not-allowed;">Dispatched</button>`
                            }
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch (error) {
        console.error("Error loading production requests:", error);
    }
}

window.approveRequest = async function(requestId) {
    try {
        const response = await fetch(`http://localhost:5000/api/material-requests/${requestId}`, {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({ action: "fulfil" })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to fulfill request");
        }
        alert(data.message);
        initializePage();
    } catch (error) {
        alert(error.message);
    }
};

window.dispatchcomponents = async function(batchId) {
    try {
        const response = await fetch(`http://localhost:5000/api/batches/${batchId}/dispatch`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to dispatch materials");
        }
        alert(data.message);
        initializePage();
    } catch (error) {
        alert(error.message);
    }
};
