# Bitcoin Lightning USSD System

A USSD-based Bitcoin Lightning payment system that integrates Africa's Talking USSD API, Python Flask, MeTTa language for symbolic reasoning, and Bitcoin Lightning Network.

## 🚀 Features

- **USSD Interface**: Interactive USSD menus for Bitcoin Lightning payments
- **Lightning Network**: Support for LND, LNbits, and mock backends
- **MeTTa Integration**: Symbolic reasoning for state management and validation
- **M-Pesa Integration**: Simulated KES ↔ Bitcoin conversions
- **Multi-language**: English and Swahili support
- **Real-time Balances**: Sync between MeTTa knowledge base and Lightning API

## 📱 USSD Menu Structure

```
Bitcoin Lightning
Balance: X sats

1. Send BTC       → Enter phone → Enter amount → Confirm
2. Receive BTC    → Enter amount → Get invoice code
3. Send Invoice   → Enter phone → Enter amount → Send via SMS
4. Top Up M-Pesa  → Enter KES → Enter M-Pesa code → Convert
5. Withdraw M-Pesa → Enter KES → Enter M-Pesa number → Convert
0. Exit
```

## 🏗️ Architecture

```
USSD Request → Flask App → USSDHandlers → MeTTa + Lightning API
                    ↓
            Africa's Talking Response
```

### Components

1. **app.py**: Flask USSD endpoint handling Africa's Talking protocol
2. **handlers.py**: Business logic with MeTTa integration
3. **lightning.py**: Lightning Network API wrapper (LND/LNbits/Mock)
4. **atoms_simple.metta**: MeTTa knowledge base for users, balances, rules
5. **test_ussd.py**: Test suite for USSD flows

## 🛠️ Installation

### 1. Environment Setup

```bash
# Ubuntu setup
sudo apt update
sudo apt install python3.12-venv -y

# Create project
mkdir MeTTaProject
cd MeTTaProject
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install hyperon==0.2.2 flask requests
```

### 2. Project Structure

```
MeTTaProject/
├── app.py                 # Flask USSD handler
├── handlers.py           # Lightning + MeTTa functions  
├── lightning.py          # Lightning API wrapper
├── atoms_simple.metta    # MeTTa knowledge base
├── test_ussd.py         # Test suite
├── requirements.txt     # Dependencies
└── venv/               # Virtual environment
```

## 🚦 Usage

### 1. Start the Server

```bash
source venv/bin/activate
python app.py
```

The server starts on `https://btc.emmanuelhaggai.com` with demo balances:
- `+254712345678`: 100,000 sats
- `+254787654321`: 50,000 sats  
- `+254798765432`: 75,000 sats

### 2. Test USSD Flows

```bash
# Run automated tests
python test_ussd.py

# Or test manually with curl
curl -X POST https://btc.emmanuelhaggai.com/ussd \
  -d "sessionId=test123" \
  -d "serviceCode=*384*123#" \
  -d "phoneNumber=+254712345678" \
  -d "text="
```

### 3. Africa's Talking Integration

Configure your Africa's Talking USSD service to POST to:
```
https://btc.emmanuelhaggai.com/ussd
```

## 🧠 MeTTa Integration

The system uses MeTTa for symbolic reasoning:

```metta
; User balances
(Balance "+254712345678" 100000)

; Transaction history  
(Transaction "+254712345678" "+254787654321" 20000)

; System rules
(MinAmount 1000)
(MaxAmount 1000000)
```

Query balances:
```python
result = metta.run('!(match &self (Balance "+254712345678" $b) $b)')
```

## ⚡ Lightning Network Backends

### Mock Mode (Default)
```python
lightning_api = LightningAPI("mock")
```

### LNbits Integration
```python
lightning_api = LightningAPI("lnbits", 
    lnbits_url="https://lnb.emmanuelhaggai.com",
    lnbits_admin_key="your-admin-key"
)
```

### LND Integration
```python
lightning_api = LightningAPI("lnd",
    lnd_url="https://lnb.emmanuelhaggai.com:8080",
    lnd_macaroon="your-macaroon-hex"
)
```

### BTCPay Server Integration
```python
lightning_api = LightningAPI("btcpay",
    btcpay_url="https://btc.emmanuelhaggai.com",
    btcpay_api_key="your-api-key",
    btcpay_store_id="your-store-id"
)
```

## 💱 Exchange Rates

Current rate: **150 KES = 1,000 sats**

```python
# Convert KES to sats
sats = kes_amount * (1000 / 150)

# Convert sats to KES  
kes = sats_amount * (150 / 1000)
```

## 🔧 API Endpoints

### USSD Endpoint
```
POST /ussd
Content-Type: application/x-www-form-urlencoded

sessionId=ATUid_session123
serviceCode=*384*123#
phoneNumber=+254712345678
text=1*+254787654321*5000
```

### Status Endpoint
```
GET /status
Response: {"status": "running", "active_sessions": 0}
```

### Test Endpoint
```
GET /test  
Response: {"test_phone": "+254712345678", "balance": 100000}
```

## 🧪 Testing

### Unit Tests
```bash
source venv/bin/activate

# Test MeTTa loading
python -c "from handlers import ussd_handlers; print('✓ MeTTa loaded')"

# Test Lightning API
python -c "from lightning import lightning_api; print('✓ Lightning API ready')"

# Test Flask import
python -c "from app import app; print('✓ Flask app ready')"
```

### USSD Flow Tests
```bash
# Start server in background
python app.py &

# Run test suite
python test_ussd.py

# Manual test
curl -X POST localhost:5000/ussd -d "sessionId=test" -d "phoneNumber=+254712345678" -d "text="
```

## 🔒 Security Features

- Phone number validation and normalization
- Amount limits (1,000 - 1,000,000 sats)
- Session management with automatic cleanup
- Input sanitization and validation
- Lightning invoice verification

## 🌍 Localization

Supports English and Swahili:

```metta
(Language "+254712345678" "en")
(Language "+254787654321" "sw")  ; Swahili
```

Menu automatically adapts based on user preference.

## 📊 Transaction Flow Example

```
User dials *384*123#
├── Shows main menu with balance
├── Selects "1" (Send BTC)  
├── Enters recipient: +254787654321
├── Enters amount: 20000 sats
├── System validates balance & limits
├── Creates Lightning invoice for recipient
├── Pays invoice via Lightning API
├── Updates MeTTa balances
└── Returns confirmation: "Sent 20000 sats"
```

## 🐛 Troubleshooting

### Common Issues

1. **MeTTa syntax warnings**: Use simplified atoms without nested expressions
2. **Import errors**: Ensure you're in the project directory with activated venv
3. **Lightning API failures**: Check backend configuration and connectivity
4. **USSD timeout**: Africa's Talking sessions timeout after 30s of inactivity

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Production Deployment

1. **Use production WSGI server**: Gunicorn, uWSGI
2. **Configure real Lightning backend**: LND, LNbits, or BTCPay Server
3. **Set up Redis**: For session storage
4. **Enable HTTPS**: Required for Africa's Talking webhooks
5. **Database storage**: Replace mock data with PostgreSQL/MySQL
6. **M-Pesa integration**: Use Safaricom Daraja API

### BTCPay Server Configuration

For production BTCPay Server integration:

1. **Install BTCPay Server**: Follow the [BTCPay Server deployment guide](https://docs.btcpayserver.org/)
2. **Create a store**: Set up your BTCPay store and configure Lightning Network
3. **Generate API key**: Create an API key with `btcpay.store.cancreateinvoice` and `btcpay.store.canviewinvoices` permissions
4. **Set environment variables**:
   ```bash
   export LIGHTNING_API_TYPE=btcpay
   export BTCPAY_URL=https://btc.emmanuelhaggai.com
   export BTCPAY_API_KEY=your-api-key
   export BTCPAY_STORE_ID=your-store-id
   ```
5. **Configure Lightning Node**: Ensure BTCPay Server is connected to a Lightning Network node (LND, c-lightning, or Eclair)

## 🏗️ BTCPay Server Infrastructure Setup

For local development and testing, we provide a complete BTCPay Server infrastructure using Docker.

### Quick Setup

```bash
# 1. Start BTCPay Server infrastructure
./setup_btcpay.sh start

# 2. Check health status
python btcpay_health_check.py

# 3. Configure your application
cp .env.btcpay.example .env
# Edit .env with your BTCPay API key and store ID
```

### Infrastructure Components

The Docker setup includes:

- **BTCPay Server**: Main payment processor (https://lnb.emmanuelhaggai.com:23000)
- **Bitcoin Core**: Regtest network for development (RPC: localhost:43782)
- **LND**: Lightning Network daemon (REST: https://lnb.emmanuelhaggai.com:8080)
- **NBXplorer**: Bitcoin blockchain explorer (localhost:32838)
- **PostgreSQL**: Database backend (localhost:5432)
- **Tor**: Privacy network (optional)

### Setup Script Commands

```bash
./setup_btcpay.sh start     # Start all services
./setup_btcpay.sh stop      # Stop all services
./setup_btcpay.sh restart   # Restart all services
./setup_btcpay.sh status    # Show service status
./setup_btcpay.sh logs      # View service logs
```

### Initial Configuration Steps

1. **Start Infrastructure**:
   ```bash
   ./setup_btcpay.sh start
   ```

2. **Visit BTCPay Server**: Open https://lnb.emmanuelhaggai.com:23000
   - Create administrator account
   - Complete initial setup wizard

3. **Create Store**:
   - Go to Stores → Create Store
   - Configure store settings
   - Note the Store ID from the URL

4. **Generate API Key**:
   - Go to Account → Manage Account → API Keys
   - Create new API key with permissions:
     - `btcpay.store.cancreateinvoice`
     - `btcpay.store.canviewinvoices`

5. **Update Environment**:
   ```bash
   cp .env.btcpay.example .env
   # Edit .env file with your API key and store ID
   ```

6. **Test Configuration**:
   ```bash
   python btcpay_health_check.py
   ```

### Development Workflow

```bash
# Start BTCPay infrastructure
./setup_btcpay.sh start

# Wait for services to be ready
python btcpay_health_check.py wait

# Run your USSD application
python app.py
```

### Regtest Bitcoin Commands

For testing, you can interact with the Bitcoin regtest network:

```bash
# Generate blocks
docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 generatetoaddress 10 $(docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 getnewaddress)

# Check balance
docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 getbalance

# Send Bitcoin
docker exec bitcoind bitcoin-cli -regtest -rpcuser=bitcoinrpc -rpcpassword=bitcoinrpc123 sendtoaddress ADDRESS AMOUNT
```

### LND Lightning Commands

```bash
# Check LND status
docker exec lnd lncli --network=regtest getinfo

# Create Lightning channel
docker exec lnd lncli --network=regtest connect PUBKEY@HOST:PORT
docker exec lnd lncli --network=regtest openchannel PUBKEY AMOUNT

# Check Lightning balance
docker exec lnd lncli --network=regtest walletbalance
docker exec lnd lncli --network=regtest channelbalance
```

### Troubleshooting

**Services not starting:**
- Check Docker is running: `docker info`
- Check logs: `./setup_btcpay.sh logs`
- Restart services: `./setup_btcpay.sh restart`

**BTCPay Server not accessible:**
- Wait for initialization (can take 2-3 minutes)
- Check service status: `./setup_btcpay.sh status`
- View BTCPay logs: `docker logs btcpay_server`

**API key issues:**
- Ensure API key has correct permissions
- Check store ID matches your store
- Run health check: `python btcpay_health_check.py`

**Lightning issues:**
- Wait for LND wallet creation
- Check LND logs: `docker logs lnd`
- Ensure Bitcoin blocks are generated for regtest

## 📝 License

MIT License - feel free to use and modify for your Bitcoin Lightning projects!

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality  
4. Ensure all tests pass
5. Submit pull request

## 📞 Support

For issues with:
- **MeTTa integration**: Check hyperon documentation
- **Lightning Network**: Verify your LND/LNbits setup
- **USSD API**: Review Africa's Talking documentation
- **General bugs**: Open GitHub issue with logs

---

**Built with ❤️ for the African Bitcoin community**# MeTTaProject
# solyntra-technologies
# solyntra-technologies
