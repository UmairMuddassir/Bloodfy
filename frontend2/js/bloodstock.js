/**
 * Blood Stock Integration Script - COMPLETE VERSION
 * Loads and manages blood stock inventory with full CRUD operations
 */

document.addEventListener('DOMContentLoaded', async () => {
    // =============================================================================
    // Load Blood Stock Grid Cards
    // =============================================================================

    async function loadBloodStockCards() {
        try {
            const stockData = await API.bloodStock.getStatistics();

            if (stockData.success && stockData.data && stockData.data.by_blood_group) {
                const bloodGrid = document.querySelector('.blood-grid');
                if (!bloodGrid) return;

                // Clear existing cards
                bloodGrid.innerHTML = '';

                // Blood groups in order
                const bloodGroups = ['A+', 'B+', 'O+', 'AB+', 'A-', 'B-', 'O-', 'AB-'];

                bloodGroups.forEach(bloodGroup => {
                    const stockInfo = stockData.data.by_blood_group[bloodGroup] || { units: 0, percentage: 0 };
                    const units = stockInfo.units || 0;
                    const percentage = Math.round(stockInfo.percentage || 0);

                    // Determine if critical (below 20%)
                    const isCritical = percentage < 20;

                    // Create card
                    const card = document.createElement('div');
                    card.className = `blood-card ${isCritical ? 'critical' : ''}`;
                    card.innerHTML = `
                        <div class="blood-type">${bloodGroup}</div>
                        <div class="blood-units">${units} Units${isCritical ? ' (Low)' : ''}</div>
                        <div class="liquid-bg" style="height: ${percentage}%;"></div>
                    `;

                    bloodGrid.appendChild(card);
                });
            }
        } catch (error) {
            console.error('Error loading blood stock cards:', error);
        }
    }

    // =============================================================================
    // Load Blood Stock Table
    // =============================================================================

    async function loadBloodStockTable() {
        try {
            const stockData = await API.bloodStock.getList();

            if (stockData.success && stockData.data) {
                const tableBody = document.querySelector('.table-body');
                if (!tableBody) return;

                // Clear existing rows
                tableBody.innerHTML = '';

                const stocks = Array.isArray(stockData.data) ? stockData.data : (stockData.data.blood_stock || stockData.data.results || []);

                if (stocks.length === 0) {
                    tableBody.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary);">No stock records found</p>';
                    return;
                }

                stocks.forEach(stock => {
                    const row = document.createElement('div');
                    row.className = 'custom-table-row';
                    row.dataset.stockId = stock.id;

                    const isCritical = stock.units_available < 20;

                    row.innerHTML = `
                        <div><span class="blood-badge">${stock.blood_group}</span></div>
                        <div>${stock.hospital_name || 'N/A'}</div>
                        <div ${isCritical ? 'style="color: #FF5252; font-weight: bold;"' : ''}>
                            ${stock.units_available}${isCritical ? ' (Critical)' : ''}
                        </div>
                        <div>${formatTimeAgo(stock.last_updated || stock.updated_at)}</div>
                        <div>
                            <button class="btn-action" onclick="editStock('${stock.id}')" title="Edit">
                                <i class="fa-solid fa-pen"></i>
                            </button>
                            <button class="btn-action" onclick="deleteStock('${stock.id}')" title="Delete">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    `;

                    tableBody.appendChild(row);
                });
            }
        } catch (error) {
            console.error('Error loading blood stock table:', error);
        }
    }

    // =============================================================================
    // CREATE STOCK MODAL
    // =============================================================================

    window.showCreateStockModal = function () {
        let modal = document.getElementById('createStockModal');

        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'createStockModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Add Blood Stock</h2>
                        <button class="modal-close" onclick="closeCreateStockModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="createStockForm">
                            <div class="form-row">
                                <div class="form-group">
                                    <label for="bloodGroup">Blood Group *</label>
                                    <select id="bloodGroup" name="blood_group" class="form-input" required>
                                        <option value="">Select Blood Group</option>
                                        <option value="A+">A+</option>
                                        <option value="A-">A-</option>
                                        <option value="B+">B+</option>
                                        <option value="B-">B-</option>
                                        <option value="O+">O+</option>
                                        <option value="O-">O-</option>
                                        <option value="AB+">AB+</option>
                                        <option value="AB-">AB-</option>
                                    </select>
                                </div>
                                
                                <div class="form-group">
                                    <label for="unitsAvailable">Units Available *</label>
                                    <input type="number" id="unitsAvailable" name="units_available" class="form-input" min="0" required>
                                </div>
                            </div>
                            
                            <div class="form-group">
                                <label for="hospitalName">Hospital Name *</label>
                                <input type="text" id="hospitalName" name="hospital_name" class="form-input" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="hospitalCity">City *</label>
                                <input type="text" id="hospitalCity" name="hospital_city" class="form-input" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="contactNumber">Contact Number</label>
                                <input type="tel" id="contactNumber" name="contact_number" class="form-input" placeholder="+92-300-1234567">
                            </div>
                            
                            <div class="form-actions">
                                <button type="button" class="btn-secondary" onclick="closeCreateStockModal()">Cancel</button>
                                <button type="submit" class="btn-primary">
                                    <i class="fas fa-plus"></i> Add Stock
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        modal.style.display = 'flex';

        // Setup form submission
        const form = document.getElementById('createStockForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            await handleCreateStock(new FormData(form));
        };
    };

    window.closeCreateStockModal = function () {
        const modal = document.getElementById('createStockModal');
        if (modal) {
            modal.style.display = 'none';
            document.getElementById('createStockForm')?.reset();
        }
    };

    async function handleCreateStock(formData) {
        const stockData = {
            blood_group: formData.get('blood_group'),
            units_available: parseInt(formData.get('units_available')),
            hospital_name: formData.get('hospital_name'),
            hospital_city: formData.get('hospital_city'),
            contact_number: formData.get('contact_number') || undefined,
        };

        try {
            const result = await API.bloodStock.create(stockData);

            if (result.success) {
                showSuccess('Blood stock added successfully!');
                closeCreateStockModal();
                await loadBloodStockCards();
                await loadBloodStockTable();
            }
        } catch (error) {
            console.error('Error creating stock:', error);
            showError(error.message || 'Failed to add blood stock');
        }
    }

    // =============================================================================
    // UPDATE STOCK MODAL
    // =============================================================================

    window.showUpdateStockModal = function () {
        let modal = document.getElementById('updateStockModal');

        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'updateStockModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Update Stock Units</h2>
                        <button class="modal-close" onclick="closeUpdateStockModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="updateStockForm">
                            <div class="form-group">
                                <label for="stockSelect">Select Blood Stock *</label>
                                <select id="stockSelect" class="form-input" required>
                                    <option value="">Loading...</option>
                                </select>
                            </div>
                            
                            <div class="form-group">
                                <label for="addUnits">Add Units</label>
                                <input type="number" id="addUnits" class="form-input" min="0" value="0">
                            </div>
                            
                            <div class="form-group">
                                <label for="removeUnits">Remove Units</label>
                                <input type="number" id="removeUnits" class="form-input" min="0" value="0">
                            </div>
                            
                            <div class="form-actions">
                                <button type="button" class="btn-secondary" onclick="closeUpdateStockModal()">Cancel</button>
                                <button type="submit" class="btn-primary">
                                    <i class="fas fa-sync"></i> Update Stock
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);

            // Load stock list
            loadStockListForUpdate();
        }

        modal.style.display = 'flex';

        // Setup form submission
        const form = document.getElementById('updateStockForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            await handleUpdateStock();
        };
    };

    window.closeUpdateStockModal = function () {
        const modal = document.getElementById('updateStockModal');
        if (modal) {
            modal.style.display = 'none';
            document.getElementById('updateStockForm')?.reset();
        }
    };

    async function loadStockListForUpdate() {
        try {
            const result = await API.bloodStock.getList();
            const select = document.getElementById('stockSelect');

            if (result.success && result.data && select) {
                const stocks = Array.isArray(result.data) ? result.data : (result.data.blood_stock || result.data.results || []);

                select.innerHTML = '<option value="">Select a stock entry</option>';
                stocks.forEach(stock => {
                    const option = document.createElement('option');
                    option.value = stock.id;
                    option.textContent = `${stock.blood_group} - ${stock.hospital_name} (${stock.units_available} units)`;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading stock list:', error);
        }
    }

    async function handleUpdateStock() {
        const stockId = document.getElementById('stockSelect').value;
        const addUnits = parseInt(document.getElementById('addUnits').value) || 0;
        const removeUnits = parseInt(document.getElementById('removeUnits').value) || 0;

        if (!stockId) {
            showError('Please select a stock entry');
            return;
        }

        if (addUnits === 0 && removeUnits === 0) {
            showError('Please specify units to add or remove');
            return;
        }

        try {
            // Get current stock
            const currentStock = await API.bloodStock.getDetail(stockId);

            if (currentStock.success && currentStock.data) {
                const currentUnits = currentStock.data.units_available || 0;
                const newUnits = currentUnits + addUnits - removeUnits;

                if (newUnits < 0) {
                    showError('Cannot remove more units than available');
                    return;
                }

                const result = await API.bloodStock.update(stockId, {
                    units_available: newUnits
                });

                if (result.success) {
                    showSuccess('Stock updated successfully!');
                    closeUpdateStockModal();
                    await loadBloodStockCards();
                    await loadBloodStockTable();
                }
            }
        } catch (error) {
            console.error('Error updating stock:', error);
            showError(error.message || 'Failed to update stock');
        }
    }

    // =============================================================================
    // EDIT STOCK MODAL
    // =============================================================================

    window.editStock = async function (stockId) {
        try {
            const result = await API.bloodStock.getDetail(stockId);

            if (result.success && result.data) {
                showEditStockModal(result.data);
            }
        } catch (error) {
            console.error('Error loading stock details:', error);
            showError('Failed to load stock details');
        }
    };

    function showEditStockModal(stock) {
        let modal = document.getElementById('editStockModal');

        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'editStockModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h2>Edit Blood Stock</h2>
                        <button class="modal-close" onclick="closeEditStockModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="editStockForm">
                            <input type="hidden" id="editStockId" name="stock_id">
                            
                            <div class="form-group">
                                <label for="editBloodGroup">Blood Group *</label>
                                <input type="text" id="editBloodGroup" class="form-input" readonly>
                            </div>
                            
                            <div class="form-group">
                                <label for="editUnitsAvailable">Units Available *</label>
                                <input type="number" id="editUnitsAvailable" name="units_available" class="form-input" min="0" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="editHospitalName">Hospital Name *</label>
                                <input type="text" id="editHospitalName" name="hospital_name" class="form-input" required>
                            </div>
                            
                            <div class="form-group">
                                <label for="editContactNumber">Contact Number</label>
                                <input type="tel" id="editContactNumber" name="contact_number" class="form-input">
                            </div>
                            
                            <div class="form-actions">
                                <button type="button" class="btn-secondary" onclick="closeEditStockModal()">Cancel</button>
                                <button type="submit" class="btn-primary">
                                    <i class="fas fa-save"></i> Save Changes
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        // Populate form
        document.getElementById('editStockId').value = stock.id;
        document.getElementById('editBloodGroup').value = stock.blood_group;
        document.getElementById('editUnitsAvailable').value = stock.units_available;
        document.getElementById('editHospitalName').value = stock.hospital_name;
        document.getElementById('editContactNumber').value = stock.contact_number || '';

        modal.style.display = 'flex';

        // Setup form submission
        const form = document.getElementById('editStockForm');
        form.onsubmit = async (e) => {
            e.preventDefault();
            await handleEditStock(new FormData(form));
        };
    }

    window.closeEditStockModal = function () {
        const modal = document.getElementById('editStockModal');
        if (modal) {
            modal.style.display = 'none';
        }
    };

    async function handleEditStock(formData) {
        const stockId = formData.get('stock_id');
        const updateData = {
            units_available: parseInt(formData.get('units_available')),
            hospital_name: formData.get('hospital_name'),
            contact_number: formData.get('contact_number') || undefined,
        };

        try {
            const result = await API.bloodStock.update(stockId, updateData);

            if (result.success) {
                showSuccess('Stock updated successfully!');
                closeEditStockModal();
                await loadBloodStockCards();
                await loadBloodStockTable();
            }
        } catch (error) {
            console.error('Error updating stock:', error);
            showError(error.message || 'Failed to update stock');
        }
    }

    // =============================================================================
    // DELETE STOCK
    // =============================================================================

    window.deleteStock = async function (stockId) {
        if (!confirm('Are you sure you want to delete this stock entry?')) {
            return;
        }

        try {
            const result = await API.bloodStock.delete(stockId);

            if (result.success) {
                showSuccess('Stock entry deleted successfully');
                await loadBloodStockCards();
                await loadBloodStockTable();
            }
        } catch (error) {
            showError(error.message || 'Failed to delete stock entry');
        }
    };

    // =============================================================================
    // EXPORT TO CSV
    // =============================================================================

    window.exportStockToCSV = async function () {
        try {
            showSuccess('Generating CSV export from server...');

            const token = getAuthToken();
            const response = await fetch(`${API_CONFIG.BASE_URL}/blood-stock/export/`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `blood_stock_${new Date().toISOString().split('T')[0]}.csv`;
                link.click();
                URL.revokeObjectURL(url);

                showSuccess('CSV exported successfully!');
            } else {
                showError('Failed to export CSV from server');
            }
        } catch (error) {
            console.error('Error exporting CSV:', error);
            showError('Failed to export CSV');
        }
    };

    // =============================================================================
    // SETUP BUTTONS
    // =============================================================================

    function setupButtons() {
        // Create Stock Button
        const createBtn = document.getElementById('btnAddStock');
        if (createBtn) {
            createBtn.addEventListener('click', (e) => {
                e.preventDefault();
                showCreateStockModal();
            });
        }

        // Update Stock Button  
        const updateBtn = document.getElementById('btnUpdateStock');
        if (updateBtn) {
            updateBtn.addEventListener('click', (e) => {
                e.preventDefault();
                showUpdateStockModal();
            });
        }

        // Export CSV Button
        const exportBtn = document.getElementById('btnExportStock');
        if (exportBtn) {
            exportBtn.addEventListener('click', (e) => {
                e.preventDefault();
                exportStockToCSV();
            });
        }
    }

    // =============================================================================
    // Initialize Blood Stock Page
    // =============================================================================

    async function initializeBloodStock() {
        console.log('Loading blood stock data...');

        await Promise.all([
            loadBloodStockCards(),
            loadBloodStockTable()
        ]);

        setupButtons();

        console.log('Blood stock data loaded');
    }

    // Only run on bloodstock page
    if (window.location.pathname.includes('bloodstock.html') ||
        document.querySelector('.stock-main')) {
        initializeBloodStock();
    }
});
