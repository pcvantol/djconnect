# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ARG BASE_IMAGE=python:3.12-slim
ARG VERIFICATION_RUNTIME_VERSION=0.2.0
ARG RELEASE_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="DJConnect Verification Platform Runtime"
LABEL org.opencontainers.image.description="Generic DJConnect verification engine runtime without repository scenario catalogs"
LABEL org.opencontainers.image.version="${VERIFICATION_RUNTIME_VERSION}"
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.base.name="${BASE_IMAGE}"
LABEL org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/opt/djconnect-verification-runtime
ENV DJCONNECT_VERIFICATION_RUNTIME_VERSION=${VERIFICATION_RUNTIME_VERSION}
ENV DJCONNECT_VERIFICATION_RELEASE_SHA=${RELEASE_SHA}

WORKDIR /workspace

COPY docker/verification-platform/requirements.txt /tmp/verification-platform-requirements.txt
COPY tools/verification /opt/djconnect-verification-runtime/tools/verification

RUN python -m pip install --no-cache-dir -r /tmp/verification-platform-requirements.txt \
    && python -m compileall -q /opt/djconnect-verification-runtime/tools/verification

ENTRYPOINT ["python", "-m", "tools.verification.cli"]
CMD ["--help"]
