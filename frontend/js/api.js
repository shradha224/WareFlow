console.log("api.js loaded");
async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem("token");
    const headers = {
        "Content-Type": "application/json",
        ...options.headers
    };
    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(API_BASE_URL + endpoint, {
        ...options,
        headers
    });
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "API Request Failed");
    }
    return data;
}

async function checkBackendConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log("Backend Connected:", data);
    }
    catch (error) {
        console.error("Backend Offline:", error);
    }
}
checkBackendConnection();