// Error Pages JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Add some interactive effects
    const errorCard = document.querySelector('.error-card');
    const buttons = document.querySelectorAll('.error-actions .btn');
    
    // Add hover effects to buttons
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Add click animation to buttons
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Create ripple effect
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple-effect');
            
            this.appendChild(ripple);
            
            // Remove ripple after animation
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // ESC key - go back
        if (e.key === 'Escape') {
            history.back();
        }
        
        // Enter key on search
        if (e.key === 'Enter' && e.target.type === 'search') {
            e.target.closest('form').submit();
        }
    });
    
    // Auto-focus search input if exists
    const searchInput = document.querySelector('.error-search input[type="search"]');
    if (searchInput) {
        // Focus search input after a short delay
        setTimeout(() => {
            searchInput.focus();
        }, 500);
    }
    
    // Add floating animation to error icon
    const errorIcon = document.querySelector('.error-icon-wrapper i');
    if (errorIcon) {
        setInterval(() => {
            errorIcon.style.transform = 'translateY(-5px)';
            setTimeout(() => {
                errorIcon.style.transform = 'translateY(0)';
            }, 1000);
        }, 3000);
    }
    
    // Check if user came from internal link
    const referrer = document.referrer;
    const currentDomain = window.location.hostname;
    
    if (referrer && referrer.includes(currentDomain)) {
        // Add "previous page" context
        const errorMessage = document.querySelector('.error-message');
        if (errorMessage && !errorMessage.textContent.includes('previous page')) {
            errorMessage.innerHTML += ' <br><small class="text-muted">You came from: <em>' + 
                                     referrer.split('/').pop() + '</em></small>';
        }
    }
    
    // Console message for developers
    console.log('🚫 Error Page Loaded - If you\'re a developer, check the network tab for more details.');
    
    // Performance timing (optional)
    if ('performance' in window) {
        window.addEventListener('load', function() {
            const loadTime = performance.now();
            console.log(`⚡ Error page loaded in ${Math.round(loadTime)}ms`);
        });
    }
});

// Add CSS for ripple effect
const style = document.createElement('style');
style.textContent = `
    .btn {
        position: relative;
        overflow: hidden;
    }
    
    .ripple-effect {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.4);
        transform: scale(0);
        animation: ripple 0.6s linear;
        pointer-events: none;
    }
    
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .error-icon-wrapper i {
        transition: transform 0.5s ease-in-out;
    }
`;
document.head.appendChild(style);
