document.addEventListener("DOMContentLoaded", () => {
    loadDashboard();
});
async function loadDashboard() {
    try {
        const data = await apiRequest("/dashboard/supervisor");
        document.getElementById("active-alert-count").textContent =
            data.active_alerts.count;
        document.getElementById("pending-request-count").textContent =
            data.pending_requests;
        const pass = data.qc_pass_percentage || 0;
        document.getElementById("qc-pass").textContent = pass + "%";
        document.getElementById("qc-fail").textContent = (100-pass) + "%";
        if(data.batch_progress.length>0){
            const batch=data.batch_progress[0];
            document.getElementById("batch-id").textContent=batch.batch_id;
            document.getElementById("progress-text").textContent=
                batch.percent_complete+"%";
            document.getElementById("progress-fill").style.width=
                batch.percent_complete+"%";
        }
        const tbody=document.getElementById("workload-body");
        tbody.innerHTML="";
        data.workload_summary.forEach(item=>{
            tbody.innerHTML+=`
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
        const alerts=document.getElementById("alerts-container");
        alerts.innerHTML="";
        data.active_alerts.items.forEach(item=>{
            alerts.innerHTML+=`
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
        });
        console.log(data.demand_forecasts);
        drawChart(data.demand_forecasts);
    }
    catch(error){
        console.error(error);
    }
}

async function placeOrder(componentId){
    const qty=prompt("Enter quantity to order");
    if(!qty) return;
    try{
        const response=await apiRequest(
            "/dashboard/supervisor/place-order",
            "POST",
            {
                component_id:componentId,
                requested_qty:Number(qty)
            }
        );
        alert(response.message);
        loadDashboard();
    }
    catch(error){
        alert(error.message);
    }
}

function drawChart(forecasts){
    const ctx=document.getElementById("demandChart");
    new Chart(ctx,{
        type:"bar",
        data:{
            labels:forecasts.map(f=>f.part_name),
            datasets:[{
                label:"Predicted Demand",
                data:forecasts.map(f=>f.predicted_demand_qty)
            }]
        }
    });
}