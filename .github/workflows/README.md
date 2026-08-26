# GitHub Actions Workflows

Repo dùng 3 workflow: **CI chạy tự động**, còn **deploy và rollback đều phải bấm tay**
(`workflow_dispatch`). Không có đường nào đẩy code lên production mà không có người xác nhận.

```
push / PR vào main|dev ──▶ ci.yml
                             ├── Laravel Tests
                             ├── Python/ML Tests
                             ├── Security Scanning
                             ├── Build Summary
                             └── Build & Push Images   ← chỉ khi push vào main
                                      │
                                      ▼
                     ghcr.io/diengbtvu/fcu-mlops-{webapp,frontend,predict}:<sha12>
                                      │
        bấm tay: "Deploy to Production (blue/green)" ──SSH──▶ deploy/deploy.sh prod <tag>
        bấm tay: "Rollback (blue/green)"             ──SSH──▶ deploy/rollback.sh <color>
```

---

## 1. `ci.yml` — Testing & Quality Checks

**Kích hoạt:** push hoặc pull request vào `main` / `dev`.
Run cũ trên cùng một ref sẽ bị huỷ (`concurrency` + `cancel-in-progress`).

| Job | Nội dung | Có chặn merge không? |
|---|---|---|
| **Laravel Tests** | PHP 8.2, Composer (có cache), DB SQLite, `php artisan migrate`, `php artisan test`, `pint --test`, upload coverage | Chỉ báo cáo (`continue-on-error`) |
| **Python/ML Tests** | Python 3.11 (cache pip), `flake8`, `black`/`isort`, `safety`, `pytest --cov` | Lỗi cú pháp / undefined name của flake8 làm fail job; phần còn lại chỉ báo cáo |
| **Security Scanning** | `composer audit` + `safety check` | Chỉ báo cáo |
| **Build Summary** | Ghi bảng kết quả vào GitHub Step Summary, fail nếu job test fail | Có |
| **Build & Push Images** | Build 3 image production bằng Buildx (cache GHA) rồi push lên GHCR | Chỉ chạy khi **push vào `main`** và 2 job test đã pass |

**Tag image = 12 ký tự đầu của commit SHA.** Đây cũng chính là tag đưa vào workflow deploy,
nên mỗi bản chạy production luôn truy ngược được về đúng một commit:

```
ghcr.io/diengbtvu/fcu-mlops-webapp:<sha12>      # php-fpm + code Laravel
ghcr.io/diengbtvu/fcu-mlops-frontend:<sha12>    # nginx + asset trong public/
ghcr.io/diengbtvu/fcu-mlops-predict:<sha12>     # Flask + toàn bộ stack ML
```

**Artifacts:** `laravel-coverage`, `python-coverage` (giữ 7 ngày) — tải trong tab
**Actions** → chọn run → mục **Artifacts**.

---

## 2. `deploy-prod.yml` — Deploy to Production (blue/green)

**Kích hoạt:** `workflow_dispatch` (Actions → chọn workflow → Run workflow).

| Input | Bắt buộc | Ghi chú |
|---|---|---|
| `confirm` | Có | Phải gõ đúng `DEPLOY` (viết hoa). Sai là job `guard` fail ngay, không SSH vào server |
| `tag` | Không | Tag image 12 ký tự. Để trống = `HEAD` hiện tại của `main` |

`concurrency: prod-deploy` dùng chung với rollback và `cancel-in-progress: false`, nên
hai lần deploy không bao giờ chồng lên nhau.

Job SSH vào server, chỉ cập nhật các file phục vụ deploy từ `origin/main`
(`deploy/`, `docker/`, hai dockerfile), rồi chạy `deploy/deploy.sh prod <tag>`.
Chi tiết 11 bước của script đó nằm ở [`deploy/README.md`](../../deploy/README.md).

---

## 3. `rollback.yml` — Rollback (blue/green)

**Kích hoạt:** `workflow_dispatch`, một input `color` (`blue` | `green`).

SSH vào server và chạy `deploy/rollback.sh <color>`: khởi động lại đúng các container đang
tồn tại của màu đó, chờ healthy, smoke test, rồi trỏ proxy về lại. Script tự lấy tag image
từ chính container cũ nên không cần nhớ lần trước chạy tag nào.

---

## Secrets cần cấu hình

Settings → Secrets and variables → Actions:

| Secret | Dùng để làm gì |
|---|---|
| `SSH_HOST` | Địa chỉ server production |
| `SSH_USER` | User SSH |
| `SSH_PRIVATE_KEY` | Private key của user đó |
| `SSH_PORT` | Không bắt buộc, mặc định `22` |
| `DEPLOY_PATH` | Đường dẫn tuyệt đối tới thư mục repo trên server |

Push image lên GHCR dùng `GITHUB_TOKEN` có sẵn (quyền `packages: write`), không cần thêm secret.

---

## Tuỳ chỉnh thường gặp

**Đổi nhánh kích hoạt CI** — sửa khối `on:` trong [`ci.yml`](ci.yml):

```yaml
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main, dev]
```

**Bắt lỗi chặt hơn** — bỏ `continue-on-error: true` ở bước tương ứng (ví dụ Pint hoặc
`php artisan test`) để job fail thật sự khi có lỗi.

**Thêm / bớt linter** — sửa các bước Flake8 / Black / isort trong job `python-tests`.

**Đổi registry hoặc tên image** — sửa `tags:` trong job `build-and-push`, đồng thời sửa
`REGISTRY` / `IMAGE_PREFIX` trong `deploy/.env.blue` và `deploy/.env.green` trên server cho khớp.

---

## Troubleshooting

**Workflow không chạy?** Kiểm tra Settings → Actions → Allow all actions, và chắc chắn
file workflow đã có trên nhánh mặc định.

**Job `build-and-push` bị skip?** Đúng như thiết kế: nó chỉ chạy với `push` vào `main`,
không chạy trên pull request.

**Deploy fail ở job `guard`?** Ô `confirm` phải là đúng chữ `DEPLOY` viết hoa.

**Deploy fail sau khi SSH?** Đọc log xem chết ở bước nào. Bước 1–8 nghĩa là chưa đụng gì
tới production, màu cũ vẫn đang phục vụ. Bước 10 nghĩa là đã tự động rollback, màu mới vẫn
được giữ chạy để debug.

**Tests fail?** Chạy local trước: `php artisan test` (trong `WebApp/`) và
`pytest tests/ -v` (trong `predict-service/`).

---

## Tài liệu liên quan

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — kiến trúc pipeline CI
- [`deploy/README.md`](../../deploy/README.md) — blue/green deployment chi tiết
- [`README.md`](../../README.md) — tổng quan dự án, setup local
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
