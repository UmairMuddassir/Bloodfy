/**
 * Patient/Blood Requests Management Integration Script
 * Complete CRUD operations for blood requests
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Check if we're on patient/requests page
    const isPatientPage = document.querySelector('.patients-main') ||
        document.querySelector('.requests-table') ||
        document.querySelector('.blood-requests') ||
        document.querySelector('.requests-main');

    if (isPatientPage) {
        await initializePatientPage();
    }
});

// =============================================================================
// INITIALIZE PATIENT PAGE
// =============================================================================

async function initializePatientPage() {
    console.log('🚀 Patients JS: Initializing patient requests page...');

    const isUserSide = document.querySelector('.requests-main');
    console.log('🚀 Patients JS: Context:', isUserSide ? 'User Side' : 'Admin Side');

    // Load stats and list in parallel to prevent blocking
    console.log('🚀 Patients JS: Starting data fetch...');

    const filters = isUserSide ? { mine: true } : {};

    // We don't await them sequentially to avoid blocking
    Promise.all([
        loadPatientStats(filters).catch(err => console.error('Stats error:', err)),
        loadRequestsList(filters).catch(err => console.error('List error:', err))
    ]).then(() => {
        console.log('🚀 Patients JS: Data fetch completed');
        setupPatientPageEvents();
    }).catch(err => {
        console.error('🚀 Patients JS: Initialization error:', err);
    });

    console.log('🚀 Patients JS: Setup complete (waiting for promises)');
}

// =============================================================================
// LOAD PATIENT STATS
// =============================================================================

async function loadPatientStats() {
    try {
        // Get all requests to calculate stats
        const allRequests = await API.requests.getList({});
        console.log('Stats API Response:', allRequests);

        if (allRequests.success && allRequests.data) {
            // CRITICAL FIX: Use blood_requests from API response
            const requests = allRequests.data.blood_requests || [];
            console.log(`Calculating stats for ${requests.length} requests`);

            // Calculate stats
            const totalPatients = requests.length;
            const activeRequests = requests.filter(r =>
                r.status === 'pending' || r.status === 'matched'
            ).length;
            const fulfilledRequests = requests.filter(r =>
                r.status === 'completed'
            ).length;

            // Update UI
            updateStat('statTotalPatients', totalPatients);
            updateStat('statActiveRequests', activeRequests);
            updateStat('statFulfilledRequests', fulfilledRequests);
        } else {
            console.warn('No data in stats response');
            // Set to 0 if no data
            updateStat('statTotalPatients', 0);
            updateStat('statActiveRequests', 0);
            updateStat('statFulfilledRequests', 0);
        }
    } catch (error) {
        console.error('Error loading patient stats:', error);
        updateStat('statTotalPatients', '--');
        updateStat('statActiveRequests', '--');
        updateStat('statFulfilledRequests', '--');
    }
}

function updateStat(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = value;
    }
}

// =============================================================================
// LOAD REQUESTS LIST
// =============================================================================

async function loadRequestsList(filters = {}) {
    const container = document.getElementById('requestsTableBody') ||
        document.querySelector('.table-body');

    if (!container) {
        console.error('CRITICAL: Requests table container #requestsTableBody not found in DOM');
        return;
    }

    console.log('Loading requests with filters:', filters);

    try {
        const result = await API.requests.getList(filters);
        console.log('API Response:', result);

        if (result.success && result.data) {
            // CRITICAL FIX: API returns blood_requests, not results
            const requests = result.data.blood_requests || [];
            console.log(`Found ${requests.length} blood requests`);

            if (requests.length === 0) {
                console.log('No requests found, showing empty state');
                container.innerHTML = `
                    <div style="grid-column: 1 / -1; padding: 60px 40px; text-align: center; color: var(--text-secondary);">
                        <i class="fa-solid fa-inbox" style="font-size: 3rem; margin-bottom: 20px; display: block; opacity: 0.3;"></i>
                        <h3 style="margin-bottom: 10px; color: var(--text-primary);">No Blood Requests Yet</h3>
                        <p style="margin-bottom: 20px;">You haven't created any blood requests. Click "Request Blood" to create your first request.</p>
                    </div>
                `;
                return;
            }

            console.log('Displaying requests...');
            displayRequests(requests, container);
        } else {
            console.error('API returned unsuccessful response:', result);
            container.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: #FF5252;">
                    <i class="fa-solid fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 15px; display: block;"></i>
                    <strong>Failed to load requests</strong><br>
                    ${result.message || 'Unknown error'}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading requests:', error);
        container.innerHTML = `
            <div style="grid-column: 1 / -1; padding: 40px; text-align: center; color: #FF5252;">
                <i class="fa-solid fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 15px; display: block;"></i>
                <strong>Failed to load requests</strong><br>
                ${error.message || 'Please check your connection and try again.'}
            </div>
        `;
    }
}

function displayRequests(requests, container) {
    container.innerHTML = '';

    requests.forEach(request => {
        const row = document.createElement('div');
        row.className = document.querySelector('.requests-main') ? 'grid-request-row' : 'grid-table-row';
        row.dataset.requestId = request.id;

        const patientName = request.patient_name || request.recipient_name || 'Unknown Patient';
        const bloodGroup = request.blood_group || 'N/A';
        const location = request.hospital_name || 'Unknown Location';
        const status = request.status || 'PENDING';

        // Map status to CSS classes
        const statusClasses = {
            'pending': 'status-pending',
            'matched': 'status-progress',
            'assigned': 'status-completed',
            'in_progress': 'status-progress',
            'approved': 'status-progress',
            'completed': 'status-completed',
            'fulfilled': 'status-completed',
            'cancelled': 'status-cancelled'
        };

        const statusLower = (status || '').toLowerCase();
        let statusClass = statusClasses[statusLower] || 'status-pending';

        // Use approved class if approved flag is set but status is still pending
        if (statusLower === 'pending' && request.is_approved) {
            statusClass = 'status-progress';
        }

        const displayStatus = (statusLower === 'pending' && request.is_approved) ? 'APPROVED' : status.replace(/_/g, ' ').toUpperCase();

        row.innerHTML = `
            <div class="patient-name">${patientName}</div>
            <div><span class="blood-type-tag">${bloodGroup}</span></div>
            <div style="font-weight: 500; color: #E2E8F0;">
                <span style="color: ${request.units_fulfilled >= request.units_required ? '#00C853' : '#FFAB00'}">${request.units_fulfilled || 0}</span> 
                <span style="color: #94A3B8;">/ ${request.units_required || 1}</span>
            </div>
            <div>${location}</div>
            <div><span class="status-tag ${statusClass}">${displayStatus}</span></div>
            <div class="table-actions">
                ${(statusLower === 'pending' || statusLower === 'matched' || (statusLower === 'approved' && !request.assigned_donor_info)) ? `
                    ${(isAdmin() && statusLower === 'pending') ? `<button class="btn-table" onclick="approveRequest('${request.id}')" style="background:#1976D2; color:white; border:none;">Approve</button>` : ''}
                    ${isAdmin() ? `<button class="btn-table" onclick="assignDonor('${request.id}')">Assign</button>` : ''}
                ` : ''}
                
                <button class="btn-table details" onclick="viewRequestDetail('${request.id}')">Details</button>
                
                ${(isAdmin() || isOwner(request)) ? `
                    ${(statusLower === 'approved' || statusLower === 'in_progress' || statusLower === 'matched' || statusLower === 'assigned') ? `
                        <button class="btn-table" onclick="completeRequest('${request.id}')" style="background:#00C853; color:white; border:none;">Complete</button>
                    ` : ''}
                    
                    ${(statusLower !== 'completed' && statusLower !== 'cancelled') ? `
                        <button class="btn-table" onclick="deleteRequest('${request.id}')" style="background:#E53935; color:white; border:none;">Delete</button>
                    ` : ''}
                ` : ''}
            </div>
        `;

        container.appendChild(row);
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

function setupPatientPageEvents() {
    // Add New Request button
    const addBtn = document.getElementById('btnAddRequest');
    if (addBtn) {
        addBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showCreateRequestModal();
        });
    }

    // Search functionality
    const searchInput = document.querySelector('.search-bar input');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const query = searchInput.value.trim();
                if (query) {
                    loadRequestsList({ search: query });
                } else {
                    loadRequestsList();
                }
            }
        });
    }
}

// =============================================================================
// CREATE REQUEST MODAL
// =============================================================================

function prepareRequestModal() {
    let modal = document.getElementById('createRequestModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'createRequestModal';
        modal.className = 'modal';
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;

        const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

        modal.innerHTML = `
            <div class="modal-content" style="background: var(--glass-bg, #1F2229); border-radius: 16px; padding: 30px; max-width: 550px; width: 95%; border: 1px solid var(--glass-border, #333); max-height: 95vh; overflow-y: auto;">
                <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px;">
                    <h2 style="font-size: 1.5rem; color: var(--text-primary, #F1F5F9);">Create Blood Request</h2>
                    <button class="modal-close" onclick="closeCreateRequestModal()" style="background: none; border: none; color: var(--text-secondary, #94A3B8); font-size: 1.5rem; cursor: pointer;">&times;</button>
                </div>
                <form id="createRequestForm">
                    <div id="modal-error-container" style="display:none; margin-bottom:20px; padding:12px; background:rgba(255,82,82,0.1); border:1px solid #ff5252; border-radius:8px; color:#ff5252; font-size:0.9rem;"></div>
                    
                    <div class="form-group" style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Patient Name *</label>
                        <input type="text" name="patient_name" required placeholder="Full Name" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Blood Group *</label>
                            <select name="blood_group" required style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                                <option value="">Select</option>
                                ${bloodGroups.map(bg => `<option value="${bg}">${bg}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Units Required *</label>
                            <input type="number" name="units_required" min="1" value="1" required style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Urgency *</label>
                            <select name="urgency_level" required style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                                <option value="normal" selected>Normal</option>
                                <option value="urgent">Urgent</option>
                                <option value="emergency">Emergency</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Patient Age (Optional)</label>
                            <input type="number" name="patient_age" placeholder="Age" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Hospital Name *</label>
                            <input type="text" name="hospital_name" required placeholder="e.g. Aga Khan" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                        </div>
                        <div class="form-group">
                            <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Hospital City *</label>
                            <input type="text" name="hospital_city" required placeholder="e.g. Karachi" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem;">
                        </div>
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Hospital Address *</label>
                        <textarea name="hospital_address" required rows="2" placeholder="Full address for coordination" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem; resize: vertical;"></textarea>
                    </div>
                    
                    <div class="form-group" style="margin-bottom: 25px;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94A3B8);">Notes / Diagnosis (Optional)</label>
                        <textarea name="notes" rows="2" placeholder="Diagnostic info or contact details" style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-primary, #F1F5F9); font-size: 1rem; resize: vertical;"></textarea>
                    </div>
                    
                    <div style="display: flex; gap: 15px; justify-content: flex-end;">
                        <button type="button" onclick="closeCreateRequestModal()" style="padding: 12px 24px; background: transparent; border: 1px solid var(--glass-border, #333); border-radius: 8px; color: var(--text-secondary, #94A3B8); cursor: pointer; font-size: 1rem;">Cancel</button>
                        <button type="submit" id="submitRequestBtn" style="padding: 12px 24px; background: linear-gradient(90deg, #c62828, #b71c1c); border: none; border-radius: 8px; color: white; cursor: pointer; font-size: 1rem; font-weight: 600;">Create Request</button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(modal);
    }
    return modal;
}

function showCreateRequestModal() {
    const modal = prepareRequestModal();
    if (modal) {
        modal.style.display = 'flex';
    }

    const errorContainer = document.getElementById('modal-error-container');
    if (errorContainer) errorContainer.style.display = 'none';

    // Setup form submission
    const form = document.getElementById('createRequestForm');
    form.onsubmit = async (e) => {
        e.preventDefault();
        await handleCreateRequest(new FormData(form));
    };
}

window.closeCreateRequestModal = function () {
    const modal = document.getElementById('createRequestModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('createRequestForm')?.reset();
    }
};

async function handleCreateRequest(formData) {
    const submitBtn = document.getElementById('submitRequestBtn');
    const errorContainer = document.getElementById('modal-error-container');
    const originalText = submitBtn.innerHTML;

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creating...';
        if (errorContainer) errorContainer.style.display = 'none';

        const requestData = {
            patient_name: formData.get('patient_name'),
            blood_group: formData.get('blood_group'),
            units_required: parseInt(formData.get('units_required')),
            urgency_level: formData.get('urgency_level') || 'normal',
            hospital_name: formData.get('hospital_name'),
            hospital_city: formData.get('hospital_city'),
            hospital_address: formData.get('hospital_address'),
            patient_age: formData.get('patient_age') ? parseInt(formData.get('patient_age')) : null,
            notes: formData.get('notes') || '',
        };

        const result = await API.requests.create(requestData);

        if (result.success) {
            alert('Blood request created successfully!');
            closeCreateRequestModal();
            await loadPatientStats();
            await loadRequestsList();
        }
    } catch (error) {
        console.error('Error creating request:', error);

        // Show detailed validation errors if available
        let errorMessage = error.message || 'Unknown error occurred';

        if (error.errors && typeof error.errors === 'object') {
            const fieldErrors = Object.entries(error.errors)
                .map(([field, msgs]) => `• ${field.replace('_', ' ')}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
                .join('<br>');

            if (fieldErrors) {
                errorMessage = `<strong>Submission Failed:</strong><br>${fieldErrors}`;
            }
        }

        if (errorContainer) {
            errorContainer.innerHTML = errorMessage;
            errorContainer.style.display = 'block';
            errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alert('Failed to create request: ' + errorMessage.replace(/<br>|<strong>|<\/strong>/g, ' '));
        }
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// =============================================================================
// REQUEST ACTIONS
// =============================================================================

window.viewRequestDetail = async function (requestId) {
    try {
        const result = await API.requests.getDetail(requestId);

        if (result.success && result.data) {
            const r = result.data;
            const patientName = r.patient_name || r.recipient_name || 'N/A';
            const requester = r.recipient_name || 'N/A';
            const contact = r.recipient_phone || 'N/A';
            const units = `${r.units_fulfilled || 0} / ${r.units_required || 0}`;

            const detailMsg = `
BLOOD REQUEST DETAILS
----------------------------
ID: ${r.id.substring(0, 8)}...
Status: ${r.status.toUpperCase()}
Urgency: ${r.urgency_level.toUpperCase()}
Approved: ${r.is_approved ? 'YES' : 'NO'}

PATIENT INFO:
Name: ${patientName}
Age: ${r.patient_age || 'N/A'}
Diagnosis: ${r.diagnosis || 'N/A'}

LOCATION:
Hospital: ${r.hospital_name}
City: ${r.hospital_city}
Address: ${r.hospital_address}

CONTACT:
Requester: ${requester}
Phone: ${contact}

${r.assigned_donor_info ? `
ASSIGNED DONOR:
Name: ${r.assigned_donor_info.name}
Phone: ${r.assigned_donor_info.phone}
${r.assigned_donor_info.email ? `Email: ${r.assigned_donor_info.email}` : ''}
`.trim() : ''}

NOTES:
${r.notes || 'No additional notes.'}
----------------------------
Created: ${new Date(r.requested_at).toLocaleString()}
            `.trim();

            alert(detailMsg);
        }
    } catch (error) {
        console.error('Error loading request details:', error);
        alert('Failed to load request details');
    }
};

window.assignDonor = async function (requestId) {
    if (!isAdmin()) {
        alert('Only administrators can assign donors.');
        return;
    }

    try {
        if (typeof showInfo === 'function') showInfo('Fetching matched donors...');
        const result = await API.requests.getMatchedDonors(requestId);

        if (result.success && result.data) {
            let donors = Array.isArray(result.data) ? result.data : result.data.donors || [];

            if (donors.length === 0) {
                if (confirm('No matching donors found in the same city. Would you like to view all approved donors with the same blood group instead?')) {
                    // Fetch all approved donors for this blood group regardless of city
                    try {
                        const requestDetail = await API.requests.getDetail(requestId);
                        const bloodGroup = requestDetail.data?.blood_group;

                        if (bloodGroup) {
                            showInfo(`Searching for all ${bloodGroup} donors...`);
                            const allDonors = await API.donors.getList({ blood_group: bloodGroup });

                            if (allDonors.success && allDonors.data && allDonors.data.donors.length > 0) {
                                donors = allDonors.data.donors;
                            } else {
                                alert(`No donors found even after searching all approved ${bloodGroup} profiles.`);
                                return;
                            }
                        } else {
                            alert('Could not determine blood group for this request.');
                            return;
                        }
                    } catch (err) {
                        console.error('Error fetching fallback donors:', err);
                        alert('Failed to search for fallback donors.');
                        return;
                    }
                } else {
                    return;
                }
            }

            showDonorAssignmentModal(requestId, donors);
        }
    } catch (error) {
        console.error('Error in donor assignment:', error);
        alert('Failed to fetch donors: ' + (error.message || 'Unknown error'));
    }
};

function showDonorAssignmentModal(requestId, donors) {
    let modal = document.getElementById('donorAssignmentModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'donorAssignmentModal';
        modal.className = 'modal';
        modal.style.cssText = `
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.85);
            justify-content: center;
            align-items: center;
            z-index: 10000;
            backdrop-filter: blur(5px);
        `;
        document.body.appendChild(modal);
    }

    modal.innerHTML = `
        <div class="modal-content" style="background: #1a1a1a; border-radius: 20px; padding: 0; max-width: 600px; width: 95%; border: 1px solid rgba(255,255,255,0.1); overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
            <div style="padding: 25px; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center; background: linear-gradient(to right, #1a1a1a, #252525);">
                <h2 style="margin: 0; color: #fff; font-size: 1.5rem; font-weight: 600;">Assign Donor</h2>
                <button onclick="closeDonorAssignmentModal()" style="background: none; border: none; color: #94A3B8; font-size: 1.8rem; cursor: pointer; transition: color 0.2s;">&times;</button>
            </div>
            
            <div style="padding: 20px; max-height: 450px; overflow-y: auto; background: #121212;" id="donorListContainer">
                <p style="color: #94A3B8; margin-bottom: 20px; font-size: 0.95rem;">Select an eligible donor to assign to this request. The requester will be notified immediately.</p>
                
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    ${donors.map(donor => {
        const name = donor.name || (donor.user?.first_name ? `${donor.user.first_name} ${donor.user.last_name || ''}` : 'Unknown Donor');
        const phone = donor.phone || donor.user?.phone_number || 'N/A';
        const responseRate = donor.response_rate || 0;

        return `
                            <div class="donor-item" style="background: #1f1f1f; border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; padding: 15px; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s ease; cursor: pointer;" onclick="handleSelectDonor('${requestId}', '${donor.id}', '${name}')">
                                <div style="display: flex; align-items: center; gap: 15px;">
                                    <div style="width: 45px; height: 45px; border-radius: 12px; background: rgba(198, 40, 40, 0.1); color: #c62828; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; border: 1px solid rgba(198, 40, 40, 0.2);">
                                        ${donor.blood_group}
                                    </div>
                                    <div>
                                        <h4 style="margin: 0; color: #F1F5F9; font-weight: 600; font-size: 1rem;">${name}</h4>
                                        <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px;">
                                            <span style="color: #94A3B8; font-size: 0.8rem; display: flex; align-items: center; gap: 4px;">
                                                <i class="fa-solid fa-location-dot" style="font-size: 0.7rem;"></i> ${donor.city || 'Unknown'}
                                            </span>
                                            <span style="color: #94A3B8; font-size: 0.8rem; display: flex; align-items: center; gap: 4px;">
                                                <i class="fa-solid fa-star" style="font-size: 0.7rem; color: #fbbf24;"></i> ${responseRate}% Resp.
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <button class="btn-assign-small" style="padding: 8px 16px; background: rgba(198, 40, 40, 0.1); color: #c62828; border: 1px solid rgba(198, 40, 40, 0.3); border-radius: 8px; font-weight: 600; font-size: 0.85rem; cursor: pointer; transition: all 0.2s;">
                                    Assign
                                </button>
                            </div>
                        `;
    }).join('')}
                </div>
            </div>
            
            <div style="padding: 20px; background: #1a1a1a; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: flex-end;">
                <button onclick="closeDonorAssignmentModal()" style="padding: 10px 20px; background: transparent; border: 1px solid rgba(255,255,255,0.1); color: #94A3B8; border-radius: 8px; cursor: pointer; font-weight: 500;">Cancel</button>
            </div>
        </div>
        
        <style>
            .donor-item:hover {
                background: #252525 !important;
                border-color: rgba(198, 40, 40, 0.3) !important;
                transform: translateX(5px);
            }
            .donor-item:hover .btn-assign-small {
                background: #c62828 !important;
                color: #fff !important;
                border-color: #c62828 !important;
                box-shadow: 0 4px 12px rgba(198, 40, 40, 0.3);
            }
        </style>
    `;

    modal.style.display = 'flex';
}

window.closeDonorAssignmentModal = function () {
    const modal = document.getElementById('donorAssignmentModal');
    if (modal) modal.style.display = 'none';
}

window.handleSelectDonor = async function (requestId, donorId, donorName) {
    if (!confirm(`Are you sure you want to assign ${donorName} to this request?`)) return;

    try {
        const btn = event.currentTarget.querySelector('.btn-assign-small');
        if (btn) {
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            btn.disabled = true;
        }

        const result = await API.requests.assignDonor(requestId, donorId);

        if (result.success) {
            alert(`Donor ${donorName} assigned successfully! The requester has been notified.`);
            closeDonorAssignmentModal();
            await loadRequestsList();
            await loadPatientStats();
        } else {
            alert('Failed to assign donor: ' + (result.message || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error assigning donor:', error);
        alert('Assignment failed: ' + (error.message || 'Unknown error'));
    }
}
window.deleteRequest = async function (requestId) {
    if (!confirm('Are you sure you want to delete this blood request?')) return;

    try {
        const result = await API.requests.delete(requestId);
        if (result.success) {
            alert(result.message || 'Request deleted successfully');
            await loadRequestsList();
            await loadPatientStats();
        }
    } catch (error) {
        console.error('Error deleting request:', error);
        alert('Failed to delete request');
    }
};

window.completeRequest = async function (requestId) {
    if (!confirm('Are you sure you want to process this request?')) return;

    try {
        const result = await API.requests.complete(requestId);
        if (result.success) {
            alert(result.message || 'Request marked as completed');
            await loadRequestsList();
            await loadPatientStats();
        }
    } catch (error) {
        console.error('Error completing request:', error);
        alert('Failed to complete request');
    }
};

window.approveRequest = async function (requestId) {
    if (!confirm('Approve this blood request?')) return;

    try {
        const result = await API.requests.approve(requestId);
        if (result.success) {
            alert(result.message || 'Request approved successfully');
            await loadRequestsList();
            await loadPatientStats();
        }
    } catch (error) {
        console.error('Error approving request:', error);
        alert('Failed to approve request');
    }
};

function isOwner(request) {
    const user = getUserData();
    if (!user) return false;
    // Check if current user is the recipient or creator
    return request.recipient_user_id === user.id ||
        (request.recipient && request.recipient.user && request.recipient.user.id === user.id);
}
