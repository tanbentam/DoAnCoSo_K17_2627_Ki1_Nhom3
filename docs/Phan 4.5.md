Các nội dung đã hoàn thành:

Cài đặt thư viện:

Cài sentence-transformers 6.1.0 cùng PyTorch 2.14.1 bản CPU (tải từ https://download.pytorch.org/whl/cpu, nhẹ hơn nhiều so với bản CUDA, phù hợp kiến trúc "Local CPU Sentence-Transformers").
requirements.txt bổ sung dòng --extra-index-url https://download.pytorch.org/whl/cpu để pip install -r requirements.txt cài đúng bản CPU.

Xây dựng service nhúng vector backend/app/services/embedding_service.py:

Mô hình paraphrase-multilingual-MiniLM-L12-v2: hỗ trợ hơn 50 ngôn ngữ (gồm tiếng Việt & tiếng Anh), vector 384 chiều, giới hạn 128 token mỗi đoạn, chạy tốt trên CPU.
get_embedding_model: Nạp mô hình một lần duy nhất (lazy singleton) có khóa threading.Lock để an toàn khi nhiều BackgroundTasks chạy song song trong threadpool; mô hình được cache trong backend/models_cache.
preload_embedding_model: Nạp sẵn mô hình + chạy warm-up; không ném lỗi để server vẫn hoạt động nếu mô hình chưa sẵn sàng.
split_into_chunks: Chia văn bản dài (CV, JD) thành các đoạn ≤ 80 từ, gối đầu 15 từ, tránh bị mô hình cắt cụt ở 128 token làm mất thông tin phần sau của CV.
encode_texts: Mã hóa danh sách câu thành ma trận vector float32, chuẩn hóa L2 (cosine similarity = tích vô hướng, chuẩn bị cho Mục 4.6).
encode_document: Mã hóa một văn bản dài thành 1 vector duy nhất: chia đoạn → mã hóa → trung bình → chuẩn hóa L2.
Exception chuẩn hóa: EmbeddingServiceError, EmbeddingModelLoadError (kèm hướng dẫn chạy script tải mô hình khi offline).

Cấu hình (backend/app/core/config.py, .env.example):

EMBEDDING_MODEL_NAME, EMBEDDING_DEVICE=cpu, EMBEDDING_BATCH_SIZE=16, EMBEDDING_CACHE_DIR=models_cache, EMBEDDING_PRELOAD=true.
.gitignore bỏ qua thư mục backend/models_cache (~460MB).

Script tải mô hình backend/download_embedding_model.py:

Tải mô hình về cache cục bộ một lần khi có mạng và kiểm tra nhanh chất lượng: câu cùng nghĩa Việt - Anh có độ tương đồng 0.932, câu khác ngành (kế toán) chỉ 0.036.
Đã kiểm tra nạp mô hình ở chế độ ngắt mạng (HF_HUB_OFFLINE=1) thành công từ cache (phục vụ kịch bản demo offline Mục 8).

Tích hợp vào server (backend/app/main.py):

Sự kiện startup nạp sẵn mô hình trong luồng nền (daemon thread): server phản hồi ngay lập tức, mô hình sẵn sàng sau ~15 giây, request chấm điểm đầu tiên không bị chậm.
Endpoint /health bổ sung trường embedding_model_loaded để theo dõi trạng thái mô hình.
README.md bổ sung bước chạy download_embedding_model.py khi cài đặt.

Kiểm thử:

Unit test backend/tests/test_embedding_service.py (13 bài test): chia đoạn (văn bản ngắn, rỗng, dài có gối đầu, tham số sai), mã hóa với mô hình giả lập (shape, dtype, chuẩn hóa L2, chia đoạn văn bản dài), nạp mô hình một lần, lỗi nạp mô hình, preload không ném lỗi; 2 bài test với mô hình thật (384 chiều, tương đồng ngữ nghĩa đa ngôn ngữ) tự bỏ qua nếu chưa tải mô hình.
Chạy toàn bộ test suite dự án: 56/56 tests passed (OK).

Cập nhật Checklist:

Đã đánh dấu [x] hoàn thành mục này trong checklist.md.
