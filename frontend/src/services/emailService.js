// src/services/emailService.js

function showLoading(message = "Sending verification code...") {
    let overlay = document.getElementById("loading-overlay");
    if (!overlay) {
        overlay = document.createElement("div");
        overlay.id = "loading-overlay";
        overlay.className = "loading-overlay";
        
        const spinner = document.createElement("div");
        spinner.className = "loading-spinner";
        overlay.appendChild(spinner);
        
        const text = document.createElement("div");
        text.className = "loading-text";
        text.id = "loading-overlay-text";
        overlay.appendChild(text);
        
        document.body.appendChild(overlay);
    }
    document.getElementById("loading-overlay-text").textContent = message;
    overlay.style.display = "flex";
}

function hideLoading() {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) {
        overlay.style.display = "none";
    }
}

async function sendOtpEmail(email, otp, purpose) {
    console.log("sendOtpEmail() called via EmailJS", { email, otp, purpose });
    const lib = (typeof emailjs !== "undefined") ? emailjs : (window.emailjs || null);
    if (!lib) {
        throw new Error("EmailJS library not loaded");
    }
    return lib.send(
        "service_1z4c9yt",
        "template_6dqkjdq",
        {
            email: email,
            otp: otp,
            purpose: purpose
        },
        "wpuAKweZzqpIwzRAS"
    );
}

// Export if module environment
if (typeof module !== "undefined" && module.exports) {
    module.exports = { sendOtpEmail, showLoading, hideLoading };
}
