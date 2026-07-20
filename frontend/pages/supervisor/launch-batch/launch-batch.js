document.addEventListener("DOMContentLoaded", () => {
    loadProducts();

    document
        .getElementById("initialize-btn")
        .addEventListener("click", initializeBatch);

    document
        .getElementById("stage-form")
        .addEventListener("submit", submitStages);
});

let currentBatchId = null;
let stageList = [];

async function loadProducts() {
    try {
        const products = await apiRequest("/products");

        const select = document.getElementById("product-select");

        products.forEach(product => {
            select.innerHTML += `
                <option value="${product.product_name}">
                    ${product.product_name}
                </option>
            `;
        });

    } catch (err) {
        console.error(err);
    }
}

async function initializeBatch() {

    const product = document.getElementById("product-select").value;

    const qty = Number(
        document.getElementById("overall-target").value
    );

    if (!product || !qty) {
        alert("Fill all fields");
        return;
    }

    try {

        const response = await apiRequest(
            "/batches",
            {
                method: "POST",
                body: JSON.stringify({
                    product_name: product,
                    target_qty: qty
                })
            }
        );

        currentBatchId = response.batch_id;

        alert("Batch Created\n\nBatch ID : " + currentBatchId);

        await loadBatchStages(currentBatchId);

    } catch (err) {

        alert(err.message);

    }

}

async function loadBatchStages(batchId) {
    try {
        const response = await apiRequest(`/batches/${batchId}/stages`);
        const stages = response.stages;

        const stageSelect = document.getElementById("stage-select");
        stageSelect.innerHTML = '<option value="">Choose Stage</option>';
        stages.forEach(stage => {
            stageSelect.innerHTML += `
                <option value="${stage.stage_name}">
                    ${stage.stage_name}
                </option>
            `;
        });

        stageList = stages.map(s => ({
            stage_name: s.stage_name,
            target_hours: s.target_hours,
            target_qty: s.target_qty || 0
        }));
        redrawTable();
    } catch (err) {
        console.error("Failed to load batch stages:", err);
    }
}

function addStageToTable(stage) {

    const tbody = document.getElementById("stage-table-body");

    tbody.innerHTML += `
        <tr>
            <td>${stage.stage_name}</td>
            <td>${stage.target_hours}</td>
            <td>
                <button
                    type="button"
                    onclick="removeStage('${stage.stage_name}')">
                    Remove
                </button>
            </td>
        </tr>
    `;

}

window.removeStage = function(stageName){

    stageList = stageList.filter(
        s => s.stage_name !== stageName
    );

    redrawTable();

}

function redrawTable(){

    const tbody = document.getElementById("stage-table-body");

    tbody.innerHTML = "";

    stageList.forEach(addStageToTable);

}

async function submitStages(e){

    e.preventDefault();

    if(!currentBatchId){

        alert("Initialize Batch First");

        return;

    }

    const stageName =
        document.getElementById("stage-select").value;

    const targetHours =
        Number(document.getElementById("target-time").value);

    const targetQty =
        Number(document.getElementById("overall-target").value) || 0;

    if(!stageName || !targetHours){

        alert("Fill stage details");

        return;

    }

    const existingIndex = stageList.findIndex(s => s.stage_name === stageName);
    if (existingIndex !== -1) {
        stageList[existingIndex].target_hours = targetHours;
        stageList[existingIndex].target_qty = targetQty;
    } else {
        stageList.push({
            stage_name: stageName,
            target_hours: targetHours,
            target_qty: targetQty
        });
    }

    redrawTable();

    try{

        await apiRequest(

            `/batches/${currentBatchId}/stages`,

            {

                method:"POST",

                body:JSON.stringify({

                    stages: stageList.map(s=>({

                        stage_name:s.stage_name,

                        target_hours:s.target_hours,

                        target_qty:s.target_qty

                    }))

                })

            }

        );

        alert("Stage Targets Saved");

    }

    catch(err){

        alert(err.message);

    }

}