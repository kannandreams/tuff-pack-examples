# Container build context

Create a disposable context from an immutable pack reference:

```sh
docker login ghcr.io
./scripts/prepare-image-context.sh ghcr.io/OWNER/tuff-pack-examples@sha256:DIGEST image-context
docker build --build-arg CAPABILITY_PACK_REF=ghcr.io/OWNER/tuff-pack-examples@sha256:DIGEST -t example-agent:1.0.0 image-context
```

The helper pulls and verifies the pack, extracts its Claude target, and copies this Dockerfile into the new context. Docker's `COPY capability-runtime/ ./` turns the extracted files into a normal image filesystem layer.

The default Python base is only a transparent demonstration of the file layout and tool dependency; it does not install or start an agent runtime. In a real agent application, set `BASE_IMAGE` to the reviewed application/runtime base and retain its own `CMD` or add one in an application-specific Dockerfile.
