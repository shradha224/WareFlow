document.addEventListener("DOMContentLoaded", () => {
    const emailInput = document.getElementById("email");
    const otpInput = document.getElementById("otp");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirmPassword");
    const resetForm = document.getElementById("resetForm");
    const resendBtn = document.getElementById("resendBtn");
    const countdownDiv = document.getElementById("countdown");
    
    // Get email from sessionStorage or URL query param
    let email = sessionStorage.getItem("reset_email");
    if (!email) {
        const urlParams = new URLSearchParams(window.location.search);
        email = urlParams.get("email");
    }
    
    if (!email) {
        alert("No active reset session. Redirecting to forgot password.");
        window.location.href = "../forgot-password/forgot-password.html";
        return;
    }
    
    emailInput.value = email;
    
    // Live validation
    passwordInput.addEventListener("input", validatePasswordRequirements);
    confirmPasswordInput.addEventListener("input", validatePasswordMatch);
    
    function validatePasswordRequirements() {
        const password = passwordInput.value;
        const reqs = {
            length: password.length >= 8,
            upper: /[A-Z]/.test(password),
            lower: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[^A-Za-z0-9]/.test(password)
        };
        
        updateRequirementUI("req-length", reqs.length, "Minimum 8 characters");
        updateRequirementUI("req-upper", reqs.upper, "One uppercase letter");
        updateRequirementUI("req-lower", reqs.lower, "One lowercase letter");
        updateRequirementUI("req-number", reqs.number, "One number");
        updateRequirementUI("req-special", reqs.special, "One special character");
        
        validatePasswordMatch();
        
        return Object.values(reqs).every(val => val === true);
    }
    
    function updateRequirementUI(elementId, isValid, labelText) {
        const element = document.getElementById(elementId);
        if (isValid) {
            element.textContent = `✅ ${labelText}`;
            element.className = "requirement valid";
        } else {
            element.textContent = `❌ ${labelText}`;
            element.className = "requirement invalid";
        }
    }
    
    function validatePasswordMatch() {
        const password = passwordInput.value;
        const confirm = confirmPasswordInput.value;
        const matchDiv = document.getElementById("passwordMatchStatus");
        
        if (!confirm) {
            matchDiv.textContent = "";
            matchDiv.className = "status-indicator";
            return false;
        }
        
        if (password === confirm) {
            matchDiv.textContent = "✅ Passwords match";
            matchDiv.className = "status-indicator status-available";
            return true;
        } else {
            matchDiv.textContent = "❌ Passwords do not match";
            matchDiv.className = "status-indicator status-taken";
            return false;
        }
    }
    
    // Manage Resend timer cooldown
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
    
    // Submit password reset
    resetForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const otp = otpInput.value.trim();
        const password = passwordInput.value;
        const confirm_password = confirmPasswordInput.value;
        
        if (otp.length !== 6 || isNaN(otp)) {
            alert("Please enter a valid 6-digit OTP code");
            return;
        }
        
        if (!validatePasswordRequirements()) {
            alert("Password does not meet complexity requirements.");
            passwordInput.focus();
            return;
        }
        
        if (!validatePasswordMatch()) {
            alert("Passwords do not match.");
            confirmPasswordInput.focus();
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email,
                    otp,
                    password,
                    confirm_password
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || "Reset password failed");
                return;
            }
            
            alert(data.message || "Password updated successfully! Redirecting to login.");
            sessionStorage.removeItem("reset_email");
            window.location.href = "../login/login.html";
            
        } catch (err) {
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
    
    // Resend reset code
    resendBtn.addEventListener("click", async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/send-reset-otp`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || "Resend failed");
                return;
            }
            
            alert(data.message || "A new reset code has been sent!");
            startResendCooldown();
            
        } catch (err) {
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
});
