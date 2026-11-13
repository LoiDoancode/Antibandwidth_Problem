# Bài Toán Antibandwidth (ABP) - SAT Solver Framework

[![Antibandwidth SAT CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

Hệ thống nghiên cứu và thực nghiệm giải quyết **Bài toán Antibandwidth (Antibandwidth Problem - ABP)** (hay còn gọi là bài toán *Đánh số đỉnh vi phân cực đại - Maximum Differential Graph Labeling*) dựa trên công nghệ **Bộ giải thỏa công thức Boolean (SAT Solvers)** và **Thuật toán Tìm kiếm nhị phân (Binary Search)**.

Dự án phục vụ môn học **Các vấn đề hiện đại trong Khoa học máy tính**.

---

## 📌 Chuẩn Hóa Môi Trường Phát Triển

> [!IMPORTANT]
> **Phiên bản Python thống nhất cho toàn bộ nhóm:** **`Python 3.11`**  
> * **Lý do:** Đảm bảo 100% các thư viện giải thuật C/C++ (`python-sat`, `ortools`, `scipy`) đều có sẵn gói cài đặt nhị phân (pre-built wheels) ổn định trên cả Windows, Linux và macOS mà không gặp lỗi biên dịch; đồng thời tận dụng cải tiến tốc độ thực thi 15–25% của Python 3.11.

---

## 🚀 Các Tính Năng Cốt Lõi

* **Mô hình hóa SAT đa phương pháp:**
  * **Direct Encoding**: Biểu diễn biến vị trí nhị phân $x_{v, p}$ ($v$ đặt tại vị trí $p$) với các ràng buộc ALO/AMO song ánh.
  * **Order Encoding (Tamura et al.)**: Biểu diễn biến thứ tự $y_{v, p}$ ($f(v) \le p$) hỗ trợ lan truyền biên khoảng cách mạnh mẽ qua Unit Propagation.
* **Kỹ thuật phá vỡ đối xứng (Symmetry Breaking):**
  * Ghim đỉnh có bậc cao nhất $\Delta(G)$ vào nửa đầu dải vị trí $f(v_0) \le \lceil n/2 \rceil$, triệt tiêu 50% không gian tìm kiếm đối xứng gương.
* **Tích hợp đa dạng Solver:**
  * Hỗ trợ trực tiếp các backend PySAT hàng đầu: **Glucose 4**, **CaDiCaL**, **Minisat22**.
  * Hỗ trợ giao diện gọi solver độc lập bên ngoài (Kissat CLI).
* **Kiểm chứng nghiệm tự động (`verify_solution`):**
  * Tự động xác thực tính toàn vẹn của hoán vị và kiểm tra khoảng cách mọi cạnh $|f(u) - f(v)| \ge k$.
* **Trực quan hóa khoa học (`cnsplots` & Matplotlib):**
  * Xuất sơ đồ vị trí tuyến tính 1D (ASCII & PNG) làm nổi bật các cạnh nút thắt (*critical/bottleneck edges*).
  * Vẽ biểu đồ so sánh đa thuật toán phục vụ báo cáo khoa học chuẩn xuất bản.
* **Tự động hóa CI/CD (GitHub Actions):**
  * Tự động lint cú pháp (`flake8`) và chạy toàn bộ 29 bài test (`pytest`) trên máy chủ mỗi khi push code.

---

## 📦 Cài Đặt Môi Trường

1. **Clone repository về máy:**
   ```bash
   git clone https://github.com/OWNER/REPO.git
   cd Antibandwidth_Problem
   ```

2. **Cài đặt toàn bộ thư viện phụ thuộc:**
   *(Bao gồm cả thư viện giải thuật, trực quan hóa và bộ công cụ kiểm thử `pytest`)*
   ```bash
   pip install -r requirements.txt
   ```

---

## 🧪 Chạy Kiểm Thử Tự Động (Pytest)

Chạy bộ test suite tự động tại máy cá nhân trước khi push code:

```bash
# Chạy toàn bộ 29 bài kiểm tra
pytest

# Chạy với thông tin hiển thị chi tiết
pytest -v

# Chạy kiểm thử kèm báo cáo độ phủ mã nguồn (Code Coverage)
pytest --cov=src
```

### Các nhóm kiểm thử tự động gồm:
1. **Thuật toán & Nghiệm lý thuyết (`test_solver.py`)**: Kiểm tra đồ thị mẫu đã biết trước đáp số ($P_4, C_5, K_n$), kiểm tra tính tương đương Direct vs Order, kiểm thử hàm xác minh nghiệm.
2. **Bộ mã hóa SAT (`test_encoders.py`)**: Kiểm tra sinh mệnh đề ALO, AMO, tính đơn điệu của Order Encoding và Symmetry Breaking.
3. **Bộ đọc dữ liệu đồ thị (`test_graph_loader.py`)**: Kiểm tra đọc file Matrix Market (`.mtx`), Harwell-Boeing (`.txt`, `.rb`), Edge list.
4. **Giao diện dòng lệnh (`test_cli.py`)**: Smoke test cho `main.py` và `benchmark.py`.
5. **Kịch bản nâng cao tuần 1 & 2 (`test_week1_...`, `test_week2_...`)**: Kiểm tra PySAT backends, export DIMACS `.cnf`, Binary/Linear search, và module vẽ đồ thị.

---

## 💻 Hướng Dẫn Sử Dụng (CLI)

### 1. Tìm nghiệm tối ưu bằng Binary Search (Direct Encoding)
```bash
python main.py --input data/sample_p6.mtx --solver glucose4
```

### 2. Giải bằng Order Encoding
```bash
python main.py --input data/sample_c5.mtx --encoding order
```

### 3. Kiểm tra tính thỏa tại một ngưỡng $k$ cụ thể
```bash
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --check-k 2
```

### 4. Giải và xuất ảnh trực quan hóa nghiệm
```bash
python main.py --input data/sample_p6.mtx --visualize solution_p6.png
```

### 5. Chạy đối chuẩn so sánh (Benchmark) trên tập dữ liệu
```bash
python benchmark.py --data-dir data/instance/harwell-boeing_v2 --output-csv benchmark_results.csv --plot benchmark_chart.png
```
