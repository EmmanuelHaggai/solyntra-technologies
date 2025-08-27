#!/bin/bash

# Production Setup Script for USSD Lightning Network Application
# Sets up Apache, SSL, and Python dependencies

set -e

echo "=================================="
echo "USSD Lightning Production Setup"
echo "=================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR="/root/metta/MeTTaProject"
DOMAIN="btc.emmanuelhaggai.com"

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root (use sudo)"
        exit 1
    fi
}

# Install required packages
install_packages() {
    print_status "Installing required packages..."
    
    # Update package list
    apt update
    
    # Install Python and mod_wsgi
    apt install -y python3 python3-pip python3-venv libapache2-mod-wsgi-py3
    
    # Install certbot for SSL
    apt install -y certbot python3-certbot-apache
    
    print_success "Packages installed"
}

# Enable Apache modules
enable_apache_modules() {
    print_status "Enabling Apache modules..."
    
    a2enmod wsgi
    a2enmod rewrite
    a2enmod ssl
    a2enmod headers
    
    print_success "Apache modules enabled"
}

# Setup Python virtual environment
setup_python_env() {
    print_status "Setting up Python virtual environment..."
    
    cd $PROJECT_DIR
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        print_warning "requirements.txt not found, installing basic packages"
        pip install flask requests hyperon pymysql python-dotenv
    fi
    
    print_success "Python environment setup complete"
}

# Configure Apache virtual host
setup_apache_vhost() {
    print_status "Configuring Apache virtual host..."
    
    # Copy virtual host configuration
    cp $PROJECT_DIR/btc.emmanuelhaggai.com.conf /etc/apache2/sites-available/
    
    # Enable the site
    a2ensite btc.emmanuelhaggai.com.conf
    
    # Disable default site
    a2dissite 000-default.conf || true
    
    # Test Apache configuration
    if apache2ctl configtest; then
        print_success "Apache configuration is valid"
    else
        print_error "Apache configuration has errors"
        exit 1
    fi
    
    # Reload Apache
    systemctl reload apache2
    
    print_success "Apache virtual host configured"
}

# Set file permissions
set_permissions() {
    print_status "Setting file permissions..."
    
    # Make WSGI file executable
    chmod +x $PROJECT_DIR/app.wsgi
    
    # Set proper ownership (Apache runs as www-data)
    chown -R www-data:www-data $PROJECT_DIR
    
    # Set proper permissions for .env file (sensitive)
    chmod 600 $PROJECT_DIR/.env
    chown www-data:www-data $PROJECT_DIR/.env
    
    print_success "File permissions set"
}

# Setup SSL certificate
setup_ssl() {
    print_status "Setting up SSL certificate..."
    
    # Check if domain resolves
    if ! nslookup $DOMAIN >/dev/null 2>&1; then
        print_warning "Domain $DOMAIN may not be properly configured"
        print_warning "Make sure your DNS points to this server"
    fi
    
    # Get SSL certificate
    print_status "Obtaining SSL certificate from Let's Encrypt..."
    certbot --apache -d $DOMAIN --non-interactive --agree-tos --email admin@emmanuelhaggai.com --redirect
    
    if [ $? -eq 0 ]; then
        print_success "SSL certificate installed successfully"
    else
        print_warning "SSL certificate installation failed"
        print_warning "You can run 'certbot --apache -d $DOMAIN' manually later"
    fi
}

# Test the application
test_application() {
    print_status "Testing application..."
    
    # Test HTTP endpoint
    if curl -s http://$DOMAIN/status >/dev/null; then
        print_success "HTTP endpoint is accessible"
    else
        print_warning "HTTP endpoint test failed"
    fi
    
    # Test HTTPS endpoint (if SSL is configured)
    if curl -s https://$DOMAIN/status >/dev/null; then
        print_success "HTTPS endpoint is accessible"
    else
        print_warning "HTTPS endpoint test failed"
    fi
}

# Show status and next steps
show_status() {
    echo ""
    echo "=================================="
    echo "Setup Complete!"
    echo "=================================="
    echo "Domain: $DOMAIN"
    echo "Project Directory: $PROJECT_DIR"
    echo ""
    echo "Test URLs:"
    echo "- Status: https://$DOMAIN/status"
    echo "- USSD Webhook: https://$DOMAIN/ussd"
    echo "- Test Endpoint: https://$DOMAIN/test"
    echo ""
    echo "Log files:"
    echo "- Apache Error: /var/log/apache2/btc.emmanuelhaggai.com_error.log"
    echo "- Apache Access: /var/log/apache2/btc.emmanuelhaggai.com_access.log"
    echo ""
    echo "Next steps:"
    echo "1. Configure Africa's Talking webhook URL: https://$DOMAIN/ussd"
    echo "2. Update AFRICASTALKING_API_KEY in .env file"
    echo "3. Test USSD functionality"
    echo "=================================="
}

# Main execution
main() {
    check_root
    install_packages
    enable_apache_modules
    setup_python_env
    setup_apache_vhost
    set_permissions
    setup_ssl
    test_application
    show_status
}

# Run main function
main "$@"