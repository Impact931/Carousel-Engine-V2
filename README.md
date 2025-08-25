# Impact931 Multi-Agent Project Template

A turnkey project template for Impact931's multi-agent development workflow. This repository provides a standardized foundation for new projects, complete with AI agents, MCP tools, and governance templates.

## 🚀 Quick Start

### 1. Clone and Initialize
```bash
git clone https://github.com/Impact931/impact931-multiagent-template.git your-project-name
cd your-project-name
make init
```

### 2. Local Development Setup
```bash
# Edit .env with your local configuration
nano .env

# Start local development environment
make dev
```
This starts:
- PostgreSQL database (localhost:5432)
- Redis cache (localhost:6379)
- MinIO S3 storage (localhost:9000)
- MailHog SMTP testing (localhost:8025)
- Your application with hot reload

### 3. Configure Your Project
1. Update `docs/context/10-prePRD-brief.md` with your project details
2. Customize agent roster for your project needs
3. Review `docs/LOCAL_DEVELOPMENT.md` for detailed local development guidelines

### 4. Run Pre-PRD Orchestration
```bash
# Open Claude Code and load the orchestration prompt
open .claude/prompts/orchestrate-prePRD.md
```

### 5. Ready for Deployment?
```bash
# Run complete readiness check before any deployment
make deploy-ready
```
Only deploy when ALL checks pass locally!

## 📁 Project Structure

```
impact931-multiagent-template/
├── .claude/
│   ├── claude.json              # MCP server configuration
│   └── prompts/
│       └── orchestrate-prePRD.md # Pre-PRD orchestration prompt
├── docs/
│   ├── agents/                  # AI agent profiles by category
│   │   ├── business-marketing/
│   │   ├── development-team/
│   │   ├── security/
│   │   └── ...
│   └── context/                 # Project documentation
│       ├── 10-prePRD-brief.md   # Pre-PRD project brief
│       ├── RFC.template.md      # RFC template
│       ├── ADR.template.md      # Architecture Decision Record template
│       └── PRD.placeholder.md   # Full PRD goes here
├── src/                         # Source code
├── Makefile                     # Common development tasks
└── package.json                 # Node.js dependencies and scripts
```

## 🤖 Available Agents

### Business & Marketing
- **Sales Automator**: Email campaigns, lead qualification, CRM automation
- **Business Analyst**: Requirements analysis, stakeholder management
- **Content Marketer**: Content strategy, copywriting, campaign management
- **Customer Support**: Support workflows, ticket management
- **Product Strategist**: Product roadmaps, go-to-market strategies

### Development Team
- **Backend Architect**: API design, system architecture, scalability
- **Frontend Developer**: UI/UX implementation, client-side development
- **DevOps Engineer**: CI/CD, infrastructure automation, deployment
- **Mobile Developer**: Cross-platform mobile applications
- **iOS Developer**: Native iOS applications
- **UI/UX Designer**: User interface and experience design

### Security
- **API Security Audit**: Vulnerability assessments, penetration testing
- **Security Auditor**: Security compliance, audit procedures

### Development Tools
- **Code Reviewer**: Automated code review, quality assurance
- **Context Manager**: Documentation, knowledge management
- **Debugger**: Error analysis, debugging automation

### Data & AI
- **Data Scientist**: Analytics, ML models, data-driven insights

### Database
- **Database Admin**: Database operations, monitoring, backups
- **Database Architect**: Schema design, data architecture
- **Database Optimizer**: Performance tuning, query optimization

### Research & Analysis
- **Competitive Intelligence Analyst**: Market research, competitor analysis
- **Market Research Analyst**: Market trends, customer insights

### Performance & Testing
- **React Performance Optimization**: Frontend performance tuning

### Content Creation
- **Social Media Copywriter**: Social content, copywriting

## 🔧 MCP Tools Integration

This template comes pre-configured with essential MCP servers:

### Context7 MCP
- **Purpose**: Context management and knowledge organization
- **Setup**: Set `CONTEXT7_API_KEY` environment variable
- **Usage**: Maintains project context across team interactions

### Sequential Thinking MCP
- **Purpose**: Structured reasoning and decision-making
- **Setup**: Auto-configured, no API key required
- **Usage**: Guides systematic problem-solving approaches

### Puppeteer MCP
- **Purpose**: Web automation and testing
- **Setup**: Auto-configured with production settings
- **Usage**: Automated browser testing, web scraping, UI testing

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:
```bash
# Context7 MCP (if using)
CONTEXT7_API_KEY=your_context7_api_key_here

# Add other project-specific environment variables
DATABASE_URL=your_database_url
API_KEY=your_api_key
```

### Claude Desktop Integration
The template includes `.claude/claude.json` for Claude Desktop integration. MCP servers will be automatically available when opening this project in Claude Code.

## 📋 Development Workflow

### 🏠 Local-First Development
**Build locally, deploy when ready.** See `docs/LOCAL_DEVELOPMENT.md` for complete guidelines.

### 1. Project Initialization
```bash
make init          # Install dependencies, copy .env template
make dev           # Start local development stack
```

### 2. Feature Development (Local)
```bash
# Create feature branch
git checkout -b feature/your-feature

# Develop with local services
make dev           # Starts databases, cache, app with hot reload

# Continuous testing
make check         # Linting, type checking, unit tests
make check-coverage # Test coverage reports
```

### 3. Pre-PRD Process
1. Complete `docs/context/10-prePRD-brief.md`
2. Run orchestration prompt in Claude Code
3. Review generated RFC-000 and ADR-000
4. Ensure 85%+ readiness score

### 4. Deployment Readiness
```bash
# Complete validation before deployment
make deploy-ready  # Runs comprehensive checks

# Only deploy when ALL checks pass:
# ✅ Code quality (linting, types, tests, coverage)
# ✅ Security (audit, secret scanning)  
# ✅ Build validation (production build success)
# ✅ Integration tests (with local services)
# ✅ Documentation validation
```

### 5. Cost-Saving Deployment Strategy
- **Develop locally**: Use `make dev` for rapid iteration
- **Test locally**: Full test suite with local services
- **Deploy weekly+**: Only when features are complete and tested
- **Staging first**: Validate on staging before production

### 6. Development Standards
- **Linting**: ESLint with strict configuration
- **Type Checking**: TypeScript with strict mode
- **Testing**: Vitest with >80% coverage requirement
- **Security**: Automated audits and secret scanning
- **Local Services**: Docker Compose for databases and dependencies

### 7. Documentation Standards
- **RFCs**: Use `docs/context/RFC.template.md` for proposals
- **ADRs**: Use `docs/context/ADR.template.md` for architectural decisions
- **Local Dev**: `docs/LOCAL_DEVELOPMENT.md` for setup and workflow
- **Agents**: Update agent profiles as capabilities evolve

## 🎯 Usage Patterns

### Starting a New Project
1. Clone this template repository
2. Update project metadata in `package.json`
3. Customize the Pre-PRD brief with your project details
4. Run the orchestration process to validate team readiness
5. Begin development once DoR criteria are met

### Agent Utilization
- Use agents **proactively** based on their descriptions
- Reference agent profiles in `docs/agents/` for capabilities
- Combine agents for complex, multi-faceted tasks
- Update agent profiles as project requirements evolve

### Governance and Decision Making
- Create RFCs for significant technical or business decisions
- Document architectural decisions with ADRs
- Use the orchestrator for complex multi-agent coordination
- Maintain context through Context7 MCP integration

## 🔍 Quality Assurance

### Automated Checks
- Code quality via ESLint
- Type safety via TypeScript
- Security scanning via npm audit
- Test coverage via Vitest

### Manual Review Process
- Code reviews required for all changes
- Architecture decisions documented in ADRs
- Regular security audits for sensitive projects
- Performance monitoring for user-facing applications

## 📈 Success Metrics

Track project health through:
- Code quality scores (linting, type coverage)
- Security audit results (vulnerability count)
- Test coverage percentages
- Agent utilization rates
- Time to market metrics

## 🤝 Contributing

### Adding New Agents
1. Create agent profile in appropriate category under `docs/agents/`
2. Follow the standard agent template format
3. Update this README with agent description
4. Test agent integration with existing workflow

### Improving Templates
1. Update templates in `docs/context/`
2. Validate changes against existing projects
3. Update documentation and examples
4. Ensure backward compatibility

## 📚 Additional Resources

- [Impact931 Development Standards](internal-link)
- [MCP Server Documentation](https://modelcontextprotocol.io/)
- [Claude Code User Guide](https://claude.ai/code)

## 📄 License

MIT License - see LICENSE file for details.

---

**Impact931** - Building the future, one agent at a time.