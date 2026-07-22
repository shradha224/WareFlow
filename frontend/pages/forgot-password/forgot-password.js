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
            showLoading("Requesting password reset...");
            const response = await fetch(`${API_BASE_URL}/send-reset-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                hideLoading();
                alert(data.error || "Failed to initiate password reset");
                return;
            }
            
            sessionStorage.setItem("reset_email", email);
            
            try {
                showLoading("Sending verification email...");
                await sendOtpEmail(email, data.otp, "Password Reset");
                hideLoading();
            } catch (emailErr) {
                hideLoading();
                console.error("EmailJS failed:", emailErr);
                alert("Failed to send OTP. Please try again.");
                return;
            }
            
            alert("A password reset verification code has been sent to your email.");
            window.location.href = "../reset-password/reset-password.html";
            
        } catch (err) {
            hideLoading();
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
});
