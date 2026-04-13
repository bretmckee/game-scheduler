# syntax=docker/dockerfile:1
FROM postgres:18.1-alpine

# Install aws-cli and supercronic (container-native cron, no setpgid issues)
# supercronic inherits the container environment so no env-file workaround is needed.
RUN apk add --no-cache python3 py3-pip curl && \
    pip install --no-cache-dir --break-system-packages awscli && \
    ARCH=$(uname -m) && \
    case "${ARCH}" in \
        x86_64)  SUPERCRONIC_ARCH=amd64 ;; \
        aarch64) SUPERCRONIC_ARCH=arm64 ;; \
        *) echo "Unsupported arch: ${ARCH}"; exit 1 ;; \
    esac && \
    curl -fsSL \
        "https://github.com/aptible/supercronic/releases/download/v0.2.33/supercronic-linux-${SUPERCRONIC_ARCH}" \
        -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic

COPY docker/backup-entrypoint.sh /usr/local/bin/backup-entrypoint.sh
COPY docker/backup-script.sh /usr/local/bin/backup-script.sh
COPY docker/restore-script.sh /usr/local/bin/restore-script.sh

RUN chmod +x /usr/local/bin/backup-entrypoint.sh /usr/local/bin/backup-script.sh /usr/local/bin/restore-script.sh

ENTRYPOINT ["/usr/local/bin/backup-entrypoint.sh"]
