# Dockerfile for a python flask app
FROM python:3.11-buster

# Set the working directory to /app
WORKDIR /app

# Install kubectl
RUN apt-get update && \
    apt-get install -y apt-transport-https curl && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/local/bin/

RUN /usr/local/bin/python -m pip install --upgrade pip
COPY entrypoint.sh /entrypoint.sh

COPY setup.cfg .
COPY setup.py .
RUN python3 -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires'])" | xargs pip install


COPY src ./src

RUN pip install --no-cache-dir .

ENTRYPOINT ["/entrypoint.sh"]
