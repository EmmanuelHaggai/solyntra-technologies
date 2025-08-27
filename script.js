// Bitcoin Lightning USSD Landing Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize page
    initializePage();
    
    // Add smooth scrolling for navigation links
    addSmoothScrolling();
    
    // Add mobile menu functionality
    addMobileMenu();
    
    // Add scroll effects
    addScrollEffects();
    
    // Add phone mockup animation
    animatePhoneMockup();
});

function initializePage() {
    // Add loading animation
    document.body.style.opacity = '0';
    setTimeout(() => {
        document.body.style.transition = 'opacity 0.5s ease';
        document.body.style.opacity = '1';
    }, 100);
}

function copyUSSDCode() {
    const ussdCode = '*384*3036#';
    
    // Try to copy to clipboard
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(ussdCode).then(() => {
            showCopyNotification('USSD code copied to clipboard!');
        }).catch(() => {
            fallbackCopyTextToClipboard(ussdCode);
        });
    } else {
        fallbackCopyTextToClipboard(ussdCode);
    }
}

function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showCopyNotification('USSD code copied to clipboard!');
        } else {
            showCopyNotification('Failed to copy. Please copy manually: ' + text, 'error');
        }
    } catch (err) {
        showCopyNotification('Please copy manually: ' + text, 'error');
    }
    
    document.body.removeChild(textArea);
}

function showCopyNotification(message, type = 'success') {
    // Remove existing notification
    const existing = document.querySelector('.copy-notification');
    if (existing) {
        existing.remove();
    }
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = 'copy-notification';
    notification.textContent = message;
    
    if (type === 'error') {
        notification.style.background = '#e53e3e';
    }
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Hide notification after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

function addSmoothScrolling() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const headerHeight = document.querySelector('.header').offsetHeight;
                const targetPosition = target.offsetTop - headerHeight - 20;
                
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });
}

function addMobileMenu() {
    // Create mobile menu button
    const nav = document.querySelector('.nav');
    const mobileMenuBtn = document.createElement('button');
    mobileMenuBtn.className = 'mobile-menu-btn';
    mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    mobileMenuBtn.style.cssText = `
        display: none;
        background: none;
        border: none;
        font-size: 1.5rem;
        color: #4a4a4a;
        cursor: pointer;
        @media (max-width: 768px) {
            display: block;
        }
    `;
    
    const navLinks = document.querySelector('.nav-links');
    nav.appendChild(mobileMenuBtn);
    
    // Toggle mobile menu
    mobileMenuBtn.addEventListener('click', () => {
        navLinks.classList.toggle('mobile-active');
    });
    
    // Add mobile styles
    const mobileStyles = document.createElement('style');
    mobileStyles.textContent = `
        @media (max-width: 768px) {
            .mobile-menu-btn {
                display: block !important;
            }
            
            .nav-links {
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: white;
                flex-direction: column;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transform: translateY(-100%);
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                padding: 1rem;
            }
            
            .nav-links.mobile-active {
                transform: translateY(0);
                opacity: 1;
                visibility: visible;
            }
        }
    `;
    document.head.appendChild(mobileStyles);
}

function addScrollEffects() {
    const header = document.querySelector('.header');
    let lastScrollY = window.scrollY;
    
    window.addEventListener('scroll', () => {
        const currentScrollY = window.scrollY;
        
        // Header show/hide on scroll
        if (currentScrollY > lastScrollY && currentScrollY > 100) {
            header.style.transform = 'translateY(-100%)';
        } else {
            header.style.transform = 'translateY(0)';
        }
        
        lastScrollY = currentScrollY;
        
        // Add scroll effect to header
        if (currentScrollY > 50) {
            header.style.background = 'rgba(255, 255, 255, 0.98)';
            header.style.boxShadow = '0 2px 20px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.background = 'rgba(255, 255, 255, 0.95)';
            header.style.boxShadow = 'none';
        }
    });
    
    header.style.transition = 'all 0.3s ease';
}

function animatePhoneMockup() {
    const phoneMockup = document.querySelector('.phone-mockup');
    if (!phoneMockup) return;
    
    // Add floating animation
    phoneMockup.style.animation = 'float 6s ease-in-out infinite';
    
    // Add animation keyframes
    const floatAnimation = document.createElement('style');
    floatAnimation.textContent = `
        @keyframes float {
            0%, 100% {
                transform: translateY(0px);
            }
            50% {
                transform: translateY(-20px);
            }
        }
    `;
    document.head.appendChild(floatAnimation);
    
    // Animate USSD content
    animateUSSDContent();
}

function animateUSSDContent() {
    const menuItems = document.querySelectorAll('.menu-item');
    if (menuItems.length === 0) return;
    
    let currentIndex = 3; // Start with "Buy BTC (M-Pesa)" highlighted
    
    setInterval(() => {
        // Remove highlight from all items
        menuItems.forEach(item => item.classList.remove('highlight'));
        
        // Highlight current item
        if (menuItems[currentIndex]) {
            menuItems[currentIndex].classList.add('highlight');
        }
        
        // Move to next item
        currentIndex = (currentIndex + 1) % menuItems.length;
        
        // Skip exit option
        if (currentIndex === menuItems.length - 1) {
            currentIndex = 0;
        }
    }, 2000);
}

function showVideoModal() {
    // Create modal for video
    const modal = document.createElement('div');
    modal.className = 'video-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 3000;
        opacity: 0;
        transition: opacity 0.3s ease;
    `;
    
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        border-radius: 16px;
        padding: 2rem;
        max-width: 600px;
        width: 90%;
        text-align: center;
        transform: scale(0.9);
        transition: transform 0.3s ease;
    `;
    
    modalContent.innerHTML = `
        <h3 style="margin-bottom: 1rem; color: #2d3748;">Demo Video Coming Soon!</h3>
        <p style="margin-bottom: 2rem; color: #4a5568;">
            We're preparing an exciting demo video that will show you exactly how to use 
            Bitcoin Lightning USSD for buying, sending, and managing Bitcoin with simple 
            phone codes. Stay tuned!
        </p>
        <p style="margin-bottom: 2rem; color: #4a5568;">
            In the meantime, try our live USSD system by dialing <strong>*384*3036#</strong> 
            or test it on the Africa's Talking simulator.
        </p>
        <button onclick="closeVideoModal()" style="
            background: #f7931a;
            color: white;
            border: none;
            padding: 0.75rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s ease;
        ">Got it!</button>
    `;
    
    modal.appendChild(modalContent);
    document.body.appendChild(modal);
    
    // Show modal
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.style.transform = 'scale(1)';
    }, 10);
    
    // Close on backdrop click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeVideoModal();
        }
    });
    
    // Store reference for closing
    window.currentVideoModal = modal;
}

function closeVideoModal() {
    const modal = window.currentVideoModal;
    if (modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
    }
}

// Add intersection observer for animations
function addIntersectionObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });
    
    // Observe feature cards and steps
    document.querySelectorAll('.feature-card, .step, .demo-card').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// Initialize intersection observer when page loads
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(addIntersectionObserver, 500);
});

// Add click tracking for analytics (placeholder)
function trackClick(element, action) {
    console.log(`Clicked: ${element} - ${action}`);
    // Add your analytics tracking code here
    // Example: gtag('event', 'click', { 'event_category': element, 'event_label': action });
}

// Add event listeners for tracking
document.addEventListener('DOMContentLoaded', () => {
    // Track USSD code copy
    document.querySelector('.copy-btn')?.addEventListener('click', () => {
        trackClick('ussd-code', 'copy');
    });
    
    // Track simulator link clicks
    document.querySelectorAll('a[href*="simulator"]').forEach(link => {
        link.addEventListener('click', () => {
            trackClick('simulator-link', 'click');
        });
    });
    
    // Track video modal
    document.querySelector('button[onclick="showVideoModal()"]')?.addEventListener('click', () => {
        trackClick('video-modal', 'open');
    });
});

// Add keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Escape to close modal
    if (e.key === 'Escape' && window.currentVideoModal) {
        closeVideoModal();
    }
    
    // Ctrl/Cmd + K to copy USSD code
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        copyUSSDCode();
    }
});

// Performance optimization: Lazy load images
function lazyLoadImages() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// Initialize lazy loading
document.addEventListener('DOMContentLoaded', lazyLoadImages);

// Add service worker for offline functionality (if needed)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Uncomment to enable service worker
        // navigator.serviceWorker.register('/sw.js')
        //     .then(registration => console.log('SW registered'))
        //     .catch(error => console.log('SW registration failed'));
    });
}