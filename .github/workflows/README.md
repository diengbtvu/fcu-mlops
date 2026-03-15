# 🤖 GitHub Actions Workflows

Dự án này sử dụng GitHub Actions để tự động hóa quy trình CI/CD.

## 📋 Workflows hiện có

### 🧪 CI - Testing & Quality Checks (`ci.yml`)

**Kích hoạt khi:**
- Có Pull Request vào branch `main` hoặc `dev`
- Push code vào branch `main` hoặc `dev`

**Các jobs:**

1. **🐘 Laravel Tests**
   - Setup PHP 8.2 + extensions
   - Install Composer dependencies (với cache)
   - Run PHPUnit tests
   - Check code style với Laravel Pint
   - Measure code coverage (minimum 70%)

2. **🐍 Python/ML Tests**
   - Setup Python 3.11
   - Install pip dependencies (với cache)
   - Lint code (Flake8, Black, isort)
   - Validate TensorFlow & ML libraries
   - Security check với Safety
   - Run pytest (nếu có)

3. **🐳 Docker Build Test**
   - Build Laravel Docker image
   - Build Predict Service Docker image
   - Validate docker-compose.yml

4. **🔒 Security Scanning**
   - PHP security audit (composer audit)
   - Python security check (safety)
   - Tìm vulnerabilities trong dependencies

5. **📋 Build Summary**
   - Tổng hợp kết quả tất cả jobs
   - Hiển thị summary trên GitHub

## 🚀 Cách sử dụng

### Chạy tự động
Workflow sẽ tự động chạy khi bạn:
```bash
# Tạo Pull Request
git checkout -b feature/new-feature
git add .
git commit -m "Add new feature"
git push origin feature/new-feature
# → Tạo PR trên GitHub → Workflow tự động chạy

# Hoặc push trực tiếp vào main/dev
git checkout main
git merge feature/new-feature
git push origin main
# → Workflow tự động chạy
```

### Xem kết quả
1. Vào GitHub repository
2. Click tab **Actions**
3. Chọn workflow run để xem chi tiết
4. Click vào từng job để xem logs

### Trên Pull Request
Workflow status sẽ hiển thị ngay trên PR:
```
✅ CI - Testing & Quality Checks — Checks have passed
   ✅ Laravel Tests
   ✅ Python Tests
   ✅ Docker Build Test
   ✅ Security Scanning
```

## 🔧 Tùy chỉnh

### Thay đổi code coverage requirement
Sửa trong [ci.yml](ci.yml):
```yaml
php artisan test --parallel --coverage --min=70  # Đổi 70 thành giá trị khác
```

### Thêm/bớt linters
Sửa phần Python tests:
```yaml
- name: Lint with Flake8
  run: |
    # Thêm/bớt rules ở đây
    flake8 . --max-line-length=127
```

### Bật/tắt jobs
Comment out job không cần:
```yaml
# docker-build:  # Comment để tắt
#   name: 🐳 Docker Build Test
#   ...
```

## 📊 Artifacts

Workflow lưu các artifacts sau mỗi lần chạy:

- **laravel-coverage** - PHP code coverage report (HTML)
- **python-coverage** - Python code coverage report (HTML)

Download trong tab **Actions** → chọn workflow run → phần **Artifacts**

## ⚙️ Requirements

Workflow yêu cầu:
- Repository phải public HOẶC có GitHub Actions enabled
- Không cần setup secrets (workflow chạy trên runner tạm)
- Free tier: 2000 minutes/month

## 🐛 Troubleshooting

### Workflow không chạy?
- Kiểm tra Settings → Actions → Allow all actions
- Đảm bảo file `.github/workflows/ci.yml` có trên branch default

### Tests fail?
- Xem logs chi tiết trong Actions tab
- Chạy tests local trước: `php artisan test` và `pytest`

### Timeout?
- Giảm số tests hoặc tách thành nhiều jobs nhỏ
- Tối ưu cache dependencies

## 📚 Tài liệu tham khảo

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Laravel Testing](https://laravel.com/docs/testing)
- [Pytest Documentation](https://docs.pytest.org/)
