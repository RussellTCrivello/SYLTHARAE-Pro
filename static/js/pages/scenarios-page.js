/** Scenarios page - list, create, edit, dry-run, evaluate, archive */

(() => {
    const API = '/api/scenarios';
    const tableBody = document.getElementById('scenariosTableBody');
    const createForm = document.getElementById('createScenarioForm');
    const createModal = document.getElementById('createScenarioModal');

    function loadScenarios() {
        fetch(API)
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                renderScenarios(data.scenarios);
            })
            .catch(console.error);
    }

    function renderScenarios(scenarios) {
        if (!tableBody) return;
        tableBody.innerHTML = scenarios.map(s => `
            <tr data-id="${s.id}">
                <td>${escapeHtml(s.name)}</td>
                <td>${s.version}</td>
                <td><span class="badge bg-${statusColor(s.status)}">${s.status}</span></td>
                <td>${s.last_evaluated_at ? new Date(s.last_evaluated_at).toLocaleString() : 'Never'}</td>
                <td class="text-end">
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="viewScenario(${s.id})" title="View"><i class="bi bi-eye"></i></button>
                        <button class="btn btn-outline-secondary" onclick="dryRunScenario(${s.id})" title="Dry-run" ${s.status === 'archived' ? 'disabled' : ''}><i class="bi bi-play"></i></button>
                        <button class="btn btn-outline-success" onclick="evaluateScenario(${s.id})" title="Evaluate" ${s.status !== 'active' ? 'disabled' : ''}><i class="bi bi-check-circle"></i></button>
                        <button class="btn btn-outline-danger" onclick="archiveScenario(${s.id})" title="Archive" ${s.status === 'archived' ? 'disabled' : ''}><i class="bi bi-archive"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    }

    function statusColor(status) {
        const colors = { draft: 'secondary', active: 'success', paused: 'warning', disabled: 'danger', archived: 'dark' };
        return colors[status] || 'secondary';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function viewScenario(id) {
        window.location.href = `/scenarios/${id}`;
    }

    function dryRunScenario(id) {
        fetch(`${API}/${id}/dry-run`, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() } })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Dry-run started. Job ID: ' + data.job.job_id);
                } else {
                    alert('Error: ' + data.error.message);
                }
            })
            .catch(console.error);
    }

    function evaluateScenario(id) {
        fetch(`${API}/${id}/evaluate`, { method: 'POST', headers: { 'X-CSRFToken': getCsrfToken() } })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Evaluation started. Job ID: ' + data.job.job_id);
                } else {
                    alert('Error: ' + data.error.message);
                }
            })
            .catch(console.error);
    }

    function archiveScenario(id) {
        if (!confirm('Archive this scenario?')) return;
        fetch(`${API}/${id}`, { method: 'DELETE', headers: { 'X-CSRFToken': getCsrfToken() } })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    loadScenarios();
                } else {
                    alert('Error: ' + data.error.message);
                }
            })
            .catch(console.error);
    }

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.content : '';
    }

    // Create scenario form
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(createForm);
            const payload = {
                name: formData.get('name'),
                definition: JSON.parse(formData.get('definition') || '{}')
            };
            try {
                const res = await fetch(API, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    bootstrap.Modal.getInstance(createModal).hide();
                    createForm.reset();
                    loadScenarios();
                } else {
                    alert('Error: ' + data.error.message);
                }
            } catch (err) {
                console.error(err);
                alert('Failed to create scenario');
            }
        });
    }

    // Initialize
    document.addEventListener('DOMContentLoaded', loadScenarios);
})();