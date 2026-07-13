document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm"); 
    const passwordInput = document.getElementById("password");
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userId=document.getElementById("userId").value.trim();
        const password =passwordInput.value.trim();
        if (!userId || !password) {
            alert("Please enter both User ID and Password.");
            return;
        }
        if (userId==="supervisor" && password==="1234") {
            window.location.href ="../supervisor/dashboard/dashboard.html";
            return;
        }
        if (userId==="inventory" && password==="1234") {
            window.location.href ="../inventory-manager/warehouse-stock/warehouse-stock.html";
            return;
        }

        if (userId === "worker" && password === "1234") {
            window.location.href ="../worker/component-consumption/component-consumption.html";
            return;
        }
        alert("Invalid credentials.");
    });
});