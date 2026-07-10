document.addEventListener("DOMContentLoaded", () =>{
    initializePage();
});

function initializePage(){
    registerEventListeners();
}

function registerEventListeners() {
    const passButtons= document.querySelectorAll(".pass-btn");
    const failButtons =document.querySelectorAll(".fail-btn");
    passButtons.forEach(button=>{
        button.addEventListener("click",handlePass);
    });
    failButtons.forEach(button =>{
        button.addEventListener("click",handleFail);
    });
}

function handlePass(event) {
    alert("Component Passed");
}

function handleFail(event) {
    alert("Component Failed");
}
