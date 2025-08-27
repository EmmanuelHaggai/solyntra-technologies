#!/bin/bash

# BTCPay Server Infrastructure Setup Script
# This script sets up a complete BTCPay Server environment for development

set -e

echo "=================================="
echo "BTCPay Server Infrastructure Setup"
echo "=================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        print_status "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        print_status "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create required directories
create_directories() {
    print_status "Creating required directories..."
    mkdir -p data/{bitcoin,lnd,btcpay,postgres,tor}
    mkdir -p logs
    print_success "Directories created"
}

# Setup environment file
setup_environment() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f .env ]; then
        print_status "Copying .env.btcpay.example to .env..."
        cp .env.btcpay.example .env
        print_warning "Please update .env file with your specific configuration"
    else
        print_warning ".env file already exists. Skipping copy."
    fi
}

# Start BTCPay Server infrastructure
start_infrastructure() {
    print_status "Starting BTCPay Server infrastructure..."
    
    # Pull images first
    print_status "Pulling Docker images..."
    docker-compose -f docker-compose.btcpay.yml pull
    
    # Start services in correct order
    print_status "Starting PostgreSQL..."
    docker-compose -f docker-compose.btcpay.yml up -d postgres
    sleep 10
    
    print_status "Starting Bitcoin Core..."
    docker-compose -f docker-compose.btcpay.yml up -d bitcoind
    sleep 20
    
    print_status "Starting NBXplorer..."
    docker-compose -f docker-compose.btcpay.yml up -d nbxplorer
    sleep 15
    
    print_status "Starting LND..."
    docker-compose -f docker-compose.btcpay.yml up -d lnd
    sleep 20
    
    print_status "Starting BTCPay Server..."
    docker-compose -f docker-compose.btcpay.yml up -d btcpayserver
    
    print_status "Starting Tor (optional)..."
    docker-compose -f docker-compose.btcpay.yml up -d tor
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."
    
    # Wait for Bitcoin Core RPC
    print_status "Waiting for Bitcoin Core RPC..."
    for i in {1..30}; do
        if curl -s --user bitcoinrpc:bitcoinrpc123 --data-binary '{"jsonrpc":"1.0","id":"curltest","method":"getblockchaininfo","params":[]}' -H 'content-type: text/plain;' http://localhost:43782/ >/dev/null 2>&1; then
            print_success "Bitcoin Core RPC is ready"
            break
        fi
        sleep 5
        echo -n "."
    done
    
    # Wait for BTCPay Server
    print_status "Waiting for BTCPay Server..."
    for i in {1..60}; do
        if curl -s http://localhost:23000/health >/dev/null 2>&1; then
            print_success "BTCPay Server is ready"
            break
        fi
        sleep 5
        echo -n "."
    done
}

# Initialize Bitcoin regtest environment
init_bitcoin_regtest() {
    print_status "Initializing Bitcoin regtest environment..."
    
    # Generate initial blocks
    print_status "Generating initial blocks for regtest..."
    docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 createwallet "default" || true
    docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 generatetoaddress 101 $(docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 getnewaddress)
    
    print_success "Bitcoin regtest environment initialized"
}

# Initialize LND wallet
init_lnd_wallet() {
    print_status "Initializing LND wallet..."
    
    # Check if wallet already exists
    if docker exec lnd lncli --network=regtest walletbalance >/dev/null 2>&1; then
        print_warning "LND wallet already exists"
        return
    fi
    
    # Create LND wallet
    print_status "Creating LND wallet..."
    docker exec -i lnd lncli --network=regtest create <<EOF
12345678
12345678
n
abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about
EOF
    
    sleep 10
    print_success "LND wallet created"
}

# Show service status
show_status() {
    echo ""
    echo "=================================="
    echo "Service Status"
    echo "=================================="
    
    docker-compose -f docker-compose.btcpay.yml ps
    
    echo ""
    echo "=================================="
    echo "Service URLs"
    echo "=================================="
    echo "BTCPay Server:   http://localhost:23000"
    echo "Bitcoin Core:    RPC on localhost:43782"
    echo "LND REST API:    https://localhost:8080"
    echo "NBXplorer:       http://localhost:32838"
    echo "PostgreSQL:      localhost:5432"
    echo ""
    echo "=================================="
    echo "Next Steps"
    echo "=================================="
    echo "1. Visit http://localhost:23000 to set up BTCPay Server"
    echo "2. Create a store and configure Lightning Network"
    echo "3. Generate an API key with invoice permissions"
    echo "4. Update your .env file with the API key and store ID"
    echo "5. Run your USSD application with: python app.py"
}

# Cleanup function
cleanup() {
    print_status "Stopping BTCPay Server infrastructure..."
    docker-compose -f docker-compose.btcpay.yml down
    print_success "Infrastructure stopped"
}

# Main execution
main() {
    case "${1:-start}" in
        start)
            check_docker
            create_directories
            setup_environment
            start_infrastructure
            wait_for_services
            init_bitcoin_regtest
            init_lnd_wallet
            show_status
            ;;
        stop)
            cleanup
            ;;
        restart)
            cleanup
            sleep 5
            main start
            ;;
        status)
            docker-compose -f docker-compose.btcpay.yml ps
            show_status
            ;;
        logs)
            docker-compose -f docker-compose.btcpay.yml logs -f
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|logs}"
            echo ""
            echo "Commands:"
            echo "  start   - Start BTCPay Server infrastructure"
            echo "  stop    - Stop BTCPay Server infrastructure"  
            echo "  restart - Restart BTCPay Server infrastructure"
            echo "  status  - Show service status"
            echo "  logs    - Show service logs"
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap cleanup EXIT

# Run main function
main "$@"