document.addEventListener("DOMContentLoaded", () => {
    const forgotForm = document.getElementById("forgotForm");
    const emailInput = document.getElementById("email");
    
    forgotForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const email = emailInput.value.trim();
        if (!email) {
            alert("Please enter a valid email address");
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/send-reset-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || "Failed to initiate password reset");
                return;
            }
            
            // Save email session parameter for reset password page
            sessionStorage.setItem("reset_email", email);
            
            alert("A password reset verification code has been sent to your email.");
            window.location.href = "../reset-password/reset-password.html";
            
        } catch (err) {
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
});
