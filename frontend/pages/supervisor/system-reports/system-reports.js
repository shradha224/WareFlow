document.addEventListener("DOMContentLoaded", () => {
    loadReports();
});

async function loadReports() {
    try {
        const data = await apiRequest("/reports");
        const batchCompletion = data.average_batch_completion_hours !== undefined ? data.average_batch_completion_hours : 0;
        const stageTransition = data.average_stage_transition_hours !== undefined ? data.average_stage_transition_hours : 0;
        const finalQc = data.average_final_qc_hours !== undefined ? data.average_final_qc_hours : 0;

        document.getElementById("assembly-time").textContent =
            Number(batchCompletion).toFixed(2) + " h";

        document.getElementById("production-time").textContent =
            Number(stageTransition).toFixed(2) + " h";

        document.getElementById("qc-time").textContent =
            Number(finalQc).toFixed(2) + " h";

        // Hide target limits dynamically
        document.querySelectorAll(".metric-limit").forEach(el => {
            el.style.display = "none";
        });

        document.getElementById("production-output").textContent =
            data.production_completed_count;

        const passRate = data.averages.avg_qc_pass_rate_percent !== null ? data.averages.avg_qc_pass_rate_percent : 0;

        document.getElementById("qc-pass").textContent =
            Number(passRate).toFixed(2) + "%";

        document.getElementById("qc-fail").textContent =
            (100 - Number(passRate)).toFixed(2) + "%";

        const tbody = document.getElementById("delay-body");
        tbody.innerHTML = "";

        if (data.delay_logs && data.delay_logs.length > 0) {
            data.delay_logs.forEach(log => {
                tbody.innerHTML += `
                <tr>
                    <td>${log.stage_name}</td>
                    <td>${log.actual_time_elapsed}</td>
                    <td>${log.target_time}</td>
                    <td>
                        <span class="delay-pill ${log.delay_display === 'On Time' ? 'on-time' : 'delayed'}">
                            ${log.delay_display}
                        </span>
                    </td>
                </tr>
                `;
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No completed stages logged.</td></tr>`;
        }

    } catch (error) {
        console.error("Reports Error:", error);
    }
}