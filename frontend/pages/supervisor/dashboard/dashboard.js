let activeBatchIds = new Set();
let lastBatchProgress = [];
const completedBatchesRetention = new Map(); // batch_id -> { product_name, completedAt }

document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
    // Poll the dashboard data every 3 seconds to keep it updated in real-time
    setInterval(loadDashboard, 3000);
});

async function loadDashboard() {
    try {
        const data = await apiRequest("/dashboard/supervisor");
        document.getElementById("active-alert-count").textContent =
            data.active_alerts.count;
        document.getElementById("pending-request-count").textContent =
            data.pending_requests;
        const pass = data.qc_pass_percentage !== null ? data.qc_pass_percentage : 0;
        document.getElementById("qc-pass").textContent = Number(pass).toFixed(2) + "%";
        document.getElementById("qc-fail").textContent = (100 - Number(pass)).toFixed(2) + "%";
   
        const newActiveBatchIds = new Set(data.batch_progress.map(b => b.batch_id));

        for (const oldId of activeBatchIds) {
            if (!newActiveBatchIds.has(oldId)) {
                const prevBatch = lastBatchProgress.find(b => b.batch_id === oldId);
                const pName = prevBatch ? prevBatch.product_name : "Product";
                if (!completedBatchesRetention.has(oldId)) {
                    completedBatchesRetention.set(oldId, {
                        product_name: pName,
                        completedAt: Date.now()
                    });
                }
            }
        }
 
        data.batch_progress.forEach(batch => {
            if (batch.status === 'Complete' || batch.percent_complete >= 100) {
                if (!completedBatchesRetention.has(batch.batch_id)) {
                    completedBatchesRetention.set(batch.batch_id, {
                        product_name: batch.product_name,
                        completedAt: Date.now()
                    });
                }
            }
        });
        
        activeBatchIds = newActiveBatchIds;
        lastBatchProgress = data.batch_progress;
   
        const now = Date.now();
        for (const [bid, info] of completedBatchesRetention.entries()) {
            if (now - info.completedAt > 45000) {
                completedBatchesRetention.delete(bid);
            }
        }
       
        const displayList = [];
        data.batch_progress.forEach(batch => {
            if (batch.status !== 'Complete' && batch.percent_complete < 100) {
                displayList.push({
                    batch_id: batch.batch_id,
                    product_name: batch.product_name,
                    percent_complete: batch.percent_complete
                });
            }
        });
        
        for (const [bid, info] of completedBatchesRetention.entries()) {
            displayList.push({
                batch_id: bid,
                product_name: info.product_name,
                percent_complete: 100.0
            });
        }
        
        const progressList = document.getElementById("batches-progress-list");
        if (progressList) {
            progressList.innerHTML = "";
            if (displayList.length === 0) {
                progressList.innerHTML = `<p style="color: #666; font-style: italic; margin-top: 10px;">No active batches.</p>`;
            } else {
                displayList.forEach(batch => {
                    progressList.innerHTML += `
                    <div style="margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span class="batch-id" style="font-weight: bold; margin-bottom: 0;">${batch.batch_id} (${batch.product_name})</span>
                            <span class="progress-text" style="font-weight: bold; margin-top: 0;">${batch.percent_complete}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${batch.percent_complete}%;"></div>
                        </div>
                    </div>
                    `;
                });
            }
        }

        const tbody = document.getElementById("workload-body");
        tbody.innerHTML = "";
        data.workload_summary.forEach(item => {
            tbody.innerHTML += `
            <tr>
                <td>${item.component_id}</td>
                <td>${item.part_name}</td>
                <td class="blue-text">
                    ${item.quantity_consumed}
                </td>
                <td>${item.stage_name}</td>
            </tr>
            `;
        });
        const alerts = document.getElementById("alerts-container");
        alerts.innerHTML = "";
        data.active_alerts.items.forEach(item => {
            if (item.is_fg_alert) {
                alerts.innerHTML += `
                <div class="alert-box">
                    <p>
                    Finished Product Ready for Final QC: Batch ${item.batch_id}
                    </p>
                </div>
                `;
            } else {
                alerts.innerHTML += `
                <div class="alert-box">
                    <p>
                    ${item.part_name} is below minimum stock.
                    </p>
                    <button
                        class="place-order-btn"
                        onclick="placeOrder('${item.component_id}')">
                        Place Order
                    </button>
                </div>
                `;
            }
        });
        console.log(data.demand_forecasts);
        drawChart(data.demand_forecasts);
    }
    catch (error) {
        console.error(error);
    }
}

async function placeOrder(componentId) {
    try {
        const response = await apiRequest(
            "/dashboard/supervisor/place-order",
            {
                method: "POST",
                body: JSON.stringify({
                    component_id: componentId
                })
            }
        );
        loadDashboard();
    }
    catch (error) {
        alert(error.message);
    }
}

function drawChart(forecasts) {
    const ctx = document.getElementById("demandChart");

    const chartTitle = document.querySelector(".chart-card h2");
    if (chartTitle) {
        chartTitle.textContent = "Demand Prediction (Next 7 Days)";
    }

    if (window.demandChartInstance) {
        window.demandChartInstance.data.labels = forecasts.map(f => f.part_name);
        window.demandChartInstance.data.datasets[0].data = forecasts.map(f => f.predicted_demand_qty);
        window.demandChartInstance.update();
    } else {
        window.demandChartInstance = new Chart(ctx, {
            type: "bar",
            data: {
                labels: forecasts.map(f => f.part_name),
                datasets: [{
                    label: "Projected Quantity (Next 7 Days)",
                    data: forecasts.map(f => f.predicted_demand_qty)
                }]
            }
        });
    }
}