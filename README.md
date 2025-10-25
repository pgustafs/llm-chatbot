# LLM Chatbot - OpenShift CI/CD Deployment

Complete deployment guide for Streamlit LLM Chatbot on OpenShift 4.19 with Tekton CI/CD pipeline....

## 📋 Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Repository Structure](#repository-structure)
- [Initial Setup](#initial-setup)
- [OpenShift Configuration](#openshift-configuration)
- [Tekton Pipeline Setup](#tekton-pipeline-setup)
- [GitHub Webhook Configuration](#github-webhook-configuration)
- [Manual Deployment](#manual-deployment)
- [CI/CD Workflow](#cicd-workflow)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture Overview

```
GitHub Repository (main branch)
    ↓ (webhook trigger)
Tekton EventListener
    ↓
Pipeline Execution:
  1. git-clone: Clone repository
  2. buildah: Build RHEL 10 UBI container
  3. buildah: Push to Quay.io
  4. openshift-client: Deploy to OpenShift
    ↓
Running Application
  - Deployment with 1 replica
  - Service (ClusterIP)
  - Route (HTTPS with edge termination)
```

## 📦 Prerequisites

### Required Tools
- `oc` CLI (OpenShift 4.19+)
- `tkn` CLI (Tekton Pipelines)
- `git` CLI
- Access to OpenShift 4.19+ cluster
- Quay.io account
- GitHub account

### OpenShift Requirements
- OpenShift Pipelines Operator 1.18+ (Tekton 0.68+)
- Cluster admin access for initial setup
- Namespace creation permissions

## 📁 Repository Structure

```
llm-chatbot/
├── README.md                      # This file
├── app.py                         # Streamlit application
├── requirements.txt               # Python dependencies
├── Dockerfile                     # RHEL 10 UBI container definition
├── .gitignore                     # Git ignore rules
├── k8s/
│   ├── deployment.yaml           # OpenShift deployment manifests
│   └── pipeline/
│       ├── pipeline.yaml         # Tekton pipeline and triggers
│       └── rbac-secrets.yaml     # RBAC and secrets configuration
└── docs/
    └── architecture.md           # Detailed architecture documentation
```

## 🚀 Initial Setup

### Step 1: Clone and Configure Repository

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/llm-chatbot.git
cd llm-chatbot

# Update configuration values
# Edit k8s/deployment.yaml - replace YOUR_QUAY_ORG
# Edit k8s/pipeline/pipeline.yaml - replace YOUR_ORG and YOUR_QUAY_ORG
```

### Step 2: Create Quay.io Repository

1. Log in to [Quay.io](https://quay.io)
2. Create new repository: `llm-chatbot`
3. Set repository to **Public** or configure robot account for private access
4. Generate robot account credentials:
   - Settings → Robot Accounts → Create Robot Account
   - Grant **Write** permissions
   - Download credentials as **Kubernetes Secret (YAML format)**
   - Save the file as `quay-robot-secret.yaml`
   ```bash
   # Edit the downloaded quay-robot-secret.yaml
   # Change the data key from .dockerconfigjson to config.json

   apiVersion: v1
   kind: Secret
   metadata:
     name: quay-auth-secret
     namespace: llm-chatbot
   type: Opaque  # Change from kubernetes.io/dockerconfigjson to Opaque
   data:
     config.json: <BASE64_ENCODED_DATA>  # Change key name here
   ```

### Step 3: Login to OpenShift

```bash
# Login to your OpenShift cluster
oc login --token=YOUR_TOKEN --server=https://api.your-cluster.com:6443

# or

oc login -u <username> --server=https://api.your-cluster.com:6443

# Verify connection
oc whoami
oc version
```

## ⚙️ OpenShift Configuration

### Step 4: Install OpenShift Pipelines Operator

If not already installed:

```bash
# Create subscription for OpenShift Pipelines
cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: openshift-pipelines-operator
  namespace: openshift-operators
spec:
  channel: latest
  name: openshift-pipelines-operator-rh
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF

# Wait for operator to be ready
oc get csv -n openshift-operators | grep openshift-pipelines
```

Verify installation:
```bash
oc get pods -n openshift-pipelines
# Should show tekton-pipelines-controller, tekton-triggers-controller, etc.
```

### Step 5: Create Project and Apply Manifests

```bash
# Create the namespace
oc apply -f k8s/deployment.yaml

# Verify namespace creation
oc get namespace llm-chatbot
oc project llm-chatbot
```

## 🔐 Secret Configuration

### Step 6: Create Quay.io Authentication Secret

You have three methods to create the Quay authentication secret:

#### Method 1: Using Quay Robot Account YAML (Recommended)

If you downloaded the Kubernetes Secret YAML from Quay.io:

```bash
# Apply the downloaded secret directly
# First, edit the downloaded file
#
# apiVersion: v1
# kind: Secret
# metadata:
#   name: quay-auth-secret # Change name
#   namespace: llm-chatbot # Add namespace
# type: Opaque  # Change from kubernetes.io/dockerconfigjson to Opaque
# data:
#   config.json: <BASE64_ENCODED_DATA>  # Change the data key from .dockerconfigjson to config.json

# Then apply it
oc apply -f quay-robot-secret.yaml

# Verify secret creation
oc get secret quay-auth-secret -n llm-chatbot
```

#### Method 2: Using Docker Config (Manual Credentials)

If you want to manually create the secret with your Quay credentials:

```bash
oc create secret docker-registry quay-auth-secret \
  --docker-server=quay.io \
  --docker-username=YOUR_QUAY_USERNAME \
  --docker-password=YOUR_QUAY_PASSWORD \
  --docker-email=YOUR_EMAIL \
  -n llm-chatbot

# Verify secret creation
oc get secret quay-auth-secret -n llm-chatbot
```

#### Method 3: Using Existing Docker Config

If you already have Docker credentials configured locally:

```bash
# Login to Quay first
podman login quay.io
# or
docker login quay.io

# Create secret from your local docker config
oc create secret generic quay-auth-secret \
  --from-file=.dockerconfigjson=${HOME}/.docker/config.json \
  --type=kubernetes.io/dockerconfigjson \
  -n llm-chatbot

# Verify secret creation
oc get secret quay-auth-secret -n llm-chatbot
```

**Important**: Make sure the secret is named `quay-auth-secret` as this is referenced in the pipeline configuration.

### Step 7: Create GitHub Webhook Secret

```bash
# Generate a secure random string for webhook
WEBHOOK_SECRET=$(openssl rand -base64 32)

# Create the secret
oc create secret generic github-webhook-secret \
  --from-literal=secret=${WEBHOOK_SECRET} \
  -n llm-chatbot

# Save this secret - you'll need it for GitHub webhook configuration
echo "Your webhook secret: ${WEBHOOK_SECRET}"

# Verify secret creation
oc get secret github-webhook-secret -n llm-chatbot

# Verify the secret value
oc get secret github-webhook-secret -n llm-chatbot -o jsonpath='{.data.secret}' | base64 -d
```

## 🔧 Tekton Pipeline Setup

### Important Note: Using Tekton Resolvers

**OpenShift Pipelines 1.11+** uses **Tekton Resolvers** instead of ClusterTasks or namespace-scoped Tasks. Resolvers dynamically fetch tasks from remote sources:

- ✅ **Hub Resolver**: Fetches from Tekton Hub or Artifact Hub
- ✅ **Bundles Resolver**: Fetches from OCI registries
- ✅ **Cluster Resolver**: References tasks in other namespaces (e.g., openshift-pipelines)
- ✅ **Git Resolver**: Fetches from Git repositories

**Benefits:**
- No need to manually install tasks
- Always get the latest task versions
- Centralized task management
- Better security and versioning

This deployment uses:
- **Hub resolver** for `git-clone` and `buildah` tasks (from Artifact Hub)
- **Cluster resolver** for `openshift-client` task (pre-installed in openshift-pipelines namespace)

### Step 8: Apply RBAC and Pipeline Resources

```bash
# Apply RBAC configurations
oc apply -f k8s/pipeline/rbac-secrets.yaml

# Apply pipeline definitions
oc apply -f k8s/pipeline/pipeline.yaml

# Verify pipeline creation
tkn pipeline list -n llm-chatbot

# View pipeline details (you'll see tasks are resolved remotely)
tkn pipeline describe llm-chatbot-pipeline -n llm-chatbot
```

**Note:** You don't need to install tasks manually - they're fetched automatically by the resolvers when the pipeline runs!

### Step 9: Verify Pipeline Components

```bash
# Check EventListener service was created
oc get svc -n llm-chatbot | grep el-llm-chatbot-listener

# Check webhook route
oc get route llm-chatbot-webhook -n llm-chatbot

# Get webhook URL
WEBHOOK_URL=$(oc get route llm-chatbot-webhook -n llm-chatbot -o jsonpath='{.spec.host}')
echo "Webhook URL: https://${WEBHOOK_URL}"
```

## 🔗 GitHub Webhook Configuration

### Step 10: Configure GitHub Webhook

1. Navigate to your GitHub repository
2. Go to **Settings** → **Webhooks** → **Add webhook**
3. Configure webhook:
   - **Payload URL**: `https://YOUR_WEBHOOK_URL` (from Step 9)
   - **Content type**: `application/json`
   - **Secret**: Use the webhook secret from Step 7
   - **SSL verification**: Enable
   - **Events**: Select "Just the push event"
   - **Active**: Check the box
4. Click **Add webhook**
5. Test webhook by pushing a commit

```bash
# 1. Check if PipelineRuns are being created
oc get pipelineruns -n llm-chatbot --sort-by=.metadata.creationTimestamp

# 2. Check for errors in EventListener
oc logs -n llm-chatbot -l eventlistener=llm-chatbot-listener --tail=100
```

## 📦 Manual Deployment

### Understanding Service Accounts

This deployment uses two different service accounts with distinct purposes:

#### 1. Application ServiceAccount (`llm-chatbot`)
**Location**: `k8s/deployment.yaml`
**Purpose**: Used by the application pods themselves

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: llm-chatbot
  namespace: llm-chatbot
```

**What it does**:
- Provides an identity for your application pods to run under
- Used for pod-to-pod communication within the cluster
- Can be granted specific RBAC permissions if the app needs to interact with Kubernetes API
- Allows linking image pull secrets if needed (e.g., `oc secrets link llm-chatbot quay-auth-secret --for=pull`)
- Follows principle of least privilege - each app has its own identity
- Even if your app doesn't currently need special permissions, it's a best practice to create a dedicated SA

**Why we use it**:
- Security: Separates application identity from default service account
- Future-proofing: Easy to add permissions later if needed
- Auditing: Clear identity in logs and security events
- Image pulls: Can be linked to private registry secrets

#### 2. Pipeline ServiceAccount (`pipeline`)
**Location**: `k8s/pipeline/rbac-secrets.yaml`
**Purpose**: Used by Tekton pipeline tasks during CI/CD

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: pipeline
  namespace: llm-chatbot
secrets:
- name: quay-auth-secret
- name: github-webhook-secret
```

**What it does**:
- Runs all Tekton pipeline tasks (git-clone, buildah, openshift-client)
- Has elevated permissions to build images (needs privileged SCC for buildah)
- Can create/update deployments, services, routes
- Has access to Quay credentials for pushing images
- Has access to GitHub webhook secrets

**Permissions granted**:
- **Role** (namespace-level): Manage pods, deployments, services, routes, configmaps, secrets
- **ClusterRole** (cluster-level): Use privileged SCC for buildah container builds

**Why it's separate from app SA**:
- Security: Pipeline needs more permissions than the application
- Isolation: Compromised app can't modify deployments
- Auditability: Clear separation of build-time vs runtime operations

#### Service Account Linking

You may need to link secrets to service accounts for different purposes:

```bash
# Link secret to pipeline SA (for pushing images during build)
oc secrets link pipeline quay-auth-secret -n llm-chatbot

# Link secret to app SA (for pulling images at runtime - if using private images)
oc secrets link llm-chatbot quay-auth-secret --for=pull -n llm-chatbot
```

The `--for=pull` flag is specifically for image pull operations, while without it, the secret is mounted as a regular secret for the pods to use.

### Step 11: Test Manual Pipeline Run

Before setting up automation, test the pipeline manually:

```bash
# Create a manual PipelineRun
cat <<EOF | oc create -f -
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: llm-chatbot-manual-
  namespace: llm-chatbot
spec:
  pipelineRef:
    name: llm-chatbot-pipeline
  params:
  - name: git-url
    value: https://github.com/YOUR_ORG/llm-chatbot.git
  - name: git-revision
    value: main
  - name: image-tag
    value: manual-test
  workspaces:
  - name: source-workspace
    persistentVolumeClaim:
      claimName: pipeline-workspace-pvc
  - name: dockerconfig-secret
    secret:
      secretName: quay-auth-secret
  serviceAccountName: pipeline
EOF

# Watch pipeline execution (tasks will be resolved automatically)
tkn pipelinerun logs -f -n llm-chatbot

# Check pipeline status
tkn pipelinerun list -n llm-chatbot
```

### Step 12: Verify Deployment

```bash
# Check deployment status
oc get deployment llm-chatbot -n llm-chatbot
oc rollout status deployment/llm-chatbot -n llm-chatbot

# Check pods
oc get pods -n llm-chatbot

# Check service
oc get svc llm-chatbot -n llm-chatbot

# Get application URL
APP_URL=$(oc get route llm-chatbot -n llm-chatbot -o jsonpath='{.spec.host}')
echo "Application URL: https://${APP_URL}"

# Test application
curl -k https://${APP_URL}/_stcore/health
```

## 🔄 CI/CD Workflow

### Automated Pipeline Trigger

Once configured, the CI/CD workflow operates as follows:

1. **Developer pushes code** to `main` branch
2. **GitHub webhook** sends event to OpenShift EventListener
3. **Tekton Trigger** validates webhook and creates PipelineRun
4. **Pipeline executes**:
   - Clones repository
   - Builds container image with Buildah
   - Pushes image to Quay.io with commit SHA as tag
   - Updates OpenShift deployment
   - Waits for rollout to complete
5. **Application automatically updates** with new version

### Monitoring Pipeline Execution

```bash
# Watch all pipeline runs
tkn pipelinerun list -n llm-chatbot

# Follow specific pipeline run
tkn pipelinerun logs PIPELINE_RUN_NAME -f -n llm-chatbot

# Check EventListener logs
oc logs -f deployment/el-llm-chatbot-listener -n llm-chatbot

# View recent events
oc get events -n llm-chatbot --sort-by='.lastTimestamp'
```

## 🧪 Testing the Pipeline

### Test 1: Make a Code Change

```bash
# Edit app.py to change the title
sed -i 's/LLM Chatbot/LLM Chatbot v2/g' app.py

# Commit and push
git add app.py
git commit -m "Update application title"
git push origin main

# Watch for pipeline trigger
tkn pipelinerun list -n llm-chatbot -w
```

### Test 2: Check Image in Quay

1. Visit your Quay repository
2. Verify new image with commit SHA tag
3. Check image size and layers

### Test 3: Verify Application Update

```bash
# Check deployment image
oc get deployment llm-chatbot -n llm-chatbot -o jsonpath='{.spec.template.spec.containers[0].image}'

# Access application
curl -k https://$(oc get route llm-chatbot -n llm-chatbot -o jsonpath='{.spec.host}')
```

## 🐛 Troubleshooting

### Pipeline Issues

#### Pipeline Run Fails at git-clone

```bash
# Check git-clone task logs
tkn taskrun logs TASKRUN_NAME -n llm-chatbot

# Common issues:
# - Invalid Git URL
# - Private repository without credentials
# - Network connectivity issues
```

**Solution**: Verify Git URL and add SSH key if using private repository:
```bash
oc create secret generic git-ssh-key \
  --from-file=id_rsa=~/.ssh/id_rsa \
  -n llm-chatbot
```

#### Pipeline Run Fails at buildah

```bash
# Check buildah logs
tkn taskrun logs -f BUILDAH_TASKRUN -n llm-chatbot

# Common issues:
# - Insufficient permissions (needs privileged SCC)
# - Registry authentication failure
# - Resource limits exceeded
```

**Solution**: Verify SCC permissions:
```bash
oc adm policy add-scc-to-user privileged -z pipeline -n llm-chatbot
```

**Verify Quay credentials are properly formatted**:
```bash
# Check the secret exists and has correct type
oc get secret quay-auth-secret -n llm-chatbot -o yaml

# The secret should have:
# - type: kubernetes.io/dockerconfigjson
# - data: .dockerconfigjson field (base64 encoded)

# Decode to verify format (should show quay.io entry)
oc get secret quay-auth-secret -n llm-chatbot -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d | jq .
```

#### Image Push Fails

```bash
# Verify Quay credentials
oc get secret quay-auth-secret -n llm-chatbot -o yaml

# Test credentials manually
podman login quay.io -u YOUR_USERNAME
```

### Deployment Issues

#### Pods Not Starting

```bash
# Check pod status
oc get pods -n llm-chatbot

# Check pod logs
oc logs POD_NAME -n llm-chatbot

# Describe pod for events
oc describe pod POD_NAME -n llm-chatbot
```

#### ImagePullBackOff Error

```bash
# Verify image exists in Quay
# Check image pull secrets
oc get deployment llm-chatbot -n llm-chatbot -o jsonpath='{.spec.template.spec.imagePullSecrets}'

# If needed, link secret to service account
oc secrets link llm-chatbot quay-auth-secret --for=pull -n llm-chatbot
```

#### Application Not Accessible

```bash
# Check route
oc get route llm-chatbot -n llm-chatbot

# Check service endpoints
oc get endpoints llm-chatbot -n llm-chatbot

# Test from within cluster
oc run -it --rm debug --image=registry.access.redhat.com/ubi9/ubi:latest --restart=Never -- curl http://llm-chatbot:8501/_stcore/health
```

### Webhook Issues

#### Webhook Not Triggering Pipeline

```bash
# Check EventListener logs
oc logs -f deployment/el-llm-chatbot-listener -n llm-chatbot

# Verify webhook secret matches
oc get secret github-webhook-secret -n llm-chatbot -o jsonpath='{.data.secret}' | base64 -d

# Check GitHub webhook delivery
# Go to GitHub → Settings → Webhooks → Recent Deliveries
```

#### Pipeline Not Running After Webhook

```bash
# Check TriggerBinding and TriggerTemplate
oc get triggerbindings -n llm-chatbot
oc get triggertemplates -n llm-chatbot

# Review EventListener configuration
oc get eventlistener llm-chatbot-listener -n llm-chatbot -o yaml
```

## 📊 Monitoring and Logs

### Application Logs

```bash
# Follow application logs
oc logs -f deployment/llm-chatbot -n llm-chatbot

# View last 100 lines
oc logs deployment/llm-chatbot -n llm-chatbot --tail=100
```

### Pipeline Metrics

```bash
# List all pipeline runs with status
tkn pipelinerun list -n llm-chatbot

# Get pipeline run duration
tkn pipelinerun describe PIPELINERUN_NAME -n llm-chatbot
```

### Resource Usage

```bash
# Check pod resource usage
oc adm top pods -n llm-chatbot

# Check node resource usage
oc adm top nodes
```

## 🔄 Updates and Maintenance

### Updating the Application

```bash
# Make changes to code
vim app.py

# Commit and push (triggers automatic pipeline)
git add .
git commit -m "Your update message"
git push origin main
```

### Scaling the Application

```bash
# Scale to 3 replicas
oc scale deployment llm-chatbot --replicas=3 -n llm-chatbot

# Verify scaling
oc get pods -n llm-chatbot -w
```

### Rollback Deployment

```bash
# View rollout history
oc rollout history deployment/llm-chatbot -n llm-chatbot

# Rollback to previous version
oc rollout undo deployment/llm-chatbot -n llm-chatbot

# Rollback to specific revision
oc rollout undo deployment/llm-chatbot --to-revision=2 -n llm-chatbot
```

## 🧹 Cleanup

### Remove Application

```bash
# Delete all resources
oc delete namespace llm-chatbot

# Remove cluster-level RBAC (if not used by other apps)
oc delete clusterrolebinding pipeline-clusterrolebinding
oc delete clusterrole pipeline-clusterrole
```

## 📚 Additional Resources

- [OpenShift Pipelines Documentation](https://docs.openshift.com/pipelines/latest/)
- [Tekton Documentation](https://tekton.dev/docs/)
- [Buildah Documentation](https://buildah.io/)
- [Quay.io Documentation](https://docs.quay.io/)
- [RHEL UBI Documentation](https://developers.redhat.com/products/rhel/ubi)
- [Streamlit Documentation](https://docs.streamlit.io/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

[Your License Here]

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Contact: your-email@example.com

tkn pipeline start llm-chatbot-pipeline \
  -n llm-chatbot \
  --param git-url=https://github.com/pgustafs/llm-chatbot.git \
  --param git-revision=main \
  --param image-name=quay.io/pgustafs/llm-chatbot \
  --param image-tag=test-$(date +%s) \
  --param dockerfile-path=./Dockerfile \
  --param context-dir=. \
  --workspace name=source-workspace,claimName=pipeline-workspace-pvc \
  --workspace name=dockerconfig-secret,secret=quay-auth-secret \
  --serviceaccount pipeline \
  --showlog
