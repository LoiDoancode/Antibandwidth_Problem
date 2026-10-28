# PHÁC THẢO NỘI DUNG SLIDE THUYẾT TRÌNH (PHẦN 3 - SLIDE 11 ĐẾN 15)
## BÀI TẬP LỚN SỐ 2 - MÔN CÁC VẤN ĐỀ HIỆN ĐẠI KHMT
**Thành viên phụ trách:** Lợi  
**Thời lượng dự kiến:** ~5 phút  
**Chủ đề:** Kỹ Thuật Tối Ưu Nâng Cao, Thực Nghiệm Đa Solver & Demo Trực Quan Hóa

---

### SLIDE 11: Kỹ Thuật Phá Vỡ Đối Xứng (Symmetry Breaking)
* **Tiêu đề Slide:** Cắt Tỉa Không Gian Tìm Kiếm Bằng Phá Vỡ Đối Xứng (Symmetry Breaking)
* **Điểm cốt lõi:**
  * **Tính đối xứng gương (Reflection Symmetry):** Với bất kỳ nghiệm gán nhãn hợp lệ $f: V \to \{1..n\}$ có khoảng cách $\ge k$, hoán vị lật ngược $f'(u) = n + 1 - f(u)$ cũng cho khoảng cách $|f'(u) - f'(v)| = |f(u) - f(v)| \ge k$.
  * **Hậu quả nếu không cắt đối xứng:** Khi bài toán ở ngưỡng $k$ là vô nghiệm (UNSAT), SAT solver phải duyệt toàn bộ hai nửa không gian đối xứng giống hệt nhau, gây lãng phí 50% thời gian CPU.
  * **Giải pháp đề xuất:** Chọn đỉnh $v_0$ có bậc lớn nhất trong đồ thị $\deg(v_0) = \Delta(G)$ và ép $v_0$ chỉ được nằm ở nửa đầu dải vị trí:
    $$f(v_0) \le \left\lceil \frac{n}{2} \right\rceil \iff \neg x_{v_0, p} \quad \left(\forall p > \left\lceil \frac{n}{2} \right\rceil\right)$$
* **Ghi chú thuyết trình (Speaker Notes):**
  *"Kính thưa thầy cô và các bạn, bài toán gán nhãn tuyến tính luôn tồn tại tính đối xứng lật ngược. Bằng cách ghim đỉnh có bậc cao nhất vào nửa đầu dải vị trí chỉ với một vài mệnh đề đơn vị, chúng ta lập tức triệt tiêu hoàn toàn một nửa cây tìm kiếm đối xứng, giúp solver phát hiện trạng thái UNSAT nhanh gấp đôi."*

---

### SLIDE 12: Phương Pháp Order Encoding Cho Bài Toán Antibandwidth
* **Tiêu đề Slide:** Mô Hình Hóa Biến Thứ Tự (Order Encoding Formulation)
* **Điểm cốt lõi:**
  * Thay vì sử dụng biến Boolean nguyên tử $x_{v, p}$ ($v$ ở đúng vị trí $p$), mô hình sử dụng biến thứ tự:
    $$y_{v, p} \iff f(v) \le p \quad (1 \le p \le n-1)$$
  * **Ưu điểm vượt trội:**
    1. *Ràng buộc đơn điệu:* $\neg y_{v, p} \lor y_{v, p+1}$ phản ánh bản chất thứ tự tự nhiên của vị trí.
    2. *Ràng buộc khoảng cách compact (Tamura et al.):* Khi $u \le p$ và $v > p$, thì $v \ge p + k$:
       $$\neg y_{u, p} \lor y_{v, p} \lor \neg y_{v, p+k-1}$$
    3. *Hỗ trợ Unit Propagation cực mạnh:* Khi gán $y_{v, p} = \text{True}$, tất cả các biến $y_{v, q}$ ($q > p$) tự động suy diễn sang True mà không cần phân nhánh quyết định.
* **Hình ảnh minh họa:** Sơ đồ bậc thang của Order Encoding so sánh với ma trận biến $n \times n$ của Direct Encoding.

---

### SLIDE 13: Thiết Lập Thực Nghiệm & Đối Chuẩn Với Google OR-Tools CP-SAT
* **Tiêu đề Slide:** Thiết Kế Hệ Thống Thực Nghiệm Đa Phương Pháp (Experimental Design)
* **Điểm cốt lõi:**
  * **Đáp ứng trọn vẹn yêu cầu so sánh của BTL 2:** So sánh SAT Solving với phương pháp giải chính xác khác (Constraint Programming).
  * **Các phương pháp tham gia đối chuẩn:**
    1. *SAT Direct Encoding* (Solver: Glucose4 / CaDiCaL).
    2. *SAT Order Encoding* (Solver: Glucose4 / CaDiCaL).
    3. *Google OR-Tools CP-SAT* (Mô hình Integer Programming / CP với biến miền nguyên `IntVar` và `AddAllDifferent`).
  * **Tập dữ liệu kiểm thử:** Bộ ma trận chuẩn Harwell-Boeing với quy mô từ nhỏ ($n = 5, 6$) đến các đồ thị kích thước lớn ($n = 24, 48, 59, 85, 100$).
* **Tiêu chí đánh giá:** Thời gian giải CPU (giây), số lượng biến/mệnh đề sinh ra, và tỷ lệ tăng tốc khi có Symmetry Breaking.

---

### SLIDE 14: Trực Quan Hóa Nghiệm Bằng Thư Viện Chuẩn `cnsplots`
* **Tiêu đề Slide:** Trực Quan Hóa Đồ Thị Nghiệm Chuẩn Xuất Bản Khoa Học (`cnsplots`)
* **Điểm cốt lõi:**
  * Áp dụng thư viện bắt buộc **`cnsplots`** theo chuẩn hiển thị tạp chí quốc tế (Nature/Science style).
  * **Mô hình trực quan 2 khung nhìn (Dual Visualization):**
    * *Khung 1 (Network Topology):* Đồ thị mạng tròn với nhãn đỉnh $v: f(v)$, tô đỏ các cạnh nút thắt (critical edges) có khoảng cách đạt đúng giá trị tối ưu $k^*$.
    * *Khung 2 (1D Linear Arc Placement):* Các đỉnh trải dọc theo trục hoành $1 \dots n$, các cạnh vẽ thành các cung cong (arcs) chứng minh trực quan tất cả các cung đều có độ sải ngang $\ge k^*$.
* **Hình ảnh minh họa:** Ảnh chụp biểu đồ nghiệm của đồ thị `sample_p6` hoặc `can_24` do file `src/visualizer.py` tự động xuất ra.

---

### SLIDE 15: Kịch Bản Demo Trực Tiếp & Kết Luận
* **Tiêu đề Slide:** Trình Diễn Mã Nguồn (Live Demo) & Kết Luận Đề Tài
* **Kịch bản Demo trực tiếp (Live Terminal Execution):**
  1. Chạy lệnh giải đồ thị với cờ `--visualize` để hiển thị sơ đồ ASCII và mở ảnh kết quả:
     ```bash
     python main.py --input data/sample_p6.mtx --visualize solution_p6.png
     ```
  2. Chạy lệnh kiểm thử so sánh giữa Direct Encoding và Order Encoding:
     ```bash
     python main.py --input data/sample_c5.mtx --encoding order
     ```
  3. Trình chiếu bảng thống kê và biểu đồ tự động sinh từ [benchmark.py](file:///c:/game/HK1_Nam3_2026/CVDHDKHMT/AntiBandWidth/Antibandwidth_Problem/benchmark.py).
* **Kết luận & Đóng góp:**
  * Xây dựng thành công framework giải quyết trọn vẹn bài toán Antibandwidth bằng SAT Solving và CP-SAT.
  * Báo cáo khoa học hoàn thiện theo đúng chuẩn **Elsevier (`cas-sc`)** với mã nguồn mở công khai tại GitHub.
  * Sẵn sàng chuyển sang phần hỏi đáp (Q&A).
