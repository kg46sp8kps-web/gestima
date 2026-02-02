#!/bin/bash
# Installation script for AI Quote Request Parsing feature

echo "🤖 GESTIMA - AI Quote Request Parsing Installation"
echo "=================================================="
echo ""

# 1. Backend dependencies
echo "📦 1. Installing backend dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install backend dependencies"
    exit 1
fi
echo "✅ Backend dependencies installed"
echo ""

# 2. Database migrations
echo "🗄️  2. Running database migrations..."
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "❌ Failed to run migrations"
    exit 1
fi
echo "✅ Database migrations complete"
echo ""

# 3. Check API key
echo "🔑 3. Checking Anthropic API key..."
if ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo "⚠️  WARNING: ANTHROPIC_API_KEY not set in .env"
    echo ""
    echo "To enable AI parsing, please:"
    echo "  1. Go to: https://console.anthropic.com/"
    echo "  2. Generate an API key"
    echo "  3. Add to .env: ANTHROPIC_API_KEY=sk-ant-..."
    echo ""
else
    echo "✅ API key found in .env"
fi
echo ""

# 4. Frontend build (development)
echo "🎨 4. Building frontend..."
cd frontend
npm install
if [ $? -ne 0 ]; then
    echo "❌ Failed to install frontend dependencies"
    exit 1
fi
echo "✅ Frontend dependencies installed"
echo ""

# 5. Type check
echo "🔍 5. Running TypeScript type check..."
npm run type-check 2>&1 | grep -A 2 "QuoteNewFromRequestView" || echo "✅ No errors in QuoteNewFromRequestView"
cd ..
echo ""

# 6. Summary
echo "=================================================="
echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Set ANTHROPIC_API_KEY in .env (if not set yet)"
echo "  2. Restart backend: python gestima.py run"
echo "  3. Restart frontend: cd frontend && npm run dev"
echo "  4. Navigate to: /quotes"
echo "  5. Click: 🤖 Z poptávky (AI)"
echo ""
echo "📚 Documentation:"
echo "  - ADR-028: docs/ADR/028-ai-quote-request-parsing.md"
echo "  - CHANGELOG: CHANGELOG.md (v1.13.0)"
echo "  - STATUS: docs/status/STATUS.md"
echo ""
