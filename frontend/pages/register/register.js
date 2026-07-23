document.addEventListener("DOMContentLoaded", () => {
    const registerForm = document.getElementById("registerForm");
    const userIdInput = document.getElementById("userId");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirmPassword");
    
    let userIdTimeout = null;
    let isUserIdAvailable = false;
    
    userIdInput.addEventListener("input", () => {
        clearTimeout(userIdTimeout);
        const user_id = userIdInput.value.trim();
        const statusDiv = document.getElementById("userIdStatus");
        
        if (!user_id) {
            statusDiv.textContent = "";
            statusDiv.className = "status-indicator";
            isUserIdAvailable = false;
            return;
        }
        
        statusDiv.textContent = "Checking availability...";
        statusDiv.className = "status-indicator";
        isUserIdAvailable = false;
        
        userIdTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/check-userid`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ user_id })
                });
                const data = await response.json();
                
                if (data.available) {
                    statusDiv.textContent = "Available";
                    statusDiv.className = "status-indicator status-available";
                    isUserIdAvailable = true;
                } else {
                    statusDiv.textContent = `${data.error || "User ID already exists"}`;
                    statusDiv.className = "status-indicator status-taken";
                    isUserIdAvailable = false;
                }
            } catch (err) {
                console.error(err);
                statusDiv.textContent = "Unable to verify ID availability";
                statusDiv.className = "status-indicator";
                isUserIdAvailable = false;
            }
        }, 400);
    });
   
    passwordInput.addEventListener("input", validatePasswordRequirements);
    
    function validatePasswordRequirements() {
        const password = passwordInput.value;
        const requirementsContainer = document.getElementById("passwordRequirements");
        const statusTitle = document.getElementById("password-status-title");
        const reqList = document.getElementById("requirements-list");
        const successMsg = document.getElementById("password-success-msg");

        if (!password) {
            if (requirementsContainer) {
                requirementsContainer.style.display = "none";
                requirementsContainer.classList.remove("show");
            }
            validatePasswordMatch();
            return false;
        }

        if (requirementsContainer) {
            requirementsContainer.style.display = "block";
            requirementsContainer.offsetHeight;
            requirementsContainer.classList.add("show");
        }

        const reqs = {
            length: password.length >= 8,
            upper: /[A-Z]/.test(password),
            lower: /[a-z]/.test(password),
            number: /[0-9]/.test(password),
            special: /[^A-Za-z0-9]/.test(password)
        };

        const ruleDetails = {
            length: "req-length",
            upper: "req-upper",
            lower: "req-lower",
            number: "req-number",
            special: "req-special"
        };

        let allSatisfied = true;

        for (const [key, satisfied] of Object.entries(reqs)) {
            const elId = ruleDetails[key];
            const li = document.getElementById(elId);
            if (li) {
                if (satisfied) {
                    li.style.display = "none";
                } else {
                    li.style.display = "list-item";
                    allSatisfied = false;
                }
            }
        }

        if (allSatisfied) {
            if (statusTitle) statusTitle.style.display = "none";
            if (reqList) reqList.style.display = "none";
            if (successMsg) successMsg.style.display = "block";
        } else {
            if (statusTitle) statusTitle.style.display = "block";
            if (reqList) reqList.style.display = "block";
            if (successMsg) successMsg.style.display = "none";
        }

        validatePasswordMatch();
        
        return allSatisfied;
    }
    
    confirmPasswordInput.addEventListener("input", validatePasswordMatch);
    
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
            matchDiv.textContent = "Passwords match";
            matchDiv.className = "status-indicator status-available";
            return true;
        } else {
            matchDiv.textContent = "Passwords do not match";
            matchDiv.className = "status-indicator status-taken";
            return false;
        }
    }

    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const user_id = userIdInput.value.trim();
        const full_name = document.getElementById("fullName").value.trim();
        const email = document.getElementById("email").value.trim();
        const phone_number = document.getElementById("phoneNumber").value.trim();
        const department = document.getElementById("department").value.trim();
        const user_role = document.getElementById("userRole").value;
        const password = passwordInput.value;
        const confirm_password = confirmPasswordInput.value;
        
        if (!isUserIdAvailable) {
            alert("Please choose a unique, available User ID first.");
            userIdInput.focus();
            return;
        }
        
        if (!validatePasswordRequirements()) {
            alert("Password does not meet all complexity requirements.");
            passwordInput.focus();
            return;
        }
        
        if (!validatePasswordMatch()) {
            alert("Passwords do not match.");
            confirmPasswordInput.focus();
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    user_id,
                    full_name,
                    username: "",
                    email,
                    phone_number,
                    department,
                    user_role,
                    password,
                    confirm_password
                })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                alert(data.error || "Registration failed");
                return;
            }
     
            sessionStorage.setItem("verify_email", email);
            
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

            alert("Registration details submitted! A verification code has been sent to your email.");
            window.location.href = "../email-verification/email-verification.html";
            
        } catch (err) {
            console.error(err);
            alert("Unable to connect to the server.");
        }
    });
});
