# KẾ HOẠCH PHÂN CÔNG DỰ ÁN: BÀI TOÁN ANTIBANDWIDTH (ABP) VỚI SAT SOLVER
**Thời lượng thực hiện:** 3 tuần  
**Thành viên:** Tường, Tùng, Lợi  
**Mục tiêu:** Hoàn thiện mã nguồn giải thuật, báo cáo khoa học và slide/video thuyết trình với sự tham gia đồng đều của cả 3 thành viên ở cả 3 mảng công việc.

---

## 1. Nguyên Tắc Phân Chia Đồng Đều (Workload Balance)

| Trụ cột | Tường | Tùng | Lợi |
| :--- | :--- | :--- | :--- |
| **1. Code & Thuật toán** | Tiền xử lý dữ liệu Harwell-Boeing + Module Direct Encoding (Hệ ràng buộc song ánh ALO/AMO). | Mã hóa ràng buộc khoảng cách $d \ge k$ + Thuật toán tìm kiếm tối ưu (Binary Search & Incremental SAT). | Tích hợp SAT Solver (Kissat/CaDiCaL) + Tối ưu Phá vỡ đối xứng (Symmetry Breaking) & Order Encoding / Đánh giá Benchmark. |
| **2. Báo cáo (Report)** | Soạn Chương 1 & 2: Cơ sở lý thuyết ABP, tính NP-hard, ứng dụng thực tế. | Soạn Chương 3 & 4.1 - 4.2: Chuyển đổi bài toán tối ưu sang SAT, chi tiết Direct Encoding & Distance Clauses. | Soạn Chương 4.3 - 5: Kỹ thuật Symmetry Breaking, Order Encoding, tổng hợp số liệu thực nghiệm & kết luận. |
| **3. Thuyết trình (Presentation)** | Thiết kế Slide Phần 1 (Đặt vấn đề, mô hình đồ thị, ứng dụng) + Thuyết trình Mở đầu (Tuần 3). | Thiết kế Slide Phần 2 (Mô hình hóa SAT, Direct Encoding, Binary Search) + Thuyết trình Kỹ thuật (Tuần 3). | Thiết kế Slide Phần 3 (Symmetry Breaking, Thực nghiệm Harwell-Boeing, Demo chạy mã nguồn) + Thuyết trình Kết luận (Tuần 3). |

---

## 2. Kế Hoạch Chi Tiết Theo Từng Tuần (3 Tuần)

### TUẦN 1: Nghiên Cứu Lý Thuyết & Xây Dựng Khung Nền Tảng (Core Setup)

#### Nhiệm vụ Code:
- **Tường:**
  - Viết module đọc và trích xuất đồ thị $G=(V, E)$ từ định dạng ma trận thưa Harwell-Boeing (`bcsstk01`, `can_24`, `dwt_59`).
  - Xây dựng cấu trúc dữ liệu đồ thị và hàm kiểm tra tính hợp lệ của hoán vị (Verifier).
- **Tùng:**
  - Khởi tạo khung ánh xạ biến SAT: quản lý chỉ số biến boolean $x_{i, p}$ ($1 \le i \le n, 1 \le p \le n$) thành ID số nguyên (DIMACS CNF).
  - Viết generator tạo các mệnh đề song ánh cơ bản: Bijective clauses (ALO & AMO từng đỉnh, ALO & AMO từng vị trí).
- **Lợi:**
  - Thiết lập môi trường thực thi SAT Solver (cài đặt `Kissat`, `CaDiCaL` hoặc `python-sat` / `PySAT`).
  - Viết pipeline tự động xuất file `.cnf`, gọi Solver và đọc kết quả trả về (SAT/UNSAT + model values).

#### Nhiệm vụ Báo cáo:
- **Tường:** Hoàn thành bản thảo **Chương 1**: Tổng quan ABP, định nghĩa hình thức song ánh $f$, hàm mục tiêu $B_A(G) = \max_f \min_{\{u,v\} \in E} |f(u) - f(v)|$, so sánh với Bandwidth Problem.
- **Tùng:** Hoàn thành bản thảo **Chương 2**: Các ứng dụng thực tế (Radio Frequency Assignment, VLSI Crosstalk Minimization, Lập lịch, Bảo mật dữ liệu).
- **Lợi:** Soạn thảo mục **Đặc tả dữ liệu**: Cấu trúc tập chuẩn Harwell-Boeing, ý nghĩa của mật độ cạnh và phân bố bậc đỉnh trong kiểm thử.

#### Nhiệm vụ Thuyết trình:
- **Cả 3 thành viên:** Họp thống nhất cấu trúc Outline Slide (15-20 slide), tông màu, template chuẩn.
  - **Tường:** Phác thảo nội dung slide 1–5 (Giới thiệu, bài toán, động lực).
  - **Tùng:** Phác thảo nội dung slide 6–10 (Công thức hóa SAT).
  - **Lợi:** Phác thảo nội dung slide 11–15 (Mã hóa nâng cao & Thực nghiệm).

---

### TUẦN 2: Cài Đặt Thuật Toán Nâng Cao & Thử Nghiệm Thực Tế

#### Nhiệm vụ Code:
- **Tường:**
  - Cài đặt cơ chế kiểm soát cận: tính cận trên lý thuyết $k_{max} = \lfloor n/2 \rfloor$, cận dưới $k_{min} = 1$.
  - Hỗ trợ xây dựng chiến lược duyệt ngưỡng: Linear Search và Binary Search qua các ngưỡng $k$.
- **Tùng:**
  - Cài đặt hệ mệnh đề ràng buộc khoảng cách Antibandwidth:
    $$\neg x_{u,p} \vee \neg x_{v,q} \quad (\forall \{u,v\} \in E, |p - q| < k)$$
  - Tối ưu hóa số lượng mệnh đề sinh ra để tránh tràn bộ nhớ trên đồ thị có nhiều cạnh.
- **Lợi:**
  - Cài đặt kỹ thuật Phá vỡ đối xứng (Symmetry Breaking):
    $$\neg x_{v_0, p} \quad \left(\forall p > \lceil n/2 \rceil, \text{với } \deg(v_0) = \Delta(G)\right)$$
  - Nghiên cứu/thực hiện thử nghiệm bổ sung với Order Encoding ($y_{i,p} \iff f(i) \le p$) để so sánh hiệu năng.

#### Nhiệm vụ Báo cáo:
- **Tường:** Viết **Chương 3**: Quy trình chuyển đổi bài toán Tối ưu sang bài toán Quyết định $ABP(G, k)$, thuật toán Binary Search & Incremental SAT.
- **Tùng:** Viết **Chương 4.1 & 4.2**: Mô hình Direct Encoding chi tiết, công thức hóa hệ ràng buộc song ánh và khoảng cách.
- **Lợi:** Viết **Chương 4.3 & 4.4**: Phân tích toán học kỹ thuật Symmetry Breaking và phương pháp Order Encoding.

#### Nhiệm vụ Thuyết trình:
- **Tường:** Hoàn thiện thiết kế chi tiết Slide Phần 1 (Đồ họa hóa đồ thị, ví dụ minh họa bằng hình vẽ trực quan).
- **Tùng:** Hoàn thiện thiết kế chi tiết Slide Phần 2 (Sơ đồ khối quá trình mã hóa CNF và duyệt nhị phân).
- **Lợi:** Hoàn thiện thiết kế chi tiết Slide Phần 3 (Bảng so sánh Direct vs Order Encoding, cơ chế phá vỡ đối xứng).

---

### TUẦN 3: Thực Nghiệm Benchmark, Hoàn Thiện Báo Cáo & Thuyết Trình

#### Nhiệm vụ Code:
- **Tường:**
  - Chạy thực nghiệm đo đạc thời gian chạy (Execution Time) và số lượng biến/mệnh đề trên các file ma trận `bcsstk01`, `can_24`,...
  - Vẽ biểu đồ so sánh: Thời gian giải khi có/không có Symmetry Breaking.
- **Tùng:**
  - Kiểm thử chéo kết quả (Cross-validation): viết test suite tự động kiểm tra tính đúng đắn của nghiệm $f$ trả về từ solver cho từng đồ thị.
  - Đóng gói mã nguồn (clean code, tài liệu hướng dẫn cài đặt `README.md`, file chạy mẫu `main.py`).
- **Lợi:**
  - Thực nghiệm so sánh giữa các solver khác nhau (hoặc giữa Direct Encoding và Order Encoding).
  - Thu thập bảng số liệu kết quả tối ưu $B_A(G)$ tìm được và thời gian CPU tương ứng.

#### Nhiệm vụ Báo cáo:
- **Tường:** Viết phần mở đầu, tóm tắt (Abstract), hoàn thiện danh mục tài liệu tham khảo và định dạng chuẩn báo cáo (LaTeX/Word).
- **Tùng:** Đưa các bảng số liệu thực nghiệm, đồ thị so sánh vào **Chương 5 (Kết quả thực nghiệm)**.
- **Lợi:** Viết phần phân tích đánh giá kết quả, ưu/nhược điểm thực tế, hướng phát triển tương lai và Kết luận chung.
- **Cả 3 thành viên:** Review chéo toàn bộ bài báo cáo để chỉnh sửa ngữ pháp, thuật ngữ chuyên ngành và thống nhất phong cách viết.

#### Nhiệm vụ Thuyết trình:
- **Tường (Phần 1 - ~5 phút):** 
  - Trình bày bối cảnh bài toán, định nghĩa toán học ABP, so sánh với Bandwidth, các ứng dụng vi mạch & phân bổ tần số vô tuyến.
- **Tùng (Phần 2 - ~5 phút):** 
  - Trình bày kỹ thuật mô hình hóa SAT, các nhóm mệnh đề Direct Encoding, chiến lược tìm kiếm nhị phân cho ngưỡng $k$.
- **Lợi (Phần 3 - ~5 phút):** 
  - Trình bày kỹ thuật Symmetry Breaking, Order Encoding, kết quả đánh giá trên tập Harwell-Boeing và Demo chương trình chạy thực tế.
- **Cả 3 thành viên:** Phối hợp trả lời các câu hỏi phản biện (Q&A) từ giảng viên/hội đồng.

---

## 3. Bảng Theo Dõi Tiến Độ & Tiêu Chí Đánh Giá (Checklist)

| Nội dung | Đầu ra mong đợi (Deliverables) | Người phụ trách chính | Deadline | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Parser Graph** | Module đọc file ma trận Harwell-Boeing | Tường | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **SAT Encoder** | Module sinh file DIMACS CNF (Song ánh + Khoảng cách) | Tùng | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **Solver Pipeline** | Pipeline gọi SAT solver và trích xuất nghiệm | Lợi | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **Draft Báo cáo 1** | Chương 1, 2 và khung tài liệu | Tường & Tùng | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **Symmetry Breaking** | Module bổ sung ràng buộc cắt đối xứng | Lợi | Giữa Tuần 2 | ⏳ Chưa bắt đầu |
| **Binary Search** | Thuật toán tìm $k$ tối ưu tự động | Tùng & Tường | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **Draft Báo cáo 2** | Hoàn thành Chương 3 & Chương 4 | Cả 3 | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **Slide Thô** | Hoàn thiện 100% nội dung Slide | Cả 3 | Giữa Tuần 3 | ⏳ Chưa bắt đầu |
| **Benchmark & Charts** | Bảng kết quả chạy trên Harwell-Boeing + Đồ thị | Tường & Lợi | Giữa Tuần 3 | ⏳ Chưa bắt đầu |
| **Final Report** | Báo cáo hoàn chỉnh định dạng chuẩn | Cả 3 (Tường gom) | Cuối Tuần 3 | ⏳ Chưa bắt đầu |
| **Rehearsal & Demo** | Thử thuyết trình khớp thời gian + Chuẩn bị Demo | Cả 3 | Trước ngày báo cáo | ⏳ Chưa bắt đầu |