# KẾ HOẠCH PHÂN CÔNG DỰ ÁN: BÀI TOÁN ANTIBANDWIDTH (ABP)
## BÀI TẬP LỚN SỐ 2 - MÔN CÁC VẤN ĐỀ HIỆN ĐẠI KHMT (HK I 2026 - 2027)

* **Topic 5:** Antibandwidth Problem (ABP)
* **Thời lượng thực hiện:** 3 tuần
* **Thành viên:** Tường, Tùng, Lợi
* **Mục tiêu:** 
  1. Cài đặt các phương pháp mã hóa SAT: **Pairwise (Direct) Encoding** (kèm tối ưu ALO/AMO nâng cao `Commander`/`SeqCounter` qua PySAT) và **Staircase Sequential Counter (SCL) Encoding** (phân rã SCAMO theo đỉnh).
  2. Xây dựng mô hình giải chính xác đối chứng bằng **Constraint Programming (Google OR-Tools CP-SAT)** để so sánh hiệu năng với SAT (`cadical153`).
  3. Thực nghiệm đánh giá trên các ma trận từ tập chuẩn Harwell-Boeing (bao gồm các ca khó như `can___61.txt`).
  4. Trực quan hóa dữ liệu và kết quả thực nghiệm bằng thư viện bắt buộc **`cnsplots`** (`https://cnsplots.farid.one/latest/`).
  5. Xuất bản báo cáo khoa học theo đúng **Template LaTeX của nhà xuất bản Elsevier (`cas-sc`)** và đính kèm link GitHub Repository trong mục **"Data Availability"**.

---

## 1. Nguyên Tắc Phân Chia Đồng Đều (Workload Balance)

| Trụ cột | Tường | Tùng | Lợi |
| :--- | :--- | :--- | :--- |
| **1. Code & Thuật toán** | - Parser đồ thị Harwell-Boeing.<br>- Bổ sung tập dữ liệu ma trận lớn.<br>- Bộ kiểm tra tính hợp lệ của nghiệm (Verifier).<br>- Chiến lược tìm kiếm **Binary Search** & **Incremental Search** (tăng dần từ LB). | - Direct Encoding (Pairwise).<br>- Tối ưu ALO/AMO nâng cao (Sequential Counter / Commander qua PySAT `CardEnc`).<br>- Cài đặt **Staircase SCL Encoding** (`src/scl_encoder.py`).<br>- Xây dựng mô hình đối chuẩn **Google OR-Tools CP-SAT**. | - Pipeline SAT Solver (PySAT `cadical153` + Kissat) & **Hard Timeout đa tiến trình**.<br>- Kỹ thuật Phá vỡ đối xứng (Symmetry Breaking).<br>- Trực quan hóa đồ thị & biểu đồ bằng **`cnsplots`**.<br>- Pipeline benchmark (`--merge`, lưu nghiệm tốt nhất khi timeout). |
| **2. Báo cáo (Report)** | - Khởi tạo Template Elsevier (`cas-sc`).<br>- Soạn Chương 1 & 2 (Tổng quan bài toán, ứng dụng thực tế).<br>- Soạn Chương 3 (Binary Search & Incremental Search).<br>- Biên tập mục **Data Availability**, Abstract & Tài liệu tham khảo (gồm Truong et al., 2025). | - Soạn Chương 4.1, 4.2, 4.4, 4.5:<br>  + Direct Encoding & ALO/AMO nâng cao.<br>  + **Staircase SCL Encoding** (SCAMO, khối AMO/AMZ, phân rã theo đỉnh).<br>  + Mô hình **CP-SAT** & bảng số liệu Chương 5. | - Soạn Chương 4.3 (Cơ chế Symmetry Breaking).<br>- Soạn Chương 5 (Phân tích so sánh thực nghiệm **Direct vs Staircase SCL vs CP-SAT** qua biểu đồ `cnsplots`, nhận xét ưu/nhược điểm & Kết luận). |
| **3. Thuyết trình (Presentation)** | - Thiết kế Slide Phần 1 (Đặt vấn đề, mô hình hóa toán học, Binary Search & Incremental Search).<br>- Thuyết trình Mở đầu (Tuần 3). | - Thiết kế Slide Phần 2 (Direct Encoding, ALO/AMO nâng cao, **Staircase SCL Encoding**, mô hình CP-SAT).<br>- Thuyết trình Kỹ thuật (Tuần 3). | - Thiết kế Slide Phần 3 (Symmetry Breaking, kết quả so sánh **Direct vs SCL vs CP-SAT** qua biểu đồ `cnsplots`).<br>- Thuyết trình Kết luận & Demo chương trình. |

---

## 2. Kế Hoạch Chi Tiết Theo Từng Tuần (3 Tuần)

### TUẦN 1: Thiết Lập Nền Tảng, Chuẩn Bị Dữ Liệu & Khung Báo Cáo Elsevier

#### Nhiệm vụ Code:
* **Tường:**
  * Xây dựng module nạp dữ liệu đồ thị thưa `graph_loader.py` hỗ trợ các định dạng Matrix Market (`.mtx`, `.rb`).
  * Tìm kiếm và tải về các ma trận kiểm thử có kích thước lớn từ kho chuẩn Harwell-Boeing / SuiteSparse Matrix Collection (ví dụ: `dwt_59`, `can_61`, `ash85`, `bcsstk01`).
  * Xây dựng hàm kiểm tra nghiệm độc lập (`verify_solution`): kiểm tra song ánh $1..n$ và khoảng cách $|f(u) - f(v)| \ge k$.
* **Tùng:**
  * Quản lý ánh xạ biến SAT: ma trận biến boolean $x_{i, p}$ ($1 \le i \le n, 1 \le p \le n$) thành chỉ số DIMACS nguyên.
  * Xây dựng hệ ràng buộc song ánh cơ bản (Direct ALO/AMO cho đỉnh và vị trí).
* **Lợi:**
  * Cấu hình môi trường SAT Solver: tích hợp `python-sat` (PySAT) với solver chính `cadical153` (CaDiCaL 1.5.3).
  * Viết pipeline xuất file DIMACS `.cnf` chuẩn và đọc kết quả (SAT/UNSAT + model values) từ solver độc lập.
  * Cài đặt và nghiên cứu API của thư viện bắt buộc **`cnsplots`**.

#### Nhiệm vụ Báo cáo:
* **Tường:** 
  * Tải và thiết lập khung bài báo khoa học chuẩn **Elsevier LaTeX Template** (`\documentclass[a4paper,fleqn]{cas-sc}`).
  * Hoàn thành bản thảo **Chương 1**: Tổng quan bài toán Antibandwidth, định nghĩa hình thức song ánh $f$, hàm mục tiêu $B_A(G)$, so sánh đối ngẫu với Bandwidth Problem.
* **Tùng:** Hoàn thành bản thảo **Chương 2**: Các ứng dụng thực tế của ABP (Radio Frequency Assignment, VLSI Crosstalk Minimization, Bảo mật thông tin, Lập lịch mạng cảm biến).
* **Lợi:** Soạn thảo mục **Đặc tả dữ liệu thực nghiệm**: Bảng thông số kỹ thuật các ma trận kiểm thử (số đỉnh $n$, số cạnh $m$, mật độ đồ thị, bậc đỉnh lớn nhất/nhỏ nhất).

#### Nhiệm vụ Thuyết trình:
* **Cả 3 thành viên:** Thống nhất dàn ý Slide (15–20 slide), phong cách thiết kế academic, phác thảo nội dung từng phần phụ trách.

---

### TUẦN 2: Cài Đặt Thuật Toán Nâng Cao, Staircase SCL & CP-SAT

#### Nhiệm vụ Code:
* **Tường:**
  * Cài đặt cơ chế kiểm soát chặn cận: cận trên lý thuyết $k_{max} = \lfloor n/2 \rfloor$, cận dưới $k_{min} = 1$.
  * Tích hợp chiến lược tìm kiếm nhị phân (Binary Search), tìm kiếm tuần tự (Linear Search) và tìm kiếm tăng dần từ cận dưới (**Incremental Search**, `--method incremental`) qua các ngưỡng $k$.
* **Tùng:**
  * Cài đặt hệ mệnh đề ràng buộc khoảng cách Antibandwidth: $\neg x_{u,p} \lor \neg x_{v,q}$ ($\forall \{u,v\} \in E, |p - q| < k$).
  * **Nâng cao ALO/AMO (Khuyến khích trong đề bài):** Tích hợp kỹ thuật mã hóa hồng hào hơn (như *Sequential Counter* hoặc *Commander* thông qua `pysat.card.CardEnc`) nhằm giảm số lượng mệnh đề từ $O(n^2)$ xuống $O(n)$ trên các ma trận lớn.
  * **Staircase Sequential Counter Encoding (`src/scl_encoder.py`):** Cài đặt mô hình mã hóa bậc thang (Staircase Encoding theo Truong et al., 2025) cho bài toán ABP (`--encoding scl`), kết hợp SCAMO theo cửa sổ trượt $w = k$ và tách biến đỉnh để giảm số mệnh đề xuống $O(|V| \cdot n)$.
  * **Mô hình hóa CP-SAT (Bắt buộc trong đề bài):** Viết module giải bài toán bằng **Google OR-Tools CP-SAT** (`src/cp_solver.py`) sử dụng biến miền nguyên `IntVar` và ràng buộc `AddAllDifferent`, làm đối trọng so sánh với SAT.
* **Lợi:**
  * Cài đặt kỹ thuật **Phá vỡ đối xứng (Symmetry Breaking)**: ghim đỉnh có bậc lớn nhất $v_0$ vào nửa đầu dải vị trí $\neg x_{v_0, p}$ ($\forall p > \lceil n/2 \rceil$).
  * Xây dựng pipeline tích hợp batch đa ma trận (`main.py`, `benchmark.py`), cơ chế **Hard Timeout đa tiến trình** (`multiprocessing.Process`), theo dõi nghiệm tốt nhất theo thời gian thực (`on_best_found`), hỗ trợ `--merge` / `--drop-graphs` và quy trình đo lường benchmark tự động.
  * Bổ sung cơ chế xuất đồ thị minh họa nghiệm bằng **`cnsplots`** (sơ đồ 1D Linear Arc Placement và cấu trúc đồ thị).

#### Nhiệm vụ Báo cáo:
* **Tường:** Viết **Chương 3** (Quy trình chuyển đổi bài toán Tối ưu sang bài toán Quyết định $ABP(G, k)$, sơ đồ khối Binary Search và Incremental Search).
* **Tùng:** Viết **Chương 4.1, 4.2, 4.4 & 4.5**:
  * Chi tiết mô hình Direct Encoding, công thức hóa các ràng buộc ALO/AMO cải tiến (Sequential Counter / Commander).
  * Chi tiết mô hình **Staircase Sequential Counter Encoding (SCL)** (SCAMO, khối AMO/AMZ, tách biến đỉnh, độ phức tạp $O(|V|\cdot n)$).
  * Chi tiết mô hình quy hoạch ràng buộc Constraint Programming (**Google OR-Tools CP-SAT**).
* **Lợi:** Viết **Chương 4.3**:
  * Cơ sở toán học của Symmetry Breaking và chứng minh thu hẹp 50% không gian tìm kiếm.
  * Xây dựng đề cương đánh giá thực nghiệm đa chiều (Runtime, Clause Count, Speedup) và cơ chế Timeout/Incremental Tracking.

#### Nhiệm vụ Thuyết trình:
* **Tường, Tùng, Lợi:** Hoàn thiện bản nháp chi tiết của Slide Phần 1, 2, 3 tương ứng với nội dung kỹ thuật đã viết trong báo cáo.

---

### TUẦN 3: Thực Nghiệm Quy Mô Lớn, Hoàn Thiện Báo Cáo & Thuyết Trình

#### Nhiệm vụ Code:
* **Tường:**
  * Thu thập và chuẩn hóa bộ dữ liệu kiểm thử kích thước lớn đầy đủ (các ma trận lớn từ $n = 30$ đến $n > 100$).
  * Phối hợp kiểm thử chéo (cross-validation) đảm bảo mọi nghiệm trả về từ SAT (Direct, Staircase SCL) và CP-SAT đều vượt qua hàm Verifier và bộ unit test (`pytest`).
* **Tùng:**
  * Chạy benchmark mô hình **Staircase SCL Encoding** và **Google OR-Tools CP-SAT** trên toàn bộ tập dữ liệu để lấy thời gian CPU, số lượng biến/mệnh đề và nghiệm tối ưu làm mốc đối chứng.
  * Đóng gói mã nguồn sạch, hoàn thiện `README.md` hướng dẫn cài đặt và chạy thử nghiệm (`--encoding scl`, `--method incremental`, `--merge`).
* **Lợi:**
  * Chạy benchmark toàn diện: **SAT Direct Encoding vs. SAT Staircase SCL vs. CP-SAT** với `cadical153`; bật/tắt **Symmetry Breaking**; so sánh chiến lược tìm kiếm (`binary` vs `incremental`).
  * Sử dụng thư viện bắt buộc **`cnsplots`** để vẽ các biểu đồ chất lượng cao (thời gian giải, số lượng mệnh đề, tỷ lệ tăng tốc speedup) đưa trực tiếp vào bài báo khoa học.

#### Nhiệm vụ Báo cáo:
* **Tường:** Hoàn thiện phần mở đầu, tóm tắt (Abstract), danh mục tài liệu tham khảo và mục **Data Availability** (link GitHub Repository lưu mã nguồn và dataset). Gom toàn bộ file LaTeX `cas-sc` và kiểm tra biên dịch không lỗi.
* **Tùng:** Chèn các bảng số liệu thực nghiệm chi tiết giữa SAT và CP-SAT vào **Chương 5 (Kết quả thực nghiệm)**.
* **Lợi:** Soạn phần **Phân tích và Thảo luận kết quả**:
  * Đánh giá tại sao SAT vượt trội hoặc kém hơn CP-SAT ở các mật độ đồ thị khác nhau.
  * Đánh giá hiệu quả giảm thời gian của Symmetry Breaking và ưu nhược điểm giữa Direct Encoding vs Staircase SCL Encoding.
  * Viết **Kết luận chung** và hướng phát triển đề tài.
* **Cả 3 thành viên:** Rà soát, hiệu đính toàn bộ báo cáo khoa học theo chuẩn Elsevier trước khi nộp.

#### Nhiệm vụ Thuyết trình & Demo:
* **Tường (Phần 1 - ~5 phút):** Giới thiệu bài toán ABP, động lực nghiên cứu, chiến lược tìm kiếm (Binary Search, Incremental Search).
* **Tùng (Phần 2 - ~5 phút):** Trình bày kỹ thuật mô hình hóa SAT (Direct Encoding, ALO/AMO nâng cao, Staircase SCL Encoding) và mô hình hóa CP-SAT.
* **Lợi (Phần 3 - ~5 phút):** Trình bày kỹ thuật Symmetry Breaking, cơ chế Hard Timeout đa tiến trình, phân tích biểu đồ thực nghiệm vẽ bởi **`cnsplots`** và **trực tiếp Demo chạy chương trình**.
* **Cả 3 thành viên:** Tham gia phần hỏi đáp (Q&A) phản biện trước hội đồng/giảng viên.

---

## 3. Bảng Theo Dõi Tiến Độ & Tiêu Chí Đánh Giá (Checklist)

| Nội dung | Đầu ra mong đợi (Deliverables) | Người phụ trách chính | Deadline | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Parser & Large Data** | Module đọc file ma trận + Bộ dữ liệu ma trận lớn | Tường | Cuối Tuần 1 | ✅ Hoàn thành |
| **SAT Encoder** | Module CNF Pairwise/Direct Encoding | Tùng | Cuối Tuần 1 | ✅ Hoàn thành |
| **Solver Pipeline** | Pipeline SAT Solver (PySAT `cadical153` + Kissat) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Data Specification** | Đặc tả dữ liệu ma trận kiểm thử chuẩn (Báo cáo) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Slide Phác Thảo 3** | Nội dung Slide 11–15 (Nâng cao & Thực nghiệm) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Symmetry Breaking** | Module cắt tỉa không gian đối xứng | Lợi | Giữa Tuần 2 | ✅ Hoàn thành (Vượt tiến độ) |
| **CP-SAT Solver** | Mô hình giải chính xác bằng Google OR-Tools CP-SAT | Tùng | Cuối Tuần 2 | ✅ Hoàn thành |
| **Advanced AMO/ALO** | Mã hóa CardEnc (Sequential Counter/Commander) | Tùng | Cuối Tuần 2 | ✅ Hoàn thành |
| **Staircase SCL Encoding** | Mô hình mã hóa bậc thang `src/scl_encoder.py` (`--encoding scl`) | Tùng | Cuối Tuần 2 | ✅ Hoàn thành |
| **Incremental Search & Hard Timeout** | Tìm kiếm tăng dần (`--method incremental`), `multiprocessing` timeout & `--merge` | Tường & Lợi | Cuối Tuần 2 | ✅ Hoàn thành |
| **cnsplots Visualizer** | Module vẽ đồ thị nghiệm & biểu đồ benchmark | Lợi | Cuối Tuần 2 | ✅ Hoàn thành (Vượt tiến độ) |
| **Draft Báo cáo 1** | Chương 1, 2 và khung Template Elsevier `cas-sc` | Tường & Tùng | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **Draft Báo cáo 2** | Chương 3 & Chương 4 (Direct + Staircase SCL + CP-SAT) | Cả 3 | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **Benchmark Suite** | Bảng số liệu 3 phương pháp (Direct, SCL, CP-SAT) trên ma trận lớn | Tùng & Lợi | Giữa Tuần 3 | ✅ Hoàn thành |
| **Slide Báo cáo** | Hoàn thiện bộ slide thuyết trình | Cả 3 | Giữa Tuần 3 | ⏳ Chưa bắt đầu |
| **Final Elsevier Paper** | Báo cáo hoàn chỉnh chuẩn `cas-sc` + link GitHub | Cả 3 (Tường gom) | Cuối Tuần 3 | ⏳ Chưa bắt đầu |
| **Rehearsal & Demo** | Thử thuyết trình khớp thời gian + Kịch bản Demo | Cả 3 | Trước ngày nộp | ⏳ Chưa bắt đầu |
