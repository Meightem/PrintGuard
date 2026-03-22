FROM python:3.11-slim-bookworm AS model-builder

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-build.txt ./requirements-build.txt
COPY scripts/download_model.py ./scripts/download_model.py

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements-build.txt \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.7.0

RUN python ./scripts/download_model.py --output-dir /opt/printguard/model

FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg libgl1 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml README.md ./
COPY printguard ./printguard
RUN pip install --no-cache-dir --no-deps .

COPY --from=model-builder /opt/printguard/model /opt/printguard/model

ENV MODEL_PATH=/opt/printguard/model/model.onnx
ENV MODEL_OPTIONS_PATH=/opt/printguard/model/opt.json
ENV PROTOTYPES_PATH=/opt/printguard/model/prototypes/cache/prototypes.pkl

ENTRYPOINT ["printguard"]
