#!/bin/bash
# Example API requests for the Similarity Intelligence Platform

# Set your API key here
API_KEY="your-api-key-here"
BASE_URL="http://localhost:8000/v1"

echo "========================================="
echo "Similarity Intelligence Platform - Demo"
echo "========================================="
echo ""

# 1. Check usage
echo "1. Getting usage statistics..."
curl -X GET "$BASE_URL/usage" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" | jq '.'

echo -e "\n\n"

# 2. Submit article for checking
echo "2. Submitting article for similarity check..."

ARTICLE_TEXT="Artificial intelligence has transformed the way we approach software development. Machine learning models can now understand natural language, generate code, and even detect bugs automatically. This technological advancement has implications for developers worldwide, changing the skills needed and the tools we use daily. The integration of AI into development workflows represents a paradigm shift in how we build and maintain software systems."

RESPONSE=$(curl -X POST "$BASE_URL/check" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"article_text\": \"$ARTICLE_TEXT\",
    \"language\": \"en\",
    \"sources\": [\"articles\", \"youtube\"],
    \"sensitivity\": \"medium\",
    \"metadata\": {
      \"title\": \"AI in Software Development\",
      \"author\": \"Demo User\"
    }
  }" | jq '.')

echo "$RESPONSE"

# Extract check_id
CHECK_ID=$(echo "$RESPONSE" | jq -r '.check_id')

echo -e "\n\n"

# 3. Poll for results
echo "3. Polling for results (check_id: $CHECK_ID)..."
echo "   Waiting 5 seconds before first poll..."
sleep 5

MAX_POLLS=10
POLL_INTERVAL=3

for i in $(seq 1 $MAX_POLLS); do
  echo "   Poll attempt $i/$MAX_POLLS..."

  RESULT=$(curl -X GET "$BASE_URL/check/$CHECK_ID" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" | jq '.')

  STATUS=$(echo "$RESULT" | jq -r '.status')

  echo "   Status: $STATUS"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo -e "\n   Final result:"
    echo "$RESULT" | jq '.'
    break
  fi

  if [ $i -lt $MAX_POLLS ]; then
    echo "   Waiting $POLL_INTERVAL seconds..."
    sleep $POLL_INTERVAL
  fi
done

echo -e "\n\n"
echo "========================================="
echo "Demo complete!"
echo "========================================="
