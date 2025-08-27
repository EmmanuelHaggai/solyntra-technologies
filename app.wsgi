#!/usr/bin/env python3
"""
WSGI configuration for USSD Lightning Network Application
"""
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, '/var/www/btc.emmanuelhaggai.com')

# Set environment variables
os.environ['PYTHONPATH'] = '/var/www/btc.emmanuelhaggai.com'

# Load environment variables
sys.path.insert(0, '/var/www/btc.emmanuelhaggai.com')
os.chdir('/var/www/btc.emmanuelhaggai.com')

# Load .env file
from dotenv import load_dotenv
load_dotenv('/var/www/btc.emmanuelhaggai.com/.env')

# Activate virtual environment
activate_this = '/var/www/btc.emmanuelhaggai.com/venv/bin/activate_this.py'
if os.path.exists(activate_this):
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

# Configure logging for WSGI
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Import the Flask application
try:
    from app import app as application
    application.debug = False
    logging.info("WSGI: Flask application loaded successfully")
except ImportError as e:
    # Fallback for debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to import Flask app: {e}")
    
    # Create a simple WSGI app for debugging
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/plain')]
        start_response(status, headers)
        return [f"Import Error: {str(e)}".encode('utf-8')]

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000, debug=True)