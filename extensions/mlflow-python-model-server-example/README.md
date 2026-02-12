# MLflow Model API Server for Posit Connect

Deploy your MLflow models to Posit Connect as a REST API with automatic documentation and multiple input format support.

## Overview

This example demonstrates how to serve MLflow models on Posit Connect through a FastAPI application. It uses MLflow's PyFunc scoring server and provides standard MLflow endpoints with enhanced OpenAPI documentation, making it easy to deploy and consume machine learning models in production on Connect.

## Features

✨ **Posit Connect Integration** - Seamless deployment with automatic authentication  
🔄 **Multiple Input Formats** - JSON, CSV, and TensorFlow Serving formats  
📚 **Interactive Docs** - Auto-generated Swagger UI and ReDoc  
🎯 **Dynamic Schema** - Examples based on your model's signature  
🔐 **Automatic Authentication** - Uses publisher's API key for MLflow access  

## Quick Start for Connect Deployment

### Prerequisites

- Python 3.8+
- MLflow model (trained and logged to MLflow)
- Access to a Posit Connect server
- Access to an MLflow tracking server (can be hosted on the same Connect instance)

### 1. Install API Dependencies

```bash
pip install -r requirements.txt
```

### 2. ⚠️ **Critical: Update requirements.txt with Model Dependencies**

**Before deploying to Connect, you must add your model's dependencies to `requirements.txt`.**

```bash
# Extract and append model requirements
mlflow artifacts download -u "models:/my-model/Production" -d ./model_artifacts
cat ./model_artifacts/requirements.txt >> requirements.txt

# Clean up duplicates if needed
sort -u requirements.txt -o requirements.txt
```

**Why is this critical for Connect?**
- Connect installs dependencies from `requirements.txt` when deploying
- Your model needs libraries like scikit-learn, TensorFlow, PyTorch, etc.
- Without these, the deployment will fail with `ImportError`

### 3. Test Locally (Optional but Recommended)

```bash
# Install model dependencies in your local environment
./install_model_deps.sh "models:/my-model/Production"

# Test locally
export MODEL_URI="models:/my-model/Production"
python app.py
```

Visit `http://localhost:8000/docs` to verify everything works.

### 4. Deploy to Posit Connect

```bash
# Deploy using rsconnect-python
rsconnect deploy fastapi \
  --server https://your-connect-server.com \
  --api-key your-api-key \
  --title "My Model API" \
  .
```

### 5. Configure in Connect

After deployment:
1. Navigate to your content in Connect
2. Go to the **Vars** panel in content settings
3. Add environment variable: `MODEL_URI` = `models:/my-model/Production`
4. Save and restart the content

**That's it!** Connect will automatically:
- Use your API key to authenticate with MLflow
- Load the model on startup
- Serve predictions at the `/invocations` endpoint
- Provide interactive documentation at `/docs`

## Configuration for Connect

The API automatically detects when running on Posit Connect and configures itself accordingly.

### Required Environment Variable (Set in Connect)

| Variable | Description | Example |
|----------|-------------|---------|
| `MODEL_URI` | MLflow model location | `models:/my-model/Production` |

### Optional Variables (Auto-configured on Connect)

| Variable | Default on Connect | Description |
|----------|-------------------|-------------|
| `MLFLOW_TRACKING_URI` | `{CONNECT_SERVER}/mlflow` | MLflow server URL |
| `MLFLOW_TRACKING_TOKEN` | Publisher's API key | Authentication token |
| `CONNECT_SERVER` | Auto-detected | Connect server URL |

**Model URI Formats:**
- Registry: `models:/my-model/Production` or `models:/my-model/1`
- Run: `runs:/<run-id>/model`

## API Endpoints

Once deployed, your Connect content will expose:

### Interactive Documentation

| URL | Description |
|-----|-------------|
| `https://connect-server/content/{guid}/docs` | Swagger UI - Try the API interactively |
| `https://connect-server/content/{guid}/redoc` | ReDoc - Clean documentation view |

### Making Predictions

**POST** `/invocations` - Multiple input formats supported:

```bash
# JSON (dataframe_split)
curl -X POST https://connect-server/content/{guid}/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "dataframe_split": {
      "columns": ["feature1", "feature2"],
      "data": [[1.0, 2.0]]
    }
  }'

# JSON (dataframe_records)
curl -X POST https://connect-server/content/{guid}/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "dataframe_records": [
      {"feature1": 1.0, "feature2": 2.0}
    ]
  }'

# CSV
curl -X POST https://connect-server/content/{guid}/invocations \
  -H "Content-Type: text/csv" \
  --data-binary @input.csv
```

### Health Checks

```bash
curl https://connect-server/content/{guid}/ping      # Quick check
curl https://connect-server/content/{guid}/health    # Detailed status
curl https://connect-server/content/{guid}/version   # MLflow version
```

## Updating requirements.txt for Connect Deployment

**This is the most important step for successful Connect deployment.**

The `requirements.txt` file initially contains only API dependencies (FastAPI, uvicorn, MLflow client). Before deploying to Connect, you must add your model's specific dependencies.

### Recommended Approach

```bash
# 1. Download model artifacts to see what your model needs
mlflow artifacts download -u "$MODEL_URI" -d ./model_artifacts

# 2. Append model requirements to your requirements.txt
cat ./model_artifacts/requirements.txt >> requirements.txt

# 3. Remove duplicates and sort
sort -u requirements.txt -o requirements.txt

# 4. Verify the file looks correct
cat requirements.txt
```

### What to Include

Your final `requirements.txt` should contain:
- **API dependencies** (already included): `fastapi`, `uvicorn`, `mlflow`
- **Model dependencies** (you must add): `scikit-learn`, `tensorflow`, `pytorch`, etc.
- **Any custom libraries** your model needs

### Example Final requirements.txt

```
fastapi>=0.104.0
uvicorn>=0.24.0
mlflow>=2.9.0
scikit-learn==1.3.0
pandas==2.0.0
numpy==1.24.0
```

**⚠️ Critical:** Every time you change models or model versions, verify the dependencies haven't changed and update `requirements.txt` before redeploying to Connect.

## Testing Before Deployment

Always test locally before deploying to Connect:

```bash
# 1. Install all dependencies (API + model)
pip install -r requirements.txt

# 2. Set environment variables
export MODEL_URI="models:/my-model/Production"
export MLFLOW_TRACKING_URI="https://your-mlflow-server.com"
export MLFLOW_TRACKING_TOKEN="your-token"

# 3. Run locally
python app.py

# 4. Test in another terminal
curl http://localhost:8000/ping
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{"dataframe_split": {"columns": ["feature1"], "data": [[1.0]]}}'
```

## Testing with Sample Model

Want to test the deployment process with a sample model first?

```bash
# 1. Train and log a sample model
python example_test.py

# 2. Update requirements.txt with the sample model's dependencies
./install_model_deps.sh 'runs:/<run-id>/model'
mlflow artifacts download -u 'runs:/<run-id>/model' -d ./model_artifacts
cat ./model_artifacts/requirements.txt >> requirements.txt

# 3. Test locally
export MODEL_URI='runs:/<run-id>/model'
python app.py

# 4. Deploy to Connect
rsconnect deploy fastapi --server https://connect.example.com --api-key your-key .

# 5. Set MODEL_URI in Connect settings to 'runs:/<run-id>/model'
```

## Connect-Specific Features

### Automatic Authentication

When deployed to Connect:
- `MLFLOW_TRACKING_TOKEN` automatically uses your Connect API key
- No additional configuration needed if MLflow is on the same Connect server
- Seamless integration with Connect-hosted MLflow tracking servers

### Content Settings

Configure your deployment in Connect:
- **Vars**: Set `MODEL_URI` and optional environment variables
- **Access**: Control who can access your API
- **Runtime**: Adjust min/max processes based on load
- **Logs**: Monitor model loading and prediction requests

### Vanity URLs

For cleaner API endpoints, set up a vanity URL in Connect:
```
https://connect-server/my-model-api/docs
```

## Updating Models in Connect

When you promote a new model version in MLflow:

1. **Update requirements.txt if dependencies changed**:
```bash
mlflow artifacts download -u "$MODEL_URI" -d ./model_artifacts
cat ./model_artifacts/requirements.txt >> requirements.txt
sort -u requirements.txt -o requirements.txt
```

2. **Redeploy to Connect**:
```bash
rsconnect deploy fastapi --server https://connect.example.com --api-key your-key .
```

3. **Or just update MODEL_URI in Connect settings** (if dependencies unchanged):
   - Go to Vars panel
   - Update `MODEL_URI` to point to new version
   - Restart the content

## Troubleshooting Connect Deployments

| Error | Solution |
|-------|----------|
| `ImportError` during deployment | Update `requirements.txt` with model dependencies |
| `Model not found` | Verify `MODEL_URI` in Connect settings |
| Authentication fails | Ensure MLflow server is accessible from Connect |
| Deployment bundle too large | Use `models:/` URI instead of including model files |

### Checking Logs in Connect

1. Navigate to your content in Connect
2. Click on the **Logs** tab
3. Look for:
   - Model loading messages
   - Dependency installation
   - Error messages with stack traces

## Best Practices for Connect

1. **Pin dependency versions** in `requirements.txt` for reproducibility
2. **Test locally** before deploying to Connect
3. **Use registered models** (`models:/`) rather than runs for production
4. **Monitor logs** in Connect after deployment
5. **Set appropriate process limits** based on model size and load
6. **Use vanity URLs** for cleaner, more stable API endpoints

## Resources

- **Posit Connect Docs**: https://docs.posit.co/connect/
- **MLflow Docs**: https://mlflow.org/docs/latest/
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **rsconnect-python**: https://github.com/rstudio/rsconnect-python

## Support

For Connect deployment issues:
- Check the troubleshooting section above
- Review Connect logs for error details
- Verify `requirements.txt` includes all model dependencies
- Test locally before deploying
