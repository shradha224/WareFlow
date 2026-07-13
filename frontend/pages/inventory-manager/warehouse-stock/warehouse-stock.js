document.addEventListener("DOMContentLoaded",()=>{
    initializePage();
});

function initializePage(){
    registerEventListeners();
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
    alert("Add Product Page...");
}

function openAddItemPage() {
    window.location.href = "../add-item/add-item.html";
}

