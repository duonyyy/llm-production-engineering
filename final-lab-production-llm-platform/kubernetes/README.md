# Kubernetes reference boundary

Kubernetes is a `REFERENCE_MODE` deployment boundary. This directory will
compose reviewed namespace, ServiceAccount, RBAC, Service, NetworkPolicy,
probe, resource-limit and monitoring manifests from the lab contracts.

No live cluster is configured by this scaffold. A manifest that parses is only
static validation; it does not prove scheduling, GPU allocation, monitoring,
autoscaling or failure recovery. Do not add broad RBAC, mounted kubeconfigs,
Secrets readers, host paths, Docker sockets or `pods/exec` to make a demo work.
