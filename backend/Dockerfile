FROM ubuntu:24.04

WORKDIR /app

RUN apt-get update && apt-get install -y \
  libcurl4 \
  libcurl3-gnutls \
  libstdc++6 \
  build-essential \
  python3 \
  python3-pip \
  python3-venv

RUN python3 -m venv /opt/venv

COPY backend/requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Make all scripts in the executables directory executable
RUN chmod +x executables/*

# Create a user 'appuser'
RUN useradd -m appuser

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to this user
USER appuser

EXPOSE 5000

CMD ["/opt/venv/bin/python", "ShashGuruBackend.py"]
