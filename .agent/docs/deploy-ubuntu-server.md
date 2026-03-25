# 🚀 Hướng Dẫn Deploy Ứng Dụng Gold Predictor Trên Ubuntu Server

> 📌 Tài liệu này hướng dẫn 2 cách triển khai: **Docker Compose** (khuyến nghị) và **cài đặt thủ công**.

---

## 📊 Tổng Quan Kiến Trúc

```
┌───────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client      │ ──► │  Nginx (port 80) │ ──► │ FastAPI (8000)  │
│   Browser     │     │  Serve Frontend  │     │ Backend API     │
└───────────────┘     │  Proxy /api/     │     │ + Scheduler     │
                      └─────────────────┘     └─────────────────┘
                                                      │
                                              ┌───────▼───────┐
                                              │   Database    │
                                              │ SQLite / PgSQL│
                                              └───────────────┘
```

| Thành phần | Công nghệ | Port |
|------------|-----------|------|
| Backend | FastAPI + Uvicorn (Python 3.12) | 8000 |
| Frontend | React + Vite → Nginx | 80 |
| Database | SQLite (dev) / PostgreSQL (prod) | - |
| Scheduler | APScheduler (tích hợp trong backend) | - |

---

## 📋 Yêu Cầu Hệ Thống

| Yêu cầu | Tối thiểu |
|----------|-----------|
| OS | Ubuntu 20.04+ (khuyến nghị 22.04 LTS) |
| RAM | 2 GB (khuyến nghị 4 GB vì có TensorFlow) |
| Disk | 10 GB trống |
| CPU | 2 cores |

---

# 🐳 CÁCH 1: Deploy Bằng Docker Compose (Khuyến Nghị)

## Bước 1: Cài đặt Docker và Docker Compose

```bash
# Cập nhật hệ thống
sudo apt update && sudo apt upgrade -y

# Cài đặt các package cần thiết
sudo apt install -y ca-certificates curl gnupg lsb-release

# Thêm Docker GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Thêm Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Cài đặt Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Cho phép user hiện tại chạy Docker mà không cần sudo
sudo usermod -aG docker $USER

# ⚠️ Logout rồi login lại để áp dụng group
```

Kiểm tra Docker đã cài thành công:
```bash
docker --version
docker compose version
```

## Bước 2: Đưa source code lên server

### Cách 2a: Clone từ Git (nếu có repository)
```bash
cd /opt
sudo mkdir -p gold-predictor && sudo chown $USER:$USER gold-predictor
git clone <YOUR_REPO_URL> gold-predictor
cd gold-predictor
```

### Cách 2b: Upload bằng SCP (nếu chưa có Git remote)
```bash
# Chạy trên máy Windows (PowerShell), thay YOUR_SERVER_IP bằng IP server
scp -r E:\Work\FinanceTrading\* user@YOUR_SERVER_IP:/opt/gold-predictor/
```

> ⚠️ **Lưu ý**: Không upload thư mục `venv/`, `node_modules/`, `.env` (những file này đã có trong `.gitignore`).

## Bước 3: Cấu hình Environment

```bash
cd /opt/gold-predictor

# Tạo file .env từ template
cp .env.example .env

# Chỉnh sửa file .env
nano .env
```

Các biến **bắt buộc** phải cấu hình:

```env
# ===== Application =====
APP_ENV=production
DEBUG=false

# ===== Database =====
# SQLite (đơn giản, không cần cài thêm gì)
DATABASE_URL=sqlite:///./data/gold_predictor.db

# Hoặc PostgreSQL (production, cần cài riêng)
# DATABASE_URL=postgresql://user:password@localhost:5432/gold_predictor

# ===== AI Reasoning =====
GEMINI_API_KEY=your_actual_gemini_api_key

# ===== API =====
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://YOUR_SERVER_IP,http://YOUR_DOMAIN
```

## Bước 4: Tạo thư mục data

```bash
mkdir -p data saved_models logs
```

## Bước 5: Build và chạy Docker Compose

```bash
# Build images
docker compose build

# Chạy ở chế độ nền (detached)
docker compose up -d
```

## Bước 6: Kiểm tra trạng thái

```bash
# Xem trạng thái containers
docker compose ps

# Xem logs
docker compose logs -f

# Chỉ xem logs backend
docker compose logs -f backend

# Kiểm tra health
curl http://localhost/health
```

**Kết quả mong đợi:**

| Container | Status |
|-----------|--------|
| gold-predictor-api | Up (healthy) |
| gold-predictor-web | Up |

Truy cập ứng dụng:
- 🌐 **Web UI**: `http://YOUR_SERVER_IP`
- 🔌 **API**: `http://YOUR_SERVER_IP/api/...`

## Các lệnh Docker Compose hữu ích

```bash
# Dừng ứng dụng
docker compose down

# Restart
docker compose restart

# Rebuild khi có code mới
docker compose down
docker compose build --no-cache
docker compose up -d

# Xem logs real-time
docker compose logs -f --tail=100
```

---

# 🔧 CÁCH 2: Cài Đặt Thủ Công (Không Dùng Docker)

## Bước 1: Cài đặt Python 3.12

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

## Bước 2: Cài đặt Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## Bước 3: Cài đặt Nginx

```bash
sudo apt install -y nginx
```

## Bước 4: Đưa source code lên server

(Tương tự Cách 1, Bước 2)

```bash
cd /opt
sudo mkdir -p gold-predictor && sudo chown $USER:$USER gold-predictor
# Clone hoặc SCP source code vào /opt/gold-predictor
```

## Bước 5: Cấu hình Backend

```bash
cd /opt/gold-predictor

# Tạo virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Cài đặt dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# Tạo file .env
cp .env.example .env
nano .env
# (Chỉnh sửa giống Cách 1, Bước 3)

# Tạo thư mục cần thiết
mkdir -p data saved_models logs
```

## Bước 6: Build Frontend

```bash
cd /opt/gold-predictor/frontend
npm ci
npm run build
# Kết quả: thư mục dist/ chứa static files
```

## Bước 7: Cấu hình Nginx

```bash
sudo nano /etc/nginx/sites-available/gold-predictor
```

Dán nội dung sau:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    root /opt/gold-predictor/frontend/dist;
    index index.html;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
```

Kích hoạt config:

```bash
# Tạo symlink
sudo ln -s /etc/nginx/sites-available/gold-predictor /etc/nginx/sites-enabled/

# Xóa default config (nếu không cần)
sudo rm -f /etc/nginx/sites-enabled/default

# Kiểm tra config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## Bước 8: Tạo Systemd Service cho Backend

```bash
sudo nano /etc/systemd/system/gold-predictor.service
```

Dán nội dung:

```ini
[Unit]
Description=Gold Predictor API
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/opt/gold-predictor/backend
Environment="PATH=/opt/gold-predictor/venv/bin"
EnvironmentFile=/opt/gold-predictor/.env
ExecStart=/opt/gold-predictor/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

# Logging
StandardOutput=append:/opt/gold-predictor/logs/backend.log
StandardError=append:/opt/gold-predictor/logs/backend-error.log

[Install]
WantedBy=multi-user.target
```

> ⚠️ **Lưu ý**: Thay `YOUR_USERNAME` bằng username thực tế trên server.

Kích hoạt service:

```bash
sudo systemctl daemon-reload
sudo systemctl start gold-predictor
sudo systemctl enable gold-predictor

# Kiểm tra trạng thái
sudo systemctl status gold-predictor
```

## Bước 9: Kiểm tra

```bash
# Backend health
curl http://localhost:8000/health

# Frontend qua Nginx
curl http://localhost

# Logs
journalctl -u gold-predictor -f
# hoặc
tail -f /opt/gold-predictor/logs/backend.log
```

---

# 🛡️ Cấu Hình Bổ Sung (Production)

## 1. Firewall

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS (nếu dùng SSL)
sudo ufw enable
```

## 2. SSL/HTTPS với Certbot (nếu có domain)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
# Certbot sẽ tự cấu hình Nginx
```

## 3. Cập nhật CORS_ORIGINS trong `.env`

```env
CORS_ORIGINS=https://YOUR_DOMAIN,http://YOUR_DOMAIN
```

---

# 🔄 Cập Nhật Ứng Dụng

## Với Docker Compose

```bash
cd /opt/gold-predictor
git pull origin main     # hoặc upload code mới

docker compose down
docker compose build --no-cache
docker compose up -d
```

## Với cài đặt thủ công

```bash
cd /opt/gold-predictor
git pull origin main

# Backend
source venv/bin/activate
pip install -r backend/requirements.txt
sudo systemctl restart gold-predictor

# Frontend
cd frontend
npm ci
npm run build
# Nginx tự serve static files mới, không cần restart
```

---

# ❓ Troubleshooting

| Vấn đề | Kiểm tra |
|--------|----------|
| Container không start | `docker compose logs backend` |
| Port 80 bị chiếm | `sudo lsof -i :80` và dừng process |
| Backend lỗi | `journalctl -u gold-predictor -n 50` |
| Frontend trắng trang | Kiểm tra Nginx error log: `sudo tail /var/log/nginx/error.log` |
| API trả 502 | Backend chưa chạy, kiểm tra service status |
| Không kết nối DB | Kiểm tra `DATABASE_URL` trong `.env` |
| TensorFlow chậm | Bình thường lần đầu start, RAM cần ≥ 4GB |
