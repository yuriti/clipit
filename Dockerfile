# SMTV in Docker (stage 21): the second way to install, next to `uv tool install`. The same page as in SMTV's window,
# opened in a browser on the host. Built from this repository:
#   docker compose up -d --build            # smtv-vodcut: SMTV and VodCut
#   docker build --build-arg TOOLS="vodcut" -t smtv-all .    # smtv-all: every plugin (today the same list)
# Your own plugin: an image of your own on top, `FROM <this image>` + `RUN pip install <your plugin>`.
#
# Inside: Python, ffmpeg with libass (captions), fonts, tini. Not inside: yt-dlp (links go through the StreamMoment
# account; «Download on this computer» is for an image of your own, `pip install yt-dlp`), the Codex and Claude Code CLIs
# (not offered in the container), speech models (downloaded into the data volume when first needed).
FROM python:3.12-slim-trixie

ARG TOOLS=vodcut

# ffmpeg from Debian is built with libass (the `ass` filter burns the captions), libx264 and NVENC; tini stops the
# server and its jobs properly on `docker stop`; fontconfig + DejaVu: a fallback for letters the bundled Montserrat lacks.
RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg tini fontconfig fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/* \
 && ffmpeg -hide_banner -filters | grep -qE '^ ... ass ' \
 && useradd --create-home --uid 1000 --shell /usr/sbin/nologin smtv \
 && mkdir -p /data && chown smtv:smtv /data

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# The packages from this folder, not from PyPI: the image is the code it was built from. Only the core, the gateway
# and the plugins named in TOOLS; no keychain package (keys are encrypted in the data volume, stage 19).
COPY packages /src/packages
RUN pip install /src/packages/smtv-core /src/packages/smtv $(for t in $TOOLS; do echo /src/packages/$t; done) \
 && rm -rf /src

# SMTV_DOCKER: the page asks for the access key, listens on every address in the container, does not update itself.
# SMTV_HOME: settings, keys, speech models, clips — all in the volume; the caches of model downloads too.
# SMTV_LOCAL_HOST: Ollama, LM Studio and the others run on the host.
ENV SMTV_DOCKER=1 \
    SMTV_HOME=/data \
    SMTV_LOCAL_HOST=host.docker.internal \
    SMTV_NO_SHORTCUT=1 \
    XDG_CACHE_HOME=/data/cache \
    HF_HOME=/data/cache/huggingface

USER smtv
WORKDIR /data
VOLUME ["/data"]
EXPOSE 8642

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8642/healthz', timeout=4).status == 200 else 1)"]

ENTRYPOINT ["tini", "--"]
CMD ["smtv", "serve", "--no-browser"]
