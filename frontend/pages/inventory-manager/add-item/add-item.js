document.addEventListener("DOMContentLoaded",()=>{
    initializePage();
});

function initializePage(){
    registerEventListeners();
}

function registerEventListeners(){
    const form = document.getElementById("add-product-form");
    const backButton = document.getElementById("back-btn");
    form.addEventListener("submit", submitProduct);
    backButton.addEventListener("click", goBack);
}

function submitProduct(event){
    alert("Product Ready To Be Sent To Backend");
}

function goBack(){
    window.location.href = "../warehouse-stock/warehouse-stock.html";
}