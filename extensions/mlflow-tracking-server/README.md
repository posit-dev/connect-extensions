# MLflow Tracking Server Extension for Posit Connect

This extension enables MLflow tracking server capabilities within Posit Connect. It provides a fully-featured MLflow tracking server that can be deployed as a Connect extension, allowing data scientists to track experiments, log models, and manage the ML lifecycle directly within their Connect environment.

## ⚠️ Alpha Status

**This extension is currently alpha.** While fully functional, there are important considerations:

- **Manual Management**: MLflow version upgrades must be performed manually by redeploying the extension to the existing app GUID
- **No Automatic Updates**: Unlike managed services, you are responsible for keeping MLflow up-to-date with security patches and new features
- **Schema Migrations**: Database schema upgrades require careful coordination during redeployment

Despite these limitations, this approach offers significant benefits for teams already invested in the Posit Connect ecosystem.

## Why Deploy MLflow to Posit Connect?

### Key Benefits

1. **Unified Authentication & Access Control**
   - Leverage your existing Connect API keys - no additional credential management
   - Data scientists use the same authentication mechanism they already know
   - Centralized user management through Connect's existing access controls
   - No separate MLflow authentication system to configure or maintain

2. **Simplified Infrastructure Management**
   - Deploy MLflow where your data science workflows already live
   - No separate Kubernetes cluster or VM infrastructure to provision
   - Benefit from Connect's built-in high availability and monitoring capabilities
   - Single platform for all data science deliverables: models, dashboards, APIs, and now MLflow tracking

3. **Zero-Configuration Local Storage Option**
   - Use Connect's persistent app storage (2025.10.0+) - no cloud resources needed for development/testing
   - No AWS/Azure/GCP accounts required to get started
   - Eliminate external infrastructure costs for smaller teams or proof-of-concepts
   - Data stays within your organization's Connect environment

4. **Seamless Integration with Existing Workflows**
   - MLflow server runs alongside your deployed models and applications
   - Direct integration with Connect-hosted Python environments
   - Natural fit for teams already standardized on Posit Connect
   - Reduced context switching between tools and platforms

## Deployment Options

This extension supports two deployment modes:

1. **Local Storage** - Artifacts and metadata stored on Connect's local filesystem (Connect 2025.10.0+)
2. **External Storage** - Artifacts and metadata stored in external services (supports any MLflow-compatible backend storage and artifact store)

## Prerequisites

- Posit Connect 2025.10.0 or later
- For external storage: Access to compatible external services (e.g., AWS S3/RDS, Azure Blob Storage/SQL, GCP Cloud Storage/SQL, etc.)

## Deployment Scenarios

### Option 1: Local Storage (Recommended for Development/Testing)

This configuration stores all MLflow data on Connect's local filesystem. No external dependencies required.

#### Setup Steps

1. Create a new Python extension in Connect
2. Deploy the MLflow server extension with default settings
3. Set the minimum number of processes to 1 to ensure the server is always running
4. No additional configuration required - the extension will use Connect's local storage (2025.10.0+)
5. [Optional] Configure environment variables for backend storage customization (see below)
6. [Optional] Set an easy-to-remember vanity URL in Connect for easy access

#### Environment Variables

```bash
# No additional environment variables needed for local storage
# The extension will automatically configure local storage paths
```

### Option 2: External Storage (Recommended for Production)

This configuration uses external services for artifact storage and metadata database. MLflow supports various external storage backends including:

- **Artifact Stores**: AWS S3, Azure Blob Storage, Google Cloud Storage, SFTP, NFS, HDFS
- **Backend Stores**: PostgreSQL, MySQL, MSSQL, SQLite

**This README provides an AWS example using S3 and RDS PostgreSQL**, but you can adapt these instructions for other cloud providers or storage systems supported by MLflow.

For comprehensive information on supported storage backends, see:
- [MLflow Artifact Stores Documentation](https://mlflow.org/docs/latest/ml/tracking/artifact-stores/)
- [MLflow Backend Stores Documentation](https://mlflow.org/docs/latest/ml/tracking/backend-stores/)

#### Setup Steps

##### 1. Create PostgreSQL Database in AWS RDS

1. Navigate to AWS RDS Console
2. Click "Create database"
3. Select PostgreSQL engine
4. Choose appropriate instance size (db.t3.micro for testing, larger for production)
5. Configure database:
   - Database name: `mlflow`
   - Master username: `mlflow_user`
   - Master password: (save securely)
   - Enable public accessibility if accessing from Connect
6. Configure security group to allow inbound traffic on port 5432 from Connect's IP
7. Note the endpoint URL (e.g., `mlflow-db.xxxxx.us-east-1.rds.amazonaws.com`)

##### 2. Create S3 Bucket for Artifacts

1. Navigate to AWS S3 Console
2. Click "Create bucket"
3. Bucket name: `mlflow-artifacts-yourorg` (must be globally unique)
4. Choose appropriate region (same as RDS for performance)
5. Configure bucket settings:
   - Block public access: Enabled (recommended)
   - Versioning: Optional (recommended for production)
6. Note the bucket name and region

##### 3. Configure IAM Credentials

1. Create IAM user with programmatic access
2. Attach policy with S3 permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::mlflow-artifacts-yourorg",
        "arn:aws:s3:::mlflow-artifacts-yourorg/*"
      ]
    }
  ]
}
```
3. Save Access Key ID and Secret Access Key

##### 4. Deploy Extension with Environment Variables

Configure the following environment variables in your Connect extension settings:

```bash
# Database Configuration
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:YOUR_PASSWORD@mlflow-db.xxxxx.us-east-1.rds.amazonaws.com:5432/mlflow

# S3 Artifact Storage
MLFLOW_ARTIFACT_ROOT=s3://mlflow-artifacts-yourorg/artifacts

# AWS Credentials
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=...JNu1VklZ+qVit3bbv6FM5P46F/fARjaP0vPXvGQ==
AWS_DEFAULT_REGION=us-east-2
```

**Important Note:** External integrations cannot yet take advantage of OAuth integrations in Posit Connect. You must provide explicit credentials (e.g., AWS Access Key ID and Secret Access Key, Azure connection strings, GCP service account keys) as environment variables for your external services. OAuth support for external storage providers is planned for a future release.

**For Other Cloud Providers:**
- **Azure**: Use `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCESS_KEY` with `wasbs://` artifact root
- **GCP**: Use `GOOGLE_APPLICATION_CREDENTIALS` with `gs://` artifact root
- **NFS**: To store artifacts in an NFS mount, specify a URI as a normal file system path, e.g., `/mnt/nfs`. This path must be the same on both the server and the client -- you may need to use symlinks or remount the client in order to enforce this property. Set `MLFLOW_ARTIFACT_ROOT=/mnt/nfs/mlflow-artifacts`
- Consult [MLflow documentation](https://mlflow.org/docs/latest/tracking.html#artifact-stores) for specific configuration requirements

## Connecting to the MLflow Server

Once deployed, the MLflow server is accessible through Connect's URL structure. Authentication is handled via Connect API keys.

```python
import os
import mlflow

# Configure connection to Connect-hosted MLflow server
CONNECT_SERVER = os.getenv('CONNECT_SERVER', 'https://connect.example.com/')
MLFLOW_TRACKING_URI = os.getenv('MLFLOW_TRACKING_URI', f'{CONNECT_SERVER}mlflow/')

# Set up authentication using Connect API key
os.environ["MLFLOW_TRACKING_TOKEN"] = os.getenv('MLFLOW_TRACKING_TOKEN', 
                                                 os.getenv('CONNECT_API_KEY', ""))

# Configure MLflow client
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Now you can use MLflow as normal
with mlflow.start_run():
    mlflow.log_param("alpha", 0.5)
    mlflow.log_metric("rmse", 0.876)
    mlflow.log_artifact("model.pkl")
```

### Key Points

- **Authentication**: Since the MLflow UI and API are deployed to Connect, a Connect API key is the only credential needed to access the endpoints
- **Transparent Storage**: Client code is identical for both local and external storage deployments
- **Server-Side Credentials**: AWS credentials for S3/RDS are configured server-side in the extension and not exposed to clients
- **Security**: All traffic goes through Connect's authentication and authorization layer

## Best Practices

### Local Storage
- ✅ Ideal for development and testing
- ✅ Simple setup with no external dependencies
- ✅ **Zero additional infrastructure costs**
- ✅ **No cloud account or credentials required**
- ✅ **Data stays within Connect's managed environment**
- ⚠️ Limited by Connect server's disk capacity
- ⚠️ Not recommended for production with multiple users
- ⚠️ Backup and recovery depend on Connect's backup strategy

### External Storage (S3 + RDS)
- ✅ Scalable artifact storage
- ✅ Robust metadata storage with PostgreSQL
- ✅ Better suited for production environments
- ✅ Supports team collaboration
- ✅ Independent backup and disaster recovery
- ⚠️ Requires AWS infrastructure setup and costs
- ⚠️ Requires explicit credentials (OAuth not yet supported)
- ⚠️ Additional external services to manage and monitor

## Management and Upgrades

### Upgrading MLflow

To upgrade MLflow to a newer version:

1. Update the version in `requirements.txt`
2. Test the upgrade in a development environment first
3. Review MLflow release notes for breaking changes and schema migrations
4. Redeploy the extension to the **same app GUID** in Connect
5. Monitor logs during startup to ensure database migrations complete successfully

**Important**: Always redeploy to the existing app GUID to preserve:
- The app's persistent storage directory (for local storage deployments)
- Configured environment variables
- Access permissions and API keys
- The MLflow tracking URI that clients are using

### Backup and Recovery

**For Local Storage:**
- Backups are handled by Connect's persistent storage backup mechanisms
- Consult your Connect administrator about backup schedules and retention
- The `app-data` directory contains all experiments, runs, and artifacts

**For External Storage:**
- Back up your RDS database using AWS automated backups or snapshots
- Enable S3 versioning for artifact recovery
- Document your environment variable configuration separately

## Troubleshooting

### Connection Issues
- Verify Connect API key has appropriate permissions
- Check that the MLflow extension is running in Connect
- Ensure `MLFLOW_TRACKING_URI` points to the correct Connect URL

### External Storage Issues
- Verify AWS credentials have correct S3 bucket permissions
- Check RDS security groups allow connections from Connect
- Ensure database exists and credentials are correct
- Verify S3 bucket exists and is in the correct region

### Upgrade Issues
- Check Connect logs for database migration errors
- Ensure the app GUID matches the previous deployment
- Verify persistent storage directory is accessible and has sufficient space
- Review MLflow's migration documentation for version-specific requirements

## Support

For issues or questions, please contact your Posit Connect administrator or open an issue in the repository.
