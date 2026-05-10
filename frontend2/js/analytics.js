/**
 * Analytics Page Integration Script
 * Fetches real data from the backend API and populates the analytics dashboard.
 */

document.addEventListener('DOMContentLoaded', async () => {
    await initializeAnalyticsPage();
});

// =============================================================================
// ANALYTICS PAGE
// =============================================================================

async function initializeAnalyticsPage() {
    // Load all statistics in parallel
    await Promise.allSettled([
        loadDonorStats(),
        loadBloodStockStats(),
        loadAIMetrics(),
    ]);
}

// =============================================================================
// LOAD DONOR STATISTICS
// =============================================================================

async function loadDonorStats() {
    try {
        const result = await API.donors.getStatistics();

        if (result.success && result.data) {
            displayDonorStats(result.data);
        }
    } catch (error) {
        console.error('Error loading donor stats:', error);
        setFallbackDonorStats();
    }
}

function displayDonorStats(stats) {
    // Top stat cards
    const totalDonorsEl = document.getElementById('totalDonors');
    if (totalDonorsEl) totalDonorsEl.textContent = stats.total_donors || 0;

    const activeDonorsEl = document.getElementById('activeDonors');
    if (activeDonorsEl) activeDonorsEl.textContent = stats.active_donors || stats.total_active_donors || 0;

    // Donor info list
    const infoTotalEl = document.getElementById('infoTotalDonors');
    if (infoTotalEl) infoTotalEl.textContent = stats.total_donors || 0;

    const infoActiveEl = document.getElementById('infoActiveDonors');
    if (infoActiveEl) infoActiveEl.textContent = stats.active_donors || stats.total_active_donors || 0;

    const infoEligibleEl = document.getElementById('infoEligibleDonors');
    if (infoEligibleEl) infoEligibleEl.textContent = stats.eligible_donors || 0;

    const infoResponseEl = document.getElementById('infoResponseRate');
    if (infoResponseEl) {
        const rate = stats.average_response_rate || 0;
        infoResponseEl.textContent = rate > 0 ? rate + '%' : 'N/A';
    }

    // Eligible donors circle
    const eligibleCircle = document.getElementById('eligibleDonorsCircle');
    if (eligibleCircle) eligibleCircle.textContent = stats.eligible_donors || 0;
}

function setFallbackDonorStats() {
    ['totalDonors', 'activeDonors', 'infoTotalDonors', 'infoActiveDonors', 'infoEligibleDonors'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '0';
    });
    const rateEl = document.getElementById('infoResponseRate');
    if (rateEl) rateEl.textContent = 'N/A';
    const eligCircle = document.getElementById('eligibleDonorsCircle');
    if (eligCircle) eligCircle.textContent = '0';
}

// =============================================================================
// LOAD BLOOD STOCK STATISTICS
// =============================================================================

async function loadBloodStockStats() {
    try {
        const result = await API.bloodStock.getStatistics();

        if (result.success && result.data) {
            displayBloodStockStats(result.data);
        }
    } catch (error) {
        console.error('Error loading blood stock stats:', error);
        setFallbackStockStats();
    }
}

function displayBloodStockStats(stats) {
    // Top stat cards
    const totalUnitsEl = document.getElementById('totalUnits');
    if (totalUnitsEl) totalUnitsEl.textContent = stats.total_units || stats.total_available || 0;

    const criticalStockEl = document.getElementById('criticalStock');
    if (criticalStockEl) {
        const criticalCount = stats.critical_stocks ? stats.critical_stocks.length : 0;
        criticalStockEl.textContent = criticalCount;
    }

    // Stock info list
    const infoAvailableEl = document.getElementById('infoTotalAvailable');
    if (infoAvailableEl) infoAvailableEl.textContent = (stats.total_available || 0) + ' units';

    const infoReservedEl = document.getElementById('infoReserved');
    if (infoReservedEl) infoReservedEl.textContent = (stats.total_reserved || 0) + ' units';

    const infoExpiredEl = document.getElementById('infoExpired');
    if (infoExpiredEl) infoExpiredEl.textContent = (stats.total_expired || 0) + ' units';

    const infoHealthEl = document.getElementById('infoInventoryHealth');
    if (infoHealthEl) {
        const pct = Math.round(stats.inventory_percentage || 0);
        infoHealthEl.textContent = pct + '%';
        if (pct >= 60) {
            infoHealthEl.className = 'value good';
        } else if (pct >= 30) {
            infoHealthEl.className = 'value';
        } else {
            infoHealthEl.className = 'value critical';
        }
    }

    // Display blood group distribution bar chart
    if (stats.by_blood_group) {
        displayBloodGroupChart(stats.by_blood_group);
    }
}

function setFallbackStockStats() {
    ['totalUnits', 'criticalStock'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '0';
    });
    const chartEl = document.getElementById('bloodGroupChart');
    if (chartEl) {
        chartEl.innerHTML = '<div style="color: var(--text-secondary); text-align: center; width: 100%; padding: 60px 0;">No blood stock data available</div>';
    }
}

// =============================================================================
// LOAD AI METRICS
// =============================================================================

async function loadAIMetrics() {
    try {
        const result = await API.ai.getMetrics();

        if (result.success && result.data) {
            displayAIMetrics(result.data);
        }
    } catch (error) {
        console.error('Error loading AI metrics:', error);
        setFallbackAIMetrics();
    }
}

function displayAIMetrics(metrics) {
    // AI Accuracy circle
    const accuracyCircle = document.getElementById('aiAccuracyCircle');
    if (accuracyCircle) {
        const accuracy = metrics.accuracy || 0;
        if (accuracy > 0) {
            accuracyCircle.textContent = Math.round(accuracy * 100) + '%';
        } else {
            accuracyCircle.textContent = 'N/A';
        }
    }

    // Total predictions circle
    const predictionsCircle = document.getElementById('totalPredictionsCircle');
    if (predictionsCircle) {
        const count = metrics.count || 0;
        predictionsCircle.textContent = count > 0 ? count : '0';
    }
}

function setFallbackAIMetrics() {
    const accCircle = document.getElementById('aiAccuracyCircle');
    if (accCircle) accCircle.textContent = 'N/A';
    const predCircle = document.getElementById('totalPredictionsCircle');
    if (predCircle) predCircle.textContent = '0';
    const eligCircle = document.getElementById('eligibleDonorsCircle');
    if (eligCircle) eligCircle.textContent = '0';
}

// =============================================================================
// DYNAMIC BAR CHART
// =============================================================================

function displayBloodGroupChart(bloodGroupData) {
    const chartContainer = document.getElementById('bloodGroupChart');
    if (!chartContainer) return;

    // Clear loading state
    chartContainer.innerHTML = '';

    const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'];
    
    // Get the max units for scaling
    let maxUnits = 0;
    bloodGroups.forEach(bg => {
        const data = bloodGroupData[bg];
        const units = data ? (typeof data === 'object' ? data.units : data) : 0;
        if (units > maxUnits) maxUnits = units;
    });

    // If max is 0, set to 1 to avoid division by zero
    if (maxUnits === 0) maxUnits = 1;

    // Create bars
    bloodGroups.forEach(bg => {
        const data = bloodGroupData[bg];
        const units = data ? (typeof data === 'object' ? data.units : data) : 0;
        const heightPct = Math.max(2, (units / maxUnits) * 100);

        const wrapper = document.createElement('div');
        wrapper.className = 'bar-wrapper';

        const valueLabel = document.createElement('div');
        valueLabel.className = 'bar-value';
        valueLabel.textContent = units;

        const bar = document.createElement('div');
        bar.className = 'bar';
        bar.style.height = '0%';
        bar.title = `${bg}: ${units} units`;

        const label = document.createElement('div');
        label.className = 'bar-label';
        label.textContent = bg;

        wrapper.appendChild(valueLabel);
        wrapper.appendChild(bar);
        wrapper.appendChild(label);
        chartContainer.appendChild(wrapper);

        // Animate bar height after a short delay
        requestAnimationFrame(() => {
            setTimeout(() => {
                bar.style.height = heightPct + '%';
            }, 100);
        });
    });
}

// =============================================================================
// EXPORT FUNCTIONALITY
// =============================================================================

window.exportAnalyticsReport = async function () {
    try {
        if (typeof showSuccess === 'function') showSuccess('Generating analytics report...');

        const [donorStats, stockStats, aiMetrics] = await Promise.allSettled([
            API.donors.getStatistics(),
            API.bloodStock.getStatistics(),
            API.ai.getMetrics(),
        ]);

        const report = {
            generated_at: new Date().toISOString(),
            donor_statistics: donorStats.status === 'fulfilled' ? donorStats.value.data : null,
            blood_stock_statistics: stockStats.status === 'fulfilled' ? stockStats.value.data : null,
            ai_metrics: aiMetrics.status === 'fulfilled' ? aiMetrics.value.data : null,
        };

        // Download as JSON
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `bloodify-analytics-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);

        if (typeof showSuccess === 'function') showSuccess('Analytics report downloaded!');
    } catch (error) {
        console.error('Error exporting analytics:', error);
        if (typeof showError === 'function') showError('Failed to export analytics report');
    }
};
