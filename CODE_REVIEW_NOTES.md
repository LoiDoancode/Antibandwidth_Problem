# Ghi chú rà soát mã nguồn Antibandwidth Problem

Ngày rà soát: 19/11/2026.

**Cập nhật theo yêu cầu người dùng: đã sửa riêng R02 và R03. Các mục khác chưa được sửa; dữ liệu, CP-SAT và kết quả benchmark được giữ nguyên. Phần mô tả phát hiện ban đầu được giữ lại để đối chiếu.**

## Phạm vi và bằng chứng đợt rà soát ban đầu

- Đọc toàn bộ mã Python của chương trình và bộ kiểm thử, cấu hình phụ thuộc, pytest, CI và hướng dẫn CLI.
- Bộ kiểm thử hiện có: **45 passed**, thời gian 15,19 giây; chạy bằng `python -B -m pytest -p no:cacheprovider`.
- Biên dịch cú pháp trong bộ nhớ cho **17 file Python**: không có lỗi cú pháp.
- Kiểm tra lint cùng nhóm lỗi với CI: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics`: **0 lỗi**.
- Đối chiếu vét cạn trên **202 đồ thị đơn vô hướng có cạnh, từ 2 đến 6 đỉnh**: cận LB/UB đều bao được tối ưu thực; **16.044 kiểm tra SAT** với sáu AMO của Direct và SCL, bật/tắt symmetry breaking, đều khớp đáp án vét cạn. Các mô hình SAT được kiểm tra trực tiếp, không để cận LB/UB bỏ qua bước giải.
- Trên phần đồ thị đến 5 đỉnh: **282 lượt tìm kiếm SAT** và **94 lượt tìm kiếm CP-SAT**, không giới hạn thời gian và không dùng bounds, đều khớp đáp án vét cạn.
- Các tình huống bổ sung dưới đây được chạy bằng dữ liệu tạm hoặc đối tượng giả lập trong bộ nhớ; không bổ sung/sửa test trong repository.
- Môi trường thực chạy: Windows, Python **3.12.14**, python-sat **1.9.dev23**, OR-Tools **9.15.6755**, NetworkX **3.7**. Thư viện được đặt trong thư mục tạm; chưa xác nhận lại trên Python 3.11 mà README quy định. Nhánh định dạng bằng `cnsplots` chưa được kiểm tra thực tế; các test biểu đồ chạy bằng matplotlib fallback.

P1 = ưu tiên cao vì có thể báo sai kết quả, sai đồ thị hoặc sai kết luận thực nghiệm. P2 = lỗi chức năng, kiểm chứng hoặc đo lường cần sửa. P3 = lỗi hướng dẫn sử dụng.

## Các phát hiện

### R01 — P1 — CP-SAT coi UNKNOWN là UNSAT, làm sai kết quả tìm kiếm

- Vị trí: `src/cp_solver.py:105-114`, `src/cp_solver.py:302-316`.
- `check_sat()` chỉ trả `True` cho OPTIMAL/FEASIBLE; UNKNOWN do hết thời gian cũng thành `False`, giống INFEASIBLE. Binary search vì thế hạ cận trên mà chưa có chứng minh vô nghiệm.
- Đã tái hiện trên `nx.path_graph(6)`, có tối ưu 3: đặt `time_limit_seconds=1e-9`, gọi `check_sat(3)` nhận `False` dù trạng thái gốc là UNKNOWN. `solve(method="binary_search")` trả `optimal_k=2`, `verified=True`.
- Đề xuất: giữ riêng SAT, UNSAT và UNKNOWN; khi UNKNOWN thì dừng với nghiệm tốt nhất cùng cận còn lại, không thu hẹp khoảng tìm kiếm theo hướng UNSAT.

### R02 — P1 — Phương thức được CLI chấp nhận khiến SAT trả cận greedy như kết quả tối ưu

- **Trạng thái: đã sửa theo cho phép của người dùng.** API SAT kiểm tra method trước cả các nhánh đồ thị tầm thường và trả ValueError nếu không hỗ trợ. CLI từ chối `direct_optimize` với SAT bằng mã thoát 2; vẫn cho CP-SAT dùng phương thức này qua cả `--solver cpsat` và `--encoding cpsat`.
- Vị trí bản sửa: `main.py:122-130`; `src/solver.py:262-268`.
- CLI cho phép `--method direct_optimize` với SAT Direct/SCL, nhưng `AntibandwidthSolver.solve()` không có nhánh cho phương thức này và cũng không báo lỗi.
- Đã tái hiện: `AntibandwidthSolver(nx.path_graph(6), verbose=False).solve(method="direct_optimize")` trả `optimal_k=2`, `verified=True`, `iterations=[]`, `timed_out=False`; phương thức hợp lệ tìm được 3.
- Đề xuất: kiểm tra tổ hợp solver/method ngay từ CLI và kiểm tra giá trị method trong API; chỉ cho CP-SAT dùng direct optimization.

### R03 — P1 — Solver bên ngoài gặp lỗi hoặc trả UNKNOWN bị hiểu là UNSAT

- **Trạng thái: đã sửa theo cho phép của người dùng.** Chỉ trả SAT/UNSAT khi trạng thái rõ ràng và nhất quán với mã thoát: 10/SAT, 20/UNSAT hoặc 0 kèm trạng thái hợp lệ cho wrapper. Lỗi tiến trình/khởi chạy, UNKNOWN, thiếu hoặc mâu thuẫn trạng thái, SAT không có model hoặc model có literal không hợp lệ sẽ báo RuntimeError. Timeout vẫn là TimeoutError và file CNF tạm luôn được dọn sau lời gọi tiến trình.
- CLI báo lỗi với mã thoát 1 trong chế độ check-k, tối ưu và batch; không tiếp tục in kết luận UNSAT hoặc bảng nghiệm tối ưu từ lỗi tiến trình.
- Vị trí bản sửa: `src/solver.py:120-200`; `main.py:210-214`, `main.py:311-315`, `main.py:362-369`.
- Giá trị mặc định là `is_sat=False`. Không có kiểm tra kết quả UNKNOWN, thiếu dòng trạng thái, hoặc mã thoát bất thường; stderr cũng không được dùng để báo lỗi.
- Đã tái hiện bằng cách giả lập tiến trình trả mã 1, stdout rỗng, stderr báo lỗi: bài P6 vẫn trả `optimal_k=2`, `verified=True` thay vì báo solver thất bại.
- Đề xuất: chỉ kết luận UNSAT khi nhận trạng thái UNSAT hợp lệ; kiểm tra trạng thái và mã thoát theo giao thức solver, phân biệt lỗi/UNKNOWN với UNSAT.

### R04 — P1 — Chưa chứng minh tối ưu nhưng CLI/CSV/Markdown vẫn trình bày như tối ưu

- Vị trí: `src/cp_solver.py:250-277`; `main.py:354-360`, `main.py:384-394`; `benchmark.py:415-434`, `benchmark.py:451-464`, `benchmark.py:497-524`.
- CP-SAT direct optimization gộp OPTIMAL với FEASIBLE; khi UNKNOWN còn có thể dùng nghiệm greedy. Kết quả vẫn mang khóa `optimal_k`, thiếu trạng thái chứng minh tối ưu. Nhánh benchmark SAT có nhận biết timeout khi in tiến độ nhưng không lưu trạng thái này vào bản ghi CSV/Markdown.
- Đã tái hiện CP-SAT direct optimization trên P6 với giới hạn rất nhỏ: trạng thái gốc UNKNOWN, nhưng kết quả là `optimal_k=2`, `verified=True`, không có `timed_out` hoặc `status`.
- Bằng chứng có sẵn: `benchmark_results.csv:32-41` ghi Direct đạt **7**, SCL/CP-SAT đạt **9** trên cùng `can___61.txt`, tất cả đều `verified=True`; `benchmark_results.md:35-44` trình bày cả hai dưới cột **B*(G)** với trạng thái PASSED. Các số này không thể đồng thời là giá trị tối ưu của cùng đồ thị. Riêng bảng hiện tại chưa đủ để chứng minh 9 là tối ưu thực.
- `verified=True` chỉ xác nhận tính hợp lệ của một nghiệm, không chứng minh không tồn tại nghiệm tốt hơn.
- Đề xuất: lưu riêng `best_k`, `optimality_proven`, trạng thái solver/timeout, cận trên và khoảng cách tối ưu; đưa trạng thái đó vào JSON/CSV/Markdown và biểu đồ.

### R05 — P1 — Nhận diện định dạng có thể âm thầm tạo sai đồ thị

- Vị trí: `src/graph_loader.py:279-303`.
- `load_graph()` không nhận diện header Harwell-Boeing trong nhánh dựa vào nội dung. Chỉ khảo sát 5 dòng đầu để phát hiện coordinate format nên cũng bỏ sót file có nhiều dòng comment.
- Đã tái hiện ngay với dữ liệu repository: `load_graph("data/acoust.data")` tạo **1.672 đỉnh, 487 cạnh**; `GraphLoader.from_harwell_boeing("data/acoust.data")` tạo **841 đỉnh, 1.624 cạnh**, phù hợp số chiều 841 trong header. Loader tự động đọc các con số trong header/pointer như edge list.
- Đã tái hiện thêm file `.txt` gồm 6 dòng comment rồi `4 4 1` và `1 2`: `load_graph()` trả **2 đỉnh**, còn parser coordinate trả đúng **4 đỉnh**, gồm cả hai đỉnh cô lập. Mất đỉnh làm thay đổi miền nhãn và đáp án ABP.
- Đề xuất: nhận diện header theo định dạng, bỏ qua comment cho đến dòng dữ liệu đầu tiên, giữ đủ số đỉnh khai báo và báo lỗi khi dữ liệu không khớp định dạng.

### R06 — P2 — Giới hạn thời gian SAT không được bảo đảm; chế độ check-k còn bỏ qua tham số

- Vị trí: `src/solver.py:89-103`; `main.py:290-299`.
- Bộ đếm giờ gọi `s.interrupt`, nhưng backend mặc định CaDiCaL 1.5.3 trong môi trường kiểm tra không hỗ trợ interrupt: gọi trực tiếp nhận `NotImplementedError: Limited solve is currently unsupported by CaDiCaL.` Tham số `expect_interrupt` của backend này không cung cấp cơ chế ngắt như code đang dựa vào. Nếu `solve_limited()` không được hỗ trợ, nhánh fallback lại gọi `s.solve()` không giới hạn.
- Với `main.py --check-k ... --time-limit ...`, đã theo dõi lời gọi và xác nhận cả constructor SAT lẫn `check_sat()` đều không nhận giới hạn do người dùng truyền.
- Đề xuất: dùng tiến trình với thời hạn cứng hoặc cơ chế deadline được backend hỗ trợ; truyền giới hạn qua mọi chế độ chạy và tính cả thời gian dựng mô hình nếu cam kết giới hạn toàn bộ lượt chạy.

### R07 — P2 — Chờ worker kết thúc trước khi đọc Queue có thể gây timeout giả

- Vị trí: `benchmark.py:381-402`.
- Parent gọi `proc.join(timeout=...)` rồi mới lấy dữ liệu trong `mp.Queue`. Worker có thể đã tính xong nhưng chưa thoát vì feeder thread còn chờ pipe được parent đọc.
- Đã tái hiện đúng thứ tự thao tác với 49 thông báo PROGRESS, mỗi thông báo chứa labeling 100 đỉnh: sau `join(timeout=3)` worker vẫn còn sống; đọc hết 49 thông báo thì worker thoát bình thường với mã 0.
- Với pipeline hiện tại, tình huống này bị đánh dấu timeout và worker bị terminate dù phần tính toán có thể đã hoàn thành.
- Đề xuất: đọc queue trong khi chờ worker, dùng thông báo hoàn tất rõ ràng và dọn tài nguyên queue; không dùng `queue.empty()` làm tín hiệu đồng bộ kết thúc.

### R08 — P2 — Trạng thái OOM và một phần số liệu benchmark là giả định, không phải đo thực tế

- Vị trí: `benchmark.py:347-370`; `src/visualizer.py:221-228`.
- Mọi cấu hình SAT có `n > 100` bị bỏ qua rồi được ghi `optimal_k="OOM"`, thời gian bằng giới hạn cấu hình và số mệnh đề ước lượng. SCL cũng đi qua nhánh ước lượng pairwise vì AMO mặc định truyền cho SCL là pairwise.
- Đã tái hiện với đồ thị đường đi 101 đỉnh và `--encodings scl`: không tạo worker nào nhưng in OOM, **300 giây**, **1.020.100 mệnh đề** cho cả hai chế độ symmetry. Đây không phải bằng chứng solver hết RAM hoặc đã chạy 300 giây.
- Hàm `_is_record_oom()` còn trả `True` với một lỗi chung `optimal_k="ERR"`, `verified=False`, ngay cả khi trạng thái mô tả FileNotFoundError; biểu đồ có thể gọi lỗi không liên quan bộ nhớ là OOM.
- Đề xuất: phân biệt SKIPPED_SIZE_LIMIT, TIMEOUT, ERROR và OOM thực; tách số liệu đo được khỏi ước lượng, không gán thời gian chạy giả cho lượt chưa chạy.

### R09 — P2 — --data-dir bị bỏ qua khi bộ dữ liệu mặc định tồn tại

- Vị trí: `benchmark.py:229-242`.
- Nhánh không có `--input` luôn ưu tiên năm file mặc định, chỉ dùng `args.data_dir` nếu không tìm thấy file mặc định nào.
- Đã truyền `--data-dir` trỏ đến thư mục tạm chứa một đồ thị khác; benchmark vẫn chọn cả năm file mặc định trong repository.
- Đề xuất: tôn trọng `--data-dir` người dùng chỉ định; nếu cần bộ curated mặc định thì cho nó chế độ lựa chọn riêng.

### R10 — P2 — Chế độ nhiều đồ thị bỏ qua các tùy chọn đã được chấp nhận

- Vị trí: `main.py:168-238`; đối chiếu nhánh single-graph `main.py:258-323`, `main.py:384-397`.
- Batch mode luôn chạy tối ưu rồi return; không xử lý `--check-k`, `--export-dimacs` hoặc `--output`.
- Đã chạy hai file `jgl009.txt`, `jgl011.txt` với `--check-k 999`: chương trình in bảng nghiệm tối ưu thay vì trả kết quả quyết định UNSAT cho k=999.
- Đề xuất: thực hiện đúng tùy chọn cho từng file, hoặc từ chối rõ các tổ hợp chưa hỗ trợ trước khi chạy.

### R11 — P2 — Kiểm chứng nghiệm chưa kiểm tra đầy đủ danh tính đỉnh và sự tồn tại của nghiệm

- Vị trí: `src/solver.py:200-215`, `src/solver.py:409-424`; `src/cp_solver.py:124-144`.
- Cả hai verifier chỉ kiểm tra các giá trị nhãn là hoán vị 1..n, chưa kiểm tra tập khóa đúng bằng tập đỉnh của đồ thị.
- Đã tái hiện đồ thị có các đỉnh 0,1,2,3 và cạnh (0,1),(1,2), đỉnh 3 cô lập: labeling `{0:1, 1:2, 2:3, 99:4}` vẫn được cả hai verifier chấp nhận. Nếu đỉnh bị thiếu có cạnh thì có thể phát sinh KeyError thay vì trả kết quả kiểm chứng không hợp lệ.
- Ngoài ra, `AntibandwidthSolver(..., time_limit_seconds=1e-12).solve(use_bounds=False)` đã trả `labeling=None` nhưng `verified=True` vì bước kiểm chứng khởi tạo mặc định là True và bỏ qua khi thiếu labeling.
- Đề xuất: kiểm tra labeling tồn tại, tập khóa trùng tập đỉnh, nhãn đúng miền và không trùng; mặc định thất bại nếu chưa có nghiệm để kiểm chứng.

### R12 — P2 — Thời gian SAT và CP-SAT không cùng phạm vi đo

- Vị trí: `src/solver.py:255-274`, `src/solver.py:304`, `src/solver.py:407`; `src/cp_solver.py:191-248`; `benchmark.py:381-384`, `benchmark.py:461`.
- Xác nhận bằng đọc code: `total_time` SAT bao gồm các lần encoding và giải trong vòng tìm kiếm, nhưng không tính bước bounds/greedy. CP-SAT direct optimization chỉ đo `solver.Solve(model)`, bỏ qua dựng mô hình và bounds. Benchmark có đo thời gian ngoài worker nhưng thường xuất `res["total_time"]` thay cho thời gian ngoài đó.
- Hệ quả: cột thời gian so sánh SAT với CP-SAT chưa có cùng định nghĩa; không nên diễn giải như so sánh thời gian toàn bộ pipeline.
- Đề xuất: đo một khoảng end-to-end thống nhất, hoặc xuất riêng thời gian preprocessing, encoding/modeling, solving và tổng, đồng thời ghi rõ định nghĩa trong báo cáo.

### R13 — P2 — --show-plot không mở được biểu đồ tương tác

- Vị trí: `src/visualizer.py:7-14`, `src/visualizer.py:213-214`; `main.py:117-120`.
- Module luôn ép matplotlib dùng backend Agg, kể cả khi người dùng yêu cầu hiển thị GUI.
- Đã gọi visualize với `show=True`: backend là Agg và phát cảnh báo `FigureCanvasAgg is non-interactive, and thus cannot be shown`.
- Đề xuất: chỉ chọn Agg cho chế độ không giao diện; giữ hoặc chọn backend tương tác phù hợp khi người dùng yêu cầu hiển thị.

### R14 — P3 — Một số lệnh hướng dẫn không chạy được với code hiện tại

- Vị trí: `README.md:83-103`, `COMMANDS.txt:52-53`; đối chiếu `main.py:60-64`, `benchmark.py:128-144`.
- `--encoding order` không thuộc các lựa chọn hiện tại: đã tái hiện argparse thoát mã 2.
- `benchmark.py --plot benchmark_chart.png` bị ambiguous giữa --plot-time, --plot-clauses, --plot-speedup: đã tái hiện thoát mã 2.
- Các đường dẫn ví dụ `data/sample_p6.mtx`, `data/sample_c5.mtx` không có trong repository. README còn mô tả Order Encoding và các file test không còn khớp cấu trúc hiện tại.
- Đề xuất: cập nhật ví dụ theo Direct/SCL/CP-SAT, dùng file dữ liệu thực có sẵn và kiểm tra tự động các lệnh hướng dẫn.

### R15 — P2 — Quét thư mục bỏ sót các định dạng đồ thị loader hỗ trợ

- Vị trí: `main.py:137-141`; `benchmark.py:194-210`; đối chiếu `src/graph_loader.py:273-278`.
- `main.py` chỉ lấy file .txt và .mtx khi nhận một thư mục; bỏ toàn bộ dữ liệu không phần mở rộng trong `data/instance/harwell-boeing/small` và cả .edges/.rb/.hb/.rsa/.rua/.mm.
- Đã chạy `main.py -i data/instance/harwell-boeing/small --check-k 1`: thoát mã 1, báo không có file hợp lệ dù thư mục có dữ liệu mà loader đọc được khi chỉ định từng file.
- `discover_graph_files()` của benchmark cũng bỏ sót .hb/.rsa/.rua/.mm, dù loader có nhánh tương ứng.
- Đề xuất: dùng chung quy tắc khám phá định dạng giữa CLI, benchmark và loader; hỗ trợ nhất quán dữ liệu không phần mở rộng.

## Phạm vi đã được phép và kiểm chứng bản sửa

- Người dùng chỉ cho phép sửa ý 2 và ý 3, tương ứng R02/R03; không mở rộng sang các phát hiện khác.
- Đã thêm 49 trường hợp kiểm thử cho method validation, tương thích CP-SAT, kết quả external SAT/UNSAT hợp lệ, các nhánh lỗi và dọn file CNF tạm.
- TDD R02: 20 test lỗi đúng như dự kiến trước sửa; sau sửa toàn bộ suite lúc đó có **67 passed**.
- TDD R03: 22 test lỗi đúng như dự kiến trước sửa, 5 test tương thích/timeout đã pass; sau sửa toàn bộ suite có **94 passed**, thời gian **32,99 giây**.
- CI lint (`E9,F63,F7,F82`): **0 lỗi**. `git diff --check`: không có lỗi khoảng trắng.
- Rà soát độc lập phạm vi R02/R03: không phát hiện lỗi mới. Chưa chạy một binary SAT bên ngoài thực; các test giao thức dùng kết quả tiến trình giả lập tại ranh giới subprocess.

## Giới hạn của lần rà soát

- Không chạy lại toàn bộ benchmark lớn với thời hạn hàng trăm giây cho mỗi cấu hình; không khẳng định đã biết tối ưu thực của `can___61.txt`.
- Solver bên ngoài được kiểm tra nhánh lỗi bằng đối tượng tiến trình giả lập; chưa chạy một binary Kissat thực.
- Không kiểm chứng các tuyên bố khoa học hay nguồn trích dẫn trong toàn bộ tài liệu báo cáo. Kết quả vét cạn chỉ chứng minh tính nhất quán trên phạm vi đồ thị đã nêu, không thay thế chứng minh tổng quát.
- Lỗi đọc dữ liệu và trạng thái benchmark cần được xử lý trước khi dùng kết quả hiện có làm bằng chứng về nghiệm tối ưu hoặc hiệu năng.
