FROM python:3.11.10

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the Streamlit config first
COPY .streamlit/config.toml .streamlit/config.toml

# Copy the rest of the application
COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Use environment variables for configuration
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ENABLE_CORS=false
# The following will be overridden during deployment
ENV STREAMLIT_BROWSER_SERVER_ADDRESS=localhost
ENV STREAMLIT_BROWSER_SERVER_PORT=8501

ENTRYPOINT ["streamlit", "run", "legionella-overview-human-selection.py", "--server.port=8501", "--server.address=0.0.0.0"]