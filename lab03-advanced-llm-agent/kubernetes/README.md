# Kubernetes security boundary

These manifests are intentionally limited to namespace, Role-based
read-only observation and network policy. They do not invent a vLLM, LMCache,
NIXL or KServe CRD. The current Lab 03 deliverable is validated on a manifest
and schema level; it does not claim a live Kubernetes deployment.

The `lab03-observer` ServiceAccount can only `get`, `list` and `watch` bounded
workload metadata. It cannot read Secrets, use `pods/exec`, or create, update
or delete resources. A token that authenticates the MCP caller would still
need authorization at the gateway and tool layer.

Apply only in a deliberate cluster:

```text
kubectl apply -f namespace.yaml
kubectl apply -f rbac.yaml -f network-policy.yaml
kubectl auth can-i --as=system:serviceaccount:lab03:lab03-observer list pods -n lab03
kubectl auth can-i --as=system:serviceaccount:lab03:lab03-observer get secrets -n lab03
```

Expected checks are `yes` for the first command and `no` for the second. The
network policy assumes a standard `kube-dns` label; verify the cluster's DNS
labels before applying it. Default-deny policies can break workloads when
their legitimate egress is not added explicitly.
