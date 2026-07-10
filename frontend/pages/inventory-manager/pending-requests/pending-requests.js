document.addEventListener("DOMContentLoaded", () => {
    initializePage();
});

function initializePage() {
    registerEventListeners();
}

function registerEventListeners() {
    document.querySelectorAll(".approve-btn").forEach(button => {
        button.addEventListener("click", approveRequest);
    });
    document.querySelectorAll(".dispatch-btn").forEach(button => {
        button.addEventListener("click", dispatchComponents);
    });
}

function approveRequest(event) {
    const row = event.target.closest("tr");
    console.log("Approve request:", row);
}

function dispatchComponents(event) {
    const row = event.target.closest("tr");
    console.log("Dispatch production request:", row);
}

