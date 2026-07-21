document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    registerEventListeners();
    loadInventory();
}

function registerEventListeners() {
    const addProductBtn = document.getElementById("add-product-btn");
    const addItemBtn = document.getElementById("add-item-btn");
    if (addProductBtn) {
        addProductBtn.addEventListener("click", openAddProductPage);
    }
    if (addItemBtn) {
        addItemBtn.addEventListener("click", openAddItemPage);
    }
}

function openAddProductPage() {
    window.location.href = "../add-product/add-product.html";
}

function openAddItemPage() {
    window.location.href = "../add-item/add-item.html";
}

async function loadInventory() {
    try {
        const response = await fetch(API_BASE_URL + "/inventory", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load inventory");
        }
        renderInventory(data.inventory);
    } catch (error) {
        console.error("Inventory Error:", error);
    }
}

function renderInventory(inventory) {
    const tbody = document.querySelector(".inventory-table tbody");
    if (!tbody) return;
    tbody.innerHTML = "";

    inventory.forEach(component => {
        const row = document.createElement("tr");
        const statusClass = component.stock_status === "Low" ? "warning" : "normal";
        const statusText = component.stock_status === "Low" ? "Low" : "Normal";

        row.innerHTML = `
            <td>${component.component_id}</td>
            <td>${component.part_name}</td>
            <td>${component.warehouse_stock} units</td>
            <td>${component.min_threshold} units</td>
            <td><span class="status ${statusClass}">${statusText}</span></td>
        `;
        tbody.appendChild(row);
    });
}
