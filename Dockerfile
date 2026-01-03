FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY requirements.txt pyproject.toml README.md MATHEMATICS.md SECURITY.md /app/
COPY src /app/src
COPY scripts /app/scripts
COPY tests /app/tests
COPY self_check.sh /app/self_check.sh

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Set Python path
ENV PYTHONPATH=/app/src

# Make self-check executable
RUN chmod +x /app/self_check.sh

# Default: run self-check in container
CMD ["/app/self_check.sh"]
