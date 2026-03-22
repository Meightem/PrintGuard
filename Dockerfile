ARG PYTHON_VERSION=3.11-slim-bookworm
ARG TORCH_VERSION=2.10.0

FROM python:${PYTHON_VERSION} AS model-builder

ARG TORCH_VERSION

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY printguard ./printguard
COPY scripts/download_model.py ./scripts/download_model.py
COPY constraints.lock ./constraints.lock

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --constraint constraints.lock ".[model-build]" \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==${TORCH_VERSION}

RUN python ./scripts/download_model.py --output-dir /opt/printguard/model

FROM python:${PYTHON_VERSION} AS package-builder

WORKDIR /app

COPY pyproject.toml README.md ./
COPY printguard ./printguard

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir build \
 && python -m build --wheel --outdir /dist

FROM python:${PYTHON_VERSION} AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg libgl1 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --system printguard \
 && useradd --system --gid printguard --create-home --home-dir /home/printguard printguard

WORKDIR /app

COPY constraints.lock ./constraints.lock
COPY --from=package-builder /dist /tmp/dist
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --constraint constraints.lock /tmp/dist/printguard-*.whl \
 && pip uninstall --yes setuptools wheel \
 && rm -rf /tmp/dist

COPY --from=model-builder /opt/printguard/model /opt/printguard/model

ENV MODEL_PATH=/opt/printguard/model/model.onnx
ENV MODEL_OPTIONS_PATH=/opt/printguard/model/opt.json
ENV PROTOTYPES_PATH=/opt/printguard/model/prototypes.npz
ENV HEALTH_PATH=/tmp/printguard-health.json
ENV HEALTH_STALE_AFTER_SECONDS=180

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD ["printguard-healthcheck"]

USER printguard

ENTRYPOINT ["printguard"]
