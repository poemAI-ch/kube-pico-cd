import json
import logging
import os
import subprocess
import tempfile

import boto3
from kubernetes import client, config

LOG_FORMAT = (
    "%(asctime)s %(levelname)8s %(name)25s  %(filename)25s:%(lineno)-4d %(message)s"
)
_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

KUBE_PICO_CD_DEPLOY_QUEUE_NAME = os.environ["KUBE_PICO_CD_DEPLOY_QUEUE_NAME"]
CONFIG_MAP_NAME = "build-info"
if "CONFIG_MAP_NAME" in os.environ:
    CONFIG_MAP_NAME = os.environ["CONFIG_MAP_NAME"]

NAMESPACE = "default"
if "NAMESPACE" in os.environ:
    NAMESPACE = os.environ["NAMESPACE"]


# Function to get the current build timestamp from the ConfigMap
def get_current_timestamp(kube_api):
    try:
        config_map = kube_api.read_namespaced_config_map(CONFIG_MAP_NAME, NAMESPACE)
        return int(config_map.data["buildTimestamp"])
    except Exception as e:
        _logger.warning(f"Failed to get current timestamp: {e}")
        return 0


# Function to apply manifests using kubectl
def apply_manifests(manifests):
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmpfile:
        tmpfile.write(manifests.encode())
        tmpfile.flush()
        subprocess.run(["kubectl", "apply", "-f", tmpfile.name])


def main():
    # Initialize Kubernetes client
    try:
        config.load_kube_config()
    except config.config_exception.ConfigException:
        _logger.info("kubeconfig not found, loading in-cluster config")
        config.load_incluster_config()

    kube_api = client.CoreV1Api()

    # Initialize AWS SQS resource
    sqs = boto3.resource("sqs")

    # read messages for an aws SQS queue
    queue = sqs.get_queue_by_name(QueueName=KUBE_PICO_CD_DEPLOY_QUEUE_NAME)
    while True:
        _logger.info(f"Waiting for messages on queue {KUBE_PICO_CD_DEPLOY_QUEUE_NAME}")

        for message in queue.receive_messages(WaitTimeSeconds=20):
            _logger.info(f"Received message {message.body}")

            body = json.loads(message.body)

            # Get the build timestamp and manifests from the message
            build_timestamp = int(body["data"]["buildTimestamp"])
            manifests = body["manifests"]

            # Check if the received build timestamp is newer
            current_timestamp = get_current_timestamp(kube_api)
            if build_timestamp > current_timestamp:
                _logger.info(f"Applying manifests for build {build_timestamp}")
                apply_manifests(manifests)
            else:
                _logger.info(
                    f"Skipping build {build_timestamp} because it is older than the current timestamp {current_timestamp}"
                )

            message.delete()

            print(f"Processed message with timestamp {build_timestamp}")


if __name__ == "__main__":
    main()
