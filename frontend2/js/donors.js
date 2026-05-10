/**
 * Donor Management Integration Script
 * Complete CRUD operations for donor management
 */

document.addEventListener('DOMContentLoaded', async () => {
    // Check if we're on donor page
    const isDonorListPage = document.querySelector('.donors-table') || document.querySelector('.donor-grid');
    const isDonorDetailPage = document.querySelector('.donor-profile-main');

    if (isDonorListPage) {
        await initializeDonorList();
    }

    if (isDonorDetailPage) {
        await initializeDonorDetail();
    }
});

// =============================================================================
// DONOR LIST PAGE
// =============================================================================

async function initializeDonorList() {
    console.log('Initializing donor list page...');

    // Load donors list
    await loadDonorsList();

    // Setup search functionality
    setupDonorSearch();

    // Setup filter functionality
    setupDonorFilters();

    // Setup page events (modal, form)
    setupDonorPageEvents();
}

async function loadDonorsList(filters = {}) {
    const container = document.querySelector('.donors-table tbody') ||
        document.querySelector('.donor-grid') ||
        document.querySelector('.table-body');

    if (!container) {
        console.warn('Donor list container not found');
        return;
    }

    showLoading(container);

    try {
        const result = await API.donors.getList(filters);

        if (result.success && result.data) {
            const donors = result.data.donors || (Array.isArray(result.data) ? result.data : result.data.results || []);

            if (donors.length === 0) {
                container.innerHTML = '<tr><td colspan="6" style="text-align: center; padding:40px; color: var(--text-secondary);">No donors found</td></tr>';
                return;
            }

            displayDonors(donors, container);
        }
    } catch (error) {
        console.error('Error loading donors:', error);
        showError('Failed to load donors. Please try again.', container);
    }
}

function displayDonors(donors, container) {
    container.innerHTML = '';

    donors.forEach(donor => {
        const row = document.createElement('tr');
        row.className = 'donor-row';
        row.dataset.donorId = donor.id;

        const userName = donor.name || (donor.user ? (donor.user.name || donor.user.first_name + ' ' + donor.user.last_name) : 'Unknown');
        const phone = donor.phone || donor.user?.phone_number || 'N/A';
        const status = donor.is_eligible ? 'Eligible' : 'Cooldown';
        const statusClass = donor.is_eligible ? 'status-eligible' : 'status-cooldown';

        // Sanitize all user-supplied data to prevent XSS
        const safeName = typeof escapeHtml === 'function' ? escapeHtml(userName) : userName;
        const safeCity = typeof escapeHtml === 'function' ? escapeHtml(donor.city || 'N/A') : (donor.city || 'N/A');
        const safePhone = typeof escapeHtml === 'function' ? escapeHtml(phone) : phone;
        const safeBloodGroup = typeof escapeHtml === 'function' ? escapeHtml(donor.blood_group) : donor.blood_group;

        row.innerHTML = `
            <td>${safeName}</td>
            <td><span class="blood-badge">${safeBloodGroup}</span></td>
            <td>${safeCity}</td>
            <td>${safePhone}</td>
            <td><span class="status-badge ${statusClass}">${status}</span></td>
            <td>
                <button class="btn-action" onclick="viewDonorDetail('${donor.id}')" title="View">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-action" onclick="editDonor('${donor.id}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
            </td>
        `;

        container.appendChild(row);
    });
}

// =============================================================================
// EVENT LISTENERS
// =============================================================================

function setupDonorPageEvents() {
    // Add New Donor button
    const addBtn = document.getElementById('btnAddDonor');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            openAddDonorModal();
        });
    }

    // Modal Form Submission
    const addForm = document.getElementById('addDonorForm');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await handleAddDonor(new FormData(addForm));
        });
    }
}

window.openAddDonorModal = function () {
    const modal = document.getElementById('addDonorModal');
    if (modal) modal.style.display = 'flex';
};

window.closeAddDonorModal = function () {
    const modal = document.getElementById('addDonorModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('addDonorForm')?.reset();
    }
};

async function handleAddDonor(formData) {
    const submitBtn = document.querySelector('#addDonorForm button[type="submit"]');
    const originalText = submitBtn.innerHTML;

    try {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';

        const donorData = {
            first_name: formData.get('first_name'),
            last_name: formData.get('last_name'),
            email: formData.get('email'),
            phone_number: formData.get('phone_number'),
            blood_group: formData.get('blood_group'),
            city: formData.get('city'),
            password: formData.get('password') || 'donor123',
            password_confirm: formData.get('password') || 'donor123',
            user_type: 'user'
        };

        // Use registration endpoint to create donor user
        const result = await API.donors.create(donorData);

        if (result.success) {
            alert('Donor created successfully!');
            closeAddDonorModal();
            await loadDonorsList();
        } else {
            const errorMsg = result.message || 'Failed to create donor';
            alert('Error: ' + errorMsg);
        }
    } catch (error) {
        console.error('Error adding donor:', error);
        let errorMsg = error.message || 'An unexpected error occurred';
        if (error.errors) {
            errorMsg += '\nDetails: ' + JSON.stringify(error.errors);
        }
        alert(`Error: ${errorMsg}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

// =============================================================================
// DONOR DETAIL PAGE
// =============================================================================

async function initializeDonorDetail() {
    console.log('Initializing donor detail page...');

    // Get donor ID from URL parameter or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const donorId = urlParams.get('id');

    if (!donorId) {
        // Try to get from current user if they're a donor
        const userData = getUserData();
        if (userData && userData.donor_status === 'DONOR_APPROVED') {
            // Load logged-in donor's own profile
            await loadDonorProfile(userData.id);
        } else if (userData && (userData.user_type === 'admin' || userData.is_staff || userData.is_superuser)) {
            // Admin accessing donor page without ID - show info message
            console.log('Admin access without donor ID - showing donor list');
            showInfo('Select a donor from the list to view their profile, or this page will display your admin profile.');
            // Try to load donor list instead if the container exists
            const listContainer = document.querySelector('.donors-table tbody') || document.querySelector('.donor-grid');
            if (listContainer) {
                await loadDonorsList();
            }
            return;
        } else {
            showError('No donor ID specified. Please select a donor from the list.');
            return;
        }
    } else {
        await loadDonorProfile(donorId);
    }

    // Setup edit functionality
    setupDonorEdit();
}

async function loadDonorProfile(donorId) {
    const profileContainer = document.querySelector('.donor-profile-main') || document.querySelector('.profile-container');

    if (!profileContainer) {
        console.warn('Profile container not found');
        return;
    }

    try {
        // Load donor details
        const donorResult = await API.donors.getDetail(donorId);

        if (donorResult.success && donorResult.data) {
            displayDonorProfile(donorResult.data);
        }

        // Load donation history
        const historyResult = await API.donors.getDonationHistory(donorId);

        if (historyResult.success && historyResult.data) {
            displayDonationHistory(historyResult.data);
        }

    } catch (error) {
        console.error('Error loading donor profile:', error);
        showError('Failed to load donor profile', profileContainer);
    }
}

function displayDonorProfile(donor) {
    // Update profile image/initials
    const avatarElement = document.querySelector('.profile-img-large') || document.querySelector('.admin-avatar');
    if (avatarElement && donor.user) {
        // avatarElement.src = donor.user.profile_image || 'assets/default-avatar.png'; // If image URL exists
    }

    // Update name
    const nameElements = document.querySelectorAll('.profile-name, .admin-name');
    nameElements.forEach(el => {
        el.textContent = donor.user?.first_name + ' ' + donor.user?.last_name;
    });

    // Update blood group
    const bloodGroupElements = document.querySelectorAll('.profile-role strong');
    bloodGroupElements.forEach(el => {
        el.textContent = donor.blood_group;
    });

    // Update eligibility status
    const statusElement = document.querySelector('.status-label');
    const daysLeftElement = document.querySelector('.days-left');
    const progressFill = document.querySelector('.progress-fill');

    if (statusElement) {
        statusElement.textContent = donor.is_eligible ? 'Eligible to Donate' : 'On Cooldown';
    }

    if (daysLeftElement && !donor.is_eligible) {
        daysLeftElement.textContent = `${donor.days_remaining || 0} Days to Active`;
    } else if (daysLeftElement) {
        daysLeftElement.textContent = 'Ready to donate!';
        daysLeftElement.style.color = '#00C853';
    }

    if (progressFill) {
        const percentage = donor.is_eligible ? 100 : ((90 - (donor.days_remaining || 0)) / 90) * 100;
        progressFill.style.width = `${Math.max(0, Math.min(100, percentage))}%`;
        progressFill.style.backgroundColor = donor.is_eligible ? '#00C853' : 'var(--primary-red)';
    }

    // Update form fields
    const form = document.querySelector('form');
    if (form) {
        if (form.elements['full_name']) form.elements['full_name'].value = donor.user?.first_name + ' ' + donor.user?.last_name;
        if (form.elements['phone_number']) form.elements['phone_number'].value = donor.user?.phone_number || '';
        if (form.elements['city']) form.elements['city'].value = donor.city || '';
        if (form.elements['address']) form.elements['address'].value = donor.user?.address || '';
        if (form.elements['last_donation']) form.elements['last_donation'].value = donor.last_donation_date || '';
    }
}

// =============================================================================
// EDIT DONOR FUNCTIONALITY
// =============================================================================

function setupDonorEdit() {
    const saveButton = document.getElementById('btnSaveDonor');

    if (saveButton) {
        saveButton.addEventListener('click', async (e) => {
            e.preventDefault();
            await saveDonorProfile();
        });
    }

    const form = document.getElementById('donorProfileForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveDonorProfile();
        });
    }
}

async function saveDonorProfile() {
    const form = document.getElementById('donorProfileForm');
    if (!form) return;

    const formData = new FormData(form);
    const donorId = getDonorIdFromUrl() || getUserData()?.donor_id; // Need a way to get ID

    // Parse name
    const fullName = formData.get('full_name').split(' ');
    const firstName = fullName[0];
    const lastName = fullName.slice(1).join(' ') || '';

    const updateData = {
        city: formData.get('city'),
        last_donation_date: formData.get('last_donation'),
        user: {
            first_name: firstName,
            last_name: lastName,
            phone_number: formData.get('phone_number'),
            address: formData.get('address')
        }
    };

    try {
        showLoading();
        // Determine endpoint based on if we are admin updating another donor or user updating self
        // For now assume updateDonor endpoint works
        const result = await API.donors.updateDonor(donorId, updateData);

        if (result.success) {
            showSuccess('Profile updated successfully');
            // Refresh data
            await initializeDonorDetail();
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showError('Failed to update profile');
    } finally {
        hideLoading();
    }
}



// =============================================================================
// SEARCH & FILTER
// =============================================================================

function setupDonorSearch() {
    const searchInput = document.getElementById('donorSearch') || document.querySelector('.search-input');

    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadDonorsList({ search: e.target.value });
            }, 300);
        });
    }
}

function setupDonorFilters() {
    const bloodGroupFilter = document.getElementById('bloodGroupFilter');
    const eligibilityFilter = document.getElementById('eligibilityFilter');

    if (bloodGroupFilter) {
        bloodGroupFilter.addEventListener('change', () => {
            applyFilters();
        });
    }

    if (eligibilityFilter) {
        eligibilityFilter.addEventListener('change', () => {
            applyFilters();
        });
    }
}

function applyFilters() {
    const filters = {};

    const bloodGroup = document.getElementById('bloodGroupFilter')?.value;
    if (bloodGroup) filters.blood_group = bloodGroup;

    const eligibility = document.getElementById('eligibilityFilter')?.value;
    if (eligibility) filters.is_eligible = eligibility === 'eligible';

    loadDonorsList(filters);
}

// =============================================================================
// GLOBAL FUNCTIONS
// =============================================================================

window.viewDonorDetail = function (donorId) {
    window.location.href = `donor-profile.html?id=${donorId}`;
};

window.editDonor = function (donorId) {
    window.location.href = `donor-profile.html?id=${donorId}&edit=true`;
};

function displayDonationHistory(historyData) {
    const historySection = document.querySelector('.history-section');
    if (!historySection) return;

    // Keep the header
    const header = historySection.querySelector('.table-head');
    const title = historySection.querySelector('h3');

    // Clear existing content except title and header
    historySection.innerHTML = '';
    if (title) historySection.appendChild(title);
    if (header) historySection.appendChild(header);

    const donations = historyData.donation_history || historyData;

    if (!donations || donations.length === 0) {
        const emptyRow = document.createElement('div');
        emptyRow.className = 'table-row';
        emptyRow.innerHTML = '<div style="flex: 1; text-align: center; padding: 20px; color: var(--text-secondary);">No donation history found</div>';
        historySection.appendChild(emptyRow);
        return;
    }

    donations.forEach(donation => {
        const row = document.createElement('div');
        row.className = 'table-row';

        const statusColor = donation.status === 'completed' ? '#00C853' : 'var(--primary-red)';
        const displayStatus = donation.status.charAt(0).toUpperCase() + donation.status.slice(1);

        row.innerHTML = `
            <div>${formatDate(donation.donation_date)}</div>
            <div>${donation.hospital_name || 'N/A'}</div>
            <div>${donation.units_donated} Unit${donation.units_donated > 1 ? 's' : ''}</div>
            <div style="color: ${statusColor};">${displayStatus}</div>
        `;
        historySection.appendChild(row);
    });
}

function getDonorIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('id');
}
