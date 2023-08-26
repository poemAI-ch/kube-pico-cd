import json
import logging
import os
import time
from pathlib import Path

import boto3
import yaml

_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Function to concatenate YAML files
def concatenate_yamls():
    concatenated_yaml = ""
    for path in Path(".").rglob("*.yaml"):
        with open(path, "r") as file:
            concatenated_yaml += file.read() + "\n---\n"
    return concatenated_yaml


# Function to create ConfigMap
def create_config_map(build_info):
    config_map = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "build-info"},
        "data": build_info,
    }

    return yaml.dump(config_map)


def main():
    concatenated_yaml = concatenate_yamls()

    build_time_stamp = os.getenv("BUILD_TIMESTAMP")
    if build_time_stamp is None or build_time_stamp == "":
        build_time_stamp = str(int(time.time()))

    build_info = {
        "buildTimestamp": build_time_stamp,
        "BRANCH_NAME": os.getenv("BRANCH_NAME", "undefined"),
        "COMMIT_HASH": os.getenv("COMMIT_HASH", "undefined"),
        "TAG_NAME": os.getenv("TAG_NAME", "undefined"),
    }

    config_map_yaml = create_config_map(build_info)
    full_yaml = concatenated_yaml + config_map_yaml

    message_body = {"data": build_info, "manifests": full_yaml}

    sqs = boto3.resource("sqs")
    kube_pico_cd_deploy_queue_name = os.getenv("KUBE_PICO_CD_DEPLOY_QUEUE_NAME")
    _logger.info(f"KUBE_PICO_CD_DEPLOY_QUEUE_NAME: {kube_pico_cd_deploy_queue_name}")

    if kube_pico_cd_deploy_queue_name is None or kube_pico_cd_deploy_queue_name == "":
        raise Exception(
            "KUBE_PICO_CD_DEPLOY_QUEUE_NAME environment variable is not set"
        )

    deploy_queue = sqs.get_queue_by_name(QueueName=kube_pico_cd_deploy_queue_name)

    message_body_text = json.dumps(message_body)
    deploy_queue.send_message(MessageBody=message_body_text)
    _logger.info(
        f"Sent message for build {build_info['buildTimestamp']} to queue {kube_pico_cd_deploy_queue_name}"
    )


if __name__ == "__main__":
    main()
