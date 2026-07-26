#!/usr/bin/env python3
"""
update_models.py — Xác định chính xác model free từ OpenCode Zen v1
bằng cách gọi API thật không cần key, model nào chạy được mới đưa vào config.

Cách dùng:
  python update_models.py              # Test thật & cập nhật config.yaml
  python update_models.py --dry-run    # Chỉ preview, không ghi file

Nguyên tắc:
  - Gọi API chat completions cho mỗi model (KHÔNG gửi API key)
  - Nếu response có "choices" → FREE → thêm vào config
  - Nếu lỗi AuthError / Missing API key → PAID → bỏ qua
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Cấu hình ────────────────────────────────────────────────────────────────

OPEnCODE_API_BASE = "https://opencode.ai/zen/v1"
MODELS_URL = f"{OPEnCODE_API_BASE}/models"
CHAT_URL = f"{OPEnCODE_API_BASE}/chat/completions"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

MAX_WORKERS = 15       # Số luồng song song tối đa
TIMEOUT_PER_MODEL = 10 # Timeout cho mỗi request (giây)

# ─── Bước 1: Fetch danh sách model ──────────────────────────────────────────

def fetch_models() -> list[dict]:
    """Gọi API /v1/models, trả về list model."""
    req = urllib.request.Request(MODELS_URL, method="GET")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "curl/8.4.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        print(f"❌ Lỗi kết nối OpenCode Zen: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Lỗi parse JSON: {e}")
        sys.exit(1)

    models = data.get("data", [])
    if not models:
        print("⚠️  Không tìm thấy model nào từ OpenCode Zen.")
        sys.exit(0)

    return models


# ─── Bước 2: Gọi API test từng model ────────────────────────────────────────

def test_model(model_id: str) -> tuple[str, bool]:
    """
    Gọi API /chat/completions cho 1 model (KHÔNG gửi API key).
    Trả về (model_id, True) nếu FREE, (model_id, False) nếu PAID.
    """
    body = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 3
    }).encode()

    req = urllib.request.Request(CHAT_URL, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "curl/8.4.0")
    # KHÔNG gửi Authorization header

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_PER_MODEL) as resp:
            response_data = json.loads(resp.read().decode())
            # Nếu có "choices" → gọi được → FREE
            if "choices" in response_data:
                return model_id, True
            return model_id, False
    except urllib.error.HTTPError as e:
        # HTTP 401/403 → AuthError → PAID
        return model_id, False
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        # Lỗi mạng hoặc timeout → coi như không free
        return model_id, False


def identify_free_models(models: list[dict]) -> list[str]:
    """Test song song tất cả model, trả về list model ID free."""
    model_ids = [m["id"] for m in models]
    total = len(model_ids)
    free_models = []

    print(f"\n🧪 Đang test {total} models (gọi API thật, không key)...")
    print(f"   Workers: {MAX_WORKERS} | Timeout: {TIMEOUT_PER_MODEL}s\n")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(test_model, mid): mid for mid in model_ids}

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            model_id, is_free = future.result()
            status = "✅ FREE" if is_free else "⏭️  PAID"
            print(f"   [{done_count:>3}/{total}] {status}  {model_id}")

            if is_free:
                free_models.append(model_id)

    free_models.sort()
    return free_models


# ─── Bước 3: Sinh config.yaml ───────────────────────────────────────────────

def parse_nvidia_entries(config_text: str) -> list[str]:
    """Trích xuất các entry NVIDIA NIM từ config cũ (nếu có)."""
    nvidia_pattern = re.compile(
        r"  # ===== NVIDIA NIM =====.*?(?=\n\S|\Z)",
        re.DOTALL
    )
    return [m.group() for m in nvidia_pattern.finditer(config_text)]


def generate_config_yaml(free_model_ids: list[str], existing_config: str) -> str:
    """Sinh config.yaml hoàn chỉnh."""
    nvidia_entries = parse_nvidia_entries(existing_config)

    # Lấy general_settings từ config cũ
    general_match = re.search(r"\ngeneral_settings:.*", existing_config, re.DOTALL)
    general_section = general_match.group(0) if general_match else """general_settings:
  master_key: sk-1234
  database_url: "postgresql://llmproxy:dbpassword9090@db:5432/litellm"
"""

    # Header
    lines = [
        "# =====================================================",
        "# LiteLLM Proxy Config — Auto-generated by update_models.py",
        f"# Nguồn: OpenCode Zen v1 — {len(free_model_ids)} free models",
        f"# Được xác định bằng cách gọi API thật, không cần key.",
        "# =====================================================",
        "",
        "model_list:",
        "",
        "  # ===== OpenCode Zen v1 (Free Models - Verified) =====",
        "  # Các model này hoạt động KHÔNG cần API key",
        f"  # Tổng số: {len(free_model_ids)}",
        "",
    ]

    for mid in free_model_ids:
        lines.extend([
            f"  - model_name: {mid}",
            "    litellm_params:",
            f"      model: openai/{mid}",
            f"      api_base: {OPEnCODE_API_BASE}",
            '      api_key: ""  # Public model, không cần key',
            "",
        ])

    # Thêm NVIDIA NIM entries nếu có
    for entry in nvidia_entries:
        lines.append(entry)

    # General settings
    lines.append("")
    lines.append(general_section)

    return "\n".join(lines)


def write_config(content: str):
    """Ghi config.yaml."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    free_count = content.count("- model_name:")
    print(f"\n✅ Đã ghi config.yaml với {free_count} models.")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    dry_run = "--dry-run" in sys.argv

    print("🚀 LiteLLM Model Updater — OpenCode Zen Free Models Detector")
    print("=" * 60)

    # Bước 1: Fetch danh sách model
    print(f"\n📡 Đang fetch model list từ {MODELS_URL}...")
    all_models = fetch_models()
    print(f"✅ Tổng số model từ API: {len(all_models)}")

    # Bước 2: Test từng model bằng API thật
    free_ids = identify_free_models(all_models)

    if not free_ids:
        print("\n❌ Không tìm thấy model free nào!")
        sys.exit(1)

    print(f"\n🎯 Kết quả: {len(free_ids)} model FREE (không cần API key):")
    for mid in free_ids:
        print(f"   • {mid}")

    # Bước 3: Đọc config cũ (nếu có)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            existing_config = f.read()
    else:
        existing_config = ""

    # Bước 4: Sinh config mới
    new_config = generate_config_yaml(free_ids, existing_config)

    # Preview
    print("\n📄 Xem trước config.yaml:")
    print("-" * 50)
    print(new_config)
    print("-" * 50)

    if dry_run:
        print("\n⏸️  Dry-run — không ghi file.")
        print("Bỏ --dry-run để cập nhật thật.")
        return

    # Bước 5: Ghi file
    write_config(new_config)
    print("\n🎉 Hoàn tất!")
    print("   Chạy 'docker compose restart' hoặc 'docker compose up -d' để reload LiteLLM Proxy.")
    print("   Kiểm tra: curl http://localhost:4000/model/info -H 'Authorization: Bearer sk-1234'")


if __name__ == "__main__":
    main()
