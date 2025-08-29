# Carousel Engine v2 - Production Deployment Guide

## 🚀 Quick Deploy to Vercel

### 1. Prerequisites
- GitHub account with this repository
- Vercel account connected to GitHub
- Environment variables ready (see below)

### 2. Deploy to Vercel

Click the deploy button:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/carousel-engine-v2)

Or manually:

```bash
npm i -g vercel
vercel --prod
```

### 3. Configure Environment Variables

In Vercel Dashboard > Settings > Environment Variables, add:

```bash
# Notion Integration
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=23ec2a32df0d80a4831adc78bc6909ca
CLIENT_PROJECT_DATABASE_ID=231c2a32df0d8174a3f9fcdf5be1a0d8

# OpenAI Integration
OPENAI_API_KEY=sk-your_openai_api_key

# Google Drive Integration (Base64 encoded service account JSON)
GOOGLE_APPLICATION_CREDENTIALS_JSON=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50...
TARGET_GOOGLE_DRIVE_FOLDER_ID=1abcd1234567890

# Configuration
MAX_COST_PER_RUN=10.0
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=pdf,docx,txt,md
```

### 4. Set up Webhooks

After deployment, configure Notion webhooks:

#### Part 1: Document Upload Webhook
- **URL**: `https://your-app.vercel.app/documents/upload`
- **Method**: POST
- **Trigger**: Manual upload via web interface

#### Part 2: Carousel Generation Webhook
- **URL**: `https://your-app.vercel.app/carousel/generate`  
- **Method**: POST
- **Trigger**: Notion database change (Format = "Carousel")

### 5. Test the Deployment

1. **Health Check**: Visit `https://your-app.vercel.app/health`
2. **API Docs**: Visit `https://your-app.vercel.app/docs`
3. **Upload Interface**: Visit `https://your-app.vercel.app/documents/upload`

## 🔧 Environment Variables Setup

### Notion API Key
1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create new integration
3. Copy the "Internal Integration Token"
4. Share your databases with the integration

### OpenAI API Key  
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create new secret key
3. Copy the key (starts with `sk-`)

### Google Drive Setup
1. Create service account in [Google Cloud Console](https://console.cloud.google.com)
2. Enable Google Drive API
3. Create and download service account JSON
4. Base64 encode the JSON: `base64 -i service-account.json`
5. Share target folder with service account email

### Database IDs
- Get from Notion database URLs
- Format: `https://notion.so/database-id?v=view-id`

## 🎯 Production Endpoints

Once deployed, your app will have these endpoints:

- **📤 Document Upload**: `/documents/upload` (GET for interface, POST for processing)
- **🎨 Carousel Generation**: `/carousel/generate` (POST)
- **❤️ Health Check**: `/health` (GET)
- **📚 API Documentation**: `/docs` (GET)
- **📊 OpenAPI Spec**: `/openapi.json` (GET)

## 🔄 Workflow Integration

### Document Upload Process:
1. User visits `/documents/upload` 
2. Uploads 3 client documents (Profile, ICP, Voice Guide)
3. System processes documents and creates personalized system message
4. Updates Client Project Database
5. Ready for carousel generation

### Carousel Generation Process:
1. Set Notion record Format = "Carousel"
2. Webhook triggers `/carousel/generate`
3. System retrieves client system message
4. GPT-4o generates 4-7 connected slides
5. Creates unique background image
6. Uploads to Google Drive
7. Updates Notion: Format = "Complete", Status = "Review"

## 🚨 Troubleshooting

### Common Issues:

1. **500 Error on startup**
   - Check environment variables are set
   - Verify Google Drive JSON is valid base64
   - Check Notion database permissions

2. **Webhook timeouts**
   - Increase Vercel function timeout (max 5 minutes)
   - Check OpenAI API limits
   - Verify Google Drive permissions

3. **Content not generating**
   - Check Notion page has content in title or blocks
   - Verify Project field relations are set
   - Check Client Project Database has system message

### Logs and Monitoring:
- View logs in Vercel Dashboard
- Check function execution time
- Monitor API usage costs

## 🔒 Security Considerations

- Never commit API keys or credentials
- Use environment variables for all secrets
- Validate file uploads (size, type)
- Monitor API usage and costs
- Regular security updates

## 📈 Performance Optimization

- **Function timeout**: Set to 300s for carousel generation
- **Memory**: Use 1024MB for image processing
- **Caching**: Enable for static assets
- **Monitoring**: Set up alerts for errors and timeouts

Ready for production! 🎉