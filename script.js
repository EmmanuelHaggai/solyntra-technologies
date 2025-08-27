// Theme Management
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('theme') || 
                    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        this.init();
    }

    init() {
        this.applyTheme();
        this.setupToggle();
        this.setupMediaQuery();
    }

    applyTheme() {
        document.documentElement.setAttribute('data-theme', this.theme);
        localStorage.setItem('theme', this.theme);
    }

    toggle() {
        this.theme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme();
    }

    setupToggle() {
        const toggle = document.getElementById('theme-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => this.toggle());
        }
    }

    setupMediaQuery() {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        mediaQuery.addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                this.theme = e.matches ? 'dark' : 'light';
                this.applyTheme();
            }
        });
    }
}

// Header Scroll Effect
class HeaderManager {
    constructor() {
        this.header = document.getElementById('header');
        this.init();
    }

    init() {
        if (this.header) {
            window.addEventListener('scroll', () => this.handleScroll());
        }
    }

    handleScroll() {
        const scrolled = window.scrollY > 10;
        this.header.classList.toggle('scrolled', scrolled);
    }
}

// Mobile Menu
class MobileMenuManager {
    constructor() {
        this.toggle = document.getElementById('mobile-menu-toggle');
        this.menu = document.getElementById('mobile-menu');
        this.init();
    }

    init() {
        if (this.toggle && this.menu) {
            this.toggle.addEventListener('click', () => this.toggleMenu());
            this.setupMenuLinks();
        }
    }

    toggleMenu() {
        this.toggle.classList.toggle('active');
        this.menu.classList.toggle('active');
    }

    setupMenuLinks() {
        const links = this.menu.querySelectorAll('a');
        links.forEach(link => {
            link.addEventListener('click', () => {
                this.toggle.classList.remove('active');
                this.menu.classList.remove('active');
            });
        });
    }
}

// Phone Animation Manager
class PhoneAnimationManager {
    constructor() {
        this.currentScreen = 0;
        this.screens = document.querySelectorAll('.screen');
        this.balance = document.getElementById('balance');
        this.newBalance = document.getElementById('new-balance');
        this.menuItems = document.getElementById('menu-items');
        this.buyBtcOption = document.getElementById('buy-btc-option');
        this.animatedBalance = 1337;
        this.init();
    }

    init() {
        if (this.screens.length > 0) {
            this.startAnimation();
            this.animateBalance();
        }
    }

    animateBalance() {
        let current = 0;
        const target = this.animatedBalance;
        const increment = target / 50;
        
        const animate = () => {
            current += increment;
            if (current < target) {
                if (this.balance) this.balance.textContent = Math.floor(current).toLocaleString();
                requestAnimationFrame(animate);
            } else {
                if (this.balance) this.balance.textContent = target.toLocaleString();
            }
        };
        
        animate();
    }

    showScreen(index) {
        this.screens.forEach((screen, i) => {
            screen.classList.toggle('active', i === index);
        });
        this.currentScreen = index;
    }

    async startAnimation() {
        // Wait 3 seconds, then start the sequence
        await this.wait(3000);
        
        // Simulate scrolling
        if (this.menuItems) {
            this.menuItems.style.transform = 'translateY(-10px)';
            await this.wait(500);
            this.menuItems.style.transform = 'translateY(0)';
        }
        
        // Highlight Buy BTC option
        if (this.buyBtcOption) {
            this.buyBtcOption.style.transform = 'scale(1.05)';
            this.buyBtcOption.style.boxShadow = '0 0 20px rgba(255, 125, 0, 0.5)';
        }
        
        await this.wait(1500);
        
        // Go to Buy BTC screen
        this.showScreen(1);
        await this.wait(3000);
        
        // Go to Processing screen
        this.showScreen(2);
        await this.wait(3000);
        
        // Go to Success screen and trigger confetti
        this.showScreen(3);
        this.triggerConfetti();
        
        // Update balance
        if (this.newBalance) {
            this.newBalance.textContent = (this.animatedBalance + 667).toLocaleString();
        }
        
        await this.wait(4000);
        
        // Reset to main screen
        this.showScreen(0);
        if (this.buyBtcOption) {
            this.buyBtcOption.style.transform = '';
            this.buyBtcOption.style.boxShadow = '';
        }
        
        // Restart the animation
        setTimeout(() => this.startAnimation(), 5000);
    }

    triggerConfetti() {
        if (typeof confetti !== 'undefined') {
            // Get phone position
            const phone = document.querySelector('.phone-mockup');
            if (phone) {
                const rect = phone.getBoundingClientRect();
                const x = (rect.left + rect.width / 2) / window.innerWidth;
                const y = (rect.top + rect.height / 2) / window.innerHeight;
                
                confetti({
                    particleCount: 100,
                    spread: 70,
                    origin: { x, y },
                    colors: ['#FF7D00', '#6C63FF', '#005F73', '#FFD700', '#10b981']
                });
            }
        }
    }

    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Smooth Scrolling
class SmoothScrollManager {
    constructor() {
        this.init();
    }

    init() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    const headerHeight = document.getElementById('header')?.offsetHeight || 0;
                    const targetPosition = target.offsetTop - headerHeight - 20;
                    
                    window.scrollTo({
                        top: targetPosition,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }
}

// FAQ Manager
class FAQManager {
    constructor() {
        this.init();
    }

    init() {
        document.querySelectorAll('.faq-question').forEach(question => {
            question.addEventListener('click', () => this.toggleFAQ(question));
        });
    }

    toggleFAQ(question) {
        const faqItem = question.closest('.faq-item');
        const isActive = faqItem.classList.contains('active');
        
        // Close all FAQ items
        document.querySelectorAll('.faq-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Open clicked item if it wasn't active
        if (!isActive) {
            faqItem.classList.add('active');
        }
    }
}

// Intersection Observer for Animations
class AnimationObserver {
    constructor() {
        this.init();
    }

    init() {
        const options = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        this.observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, options);

        // Observe elements
        document.querySelectorAll('.feature-card, .step, .stat-card, .demo-card').forEach(el => {
            this.observer.observe(el);
        });
    }
}

// Copy USSD Code Function
function copyUSSDCode() {
    const code = '*384*3036#';
    const feedback = document.getElementById('copy-feedback');
    
    if (navigator.clipboard) {
        navigator.clipboard.writeText(code).then(() => {
            showCopyFeedback(feedback);
        }).catch(() => {
            fallbackCopy(code, feedback);
        });
    } else {
        fallbackCopy(code, feedback);
    }
}

function fallbackCopy(text, feedback) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showCopyFeedback(feedback);
    } catch (err) {
        console.error('Failed to copy text: ', err);
    }
    
    document.body.removeChild(textArea);
}

function showCopyFeedback(feedback) {
    if (feedback) {
        feedback.classList.add('show');
        setTimeout(() => {
            feedback.classList.remove('show');
        }, 2000);
    }
}

// Video Functions
function playVideo() {
    const placeholder = document.getElementById('video-placeholder');
    const embed = document.getElementById('video-embed');
    
    if (placeholder && embed) {
        // Show the video embed and hide placeholder
        placeholder.style.display = 'none';
        embed.style.display = 'block';
        
        // Try to play the video
        const iframe = embed.querySelector('iframe');
        if (iframe) {
            // Reload iframe to trigger autoplay
            const src = iframe.src;
            iframe.src = '';
            setTimeout(() => {
                iframe.src = src;
            }, 100);
        }
    }
}

function toggleVolume() {
    const button = document.querySelector('.volume-toggle');
    const icon = button.querySelector('i');
    
    if (icon.classList.contains('fa-volume-up')) {
        icon.classList.remove('fa-volume-up');
        icon.classList.add('fa-volume-mute');
    } else {
        icon.classList.remove('fa-volume-mute');
        icon.classList.add('fa-volume-up');
    }
}

// Performance Optimization
class PerformanceManager {
    constructor() {
        this.init();
    }

    init() {
        // Lazy load images
        this.setupLazyLoading();
        
        // Debounce scroll events
        this.setupScrollDebounce();
        
        // Preload critical resources
        this.preloadResources();
    }

    setupLazyLoading() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    }
                });
            });

            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    }

    setupScrollDebounce() {
        let ticking = false;
        
        const updateScroll = () => {
            // Scroll-based animations here
            ticking = false;
        };
        
        const requestTick = () => {
            if (!ticking) {
                requestAnimationFrame(updateScroll);
                ticking = true;
            }
        };
        
        window.addEventListener('scroll', requestTick, { passive: true });
    }

    preloadResources() {
        // Preload critical CSS
        const criticalCSS = document.createElement('link');
        criticalCSS.rel = 'preload';
        criticalCSS.as = 'style';
        criticalCSS.href = 'styles.css';
        document.head.appendChild(criticalCSS);
    }
}

// Touch and Mobile Enhancements
class TouchManager {
    constructor() {
        this.init();
    }

    init() {
        // Add touch feedback for interactive elements
        this.setupTouchFeedback();
        
        // Handle touch gestures
        this.setupGestures();
        
        // Improve mobile scrolling
        this.setupMobileScrolling();
    }

    setupTouchFeedback() {
        const interactiveElements = document.querySelectorAll(
            '.btn, .feature-card, .faq-question, .menu-item, .copy-btn'
        );
        
        interactiveElements.forEach(element => {
            element.addEventListener('touchstart', () => {
                element.style.transform = 'scale(0.98)';
            }, { passive: true });
            
            element.addEventListener('touchend', () => {
                setTimeout(() => {
                    element.style.transform = '';
                }, 150);
            }, { passive: true });
        });
    }

    setupGestures() {
        let startY = 0;
        let startX = 0;
        
        document.addEventListener('touchstart', (e) => {
            startY = e.touches[0].clientY;
            startX = e.touches[0].clientX;
        }, { passive: true });
        
        document.addEventListener('touchmove', (e) => {
            // Prevent overscroll on iOS
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });
    }

    setupMobileScrolling() {
        // Smooth scrolling for mobile
        document.documentElement.style.scrollBehavior = 'smooth';
        
        // Fix iOS scroll momentum
        document.body.style.webkitOverflowScrolling = 'touch';
    }
}

// Accessibility Enhancements
class AccessibilityManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupKeyboardNavigation();
        this.setupFocusManagement();
        this.setupARIA();
        this.setupReducedMotion();
    }

    setupKeyboardNavigation() {
        // Handle Enter key on clickable elements
        document.querySelectorAll('[onclick], .faq-question').forEach(element => {
            element.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    element.click();
                }
            });
            
            // Make focusable if not already
            if (!element.hasAttribute('tabindex')) {
                element.setAttribute('tabindex', '0');
            }
        });
    }

    setupFocusManagement() {
        // Visible focus indicators
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                document.body.classList.add('keyboard-navigation');
            }
        });
        
        document.addEventListener('mousedown', () => {
            document.body.classList.remove('keyboard-navigation');
        });
    }

    setupARIA() {
        // Add ARIA labels where needed
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.setAttribute('aria-label', 'Toggle dark/light theme');
        }
        
        const mobileToggle = document.getElementById('mobile-menu-toggle');
        if (mobileToggle) {
            mobileToggle.setAttribute('aria-label', 'Toggle mobile menu');
            mobileToggle.setAttribute('aria-expanded', 'false');
        }
    }

    setupReducedMotion() {
        // Respect user's motion preferences
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (prefersReducedMotion.matches) {
            document.documentElement.style.setProperty('--transition-fast', '0.01ms');
            document.documentElement.style.setProperty('--transition-normal', '0.01ms');
            document.documentElement.style.setProperty('--transition-slow', '0.01ms');
        }
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Core functionality
    new ThemeManager();
    new HeaderManager();
    new MobileMenuManager();
    new PhoneAnimationManager();
    new SmoothScrollManager();
    new FAQManager();
    
    // Enhancements
    new AnimationObserver();
    new PerformanceManager();
    new TouchManager();
    new AccessibilityManager();
    
    // Add loading complete class
    document.body.classList.add('loaded');
});

// Handle page visibility changes
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Pause animations when page is hidden
        document.body.classList.add('paused');
    } else {
        // Resume animations when page is visible
        document.body.classList.remove('paused');
    }
});

// Handle resize events
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        // Recalculate layouts after resize
        window.dispatchEvent(new Event('resize-complete'));
    }, 250);
});

// Service Worker registration (for PWA capabilities)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('SW registered: ', registration);
            })
            .catch(registrationError => {
                console.log('SW registration failed: ', registrationError);
            });
    });
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
    // Could send to analytics service
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    // Could send to analytics service
});