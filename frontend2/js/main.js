/**
 * Bloodify Main JavaScript
 * 
 * This file contains common functionality used across all pages
 * including authentication checks, utilities, and shared UI logic.
 */

// =============================================================================
// Page Protection & Authentication
// =============================================================================

/**
 * Define page access levels
 * PUBLIC: Anyone can access
 * AUTH: Requires authentication (any logged in user)
 * ADMIN: Requires admin role
 */
const PAGE_ACCESS = {
    // Public pages - no login required
    'index.html': 'PUBLIC',
    'index.html': 'PUBLIC',
    'user-login.html': 'PUBLIC',
    'admin-login.html': 'PUBLIC',
    '': 'PUBLIC',

    // User pages - requires any authenticated user
    'user-dashboard.html': 'AUTH',

    // Admin-only pages - requires admin role
    'dashboard.html': 'ADMIN',
    'donor.html': 'ADMIN',
    'patient.html': 'ADMIN',
    'bloodstock.html': 'ADMIN',
    'staff.html': 'ADMIN',
    'analytics.html': 'ADMIN',
    'emergency.html': 'AUTH',
    'chatbot.html': 'AUTH',
    'requests.html': 'AUTH',
    'notifications.html': 'AUTH',
    'settings.html': 'AUTH',
};

/**
 * Check if current page is in admin or user directory
 */
function getPageContext() {
    const path = window.location.pathname;
    if (path.includes('/admin/')) return 'ADMIN_DIR';
    if (path.includes('/user/')) return 'USER_DIR';
    if (path.includes('/auth/')) return 'AUTH_DIR';
    return 'PUBLIC_DIR';
}

/**
 * Protect page - redirect based on access level requirements and directory
 */
function protectPage() {
    const context = getPageContext();
    const currentPage = window.location.pathname.split('/').pop();

    // Context: AUTH Directory (Login pages)
    if (context === 'AUTH_DIR') {
        if (isAuthenticated()) {
            // If logged in, redirect to appropriate dashboard
            if (isAdmin()) {
                window.location.href = '../admin/pages/dashboard.html';
            } else {
                window.location.href = '../user/pages/dashboard.html';
            }
        }
        return;
    }

    // Context: ADMIN Directory
    if (context === 'ADMIN_DIR') {
        if (!isAuthenticated()) {
            // Not logged in -> Go to Admin Login
            window.location.href = '../../auth/admin-login.html';
            return;
        }

        if (!isAdmin()) {
            // Logged in but not admin -> Go to User Dashboard
            console.warn('Access denied: User tried to access admin page');
            window.location.href = '../../user/pages/dashboard.html';
            return;
        }
        return; // Allowed
    }

    // Context: USER Directory
    if (context === 'USER_DIR') {
        if (!isAuthenticated()) {
            // Not logged in -> Go to User Login
            window.location.href = '../../auth/user-login.html';
            return;
        }

        if (isAdmin()) {
            // Admin entering user area? 
            // Technically admins might want to see user dashboard, but stricter separation requested.
            // Redirect to Admin Dashboard
            console.warn('Redirecting admin to admin dashboard');
            window.location.href = '../../admin/pages/dashboard.html';
            return;
        }
        return; // Allowed
    }
}

/**
 * Initialize page on load
 */
function initializePage() {
    protectPage();

    if (isAuthenticated()) {
        displayUserInfo();
        // Show page content after successful auth check
        document.body.classList.add('loaded');
    }
}

/**
 * Display user information in header/sidebar
 */
function displayUserInfo() {
    const userData = getUserData();
    if (!userData) return;

    // Get name with multiple fallbacks
    let name = 'User';
    if (userData.first_name) {
        name = userData.first_name;
        if (userData.last_name) name += ' ' + userData.last_name;
    } else if (userData.name) {
        name = userData.name;
    } else if (userData.username) {
        name = userData.username;
    } else if (userData.email) {
        name = userData.email.split('@')[0];
    }

    // 1. Update elements with specific IDs
    const userNameEls = [
        document.getElementById('userName'),
        document.getElementById('headerUserName'),
        document.getElementById('adminName')
    ];
    userNameEls.forEach(el => {
        if (el) el.textContent = name;
    });

    // 2. Update common header/profile spans with the authenticated user's name
    const profileSelectors = '.admin-profile span, .user-profile span, .header-user span, .user-info span, .user-name-display, .profile-name, .admin-name';
    document.querySelectorAll(profileSelectors).forEach(el => {
        const text = el.textContent.trim();
        // More aggressive matching: if it contains 'Hameed', 'Admin', or is empty/generic
        if (text.includes('Hameed') ||
            text === 'Admin' ||
            text === 'User' ||
            text === '' ||
            el.classList.contains('user-name-display') ||
            el.parentElement.classList.contains('admin-profile')) {

            // If it has children (like the chevron icon), only replace the text node
            if (el.children.length > 0) {
                // Find text node
                for (let node of el.childNodes) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        node.textContent = name + ' ';
                        break;
                    }
                }
            } else {
                el.textContent = name;
            }
        }
    });

    // 3. Update role/type displays
    const role = userData.user_type || userData.role || 'Member';
    const displayRole = role.charAt(0).toUpperCase() + role.slice(1);

    const roleEls = [
        document.getElementById('userRole'),
        document.getElementById('headerUserRole'),
        document.getElementById('adminRole')
    ];
    roleEls.forEach(el => {
        if (el) el.textContent = displayRole;
    });

    // 4. Update emails
    document.querySelectorAll('.user-email-display').forEach(el => {
        el.textContent = userData.email || '';
    });
}

// =============================================================================
// Logout Functionality
// =============================================================================

/**
 * Handle logout action
 */
async function handleLogout() {
    try {
        // Call backend logout endpoint
        await API.auth.logout();
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Always clear local data and redirect
        clearAuthToken();
        // Redirect to auth page. Since we are in separate folders, we should use a path that works.
        // If we are deep (admin/pages), go up 2 levels.
        const context = getPageContext();
        if (context === 'ADMIN_DIR' || context === 'USER_DIR') {
            window.location.href = '../../auth/user-login.html';
        } else if (context === 'AUTH_DIR') {
            window.location.href = 'user-login.html';
        } else {
            window.location.href = 'auth/user-login.html';
        }
    }
}

/**
 * Attach logout handlers to all logout links/buttons
 */
function setupLogoutHandlers() {
    document.querySelectorAll('[data-action="logout"]').forEach(element => {
        element.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                handleLogout();
            }
        });
    });
}

// =============================================================================
// UI Utilities
// =============================================================================

/**
 * Show loading spinner
 * @param {HTMLElement} container - Container element
 */
function showLoading(container) {
    if (!container) return;

    const spinner = document.createElement('div');
    spinner.className = 'loading-spinner';
    spinner.innerHTML = `
        <div style="display: flex; justify-content: center; align-items: center; padding: 40px;">
            <i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: var(--primary-red);"></i>
        </div>
    `;
    container.innerHTML = '';
    container.appendChild(spinner);
}

/**
 * Hide loading spinner
 * @param {HTMLElement} container - Container element
 */
function hideLoading(container) {
    if (!container) return;
    const spinner = container.querySelector('.loading-spinner');
    if (spinner) {
        spinner.remove();
    }
}

/**
 * Show error message
 * @param {string} message - Error message
 * @param {HTMLElement} container - Optional container for inline errors
 */
function showError(message, container = null) {
    if (container) {
        container.innerHTML = `
            <div class="error-message" style="
                background: rgba(244, 67, 54, 0.1);
                border: 1px solid #F44336;
                color: #F44336;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            ">
                <i class="fas fa-exclamation-circle"></i>
                <span>${message}</span>
            </div>
        `;
    } else {
        alert('Error: ' + message);
    }
}

/**
 * Show success message
 * @param {string} message - Success message
 * @param {HTMLElement} container - Optional container for inline messages
 */
function showSuccess(message, container = null) {
    if (container) {
        container.innerHTML = `
            <div class="success-message" style="
                background: rgba(76, 175, 80, 0.1);
                border: 1px solid #4CAF50;
                color: #4CAF50;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            ">
                <i class="fas fa-check-circle"></i>
                <span>${message}</span>
            </div>
        `;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    } else {
        alert(message);
    }
}

// =============================================================================
// Data Formatting Utilities
// =============================================================================

/**
 * Show informational message
 * @param {string} message - Info message
 * @param {HTMLElement} container - Optional container for inline messages
 */
function showInfo(message, container = null) {
    if (container) {
        container.innerHTML = `
            <div class="info-message" style="
                background: rgba(33, 150, 243, 0.1);
                border: 1px solid #2196F3;
                color: #2196F3;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
            ">
                <i class="fas fa-info-circle"></i>
                <span>${message}</span>
            </div>
        `;

        // Auto-hide after 5 seconds
        setTimeout(() => {
            container.innerHTML = '';
        }, 5000);
    } else {
        alert(message);
    }
}

// =============================================================================
// Data Formatting Utilities
// =============================================================================

/**
 * Format date to readable string
 * @param {string} dateString - ISO date string
 * @returns {string} - Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format datetime to readable string
 * @param {string} dateTimeString - ISO datetime string
 * @returns {string} - Formatted datetime
 */
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'N/A';
    const date = new Date(dateTimeString);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format time ago (e.g., "2 hours ago")
 * @param {string} dateTimeString - ISO datetime string
 * @returns {string} - Time ago string
 */
function formatTimeAgo(dateTimeString) {
    if (!dateTimeString) return 'N/A';

    const date = new Date(dateTimeString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;

    return formatDate(dateTimeString);
}

/**
 * Get status badge HTML
 * @param {string} status - Status value
 * @returns {string} - HTML for status badge
 */
function getStatusBadge(status) {
    const statusMap = {
        'PENDING': { class: 'status-pending', text: 'Pending' },
        'IN_PROGRESS': { class: 'status-progress', text: 'In Progress' },
        'APPROVED': { class: 'status-progress', text: 'Approved' },
        'COMPLETED': { class: 'status-completed', text: 'Completed' },
        'CANCELLED': { class: 'status-cancelled', text: 'Cancelled' },
        'ACTIVE': { class: 'status-completed', text: 'Active' },
        'INACTIVE': { class: 'status-cancelled', text: 'Inactive' },
    };

    const statusInfo = statusMap[status] || { class: 'status-pending', text: status };
    return `<span class="status-tag ${statusInfo.class}">${statusInfo.text}</span>`;
}

/**
 * Get blood type badge HTML
 * @param {string} bloodType - Blood type
 * @returns {string} - HTML for blood type badge
 */
function getBloodTypeBadge(bloodType) {
    return `<span class="blood-type-tag">${bloodType}</span>`;
}

// =============================================================================
// Form Utilities
// =============================================================================

/**
 * Get form data as object
 * @param {HTMLFormElement} form - Form element
 * @returns {Object} - Form data as object
 */
function getFormData(form) {
    const formData = new FormData(form);
    const data = {};
    for (const [key, value] of formData.entries()) {
        data[key] = value;
    }
    return data;
}

/**
 * Clear form
 * @param {HTMLFormElement} form - Form element
 */
function clearForm(form) {
    form.reset();
}

/**
 * Disable form
 * @param {HTMLFormElement} form - Form element
 */
function disableForm(form) {
    const elements = form.elements;
    for (let i = 0; i < elements.length; i++) {
        elements[i].disabled = true;
    }
}

/**
 * Enable form
 * @param {HTMLFormElement} form - Form element
 */
function enableForm(form) {
    const elements = form.elements;
    for (let i = 0; i < elements.length; i++) {
        elements[i].disabled = false;
    }
}

// =============================================================================
// Blood Group Constants
// =============================================================================

const BLOOD_GROUPS = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'];

/**
 * Get blood group options HTML for select element
 * @param {string} selectedValue - Currently selected value
 * @returns {string} - HTML options
 */
function getBloodGroupOptions(selectedValue = '') {
    let options = '<option value="">Select Blood Group</option>';
    BLOOD_GROUPS.forEach(group => {
        const selected = group === selectedValue ? ' selected' : '';
        options += `<option value="${group}"${selected}>${group}</option>`;
    });
    return options;
}

// =============================================================================
// Modal Utilities
// =============================================================================

/**
 * Show modal
 * @param {string} modalId - Modal element ID
 */
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

/**
 * Hide modal
 * @param {string} modalId - Modal element ID
 */
function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}

// =============================================================================
// Initialize on page load
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    initializePage();
    setupLogoutHandlers();
});
