import argparse
import json
import logging
import os
import subprocess
import tempfile

from kube_pico_cd.config import settings
from kube_pico_cd.deployer import push_to_deploy_queue
from kube_pico_cd.listener import Listener
from kube_pico_cd.manifest_generator import generate_manifest

_logger = logging.getLogger(__name__)


def start_listener(args):
    _logger.info(f"Start listenere")
    if hasattr(args, "namespace") and args.namespace is not None:
        settings.kube_namespace = args.namespace

    _logger.info("Start kube-pico-cd")
    listener = Listener(settings)
    listener.start()


def deploy(args):
    _logger.info(f"Deploy")
    manifests_root = args.manifests_root

    push_to_deploy_queue(args.deploy_queue_name, manifests_root=manifests_root)


def do_generate_manifest(args):
    _logger.info(f"Generate manifest")
    namespace = args.namespace
    deploy_queue_name = args.deploy_queue_name
    aws_region = args.aws_region
    manifest_file_name = args.manifest_file_name  # This will be None if not provided
    # Now call your generate_manifest function with these arguments
    generate_manifest(
        namespace, deploy_queue_name, aws_region, filename=manifest_file_name
    )


def main():
    parser = argparse.ArgumentParser(
        description="Command line of kube-pico-cd", prog="kube_pico_cd"
    )
    parser.set_defaults(func=start_listener)
    subparsers = parser.add_subparsers(
        title="sub-commands", description="valid sub-commands", help="additional help"
    )

    parser_listener = subparsers.add_parser("start_listener", help="Start the listener")
    parser_listener.add_argument(
        "--namespace",
        type=str,
        default="default-namespace",
        help="Kubernetes namespace (optional)",
    )

    parser_listener.set_defaults(func=start_listener)

    parser_deploy = subparsers.add_parser(
        "deploy",
        help="Deploy application by pushing manifests to queue. Concatenates all .yaml files in current directory and below",
    )
    parser_deploy.add_argument(
        "--deploy_queue_name",
        default=None,
        help="Name of the deployment queue (optional)",
    )
    parser_deploy.add_argument(
        "--manifests_root", default=None, help="Manifests root directory (optional)"
    )

    parser_deploy.set_defaults(func=deploy)

    parser_manifest = subparsers.add_parser(
        "generate_manifest",
        help="Generate a manifest file",
        usage="%(prog)s namespace deploy_queue_name aws_region [OPTIONS]",
    )
    parser_manifest.add_argument(
        "deploy_queue_name", help="Name of the deployment queue"
    )
    parser_manifest.add_argument("aws_region", help="AWS region")
    parser_manifest.add_argument(
        "--manifest_file_name", default=None, help="Manifest file name (optional)"
    )
    parser_manifest.set_defaults(func=do_generate_manifest)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
