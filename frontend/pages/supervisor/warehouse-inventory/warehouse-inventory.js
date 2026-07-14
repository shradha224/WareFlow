document.addEventListener("DOMContentLoaded",()=> {
    loadInventory();
});
async function loadInventory() {
    try {
        const data = await apiRequest("/inventory");
        renderInventory(data.inventory);
    }
    catch (error) {
        console.error("Inventory Error:", error);
    }
}

function renderInventory(inventory) {
    const tableBody = document.getElementById("inventory-table-body");
    tableBody.innerHTML = "";
    inventory.forEach(component => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${component.component_id}</td>
            <td>${component.part_name}</td>
            <td>${component.description}</td>
            <td>${component.total_stock}</td>
            <td>${component.min_threshold}</td>
            <td>
                <span class="${component.stock_status === "Low" ? "status-low" : "status-good"}">
                    ${component.stock_status}
                </span>
            </td>
        `;
        tableBody.appendChild(row);
    });
}