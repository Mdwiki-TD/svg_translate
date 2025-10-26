const STATUS_CLASSES = {
    "Completed": "success",
    "Failed": "danger",
    "Skipped": "warning",
    "Running": "primary",
    "Pending": "secondary",
    "Cancelled": "warning",
    "error": "danger"
};

function overall_progress(stages_obj) {
    const total = stages_obj.length;
    if (!total) return 0;
    const done = stages_obj.filter(([_, st]) => st.status === "Completed").length;
    return Math.round((done / total) * 100);
}

function formatStageTimestamp(updatedAtRaw) {
    if (!updatedAtRaw) {
        return '';
    }

    const date = new Date(updatedAtRaw);
    if (Number.isNaN(date.valueOf())) {
        return '';
    }

    try {
        return date.toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
        });
    } catch (err) {
        // Fallback for browsers that don't support dateStyle/timeStyle options
        return date.toLocaleString();
    }
}

function stages_html_new(st, name) {
    const subname = st.sub_name ? ` <small class="text-muted">(${st.sub_name})</small>` : '';
    const color = STATUS_CLASSES[st.status] || "secondary";
    const percent = st.status === "Completed" ? 100 : st.status === "Running" ? 60 : st.status === "Pending" ? 10 : 0;

    const cls = st.status === "Running" ? "running" : "";

    const messageHtml = st.message ? `<div class="small text-muted">${st.message}</div>` : '';
    const timestamp = formatStageTimestamp(st.updated_at);
    const timestampHtml = timestamp ? `<div class="stage-timestamp text-muted">Updated: ${timestamp}</div>` : '';
    const infoSection = (messageHtml || timestampHtml)
        ? `<div class="stage-card-body">${messageHtml}${timestampHtml}</div>`
        : '';

    return `
        <li class="list-group-item ${cls} border border-${color}">
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="fw-bold">${name}${subname}</span>
                <span class="badge text-bg-${color} border border-${color}">${st.status}</span>
            </div>
            ${infoSection}
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
    const cancelBtn = document.getElementById('cancel-task-btn');
    const restartBtn = document.getElementById('restart-task-btn');
    const taskStatus = document.getElementById('task_status');
    const alertDiv = document.getElementById('alert_div');
    const lastUpdate = document.getElementById('last-update');
    const STOP_STATUSES = new Set(['Completed', 'Failed', 'Cancelled', 'error']);
    const RESTART_STATUSES = new Set(['Completed', 'Failed', 'Cancelled']);
    let timer = null;

    function statusBadge(status) {
        if (!status) {
            return '';
        }
        const color = STATUS_CLASSES[status] || 'secondary';
        return `<span class="badge text-bg-${color}">${status}</span>`;
    }

    function updateStatus(status) {
        if (!taskStatus) return;
        const normalizedStatus = status || '';
        taskStatus.dataset.status = normalizedStatus;
        if (!normalizedStatus) {
            taskStatus.innerHTML = '';
            return;
        }
        taskStatus.innerHTML = statusBadge(normalizedStatus);
    }

    function updateControls(status) {
        const normalizedStatus = status || '';
        if (cancelBtn) {
            cancelBtn.classList.toggle('d-none', STOP_STATUSES.has(normalizedStatus));
            cancelBtn.disabled = false;
        }
        if (restartBtn) {
            restartBtn.classList.toggle('d-none', !RESTART_STATUSES.has(normalizedStatus));
            restartBtn.disabled = false;
        }
    }

    function showAlert(kind, message) {
        if (!alertDiv) return;
        alertDiv.innerHTML = `
            <div class="alert alert-${kind}" role="alert">
                ${message}
            </div>
        `;
    }

    const initialStatus = taskStatus?.dataset.status || '';
    if (initialStatus) {
        updateStatus(initialStatus);
    }
    updateControls(initialStatus);

    async function refresh() {
        try {
            const res = await fetch(`/status/${taskId}`, { cache: "no-store" });
            const taskData = await res.json();
            if (!res.ok) {
                if (taskData?.error === 'not-found') {
                    if (taskStatus) {
                        taskStatus.innerHTML = '<span class="badge text-bg-danger">Not Found</span>';
                    }
                    if (cancelBtn) {
                        cancelBtn.classList.add('d-none');
                    }
                    if (restartBtn) {
                        restartBtn.classList.add('d-none');
                    }
                    showAlert('danger', 'Task not found.');
                    if (timer) {
                        clearInterval(timer);
                    }
                }
                return;
            }

            const stagesContainerNew = document.getElementById('stagesnew');
            const stages = (taskData.data?.stages) || taskData.stages || {};
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
                updateStatus(taskData.status);
            } else {
                updateStatus('');
            }

            updateControls(taskData.status);

            if (taskData.status && STOP_STATUSES.has(taskData.status)) {
                if (timer) {
                    clearInterval(timer);
                }
            }

            if (lastUpdate) {
                lastUpdate.innerHTML = `Last updated: ${new Date().toLocaleTimeString()}`;
            }

        } catch (e) { /* ignore transient errors */ }
    }

    timer = setInterval(refresh, 2000);
    refresh();

    if (cancelBtn) {
        cancelBtn.addEventListener('click', async (event) => {
            event.preventDefault();
            if (cancelBtn.disabled) {
                return;
            }
            if (timer) {
                clearInterval(timer);
            }
            cancelBtn.disabled = true;
            showAlert('info', 'Stopping task...');
            let message = 'Unable to cancel the task.';
            let showmessage = true;
            try {
                const response = await fetch(`/tasks/${taskId}/cancel`, { method: 'POST' });
                let result = await response.json();
                if (result && result.error) {
                    throw new Error(result.error);
                }
                if (!response.ok) {
                    console.error("error:", result);
                    throw new Error('Failed to stop task');
                }
                if (result.status == "Cancelled") {
                    updateStatus('Cancelled');
                    updateControls('Cancelled');
                    showmessage = false;
                }
                showAlert('success', 'Task cancelled successfully.');
            } catch (error) {
                console.error("error:", error);
                message += ` (${error})`;
            }
            if (showmessage) {
                cancelBtn.disabled = false;
                showAlert('danger', message);
                timer = setInterval(refresh, 2000);
            }
        });
    }

    if (restartBtn) {
        restartBtn.addEventListener('click', async (event) => {
            event.preventDefault();
            if (restartBtn.disabled) {
                return;
            }
            if (timer) clearInterval(timer);

            restartBtn.disabled = true;
            showAlert('info', 'Restarting task...');

            let message = 'Unable to restart the task.';
            let showmessage = true;

            try {
                const response = await fetch(`/tasks/${taskId}/restart`, { method: 'POST' });
                let data = await response.json();
                if (data && data.error) {
                    throw new Error(data.error);
                }
                if (!response.ok) {
                    throw new Error('Failed to restart task');
                }
                const nextTaskId = data?.task_id;
                if (!nextTaskId) {
                    throw new Error('Missing task id');
                }
                showmessage = false;
                window.location.href = `/task2?task_id=${nextTaskId}`;
            } catch (error) {
                console.error("error:", error);
                message += ` (${error})`;
            }
            if (showmessage) {
                restartBtn.disabled = false;
                showAlert('danger', message);
                timer = setInterval(refresh, 2000);
            }
        });
    }
})();
