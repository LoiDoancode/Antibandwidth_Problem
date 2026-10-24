# BÁO CÁO BTL 2 - MÔN CÁC VẤN ĐỀ HIỆN ĐẠI KHMT
## ĐẶC TẢ DỮ LIỆU THỰC NGHIỆM (BENCHMARK DATA SPECIFICATION)
**Người soạn thảo:** Lợi (Phần đóng góp vào Báo cáo khoa học - Template Elsevier `cas-sc`)

---

### 1. Giới Thiệu Bộ Dữ Liệu Chuẩn Harwell-Boeing & Matrix Market

Để đánh giá thực nghiệm tính đúng đắn và hiệu năng giải bài toán Antibandwidth Problem (ABP), nhóm nghiên cứu sử dụng tập dữ liệu ma trận thưa từ **Bộ sưu tập ma trận SuiteSparse (trước đây là Harwell-Boeing Sparse Matrix Collection)**. Đây là bộ dữ liệu chuẩn mực quốc tế được sử dụng rộng rãi trong các bài toán tối ưu tổ hợp đồ thị (Graph Bandwidth, Profile Minimization, Antibandwidth).

Mỗi đồ thị vô hướng $G = (V, E)$ được biểu diễn dưới dạng ma trận kề đối xứng $A \in \{0, 1\}^{n \times n}$ lưu trữ theo định dạng chuẩn **Matrix Market (`.mtx`)**:
* Dòng tiêu đề: `%%MatrixMarket matrix coordinate pattern symmetric`.
* Dòng kích thước: `n n m` (trong đó $n = |V|$ là số đỉnh, $m = |E|$ là số cạnh).
* Các dòng tiếp theo: Mỗi dòng chứa một cặp chỉ số đỉnh `(u, v)` (đánh số từ 1 đến $n$) đại diện cho một cạnh nối giữa đỉnh $u$ và $v$.

---

### 2. Bảng Thông Số Kỹ Thuật Các Đồ Thị Kiểm Thử

Bảng dưới đây tổng hợp đặc tính cấu trúc của các đồ thị được lựa chọn trong quá trình thực nghiệm, trải dài từ các đồ thị mẫu nhỏ đến các ma trận thưa có kích thước lớn:

| Tên Đồ Thị / Ma Trận | Số đỉnh $\|V\|$ | Số cạnh $\|E\|$ | Mật độ cạnh ($D$) | Bậc cực tiểu $\delta(G)$ | Bậc cực đại $\Delta(G)$ | Bậc trung bình $\bar{d}$ | Mô tả nguồn gốc bài toán |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **sample_p6** | 6 | 5 | 0.333 | 1 | 2 | 1.67 | Đồ thị đường đi $P_6$ (Path graph) |
| **sample_c5** | 5 | 5 | 0.500 | 2 | 2 | 2.00 | Đồ thị chu trình $C_5$ (Cycle graph) |
| **can_24** | 24 | 68 | 0.246 | 3 | 9 | 5.67 | Bài toán cơ học kết cấu (Cannes collection) |
| **dwt_59** | 59 | 104 | 0.061 | 1 | 6 | 3.53 | Lưới biến đổi sóng con (Wavelet transform) |
| **bcsstk01** | 48 | 176 | 0.156 | 4 | 14 | 7.33 | Ma trận độ cứng kết cấu giàn khung tĩnh học |
| **can_61** | 61 | 248 | 0.136 | 4 | 16 | 8.13 | Ma trận kết cấu máy bay (Structural engineering) |
| **nos4** | 100 | 247 | 0.050 | 1 | 7 | 4.94 | Ma trận xấp xỉ phần tử hữu hạn |
| **ash85** | 85 | 219 | 0.061 | 2 | 10 | 5.15 | Ma trận trắc địa và bản đồ thưa |

*Ghi chú công thức tính mật độ đồ thị vô hướng:*
$$D = \frac{2 \cdot |E|}{|V| \cdot (|V| - 1)}$$

---

### 3. Phân Tích Ý Nghĩa Học Thuật & Tác Động Đến Độ Phức Tạp SAT

Các thông số cấu trúc của ma trận kiểm thử có tác động trực tiếp và sâu sắc đến hành vi của các thuật toán SAT Solving và CP-SAT:

#### 3.1. Tác động của mật độ cạnh ($D$) đến quy mô công thức CNF
* Trong mô hình **Direct Encoding**, mỗi cạnh $(u, v) \in E$ và mỗi vị trí $p \in \{1, \dots, n\}$ sẽ phát sinh các mệnh đề cấm vị trí kề cận có khoảng cách $< k$:
  $$\text{Số lượng mệnh đề khoảng cách} \approx O(|E| \cdot k)$$
* Khi mật độ cạnh $D$ cao (đồ thị dày), số lượng cạnh $|E|$ tăng lên xấp xỉ $O(n^2)$, dẫn đến kích thước file CNF bùng nổ hàng chục nghìn mệnh đề. Ngược lại, trên đồ thị dày, giá trị tối ưu $B^*(G)$ bị chặn trên rất nhỏ (thường chỉ đạt 1 hoặc 2) do hiệu ứng "lồng bồ câu" (Pigeonhole principle).

#### 3.2. Phân bố bậc đỉnh và Kỹ thuật Phá vỡ đối xứng (Symmetry Breaking)
* Độ chênh lệch giữa bậc cực đại $\Delta(G)$ và bậc cực tiểu $\delta(G)$ phản ánh mức độ bất đối xứng trong cấu trúc bậc của đồ thị.
* Khi chọn đỉnh neo $v_0$ thỏa mãn $\deg(v_0) = \Delta(G)$ để áp dụng ràng buộc phá vỡ đối xứng:
  $$f(v_0) \le \lceil n/2 \rceil$$
  Đỉnh có bậc càng cao sẽ kéo theo việc loại trừ nhiều khả năng gán nhãn cho các đỉnh lân cận nhất thông qua quá trình **Unit Propagation** của SAT solver ngay ở các bước quyết định đầu tiên (decision level thấp), giúp cắt tỉa hơn 50% không gian tìm kiếm và hạn chế hiện tượng xung đột mệnh đề.

#### 3.3. Đường kính đồ thị và khả năng đạt cận tối ưu
* Trên các đồ thị đường đi ($P_n$) hoặc cây (Tree) có đường kính lớn và mật độ rất thấp ($D \to 0$), cận kháng dải Antibandwidth $B^*(G)$ có thể đạt cực đại lý thuyết là $\lfloor n/2 \rfloor$.
* Đây là nhóm đồ thị kiểm thử tốt nhất để đo đạc khả năng tìm kiếm nhị phân qua nhiều ngưỡng $k$ khác nhau và so sánh tốc độ giải giữa **Direct Encoding** và **Order Encoding**.

---

### 4. Kết Nối Với Thư Viện Trực Quan Hóa `cnsplots`
Toàn bộ bảng thông số trên được tích hợp vào script tự động phân tích đồ thị `src/graph_loader.py` và sẽ được hiển thị qua các biểu đồ phân bố bậc đỉnh và ma trận kề sử dụng thư viện **`cnsplots`** theo đúng tiêu chuẩn bài báo khoa học của nhà xuất bản Elsevier.
