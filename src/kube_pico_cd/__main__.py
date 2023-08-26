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
BUILD_INCREMENTAL_IDENTIFIER = "BUILD_TIMESTAMP"


def get_current_namespace():
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
            return f.read().strip()
    except IOError as e:
        _logger.warning(f"An IOError occurred while determining the namespace: {e}")
        return None


if "NAMESPACE" in os.environ:
    NAMESPACE = os.environ["NAMESPACE"]
else:
    NAMESPACE = get_current_namespace()

if NAMESPACE is None:
    raise Exception("Failed to determine namespace")

_logger.info(f"Using namespace {NAMESPACE}")

CONFIG_MAP_NAME = os.environ.get("CONFIG_MAP_NAME", "kube-pico-cd-build-info")


# Function to get the current build timestamp from the ConfigMap
def get_current_incremental_identifier(kube_api, config_map_name):
    try:
        _logger.info(
            f"Getting BUILD_INCREMENTAL_IDENTIFIER {BUILD_INCREMENTAL_IDENTIFIER} from ConfigMap {config_map_name} in namespace {NAMESPACE}"
        )
        config_map = kube_api.read_namespaced_config_map(config_map_name, NAMESPACE)
        return int(config_map.data[BUILD_INCREMENTAL_IDENTIFIER])
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
    idle_loop_counter = 0
    while True:
        if idle_loop_counter % 50 == 0:
            _logger.info(
                f"Waiting for messages on queue {KUBE_PICO_CD_DEPLOY_QUEUE_NAME}, idle for {idle_loop_counter} loops"
            )
        idle_loop_counter += 1
        for message in queue.receive_messages(WaitTimeSeconds=20):
            idle_loop_counter = 0
            _logger.info(f"Received message {message.body}")

            body = json.loads(message.body)

            # Get the build timestamp and manifests from the message
            if BUILD_INCREMENTAL_IDENTIFIER in body["data"]:
                build_incremental_identifier = int(
                    body["data"][BUILD_INCREMENTAL_IDENTIFIER]
                )
                config_map_name = body["data"].get("CONFIG_MAP_NAME", CONFIG_MAP_NAME)
                manifests = body["manifests"]

                # Check if the received build timestamp is newer
                current_incremental_identifier = get_current_incremental_identifier(
                    kube_api, config_map_name
                )
                _logger.info(
                    f"Current incremental identfier {BUILD_INCREMENTAL_IDENTIFIER} is {current_incremental_identifier}, build identifier in message is {build_incremental_identifier}"
                )
                if build_incremental_identifier >= current_incremental_identifier:
                    # Note: We will also apply the manifests if the build timestamp is equal to the current timestamp
                    # this is to handle the case where we crashed during the previous apply, but were already
                    # able to update the build timestamp in the ConfigMap
                    # the message would then stay in the queue, and we would get it again here after a restart
                    # and we will detect an equal build number, and apply the manifests again.
                    # This however requires that the upstream processes must make sure that equal build numbers have equal content

                    _logger.info(
                        f"Applying manifests for build {build_incremental_identifier}"
                    )
                    apply_manifests(manifests)

                else:
                    _logger.info(
                        f"Skipping build {build_incremental_identifier} because it is older than the current timestamp {current_incremental_identifier}"
                    )
            else:
                _logger.warning(
                    f"Message does not contain {BUILD_INCREMENTAL_IDENTIFIER}, skipping"
                )

            message.delete()

            print(f"Processed message with timestamp {build_incremental_identifier}")


if __name__ == "__main__":
    main()
