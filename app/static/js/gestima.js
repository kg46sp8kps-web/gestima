/**
 * GESTIMA - Main JavaScript
 */

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    
    // Barvy podle typu (50% opacity pro pozadí)
    const bgColor = type === 'success' ? 'rgba(34, 197, 94, 0.5)' : 
                    type === 'error' ? 'rgba(214, 40, 40, 0.5)' : 
                    'rgba(59, 130, 246, 0.5)';
    const borderColor = type === 'success' ? '#22c55e' : 
                        type === 'error' ? '#d62828' : 
                        '#3b82f6';
    
    toast.style.cssText = `
        background: ${bgColor};
        backdrop-filter: blur(8px);
        border: 2px solid ${borderColor};
        border-radius: 6px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        gap: 0.75rem;
        color: white;
        font-size: 0.85rem;
        font-weight: 500;
        transition: opacity 0.3s;
        min-width: 250px;
        max-width: 400px;
    `;
    
    toast.innerHTML = `
        <span style="flex: 1;">${message}</span>
        <button onclick="this.parentElement.remove()" 
                style="background: none; border: none; color: white; opacity: 0.8; cursor: pointer; font-size: 1.3rem; padding: 0; line-height: 1; font-weight: 300;">
            ×
        </button>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

window.showToast = showToast;

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

window.debounce = debounce;

console.log('🚀 GESTIMA JS loaded');
