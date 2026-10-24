# Data Directory - Antibandwidth Problem

Thư mục này dùng để lưu trữ các bộ dữ liệu đồ thị benchmark dùng cho bài toán Antibandwidth (ABP):

- **Định dạng MatrixMarket (`.mtx`)**: Được sử dụng phổ biến trong SuiteSparse Matrix Collection (Florida Sparse Matrix Collection).
- **Định dạng Harwell-Boeing / Rutherford-Boeing (`.rb`)**: Các ma trận thưa từ bộ Harwell-Boeing benchmark.

## Cấu trúc mẫu đã có sẵn:
- `sample_c5.mtx`: Đồ thị chu trình 5 đỉnh ($C_5$), nghiệm tối ưu $B^*(C_5) = 2$.
- `sample_p6.mtx`: Đồ thị đường đi 6 đỉnh ($P_6$), nghiệm tối ưu $B^*(P_6) = 3$.

Bạn có thể copy thêm các file `.mtx` hoặc `.rb` của bài tập/đề tài vào thư mục này để chạy thử nghiệm.
