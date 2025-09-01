# 🎠 Carousel Engine v2 - Production Documentation

## Overview

**Carousel Engine v2** is an advanced AI-powered content generation system that creates personalized Facebook carousel content based on client-specific business profiles. Built with RFC-004 specifications, it combines document intelligence, AI content generation, and workflow automation to deliver highly targeted marketing content.

## 🎯 Core Purpose

Transform raw business content into engaging, personalized carousel posts by:
1. **Learning from client documents** (Business Profile, ICP, Voice Guide)
2. **Generating AI-powered content** using GPT-4o with client-specific context
3. **Creating visual assets** with unique background imagery
4. **Managing workflow** through Notion database integration
5. **Delivering assets** via Google Drive organization

## 🏗️ System Architecture

### Two-Part Workflow System

#### **Part 1: Client Profile Uploader**
- **Purpose**: Onboard new clients with document-based personalization
- **Endpoint**: `/api/documents/upload`
- **Process**: Document → AI Analysis → System Message → Database Storage

#### **Part 2: Carousel Content Engine**
- **Purpose**: Generate personalized carousel content on demand
- **Endpoint**: `/api/carousel/generate`
- **Process**: Content Request → Client Context → AI Generation → Asset Creation

---

## 📋 Detailed Functionality

### 🔄 **Part 1: Client Profile Uploader (`/api/documents/upload`)**

**Purpose**: Create personalized AI system messages from client business documents.

#### **Required Documents (3 files)**:
1. **Client Profile** - Business overview, services, target market
2. **Ideal Client Profile (ICP)** - Target audience demographics and psychographics
3. **Voice & Style Guide** - Brand voice, tone, messaging preferences

#### **Process Flow**:
```
Upload Documents → Extract Content → AI Analysis → System Message (88,927+ chars) → Store in Database
```

#### **Technical Implementation**:
- **Web Interface**: Drag-and-drop document upload with real-time validation
- **File Processing**: Multi-format support (PDF, DOCX, TXT, MD) with content extraction
- **AI Analysis**: GPT-4o processes documents to create comprehensive system message
- **Storage**: Google Drive organization + Notion Client Project Database updates
- **Validation**: No duplicate records - updates existing projects only

#### **Output**:
- **System Message**: Detailed client context (up to 88,927+ characters)
- **Database Record**: Updated Client Project Database with personalized context
- **File Storage**: Organized Google Drive folders with source documents

---

### 🎨 **Part 2: Carousel Content Engine (`/api/carousel/generate`)**

**Purpose**: Generate personalized carousel content using client-specific context.

#### **Input Requirements**:
- **Notion Page ID**: Content record marked with Format = "Carousel"
- **Client Context**: System message from Part 1 (retrieved automatically)
- **Content Base**: Title and content from Notion record

#### **Process Flow**:
```
Notion Trigger → Retrieve Client Context → GPT-4o Generation → Image Creation → Asset Delivery → Database Updates
```

#### **AI Content Generation**:
- **Model**: GPT-4o (enhanced reasoning and creativity)
- **Context**: Full client system message for personalization
- **Output**: 4-7 connected carousel slides with cohesive storytelling
- **Style**: Client-specific voice, tone, and messaging preferences

#### **Visual Asset Creation**:
- **Background Images**: Unique AI-generated imagery for each carousel theme
- **Content Optimization**: Client-specific messaging and style adaptation
- **Format**: Ready-to-use carousel slides optimized for Facebook

#### **Workflow Integration**:
- **Trigger**: Notion record Format = "Carousel"
- **Processing**: Automated content generation with client personalization
- **Completion**: Format = "Complete", Status = "Review"
- **Delivery**: Google Drive upload with organized file structure

---

## 🔗 **Webhook Integration Requirements**

### **Webhook #1: Document Upload Trigger**
```
Purpose: Client Onboarding
URL: https://your-app.vercel.app/api/documents/upload
Method: GET (interface) / POST (processing)
Trigger: Manual upload via web interface
Use Case: New client setup, system message creation
```

### **Webhook #2: Carousel Generation Trigger**
```
Purpose: Automated Content Generation  
URL: https://your-app.vercel.app/api/carousel/generate
Method: POST
Trigger: Notion database change (Format = "Carousel")
Use Case: On-demand carousel creation with client personalization

Required Payload:
{
  "notion_page_id": "12345678-1234-1234-1234-123456789012"
}
```

---

## 🎯 **Key Features & Benefits**

### **Client-Specific Personalization**
- **Context-Aware**: Every carousel reflects client's business profile, ICP, and voice
- **Dynamic Adaptation**: Content style automatically adjusts to client preferences
- **Consistency**: Maintains brand voice across all generated content

### **Advanced AI Integration**
- **GPT-4o**: Latest OpenAI model for superior content quality and reasoning
- **Large Context Windows**: Processes up to 88,927+ character system messages
- **Content Optimization**: Ensures engaging, conversion-focused messaging

### **Automated Workflow**
- **Notion Integration**: Seamless database management and status tracking
- **Google Drive**: Organized file storage with automatic folder creation
- **Error Handling**: Comprehensive logging and graceful failure management

### **Production-Ready Architecture**
- **Serverless Deployment**: Vercel-optimized for scalability and cost efficiency
- **Security**: Environment variable protection, no hardcoded credentials
- **Monitoring**: Structured logging with Sentry integration support

---

## 📊 **Performance Specifications**

### **Processing Metrics**:
- **Document Upload**: 10-30 seconds for 3-document processing
- **Carousel Generation**: 30-80 seconds per carousel set
- **Cost per Generation**: ~$0.65 (OpenAI API costs)
- **Output Volume**: 4-7 connected slides per carousel

### **Technical Limits**:
- **Max File Size**: 50MB per document
- **Supported Formats**: PDF, DOCX, TXT, MD
- **Max Cost per Run**: $10.00 (configurable)
- **Function Timeout**: 300 seconds (5 minutes)

---

## 🚀 **Deployment & Configuration**

### **Environment Variables**:
```bash
# Core API Integration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_content_database_id
CLIENT_PROJECT_DATABASE_ID=your_client_database_id
OPENAI_API_KEY=sk-your_openai_api_key

# Google Drive Integration
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_secret
TARGET_GOOGLE_DRIVE_FOLDER_ID=your_target_folder_id

# Configuration
MAX_COST_PER_RUN=10.0
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=pdf,docx,txt,md
```

### **Notion Database Setup**:

#### **Content Engine Database** (Primary):
- **Format**: Text field (values: "Carousel", "Complete")
- **Status**: Status field (values: "Review", "Published", etc.)
- **Project**: Relation to Client Project Database
- **Title**: Text field for carousel topic
- **Content**: Rich text for base content

#### **Client Project Database** (Secondary):
- **Name**: Text field (client project name)
- **Client_Project_Name**: Text field (matching field)
- **System_Message**: Rich text (AI-generated context)
- **Documents_Uploaded**: Checkbox (upload status)

---

## 🔧 **API Endpoints**

### **Production Endpoints**:

#### **Health Check**
```
GET /health
Response: {"status": "healthy", "version": "2.0"}
```

#### **Document Upload Interface**
```
GET /api/documents/upload
Returns: HTML upload interface
```

#### **Document Processing**
```
POST /api/documents/upload
Content-Type: multipart/form-data
Required: 3 files (Client Profile, ICP, Voice Guide)
Response: Processing status and system message details
```

#### **Carousel Generation**
```
POST /api/carousel/generate
Content-Type: application/json
Body: {"notion_page_id": "page-id"}
Response: Generation status and asset details
```

#### **API Documentation**
```
GET /docs
Returns: Interactive FastAPI documentation
```

---

## 🎯 **Use Cases & Workflow**

### **Typical Client Onboarding**:
1. **Setup**: Create client project record in Notion Client Project Database
2. **Upload**: Visit `/api/documents/upload`, upload 3 required documents
3. **Processing**: System extracts content, generates AI system message
4. **Ready**: Client project now has personalized context for carousel generation

### **Typical Content Generation**:
1. **Content Creation**: Create record in Content Engine Database
2. **Trigger Setup**: Set Format = "Carousel", link to client Project
3. **Webhook Trigger**: System automatically generates personalized carousel
4. **Review**: Format updates to "Complete", Status = "Review"
5. **Assets**: Carousel slides available in Google Drive with unique imagery

---

## 🏆 **RFC-004 Compliance**

This implementation fully satisfies RFC-004 requirements:

- ✅ **Client-Specific Content Generation**: Personalized system messages
- ✅ **Document-Based Intelligence**: 3-document upload and analysis
- ✅ **AI-Powered Personalization**: GPT-4o with client context
- ✅ **Workflow Integration**: Notion database automation
- ✅ **Asset Management**: Google Drive organization
- ✅ **Production Deployment**: Vercel serverless architecture

---

## 📈 **Business Impact**

### **For Agencies**:
- **Scalability**: Handle multiple clients with personalized content
- **Efficiency**: Automated workflow reduces manual content creation time
- **Quality**: AI-generated content maintains client voice and brand consistency
- **Organization**: Centralized asset management and status tracking

### **For Clients**:
- **Personalization**: Content reflects their specific business profile and voice
- **Relevance**: Carousel messaging targets their ideal client profile
- **Consistency**: All content maintains their brand guidelines
- **Performance**: Optimized for engagement and conversion

---

## 🔒 **Security & Compliance**

- **Environment Variables**: All sensitive data protected via Vercel environment variables
- **OAuth Integration**: Secure Google Drive access via OAuth 2.0
- **API Key Management**: Rotatable keys for all third-party integrations
- **Error Handling**: Graceful failure management with detailed logging
- **Data Protection**: No hardcoded credentials or exposed secrets

---

**Carousel Engine v2** represents the cutting edge of AI-powered content personalization, delivering scalable, client-specific marketing automation that drives engagement and conversion through intelligent workflow integration.

---

*Built by Impact931 - Powered by RFC-004 Specifications*