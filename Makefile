init:
	npm install
	cp .env.example .env 2>/dev/null || echo ".env already exists"
	@echo "✅ Project initialized"
	@echo "📝 Edit .env with your local configuration"

dev:
	docker-compose -f docker-compose.local.yml up -d
	@echo "🚀 Local services started"
	@echo "   - PostgreSQL: localhost:5432"
	@echo "   - Redis: localhost:6379"  
	@echo "   - MinIO: localhost:9000 (admin: minioadmin/minioadmin123)"
	@echo "   - MailHog: localhost:8025"
	npm run dev

check:
	npm run lint && npm run typecheck && npm run test

check-coverage:
	npm run test:coverage

sec:
	npm audit || true

deploy-ready:
	@echo "🔍 Running complete deployment readiness check..."
	./scripts/pre-deploy-check.sh

services-up:
	docker-compose -f docker-compose.local.yml up -d
	@echo "🐳 Local services started"

services-down:
	docker-compose -f docker-compose.local.yml down
	@echo "🛑 Local services stopped"

services-clean:
	docker-compose -f docker-compose.local.yml down -v
	docker system prune -f
	@echo "🧹 Local services cleaned"

plan:
	@echo "Run orchestrator plan step in Claude Code"

.PHONY: init dev check check-coverage sec deploy-ready services-up services-down services-clean plan