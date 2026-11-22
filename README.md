# Bài Toán Antibandwidth (ABP) - SAT & CP-SAT Solver Framework

[![Antibandwidth SAT CI](https://github.com/LoiDoancode/Antibandwidth_Problem/actions/workflows/ci.yml/badge.svg)](https://github.com/LoiDoancode/Antibandwidth_Problem/actions/workflows/ci.yml)

Hệ thống nghiên cứu và thực nghiệm giải quyết **Bài toán Antibandwidth (Antibandwidth Problem - ABP)** (hay bài toán *Đánh số đỉnh vi phân cực đại - Maximum Differential Graph Labeling*) bằng các phương pháp **Mã hóa SAT nâng cao (Direct + CardEnc/Commander, Staircase SCL)** kết hợp **Tìm kiếm nhị phân / Tìm kiếm tăng dần (Binary & Incremental Search)** và mô hình đối chứng **Constraint Programming (Google OR-Tools CP-SAT)**.

Dự án phục vụ **Bài tập lớn số 2** — môn **Các vấn đề hiện đại trong Khoa học máy tính (HK I 2026–2027)**.

---

## 📌 Chuẩn Hóa Môi Trường Phát Triển

> [!IMPORTANT]
> **Phiên bản Python thống nhất cho toàn bộ nhóm:** **`Python 3.11`**  
> * **Lý do:** Đảm bảo 100% các thư viện giải thuật C/C++ (`python-sat`, `ortools`, `scipy`) đều có sẵn gói cài đặt nhị phân (pre-built wheels) ổn định trên Windows, Linux và macOS mà không gặp lỗi biên dịch.

---

## 🚀 Các Tính Năng Cốt Lõi

* **Mô hình hóa SAT đa phương pháp:**
  * **Direct Encoding (`src/sat_encoder.py`)**: Biểu diễn biến vị trí nhị phân $x_{v, p}$ ($v$ đặt tại vị trí $p$) cùng tối ưu **AMO nâng cao** (`--amo-encoding`): `pairwise`, `seqcounter`, `commander`, `totalizer`, `ladder`, `bitwise`.
  * **Staircase Sequential Counter Encoding — SCL (`src/scl_encoder.py`)**: Cài đặt mô hình bậc thang theo Truong et al. (ICAART 2025), phân rã SCAMO theo cửa sổ trượt $w = k$ và tách biến đỉnh giúp giảm số mệnh đề xuống $\mathcal{O}(|V| \cdot n)$, tránh tràn bộ nhớ (`OOM`) trên đồ thị lớn.
* **Mô hình đối chứng CP-SAT (`src/cp_solver.py`):**
  * Giải chính xác bằng **Google OR-Tools CP-SAT** với biến miền nguyên `IntVar`, ràng buộc toàn cục `AddAllDifferent`, `AddAbsEquality` và 2 chế độ `direct_optimize` / `binary_search`.
* **Tính cận mức 1 & Chiến lược tìm kiếm (`src/bounds.py`, `src/solver.py`):**
  * Tự động tính cận trên toán học $UB$ theo $\Delta(G), \delta(G)$ và cận dưới tham lam $LB$ kèm nghiệm khả thi ban đầu.
  * Hỗ trợ **Binary Search** (`--method binary_search`), **Incremental Search** (`--method incremental`, có tính chất *anytime* lưu nghiệm tốt nhất khi timeout) và **Linear Search** (`--method linear_search`).
* **Kỹ thuật phá vỡ đối xứng (Symmetry Breaking):**
  * Ghim đỉnh có bậc cao nhất $v_0 = \arg\max \deg(v)$ vào nửa đầu dải vị trí $f(v_0) \le \lceil n/2 \rceil$, triệt tiêu 50% không gian tìm kiếm đối xứng gương.
* **Tích hợp đa dạng Solver & Hard Timeout:**
  * Hỗ trợ backend PySAT (`cadical153`, `glucose4`, `minisat22`) và solver độc lập bên ngoài (`--external-solver kissat`).
  * Hỗ trợ cô lập tiến trình con với Hard Timeout (`multiprocessing.Process`) và đồng bộ tiến độ thời gian thực trong `benchmark.py`.
* **Kiểm chứng nghiệm tự động (`verify_solution`):**
  * Tự động xác thực tính song ánh $\{1..n\}$ và kiểm tra khoảng cách mọi cạnh $|f(u) - f(v)| \ge k$.
* **Trực quan hóa khoa học (`src/visualizer.py`, `cnsplots` & Matplotlib):**
  * Xuất sơ đồ vị trí tuyến tính 1D (ASCII & PNG) làm nổi bật các cạnh nút thắt (*critical/bottleneck edges*).
  * Xuất 3 biểu đồ đối chuẩn chuẩn xuất bản: thời gian giải, số lượng mệnh đề/ràng buộc, và hệ số tăng tốc Symmetry Breaking.
* **Tự động hóa CI/CD (GitHub Actions):**
  * Tự động kiểm tra cú pháp (`flake8`), chạy toàn bộ bộ kiểm thử `pytest` và smoke test CLI mỗi khi push/PR trên Python 3.11.

---

## 📦 Cài Đặt Môi Trường

1. **Clone repository về máy:**
   ```bash
   git clone https://github.com/LoiDoancode/Antibandwidth_Problem.git
   cd Antibandwidth_Problem
   ```

2. **Cài đặt toàn bộ thư viện phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 🧪 Chạy Kiểm Thử Tự Động (Pytest)

Chạy bộ test suite tự động trong thư mục `tests/` trước khi push code:

```bash
# Chạy toàn bộ test suite
pytest

# Chạy với thông tin chi tiết từng test
pytest -v

# Chạy kiểm thử kèm báo cáo độ phủ mã nguồn
pytest --cov=src
```

### Các nhóm kiểm thử tự động gồm:
1. **Cận mức 1 (`tests/test_bounds.py`)**: Kiểm tra tính toán `LB`, `UB` và nghiệm tham lam ban đầu.
2. **Bộ mã hóa SAT (`tests/test_encoders.py`)**: Kiểm tra Direct Encoding (Pairwise, SeqCounter, Commander, Totalizer, Ladder, Bitwise), Staircase SCL Encoding và Symmetry Breaking.
3. **Bộ điều phối giải SAT (`tests/test_solver.py`)**: Kiểm tra nghiệm chuẩn trên đồ thị mẫu, tính tương đương Direct vs SCL, `verify_solution`, Binary / Linear / Incremental Search.
4. **Bộ giải CP-SAT (`tests/test_cp_solver.py`)**: Kiểm tra Google OR-Tools CP-SAT (`direct_optimize`, `binary_search`, `check_sat`) và đối chiếu chéo với SAT.
5. **Bộ đọc dữ liệu đồ thị (`tests/test_graph_loader.py`)**: Kiểm tra đọc file Matrix Market (`.mtx`), Harwell-Boeing (`.txt`, `.rb`), Edge list.
6. **Trực quan hóa (`tests/test_visualizer.py`)**: Kiểm tra ASCII layout, xuất ảnh nghiệm và biểu đồ benchmark.
7. **Giao diện dòng lệnh (`tests/test_cli.py`)**: Smoke test cho `main.py` và `benchmark.py`.

---

## 💻 Hướng Dẫn Sử Dụng (CLI)

### 1. Giải với Direct Encoding (Pairwise / SeqCounter / Commander)
```bash
# Direct Encoding mặc định (Pairwise AMO, CaDiCaL 1.5.3)
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --solver cadical153

# Direct Encoding với AMO nâng cao (seqcounter hoặc commander)
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --encoding direct --amo-encoding seqcounter
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --encoding commander
```

### 2. Giải bằng Staircase SCL Encoding kết hợp Incremental Search
```bash
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --encoding scl --method incremental --solver cadical153
```

### 3. Giải đối chứng bằng Google OR-Tools CP-SAT
```bash
python main.py --input data/instance/harwell-boeing_v2/bcspwr01.txt --encoding cpsat --method direct_optimize
```

### 4. Kiểm tra tính thỏa tại một ngưỡng $k$ cụ thể & xuất DIMACS
```bash
python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --check-k 1
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --check-k 5 --encoding scl --export-dimacs can24_k5.cnf
```

### 5. Giải và xuất ảnh trực quan hóa nghiệm
```bash
python main.py --input data/instance/harwell-boeing_v2/can___24.txt --encoding scl --visualize docs/solution_can24.png
```

### 6. Chạy đối chuẩn Benchmark toàn diện (`benchmark.py`)
```bash
# Chạy toàn bộ bộ dữ liệu chuẩn (Direct Pairwise/Commander/SeqCounter, SCL, CP-SAT; bật/tắt Symmetry Breaking)
python benchmark.py --time-limit 1800

# Chạy bổ sung một đồ thị mới và gộp (merge) vào benchmark_results.csv hiện có
python benchmark.py -i data/instance/harwell-boeing/small/bcspwr03 --encodings scl cpsat --time-limit 1800 --merge

# Gộp và loại bỏ đồ thị cũ nếu cần trước khi vẽ lại biểu đồ
python benchmark.py --merge --drop-graphs nos3 --plot-time docs/benchmark_time_comparison.png --plot-clauses docs/benchmark_clause_comparison.png --plot-speedup docs/benchmark_speedup_comparison.png
```
