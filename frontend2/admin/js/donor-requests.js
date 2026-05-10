/**
 * Admin Donor Requests Script
 * Handles reviewing, approving and rejecting donor applications
 */

let currentRequestId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initial fetch
    fetchPendingRequests();

    // Event Listeners
    const confirmRejectBtn = document.getElementById('confirmRejectBtn');
    if (confirmRejectBtn) {
        confirmRejectBtn.addEventListener('click', () => handleRejectSubmit());
    }

    // Set body as loaded
    document.body.classList.add('loaded');
});

async function fetchPendingRequests() {
    const tableBody = document.getElementById('requestsTableBody');
    if (!tableBody) return;

    try {
        const response = await API.donors.getPendingRequests();

        if (response.success && response.data) {
            const requests = response.data.pending_requests || response.data.requests || [];

            if (requests.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6" class="empty-state">
                            <i class="fa-solid fa-check-double"></i>
                            <p>No pending donor requests at the moment.</p>
                        </td>
                    </tr>
                `;
                return;
            }

            renderRequests(requests, tableBody);
        } else {
            tableBody.innerHTML = `<tr><td colspan="6" class="empty-state"><p>${response.message || 'Failed to load requests'}</p></td></tr>`;
        }
    } catch (error) {
        console.error('Error fetching pending requests:', error);
        tableBody.innerHTML = `<tr><td colspan="6" class="empty-state"><p>Error: ${error.message || 'Failed to connect to server'}</p></td></tr>`;
    }
}

function renderRequests(requests, container) {
    container.innerHTML = '';

    requests.forEach(req => {
        const tr = document.createElement('tr');

        const userName = req.name || req.email || 'Unknown';
        const initials = userName.charAt(0).toUpperCase();
        const dateStr = new Date(req.created_at).toLocaleDateString();

        tr.innerHTML = `
            <td>
                <div class="user-cell">
                    <div class="user-avatar">${initials}</div>
                    <span>${userName}</span>
                </div>
            </td>
            <td><span class="blood-badge">${req.blood_group}</span></td>
            <td>${req.city || 'N/A'}</td>
            <td>${dateStr}</td>
            <td><span class="status-badge" style="color: var(--warning-yellow);">Pending</span></td>
            <td>
                <div class="action-btns">
                    <button class="btn btn-approve" onclick="handleAction('${req.id}', 'approve')">
                        <i class="fa-solid fa-check"></i> Approve
                    </button>
                    <button class="btn btn-reject" onclick="openRejectModal('${req.id}')">
                        <i class="fa-solid fa-xmark"></i> Reject
                    </button>
                </div>
            </td>
        `;
        container.appendChild(tr);
    });
}

window.handleAction = async function (requestId, action, reason = '') {
    try {
        const response = await API.donors.approveRequest(requestId, action, reason);

        if (response.success) {
            alert(`Application ${action === 'approve' ? 'approved' : 'rejected'} successfully!`);
            if (action === 'reject') closeRejectModal();
            fetchPendingRequests(); // Refresh table
        } else {
            alert(response.message || `Failed to ${action} application`);
        }
    } catch (error) {
        console.error(`Error during ${action}:`, error);
        alert(error.message || `An error occurred while ${action}ing the application`);
    }
};

window.openRejectModal = function (requestId) {
    currentRequestId = requestId;
    document.getElementById('rejectModal').style.display = 'flex';
};

window.closeRejectModal = function () {
    currentRequestId = null;
    document.getElementById('rejectionReason').value = '';
    document.getElementById('rejectModal').style.display = 'none';
};

async function handleRejectSubmit() {
    const reason = document.getElementById('rejectionReason').value.trim();
    if (!reason) {
        alert('Please provide a reason for rejection');
        return;
    }

    if (currentRequestId) {
        await handleAction(currentRequestId, 'reject', reason);
    }
}
