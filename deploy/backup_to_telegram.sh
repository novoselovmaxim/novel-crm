#!/bin/bash
# Daily backup: database dump + .env config → Telegram (split large files)
set -e

# Load environment variables from .env
ENV_FILE_PATH="/opt/novel-crm/.env"
if [ -f "${ENV_FILE_PATH}" ]; then
    set -a
    source "${ENV_FILE_PATH}"
    set +a
fi

BOT_TOKEN="${TG_BACKUP_BOT_TOKEN:-}"
CHAT_ID="${TG_BACKUP_CHAT_ID:-}"
DB_NAME="${DB_NAME:-novel_crm}"
DB_USER="${DB_USER:-novel}"
BACKUP_DIR="/opt/novel-crm/backups"
DATE=$(date +%Y%m%d_%H%M%S)
MAX_PART_SIZE=45M  # Safe margin under Telegram's 50MB limit

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup..."

# 1) Database dump
DB_FILE="${BACKUP_DIR}/novel_crm_${DATE}.sql.gz"
docker exec novel_crm_postgres pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${DB_FILE}"
DB_SIZE=$(du -h "${DB_FILE}" | cut -f1)
echo "[$(date)] DB dump: ${DB_FILE} (${DB_SIZE})"

# 2) .env config backup
ENV_BACKUP_FILE="${BACKUP_DIR}/env_${DATE}.txt"
cp /opt/novel-crm/.env "${ENV_BACKUP_FILE}"
ENV_SIZE=$(du -h "${ENV_BACKUP_FILE}" | cut -f1)
echo "[$(date)] .env backup: ${ENV_BACKUP_FILE} (${ENV_SIZE})"

# 3) docker-compose.yml backup
COMPOSE_FILE="${BACKUP_DIR}/docker-compose_${DATE}.yml"
cp /opt/novel-crm/docker-compose.yml "${COMPOSE_FILE}"

# 4) Send to Telegram
if [ -n "${BOT_TOKEN}" ] && [ -n "${CHAT_ID}" ]; then
    # Split DB dump if larger than MAX_PART_SIZE
    if [ $(stat -c%s "${DB_FILE}") -gt $((45 * 1024 * 1024)) ]; then
        echo "[$(date)] Splitting DB dump into ${MAX_PART_SIZE} parts..."
        split -b "${MAX_PART_SIZE}" -d -a 3 "${DB_FILE}" "${DB_FILE}.part."
        PART_NUM=1
        for part in "${DB_FILE}".part.*; do
            RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
                -F chat_id="${CHAT_ID}" \
                -F document=@"${part}" \
                -F caption="🗄️ DB Backup $(date '+%Y-%m-%d %H:%M') | ${DB_SIZE} | ${DB_NAME} (part ${PART_NUM})")
            if echo "${RESPONSE}" | grep -q '"ok":true'; then
                echo "[$(date)] DB part ${PART_NUM} sent to Telegram"
            else
                echo "[$(date)] ERROR sending part ${PART_NUM}: ${RESPONSE}"
            fi
            PART_NUM=$((PART_NUM + 1))
        done
        rm -f "${DB_FILE}".part.*
    else
        RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
            -F chat_id="${CHAT_ID}" \
            -F document=@"${DB_FILE}" \
            -F caption="🗄️ DB Backup $(date '+%Y-%m-%d %H:%M') | ${DB_SIZE} | ${DB_NAME}")
        if echo "${RESPONSE}" | grep -q '"ok":true'; then
            echo "[$(date)] DB dump sent to Telegram"
        else
            echo "[$(date)] ERROR sending DB dump: ${RESPONSE}"
        fi
    fi

    # Send .env (WARNING: contains secrets!)
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F chat_id="${CHAT_ID}" \
        -F document=@"${ENV_BACKUP_FILE}" \
        -F caption="⚙️ .env config $(date '+%Y-%m-%d %H:%M') | ${ENV_SIZE}")
    if echo "${RESPONSE}" | grep -q '"ok":true'; then
        echo "[$(date)] .env sent to Telegram"
    else
        echo "[$(date)] ERROR sending .env: ${RESPONSE}"
    fi

    # Send docker-compose.yml
    RESPONSE=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendDocument" \
        -F chat_id="${CHAT_ID}" \
        -F document=@"${COMPOSE_FILE}" \
        -F caption="🐳 docker-compose.yml $(date '+%Y-%m-%d %H:%M')")
    if echo "${RESPONSE}" | grep -q '"ok":true'; then
        echo "[$(date)] docker-compose.yml sent to Telegram"
    else
        echo "[$(date)] ERROR sending docker-compose.yml: ${RESPONSE}"
    fi
else
    echo "[$(date)] Telegram not configured (TG_BACKUP_BOT_TOKEN or TG_BACKUP_CHAT_ID not set), skipping send"
fi

# 5) Copy as latest
cp "${DB_FILE}" "${BACKUP_DIR}/novel_crm_latest.sql.gz"

# 6) Keep only last 7 days of local files
find "${BACKUP_DIR}" -name "novel_crm_*.sql.gz" -mtime +7 -delete
find "${BACKUP_DIR}" -name "env_*.txt" -mtime +7 -delete
find "${BACKUP_DIR}" -name "docker-compose_*.yml" -mtime +7 -delete

echo "[$(date)] Backup complete"
