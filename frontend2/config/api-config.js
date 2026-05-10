/**
 * Bloodify Frontend API Configuration
 * 
 * This file centralizes all API endpoint configurations and provides
 * utility functions for making HTTP requests to the Django backend.
 */

// =============================================================================
// API Configuration
// =============================================================================

const API_CONFIG = {
    // Base URL for the backend API (Production Render)
    BASE_URL: 'https://bloodify-api-gin9.onrender.com/api',

    // Request timeout in milliseconds
    TIMEOUT: 30000,

    // Enable/disable request logging
    DEBUG: true,
};

// =============================================================================
// API Endpoints
// =============================================================================

const API_ENDPOINTS = {
    // Authentication
    AUTH: {
        REGISTER: '/auth/register/',
        LOGIN: '/auth/login/',
        LOGOUT: '/auth/logout/',
        REFRESH: '/auth/refresh/',
        VERIFY_EMAIL: '/auth/verify-email/',
        RESEND_OTP: '/auth/resend-otp/',
        REQUEST_PASSWORD_RESET: '/auth/request-password-reset/',
        RESET_PASSWORD: '/auth/reset-password/',
    },

    // Donors
    DONORS: {
        LIST: '/donors/',
        REGISTER: '/donors/register/',
        CREATE: '/donors/create/',
        DETAIL: (donorId) => `/donors/${donorId}/`,
        ELIGIBILITY: '/donors/eligibility-status/',
        STATISTICS: '/donors/statistics/',
        DONATION_HISTORY: (donorId) => `/donors/${donorId}/donation-history/`,
        REACTIVATE: (donorId) => `/donors/${donorId}/reactivate/`,
        PENDING: '/donors/pending/',
        APPROVE: (requestId) => `/donors/requests/${requestId}/approve/`,
    },

    // Blood Requests (Patient Requests)
    REQUESTS: {
        LIST: '/blood-requests/',
        DETAIL: (requestId) => `/blood-requests/${requestId}/`,
        APPROVE: (requestId) => `/blood-requests/${requestId}/approve/`,
        ASSIGN: (requestId) => `/blood-requests/${requestId}/assign/`,
        COMPLETE: (requestId) => `/blood-requests/${requestId}/complete/`,
        MATCHED_DONORS: (requestId) => `/blood-requests/${requestId}/matched-donors/`,
        DONOR_RESPONSES: '/blood-requests/responses/',
    },

    // Emergency (correct backend URL)
    EMERGENCY: {
        SEARCH: '/donors/emergency/search/',
        CONTACT: '/donors/emergency/contact/',
    },

    // Blood Stock
    BLOOD_STOCK: {
        LIST: '/blood-stock/',
        DETAIL: (stockId) => `/blood-stock/${stockId}/`,
        STATISTICS: '/blood-stock/statistics/',
        EXPORT: '/blood-stock/export/',
        IMPORT: '/blood-stock/import/',
    },

    // AI Engine
    AI: {
        RANK_DONORS: '/ai/rank-donors/',
        RANKING_HISTORY: (requestId) => `/ai/ranking-history/${requestId}/`,
        REACTIVATION_CHECK: '/ai/reactivation-check/',
        METRICS: '/ai/metrics/',
    },

    // Chatbot
    CHATBOT: {
        QUERY: '/chatbot/query/',
        FAQS: '/chatbot/faqs/',
        FAQ_DETAIL: (faqId) => `/chatbot/faqs/${faqId}/`,
        FAQ_MANAGE: '/chatbot/faqs/manage/',
        FEEDBACK: '/chatbot/feedback/',
    },

    // Notifications
    NOTIFICATIONS: {
        LIST: '/notifications/',
        SEND_BULK: '/notifications/send-bulk/',
        MARK_READ: (notificationId) => `/notifications/${notificationId}/mark-read/`,
        APP_LIST: '/notifications/app/',
        APP_MARK_READ: (notificationId) => notificationId
            ? `/notifications/app/${notificationId}/`
            : '/notifications/app/',
    },

    // Users
    USERS: {
        LIST: '/users/',
        DETAIL: (userId) => `/users/${userId}/`,
        PROFILE: '/users/profile/',
        CHANGE_PASSWORD: '/users/change-password/',
    },
};

// =============================================================================
// HTTP Request Utility
// =============================================================================

/**
 * Make an HTTP request to the API
 * @param {string} endpoint - The API endpoint
 * @param {Object} options - Request options
 * @returns {Promise<Object>} - Response data
 */
async function apiRequest(endpoint, options = {}) {
    const {
        method = 'GET',
        body = null,
        headers = {},
        requiresAuth = true,
    } = options;

    // Build request URL
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;

    // Prepare headers
    const requestHeaders = {
        'Content-Type': 'application/json',
        ...headers,
    };

    // Add authentication token if required
    if (requiresAuth) {
        const token = getAuthToken();
        if (token) {
            requestHeaders['Authorization'] = `Bearer ${token}`;
        }
    }

    // Prepare request configuration
    const requestConfig = {
        method,
        headers: requestHeaders,
    };

    // Add body for non-GET requests
    if (body && method !== 'GET') {
        requestConfig.body = JSON.stringify(body);
    }

    // Log request in debug mode
    if (API_CONFIG.DEBUG) {
        console.log(`[API] ${method} ${endpoint}`, body || '');
    }

    try {
        // Make the request
        const response = await fetch(url, requestConfig);

        // Parse response
        const data = await response.json();

        // Log response in debug mode
        if (API_CONFIG.DEBUG) {
            console.log(`[API] Response:`, data);
        }

        // Handle errors
        if (!response.ok) {
            throw {
                status: response.status,
                message: data.message || 'Request failed',
                errors: data.errors || {},
                data: data,
            };
        }

        return data;
    } catch (error) {
        // Log errors
        if (API_CONFIG.DEBUG) {
            console.error(`[API] Error:`, error);
        }

        // Re-throw for handling by caller
        throw error;
    }
}

// =============================================================================
// Authentication Helpers
// =============================================================================

/**
 * Get authentication token from localStorage
 * @returns {string|null} - The auth token
 */
function getAuthToken() {
    return localStorage.getItem('bloodify_auth_token');
}

/**
 * Set authentication token in localStorage
 * @param {string} token - The auth token
 */
function setAuthToken(token) {
    localStorage.setItem('bloodify_auth_token', token);
}

/**
 * Remove authentication token from localStorage
 */
function clearAuthToken() {
    localStorage.removeItem('bloodify_auth_token');
    localStorage.removeItem('bloodify_refresh_token');
    localStorage.removeItem('bloodify_user_data');
}

/**
 * Get user data from localStorage
 * @returns {Object|null} - User data
 */
function getUserData() {
    const data = localStorage.getItem('bloodify_user_data');
    return data ? JSON.parse(data) : null;
}

/**
 * Set user data in localStorage
 * @param {Object} userData - User data object
 */
function setUserData(userData) {
    localStorage.setItem('bloodify_user_data', JSON.stringify(userData));
}

/**
 * Check if user is authenticated
 * @returns {boolean} - True if authenticated
 */
function isAuthenticated() {
    return !!getAuthToken();
}

// =============================================================================
// API Service Methods
// =============================================================================

const API = {
    // Authentication
    auth: {
        async login(email, password) {
            const data = await apiRequest(API_ENDPOINTS.AUTH.LOGIN, {
                method: 'POST',
                body: { email, password },
                requiresAuth: false,
            });

            if (data.success && data.data.tokens && data.data.tokens.access) {
                setAuthToken(data.data.tokens.access);
                // Store refresh token for token refresh & logout
                if (data.data.tokens.refresh) {
                    localStorage.setItem('bloodify_refresh_token', data.data.tokens.refresh);
                }
                setUserData(data.data.user);
            }

            return data;
        },

        async register(userData) {
            return await apiRequest(API_ENDPOINTS.AUTH.REGISTER, {
                method: 'POST',
                body: userData,
                requiresAuth: false,
            });
        },

        async logout() {
            try {
                const refreshToken = localStorage.getItem('bloodify_refresh_token');
                await apiRequest(API_ENDPOINTS.AUTH.LOGOUT, {
                    method: 'POST',
                    body: refreshToken ? { refresh: refreshToken } : {},
                });
            } finally {
                clearAuthToken();
            }
        },
    },

    // Donors
    donors: {
        async getList(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const endpoint = queryString
                ? `${API_ENDPOINTS.DONORS.LIST}?${queryString}`
                : API_ENDPOINTS.DONORS.LIST;
            return await apiRequest(endpoint);
        },

        async getDetail(donorId) {
            return await apiRequest(API_ENDPOINTS.DONORS.DETAIL(donorId));
        },

        async register(donorData) {
            return await apiRequest(API_ENDPOINTS.DONORS.REGISTER, {
                method: 'POST',
                body: donorData,
            });
        },

        async create(donorData) {
            return await apiRequest(API_ENDPOINTS.DONORS.CREATE, {
                method: 'POST',
                body: donorData,
            });
        },

        async updateDonor(donorId, donorData) {
            return await apiRequest(API_ENDPOINTS.DONORS.DETAIL(donorId), {
                method: 'PUT',
                body: donorData,
            });
        },

        async getDonationHistory(donorId) {
            return await apiRequest(API_ENDPOINTS.DONORS.DONATION_HISTORY(donorId));
        },

        async getStatistics() {
            return await apiRequest(API_ENDPOINTS.DONORS.STATISTICS);
        },
        async getPendingRequests() {
            return await apiRequest(API_ENDPOINTS.DONORS.PENDING);
        },
        async approveRequest(requestId, action, reason = '') {
            return await apiRequest(API_ENDPOINTS.DONORS.APPROVE(requestId), {
                method: 'POST',
                body: { action, rejection_reason: reason }
            });
        },
    },

    // Blood Requests (Patients)
    requests: {
        async getList(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const endpoint = queryString
                ? `${API_ENDPOINTS.REQUESTS.LIST}?${queryString}`
                : API_ENDPOINTS.REQUESTS.LIST;
            return await apiRequest(endpoint);
        },

        async create(requestData) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.LIST, {
                method: 'POST',
                body: requestData,
            });
        },

        async getDetail(requestId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.DETAIL(requestId));
        },

        async update(requestId, updateData) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.DETAIL(requestId), {
                method: 'PUT',
                body: updateData,
            });
        },

        async delete(requestId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.DETAIL(requestId), {
                method: 'DELETE',
            });
        },

        async approve(requestId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.APPROVE(requestId), {
                method: 'POST',
            });
        },

        async complete(requestId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.COMPLETE(requestId), {
                method: 'POST',
            });
        },

        async assignDonor(requestId, donorId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.ASSIGN(requestId), {
                method: 'POST',
                body: { donor_id: donorId },
            });
        },

        async getMatchedDonors(requestId) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.MATCHED_DONORS(requestId));
        },

        async emergencySearch(searchData) {
            return await apiRequest(API_ENDPOINTS.REQUESTS.EMERGENCY_SEARCH, {
                method: 'POST',
                body: searchData,
            });
        },
    },

    // Blood Stock
    bloodStock: {
        async getList(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const endpoint = queryString
                ? `${API_ENDPOINTS.BLOOD_STOCK.LIST}?${queryString}`
                : API_ENDPOINTS.BLOOD_STOCK.LIST;
            return await apiRequest(endpoint);
        },

        async create(stockData) {
            return await apiRequest(API_ENDPOINTS.BLOOD_STOCK.LIST, {
                method: 'POST',
                body: stockData,
            });
        },

        async update(stockId, stockData) {
            return await apiRequest(API_ENDPOINTS.BLOOD_STOCK.DETAIL(stockId), {
                method: 'PUT',
                body: stockData,
            });
        },

        async delete(stockId) {
            return await apiRequest(API_ENDPOINTS.BLOOD_STOCK.DETAIL(stockId), {
                method: 'DELETE',
            });
        },

        async getStatistics() {
            return await apiRequest(API_ENDPOINTS.BLOOD_STOCK.STATISTICS);
        },

        async exportData() {
            return await apiRequest(API_ENDPOINTS.BLOOD_STOCK.EXPORT);
        },
    },

    // Notifications
    notifications: {
        async getAppNotifications() {
            return await apiRequest(API_ENDPOINTS.NOTIFICATIONS.APP_LIST);
        },
        async markAppAsRead(notificationId = null) {
            return await apiRequest(API_ENDPOINTS.NOTIFICATIONS.APP_MARK_READ(notificationId), {
                method: 'POST'
            });
        },
        async sendBulk(data) {
            return await apiRequest(API_ENDPOINTS.NOTIFICATIONS.SEND_BULK, {
                method: 'POST',
                body: data
            });
        }
    },

    // Emergency Donor Search
    emergency: {
        async search(blood_group, location, latitude = null, longitude = null) {
            const params = new URLSearchParams({ blood_group, location });
            if (latitude) params.append('latitude', latitude);
            if (longitude) params.append('longitude', longitude);
            return await apiRequest(`${API_ENDPOINTS.EMERGENCY.SEARCH}?${params.toString()}`);
        },
        async contact(donor_id, contact_type = 'SMS') {
            return await apiRequest(API_ENDPOINTS.EMERGENCY.CONTACT, {
                method: 'POST',
                body: { donor_id, contact_type }
            });
        }
    },

    // AI Engine
    ai: {
        async rankDonors(requestData) {
            return await apiRequest(API_ENDPOINTS.AI.RANK_DONORS, {
                method: 'POST',
                body: requestData,
            });
        },

        async getMetrics() {
            return await apiRequest(API_ENDPOINTS.AI.METRICS);
        },
    },

    // Chatbot (public — no auth required)
    chatbot: {
        async sendQuery(query) {
            return await apiRequest(API_ENDPOINTS.CHATBOT.QUERY, {
                method: 'POST',
                body: { message: query },
                requiresAuth: false,
            });
        },

        async getFAQs() {
            return await apiRequest(API_ENDPOINTS.CHATBOT.FAQS, {
                requiresAuth: false,
            });
        },
    },

    // Users
    users: {
        async getList(params = {}) {
            const queryString = new URLSearchParams(params).toString();
            const endpoint = queryString
                ? `${API_ENDPOINTS.USERS.LIST}?${queryString}`
                : API_ENDPOINTS.USERS.LIST;
            return await apiRequest(endpoint);
        },

        async getDetail(userId) {
            return await apiRequest(API_ENDPOINTS.USERS.DETAIL(userId));
        },

        async getProfile() {
            return await apiRequest(API_ENDPOINTS.USERS.PROFILE);
        },

        async updateProfile(userData) {
            return await apiRequest(API_ENDPOINTS.USERS.PROFILE, {
                method: 'PUT',
                body: userData,
            });
        },

        async changePassword(passwordData) {
            return await apiRequest(API_ENDPOINTS.USERS.CHANGE_PASSWORD, {
                method: 'POST',
                body: passwordData,
            });
        },

        async createUser(userData) {
            return await apiRequest(API_ENDPOINTS.USERS.LIST, {
                method: 'POST',
                body: userData,
            });
        },

        async deleteUser(userId) {
            return await apiRequest(API_ENDPOINTS.USERS.DETAIL(userId), {
                method: 'DELETE',
            });
        },
    },
};

/**
 * Check if user is authenticated
 * @returns {boolean} - True if authenticated
 */
function isAuthenticated() {
    return !!getAuthToken();
}

/**
 * Check if user is an admin
 * @returns {boolean} - True if user has admin role
 */
function isAdmin() {
    const user = getUserData();
    if (!user) return false;
    const type = user.user_type || user.role || '';
    return ['admin', 'ADMIN', 'staff', 'STAFF'].includes(type) || user.is_staff === true || user.is_superuser === true;
}

// =============================================================================
// Export
// =============================================================================

// Make API available globally for use in HTML pages
window.API = API;
window.API_CONFIG = API_CONFIG;
window.isAuthenticated = isAuthenticated;
window.getUserData = getUserData;
window.isAdmin = isAdmin;
window.clearAuthToken = clearAuthToken;
