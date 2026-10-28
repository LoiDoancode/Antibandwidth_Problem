# KẾ HOẠCH PHÂN CÔNG DỰ ÁN: BÀI TOÁN ANTIBANDWIDTH (ABP)
## BÀI TẬP LỚN SỐ 2 - MÔN CÁC VẤN ĐỀ HIỆN ĐẠI KHMT (HK I 2026 - 2027)

* **Topic 5:** Antibandwidth Problem (ABP)
* **Thời lượng thực hiện:** 3 tuần
* **Thành viên:** Tường, Tùng, Lợi
* **Mục tiêu:** 
  1. Cài đặt các phương pháp mã hóa SAT: **Pairwise (Direct) Encoding** và **Order Encoding** (có tối ưu ALO/AMO nâng cao).
  2. Xây dựng mô hình giải chính xác đối chứng bằng **Constraint Programming (Google OR-Tools CP-SAT)** để so sánh hiệu năng với SAT.
  3. Thực nghiệm đánh giá trên các ma trận có kích thước lớn từ tập chuẩn Harwell-Boeing.
  4. Trực quan hóa dữ liệu và kết quả thực nghiệm bằng thư viện bắt buộc **`cnsplots`** (`https://cnsplots.farid.one/latest/`).
  5. Xuất bản báo cáo khoa học theo đúng **Template LaTeX của nhà xuất bản Elsevier (`cas-sc`)** và đính kèm link GitHub Repository trong mục **"Data Availability"**.

---

## 1. Nguyên Tắc Phân Chia Đồng Đều (Workload Balance)

| Trụ cột | Tường | Tùng | Lợi |
| :--- | :--- | :--- | :--- |
| **1. Code & Thuật toán** | - Parser đồ thị Harwell-Boeing.<br>- Bổ sung tập dữ liệu ma trận lớn.<br>- Bộ kiểm tra tính hợp lệ của nghiệm (Verifier). | - Direct Encoding (Pairwise).<br>- Tối ưu ALO/AMO nâng cao (Sequential Counter / Commander qua PySAT `CardEnc`).<br>- Xây dựng mô hình đối chuẩn **Google OR-Tools CP-SAT**. | - Pipeline SAT Solver (PySAT + Kissat/CaDiCaL).<br>- Kỹ thuật Phá vỡ đối xứng (Symmetry Breaking).<br>- Cài đặt **Order Encoding**.<br>- Trực quan hóa đồ thị & biểu đồ bằng **`cnsplots`**. |
| **2. Báo cáo (Report)** | - Khởi tạo Template Elsevier (`cas-sc`).<br>- Soạn Chương 1 & 2 (Tổng quan bài toán, ứng dụng thực tế).<br>- Biên tập mục **Data Availability** (Link GitHub) & Abstract. | - Soạn Chương 3 & 4.1 - 4.2:<br>  + Chuyển đổi tối ưu sang SAT & mô hình CP-SAT.<br>  + Chi tiết các hệ ràng buộc ALO/AMO nâng cao & khoảng cách. | - Soạn Chương 4.3 - 5:<br>  + Cơ chế Symmetry Breaking & Order Encoding.<br>  + Phân tích so sánh thực nghiệm SAT vs CP-SAT.<br>  + Nhận xét ưu/nhược điểm & Kết luận. |
| **3. Thuyết trình (Presentation)** | - Thiết kế Slide Phần 1 (Đặt vấn đề, mô hình hóa toán học, ứng dụng).<br>- Thuyết trình Mở đầu (Tuần 3). | - Thiết kế Slide Phần 2 (Công thức hóa SAT, ALO/AMO nâng cao, mô hình CP-SAT).<br>- Thuyết trình Kỹ thuật (Tuần 3). | - Thiết kế Slide Phần 3 (Symmetry Breaking, Order Encoding, kết quả so sánh với CP-SAT qua biểu đồ `cnsplots`).<br>- Thuyết trình Kết luận & Demo chương trình. |

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
  * Cấu hình môi trường SAT Solver: tích hợp `python-sat` (PySAT), hỗ trợ các backend solver (`glucose4`, `cadical153`, `minisat22`).
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

### TUẦN 2: Cài Đặt Thuật Toán Nâng Cao, CP-SAT & Order Encoding

#### Nhiệm vụ Code:
* **Tường:**
  * Cài đặt cơ chế kiểm soát chặn cận: cận trên lý thuyết $k_{max} = \lfloor n/2 \rfloor$, cận dưới $k_{min} = 1$.
  * Tích hợp chiến lược tìm kiếm nhị phân (Binary Search) và tìm kiếm tuần tự (Linear Search) qua các ngưỡng $k$.
* **Tùng:**
  * Cài đặt hệ mệnh đề ràng buộc khoảng cách Antibandwidth: $\neg x_{u,p} \lor \neg x_{v,q}$ ($\forall \{u,v\} \in E, |p - q| < k$).
  * **Nâng cao ALO/AMO (Khuyến khích trong đề bài):** Tích hợp kỹ thuật mã hóa hồng hào hơn (như *Sequential Counter* hoặc *Commander* thông qua `pysat.card.CardEnc`) nhằm giảm số lượng mệnh đề từ $O(n^2)$ xuống $O(n)$ trên các ma trận lớn.
  * **Mô hình hóa CP-SAT (Bắt buộc trong đề bài):** Viết module giải bài toán bằng **Google OR-Tools CP-SAT** (`src/cp_solver.py`) sử dụng biến miền nguyên `IntVar` và ràng buộc `AddAllDifferent`, làm đối trọng so sánh với SAT.
* **Lợi:**
  * Cài đặt kỹ thuật **Phá vỡ đối xứng (Symmetry Breaking)**: ghim đỉnh có bậc lớn nhất $v_0$ vào nửa đầu dải vị trí $\neg x_{v_0, p}$ ($\forall p > \lceil n/2 \rceil$).
  * Cài đặt hoàn chỉnh mô hình **Order Encoding** (`y_{i, p} \iff f(i) \le p`) với các mệnh đề đơn điệu và lan truyền khoảng cách theo mô hình Tamura et al.
  * Bổ sung cơ chế xuất đồ thị minh họa nghiệm bằng **`cnsplots`** (sơ đồ 1D Linear Arc Placement và cấu trúc đồ thị).

#### Nhiệm vụ Báo cáo:
* **Tường:** Viết **Chương 3**: Quy trình chuyển đổi bài toán Tối ưu sang bài toán Quyết định $ABP(G, k)$, sơ đồ khối thuật toán Binary Search.
* **Tùng:** Viết **Chương 4.1 & 4.2**:
  * Chi tiết mô hình Direct Encoding, công thức hóa các ràng buộc ALO/AMO cải tiến (Sequential Counter / Commander).
  * Chi tiết mô hình quy hoạch ràng buộc Constraint Programming (**Google OR-Tools CP-SAT**).
* **Lợi:** Viết **Chương 4.3 & 4.4**:
  * Cơ sở toán học của Symmetry Breaking và chứng minh thu hẹp 50% không gian tìm kiếm.
  * Chi tiết công thức hóa Order Encoding và so sánh lý thuyết về độ phức tạp mệnh đề với Direct Encoding.

#### Nhiệm vụ Thuyết trình:
* **Tường, Tùng, Lợi:** Hoàn thiện bản nháp chi tiết của Slide Phần 1, 2, 3 tương ứng với nội dung kỹ thuật đã viết trong báo cáo.

---

### TUẦN 3: Thực Nghiệm Quy Mô Lớn, Hoàn Thiện Báo Cáo & Thuyết Trình

#### Nhiệm vụ Code:
* **Tường:**
  * Thu thập và chuẩn hóa bộ dữ liệu kiểm thử kích thước lớn đầy đủ (các ma trận lớn từ $n = 30$ đến $n > 100$).
  * Phối hợp kiểm thử chéo (cross-validation) đảm bảo mọi nghiệm trả về từ SAT và CP-SAT đều vượt qua hàm Verifier.
* **Tùng:**
  * Chạy benchmark mô hình **Google OR-Tools CP-SAT** trên toàn bộ tập dữ liệu để lấy thời gian CPU và nghiệm tối ưu làm mốc đối chứng.
  * Đóng gói mã nguồn sạch, hoàn thiện `README.md` hướng dẫn cài đặt và chạy thử nghiệm.
* **Lợi:**
  * Chạy benchmark toàn diện: **SAT Direct Encoding vs. SAT Order Encoding vs. CP-SAT**; bật/tắt **Symmetry Breaking**; so sánh giữa các SAT solver backend (`glucose4` vs `cadical153`).
  * Sử dụng thư viện bắt buộc **`cnsplots`** để vẽ các biểu đồ chất lượng cao (thời gian giải, số lượng mệnh đề, tỷ lệ tăng tốc speedup) đưa trực tiếp vào bài báo khoa học.

#### Nhiệm vụ Báo cáo:
* **Tường:** Hoàn thiện phần mở đầu, tóm tắt (Abstract), danh mục tài liệu tham khảo và mục **Data Availability** (link GitHub Repository lưu mã nguồn và dataset). Gom toàn bộ file LaTeX `cas-sc` và kiểm tra biên dịch không lỗi.
* **Tùng:** Chèn các bảng số liệu thực nghiệm chi tiết giữa SAT và CP-SAT vào **Chương 5 (Kết quả thực nghiệm)**.
* **Lợi:** Soạn phần **Phân tích và Thảo luận kết quả**:
  * Đánh giá tại sao SAT vượt trội hoặc kém hơn CP-SAT ở các mật độ đồ thị khác nhau.
  * Đánh giá hiệu quả giảm thời gian của Symmetry Breaking và ưu nhược điểm giữa Direct Encoding vs Order Encoding.
  * Viết **Kết luận chung** và hướng phát triển đề tài.
* **Cả 3 thành viên:** Rà soát, hiệu đính toàn bộ báo cáo khoa học theo chuẩn Elsevier trước khi nộp.

#### Nhiệm vụ Thuyết trình & Demo:
* **Tường (Phần 1 - ~5 phút):** Giới thiệu bài toán ABP, động lực nghiên cứu, ứng dụng vi mạch và phân bổ tần số.
* **Tùng (Phần 2 - ~5 phút):** Trình bày kỹ thuật mô hình hóa SAT (Direct Encoding, ALO/AMO nâng cao) và mô hình hóa CP-SAT.
* **Lợi (Phần 3 - ~5 phút):** Trình bày Symmetry Breaking, Order Encoding, phân tích biểu đồ thực nghiệm vẽ bởi **`cnsplots`** và **trực tiếp Demo chạy chương trình**.
* **Cả 3 thành viên:** Tham gia phần hỏi đáp (Q&A) phản biện trước hội đồng/giảng viên.

---

## 3. Bảng Theo Dõi Tiến Độ & Tiêu Chí Đánh Giá (Checklist)

| Nội dung | Đầu ra mong đợi (Deliverables) | Người phụ trách chính | Deadline | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Parser & Large Data** | Module đọc file ma trận + Bộ dữ liệu ma trận lớn | Tường | Cuối Tuần 1 | 🔄 Đang hoàn thiện |
| **SAT Encoder** | Module CNF Pairwise/Direct Encoding | Tùng | Cuối Tuần 1 | ✅ Hoàn thành |
| **Solver Pipeline** | Pipeline SAT Solver (PySAT + Kissat/CaDiCaL) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Data Specification** | Đặc tả dữ liệu ma trận kiểm thử chuẩn (Báo cáo) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Slide Phác Thảo 3** | Nội dung Slide 11–15 (Nâng cao & Thực nghiệm) | Lợi | Cuối Tuần 1 | ✅ Hoàn thành |
| **Order Encoding** | Module mã hóa thứ tự Order Encoding | Lợi | Giữa Tuần 2 | ✅ Hoàn thành (Vượt tiến độ) |
| **Symmetry Breaking** | Module cắt tỉa không gian đối xứng | Lợi | Giữa Tuần 2 | ✅ Hoàn thành (Vượt tiến độ) |
| **CP-SAT Solver** | Mô hình giải chính xác bằng Google OR-Tools CP-SAT | Tùng | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **Advanced AMO/ALO** | Mã hóa CardEnc (Sequential Counter/Commander) | Tùng | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **cnsplots Visualizer** | Module vẽ đồ thị nghiệm & biểu đồ benchmark | Lợi | Cuối Tuần 2 | ✅ Hoàn thành (Vượt tiến độ) |
| **Draft Báo cáo 1** | Chương 1, 2 và khung Template Elsevier `cas-sc` | Tường & Tùng | Cuối Tuần 1 | ⏳ Chưa bắt đầu |
| **Draft Báo cáo 2** | Chương 3 & Chương 4 (SAT + CP-SAT + Order) | Cả 3 | Cuối Tuần 2 | ⏳ Chưa bắt đầu |
| **Benchmark Suite** | Bảng số liệu SAT vs CP-SAT trên ma trận lớn | Tùng & Lợi | Giữa Tuần 3 | ⏳ Chưa bắt đầu |
| **Slide Báo cáo** | Hoàn thiện bộ slide thuyết trình | Cả 3 | Giữa Tuần 3 | ⏳ Chưa bắt đầu |
| **Final Elsevier Paper** | Báo cáo hoàn chỉnh chuẩn `cas-sc` + link GitHub | Cả 3 (Tường gom) | Cuối Tuần 3 | ⏳ Chưa bắt đầu |
| **Rehearsal & Demo** | Thử thuyết trình khớp thời gian + Kịch bản Demo | Cả 3 | Trước ngày nộp | ⏳ Chưa bắt đầu |