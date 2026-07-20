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
}

function registerEventListeners() {
    const form = document.getElementById("add-product-form");
    const backButton = document.getElementById("back-btn");
    if (form) {
        form.addEventListener("submit", submitProduct);
    }
    if (backButton) {
        backButton.addEventListener("click", goBack);
    }
}

async function submitProduct(event) {
    event.preventDefault();

    const part_name = document.getElementById("part-name").value.trim();
    const description = document.getElementById("description").value.trim();
    const warehouse_stock = Number(document.getElementById("stock").value);
    const min_threshold = Number(document.getElementById("threshold").value);

    try {
        const response = await fetch("http://localhost:5000/api/inventory/items", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                part_name,
                description,
                warehouse_stock,
                min_threshold,
                floor_stock: 0
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to create inventory item");
        }

        alert(`Inventory item created!\n\nID: ${data.component_id}`);
        goBack();
    } catch (error) {
        alert(error.message);
    }
}

function goBack() {
    window.location.href = "../warehouse-stock/warehouse-stock.html";
}