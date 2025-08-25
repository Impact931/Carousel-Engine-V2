#!/bin/bash

# Pre-Deployment Readiness Check
# Only deploy after ALL these checks pass locally

set -e  # Exit on any error

echo "🏁 Running complete deployment readiness check..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check functions
check_step() {
    echo -e "${YELLOW}🔍 $1${NC}"
}

pass_step() {
    echo -e "${GREEN}✅ $1${NC}"
}

fail_step() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# 1. Code Quality Gates
check_step "Running code quality checks..."

echo "  • Linting..."
npm run lint > /dev/null 2>&1 || fail_step "Linting failed - fix errors before deployment"
pass_step "Linting passed"

echo "  • Type checking..."
npm run typecheck > /dev/null 2>&1 || fail_step "TypeScript errors found - fix before deployment"
pass_step "Type checking passed"

echo "  • Unit tests..."
npm run test > /dev/null 2>&1 || fail_step "Unit tests failing - fix before deployment"
pass_step "Unit tests passed"

echo "  • Test coverage..."
COVERAGE=$(npm run test:coverage --silent 2>/dev/null | grep "All files" | awk '{print $10}' | sed 's/%//' || echo "0")
if [ -z "$COVERAGE" ] || [ "$COVERAGE" -lt 80 ]; then
    fail_step "Test coverage below 80% - add more tests"
fi
pass_step "Test coverage: ${COVERAGE}%"

# 2. Security Gates
check_step "Running security checks..."

echo "  • Dependency audit..."
npm audit --audit-level high > /dev/null 2>&1 || fail_step "High/critical vulnerabilities found - update dependencies"
pass_step "No high/critical vulnerabilities"

echo "  • Secret scanning..."
if command -v git-secrets &> /dev/null; then
    git secrets --scan || fail_step "Secrets detected in code - remove before deployment"
    pass_step "No secrets detected"
else
    echo "  ⚠️  git-secrets not installed - skipping secret scan"
fi

# 3. Build and Performance Gates
check_step "Running build validation..."

echo "  • Production build..."
npm run build > /dev/null 2>&1 || fail_step "Production build failed - fix build errors"
pass_step "Production build successful"

echo "  • Bundle size analysis..."
if [ -f "dist/bundle-stats.json" ]; then
    BUNDLE_SIZE=$(node -e "console.log(Math.round(require('./dist/bundle-stats.json').assets.reduce((a,b) => a + b.size, 0) / 1024))")
    if [ "$BUNDLE_SIZE" -gt 1000 ]; then  # 1MB threshold
        echo "  ⚠️  Bundle size: ${BUNDLE_SIZE}KB (consider optimization)"
    else
        pass_step "Bundle size: ${BUNDLE_SIZE}KB"
    fi
fi

# 4. Integration Tests
check_step "Running integration tests..."

echo "  • Starting local services..."
docker-compose -f docker-compose.local.yml up -d > /dev/null 2>&1
sleep 5  # Wait for services to start

echo "  • Integration tests..."
npm run test:integration > /dev/null 2>&1 || fail_step "Integration tests failing - fix before deployment"
pass_step "Integration tests passed"

echo "  • Stopping local services..."
docker-compose -f docker-compose.local.yml down > /dev/null 2>&1

# 5. Documentation Gates
check_step "Validating documentation..."

if [ ! -f "README.md" ]; then
    fail_step "README.md missing"
fi

if [ ! -f "docs/context/PRD.md" ] && [ ! -f "docs/context/10-prePRD-brief.md" ]; then
    fail_step "No PRD or Pre-PRD documentation found"
fi

pass_step "Documentation validated"

# 6. Environment Configuration
check_step "Checking environment configuration..."

if [ ! -f ".env.example" ]; then
    fail_step ".env.example missing - create template for deployments"
fi

if grep -q "your_.*_here" .env.example; then
    pass_step "Environment template properly configured"
else
    echo "  ⚠️  Verify .env.example has placeholder values"
fi

# Final Summary
echo ""
echo "================================================"
echo -e "${GREEN}🚀 ALL CHECKS PASSED - READY FOR DEPLOYMENT!${NC}"
echo ""
echo "Deployment recommendations:"
echo "  1. Deploy to staging first: npm run deploy:staging"
echo "  2. Run staging tests: npm run test:staging"  
echo "  3. Manual QA on staging environment"
echo "  4. Deploy to production: npm run deploy:prod"
echo ""
echo "Cost-saving reminder:"
echo "  • Only deploy when features are complete"
echo "  • Use staging for final validation"
echo "  • Monitor deployment costs and frequency"