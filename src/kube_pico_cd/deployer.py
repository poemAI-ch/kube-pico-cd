import json
import logging
import os
import time
from pathlib import Path

import boto3
import yaml
from kube_pico_cd.config import settings

_logger = logging.getLogger(__name__)


# Function to concatenate YAML files
def concatenate_yamls(manifests_root):
    concatenated_yaml = ""

    paths = []
    for path in Path(manifests_root).rglob("*.yaml"):
        with open(path, "r") as file:
            concatenated_yaml += file.read() + "\n---\n"

        paths.append(path)
    if len(paths) == 0:
        full_path = os.path.abspath(manifests_root)
        raise Exception(f"No YAML files found in {manifests_root} ({full_path})")
    else:
        _logger.info(f"Concatenated YAML files: {[str(p) for p in paths]}")
    return concatenated_yaml


# Function to create ConfigMap
def create_config_map(build_info):
    config_map = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": settings.config_map_name},
        "data": build_info,
    }

    return yaml.dump(config_map)


def push_to_deploy_queue(deploy_queue_name=None, manifests_root=None):
    if manifests_root is None:
        manifests_root = "."

    if deploy_queue_name is None:
        if "deploy_queue_name" in settings:
            deploy_queue_name = settings.deploy_queue_name
            _logger.info(f"Using queue name from settings: {deploy_queue_name}")

    if deploy_queue_name is None:
        raise Exception(
            "deploy_queue_name is neither given as argument nor set in settings"
        )

    concatenated_yaml = concatenate_yamls(manifests_root)

    build_time_stamp = os.getenv("BUILD_TIMESTAMP", str(int(time.time())))

    build_info = {
        "BUILD_TIMESTAMP": build_time_stamp,
        "buildTimestamp": build_time_stamp,
        "BRANCH_NAME": os.getenv("BRANCH_NAME", "undefined"),
        "COMMIT_HASH": os.getenv("COMMIT_HASH", "undefined"),
        "TAG_NAME": os.getenv("TAG_NAME", "undefined"),
        "GITHUB_RUN_NUMBER": os.getenv("GITHUB_RUN_NUMBER", "undefined"),
        "CONFIG_MAP_NAME": settings.config_map_name,
    }

    config_map_yaml = create_config_map(build_info)
    _logger.info(f"ConfigMap YAML:\n{config_map_yaml}")
    full_yaml = concatenated_yaml + config_map_yaml

    message_body = {"data": build_info, "manifests": full_yaml}

    sqs = boto3.resource("sqs")
    _logger.info(f"KUBE_PICO_CD_DEPLOY_QUEUE_NAME: {deploy_queue_name}")

    if deploy_queue_name is None or deploy_queue_name == "":
        raise Exception(
            "KUBE_PICO_CD_DEPLOY_QUEUE_NAME environment variable is not set"
        )

    deploy_queue = sqs.get_queue_by_name(QueueName=deploy_queue_name)

    message_body_text = json.dumps(message_body)
    deploy_queue.send_message(MessageBody=message_body_text)
    _logger.info(
        f"Sent message for build {build_info['buildTimestamp']} to queue {deploy_queue_name}"
    )
