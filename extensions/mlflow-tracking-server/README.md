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

Both deployment modes now support **OAuth integrations** for seamless authentication to cloud resources without managing long-lived credentials.

## Prerequisites

- Posit Connect 2025.10.0 or later
- For external storage: Access to compatible external services (e.g., AWS S3/RDS, Azure Blob Storage/SQL, GCP Cloud Storage/SQL, etc.)
- For OAuth integrations: Appropriate OAuth integration configured in Connect (AWS, Azure, or GCP)

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

### Option 2: External Storage with OAuth (Recommended for Production)

This configuration uses external services for artifact storage and metadata database with **automatic OAuth-based authentication** - no need to manage access keys or connection strings!

The extension supports **AWS RDS IAM authentication** and **Azure AD authentication** through Posit Connect's OAuth integrations. When configured:
- Database authentication tokens are automatically generated and refreshed
- AWS credentials for S3 access are obtained via OAuth (no access keys needed)
- Azure credentials for Blob Storage are obtained via OAuth (no connection strings needed)
- All credentials are automatically rotated before expiration

#### AWS Setup with OAuth Integration

##### Prerequisites

1. **Enable IAM Authentication on RDS Database**
   - Your RDS PostgreSQL instance **must have IAM database authentication enabled**
   - This is required for OAuth-based authentication to work
   - See [AWS RDS IAM Authentication Overview](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html)

2. **Configure Database User for IAM Authentication**
   - The PostgreSQL user must be granted the `rds_iam` role
   - Connect to your RDS instance using a master/admin account and run:
     ```sql
     CREATE USER mlflow_user WITH LOGIN;
     GRANT rds_iam TO mlflow_user;
     ```
   - See [Creating a Database Account Using IAM Authentication](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.DBAccounts.html#UsingWithRDS.IAMDBAuth.DBAccounts.PostgreSQL)

3. **Configure IAM Policy**
   - The OAuth integration's IAM role needs permission to connect to the database
   - Required IAM policy:
     ```json
     {
       "Version": "2012-10-17",
       "Statement": [
         {
           "Effect": "Allow",
           "Action": [
             "rds-db:connect"
           ],
           "Resource": [
             "arn:aws:rds-db:REGION:ACCOUNT_ID:dbuser:DB_RESOURCE_ID/mlflow_user"
           ]
         }
       ]
     }
     ```
   - See [Creating and Using an IAM Policy for IAM Database Access](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.IAMPolicy.html)

##### Setup Steps

1. **Create PostgreSQL Database in AWS RDS**
   - Navigate to AWS RDS Console
   - Click "Create database"
   - Select PostgreSQL engine
   - **Enable IAM database authentication** (required for OAuth)
   - Configure database:
     - Database name: `mlflow`
     - Master username: `postgres` (for initial setup)
     - Master password: (save securely for initial setup)
   - Configure security group to allow inbound traffic on port 5432 from Connect's IP
   - Note the endpoint URL and DB resource ID

2. **Grant rds_iam Role to Database User**
   - Connect to the database using the master credentials:
     ```bash
     psql -h your-db.xxxxx.region.rds.amazonaws.com -U postgres -d mlflow
     ```
   - Grant the `rds_iam` role:
     ```sql
     CREATE USER mlflow_user WITH LOGIN;
     GRANT rds_iam TO mlflow_user;
     ```

3. **Create S3 Bucket for Artifacts**
   - Navigate to AWS S3 Console
   - Click "Create bucket"
   - Bucket name: `mlflow-artifacts-yourorg` (must be globally unique)
   - Choose appropriate region (same as RDS for performance)
   - Block public access: Enabled (recommended)
   - Versioning: Optional (recommended for production)

4. **Configure AWS OAuth Integration in Connect**
   - In Connect, navigate to your content item
   - Configure AWS OAuth integration with appropriate IAM role
   - Ensure the IAM role has:
     - RDS connect permission (`rds-db:connect`)
     - S3 access permissions (PutObject, GetObject, DeleteObject, ListBucket)

5. **Deploy Extension with Environment Variables**

Configure the following environment variables in your Connect extension settings:

```bash
# AWS RDS Configuration (OAuth-based authentication)
RDS_ENDPOINT=your-database.xxxxx.region.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=mlflow
RDS_USERNAME=mlflow_user
RDS_DB_TYPE=postgresql
AWS_REGION=us-east-2

# S3 Artifact Storage (OAuth will provide credentials automatically)
MLFLOW_ARTIFACTS_DESTINATION=s3://mlflow-artifacts-yourorg/artifacts
```

**No AWS access keys or database passwords needed!** The extension automatically:
- Generates RDS IAM authentication tokens via OAuth
- Obtains temporary AWS credentials for S3 access
- Refreshes all tokens before expiration (every hour by default)

#### Azure Setup with OAuth Integration

##### Prerequisites

1. **Enable Azure AD Authentication on Azure Database**
   - Your Azure PostgreSQL or SQL Server must have Azure AD authentication enabled
   - This is required for OAuth-based authentication

2. **Grant Database Access to Azure AD Service Principal**
   - The service principal from your OAuth integration needs database access
   - For PostgreSQL:
     ```sql
     CREATE USER "service-principal-name" WITH LOGIN;
     GRANT ALL PRIVILEGES ON DATABASE mlflow TO "service-principal-name";
     ```
   - For SQL Server:
     ```sql
     CREATE USER [service-principal-name] FROM EXTERNAL PROVIDER;
     ALTER ROLE db_owner ADD MEMBER [service-principal-name];
     ```
   - See [Azure AD Authentication for PostgreSQL](https://docs.microsoft.com/en-us/azure/postgresql/connect-azure-active-directory) and [Azure AD Authentication for SQL Server](https://docs.microsoft.com/en-us/sql/relational-databases/security/authentication-access/azure-active-directory-authentication?view=sql-server-ver15) for details

##### Setup Steps

1. **Create Azure Database (PostgreSQL or SQL Server)**
   - Use the Azure portal to create a new PostgreSQL or SQL Server instance
   - Configure firewall rules to allow Connect's IP
   - Note the server name, database name, and admin login

2. **Configure Azure AD Authentication**
   - Assign the Azure AD admin for the server in the Azure portal
   - Create a new Azure AD user or use an existing one
   - For PostgreSQL, run the following in the query editor:
     ```sql
     CREATE USER "service-principal-name" WITH LOGIN;
     GRANT ALL PRIVILEGES ON DATABASE mlflow TO "service-principal-name";
     ```
   - For SQL Server, run the following in the query editor:
     ```sql
     CREATE USER [service-principal-name] FROM EXTERNAL PROVIDER;
     ALTER ROLE db_owner ADD MEMBER [service-principal-name];
     ```

3. **Create Azure Blob Storage Account for Artifacts**
   - Use the Azure portal to create a new Storage account
   - Choose Blob storage and appropriate performance/tier options
   - Note the storage account name and container

4. **Configure Azure OAuth Integration in Connect**
   - In Connect, navigate to your content item
   - Configure Azure OAuth integration with appropriate permissions
   - Ensure the service principal has:
     - Contributor role on the Storage account
     - Database access in Azure AD

5. **Deploy Extension with Environment Variables**

Configure the following environment variables in your Connect extension settings:

```bash
# Azure Database Configuration (OAuth-based authentication)
AZURE_DATABASE_SERVER=your-server-name.database.windows.net
AZURE_DATABASE_NAME=mlflow
AZURE_DATABASE_USERNAME=service-principal-name
AZURE_DATABASE_TYPE=postgresql
AZURE_REGION=eastus

# Azure Blob Storage Configuration (OAuth will provide credentials automatically)
MLFLOW_ARTIFACTS_DESTINATION=wasbs://mlflow-artifacts@your-storage-account.blob.core.windows.net/artifacts
```

**No Azure connection strings or database passwords needed!** The extension automatically:
- Authenticates to Azure SQL/PostgreSQL using Azure AD tokens
- Obtains temporary credentials for Blob Storage access
- Refreshes all tokens before expiration (every hour by default)

### GCP Setup with OAuth Integration

##### Prerequisites

1. **Enable Cloud SQL and Cloud Storage APIs**
   - Enable the Cloud SQL API and Cloud Storage API in your GCP project
   - This is required for the extension to access Cloud SQL and Cloud Storage

2. **Create a Cloud SQL Instance**
   - Create a new Cloud SQL instance (PostgreSQL or SQL Server)
   - Note the instance connection name and database name

3. **Create a Cloud Storage Bucket**
   - Create a new Cloud Storage bucket for storing artifacts
   - Note the bucket name

4. **Configure IAM Permissions**
   - The service account used by Posit Connect needs permissions to access Cloud SQL and Cloud Storage
   - Assign the following roles:
     - Cloud SQL Client
     - Storage Object Admin

5. **Create a Service Account Key (Optional)**
   - If not using the default service account, create a service account key
   - Download the JSON key file

##### Setup Steps

1. **Create PostgreSQL Database in Cloud SQL**
   - Connect to your Cloud SQL instance using the Cloud SQL Auth proxy or public IP
   - Create a new database for MLflow:
     ```sql
     CREATE DATABASE mlflow;
     ```

2. **Create a Cloud Storage Bucket for Artifacts**
   - Use the GCP Console or `gsutil` to create a new bucket:
     ```bash
     gsutil mb gs://mlflow-artifacts-yourorg/
     ```

3. **Deploy Extension with Environment Variables**

Configure the following environment variables in your Connect extension settings:

```bash
# GCP Cloud SQL Configuration
CLOUD_SQL_CONNECTION_NAME=your-project:us-central1:your-sql-instance
CLOUD_SQL_DATABASE=mlflow
CLOUD_SQL_USERNAME=mlflow_user
CLOUD_SQL_PASSWORD=your_password

# GCP Cloud Storage Configuration (OAuth will provide credentials automatically)
MLFLOW_ARTIFACTS_DESTINATION=gs://mlflow-artifacts-yourorg/artifacts
```

**No GCP service account keys or database passwords needed!** The extension automatically:
- Authenticates to Cloud SQL using Cloud SQL Auth proxy or public IP
- Obtains temporary credentials for Cloud Storage access
- Refreshes all tokens before expiration (every hour by default)

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
