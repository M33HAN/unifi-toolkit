/**
 * Threat Intelligence Module for Threat Watch
 * Provides AbuseIPDB lookup UI with slide-out panel
 * Requires: /threat-watch/api/intel/check/{ip} backend endpoint
 */

class ThreatIntel {
    constructor() {
        this.panel = null;
        this.cache = new Map();
        this.isOpen = false;
        this.currentIP = null;
    }

    init() {
        this.createPanel();
        this.hookIPClicks();
        this.checkAPIStatus();
    }

    async checkAPIStatus() {
        try {
            const resp = await fetch('/threat-watch/api/intel/status');
            if (resp.ok) {
                const data = await resp.json();
                this.apiConfigured = data.configured;
            }
        } catch (e) {
            this.apiConfigured = false;
        }
    }

    createPanel() {
        // Create the slide-out panel
        const panel = document.createElement('div');
        panel.id = 'threat-intel-panel';
        panel.className = 'intel-panel';
        panel.innerHTML = `
            <div class="intel-panel-header">
                <div class="intel-panel-title">
                    <span class="intel-icon">🛡️</span>
                    <span>Threat Intelligence</span>
                </div>
                <button class="intel-close-btn" onclick="window.threatIntel.close()">&times;</button>
            </div>
            <div class="intel-panel-body">
                <div class="intel-search-bar">
                    <input type="text" id="intel-ip-input" class="intel-ip-input"
                           placeholder="Enter IP address..."
                           onkeydown="if(event.key==='Enter')window.threatIntel.lookup(this.value)">
                    <button class="intel-search-btn" onclick="window.threatIntel.lookup(document.getElementById('intel-ip-input').value)">
                        Analyze
                    </button>
                </div>
                <div id="intel-results" class="intel-results">
                    <div class="intel-placeholder">
                        <div class="intel-placeholder-icon">🔍</div>
                        <p>Click any IP address in the dashboard or enter one above to check its threat reputation.</p>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
        this.panel = panel;

        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'intel-overlay';
        overlay.className = 'intel-overlay';
        overlay.onclick = () => this.close();
        document.body.appendChild(overlay);
        this.overlay = overlay;

        // Create floating trigger button
        const trigger = document.createElement('button');
        trigger.id = 'intel-trigger-btn';
        trigger.className = 'intel-trigger-btn';
        trigger.innerHTML = '<span class="intel-trigger-icon">🛡️</span><span class="intel-trigger-text">Threat Intel</span>';
        trigger.onclick = () => this.toggle();
        document.body.appendChild(trigger);
        this.triggerBtn = trigger;
    }

    hookIPClicks() {
        // Use event delegation to catch clicks on IP addresses
        document.addEventListener('click', (e) => {
            const target = e.target.closest('[data-ip], .ip-cell, .attacker-ip, .threat-popup-ip, code');
            if (!target) return;

            let ip = null;
            if (target.dataset.ip) {
                ip = target.dataset.ip;
            } else {
                const text = target.textContent.trim();
                // Validate it looks like an IP
                if (/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(text)) {
                    ip = text;
                }
            }

            if (ip && !this.isPrivateIP(ip)) {
                e.preventDefault();
                e.stopPropagation();
                this.lookup(ip);
            }
        });
    }

    isPrivateIP(ip) {
        if (!ip) return true;
        const parts = ip.split('.').map(Number);
        if (parts[0] === 10) return true;
        if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) return true;
        if (parts[0] === 192 && parts[1] === 168) return true;
        if (parts[0] === 127) return true;
        return false;
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.panel.classList.add('intel-panel-open');
        this.overlay.classList.add('intel-overlay-visible');
        this.triggerBtn.classList.add('intel-trigger-active');
        this.isOpen = true;
    }

    close() {
        this.panel.classList.remove('intel-panel-open');
        this.overlay.classList.remove('intel-overlay-visible');
        this.triggerBtn.classList.remove('intel-trigger-active');
        this.isOpen = false;
    }

    async lookup(ip) {
        if (!ip || !ip.trim()) return;
        ip = ip.trim();

        // Validate IP format
        if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip)) {
            this.showError('Invalid IP address format');
            return;
        }

        if (this.isPrivateIP(ip)) {
            this.showError('Private/internal IP addresses cannot be looked up via AbuseIPDB.');
            return;
        }

        // Open panel if not already
        if (!this.isOpen) this.open();

        // Update input
        document.getElementById('intel-ip-input').value = ip;
        this.currentIP = ip;

        // Check cache
        if (this.cache.has(ip)) {
            this.renderResults(this.cache.get(ip));
            return;
        }

        // Show loading
        this.showLoading(ip);

        try {
            const resp = await fetch(`/threat-watch/api/intel/check/${encodeURIComponent(ip)}`);
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${resp.status}`);
            }
            const data = await resp.json();
            this.cache.set(ip, data);
            this.renderResults(data);
        } catch (err) {
            this.showError(err.message || 'Failed to fetch threat intelligence');
        }
    }

    showLoading(ip) {
        const results = document.getElementById('intel-results');
        results.innerHTML = `
            <div class="intel-loading">
                <div class="intel-loading-spinner"></div>
                <p>Analyzing <strong>${this.escapeHtml(ip)}</strong>...</p>
                <p class="intel-loading-sub">Querying AbuseIPDB threat database</p>
            </div>
        `;
    }

    showError(message) {
        if (!this.isOpen) this.open();
        const results = document.getElementById('intel-results');
        results.innerHTML = `
            <div class="intel-error">
                <div class="intel-error-icon">⚠️</div>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    }

    renderResults(data) {
        const results = document.getElementById('intel-results');
        const score = data.abuse_confidence_score || 0;
        const risk = data.risk_classification || 'unknown';

        // Risk color mapping
        const riskColors = {
            critical: { color: '#ef4444', bg: 'rgba(239,68,68,0.15)', label: 'CRITICAL' },
            high: { color: '#f97316', bg: 'rgba(249,115,22,0.15)', label: 'HIGH RISK' },
            medium: { color: '#f59e0b', bg: 'rgba(245,158,11,0.15)', label: 'MEDIUM' },
            low: { color: '#00e1ff', bg: 'rgba(0,225,255,0.15)', label: 'LOW RISK' },
            clean: { color: '#10b981', bg: 'rgba(16,185,129,0.15)', label: 'CLEAN' },
            unknown: { color: '#94a3b8', bg: 'rgba(148,163,184,0.15)', label: 'UNKNOWN' }
        };

        const riskInfo = riskColors[risk] || riskColors.unknown;

        // Build reports HTML
        let reportsHTML = '';
        if (data.recent_reports && data.recent_reports.length > 0) {
            reportsHTML = data.recent_reports.slice(0, 10).map(report => `
                <div class="intel-report-item">
                    <div class="intel-report-date">${this.formatDate(report.reported_at)}</div>
                    <div class="intel-report-comment">${this.escapeHtml(report.comment || 'No comment')}</div>
                    <div class="intel-report-cats">
                        ${(report.categories || []).map(c => `<span class="intel-cat-badge">${this.escapeHtml(c)}</span>`).join('')}
                    </div>
                </div>
            `).join('');
        } else {
            reportsHTML = '<div class="intel-no-reports">No recent reports found</div>';
        }

        results.innerHTML = `
            <div class="intel-result-card">
                <!-- Risk Score Gauge -->
                <div class="intel-score-section">
                    <div class="intel-score-gauge" style="--score-color: ${riskInfo.color}">
                        <svg viewBox="0 0 120 120" class="intel-gauge-svg">
                            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8"/>
                            <circle cx="60" cy="60" r="52" fill="none" stroke="${riskInfo.color}" stroke-width="8"
                                    stroke-dasharray="${(score / 100) * 327} 327"
                                    stroke-linecap="round" transform="rotate(-90 60 60)"
                                    class="intel-gauge-arc"/>
                        </svg>
                        <div class="intel-score-value" style="color: ${riskInfo.color}">${score}</div>
                        <div class="intel-score-label">Abuse Score</div>
                    </div>
                    <div class="intel-risk-badge" style="background: ${riskInfo.bg}; color: ${riskInfo.color}; border: 1px solid ${riskInfo.color}40">
                        ${riskInfo.label}
                    </div>
                </div>

                <!-- IP Info -->
                <div class="intel-info-grid">
                    <div class="intel-info-item">
                        <span class="intel-info-label">IP Address</span>
                        <span class="intel-info-value intel-ip-mono">${this.escapeHtml(data.ip_address || this.currentIP)}</span>
                    </div>
                    <div class="intel-info-item">
                        <span class="intel-info-label">ISP</span>
                        <span class="intel-info-value">${this.escapeHtml(data.isp || 'Unknown')}</span>
                    </div>
                    <div class="intel-info-item">
                        <span class="intel-info-label">Usage Type</span>
                        <span class="intel-info-value">${this.escapeHtml(data.usage_type || 'Unknown')}</span>
                    </div>
                    <div class="intel-info-item">
                        <span class="intel-info-label">Domain</span>
                        <span class="intel-info-value">${this.escapeHtml(data.domain || 'N/A')}</span>
                    </div>
                    <div class="intel-info-item">
                        <span class="intel-info-label">Country</span>
                        <span class="intel-info-value">${this.escapeHtml(data.country_name || data.country_code || 'Unknown')}</span>
                    </div>
                    <div class="intel-info-item">
                        <span class="intel-info-label">Total Reports</span>
                        <span class="intel-info-value">${data.total_reports || 0}</span>
                    </div>
                </div>

                <!-- Badges -->
                <div class="intel-badges">
                    ${data.is_tor ? '<span class="intel-badge intel-badge-tor">🧅 TOR Exit Node</span>' : ''}
                    ${data.is_whitelisted ? '<span class="intel-badge intel-badge-safe">✅ Whitelisted</span>' : ''}
                    ${(data.total_reports || 0) > 50 ? '<span class="intel-badge intel-badge-warn">⚡ Frequently Reported</span>' : ''}
                    ${score >= 80 ? '<span class="intel-badge intel-badge-danger">🚨 Known Abuser</span>' : ''}
                </div>

                <!-- External Links -->
                <div class="intel-external-links">
                    <a href="https://www.abuseipdb.com/check/${encodeURIComponent(data.ip_address || this.currentIP)}" target="_blank" class="intel-ext-link">
                        🔍 AbuseIPDB
                    </a>
                    <a href="https://www.virustotal.com/gui/ip-address/${encodeURIComponent(data.ip_address || this.currentIP)}" target="_blank" class="intel-ext-link">
                        🦠 VirusTotal
                    </a>
                    <a href="https://www.shodan.io/host/${encodeURIComponent(data.ip_address || this.currentIP)}" target="_blank" class="intel-ext-link">
                        🔎 Shodan
                    </a>
                </div>

                <!-- Recent Reports -->
                <div class="intel-reports-section">
                    <h4 class="intel-reports-title">Recent Reports</h4>
                    <div class="intel-reports-list">
                        ${reportsHTML}
                    </div>
                </div>
            </div>
        `;
    }

    formatDate(dateStr) {
        if (!dateStr) return 'Unknown';
        const d = new Date(dateStr);
        return d.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

// ============================================================
// INITIALIZATION
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
    window.threatIntel = new ThreatIntel();
    window.threatIntel.init();
});
