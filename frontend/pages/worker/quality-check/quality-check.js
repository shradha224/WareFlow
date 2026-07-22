let selectedStatus = null;

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    replaceInputWithSelect();
    loadPendingQCBatches();
    registerEventListeners();
}

function replaceInputWithSelect() {
    const select = document.getElementById("productId");
    if (select) {
        select.addEventListener("change", () => {
            const selectedOpt = select.options[select.selectedIndex];
            const pName = selectedOpt ? selectedOpt.dataset.productName || "" : "";
            const bId = selectedOpt ? selectedOpt.dataset.batchId || "" : "";
            
            const displayBatch = document.getElementById("display-batch-id");
            if (displayBatch) displayBatch.textContent = bId || "--";
            
            const displayProduct = document.getElementById("display-product-name");
            if (displayProduct) displayProduct.textContent = pName || "--";
        });
    }
}

async function loadPendingQCBatches() {
    const select = document.getElementById("productId");
    if (!select) return;
    select.innerHTML = '<option value="">Select Product ID</option>';
    try {
        const response = await fetch(API_BASE_URL + "/qc/pending-batches", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load pending batches");
        }
        data.batches.forEach(b => {
            const option = document.createElement("option");
            option.value = b.finished_good_id;
            option.textContent = b.finished_good_id;
            option.dataset.batchId = b.batch_id;
            option.dataset.productName = b.product_name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error("Error loading pending batches:", error);
    }
}

function registerEventListeners() {
    const failBtn = document.querySelector(".fail-btn");
    const passBtn = document.querySelector(".pass-btn");
    const form = document.getElementById("qualityForm");

    if (failBtn) {
        failBtn.addEventListener("click", () => selectStatus("Fail", failBtn));
    }
    if (passBtn) {
        passBtn.addEventListener("click", () => selectStatus("Pass", passBtn));
    }
    if (form) {
        form.addEventListener("submit", submitQCResult);
    }
}

function selectStatus(status, btnElement) {
    selectedStatus = status;
    document.querySelectorAll(".status-btn").forEach(btn => btn.classList.remove("active"));
    btnElement.classList.add("active");
}

async function submitQCResult(event) {
    event.preventDefault();

    const productId = document.getElementById("productId").value.trim();

    if (!productId) {
        alert("Please select a Product ID");
        return;
    }

    if (!selectedStatus) {
        alert("Please select Pass or Fail");
        return;
    }

    try {
        const response = await fetch(API_BASE_URL + "/qc/finished-good", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                productId: productId,
                result: selectedStatus
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to submit QC result");
        }

        alert(`QC Result Recorded!\n\nID: ${productId}\nStatus: ${selectedStatus}`);
        document.getElementById("productId").value = "";
        
        const displayBatch = document.getElementById("display-batch-id");
        if (displayBatch) displayBatch.textContent = "--";
        
        const displayProduct = document.getElementById("display-product-name");
        if (displayProduct) displayProduct.textContent = "--";

        selectedStatus = null;
        document.querySelectorAll(".status-btn").forEach(btn => btn.classList.remove("active"));
        initializePage();
    } catch (error) {
        alert(error.message);
    }
}
