ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ARG CAPABILITY_PACK_REF
LABEL dev.tuffcli.capability-pack.ref=${CAPABILITY_PACK_REF}

WORKDIR /app
COPY capability-runtime/ ./
