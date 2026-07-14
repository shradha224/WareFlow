document.addEventListener("DOMContentLoaded", () => {
    loadReports();
});

async function loadReports() {
    try {
        const data = await apiRequest("/reports");
        const stages = {};
        data.stage_metrics.forEach(stage => {
            stages[stage.stage_name.toLowerCase()] = stage;
        });

        if (stages["assembly"]) {
            document.getElementById("assembly-time").textContent =
                stages["assembly"].avg_elapsed + " h";

            document.getElementById("assembly-target").textContent =
                stages["assembly"].target_hours + " h";
        }

        if (stages["production"]) {
            document.getElementById("production-time").textContent =
                stages["production"].avg_elapsed + " h";

            document.getElementById("production-target").textContent =
                stages["production"].target_hours + " h";
        }

        const qc =
            stages["quality check"] ||
            stages["qc"];

        if (qc) {
            document.getElementById("qc-time").textContent =
                qc.avg_elapsed + " h";

            document.getElementById("qc-target").textContent =
                qc.target_hours + " h";
        }

        document.getElementById("production-output").textContent =
            data.logs.filter(log => log.log_type === "Batch Stage").length;
        const passRate =
            data.averages.avg_qc_pass_rate_percent || 0;

        document.getElementById("qc-pass").textContent =
            passRate + "%";

        document.getElementById("qc-fail").textContent =
            (100 - passRate) + "%";
        const tbody = document.getElementById("delay-body");
        tbody.innerHTML = "";

        data.logs
            .filter(log => log.log_type === "Batch Stage")
            .forEach(log => {

                const delayed =
                    log.detail.includes("Delayed");

                tbody.innerHTML += `
                <tr>
                    <td>${log.ref_id}</td>

                    <td>
                        ${log.event_time}
                    </td>

                    <td>--</td>

                    <td>
                        <span class="delay-pill">
                            ${delayed ? "Delayed" : "On Time"}
                        </span>
                    </td>
                </tr>
                `;
            });

    } catch (error) {
        console.error("Reports Error:", error);
    }
}