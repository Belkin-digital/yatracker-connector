FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY requirements.txt /app/
COPY src/ /app/src/
COPY scripts/ /app/scripts/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src

# Expose port for SSE transport
EXPOSE 8080

# Run the MCP server
CMD ["python3.11", "-m", "scripts.mcp_server"]
