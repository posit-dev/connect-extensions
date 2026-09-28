# DAG Builder

A visual DAG (Directed Acyclic Graph) builder and builder for Posit Connect content, built with FastAPI and React. This application allows you to create, visualize, and execute workflows that combine Posit Connect content with custom action nodes.

## Features

- **Visual DAG Builder**: Drag-and-drop interface for creating content workflows
- **Posit Connect Integration**: Search and add content from your Posit Connect server
- **Custom Action Nodes**: Add webhooks, delays, and conditional logic to your workflows
- **Background Publishing**: Publish DAGs to Posit Connect as Quarto documents with parallel execution
- **Historical Tracking**: Download and re-publish previous DAG versions
- **Real-time Validation**: Automatic cycle detection and connectivity validation

## Directory Structure

- **`py/`** - Python FastAPI backend application
  - `app.py` - Main FastAPI server with WebSocket endpoint and REST API routes
  - `dag_storage.py` - DAG persistence and artifact management
  - `dag_validation.py` - DAG validation and topological sorting
  - `connect_client.py` - Posit Connect API client
  - `quarto_generator.py` - Quarto document generation
  - `api_handlers.py` - REST API endpoint handlers
- **`srcts/`** - TypeScript/React frontend source code
  - `main.tsx` - Entry point that renders the React app
  - `DAGBuilder.tsx` - Main DAG builder component with ReactFlow
  - `hooks/useWebSocket.tsx` - WebSocket hook for backend communication
  - `styles.css` - Application styling and custom node styles
- **`artifacts/`** - Published DAG artifacts and metadata (generated)
- **`py/www/`** - Built JavaScript/CSS output (generated)
- **`node_modules/`** - npm dependencies (generated)

## Prerequisites

### Posit Connect Integration

This application integrates with Posit Connect to search for content and deploy DAGs. You'll need:

1. **Posit Connect Server**: Access to a Posit Connect server
2. **API Access**: Valid API credentials for your Posit Connect server

### Setting Up Posit Connect Access

#### 1. Create an API Key

1. Log into your Posit Connect server
2. Navigate to your user profile (click your name in top-right corner)
3. Go to **"API Keys"** section
4. Click **"Create API Key"**
5. Give it a descriptive name (e.g., "DAG Builder")
6. Copy the generated API key (you won't see it again!)

#### 2. Configure Environment Variables

Create a `.env` file in the project root with your Posit Connect credentials:

```bash
# .env file
CONNECT_SERVER_URL=https://your-connect-server.com
CONNECT_API_KEY=your-api-key-here
ENVIRONMENT=development
```

**Important Security Notes:**
- Never commit your `.env` file to version control (it's already in `.gitignore`)
- Use environment-specific API keys (separate keys for dev/staging/production)
- Rotate API keys regularly according to your organization's security policy

#### 3. Install rsconnect-python (Required for Publishing)

The DAG Builder uses `rsconnect-python` to deploy generated Quarto documents to Posit Connect:

```bash
# Install rsconnect-python
pip install rsconnect-python

# Configure rsconnect with your server (one-time setup)
rsconnect add \
  --account your-account-name \
  --name your-server-name \
  --server https://your-connect-server.com \
  --key your-api-key-here
```

## Getting Started

```bash
# Install npm dependencies
npm install

# Install Python dependencies
pip install -r py/requirements.txt

# Start development with hot-reload (recommended)
npm run dev
```

The `npm run dev` command will automatically:
- Build the TypeScript/React frontend with CSS processing
- Start the FastAPI server with hot-reload enabled
- Open your browser to http://localhost:8000
- Watch for changes and rebuild/restart as needed

## Available npm Scripts

This application includes several npm scripts for different development and build workflows:

### Development Scripts (Recommended)

- **`npm run dev`** - 🚀 **Primary development command** - Builds frontend and starts FastAPI server automatically with hot-reload
- **`npm run watch`** - 👀 **Frontend-only watching** - Watch TypeScript/React files for changes and rebuild automatically
- **`npm run fastapi`** - 🖥️ **Backend-only server** - Start only the FastAPI server

### Build Scripts

- **`npm run build`** - 🔨 **Development build** - Build frontend once with TypeScript checking and CSS processing
- **`npm run clean`** - 🧹 **Clean build** - Remove all generated build files

### Port Configuration

You can customize the port (default is 8000):

```bash
# Use custom port
PORT=3000 npm run dev
PORT=3000 npm run fastapi
```

## Manual Development Setup

If you prefer more control, you can run the frontend and backend separately:

### 1. Start Build Watcher (in one terminal)

```bash
npm run watch
```

This watches TypeScript/React files for changes and rebuilds automatically.

### 2. Run FastAPI Server (in another terminal)

```bash
cd py
uvicorn app:app --reload --port 8000
```

### 3. View Your App

Open your browser and navigate to `http://localhost:8000`.

## Production Deployment

For production builds:

```bash
# Create optimized production build
npm run build

# Run FastAPI with production settings
cd py
uvicorn app:app --host 0.0.0.0 --port 8000
```
