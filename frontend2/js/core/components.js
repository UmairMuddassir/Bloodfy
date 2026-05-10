/**
 * Bloodify Component Loader
 * =========================
 * Loads reusable HTML partials (sidebar, header) into pages.
 * This enables component reuse without a framework.
 */

(function () {
    'use strict';

    // Configuration
    const CONFIG = {
        partialsPath: '../partials/',
        adminPath: 'admin/',
    };

    /**
     * Load HTML partial into an element
     * @param {string} elementId - ID of target element
     * @param {string} partialPath - Path to partial HTML file
     * @returns {Promise<boolean>}
     */
    async function loadPartial(elementId, partialPath) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.warn(`Element #${elementId} not found`);
            return false;
        }

        try {
            const response = await fetch(partialPath);
            if (!response.ok) {
                throw new Error(`Failed to load ${partialPath}: ${response.status}`);
            }
            const html = await response.text();
            element.innerHTML = html;
            return true;
        } catch (error) {
            console.error(`Failed to load partial: ${partialPath}`, error);
            return false;
        }
    }

    /**
     * Mark the active navigation item based on current page
     */
    function markActiveNavItem() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const links = document.querySelectorAll('.sidebar__link');

        links.forEach(link => {
            const linkPage = link.getAttribute('data-page') || link.getAttribute('href');
            if (linkPage === currentPage) {
                link.classList.add('sidebar__link--active');
            } else {
                link.classList.remove('sidebar__link--active');
            }
        });
    }

    /**
     * Update page title based on current page
     */
    function updatePageTitle() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        const titles = {
            'index.html': 'Dashboard',
            'donors.html': 'Donor Management',
            'patients.html': 'Patient Requests',
            'blood-stock.html': 'Blood Stock',
            'staff.html': 'Staff Management',
            'analytics.html': 'Analytics',
            'emergency.html': 'Emergency Requests',
            'chatbot.html': 'AI Assistant',
            'notifications.html': 'Notifications',
            'settings.html': 'Settings',
        };

        const pageTitle = document.getElementById('pageTitle');
        if (pageTitle && titles[currentPage]) {
            pageTitle.textContent = titles[currentPage];
        }
    }

    /**
     * Setup logout button handler
     */
    function setupLogout() {
        const handleLogoutClick = (e) => {
            e.preventDefault();
            // Clear all auth data
            if (typeof clearAuthToken === 'function') {
                clearAuthToken();
            }
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user_data');
            localStorage.removeItem('bloodify_token');
            sessionStorage.clear();
            
            // Admin pages are at /admin/pages/ — need ../../ to reach /auth/
            window.location.href = '../../auth/user-login.html';
        };

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', handleLogoutClick);
        }

        const headerLogoutBtn = document.getElementById('headerLogoutBtn');
        if (headerLogoutBtn) {
            headerLogoutBtn.addEventListener('click', handleLogoutClick);
        }
    }

    /**
     * Setup mobile menu toggle
     */
    function setupMobileMenu() {
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');

        if (!menuToggle || !sidebar) return;

        menuToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('sidebar--active');
        });

        // Close sidebar when clicking on main content
        if (mainContent) {
            mainContent.addEventListener('click', () => {
                if (sidebar.classList.contains('sidebar--active')) {
                    sidebar.classList.remove('sidebar--active');
                }
            });
        }
    }

    /**
     * Setup user dropdown menu
     */
    function setupUserDropdown() {
        const userProfile = document.getElementById('userProfile');
        const userDropdown = document.getElementById('userDropdown');

        if (!userProfile || !userDropdown) return;

        // Toggle dropdown on click
        userProfile.addEventListener('click', (e) => {
            e.stopPropagation();
            userDropdown.classList.toggle('header__user-dropdown--active');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!userProfile.contains(e.target)) {
                userDropdown.classList.remove('header__user-dropdown--active');
            }
        });
    }

    /**
     * Update user info in header
     */
    function updateUserInfo() {
        if (typeof getUserData === 'function') {
            const user = getUserData();
            if (user) {
                const userName = document.getElementById('userName');
                const userRole = document.getElementById('userRole');
                const pageSubtitle = document.getElementById('pageSubtitle');

                if (userName) {
                    userName.textContent = user.first_name || user.name || user.email || 'Admin';
                }
                if (userRole) {
                    userRole.textContent = (user.user_type || 'admin').charAt(0).toUpperCase() +
                        (user.user_type || 'admin').slice(1);
                }
                if (pageSubtitle) {
                    pageSubtitle.textContent = `Welcome back, ${user.first_name || 'Admin'}`;
                }
            }
        }
    }

    /**
     * Initialize admin components
     */
    async function initAdminComponents() {
        // Check if we're on an admin page
        if (!document.body.classList.contains('admin-layout')) {
            return;
        }

        const basePath = CONFIG.partialsPath + CONFIG.adminPath;

        // Load sidebar
        const sidebarLoaded = await loadPartial('adminSidebar', basePath + 'sidebar.html');

        // Load header
        const headerLoaded = await loadPartial('adminHeader', basePath + 'header.html');

        // Setup after components are loaded
        if (sidebarLoaded) {
            markActiveNavItem();
            setupLogout(); // Also handles sidebar logout
        }

        if (headerLoaded) {
            updatePageTitle();
            updateUserInfo();
            setupUserDropdown();
            setupLogout(); // Also handles header logout if header loaded later
            setupMobileMenu(); // Setup mobile menu after header is loaded
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAdminComponents);
    } else {
        initAdminComponents();
    }

    // Export for external use
    window.BloodfyComponents = {
        loadPartial,
        markActiveNavItem,
        updatePageTitle,
        updateUserInfo,
    };
})();
