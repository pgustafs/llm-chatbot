# Use RHEL 10 UBI as base image
FROM registry.access.redhat.com/ubi10/ubi:latest

# Set metadata labels
LABEL maintainer="your-email@example.com" \
      name="streamlit-llm-chatbot" \
      version="1.0.0" \
      description="Streamlit chatbot for local LLM communication" \
      io.k8s.description="Streamlit-based chatbot application for OpenAI-compatible LLM APIs" \
      io.k8s.display-name="LLM Chatbot" \
      io.openshift.tags="streamlit,llm,chatbot,python"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/opt/app-root/src

# Install Python 3.12 and required system dependencies
RUN dnf install -y \
    python3.12 \
    python3.12-pip \
    python3.12-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf

# Create non-root user and app directory
RUN useradd -u 1001 -r -g 0 -d ${APP_HOME} -s /sbin/nologin \
    -c "Default Application User" default && \
    mkdir -p ${APP_HOME} && \
    chown -R 1001:0 ${APP_HOME} && \
    chmod -R g+rwX ${APP_HOME}

# Set working directory
WORKDIR ${APP_HOME}

# Copy requirements file
COPY --chown=1001:0 requirements.txt .

# Install Python dependencies
RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install -r requirements.txt

# Copy application code
COPY --chown=1001:0 app.py .

# Switch to non-root user
USER 1001

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
