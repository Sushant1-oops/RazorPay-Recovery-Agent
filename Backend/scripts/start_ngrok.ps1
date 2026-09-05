# Expose the local backend (default port 8000) via ngrok so Razorpay's
# test-mode webhook can reach it without deploying anywhere.
#
# One-time setup:
#   1. Install ngrok:        https://ngrok.com/download   (or `choco install ngrok`)
#   2. Add your authtoken:   ngrok config add-authtoken <your-token-from-ngrok-dashboard>
#   3. Run the backend in another terminal first:
#        uvicorn app.main:app --reload --port 8000
#
# Then run this script. It starts ngrok and prints the URL to register
# in the Razorpay Dashboard -> Settings -> Webhooks as:
#   https://<random>.ngrok-free.app/api/v1/webhooks/razorpay
#
# Set the SAME secret you enter there as RAZORPAY_WEBHOOK_SECRET in your .env,
# then restart the backend so it picks it up.

param(
    [int]$Port = 8000
)

Write-Host "Starting ngrok tunnel to http://localhost:$Port ..." -ForegroundColor Cyan
Write-Host "(Ctrl+C to stop. Backend must already be running on this port.)" -ForegroundColor DarkGray
Write-Host ""

ngrok http $Port

# After ngrok starts, copy the "Forwarding" HTTPS URL it prints, e.g.:
#   https://abcd-12-34-56-78.ngrok-free.app
# Webhook URL to paste into Razorpay is that URL + /api/v1/webhooks/razorpay
