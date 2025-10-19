

function overall_progress(stages_obj) {
    const total = stages_obj.length;
    if (!total) return 0;
    const done = stages_obj.filter(([_, st]) => st.status === "Completed").length;
    return Math.round((done / total) * 100);
}

function stages_html_new(st, name) {
    const subname = st.sub_name ? ` <small class="text-muted">(${st.sub_name})</small>` : '';
    const classes = {
        "Completed": "success",
        "Failed": "danger",
        "Skipped": "warning",
        "Running": "primary",
        "Pending": "secondary"
    };
    const color = classes[st.status] || "secondary";
    const percent = st.status === "Completed" ? 100 : st.status === "Running" ? 60 : st.status === "Pending" ? 10 : 0;

    const cls = st.status === "Running" ? "running" : "";

    return `
        <li class="list-group-item ${cls} border border-${color}">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="fw-bold">${name}${subname}</span>
                <span class="badge text-bg-${color} border border-${color}">${st.status}</span>
            </div>
            <div class="small text-muted">${st.message || ''}</div>
            <div class="progress mt-2" style="height: 6px;">
                <div class="progress-bar bg-${color}" style="width:${percent}%"></div>
            </div>
        </li>
        `;
}

function result_html(r) {
    return `
        <h3 class="h6">Summary</h3>
        <ul class="list-group">
        <li class="list-group-item">Total files: ${r.total_files}</li>
        <li class="list-group-item">Ready to upload: ${r.files_to_upload_count}</li>
        <li class="list-group-item">No file path: ${r.no_file_path}</li>
        <li class="list-group-item">Nested files: ${r.injects_result.nested_files}</li>
        <li class="list-group-item">New translations: ${r.new_translations_count}</li>
        </ul>
    `
}

(function () {
    const section = document.getElementById('progress-section');
    if (!section) return;
    const taskId = section.getAttribute('data-task-id');

    async function refresh() {
        try {
            const res = await fetch(`/status/${taskId}`, { cache: "no-store" });
            const taskData = await res.json();
            if (!res.ok) {
                if (taskData?.error === 'not-found') {
                    document.getElementById("task_status").innerText = " (Not Found)";
                    document.getElementById("alert_div").innerHTML = `
                            <div class="alert alert-danger" role="alert">
                                Task not found.
                            </div>
                        `;
                    clearInterval(timer);
                }
                return;
            }

            const stagesContainerNew = document.getElementById('stagesnew');
            const stages = taskData.data.stages || taskData.stages || {};
            if (stages) {
                const stages_obj = Object.entries(stages).sort((a, b) => (a[1].number || 0) - (b[1].number || 0));
                document.getElementById("global-progress").style.width = `${overall_progress(stages_obj)}%`;
                stagesContainerNew.innerHTML = stages_obj.map(([name, st]) => stages_html_new(st, name)).join('');
            }

            const results = document.getElementById('results');
            if (taskData && taskData.results && results) {
                const r = taskData.results;
                results.innerHTML = result_html(r);
            }

            if (taskData.status) {
                document.getElementById("task_status").innerText = ` (${taskData.status})`;
            }

            if (['Completed', 'error', 'Failed'].includes(taskData.status)) {
                clearInterval(timer);
            }

            document.getElementById('last-update').innerHTML = `Last updated: ${new Date().toLocaleTimeString()}`;

        } catch (e) { /* ignore transient errors */ }
    }

    const timer = setInterval(refresh, 2000);
    refresh();
})();
