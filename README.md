# LiteLLM Proxy — OpenCode Zen Free Models

Dockerized [LiteLLM Proxy](https://litellm.vercel.app/) tích hợp **7 model free** từ **OpenCode Zen v1**, kèm Postgres (config storage) và Prometheus (monitoring).

## 📋 Yêu cầu hệ thống

- **Docker Desktop** cho Windows (đã cài WSL2 backend)
- **WSL 2** (tuỳ chọn — nếu muốn gọi API từ Linux CLI)
- **Python 3.10+** (chỉ cần nếu chạy script `update_models.py`)

## 🏗 Kiến trúc

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  Client App  │────▶│  LiteLLM Proxy   │────▶│  OpenCode Zen    │
│  (curl/Grok) │     │  (localhost:4000) │     │  /zen/v1 (free)  │
└──────────────┘     └────────┬─────────┘     └──────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    Postgres DB    │
                    │  (config store)   │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │    Prometheus     │
                    │  (monitoring)     │
                    └───────────────────┘
```

## 🚀 Quick Start

### 1. Khởi động hệ thống

```bash
cd D:\CODE\litellm
docker compose up -d
```

Lệnh này sẽ khởi động 3 containers:
| Container | Port | Mục đích |
|---|---|---|
| `litellm-litellm-1` | `:4000` | Proxy chính |
| `litellm_db` | `:5432` | Postgres database |
| `litellm-prometheus-1` | `:9090` | Monitoring |

⏱ Sau khoảng **40s** (start_period), container sẽ chuyển sang trạng thái `healthy`.

### 2. Kiểm tra hoạt động

```bash
# Health check
curl http://localhost:4000/health/liveliness
# → "I'm alive!"

# Danh sách model
curl http://localhost:4000/model/info -H 'Authorization: Bearer sk-1234'

# Chat completion — thử với model free
curl http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron-3-ultra-free","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}'
```

### 3. Dừng hệ thống

```bash
docker compose down
# Xoá luôn volumes (cảnh báo: mất dữ liệu Postgres):
docker compose down -v
```

## 📁 Cấu trúc dự án

```
D:\CODE\litellm\
├── config.yaml            # Cấu hình LiteLLM (model list + general settings)
├── docker-compose.yml     # Docker Compose orchestration
├── .env                   # Biến môi trường (API keys)
├── opencode-models.json   # Danh sách model OpenCode Zen (định nghĩa tĩnh)
├── update_models.py       # Script tự động dò model free từ API
├── prometheus.yml         # Cấu hình Prometheus monitoring
├── AGENTS.md              # Hướng dẫn AI coding agents
└── README.md              # Tài liệu này
```

## ⚙️ Cấu hình chi tiết

### `config.yaml` — Danh sách model

```yaml
model_list:
  # Model Azure (giữ nguyên template mẫu)
  - model_name: gpt-4o
    litellm_params:
      model: azure/my_azure_deployment
      api_base: os.environ/AZURE_API_BASE
      api_key: os.environ/AZURE_API_KEY
      api_version: "2025-01-01-preview"

  # 7 Model Free từ OpenCode Zen
  - model_name: big-pickle           # Tên hiển thị trong proxy
    litellm_params:
      model: openai/big-pickle       # openai/{model_id} — format OpenAI-compatible
      api_base: https://opencode.ai/zen/v1
      api_key: "public"              # OpenCode Zen chấp nhận mọi key
  - model_name: deepseek-v4-flash-free
  - model_name: laguna-s-2.1-free
  - model_name: ling-3.0-flash-free
  - model_name: mimo-v2.5-free
  - model_name: nemotron-3-ultra-free
  - model_name: north-mini-code-free

general_settings:
  master_key: sk-1234        # 🔑 Key xác thực proxy — client phải gửi Bearer token này
  database_url: "postgresql://llmproxy:dbpassword9090@db:5432/litellm"
```

> **Quan trọng:** `api_key` trong `config.yaml` là key LiteLLM gửi lên **OpenCode Zen**. Khác với `master_key` dùng để client xác thực với proxy.

### `docker-compose.yml` — Các dịch vụ

| Service | Image | Ghi chú |
|---|---|---|
| `litellm` | `docker.litellm.ai/berriai/litellm:main-stable` | Mount `config.yaml` vào `/app/config.yaml` |
| `db` | `postgres:16` | Database, dữ liệu persist qua volume `litellm_postgres_data` |
| `prometheus` | `prom/prometheus` | Scrape metrics mỗi 15s, retention 15 ngày |

### `.env` — Biến môi trường

```
LlTELLM_MASTER_KEY="sk-1234"           # Master key (dự phòng)
LITELLM_SALT_KEY="sk-1234"             # Salt key
AZURE_API_BASE="https://openai-..."    # Azure endpoint (placeholder)
AZURE_API_KEY="your-azure-api-key"     # Azure key (placeholder)
```

> Nếu không dùng Azure, có thể comment hoặc bỏ qua — proxy vẫn chạy với 7 model free.

## 🧠 Quản lý model

### Thêm model mới vào config

Thêm entry theo format:

```yaml
  - model_name: ten-model
    litellm_params:
      model: openai/ten-model
      api_base: https://opencode.ai/zen/v1
      api_key: "public"        # Luôn là "public" cho free models
```

Sau đó restart:

```bash
docker compose restart litellm
```

### Tự động dò model free (Script)

Script `update_models.py` tự động:
1. Fetch danh sách model từ OpenCode Zen API
2. Test từng model bằng API chat completions (không gửi key)
3. Nếu response có `choices` → FREE → thêm vào config
4. Sinh lại `config.yaml` hoàn chỉnh

```bash
# Preview trước
python update_models.py --dry-run

# Chạy thật (ghi đè config.yaml)
python update_models.py
```

## 🌐 Kết nối từ các Client

### Từ Windows (PowerShell/cmd)

```powershell
# Dùng master_key để xác thực
curl.exe -s http://localhost:4000/chat/completions `
  -H "Authorization: Bearer sk-1234" `
  -H "Content-Type: application/json" `
  -d '{\"model\":\"nemotron-3-ultra-free\",\"messages\":[{\"role\":\"user\",\"content\":\"Hi\"}]}'
```

### Từ WSL (Ubuntu/Debian)

WSL2 có thể truy cập `localhost:4000` của Windows nhờ `localhostForwarding`.

```bash
curl -s http://localhost:4000/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{"model":"nemotron-3-ultra-free","messages":[{"role":"user","content":"Hello"}]}'
```

> ⚠️ Trong zsh, nhớ dùng single quotes `'...'` cho JSON data để tránh zsh parse sai.

### Từ Grok CLI

Config Grok (`~/.grok/config.toml`) đã được cập nhật để trỏ qua LiteLLM:

```toml
[model.deepseek-v4-flash-free]
model = "deepseek-v4-flash-free"
base_url = "http://localhost:4000"     # Trỏ tới LiteLLM
api_key = "sk-1234"                     # Dùng master_key của LiteLLM (không phải "public")
```

Chạy Grok như bình thường:

```bash
grok "Xin chào, hãy giúp tôi viết code Python"
```

### Từ bất kỳ OpenAI-compatible client nào

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4000",   # Trỏ tới LiteLLM
    api_key="sk-1234"                   # Master key của LiteLLM
)

response = client.chat.completions.create(
    model="nemotron-3-ultra-free",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

## 🔧 Bảo trì & Vận hành

### Restart sau khi thay đổi config

```bash
docker compose -f D:\CODE\litellm\docker-compose.yml restart litellm
```

### Xem logs

```bash
docker logs litellm-litellm-1 --tail 50
docker compose -f D:\CODE\litellm\docker-compose.yml logs litellm -f
```

### Kiểm tra trạng thái container

```bash
docker ps --filter "name=litellm" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Cập nhật image LiteLLM

```bash
docker compose pull litellm
docker compose up -d
```

## 🚨 Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|---|---|---|
| `project name must not be empty` | `docker compose` không tìm thấy compose file | Dùng `docker compose -f D:\CODE\litellm\docker-compose.yml` |
| Container `health: starting` mãi | Health check có `start_period: 40s` | Đợi ~40-70s, kiểm tra lại |
| API trả về 401 | Sai `Authorization` header | Dùng `Bearer sk-1234` (master_key) |
| Lỗi `api_key client option must be set` | `api_key` rỗng trong config.yaml | Set `api_key: "public"` (non-empty) |
| Lỗi `Invalid API key` từ OpenCode Zen | Gửi sai key | Dùng `api_key: "public"` hoặc không gửi key |
| Grok chậm / không response | Sai api_key trong Grok config | Kiểm tra `~/.grok/config.toml`: dùng `sk-1234` |
| WSL không kết nối được | localhostForwarding bị tắt | Dùng `host.docker.internal` thay `localhost` |

## 📚 Tham khảo

- **LiteLLM Proxy Docs:** https://litellm.vercel.app/
- **OpenCode Zen:** https://opencode.ai/zen/v1
- **Grok CLI:** https://x.ai/grok
- **Hướng dẫn AI Agent cho dự án:** [`AGENTS.md`](./AGENTS.md)

---

**Model list hiện tại (7 free models):**

| # | Model | Context | Đặc điểm |
|---|---|---|---|
| 1 | `big-pickle` | 200K | General purpose |
| 2 | `deepseek-v4-flash-free` | 200K | Reasoning, có variants high/max |
| 3 | `laguna-s-2.1-free` | 256K | Reasoning, có variants low/medium/high |
| 4 | `ling-3.0-flash-free` | 262K | Flash inference |
| 5 | `mimo-v2.5-free` | 200K | Đa phương thức (text + image + audio input) |
| 6 | `nemotron-3-ultra-free` | 1M | Context 1 triệu token, reasoning |
| 7 | `north-mini-code-free` | 256K | Code chuyên dụng, có variant none/high |
