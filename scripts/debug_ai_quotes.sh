#!/bin/bash
# Debug script for AI Quote Request Parsing feature

echo "🔍 GESTIMA - AI Quote Request Debugging"
echo "========================================"
echo ""

echo "1️⃣ Checking frontend files..."
echo ""

# Check if QuoteNewFromRequestView exists
if [ -f "frontend/src/views/quotes/QuoteNewFromRequestView.vue" ]; then
    echo "✅ QuoteNewFromRequestView.vue exists"
    lines=$(wc -l < frontend/src/views/quotes/QuoteNewFromRequestView.vue)
    echo "   Lines: $lines"
else
    echo "❌ QuoteNewFromRequestView.vue MISSING!"
fi

# Check if route exists
if grep -q "quote-new-from-request" frontend/src/router/index.ts; then
    echo "✅ Route registered in router"
else
    echo "❌ Route NOT registered!"
fi

# Check if button exists in QuotesListView
if grep -q "Z poptávky (AI)" frontend/src/views/quotes/QuotesListView.vue; then
    echo "✅ Button exists in QuotesListView"
    echo "   Line: $(grep -n "Z poptávky (AI)" frontend/src/views/quotes/QuotesListView.vue | cut -d: -f1)"
else
    echo "❌ Button NOT found in QuotesListView!"
fi

# Check if API methods exist
if grep -q "parseQuoteRequest" frontend/src/api/quotes.ts; then
    echo "✅ parseQuoteRequest API method exists"
else
    echo "❌ parseQuoteRequest API method MISSING!"
fi

# Check if store actions exist
if grep -q "parseQuoteRequestPDF" frontend/src/stores/quotes.ts; then
    echo "✅ Store actions exist"
else
    echo "❌ Store actions MISSING!"
fi

echo ""
echo "2️⃣ Checking backend files..."
echo ""

# Check if endpoint exists
if grep -q "parse-request" app/routers/quotes_router.py; then
    echo "✅ parse-request endpoint exists"
    echo "   Line: $(grep -n "parse-request" app/routers/quotes_router.py | head -1 | cut -d: -f1)"
else
    echo "❌ parse-request endpoint MISSING!"
fi

# Check if service exists
if [ -f "app/services/quote_request_parser.py" ]; then
    echo "✅ quote_request_parser.py exists"
    lines=$(wc -l < app/services/quote_request_parser.py)
    echo "   Lines: $lines"
else
    echo "❌ quote_request_parser.py MISSING!"
fi

# Check if schemas exist
if [ -f "app/schemas/quote_request.py" ]; then
    echo "✅ quote_request.py schemas exist"
    lines=$(wc -l < app/schemas/quote_request.py)
    echo "   Lines: $lines"
else
    echo "❌ quote_request.py schemas MISSING!"
fi

# Check if migration exists
if ls alembic/versions/*article_number_unique*.py 2>/dev/null; then
    echo "✅ Migration exists"
else
    echo "❌ Migration MISSING!"
fi

echo ""
echo "3️⃣ Checking configuration..."
echo ""

# Check if API key is set
if grep -q "ANTHROPIC_API_KEY=" .env 2>/dev/null; then
    if grep -q "ANTHROPIC_API_KEY=sk-ant-" .env; then
        echo "✅ API key set in .env"
    else
        echo "⚠️  API key empty in .env"
    fi
else
    echo "❌ API key NOT in .env"
fi

# Check if rate limit is set
if grep -q "AI_RATE_LIMIT=" app/config.py; then
    echo "✅ AI_RATE_LIMIT configured"
else
    echo "❌ AI_RATE_LIMIT NOT configured"
fi

echo ""
echo "4️⃣ Process check..."
echo ""

# Check if backend is running
if pgrep -f "gestima.py run" > /dev/null; then
    echo "✅ Backend process running"
else
    echo "⚠️  Backend NOT running (expected if stopped)"
fi

# Check if frontend dev server is running
if lsof -i:5173 > /dev/null 2>&1; then
    echo "✅ Frontend dev server running (port 5173)"
else
    echo "⚠️  Frontend dev server NOT running"
fi

echo ""
echo "========================================"
echo "🏁 Debug complete!"
echo ""
echo "If all checks pass but you still don't see the button:"
echo "  1. Hard refresh browser: Ctrl+Shift+R"
echo "  2. Clear browser cache completely"
echo "  3. Restart frontend: cd frontend && npm run dev"
echo "  4. Check browser console (F12) for errors"
echo ""
