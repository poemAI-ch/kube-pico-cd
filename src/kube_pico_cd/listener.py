import json
import logging
import subprocess
import tempfile

import boto3
from kubernetes import client as kube_client
from kubernetes import config as kube_config

_logger = logging.getLogger(__name__)


class Listener:
    def __init__(self, settings):
        self.settings = settings
        self.kube_api = None

    def get_kube_api(self):
        if self.kube_api is not None:
            return self.kube_api

        # Initialize Kubernetes client
        try:
            kube_config.load_kube_config()
        except kube_config.config_exception.ConfigException:
            _logger.info("kubeconfig not found, loading in-cluster config")
            kube_config.load_incluster_config()

        self.kube_api = kube_client.CoreV1Api()

    # Function to get the current build timestamp from the ConfigMap
    def get_current_incremental_identifier(self):
        config_map_name = self.settings.config_map_name
        namespace = self.settings.namespace
        try:
            _logger.info(
                f"Getting build_incremental_identifier {self.settings.build_incremental_identifier} from ConfigMap {config_map_name} in namespace {namespace}"
            )
            config_map = self.get_kube_api().read_namespaced_config_map(
                config_map_name, self.settings.namespace
            )
            return int(config_map.data[self.settings.build_incremental_identifier])
        except Exception as e:
            _logger.warning(f"Failed to get current timestamp: {e}")
            return 0

    # Function to apply manifests using kubectl
    def apply_manifests(manifests):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmpfile:
            tmpfile.write(manifests.encode())
            tmpfile.flush()
            subprocess.run(["kubectl", "apply", "-f", tmpfile.name])

    def start(self):
        _logger.info(f"Using namespace {self.settings.namespace}")

        # Initialize AWS SQS resource
        sqs = boto3.resource("sqs")
        deploy_queue_name = self.settings.deploy_queue_name

        # read messages for an aws SQS queue
        queue = sqs.get_queue_by_name(QueueName=deploy_queue_name)
        idle_loop_counter = 0
        while True:
            if idle_loop_counter % 50 == 0:
                _logger.info(
                    f"Waiting for messages on queue {deploy_queue_name}, idle for {idle_loop_counter} loops"
                )
            idle_loop_counter += 1
            for message in queue.receive_messages(WaitTimeSeconds=20):
                idle_loop_counter = 0
                _logger.info(f"Received message {message.body}")

                body = json.loads(message.body)

                # Get the build timestamp and manifests from the message
                if self.settings.build_incremental_identifier in body["data"]:
                    self.settings.build_incremental_identifier = int(
                        body["data"][self.settings.build_incremental_identifier]
                    )
                    config_map_name = body["data"].get(
                        "CONFIG_MAP_NAME", self.settings.config_map_name
                    )
                    manifests = body["manifests"]

                    # Check if the received build timestamp is newer
                    current_incremental_identifier = (
                        self.get_current_incremental_identifier(config_map_name)
                    )
                    _logger.info(
                        f"Current incremental identfier {self.settings.build_incremental_identifier} is {current_incremental_identifier}, build identifier in message is {self.settings.build_incremental_identifier}"
                    )
                    if (
                        self.settings.build_incremental_identifier
                        >= current_incremental_identifier
                    ):
                        # Note: We will also apply the manifests if the build timestamp is equal to the current timestamp
                        # this is to handle the case where we crashed during the previous apply, but were already
                        # able to update the build timestamp in the ConfigMap
                        # the message would then stay in the queue, and we would get it again here after a restart
                        # and we will detect an equal build number, and apply the manifests again.
                        # This however requires that the upstream processes must make sure that equal build numbers have equal content

                        _logger.info(
                            f"Applying manifests for build {self.settings.build_incremental_identifier}"
                        )
                        self.apply_manifests(manifests)

                    else:
                        _logger.info(
                            f"Skipping build {self.settings.build_incremental_identifier} because it is older than the current timestamp {current_incremental_identifier}"
                        )
                else:
                    _logger.warning(
                        f"Message does not contain {self.settings.build_incremental_identifier}, skipping"
                    )

                message.delete()

                print(
                    f"Processed message with timestamp {self.settings.build_incremental_identifier}"
                )
