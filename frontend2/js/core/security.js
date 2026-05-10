/**
 * Bloodify Security Utilities
 * ============================
 * XSS protection and input sanitization for frontend rendering.
 * All user-supplied data MUST be passed through escapeHtml() before
 * being inserted into the DOM via innerHTML.
 */

(function () {
    'use strict';

    /**
     * Escape HTML special characters to prevent XSS attacks.
     * Use this for ALL user-supplied data rendered with innerHTML.
     * 
     * @param {string} str - Raw string (potentially from API/user input)
     * @returns {string} - HTML-safe string
     * 
     * @example
     *   row.innerHTML = `<td>${escapeHtml(donor.name)}</td>`;
     */
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        const text = String(str);
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;',
            '/': '&#x2F;',
        };
        return text.replace(/[&<>"'/]/g, char => map[char]);
    }

    /**
     * Sanitize an object's string values recursively.
     * Returns a new object with all string values escaped.
     * 
     * @param {Object} obj - Object with potentially unsafe string values
     * @returns {Object} - New object with escaped values
     */
    function sanitizeObject(obj) {
        if (typeof obj === 'string') return escapeHtml(obj);
        if (typeof obj !== 'object' || obj === null) return obj;
        if (Array.isArray(obj)) return obj.map(sanitizeObject);

        const sanitized = {};
        for (const [key, value] of Object.entries(obj)) {
            sanitized[key] = sanitizeObject(value);
        }
        return sanitized;
    }

    /**
     * Validate and sanitize a UUID string.
     * Prevents injection through ID parameters.
     * 
     * @param {string} uuid - UUID string to validate
     * @returns {string|null} - Valid UUID or null
     */
    function sanitizeUUID(uuid) {
        if (!uuid) return null;
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        return uuidRegex.test(uuid) ? uuid : null;
    }

    // Export globally
    window.escapeHtml = escapeHtml;
    window.sanitizeObject = sanitizeObject;
    window.sanitizeUUID = sanitizeUUID;
})();
