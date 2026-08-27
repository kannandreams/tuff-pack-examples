# Publishing packs and using them in container images

OCI is a distribution standard used by registries such as GHCR and Amazon ECR. It can carry more than runnable container images. Tuff stores the exact `.tuffpack` bytes as a generic OCI artifact with Tuff-specific media types.

That distinction matters: a Tuff pack is not a Docker image and its OCI layer is not a Docker root-filesystem layer. Dockerfiles cannot write `FROM ghcr.io/example/packs:csv-data-quality-v1.0.0` or `COPY --from=<pack-reference>`. The safe bridge is a Tuff operation:

```text
OCI registry
    |
    | tuff pack pull (prefer an immutable @sha256 reference)
    v
verified .tuffpack
    |
    | tuff pack extract --agent claude
    v
Claude-native files
    |
    | Docker COPY
    v
agent application image
```

## GHCR release

```sh
docker login ghcr.io
./scripts/build.sh .work/artifacts
tuff pack push .work/artifacts/csv-data-quality-1.0.0.tuffpack ghcr.io/OWNER/tuff-pack-examples:csv-data-quality-v1.0.0 --json
```

The response includes two digests. The artifact digest identifies the `.tuffpack` bytes. The OCI manifest digest identifies the registry envelope and is used in the returned immutable `reference`. Record both in release metadata; deploy using the digest reference.

## Amazon ECR release

Create the repository once, authenticate Docker, then use the same Tuff command:

```sh
aws ecr create-repository --repository-name tuff-pack-examples
aws ecr get-login-password --region eu-west-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com
tuff pack push .work/artifacts/csv-data-quality-1.0.0.tuffpack ACCOUNT_ID.dkr.ecr.eu-west-1.amazonaws.com/tuff-pack-examples:csv-data-quality-v1.0.0 --json
```

Tuff reads credentials written by `docker login`. The ECR authentication token expires, so CI should authenticate immediately before pushing or pulling.

## Multi-stage Docker build

Pull and extract before invoking Docker, or do it in a build stage that has a pinned Tuff binary. A simple pre-build flow is easier to audit:

```sh
tuff pack pull "$TUFF_PACK_REF" --output .work/artifacts/capability.tuffpack
tuff pack verify .work/artifacts/capability.tuffpack
tuff pack extract .work/artifacts/capability.tuffpack --agent claude --output .work/artifacts/capability-runtime
docker build --build-arg CAPABILITY_PACK_REF="$TUFF_PACK_REF" -t example-agent:1.0.0 .
```

```dockerfile
FROM python:3.12-slim
ARG CAPABILITY_PACK_REF
LABEL dev.tuffcli.capability-pack.ref=$CAPABILITY_PACK_REF
WORKDIR /app
COPY capability-runtime/.claude/ .claude/
COPY capability-runtime/.mcp.json .mcp.json
COPY app/ .
CMD ["python", "agent.py"]
```

The label makes the capability identity inspectable on the final application image. The application runtime still has to support the copied Claude configuration and Python 3.9+ tool dependency. For an AWS Lambda or AgentCore deployment, the Tuff step belongs in CI or the image build; Tuff does not need to run in the production process unless you deliberately choose runtime retrieval.

## Promotion without rebuilding

Prefer promoting the same immutable pack digest between development, staging, and production rather than rebuilding from source in each environment. Registry-specific copying or a controlled pull-and-push can mirror the object. Verify after every copy and retain the digest reference in deployment metadata.

OCI transport detects changed bytes. It does not prove who published them. Tuff 0.1.4 does not yet enforce signatures or attestations, so registry permissions, protected release workflows, and digest pinning are still part of the trust model.
