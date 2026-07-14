document.addEventListener("DOMContentLoaded",()=>{
    initializePage();
});

function initializePage(){
    registerEventListeners();
}
function registerEventListeners(){
    const backButton = document.getElementById("back-btn");
    backButton.addEventListener("click", goBack);
}
function goBack(){
    window.location.href = "../warehouse-stock/warehouse-stock.html";
}