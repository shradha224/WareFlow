document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    loadTransfers();
}

async function loadTransfers() {
    try {
        const response = await fetch(API_BASE_URL + "/transfers", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load transfers");
        }

        const tbody = document.getElementById("intake-table-body");
        if (tbody) {
            tbody.innerHTML = "";
            const transfers = data.transfers;
            if (transfers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No materials currently in transit to floor.</td></tr>';
            } else {
                transfers.forEach(tr => {
                    const row = document.createElement("tr");
                    row.innerHTML = `
                        <td>TRF-${tr.transfer_id}</td>
                        <td>${tr.component_id}</td>
                        <td><strong>${tr.part_name}</strong></td>
                        <td><strong>${tr.dispatched_qty} units</strong></td>
                        <td>
                            <button class="receive-btn primary-btn" onclick="receiveTransfer(${tr.transfer_id})">Received</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            }
        }
    } catch (error) {
        console.error("Error loading transfers:", error);
    }
}

window.receiveTransfer = async function(transferId) {
    try {
        const response = await fetch(`http://localhost:5000/api/transfers/${transferId}/verify`, {
            method: "PATCH",
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to verify receipt");
        }
        alert(data.message);
        initializePage();
    } catch (error) {
        alert(error.message);
    }
};
