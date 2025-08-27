#!/bin/bash
# USSD Lightning Network - Public Endpoint Setup

echo "🚀 Setting up public endpoints for USSD Lightning Network"
echo "=================================================="

# Check if application is running
if curl -s http://localhost:5000/status > /dev/null; then
    echo "✅ Local application is running on port 5000"
else
    echo "❌ Local application not running. Start with: python app.py"
    exit 1
fi

echo ""
echo "🌐 Choose your tunneling method:"
echo "1. ngrok (requires free account)"
echo "2. Manual setup instructions"
echo "3. Deploy to your server"

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "📋 ngrok Setup Instructions:"
        echo "1. Sign up: https://dashboard.ngrok.com/signup"
        echo "2. Get authtoken: https://dashboard.ngrok.com/get-started/your-authtoken"
        echo "3. Run: ./ngrok config add-authtoken YOUR_TOKEN"
        echo "4. Run: ./ngrok http 5000"
        echo "5. Copy the https URL (e.g., https://abc123.ngrok.io)"
        echo ""
        echo "💡 Then update Africa's Talking with:"
        echo "   Callback: https://YOUR-NGROK-URL.ngrok.io/ussd"
        echo "   Events: https://YOUR-NGROK-URL.ngrok.io/ussd"
        ;;
    2)
        echo ""
        echo "📋 Manual Setup:"
        echo "Your local endpoints:"
        echo "   🔹 USSD Handler: http://localhost:5000/ussd"
        echo "   🔹 Status: http://localhost:5000/status"
        echo "   🔹 Test: http://localhost:5000/test"
        echo ""
        echo "To make public:"
        echo "1. Use ngrok, localtunnel, or similar"
        echo "2. Deploy to cloud (AWS, Heroku, DigitalOcean)"
        echo "3. Use your existing domain (mabopay.com)"
        ;;
    3)
        echo ""
        echo "📋 Deploy to Server:"
        echo "1. Copy files to your server: mabopay.com"
        echo "2. Install dependencies: pip install -r requirements.txt"
        echo "3. Set up database connection"
        echo "4. Run: python app.py"
        echo "5. Configure web server (nginx/apache)"
        echo ""
        echo "💡 Your endpoints would be:"
        echo "   Callback: https://mabopay.com/ussd/lightning.php"
        echo "   Events: https://mabopay.com/ussd/lightning.php"
        ;;
esac

echo ""
echo "🧪 Test your setup:"
echo "curl -X POST YOUR-PUBLIC-URL/ussd \\"
echo "  -d 'sessionId=TEST123' \\"
echo "  -d 'serviceCode=*384*3036#' \\"
echo "  -d 'phoneNumber=+254712345678' \\"
echo "  -d 'text='"

echo ""
echo "🎯 Your USSD Code: *384*3036#"
echo "📱 Demo Users: +254712345678, +254787654321, +254798765432"