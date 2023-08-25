# kube-pico-cd

`kube-pico-cd` is a lightweight and minimalist Continuous Deployment (CD) solution designed specifically for Kubernetes clusters. It aims to provide a straightforward and simple way to automate the deployment of applications within a Kubernetes environment without the complexity of larger CD platforms.

## Overview

The `kube-pico-cd` project is built with simplicity and ease of use in mind. It leverages existing tools such as AWS SQS and `kubectl`, and integrates them into a seamless workflow to apply application manifests to a Kubernetes cluster.

### How it Works

1. **GitHub Integration**: Application manifests are stored in a GitHub repository. A GitHub Action is triggered on commits to the main branch, concatenating all manifests into a single YAML file.
   
2. **SQS Queue**: The concatenated manifests, along with build information such as timestamps, are posted into an AWS SQS queue. This acts as a bridge between the code repository and the Kubernetes cluster.
   
3. **Deployment Listener**: Inside the Kubernetes cluster, a Python application runs in a container/pod, listening to the SQS queue. When a new message is received, the application checks the build timestamp and compares it to the current deployed version.
   
4. **Deployment Execution**: If the received build is newer, the Python application executes `kubectl apply` to update the deployed applications within the cluster. This approach ensures that only the latest manifests are applied.

5. **Version Tracking**: Build version information is maintained within a ConfigMap, enabling transparency and control over the deployed application versions.

## Features

- **Lightweight**: A minimal and focused solution that does one thing and does it well.
- **Easy to Configure**: With just a few environment variables, the system can be tailored to various use cases.
- **Integrated with GitHub**: Utilizes GitHub Actions to automate the deployment process.
- **AWS Integration**: Leverages AWS SQS for robust and scalable message handling between GitHub and the Kubernetes cluster.

