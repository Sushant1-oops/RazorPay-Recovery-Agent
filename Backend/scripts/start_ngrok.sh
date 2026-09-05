#!/usr/bin/env bash
# Expose the local backend (default port 8000) via ngrok so Razorpay's
# test-mode webhook can reach it without deploying anywhere.
#
# One-time setup:
#   1. Install ngrok:        https://ngrok.com/download
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

PORT="${1:-8000}"

echo "Starting ngrok tunnel to http://localhost:${PORT} ..."
echo "(Ctrl+C to stop. Backend must already be running on this port.)"
echo ""

ngrok http "${PORT}"
