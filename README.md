# Novel CRM

Mini-CRM для обзвона B2B-контактов.

## Быстрый старт (локально)

```bash
# 1. Создать .env
cp .env.example .env
# Отредактировать .env

# 2. Запустить
docker compose up -d --build

# 3. Создать админа
docker compose exec backend python create_admin.py

# 4. Импортировать Excel
docker compose exec backend python migrate.py /path/to/file.xlsx

# Приложение доступно на http://localhost:3020
```

## Деплой на VPS

```bash
# 1. Скопировать на сервер
scp -r . root@80.87.111.142:/opt/novel-crm

# 2. На сервере
cd /opt/novel-crm
cp deploy/.env.production .env
# Заполнить .env

# 3. Получить SSL
sudo certbot --nginx -d novel.maxnov.ru

# 4. Добавить nginx конфиг
sudo cp deploy/nginx-novel.conf /etc/nginx/sites-available/novel.maxnov.ru
sudo ln -sf /etc/nginx/sites-available/novel.maxnov.ru /etc/nginx/sites-enabled/
sudo nginx -t && sudo nginx -s reload

# 5. Запустить
bash deploy/deploy.sh
```

## Стек

- **Backend:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16
- **Frontend:** React 18, TypeScript, Tailwind CSS, TanStack Table
- **Deploy:** Docker Compose, Nginx (host), Let's Encrypt

## Структура проекта

```
├── backend/          # FastAPI backend
│   ├── app/          # Application code
│   ├── migrate.py    # Excel import script
│   └── create_admin.py
├── frontend/         # React frontend
├── deploy/           # Deployment scripts
├── docker-compose.yml
└── README.md
```
