import boto3
import json
from kubernetes import client, config
import subprocess
import tempfile
import os
import logging

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
    # Initialize boto3 SQS client
    sqs = boto3.client("sqs")
    
    # Initialize Kubernetes client
    config.load_kube_config()
    kube_api = client.CoreV1Api()




    sqs = boto3.resource("sqs")

    # read messages for an aws SQS queue
    queue = sqs.get_queue_by_name(QueueName=KUBE_PICO_CD_DEPLOY_QUEUE_NAME)
    while True:
        _logger.info(f"Waiting for messages on queue {KUBE_PICO_CD_DEPLOY_QUEUE_NAME}")
        for message in queue.receive_messages(WaitTimeSeconds=20):
            _logger.info(f"Received message {message.body}")
            page_key_list = json.loads(message.body)
            for page_keys in page_key_list:
                paragrapher.extract_paragraphs(page_keys)
            message.delete()
            _logger.info(f"Deleted message {message.body}")
            if args.single:
                return


    # Poll SQS queue for messages
    while True:
        response = sqs.receive_message(QueueUrl=SQS_QUEUE_URL, MaxNumberOfMessages=1)

        messages = response.get("Messages")
        if messages:
            message = messages[0]
            body = json.loads(message["Body"])

            # Get the build timestamp and manifests from the message
            build_timestamp = int(body["data"]["buildTimestamp"])
            manifests = body["manifests"]

            # Check if the received build timestamp is newer
            if build_timestamp > get_current_timestamp(kube_api):
                apply_manifests(manifests)

                # Delete the processed message from the queue
                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL, ReceiptHandle=message["ReceiptHandle"]
                )

            print(f"Processed message with timestamp {build_timestamp}")


if __name__ == "__main__":
    main()
