/**
 * AAWAJ Main JS - Shared utilities and navigation
 */

// Navbar scroll effect
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    if (nav) nav.classList.toggle('scrolled', window.scrollY > 20);
});

// Mobile nav toggle
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => links.classList.toggle('open'));
        document.addEventListener('click', (e) => {
            if (!toggle.contains(e.target) && !links.contains(e.target)) links.classList.remove('open');
        });
    }
});

// Utility: Format date
function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

// Utility: Time ago
function timeAgo(dateStr) {
    const now = new Date();
    const d = new Date(dateStr);
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    return formatDate(dateStr);
}

// Utility: Get CSRF token from cookie
function getCookie(name) {
    let v = null;
    document.cookie.split(';').forEach(c => {
        c = c.trim();
        if (c.startsWith(name + '=')) v = decodeURIComponent(c.substring(name.length + 1));
    });
    return v;
}

// Utility: Category badge HTML
function categoryBadge(cat) {
    const labels = {
        roads: 'Roads', garbage: 'Garbage', water: 'Water', electricity: 'Electricity',
        health: 'Health', education: 'Education', corruption: 'Corruption',
        infrastructure: 'Infrastructure', other: 'Other'
    };
    return `<span class="badge badge-${cat}">${labels[cat] || cat}</span>`;
}

// Utility: Priority badge
function priorityBadge(p) {
    return `<span class="badge badge-${p}">${p}</span>`;
}

// Utility: Status badge
function statusBadge(status) {
    const labels = {
        published: 'Published', pending_review: 'In Review', rejected: 'Rejected', resolved: 'Resolved', pending_ai: 'Processing'
    };
    return `<span class="badge badge-${status}">${labels[status] || status}</span>`;
}

// Utility: Complaint card HTML
function complaintCardHTML(c) {
    const img = c.first_image || 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" fill="%2312121a"><rect width="400" height="200"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%2355556a" font-family="sans-serif" font-size="16">No Image</text></svg>');
    return `
    <div class="complaint-card" onclick="showComplaintDetail('${c.complaint_code}')">
        <img src="${img}" alt="Complaint" class="complaint-card-img" loading="lazy" onerror="this.style.display='none'">
        <div class="complaint-card-body">
            <div class="complaint-card-header">
                <span class="complaint-code">${c.complaint_code}</span>
                ${categoryBadge(c.category)}
            </div>
            <p class="complaint-card-desc">${c.description || 'No description'}</p>
            <div class="complaint-card-meta">
                <span>📍 ${c.location_text ? c.location_text.substring(0, 30) : 'N/A'}${c.location_text && c.location_text.length > 30 ? '...' : ''}</span>
                <span>${timeAgo(c.created_at)}</span>
            </div>
            <div style="margin-top:0.8rem;display:flex;gap:0.5rem;align-items:center;">
                ${priorityBadge(c.priority)}
                ${statusBadge(c.status)}
            </div>
        </div>
    </div>`;
}

// Utility: Show toast notification
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.style.cssText = `position:fixed;bottom:2rem;right:2rem;padding:1rem 1.5rem;border-radius:12px;color:#fff;font-weight:600;font-size:0.9rem;z-index:9999;animation:slideUp 0.3s ease;font-family:Inter,sans-serif;max-width:400px;`;
    const colors = { success: '#22c55e', error: '#ef4444', info: '#3b82f6', warning: '#f59e0b' };
    toast.style.background = colors[type] || colors.info;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3500);
}

// Animate numbers
function animateNumber(el, target) {
    let current = 0;
    const step = Math.ceil(target / 40);
    const interval = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(interval); }
        el.textContent = current.toLocaleString();
    }, 30);
}
