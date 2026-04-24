# Slide 1 - Arm A: Direct Chart-to-Text

## Arm A - Sinh giải thích trực tiếp từ biểu đồ/bảng

**Mục tiêu:** tạo baseline đơn giản để đánh giá khả năng LLM mô tả artifact ML một cách trực tiếp.

**Cách hoạt động:**

- Nhận evidence từ bảng/JSON, biểu đồ và phần summary theo từng điều kiện input.
- Sinh `explanation_short` và `explanation_full` trong một lượt.
- Ưu tiên các phát hiện được chứng cứ hỗ trợ rõ ràng.
- Hạn chế diễn giải sâu hoặc suy luận ngoài dữ liệu.

**Vai trò trong benchmark:**

- Là mốc so sánh cơ bản cho các phương pháp phức tạp hơn.
- Giúp kiểm tra LLM có thể mô tả đúng các metric, ranking và mô hình tốt nhất hay không.
- Dễ chạy, ít chi phí, nhưng dễ bỏ sót insight hoặc tạo claim chưa được kiểm chứng.

---

# Slide 2 - Arm B: VisText-Style Layered Explanation

## Arm B - Giải thích phân tầng theo mức ngữ nghĩa

**Mục tiêu:** kiểm tra xem việc kiểm soát tầng ý nghĩa có giúp explanation rõ ràng và đầy đủ hơn không.

**Ba mức semantic level:**

- **L1:** mô tả cấu trúc artifact, ví dụ loại biểu đồ, trục, cột, entity, metric.
- **L2/L3:** mô tả insight phân tích, ví dụ best/worst model, ranking, trend, caveat.
- **L1+L2/L3:** kết hợp mô tả cấu trúc và insight phân tích trong cùng explanation.

**Vai trò trong benchmark:**

- Tách rõ phần "nhìn thấy gì" và "rút ra điều gì".
- Giúp đánh giá coverage theo từng loại thông tin.
- Có khả năng tăng recall, nhưng tạo nhiều run hơn Arm A vì mỗi condition có nhiều semantic level.

---

# Slide 3 - Arm C: Generate + Validate + Correct

## Arm C - Sinh, kiểm chứng và tự sửa lỗi factual

**Mục tiêu:** giảm claim sai, claim không kiểm chứng được và tăng độ trung thành với evidence.

**Pipeline chính:**

1. **Draft generator:** sinh bản giải thích nháp từ artifact context.
2. **Claim extraction:** trích xuất các claim có cấu trúc từ bản nháp.
3. **Validator:** kiểm tra từng claim với evidence packet và gán trạng thái `supported`, `partially_supported`, `contradicted`, hoặc `unverifiable`.
4. **Corrector:** sửa claim sai, bỏ claim không có chứng cứ, giữ claim được hỗ trợ.
5. **Re-validation:** kiểm chứng lại bản đã sửa và chọn output tốt hơn.

**Vai trò trong benchmark:**

- Là arm có cơ chế kiểm soát factuality mạnh nhất.
- Phù hợp khi báo cáo cần độ tin cậy cao hơn so với sinh một lượt.
- Chi phí chạy cao hơn A/B, nhưng thường kỳ vọng giảm contradiction và unsupported claim rate.
