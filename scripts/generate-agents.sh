#!/bin/bash

# Generate remaining agent templates
agents=(
  "business-marketing/business-analyst:Business Analyst Agent:Analyzes business requirements and translates them into technical specifications"
  "business-marketing/content-marketer:Content Marketer Agent:Creates and manages content marketing strategies and campaigns"
  "business-marketing/customer-support:Customer Support Agent:Handles customer inquiries and support ticket management"
  "business-marketing/product-strategist:Product Strategist Agent:Defines product vision, roadmap, and go-to-market strategies"
  "data-ai/data-scientist:Data Scientist Agent:Analyzes data, builds ML models, and provides data-driven insights"
  "database/database-admin:Database Admin Agent:Manages database operations, backups, and performance monitoring"
  "database/database-architect:Database Architect Agent:Designs database schemas and data architecture strategies"
  "database/database-optimizer:Database Optimizer Agent:Optimizes database performance and query efficiency"
  "deep-research-team/competitive-intelligence-analyst:Competitive Intelligence Analyst Agent:Researches competitors and market trends"
  "development-tools/debugger:Debugger Agent:Automated debugging and error analysis"
  "development-team/devops-engineer:DevOps Engineer Agent:Manages CI/CD pipelines and infrastructure automation"
  "development-team/frontend-developer:Frontend Developer Agent:Develops user interfaces and client-side applications"
  "development-team/ios-developer:iOS Developer Agent:Develops iOS applications and mobile experiences"
  "development-team/mobile-developer:Mobile Developer Agent:Develops cross-platform mobile applications"
  "development-team/ui-ux-designer:UI/UX Designer Agent:Designs user interfaces and user experiences"
  "performance-testing/react-performance-optimization:React Performance Optimization Agent:Optimizes React application performance"
  "podcast-creator-team/market-research-analyst:Market Research Analyst Agent:Conducts market research and analysis"
  "podcast-creator-team/social-media-copywriter:Social Media Copywriter Agent:Creates social media content and copy"
  "security/security-auditor:Security Auditor Agent:Conducts security audits and compliance assessments"
)

for agent in "${agents[@]}"; do
  IFS=':' read -r path title description <<< "$agent"
  
  mkdir -p "docs/agents/$(dirname "$path")"
  
  cat > "docs/agents/${path}.md" << EOF
# $title

**Role:** $description

**Key Responsibilities:**
- [Responsibility 1]
- [Responsibility 2] 
- [Responsibility 3]
- [Responsibility 4]

**Tools & Integrations:**
- [Tool 1]
- [Tool 2]
- [Tool 3]
- [Tool 4]

**Success Metrics:**
- [Metric 1]
- [Metric 2]
- [Metric 3]
- [Metric 4]
EOF
  
  echo "Created docs/agents/${path}.md"
done

echo "All agent templates generated successfully!"