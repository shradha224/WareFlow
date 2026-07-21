let selectedBatchId = null;

document.addEventListener("DOMContentLoaded", () => {
    const token = localStorage.getItem("token");
    if (!token) {
        window.location.href = "../../login/login.html";
        return;
    }
    initializePage();
});

function initializePage() {
    replaceComponentInputWithSelect();
    loadActiveBatches();
    registerEventListeners();
}

function replaceComponentInputWithSelect() {
    const input = document.getElementById("componentId");
    if (input && input.tagName === "INPUT") {
        const select = document.createElement("select");
        select.id = "componentId";
        select.className = input.className;
        input.parentNode.replaceChild(select, input);
    }

    if (!document.getElementById("consumption-progress")) {
        const completeBtn = document.getElementById("completeBtn");
        if (completeBtn) {
            const progressDiv = document.createElement("div");
            progressDiv.id = "consumption-progress";
            progressDiv.style.marginTop = "15px";
            progressDiv.style.fontWeight = "bold";
            progressDiv.style.color = "var(--text-color, #333)";
            completeBtn.parentNode.insertBefore(progressDiv, completeBtn.nextSibling);
        }
    }
}

async function loadcomponentsForBatch(batchId) {
    const select = document.getElementById("componentId");
    if (!select) return;
    select.innerHTML = '<option value="">Select Component</option>';
    try {
        const response = await fetch(`http://localhost:5000/api/consumption/components?batch_id=${batchId}`, {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load components");
        }
        data.components.forEach(comp => {
            const option = document.createElement("option");
            option.value = comp.component_id;
            option.textContent = `${comp.part_name} (${comp.component_id})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error("Error loading components for batch:", error);
    }
}

async function loadStagesForBatch(batchId) {
    const select = document.getElementById("stage");
    if (!select) return;
    select.innerHTML = '<option value="">Select Stage</option>';
    try {
        const response = await fetch(`http://localhost:5000/api/consumption/stages?batch_id=${batchId}`, {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load stages");
        }
        data.stages.forEach(s => {
            const option = document.createElement("option");
            option.value = s.stage_name;
            option.textContent = s.stage_name;
            select.appendChild(option);
        });
        if (data.stages.length > 0) {
            select.value = data.stages[0].stage_name;
        }
    } catch (error) {
        console.error("Error loading stages for batch:", error);
    }
}

function registerEventListeners() {
    const completeBtn = document.getElementById("completeBtn");
    if (completeBtn) {
        completeBtn.addEventListener("click", submitConsumption);
    }
}

async function loadActiveBatches() {
    try {
        const response = await fetch("http://localhost:5000/api/batches/active", {
            headers: {
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            }
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to load active batches");
        }
        renderBatchSelector(data.batches);
    } catch (error) {
        console.error("Error loading active batches:", error);
    }
}

function renderBatchSelector(batches) {
    const selector = document.querySelector(".batch-selector");
    if (!selector) return;
    selector.innerHTML = "";
    selectedBatchId = null;

    if (batches.length === 0) {
        selector.innerHTML = "<p>No active production batches.</p>";
        return;
    }

    batches.forEach((batch, index) => {
        const btn = document.createElement("button");
        btn.className = "batch-btn";
        if (index === 0) {
            btn.className += " active";
            selectedBatchId = batch.batch_id;
            loadcomponentsForBatch(batch.batch_id);
            loadStagesForBatch(batch.batch_id);
        }
        btn.dataset.batch = batch.batch_id;
        btn.textContent = batch.batch_id;
        btn.addEventListener("click", () => {
            document.querySelectorAll(".batch-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            selectedBatchId = batch.batch_id;
            loadcomponentsForBatch(batch.batch_id);
            loadStagesForBatch(batch.batch_id);
            const progressEl = document.getElementById("consumption-progress");
            if (progressEl) progressEl.innerHTML = "";
        });
        selector.appendChild(btn);
    });
}

async function submitConsumption() {
    const componentId = document.getElementById("componentId").value.trim();
    const stage = document.getElementById("stage").value;

    if (!selectedBatchId) {
        alert("Please select an active production batch");
        return;
    }
    if (!componentId) {
        alert("Please enter a component ID");
        return;
    }
    if (!stage) {
        alert("Please select a stage");
        return;
    }

    try {
        const response = await fetch("http://localhost:5000/api/consumption", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${localStorage.getItem("token")}`
            },
            body: JSON.stringify({
                batch_id: selectedBatchId,
                component_id: componentId,
                stage_name: stage,
                qty_used: null, // Let the backend lookup the BOM quantity automatically
                units_completed: 1
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to record consumption");
        }

        if (data.target_reached && data.remaining_stages && data.remaining_stages.length > 0) {
            const progressEl = document.getElementById("consumption-progress");
            if (progressEl) {
                let optionsHtml = data.remaining_stages.map(rs => `<option value="${rs}">${rs}</option>`).join("");
                progressEl.innerHTML = `
                    <div style="margin-top: 15px; border: 1px solid var(--border-color, #eee); padding: 15px; border-radius: 8px; background: var(--card-bg, #fcfcfc);">
                        <p style="color: var(--primary-color, #4f46e5); font-weight: bold; margin-bottom: 10px;">Stage completed! Send component to next stage:</p>
                        <div class="form-group" style="margin-bottom: 10px;">
                            <label>Send To Stage</label>
                            <select id="next-stage-select" style="width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--border-color, #ccc);">${optionsHtml}</select>
                        </div>
                        <button id="send-stage-btn" class="submit-btn" style="width: 100%;">Send</button>
                    </div>
                `;

                document.getElementById("send-stage-btn").addEventListener("click", async () => {
                    const nextStage = document.getElementById("next-stage-select").value;
                    if (!nextStage) return;
                    try {
                        const transResponse = await fetch(`http://localhost:5000/api/batches/${selectedBatchId}/transition`, {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json",
                                "Authorization": `Bearer ${localStorage.getItem("token")}`
                            },
                            body: JSON.stringify({
                                current_stage: stage,
                                next_stage: nextStage
                            })
                        });
                        const transData = await transResponse.json();
                        if (!transResponse.ok) {
                            throw new Error(transData.error || "Failed to transition stage");
                        }

                        alert(`Component transitioned to ${nextStage}!`);
                        document.getElementById("componentId").value = "";
                        document.getElementById("stage").value = "";
                        progressEl.innerHTML = "";
                        initializePage();
                    } catch (err) {
                        alert(err.message);
                    }
                });
            }
        } else if (data.target_reached && (!data.remaining_stages || data.remaining_stages.length === 0)) {
            document.getElementById("componentId").value = "";
            document.getElementById("stage").value = "";
            const progressEl = document.getElementById("consumption-progress");
            if (progressEl) progressEl.innerHTML = "";
            initializePage();
        } else {
            const progressEl = document.getElementById("consumption-progress");
            if (progressEl) {
                progressEl.innerHTML = `Processed Qty: ${data.completed_qty} / ${data.target_qty}`;
            }
        }
    } catch (error) {
        alert(error.message);
    }
}
