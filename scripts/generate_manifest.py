import argparse

import yaml


def generate_manifest(namespace, queue_name, aws_region):
    service_account_name = f"kube-pico-cd-{namespace}-edit"

    manifest = {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            {
                "apiVersion": "v1",
                "kind": "ServiceAccount",
                "metadata": {"name": service_account_name, "namespace": namespace},
            },
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {
                    "name": f"{namespace}-namespace-edit",
                    "namespace": namespace,
                },
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": service_account_name,
                        "namespace": namespace,
                    }
                ],
                "roleRef": {
                    "kind": "ClusterRole",
                    "name": "edit",
                    "apiGroup": "rbac.authorization.k8s.io",
                },
            },
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {
                    "name": f"kube-pico-cd-{namespace}",
                    "namespace": namespace,
                },
                "spec": {
                    "replicas": 1,
                    "selector": {"matchLabels": {"app": "kube-pico-cd"}},
                    "template": {
                        "metadata": {"labels": {"app": "kube-pico-cd"}},
                        "spec": {
                            "serviceAccountName": service_account_name,
                            "containers": [
                                {
                                    "name": "kube-pico-cd-container",
                                    "image": "empoemai/kube-pico-cd:v0.0.1",
                                    "env": [
                                        {
                                            "name": "KUBE_PICO_CD_DEPLOY_QUEUE_NAME",
                                            "value": queue_name,
                                        },
                                        {
                                            "name": "AWS_DEFAULT_REGION",
                                            "value": aws_region,
                                        },
                                    ],
                                }
                            ],
                        },
                    },
                },
            },
        ],
    }

    with open(f"kube-pico-cd-{namespace}.yaml", "w") as outfile:
        yaml.dump(manifest, outfile, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Kubernetes manifest for kube-pico-cd"
    )
    parser.add_argument("namespace", type=str, help="Kubernetes namespace")
    parser.add_argument("queue_name", type=str, help="AWS SQS queue name")
    parser.add_argument("aws_region", type=str, help="AWS region")

    args = parser.parse_args()
    generate_manifest(args.namespace, args.queue_name, args.aws_region)
