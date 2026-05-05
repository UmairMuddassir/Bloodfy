/**
 * Staff Management Integration Script
 * Handles listing, adding, and managing staff/admin users
 */

document.addEventListener('DOMContentLoaded', async () => {
    await initializeStaffPage();
});

// =============================================================================
// STAFF PAGE INITIALIZATION
// =============================================================================

async function initializeStaffPage() {
    console.log('Initializing staff management page...');

    // Load staff list
    await loadStaffList();

    // Setup event listeners
    setupEventListeners();
}

// =============================================================================
// LOAD STAFF LIST
// =============================================================================

async function loadStaffList() {
    try {
        const response = await API.users.getList();

        if (response.success && response.data) {
            // Updated to use new backend structure
            const users = response.data.users || (Array.isArray(response.data) ? response.data : []);
            renderStaffTable(users);
        }
    } catch (error) {
        console.error('Error loading staff list:', error);
        showError('Failed to load staff list');
    }
}

function renderStaffTable(users) {
    const tableBody = document.querySelector('.staff-table tbody');
    if (!tableBody) return;

    tableBody.innerHTML = '';

    if (users.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:20px;">No users found</td></tr>';
        return;
    }

    users.forEach(user => {
        const row = document.createElement('tr');

        // Format user type/role
        const roleClass = user.is_superuser || user.user_type === 'admin' ? 'role-admin' : 'role-manager';
        const roleLabel = user.is_superuser ? 'Super Admin' : (user.user_type || 'User').toUpperCase();

        // Format status
        const statusClass = user.is_active ? 'status-active' : 'status-inactive';
        const statusLabel = user.is_active ? 'Active' : 'Inactive';

        // User profile image (fallback if not available)
        const profileImage = user.profile_image || `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='35' height='35'%3E%3Ccircle cx='17.5' cy='17.5' r='17.5' fill='%23374151'/%3E%3Ctext x='17.5' y='22' text-anchor='middle' fill='%23F9FAFB' font-size='14' font-family='sans-serif'%3E${(user.first_name || 'U').charAt(0)}%3C/text%3E%3C/svg%3E`;

        row.innerHTML = `
            <td>
                <div style="display:flex; align-items:center; gap:10px;">
                    <img src="${profileImage}" style="border-radius:50%; width:35px; height:35px; object-fit:cover;">
                    <strong>${user.first_name} ${user.last_name}</strong>
                </div>
            </td>
            <td><span class="role-badge ${roleClass}">${roleLabel}</span></td>
            <td>${user.email}</td>
            <td><span class="status-dot ${statusClass}"></span> ${statusLabel}</td>
            <td>
                <button class="action-btn" onclick="editStaff('${user.id}')" title="Edit User">
                    <i class="fa-solid fa-pen"></i>
                </button>
                ${!user.is_superuser ? `
                <button class="action-btn" onclick="deleteStaff('${user.id}')" title="Delete User" style="margin-left:5px;">
                    <i class="fa-solid fa-trash"></i>
                </button>
                ` : ''}
            </td>
        `;

        tableBody.appendChild(row);
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

function setupEventListeners() {
    const addUserBtn = document.getElementById('btnAddUser');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', () => {
            showAddUserModal();
        });
    }
}

// =============================================================================
// MODALS
// =============================================================================

window.showAddUserModal = function () {
    let modal = document.getElementById('addUserModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'addUserModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Add New Staff/Admin</h2>
                    <button class="modal-close" onclick="closeAddUserModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="addUserError" style="display:none; background:rgba(244,67,54,0.1); border:1px solid #F44336; color:#F44336; padding:12px; border-radius:8px; margin-bottom:15px; font-size:14px;"></div>
                    <div id="addUserSuccess" style="display:none; background:rgba(76,175,80,0.1); border:1px solid #4CAF50; color:#4CAF50; padding:12px; border-radius:8px; margin-bottom:15px; font-size:14px;"></div>
                    <form id="addUserForm">
                        <div class="form-row">
                            <div class="form-group">
                                <label>First Name *</label>
                                <input type="text" name="first_name" class="form-input" required>
                            </div>
                            <div class="form-group">
                                <label>Last Name *</label>
                                <input type="text" name="last_name" class="form-input" required>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Email *</label>
                            <input type="email" name="email" class="form-input" required>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label>User Type *</label>
                                <select name="user_type" class="form-input" required>
                                    <option value="user">User</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Phone Number</label>
                                <input type="tel" name="phone_number" class="form-input">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>Password *</label>
                            <input type="password" name="password" class="form-input" required minlength="8">
                        </div>
                        
                        <div class="form-group">
                            <label>Confirm Password *</label>
                            <input type="password" name="password_confirm" class="form-input" required minlength="8">
                        </div>
                        
                        <div class="form-actions">
                            <button type="button" class="btn-secondary" onclick="closeAddUserModal()">Cancel</button>
                            <button type="submit" id="addUserSubmitBtn" class="btn-primary">Create User</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        // Setup form submission
        const form = document.getElementById('addUserForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleAddUser(form);
        });
    } else {
        // Reset error/success banners when re-opening
        const errDiv = document.getElementById('addUserError');
        const okDiv = document.getElementById('addUserSuccess');
        const form = document.getElementById('addUserForm');
        if (errDiv) errDiv.style.display = 'none';
        if (okDiv) okDiv.style.display = 'none';
        if (form) form.reset();
    }

    modal.style.display = 'flex';
};

window.closeAddUserModal = function () {
    const modal = document.getElementById('addUserModal');
    if (modal) modal.style.display = 'none';
};

async function handleAddUser(form) {
    const formData = new FormData(form);
    const userData = Object.fromEntries(formData.entries());

    const errDiv = document.getElementById('addUserError');
    const okDiv = document.getElementById('addUserSuccess');
    const submitBtn = document.getElementById('addUserSubmitBtn');

    function showModalError(msg) {
        if (errDiv) { errDiv.style.display = 'block'; errDiv.textContent = msg; }
        if (okDiv) okDiv.style.display = 'none';
    }
    function showModalSuccess(msg) {
        if (okDiv) { okDiv.style.display = 'block'; okDiv.textContent = msg; }
        if (errDiv) errDiv.style.display = 'none';
    }

    if (userData.password !== userData.password_confirm) {
        showModalError('Passwords do not match');
        return;
    }

    if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Creating...'; }

    try {
        const token = getAuthToken();
        const response = await fetch(`${API_CONFIG.BASE_URL}/users/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token,
            },
            body: JSON.stringify(userData),
        });

        const result = await response.json();
        console.log('Create user response:', result);

        if (result.success) {
            showModalSuccess('User created successfully!');
            form.reset();
            setTimeout(async () => {
                closeAddUserModal();
                await loadStaffList();
            }, 1200);
        } else {
            // Show field-level errors if present
            let errMsg = result.message || 'Failed to create user';
            if (result.errors && typeof result.errors === 'object') {
                errMsg = Object.entries(result.errors)
                    .map(([f, msgs]) => `${f}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
                    .join(' | ');
            }
            showModalError(errMsg);
        }
    } catch (error) {
        console.error('Error creating user:', error);
        showModalError(error.message || 'Network error – check server is running');
    } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Create User'; }
    }
}

// =============================================================================
// ACTIONS
// =============================================================================

window.editStaff = async function (userId) {
    try {
        const response = await API.users.getDetail(userId);
        if (response.success && response.data) {
            showEditUserModal(response.data);
        }
    } catch (error) {
        console.error('Error loading user details:', error);
        showError('Failed to load user details');
    }
};

function showEditUserModal(user) {
    let modal = document.getElementById('editUserModal');

    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'editUserModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Edit User</h2>
                    <button class="modal-close" onclick="closeEditUserModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="editUserForm">
                        <input type="hidden" name="id">
                        <div class="form-row">
                            <div class="form-group">
                                <label>First Name</label>
                                <input type="text" name="first_name" class="form-input">
                            </div>
                            <div class="form-group">
                                <label>Last Name</label>
                                <input type="text" name="last_name" class="form-input">
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label>User Type</label>
                            <select name="user_type" class="form-input">
                                <option value="user">User</option>
                                <option value="admin">Admin</option>
                            </select>
                        </div>
                        
                        <div class="form-group">
                            <label>Status</label>
                            <select name="is_active" class="form-input">
                                <option value="true">Active</option>
                                <option value="false">Inactive</option>
                            </select>
                        </div>
                        
                        <div class="form-actions">
                            <button type="button" class="btn-secondary" onclick="closeEditUserModal()">Cancel</button>
                            <button type="submit" class="btn-primary">Save Changes</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        const form = document.getElementById('editUserForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            await handleEditUser(new FormData(form));
        };
    }

    // Populate form
    const form = document.getElementById('editUserForm');
    form.elements['id'].value = user.id;
    form.elements['first_name'].value = user.first_name || '';
    form.elements['last_name'].value = user.last_name || '';
    form.elements['user_type'].value = user.user_type || 'user';
    form.elements['is_active'].value = user.is_active.toString();

    modal.style.display = 'flex';
}

window.closeEditUserModal = function () {
    const modal = document.getElementById('editUserModal');
    if (modal) modal.style.display = 'none';
};

async function handleEditUser(formData) {
    const userId = formData.get('id');
    const updateData = {
        first_name: formData.get('first_name'),
        last_name: formData.get('last_name'),
        user_type: formData.get('user_type'),
        is_active: formData.get('is_active') === 'true'
    };

    try {
        const result = await apiRequest(`/users/${userId}/`, {
            method: 'PUT',
            body: updateData
        });

        if (result.success) {
            showSuccess('User updated successfully');
            closeEditUserModal();
            await loadStaffList();
        }
    } catch (error) {
        console.error('Error updating user:', error);
        showError(error.message || 'Failed to update user');
    }
}

window.deleteStaff = async function (userId) {
    if (!confirm('Are you sure you want to deactivate this user?')) return;

    try {
        const response = await API.users.deleteUser(userId);
        if (response.success) {
            showSuccess('User deactivated successfully');
            await loadStaffList();
        }
    } catch (error) {
        console.error('Error deactivating user:', error);
        showError(error.message || 'Failed to deactivate user');
    }
};
