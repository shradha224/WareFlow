document.addEventListener("DOMContentLoaded", () => {
    const emailInput = document.getElementById("email");
    const otpInput = document.getElementById("otp");
    const verifyForm = document.getElementById("verifyForm");
    const resendBtn = document.getElementById("resendBtn");
    const countdownDiv = document.getElementById("countdown");

    let email = sessionStorage.getItem("verify_email");
    if (!email) {
        const urlParams = new URLSearchParams(window.location.search);
        email = urlParams.get("email");
    }
    
    if (!email) {
        alert("No active verification session. Redirecting to registration.");
        window.location.href = "../register/register.html";
        return;
    }
    
    emailInput.value = email;
    
    let cooldownSeconds = 0;
    let countdownInterval = null;
    
    function startResendCooldown() {
        cooldownSeconds = 60;
        resendBtn.disabled = true;
        
        countdownInterval = setInterval(() => {
            cooldownSeconds--;
            if (cooldownSeconds <= 0) {
                clearInterval(countdownInterval);
                resendBtn.disabled = false;
                countdownDiv.textContent = "";
            } else {
                countdownDiv.textContent = `You can request a new code in ${cooldownSeconds}s`;
            }
        }, 1000);
    }
    
    verifyForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const otp = otpInput.value.trim();
        if (otp.length !== 6 || isNaN(otp)) {
            alert("Please enter a valid 6-digit number");
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/verify-registration`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, otp })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || "Verification failed");
                return;
            }
            
            alert(data.message || "Email verified! You can now log in.");
            sessionStorage.removeItem("verify_email");
            window.location.href = "../login/login.html";
            
        } catch (err) {
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
 
    resendBtn.addEventListener("click", async () => {
        try {
            showLoading("Requesting new verification code...");
            const response = await fetch(`${API_BASE_URL}/send-registration-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                hideLoading();
                alert(data.error || "Resend failed");
                return;
            }
            
            try {
                showLoading("Sending verification email...");
                await sendOtpEmail(email, data.otp, "Registration");
                hideLoading();
            } catch (emailErr) {
                hideLoading();
                console.error("EmailJS failed:", emailErr);
                alert("Failed to send OTP. Please try again.");
                return;
            }
            
            alert(data.message || "A new verification code has been sent!");
            startResendCooldown();
            
        } catch (err) {
            hideLoading();
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
});
