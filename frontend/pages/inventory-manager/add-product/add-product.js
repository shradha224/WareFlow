let addedcomponents = [];
let addedStages = [];

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    registerEventListeners();
    loadcomponents();
    renderAddedStages();
}

function registerEventListeners() {
    const addCompBtn = document.getElementById("add-component-btn");
    const addStageBtn = document.getElementById("add-stage-btn");
    const form = document.getElementById("add-product-form");
    const backBtn = document.getElementById("go-back-btn");

    if (addCompBtn) {
        addCompBtn.addEventListener("click", addComponentToList);
    }
    if (addStageBtn) {
        addStageBtn.addEventListener("click", addStageToWorkflow);
    }
    if (form) {
        form.addEventListener("submit", submitProduct);
    }
    if (backBtn) {
        backBtn.addEventListener("click", goBack);
    }
}


async function loadcomponents() {
    try {
        const response = await fetch(API_BASE_URL + "/components", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load components");
        }

        const select = document.getElementById("component-select");
        if (select) {
            select.innerHTML = '<option value="">Select Component</option>';
            data.components.forEach(comp => {
                const opt = document.createElement("option");
                opt.value = comp.component_id;
                opt.dataset.name = comp.part_name;
                opt.textContent = `${comp.part_name} (${comp.component_id})`;
                select.appendChild(opt);
            });
        }
    } catch (error) {
        console.error("Error loading components:", error);
    }
}

function addComponentToList() {
    const select = document.getElementById("component-select");
    const qtyInput = document.getElementById("component-qty");

    const component_id = select.value;
    const qty = Number(qtyInput.value);

    if (!component_id || qty <= 0) {
        alert("Select a valid component and quantity");
        return;
    }

    const selectedOption = select.options[select.selectedIndex];
    const part_name = selectedOption.dataset.name;

    if (addedcomponents.some(c => c.component_id === component_id)) {
        alert("Component already added");
        return;
    }

    addedcomponents.push({
        component_id,
        part_name,
        quantity_required: qty
    });

    qtyInput.value = "";
    select.value = "";

    renderAddedcomponents();
}

window.removeComponent = function(index) {
    addedcomponents.splice(index, 1);
    renderAddedcomponents();
};

function renderAddedcomponents() {
    const listDiv = document.getElementById("component-list");
    if (!listDiv) return;
    listDiv.innerHTML = "";

    addedcomponents.forEach((item, index) => {
        listDiv.innerHTML += `
            <div class="added-component-item" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; background: #f3f5f7; padding: 8px 12px; border-radius: 8px;">
                <span><strong>${item.part_name}</strong> &times; ${item.quantity_required} units</span>
                <button type="button" onclick="removeComponent(${index})" style="background: #C62828; color: white; padding: 4px 8px; border: none; border-radius: 4px; cursor: pointer;">Remove</button>
            </div>
        `;
    });
}

function addStageToWorkflow() {
    const stageInput = document.getElementById("stage-name-input");
    const stageName = stageInput.value.trim();

    if (!stageName) {
        alert("Please enter a stage name");
        return;
    }

    if (addedStages.includes(stageName)) {
        alert("Stage already added to workflow");
        return;
    }

    addedStages.push(stageName);
    stageInput.value = "";
    renderAddedStages();
}

window.removeStageFromWorkflow = function(index) {
    addedStages.splice(index, 1);
    renderAddedStages();
};

window.moveStageUp = function(index) {
    if (index > 0) {
        const temp = addedStages[index];
        addedStages[index] = addedStages[index - 1];
        addedStages[index - 1] = temp;
        renderAddedStages();
    }
};

window.moveStageDown = function(index) {
    if (index < addedStages.length - 1) {
        const temp = addedStages[index];
        addedStages[index] = addedStages[index + 1];
        addedStages[index + 1] = temp;
        renderAddedStages();
    }
};

function renderAddedStages() {
    const listDiv = document.getElementById("stage-list");
    if (!listDiv) return;
    listDiv.innerHTML = "";

    if (addedStages.length === 0) {
        listDiv.innerHTML = '<p style="color: #999; font-size: 16px; margin: 0; padding: 10px;">No stages defined yet. Please add stages to configure the workflow.</p>';
        return;
    }

    addedStages.forEach((stageName, index) => {
        listDiv.innerHTML += `
            <div class="added-stage-item" style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; background: #f3f5f7; padding: 8px 12px; border-radius: 8px;">
                <span><strong>Stage ${index + 1}:</strong> ${stageName}</span>
                <div style="display: flex; gap: 8px;">
                    <button type="button" onclick="moveStageUp(${index})" style="background: #e0e0e0; color: #333; padding: 4px 8px; border: none; border-radius: 4px; cursor: pointer;" ${index === 0 ? 'disabled style="opacity: 0.5; cursor: default;"' : ''}>▲</button>
                    <button type="button" onclick="moveStageDown(${index})" style="background: #e0e0e0; color: #333; padding: 4px 8px; border: none; border-radius: 4px; cursor: pointer;" ${index === addedStages.length - 1 ? 'disabled style="opacity: 0.5; cursor: default;"' : ''}>▼</button>
                    <button type="button" onclick="removeStageFromWorkflow(${index})" style="background: #C62828; color: white; padding: 4px 8px; border: none; border-radius: 4px; cursor: pointer;">Remove</button>
                </div>
            </div>
        `;
    });
}

async function submitProduct(event) {
    event.preventDefault();

    const product_name = document.getElementById("product-name").value.trim();

    if (!product_name) {
        alert("Please enter a product name");
        return;
    }

    if (addedcomponents.length === 0) {
        alert("Please add at least one component to the mapping");
        return;
    }

    if (addedStages.length === 0) {
        alert("Please add at least one manufacturing stage to define the product workflow");
        return;
    }

    try {
        const response = await fetch(API_BASE_URL + "/products", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                product_name,
                description: `Automatically created with ${addedcomponents.length} components`,
                components: addedcomponents.map(c => ({
                    component_id: c.component_id,
                    quantity_required: c.quantity_required
                })),
                stages: addedStages
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to create product");
        }

        alert(`Product created successfully!\n\nID: ${data.product_id}`);
        goBack();
    } catch (error) {
        alert(error.message);
    }
}

function goBack() {
    window.location.href = "../warehouse-stock/warehouse-stock.html";
}