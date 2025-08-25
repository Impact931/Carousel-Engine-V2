# Local Development Guidelines

## 🏠 Local-First Development Philosophy

**Build locally, deploy when ready.** This approach minimizes costs and prevents premature deployments while iterating on features.

## 🚀 Local Development Setup

### Prerequisites
```bash
# Install Node.js 18+ 
node --version  # Should be 18+
npm --version   # Should be 9+

# Install Docker (for database/services)
docker --version
docker-compose --version
```

### Initial Setup
```bash
# Clone and initialize
git clone <your-project> && cd <your-project>
make init

# Copy environment template
cp .env.example .env
# Edit .env with your local configuration
```

### Local Services Stack
```bash
# Start local development stack
docker-compose up -d  # Starts databases, redis, etc.

# Run application locally
npm run dev           # Starts dev server with hot reload

# Run tests locally
npm run test:watch    # Continuous testing
npm run test:coverage # Coverage reports
```

## 🔄 Local Development Workflow

### 1. Feature Development
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Run local development stack
npm run dev

# Make changes and test locally
npm run test
npm run lint
npm run typecheck
```

### 2. Local Quality Gates
Before any commit, ensure these pass locally:
```bash
make check  # Runs all quality checks
# - ESLint (code quality)
# - TypeScript (type checking)  
# - Vitest (unit tests)
# - Security audit
```

### 3. Local Integration Testing
```bash
# Run full integration test suite
npm run test:integration

# Test with production-like data
npm run test:e2e:local

# Performance testing
npm run test:perf:local
```

## 🛡️ Cost-Saving Strategies

### Local Database Development
```yaml
# docker-compose.local.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: your_app_dev
      POSTGRES_USER: dev_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### Local API Testing
```bash
# Mock external APIs locally
npm run mock-apis     # Starts mock server

# Local API testing
npm run test:api:local

# Load testing locally
npm run load-test:local
```

### Local Build Validation
```bash
# Test production build locally
npm run build
npm run preview       # Preview production build

# Validate bundle size
npm run analyze       # Bundle analyzer

# Check for production issues
npm run audit:prod
```

## 🚦 Ready-for-Deployment Checklist

Only push to remote/deploy when ALL these pass locally:

### Code Quality Gates
- [ ] `npm run lint` - No linting errors
- [ ] `npm run typecheck` - No TypeScript errors  
- [ ] `npm run test` - All tests passing
- [ ] `npm run test:coverage` - Coverage > 80%

### Performance Gates  
- [ ] `npm run build` - Successful production build
- [ ] Bundle size < target threshold
- [ ] Lighthouse score > 90 (if applicable)
- [ ] Core Web Vitals within limits

### Security Gates
- [ ] `npm audit` - No high/critical vulnerabilities
- [ ] No secrets in code (use git-secrets)
- [ ] Environment variables properly configured
- [ ] API security validated

### Documentation Gates
- [ ] README updated for new features
- [ ] API documentation current
- [ ] Architecture decisions documented (ADRs)
- [ ] Agent profiles updated if modified

## 🔧 Local Environment Configuration

### Development Environment Variables
```bash
# .env.local
NODE_ENV=development

# Database
DATABASE_URL=postgresql://dev_user:dev_password@localhost:5432/your_app_dev

# Local API endpoints
API_BASE_URL=http://localhost:3001

# Feature flags for local development
ENABLE_DEBUG=true
SKIP_AUTH=true
MOCK_EXTERNAL_APIS=true

# Local service endpoints
REDIS_URL=redis://localhost:6379
```

### Local Testing Configuration
```bash
# .env.test
NODE_ENV=test
DATABASE_URL=postgresql://test_user:test_password@localhost:5433/your_app_test
DISABLE_LOGGING=true
ENABLE_TEST_HELPERS=true
```

## 📊 Local Monitoring and Debugging

### Development Debugging
```bash
# Debug mode with detailed logging
DEBUG=* npm run dev

# Database debugging
npm run db:debug

# API request debugging  
npm run debug:api
```

### Local Performance Monitoring
```bash
# Profile application locally
npm run profile

# Memory leak detection
npm run test:memory

# Performance benchmarks
npm run benchmark:local
```

## 🎯 Deployment Readiness Validation

### Pre-Deployment Checklist
Run this complete validation before any deployment:

```bash
#!/bin/bash
# scripts/pre-deploy-check.sh

echo "🏁 Running complete deployment readiness check..."

# Quality gates
npm run lint || exit 1
npm run typecheck || exit 1  
npm run test || exit 1
npm run test:integration || exit 1

# Security checks
npm audit --audit-level high || exit 1
npm run security-scan || exit 1

# Performance validation
npm run build || exit 1
npm run test:e2e:local || exit 1

# Documentation checks
npm run docs:validate || exit 1

echo "✅ All checks passed - ready for deployment!"
```

### Staging Environment
Only after local validation passes:
```bash
# Deploy to staging environment
npm run deploy:staging

# Run staging integration tests
npm run test:staging

# Manual QA on staging
# Performance testing on staging
# Security testing on staging

# Then deploy to production
npm run deploy:prod
```

## 💡 Best Practices

### 1. Local Data Management
- Use realistic but anonymized local data
- Seed local database with representative data
- Keep local data separate from production

### 2. Local Performance Testing  
- Test with production-like data volumes
- Simulate network latency locally
- Profile memory usage during development

### 3. Local Security Testing
- Run security scans locally before commit
- Test authentication/authorization locally
- Validate input sanitization locally

### 4. Cost Monitoring
- Track deployment frequency (aim for weekly+)
- Monitor CI/CD usage and costs
- Use local development for rapid iteration

This local-first approach ensures:
- 🔥 Faster iteration cycles
- 💰 Reduced cloud costs  
- 🐛 Fewer production issues
- 🚀 More confident deployments
- ⚡ Better developer experience