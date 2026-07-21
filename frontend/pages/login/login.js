document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("loginForm");

    form.addEventListener("submit", loginUser);
});

async function loginUser(e) {
    e.preventDefault();

    const user_id = document.getElementById("userId").value.trim();
    const password = document.getElementById("password").value;
    console.log({
    user_id,
    password
    });
    try {
        const response = await fetch(API_BASE_URL + "/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id,
                password
            })
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error);
            return;
        }

        // Save login information
        localStorage.setItem("token", data.token);
        localStorage.setItem("role", data.user_role);
        localStorage.setItem("user_id", data.user_id);
        console.log(data.user_role);
        console.log(window.location.href);
        // Redirect according to role
        switch (data.user_role) {

            case "Supervisor":
                window.location.href =
                    "../supervisor/dashboard/dashboard.html";
                break;

            case "Inventory Inspector":
                window.location.href =
                    "../inventory-manager/warehouse-stock/warehouse-stock.html";
                break;

            case "Worker":
                window.location.href =
                    "../worker/material-intake/material-intake.html";
                break;

            default:
                alert("Unknown role");
        }

    } catch (err) {
        console.error(err);
        alert("Unable to connect to server.");
    }
}