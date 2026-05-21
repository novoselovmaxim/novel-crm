#!/bin/bash

# База обзвона — запуск
DIR="$(cd "$(dirname "$0")" && pwd)"
PORT=8765
URL="http://127.0.0.1:$PORT"

# Проверяем python
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    osascript -e 'display alert "Python не найден" message "Установите Python 3 с python.org"'
    exit 1
fi

# Ставим зависимости если нет
$PY -c "import fastapi, uvicorn, openpyxl, pandas" 2>/dev/null || {
    osascript -e 'display notification \"Устанавливаю зависимости, подождите...\" with title \"База обзвона\"'
    $PY -m pip install fastapi uvicorn openpyxl pandas python-multipart --quiet
}

# Убиваем старый процесс на этом порту если есть
lsof -ti:$PORT | xargs kill -9 2>/dev/null

# Запускаем сервер в фоне
cd "$DIR"
$PY server-3.py &
SERVER_PID=$!

# Ждём пока поднимется
for i in $(seq 1 20); do
    sleep 0.3
    curl -s "$URL" &>/dev/null && break
done

# Открываем в Brave
open -a "Brave Browser" "$URL"

# Показываем уведомление
osascript -e 'display notification "База открыта в браузере" with title "База обзвона"'

# Ждём завершения сервера (Ctrl+C)
wait $SERVER_PID