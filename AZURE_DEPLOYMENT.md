# Azure Deployment Guide for WCO Hackathon Dashboard

## Prerequisites
- Azure account with active subscription
- Azure CLI installed (`az`)
- Docker Desktop (for container deployment)

## Deployment Options

### Option 1: Azure App Service (Recommended)

#### Step 1: Login to Azure
```bash
az login
```

#### Step 2: Create Resource Group
```bash
az group create --name wco-hackathon-rg --location eastus
```

#### Step 3: Create App Service Plan
```bash
az appservice plan create \
  --name wco-hackathon-plan \
  --resource-group wco-hackathon-rg \
  --sku B1 \
  --is-linux
```

#### Step 4: Create Web App
```bash
az webapp create \
  --resource-group wco-hackathon-rg \
  --plan wco-hackathon-plan \
  --name wco-hackathon-dashboard \
  --runtime "PYTHON:3.11"
```

#### Step 5: Configure Startup Command
```bash
az webapp config set \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-dashboard \
  --startup-file "startup.sh"
```

#### Step 6: Deploy from Local Git
```bash
# Get deployment credentials
az webapp deployment user set \
  --user-name <your-username> \
  --password <your-password>

# Get Git URL
az webapp deployment source config-local-git \
  --name wco-hackathon-dashboard \
  --resource-group wco-hackathon-rg

# Add Azure remote and push
git remote add azure <git-url-from-above>
git push azure master
```

#### Step 7: Access Your App
```bash
az webapp browse --name wco-hackathon-dashboard --resource-group wco-hackathon-rg
```

Your app will be available at: `https://wco-hackathon-dashboard.azurewebsites.net`

---

### Option 2: Azure Container Instances (Docker)

#### Step 1: Build and Push Docker Image to Azure Container Registry

```bash
# Create Azure Container Registry
az acr create \
  --resource-group wco-hackathon-rg \
  --name wcohackathonregistry \
  --sku Basic

# Login to ACR
az acr login --name wcohackathonregistry

# Build and push image
az acr build \
  --registry wcohackathonregistry \
  --image wco-dashboard:latest .
```

#### Step 2: Deploy Container Instance

```bash
# Get ACR credentials
ACR_LOGIN_SERVER=$(az acr show --name wcohackathonregistry --query loginServer --output tsv)

az container create \
  --resource-group wco-hackathon-rg \
  --name wco-dashboard-container \
  --image ${ACR_LOGIN_SERVER}/wco-dashboard:latest \
  --registry-login-server ${ACR_LOGIN_SERVER} \
  --registry-username wcohackathonregistry \
  --registry-password $(az acr credential show --name wcohackathonregistry --query "passwords[0].value" -o tsv) \
  --dns-name-label wco-hackathon \
  --ports 8501 \
  --cpu 1 \
  --memory 2
```

#### Step 3: Get Container URL
```bash
az container show \
  --resource-group wco-hackathon-rg \
  --name wco-dashboard-container \
  --query "{FQDN:ipAddress.fqdn,ProvisioningState:provisioningState}" \
  --output table
```

Your app will be available at: `http://<dns-name>.eastus.azurecontainer.io:8501`

---

### Option 3: Deploy via Azure Portal (GUI)

1. **Login to Azure Portal**: https://portal.azure.com

2. **Create Web App**:
   - Click "Create a resource" → "Web App"
   - Fill in details:
     - Resource Group: Create new "wco-hackathon-rg"
     - Name: wco-hackathon-dashboard
     - Runtime: Python 3.11
     - Region: East US
     - Pricing: Basic B1
   - Click "Review + Create"

3. **Configure Deployment**:
   - Go to your Web App → "Deployment Center"
   - Choose "Local Git" or "GitHub"
   - If GitHub: Connect repository and select branch
   - If Local Git: Follow git push instructions

4. **Configure Application Settings**:
   - Go to "Configuration" → "General settings"
   - Startup Command: `bash startup.sh`
   - Save changes

5. **Browse**: Click "Browse" to view your app

---

## Environment Variables (Optional)

If you need to set environment variables:

```bash
az webapp config appsettings set \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-dashboard \
  --settings \
    STREAMLIT_SERVER_PORT=8000 \
    STREAMLIT_SERVER_HEADLESS=true
```

---

## Monitoring & Logs

### View Application Logs
```bash
az webapp log tail \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-dashboard
```

### Enable Application Insights
```bash
az monitor app-insights component create \
  --app wco-hackathon-insights \
  --location eastus \
  --resource-group wco-hackathon-rg \
  --application-type web

# Link to Web App
az webapp config appsettings set \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-dashboard \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=<key-from-above>
```

---

## Scaling

### Scale Up (Vertical)
```bash
az appservice plan update \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-plan \
  --sku S1
```

### Scale Out (Horizontal)
```bash
az appservice plan update \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-plan \
  --number-of-workers 2
```

---

## Cost Management

Estimated monthly costs:
- **Basic B1**: ~$13/month
- **Standard S1**: ~$70/month
- **Container Instances**: Pay-per-second billing

Stop the app when not in use:
```bash
az webapp stop \
  --resource-group wco-hackathon-rg \
  --name wco-hackathon-dashboard
```

---

## Cleanup Resources

When you're done:
```bash
az group delete --name wco-hackathon-rg --yes --no-wait
```

---

## Troubleshooting

### App not starting
1. Check logs: `az webapp log tail ...`
2. Verify startup command: Check Configuration → General Settings
3. Ensure all dependencies in requirements.txt

### Slow performance
1. Upgrade App Service Plan to S1 or higher
2. Enable Application Insights for monitoring
3. Add caching with `@st.cache_data`

### File upload issues
1. Increase file upload limit in Streamlit config
2. Check Azure App Service file size limits
3. Consider using Azure Blob Storage for large files

---

## Custom Domain (Optional)

```bash
# Add custom domain
az webapp config hostname add \
  --webapp-name wco-hackathon-dashboard \
  --resource-group wco-hackathon-rg \
  --hostname www.your-domain.com

# Enable HTTPS
az webapp config ssl bind \
  --certificate-thumbprint <thumbprint> \
  --ssl-type SNI \
  --name wco-hackathon-dashboard \
  --resource-group wco-hackathon-rg
```

---

## GitHub Actions CI/CD (Advanced)

Create `.github/workflows/azure-deploy.yml` for automated deployments on every push.
