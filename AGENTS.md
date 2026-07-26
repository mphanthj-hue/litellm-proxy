# LiteLLM Proxy — AI Agent Guide

## Project Overview

Dockerized [LiteLLM Proxy](https://litellm.vercel.app/) để proxy LLM API requests, kết hợp Postgres (config storage) và Prometheus (monitoring).

## Quick Start

```bash
# Khởi động toàn bộ hệ thống
docker compose up -d

# Kiểm tra health
curl http://localhost:4000/health/liveliness

# Kiểm tra model list
curl http://localhost:4000/model/info -H 'Authorization: Bearer sk-1234'

# Dừng hệ thống
docker compose down
```

## Dò model free từ OpenCode Zen

```bash
# Preview (không ghi file)
python update_models.py --dry-run

# Test thật & cập nhật config.yaml
python update_models.py
```

## Key Files

| File | Purpose |
|---|---|
| `config.yaml` | Cấu hình proxy — model list + general settings |
| `docker-compose.yml` | Orchestration (litellm + postgres + prometheus) |
| `update_models.py` | Script tự động dò model free từ OpenCode Zen API |
| `opencode-models.json` | Danh sách model OpenCode Zen (định nghĩa tĩnh) |
| `.env` | Biến môi trường (API keys, secrets) |

## Architecture

```
Client → LiteLLM Proxy (:4000) → OpenAI/Azure/OpenCode Zen...
                                    ↑
                              Postgres (config DB)
                                    ↑
                            Prometheus (:9090, metrics)
```

## Conventions

### Thêm model free từ OpenCode Zen

- `api_key: "public"` (OpenCode Zen chấp nhận mọi key, dùng "public" cho free models)
- `api_base: https://opencode.ai/zen/v1`
- `model: openai/{model_id}`
- Thêm entries vào `model_list` trong `config.yaml`

### Model ID

Model ID trong `opencode-models.json` dùng key format `opencode/{id}`. Khi thêm vào config, dùng `{id}` cho cả `model_name` và `openai/{id}`.

> **Lưu ý:** `api_key` phải là non-empty string (VD: `"public"`). `api_key: ""` (rỗng) sẽ bị OpenAI client báo lỗi.

### Kết nối từ Grok CLI qua LiteLLM

Khi dùng Grok gọi qua LiteLLM proxy:
- `base_url: http://localhost:4000` (trỏ tới LiteLLM)
- `api_key: "sk-1234"` (dùng **master_key** của LiteLLM, không phải "public")
- LiteLLM config.yaml vẫn dùng `api_key: "public"` để gọi OpenCode Zen

## Pitfalls

1. **Volume mount bị comment:** Trong `docker-compose.yml`, dòng mount `config.yaml` vào container đang bị comment. Cần uncomment trước khi dùng config thật.
2. **Cập nhật model:** Sau khi sửa `config.yaml`, chạy `docker compose restart litellm` để reload.
3. **Master key:** Mặc định `sk-1234` — đổi trong `.env` nếu deploy production.
