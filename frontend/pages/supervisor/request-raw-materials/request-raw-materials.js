document.addEventListener("DOMContentLoaded", () => {
    loadComponents();

    document
        .getElementById("request-material-form")
        .addEventListener("submit", submitRequest);

    document
        .getElementById("cancel-btn")
        .addEventListener("click", () => {
            document.getElementById("request-material-form").reset();
        });
});

async function loadComponents() {
    try {
        const data = await apiRequest("/components");

        console.log("Components:", data);

        const materialSelect = document.getElementById("material");

        materialSelect.innerHTML =
            '<option value="">Select Material</option>';

        data.components.forEach(component => {

            const option = document.createElement("option");

            option.value = component.component_id;

            option.textContent =
                `${component.part_name} (${component.component_id})`;

            materialSelect.appendChild(option);

        });

    } catch (error) {
        console.error("Failed to load components:", error);
    }
}

async function submitRequest(event) {

    event.preventDefault();

    const component_id =
        document.getElementById("material").value;

    const requested_qty = Number(
        document.getElementById("quantity").value
    );

    if (!component_id || requested_qty <= 0) {
        alert("Please select a material and enter a valid quantity.");
        return;
    }

    try {

        const response = await apiRequest(
            "/material-requests",
            {
                method: "POST",
                body: JSON.stringify({
                    component_id,
                    requested_qty
                })
            }
        );

        alert(
            `Request Submitted!\n\nRequest ID: ${response.request_id}`
        );

        document
            .getElementById("request-material-form")
            .reset();

    } catch (error) {
        console.error(error);
        alert(error.message);
    }
}