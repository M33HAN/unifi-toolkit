/**
 * Enhanced Features Module for Threat Watch
 * Adds: GeoIP Threat Map, Richer Charts, Live Log Stream
 * Dependencies: Leaflet.js (for maps), Chart.js (existing)
 */

// ============================================================
// 1. GeoIP THREAT MAP (using Leaflet.js + OpenStreetMap)
// ============================================================
class ThreatMap {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
        this.markers = [];
        this.markerCluster = null;
    }

    async init() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        // Initialize Leaflet map with dark theme
        this.map = L.map(this.containerId, {
            center: [20, 0],
            zoom: 2,
            minZoom: 2,
            maxZoom: 12,
            zoomControl: true,
            attributionControl: false
        });

        // Dark-themed tile layer
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19
        }).addTo(this.map);

        // Custom attribution
        L.control.attribution({
            prefix: false,
            position: 'bottomright'
        }).addAttribution('&copy; <a href="https://carto.com/">CARTO</a>').addTo(this.map);

        // Load threat data
        await this.loadThreats();
    }

    async loadThreats() {
        try {
            const response = await fetch('/threat-watch/api/events?page_size=200');
            if (!response.ok) return;
            const data = await response.json();

            this.clearMarkers();

            const locationCounts = {};

            data.events.forEach(event => {
                if (event.src_country) {
                    const key = event.src_ip || event.src_country;
                    if (!locationCounts[key]) {
                        locationCounts[key] = {
                            ip: event.src_ip,
                            country: event.src_country,
                            city: event.src_city,
                            org: event.src_org,
                            count: 0,
                            severities: []
                        };
                    }
                    locationCounts[key].count++;
                    if (event.severity) locationCounts[key].severities.push(event.severity);
                }
            });

            // We need lat/lng — use ip-api.com for batch geolocation
            const ips = Object.keys(locationCounts).filter(k => locationCounts[k].ip).slice(0, 50);
            if (ips.length > 0) {
                await this.geolocateIPs(ips, locationCounts);
            }
        } catch (err) {
            console.error('ThreatMap: Failed to load threats', err);
        }
    }

    async geolocateIPs(ips, locationCounts) {
        try {
            // Use ip-api.com batch endpoint (free, no key required, 15 req/min)
            const batchSize = 15;
            for (let i = 0; i < ips.length; i += batchSize) {
                const batch = ips.slice(i, i + batchSize);
                const response = await fetch('http://ip-api.com/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(batch.map(ip => ({ query: ip, fields: 'query,lat,lon,country,city,isp,org' })))
                });

                if (response.ok) {
                    const results = await response.json();
                    results.forEach(result => {
                        if (result.lat && result.lon) {
                            const info = locationCounts[result.query];
                            if (info) {
                                this.addThreatMarker(
                                    result.lat, result.lon,
                                    info.ip, info.country, info.city || result.city,
                                    info.org || result.org, info.count,
                                    info.severities
                                );
                            }
                        }
                    });
                }

                // Rate limit: wait 1 second between batches
                if (i + batchSize < ips.length) {
                    await new Promise(r => setTimeout(r, 1100));
                }
            }
        } catch (err) {
            console.error('ThreatMap: GeoIP lookup failed', err);
        }
    }

    addThreatMarker(lat, lng, ip, country, city, org, count, severities) {
        const maxSev = Math.min(...severities);
        let color, pulseClass;
        if (maxSev === 1) { color = '#ff3333'; pulseClass = 'threat-high'; }
        else if (maxSev === 2) { color = '#ffaa00'; pulseClass = 'threat-medium'; }
        else { color = '#00ccff'; pulseClass = 'threat-low'; }

        const radius = Math.min(8 + Math.log2(count) * 4, 25);

        const marker = L.circleMarker([lat, lng], {
            radius: radius,
            fillColor: color,
            color: color,
            weight: 1,
            opacity: 0.8,
            fillOpacity: 0.5,
            className: pulseClass
        });

        const locationStr = [city, country].filter(Boolean).join(', ');
        marker.bindPopup(
            '<div class="threat-popup">' +
            '<div class="threat-popup-ip">' + (ip || 'Unknown') + '</div>' +
            '<div class="threat-popup-location">' + locationStr + '</div>' +
            (org ? '<div class="threat-popup-org">' + org + '</div>' : '') +
            '<div class="threat-popup-count">' + count + ' event' + (count !== 1 ? 's' : '') + '</div>' +
            '<div class="threat-popup-severity ' + pulseClass + '">' +
                (maxSev === 1 ? 'HIGH' : maxSev === 2 ? 'MEDIUM' : 'LOW') + ' severity</div>' +
            '</div>',
            { className: 'dark-popup' }
        );

        marker.addTo(this.map);
        this.markers.push(marker);
    }

    clearMarkers() {
        this.markers.forEach(m => m.remove());
        this.markers = [];
    }

    refresh() {
        this.loadThreats();
    }
}

// ============================================================
// 2. ENHANCED CHARTS (using Chart.js with futuristic styling)
// ============================================================
class EnhancedCharts {
    constructor() {
        this.charts = {};
        this.neonCyan = '#00e1ff';
        this.neonPurple = '#8b5cf6';
        this.neonPink = '#ec4899';
        this.neonGreen = '#10b981';
        this.neonOrange = '#f59e0b';
        this.neonRed = '#ef4444';
    }

    getGradient(ctx, color1, color2) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, color1 + '80');
        gradient.addColorStop(1, color1 + '05');
        return gradient;
    }

    async initTimelineChart(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            const response = await fetch('/threat-watch/api/events/timeline?interval=hour&days=7');
            if (!response.ok) return;
            const data = await response.json();

            const ctx = canvas.getContext('2d');
            const gradient = this.getGradient(ctx, this.neonCyan, 'transparent');

            this.charts.timeline = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.data.map(p => {
                        const d = new Date(p.timestamp);
                        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit' });
                    }),
                    datasets: [{
                        label: 'Threat Events',
                        data: data.data.map(p => p.count),
                        borderColor: this.neonCyan,
                        backgroundColor: gradient,
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        pointHoverRadius: 6,
                        pointHoverBackgroundColor: this.neonCyan,
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { intersect: false, mode: 'index' },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(10, 10, 30, 0.9)',
                            borderColor: this.neonCyan,
                            borderWidth: 1,
                            titleColor: this.neonCyan,
                            bodyColor: '#e2e8f0',
                            padding: 12,
                            cornerRadius: 8
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#94a3b8', maxTicksLimit: 12, font: { size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#94a3b8', font: { size: 10 } },
                            beginAtZero: true
                        }
                    }
                }
            });
        } catch (err) {
            console.error('EnhancedCharts: Timeline failed', err);
        }
    }

    async initSeverityDonut(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            const response = await fetch('/threat-watch/api/events/stats');
            if (!response.ok) return;
            const data = await response.json();

            const ctx = canvas.getContext('2d');
            const sevColors = [this.neonRed, this.neonOrange, this.neonCyan];
            const sevLabels = data.by_severity.map(s => s.label);
            const sevCounts = data.by_severity.map(s => s.count);

            this.charts.severity = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: sevLabels,
                    datasets: [{
                        data: sevCounts,
                        backgroundColor: sevColors.slice(0, sevLabels.length),
                        borderColor: 'rgba(10, 10, 30, 0.8)',
                        borderWidth: 3,
                        hoverOffset: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { color: '#e2e8f0', padding: 16, usePointStyle: true, pointStyleWidth: 12 }
                        },
                        tooltip: {
                            backgroundColor: 'rgba(10, 10, 30, 0.9)',
                            borderColor: this.neonPurple,
                            borderWidth: 1,
                            titleColor: this.neonPurple,
                            bodyColor: '#e2e8f0',
                            padding: 12,
                            cornerRadius: 8
                        }
                    }
                }
            });
        } catch (err) {
            console.error('EnhancedCharts: Severity donut failed', err);
        }
    }

    async initCategoryBar(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            const response = await fetch('/threat-watch/api/events/stats');
            if (!response.ok) return;
            const data = await response.json();

            const ctx = canvas.getContext('2d');
            const categories = data.by_category.slice(0, 8);

            const barColors = categories.map((_, i) => {
                const colors = [this.neonCyan, this.neonPurple, this.neonPink, this.neonGreen,
                               this.neonOrange, this.neonRed, '#6366f1', '#14b8a6'];
                return colors[i % colors.length];
            });

            this.charts.category = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: categories.map(c => c.category.length > 20 ? c.category.substring(0, 20) + '...' : c.category),
                    datasets: [{
                        label: 'Events',
                        data: categories.map(c => c.count),
                        backgroundColor: barColors.map(c => c + '60'),
                        borderColor: barColors,
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: 'rgba(10, 10, 30, 0.9)',
                            borderColor: this.neonPurple,
                            borderWidth: 1,
                            padding: 12,
                            cornerRadius: 8,
                            titleColor: this.neonCyan,
                            bodyColor: '#e2e8f0'
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255,255,255,0.05)' },
                            ticks: { color: '#94a3b8', font: { size: 10 } },
                            beginAtZero: true
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: '#e2e8f0', font: { size: 11 } }
                        }
                    }
                }
            });
        } catch (err) {
            console.error('EnhancedCharts: Category bar failed', err);
        }
    }
}

// ============================================================
// 3. LIVE LOG STREAM
// ============================================================
class LiveLogStream {
    constructor(containerId, maxEntries = 100) {
        this.containerId = containerId;
        this.maxEntries = maxEntries;
        this.container = null;
        this.entries = [];
        this.autoScroll = true;
        this.pollInterval = null;
        this.lastEventId = null;
        this.paused = false;
    }

    init() {
        this.container = document.getElementById(this.containerId);
        if (!this.container) return;

        // Add control bar
        const controls = document.createElement('div');
        controls.className = 'log-stream-controls';
        controls.innerHTML =
            '<div class="log-stream-status">' +
                '<span class="log-pulse"></span>' +
                '<span class="log-status-text">Live</span>' +
            '</div>' +
            '<div class="log-stream-actions">' +
                '<button class="log-btn log-btn-pause" onclick="window.logStream.togglePause()">' +
                    '<span class="log-btn-icon">⏸</span> Pause' +
                '</button>' +
                '<button class="log-btn log-btn-clear" onclick="window.logStream.clear()">' +
                    '<span class="log-btn-icon">🗑</span> Clear' +
                '</button>' +
                '<button class="log-btn log-btn-export" onclick="window.logStream.exportCSV()">' +
                    '<span class="log-btn-icon">📥</span> Export CSV' +
                '</button>' +
            '</div>';

        this.container.parentElement.insertBefore(controls, this.container);

        // Start polling
        this.startPolling();
    }

    startPolling() {
        this.poll();
        this.pollInterval = setInterval(() => {
            if (!this.paused) this.poll();
        }, 5000);
    }

    async poll() {
        try {
            let url = '/threat-watch/api/events?page_size=20';
            const response = await fetch(url);
            if (!response.ok) return;
            const data = await response.json();

            data.events.reverse().forEach(event => {
                if (this.lastEventId && event.id <= this.lastEventId) return;
                this.addEntry(event);
            });

            if (data.events.length > 0) {
                this.lastEventId = Math.max(...data.events.map(e => e.id));
            }
        } catch (err) {
            console.error('LiveLogStream: Poll failed', err);
        }
    }

    addEntry(event) {
        const entry = document.createElement('div');
        entry.className = 'log-entry log-entry-animate';
        entry.dataset.eventId = event.id;

        const sevClass = event.severity === 1 ? 'sev-high' :
                         event.severity === 2 ? 'sev-medium' : 'sev-low';
        const sevLabel = event.severity === 1 ? 'HIGH' :
                         event.severity === 2 ? 'MED' : 'LOW';
        const actionClass = event.action === 'block' ? 'action-block' : 'action-alert';
        const time = new Date(event.timestamp).toLocaleTimeString('en-US', {
            hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
        });

        entry.innerHTML =
            '<div class="log-entry-time">' + time + '</div>' +
            '<span class="log-entry-sev ' + sevClass + '">' + sevLabel + '</span>' +
            '<span class="log-entry-action ' + actionClass + '">' + (event.action || 'alert').toUpperCase() + '</span>' +
            '<div class="log-entry-detail">' +
                '<span class="log-entry-sig">' + (event.signature || event.message || 'Unknown') + '</span>' +
                '<span class="log-entry-network">' +
                    (event.src_ip || '?') + ':' + (event.src_port || '?') +
                    ' → ' +
                    (event.dest_ip || '?') + ':' + (event.dest_port || '?') +
                '</span>' +
            '</div>' +
            (event.src_country ?
                '<div class="log-entry-country">' + event.src_country + '</div>' : '');

        // Add click handler for expandable detail
        entry.addEventListener('click', () => this.toggleDetail(entry, event));

        this.container.appendChild(entry);
        this.entries.push(event);

        // Remove old entries
        while (this.container.children.length > this.maxEntries) {
            this.container.removeChild(this.container.firstChild);
            this.entries.shift();
        }

        // Auto-scroll
        if (this.autoScroll) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    toggleDetail(entryEl, event) {
        const existing = entryEl.querySelector('.log-entry-expanded');
        if (existing) {
            existing.remove();
            return;
        }

        const detail = document.createElement('div');
        detail.className = 'log-entry-expanded';
        detail.innerHTML =
            '<div class="log-detail-grid">' +
                '<div><strong>Event ID:</strong> ' + event.id + '</div>' +
                '<div><strong>Category:</strong> ' + (event.category || 'N/A') + '</div>' +
                '<div><strong>Protocol:</strong> ' + (event.protocol || 'N/A') + '</div>' +
                '<div><strong>Source:</strong> ' + (event.src_ip || '?') +
                    (event.src_country ? ' (' + event.src_country + ')' : '') + '</div>' +
                '<div><strong>Destination:</strong> ' + (event.dest_ip || '?') + '</div>' +
                '<div><strong>Org:</strong> ' + (event.src_org || 'N/A') + '</div>' +
            '</div>';

        entryEl.appendChild(detail);
    }

    togglePause() {
        this.paused = !this.paused;
        const btn = document.querySelector('.log-btn-pause');
        const status = document.querySelector('.log-status-text');
        const pulse = document.querySelector('.log-pulse');
        if (this.paused) {
            btn.innerHTML = '<span class="log-btn-icon">▶</span> Resume';
            status.textContent = 'Paused';
            pulse.classList.add('paused');
        } else {
            btn.innerHTML = '<span class="log-btn-icon">⏸</span> Pause';
            status.textContent = 'Live';
            pulse.classList.remove('paused');
        }
    }

    clear() {
        this.container.innerHTML = '';
        this.entries = [];
    }

    exportCSV() {
        const headers = ['timestamp', 'severity', 'action', 'signature', 'src_ip', 'src_port',
                         'dest_ip', 'dest_port', 'protocol', 'category', 'src_country'];
        const rows = this.entries.map(e =>
            headers.map(h => JSON.stringify(e[h] || '')).join(',')
        );
        const csv = headers.join(',') + '\n' + rows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'threat-events-' + new Date().toISOString().split('T')[0] + '.csv';
        a.click();
        URL.revokeObjectURL(url);
    }

    destroy() {
        if (this.pollInterval) clearInterval(this.pollInterval);
    }
}

// ============================================================
// 4. INITIALIZATION
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
    // Only initialize on pages that have the corresponding containers
    
    // Threat Map
    if (document.getElementById('threat-map')) {
        window.threatMap = new ThreatMap('threat-map');
        window.threatMap.init();
    }

    // Enhanced Charts
    if (document.getElementById('timeline-chart-enhanced') ||
        document.getElementById('severity-donut') ||
        document.getElementById('category-bar')) {
        window.enhancedCharts = new EnhancedCharts();
        if (document.getElementById('timeline-chart-enhanced')) {
            window.enhancedCharts.initTimelineChart('timeline-chart-enhanced');
        }
        if (document.getElementById('severity-donut')) {
            window.enhancedCharts.initSeverityDonut('severity-donut');
        }
        if (document.getElementById('category-bar')) {
            window.enhancedCharts.initCategoryBar('category-bar');
        }
    }

    // Live Log Stream
    if (document.getElementById('live-log-stream')) {
        window.logStream = new LiveLogStream('live-log-stream');
        window.logStream.init();
    }
});
