# HƯỚNG DẪN CHẠY

Tài liệu này hướng dẫn chạy nhanh service Lab 04 bằng Docker và kiểm tra bằng Newman.

## 1. Chuẩn bị môi trường

- Cài Docker Desktop hoặc Docker Engine.
- Cài Node.js 20.x và npm.
- Cài Python nếu cần chạy app local.

## 2. Cài dependencies

Mở terminal tại thư mục dự án rồi chạy:

```bash
npm install
```

## 3. Build Docker image

```bash
docker build -t fit4110/iot-ingestion:lab04 .
```

## 4. Chạy container

```bash
docker run --rm \
  --name fit4110-iot-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/iot-ingestion:lab04
```

Sau khi container chạy, mở terminal khác và kiểm tra:

```bash
curl http://localhost:8000/health
```

Kết quả mong đợi:

```json
{
  "status": "ok",
  "service": "iot-ingestion",
  "version": "0.4.0"
}
```

## 5. Chạy Newman test

Khi container đang chạy, thực hiện:

```bash
npm run test:local
```

Hoặc dùng script:

```bash
bash scripts/run-newman.sh local
```

Báo cáo sẽ được sinh vào:

- `reports/newman-lab04-local.xml`
- `reports/newman-lab04-local.html`

## 6. Dừng container

Nếu sử dụng `--rm` thì container sẽ tự xóa khi kết thúc.

Nếu cần dừng bằng tay thì chạy:

```bash
docker stop fit4110-iot-lab04
```

## 7. Lệnh nhanh bằng Makefile

```bash
make build
make run
make test-docker
make stop
```

Nếu dùng PowerShell thì lệnh `make` vẫn áp dụng nếu đã cài Make.
