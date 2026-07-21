document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    loadPendingQC();
}

async function loadPendingQC() {
    try {
        const response = await fetch(API_BASE_URL + "/qc/pending", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load pending QC items");
        }

        const tbody = document.querySelector(".qc-table tbody");
        if (tbody) {
            tbody.innerHTML = "";
            const pendingItems = data.pending;
            if (pendingItems.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No raw materials pending quality check.</td></tr>';
            } else {
                pendingItems.forEach(item => {
                    const row = document.createElement("tr");
                    const dateStr = new Date(item.created_at).toLocaleString();

                    row.innerHTML = `
                        <td>${item.component_id}</td>
                        <td>${item.part_name}</td>
                        <td><strong>${item.requested_qty} units</strong></td>
                        <td>${dateStr}</td>
                        <td>
                            <div class="action-buttons">
                                <button class="pass-btn primary-btn" onclick="submitQC(${item.request_id}, '${item.component_id}', ${item.requested_qty}, 'Pass')">Pass</button>
                                <button class="fail-btn secondary-btn" onclick="submitQC(${item.request_id}, '${item.component_id}', ${item.requested_qty}, 'Fail')" style="border-color: #C62828; color: #C62828;">Fail</button>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch (error) {
        console.error("Error loading pending QC:", error);
    }
}

window.submitQC = async function(requestId, componentId, qtyInspected, result) {
    try {
        const response = await fetch(API_BASE_URL + "/qc/component", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                component_id: componentId,
                qty_inspected: qtyInspected,
                result: result,
                request_id: requestId
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to submit QC result");
        }

        alert(`QC Check recorded: ${result}\n\n${data.message}`);
        initializePage();
    } catch (error) {
        alert(error.message);
    }
};
