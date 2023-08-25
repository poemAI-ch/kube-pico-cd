# Dockerfile for a python flask app
FROM python:3.11-buster

# Set the working directory to /app
WORKDIR /app

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY setup.cfg .
COPY setup.py .
RUN python3 -c "import configparser; c = configparser.ConfigParser(); c.read('setup.cfg'); print(c['options']['install_requires'])" | xargs pip install


COPY src ./src

RUN pip install --no-cache-dir .

# Run app.py when the container launches
CMD ["python", "-m","kube_pico_cd"]