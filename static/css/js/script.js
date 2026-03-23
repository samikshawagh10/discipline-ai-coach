// ==================== FLASH MESSAGES AUTO-CLOSE ====================
document.addEventListener('DOMContentLoaded', function() {
    // Close alerts when clicking the X button
    const closeButtons = document.querySelectorAll('.close-alert');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => {
                this.parentElement.remove();
            }, 300);
        });
    });

    // Auto-close flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        }, 5000);
    });
});

// ==================== CONFIRMATION DIALOGS ====================
// Habit deletion confirmation is already handled in HTML with onsubmit="return confirm(...)"

// ==================== ANIMATIONS ====================
// Add slide-out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== FORM VALIDATION ====================
// Add visual feedback for form fields
document.addEventListener('DOMContentLoaded', function() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input[required], textarea[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                if (this.value.trim() === '') {
                    this.style.borderColor = '#ef4444';
                } else {
                    this.style.borderColor = '#10b981';
                }
            });

            input.addEventListener('focus', function() {
                this.style.borderColor = '#6366f1';
            });
        });
    });
});

// ==================== HABIT TRACKING ANIMATION ====================
document.addEventListener('DOMContentLoaded', function() {
    const trackForms = document.querySelectorAll('.track-form');
    
    trackForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const button = this.querySelector('button[type="submit"]');
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
            button.disabled = true;
        });
    });
});

// ==================== SMOOTH SCROLL ====================
document.addEventListener('DOMContentLoaded', function() {
    const links = document.querySelectorAll('a[href^="#"]');
    
    links.forEach(link => {
        link.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });
});

// ==================== STATS ANIMATION ====================
document.addEventListener('DOMContentLoaded', function() {
    const statValues = document.querySelectorAll('.stat-value');
    
    const animateValue = (element, start, end, duration) => {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = value;
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    };

    statValues.forEach(stat => {
        const value = parseInt(stat.textContent);
        if (!isNaN(value) && value > 0) {
            stat.textContent = '0';
            setTimeout(() => {
                animateValue(stat, 0, value, 1000);
            }, 300);
        }
    });
});

// ==================== COMPLETION BAR ANIMATION ====================
document.addEventListener('DOMContentLoaded', function() {
    const completionBars = document.querySelectorAll('.completion-fill');
    
    completionBars.forEach(bar => {
        const width = bar.style.width;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = width;
        }, 100);
    });
});

// ==================== RESPONSIVE NAVIGATION ====================
// Simple mobile menu toggle (if needed in future)
console.log('Discipline AI - Smart Habit Coach loaded successfully!');