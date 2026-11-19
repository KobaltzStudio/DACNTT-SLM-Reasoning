# Hướng dẫn thực thi RunPod — P1/P2 Unified, seed 13

Tài liệu dành cho người vận hành Python, Linux và SSH. Bản bàn giao hiện đã được kiểm tra trên Windows. `LINUX_CPU_VALIDATION=PENDING`, `RUNPOD_GPU_EXECUTION=NOT_RUN` và `D_TEST_EXECUTION=NOT_RUN`. Các lệnh live ở B6–B9 và B15 là lệnh bàn giao để chạy sau khi có phê duyệt đúng phạm vi.

## B1. Mục tiêu và quy trình khoa học

Đề tài nghiên cứu chưng cất kỹ năng suy luận chuỗi từ Teacher sang Student bằng cách chọn trajectory phù hợp ở mỗi vòng. **P1** ưu tiên thiếu hụt năng lực của Student. **P2** dùng learnability động, ước lượng từ NLL của Student tại checkpoint hiện tại. Run A (`P1-DEFICIT`) chọn dựa trên deficit. Run B (`P1P2`) dùng `0.5 × deficit + 0.5 × percentile_rank(L_proxy)`. Đợt này sử dụng hai phương pháp đó với seed 13, không có graph-guided training.

Hai run có chung **S0**, là base Student đã khóa revision; namespace, adapter và lineage S1–S3 của chúng độc lập. S1 gắn LoRA lên base; S2 nối từ S1 cùng run; S3 nối từ S2 cùng run. Round của controller là 1–3, tương ứng S1–S3. Với Run B, NLL dùng Student **trước** vòng train kế tiếp.

- **D_dev** có 500 ID. Mỗi checkpoint hoàn tất sau khi đánh giá D_dev, kiểm tra prediction, chạy post-evaluation hook và tạo capability state.
- **D_dev_select** có 415 ID thuộc D_dev, xác định bởi split manifest, dùng cho G7. Accuracy strict đếm đúng khi `status == "valid"`. **D_test** là tập giữ lại 1.319 ID, chỉ dùng đánh giá cuối theo B15.
- **Sidecar** lưu kết quả trên 85 Gold ID ứng với bảy capability và dấu vân tay đầu vào. **Capability state** là trạng thái đã kiểm tra của checkpoint nguồn, dùng cho selection kế tiếp. **Lineage** nối train set, selection log, adapter cha và con, prediction, checkpoint log và SHA.

## B2. Trạng thái bàn giao

| Run | Checkpoint | Trạng thái đã xác minh |
| --- | --- | --- |
| A · P1-DEFICIT · seed 13 | S1 | PASS — strict D_dev 416/500 |
| A | S2 | Adapter LoRA hoàn tất sau 26 optimizer steps; D_dev có 75/500, còn 425 ID; hook và capability state chưa hoàn tất |
| A | S3 | NOT RUN |
| B · P1P2 · seed 13 | S1 | PASS — strict D_dev 406/500 |
| B | S2 | NOT RUN; cần NLL S1 |
| B | S3 | NOT RUN; cần NLL S2 |

Mỗi S3 chỉ được chạy sau khi S2 **cùng run** PASS. Hai số accuracy ở trên thuộc S1. G6, G7 và bảy hình G8 hiện có coverage PARTIAL.

## B3. Nhận source, runtime và Student cache

Yêu cầu người bàn giao cung cấp ba đầu vào qua kênh phù hợp với quyền truy cập:

| Đầu vào | Đường dẫn tương đối theo vai trò | Dùng để |
| --- | --- | --- |
| GitHub source đã phê duyệt | `manifests/public_files.txt`, `manifests/GITHUB_RELEASE_MANIFEST.json`, `manifests/runtime_payload.csv` trong source checkout | Xác minh source, fixture test và đối chiếu với runtime. GitHub không chứa frozen data, weights hoặc artifacts nghiên cứu riêng. |
| Sealed runtime 658 file | Handoff `P1P2-Unified/runtime/`; danh sách chuyển `P1P2-Unified/manifests/runpod_files.txt` và inventory `P1P2-Unified/manifests/runpod_inclusion_manifest.csv` | Chứa source đúng phiên bản, frozen config, taxonomy, split, Gold, pool, token table, NLL, prediction, adapter, checkpoint log, sidecar, capability state và manifest. Manual root nằm tại `P2/experiments/week2September/manual` bên trong runtime. |
| Offline Student cache 7 file | `P1P2-Unified/manifests/MODEL_CACHE_TRANSFER_MANIFEST.csv` và `P1P2-Unified/manifests/MODEL_CACHE_SHA256SUMS.txt`; danh sách checksum cũng có trong source | `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, gồm config, tokenizer và weights đúng revision. Không cần Teacher weights cho verified-pool workflow. |

Ghi pin từ kênh bàn giao độc lập trước khi nhận file. Với bản release này, `runtime/manifests/SHA256SUMS.txt` có SHA `bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798` và `runtime/manifests/RUNPOD_PACKAGE_MANIFEST.json` có SHA `dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62`. Wrapper còn kiểm tra manifest CSV, kích thước, membership và SHA từng file. Giữ nguyên layout và byte gốc. Chuyển cache riêng, không đưa weights vào GitHub.

## B4. Chuẩn bị máy, volume, SSH và môi trường

Chọn GPU hỗ trợ BF16 cùng driver tương thích PyTorch cu126. Theo `LINUX_ENVIRONMENT_CONTRACT.md` của release audit, Windows A S1 đã dùng khoảng 7,52 GiB VRAM reserved; hợp đồng đưa thiết bị BF16 16 GiB làm ví dụ có dư địa. Đây là tham chiếu lập kế hoạch, chưa có đo đạc trên RunPod. Dùng persistent volume cho intake, cache, work và log. Bundle + một work copy + cache chiếm khoảng 4,25 GB trước wheelhouse và kết quả. Wrapper mặc định yêu cầu thêm ít nhất 2 GiB trống theo filesystem liên quan. Kiểm tra dung lượng thật trước khi sao chép.

Trên máy gửi có Bash, SSH và rsync, điền `RUNPOD_SSH` (SSH alias đã cấu hình theo endpoint được duyệt), `REMOTE_VOLUME` (đường dẫn persistent volume trên pod), `HANDOFF` và `CACHE_SOURCE_HUB`. Dùng volume mới hoặc thư mục release còn trống. Thiết lập port/key trong cấu hình SSH thay vì đưa vào repo.

```bash
set -euo pipefail
: "${RUNPOD_SSH:?set approved SSH alias}"
: "${REMOTE_VOLUME:?set absolute Linux persistent volume path without spaces}"
: "${HANDOFF:?set local P1P2-Unified handoff path}"
: "${CACHE_SOURCE_HUB:?set local approved HF hub path}"
test -f "$HANDOFF/runtime/manifests/SHA256SUMS.txt"
test -f "$HANDOFF/manifests/MODEL_CACHE_SHA256SUMS.txt"
ssh "$RUNPOD_SSH"
```

Trên pod, tạo thư mục intake mới. Sau đó quay lại máy gửi để chuyển file.

```bash
set -euo pipefail
: "${P1P2_VOLUME:?set the same absolute persistent volume path}"
test -d "$P1P2_VOLUME" && test -w "$P1P2_VOLUME"
df -h "$P1P2_VOLUME"
umask 077
mkdir "$P1P2_VOLUME/intake"
mkdir "$P1P2_VOLUME/intake/runtime" "$P1P2_VOLUME/intake/hf"
mkdir "$P1P2_VOLUME/intake/hf/hub" "$P1P2_VOLUME/intake/logs"
```

```bash
set -euo pipefail
rsync -rt --checksum --ignore-existing -- \
  "$HANDOFF/runtime/" "$RUNPOD_SSH:$REMOTE_VOLUME/intake/runtime/"
cut -c67- "$HANDOFF/manifests/MODEL_CACHE_SHA256SUMS.txt" |
  rsync -rt --copy-links --checksum --ignore-existing --files-from=- -- \
    "$CACHE_SOURCE_HUB/" "$RUNPOD_SSH:$REMOTE_VOLUME/intake/hf/hub/"
```

Trên pod, dùng repository URL, branch **và commit source đã được duyệt**. Nếu chưa có commit chứa bản source 63 file đúng audit, dừng ở đây để người bàn giao cung cấp checkout đã duyệt. Đặt `APPROVED_SOURCE_MANIFEST_SHA` từ kênh độc lập cho đúng checkout. Không tải Git worktree đầy đủ có dữ liệu riêng.

```bash
set -euo pipefail
: "${P1P2_VOLUME:?set absolute persistent volume path}"
: "${GITHUB_URL:?set approved source URL}"
: "${GITHUB_BRANCH:?set reviewed branch}"
: "${APPROVED_SOURCE_COMMIT:?set full reviewed commit ID}"
: "${APPROVED_SOURCE_MANIFEST_SHA:?set independently reviewed release manifest SHA}"
: "${WHEELHOUSE:?set approved Linux x86_64 wheelhouse}"
export SOURCE="$P1P2_VOLUME/intake/source"
export P1P2_PACKAGE="$P1P2_VOLUME/intake/runtime"
export WORK="$P1P2_VOLUME/intake/work"
export LOG_ROOT="$P1P2_VOLUME/intake/logs"
export MANUAL="$WORK/P2/experiments/week2September/manual"
export HF_HOME="$P1P2_VOLUME/intake/hf" HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HUB_CACHE="$HF_HOME/hub"
export P1P2_PYTHON="$P1P2_VOLUME/intake/venv/bin/python"
test ! -e "$SOURCE" && test ! -e "$WORK" && test ! -e "$P1P2_VOLUME/intake/venv"
git clone --branch "$GITHUB_BRANCH" --single-branch -- "$GITHUB_URL" "$SOURCE"
test "$(git -C "$SOURCE" rev-parse HEAD)" = "$APPROVED_SOURCE_COMMIT"
test -f "$SOURCE/manifests/GITHUB_RELEASE_MANIFEST.json"
printf '%s  %s\n' "$APPROVED_SOURCE_MANIFEST_SHA" "$SOURCE/manifests/GITHUB_RELEASE_MANIFEST.json" |
  sha256sum -c -
python3.11 -m venv "$P1P2_VOLUME/intake/venv"
"$P1P2_PYTHON" --version
"$P1P2_PYTHON" -m pip install --no-index --find-links "$WHEELHOUSE" \
  -r "$SOURCE/P2/requirements-lock.txt"
"$P1P2_PYTHON" -m pip check
```

Theo lock và hợp đồng Linux, dùng Python 3.11 x86_64, torch `2.13.0+cu126`, transformers `5.15.0`, peft `0.20.0`, accelerate `1.14.0`, tokenizers `0.22.2`, huggingface-hub `1.27.0`, safetensors `0.8.0`, PyYAML `6.0.3`, matplotlib `3.11.2`. `datasets==5.0.1` và `bitsandbytes==0.50.2` có pin trong lock; workflow HF BF16 được bàn giao không gọi trực tiếp hai gói này. Wheelhouse phải có các wheel theo platform marker. Nếu không resolve được phiên bản hoặc driver, ghi nhận lỗi và dừng. Dùng HF backend. CPU acceptance không gọi CUDA.

## B5. Preflight bắt buộc trên Linux

```bash
set -euo pipefail
test -d "$LOG_ROOT" && test -w "$LOG_ROOT"
test -d "$HF_HUB_CACHE" && test -r "$HF_HUB_CACHE"
df -h "$P1P2_PACKAGE" "$HF_HUB_CACHE" "$LOG_ROOT"
(
  cd "$P1P2_PACKAGE"
  printf '%s  %s\n' \
    bf0c50c301de9e2b78d9533a6a995733a431a6834d8ad019926e1c826af07798 manifests/SHA256SUMS.txt \
    dbe0d5bb0b2b80df5d0b4f41ff57b3318a543c264e2d5b20c5c7f818e0424f62 manifests/RUNPOD_PACKAGE_MANIFEST.json |
    sha256sum -c -
  sha256sum -c manifests/SHA256SUMS.txt
)
bash "$SOURCE/deployment/verify_package.sh" --package "$P1P2_PACKAGE"
bash "$SOURCE/deployment/verify_model_cache.sh" --package "$P1P2_PACKAGE"
(
  export CUDA_VISIBLE_DEVICES=''
  cd "$SOURCE"
  "$P1P2_PYTHON" -B -c 'import torch, transformers, peft, accelerate, tokenizers, safetensors, yaml, matplotlib; print(torch.__version__, torch.version.cuda, transformers.__version__, peft.__version__)'
  "$P1P2_PYTHON" -B tools/preflight.py source
  "$P1P2_PYTHON" -B tools/preflight.py tests
  "$P1P2_PYTHON" -B -m unittest discover -s tests -v
  "$P1P2_PYTHON" -B tools/preflight.py bundle --bundle "$P1P2_PACKAGE"
)
bash "$SOURCE/deployment/setup_environment.sh" --package "$P1P2_PACKAGE" --work "$WORK"
test -w "$MANUAL" && test -w "$MANUAL/runs/p1p2_integration"
test -z "$(find "$MANUAL/runs/p1p2_integration" -name .controller.lock -print)"
bash "$SOURCE/deployment/linux_cpu_preflight.sh" --package "$P1P2_PACKAGE" \
  --work "$WORK" --output "$LOG_ROOT/cpu-preflight"
export RECEIPT="$LOG_ROOT/cpu-preflight/preflight.json"
"$P1P2_PYTHON" -B - "$RECEIPT" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert (r["status"], r["platform"], r["actions"]) == ("PASS", "linux", [0, 0, 4, 16]), r
print("Linux CPU receipt OK:", r["actions"])
PY
```

Xác nhận 103 runtime tests trong `cpu-preflight/unittest.log`, gồm fixture no-overwrite, atomic publication, lock, partial JSONL và lineage. Receipt phải khớp interpreter, package và **đúng work root**. Wrapper xác minh checksum package, cache, source, adapter/prediction hiện có, prefix append-only và log path. Kế hoạch Windows tham chiếu: A S1 và B S1 có 0 action; A S2 có 4 action (eval, checkpoint log, hook, state); B S2–S3 có 16 action. Dry-run trên Linux phải tự thu được receipt đó. CPU preflight đòi work tree ở trạng thái mới sao từ seal. Khi resume một work tree đã tiến triển, giữ receipt ban đầu và dùng preview theo scope; không dựng lại work tree đè lên tiến độ.

Sau khi reviewer chấp nhận Linux CPU receipt và cho phép kiểm tra GPU target, đặt `GPU_PREFLIGHT_APPROVED=BF16-CHECK` để xác minh thiết bị và CUDA/BF16:

```bash
test "${GPU_PREFLIGHT_APPROVED:-}" = BF16-CHECK &&
  nvidia-smi &&
  "$P1P2_PYTHON" -B -c 'import torch; assert torch.cuda.is_available() and torch.cuda.is_bf16_supported(); print(torch.version.cuda, torch.cuda.get_device_name(0))'
```

Dừng trước checkpoint nếu bất kỳ kiểm tra bắt buộc nào lỗi, có job/lock chưa rõ chủ, source lệch seal hoặc work/evidence path bị trùng.

## B6. Run A S2 — tiếp tục đánh giá

Chạy preview. Bản intake mới phải hiện đúng bốn stage ở B5, không có train/selection/NLL. So sánh prefix 75 dòng với seal trước khi thực thi.

```bash
set -euo pipefail
a_s2='runs/p1p2_integration/P1-DEFICIT_seed13/S2/eval_dev.jsonl'
sealed_prefix="$P1P2_PACKAGE/P2/experiments/week2September/manual/$a_s2"
test "$(wc -l < "$sealed_prefix")" -eq 75
cmp -n "$(wc -c < "$sealed_prefix")" -- "$sealed_prefix" "$MANUAL/$a_s2"
bash "$SOURCE/deployment/run_a_s2.sh" --package "$P1P2_PACKAGE" --work "$WORK"
```

**Live, chỉ sau khi duyệt riêng A S2.** Wrapper resume round 2, dùng adapter đã lưu, nối các D_dev ID còn thiếu vào JSONL theo `problem_id`, xuất summary, checkpoint log, sidecar và capability state. Trên intake nguyên trạng là 425 ID. Khi tiếp tục sau một gián đoạn khác, số ID còn lại căn cứ vào prefix hợp lệ lúc resume. Chọn tên attempt mới khi retry.

```bash
test "${APPROVED_A_S2:-}" = 'P1-DEFICIT:13:S2' &&
  bash "$SOURCE/deployment/run_a_s2.sh" --package "$P1P2_PACKAGE" --work "$WORK" \
  --execute --approve P1-DEFICIT:13:S2 --receipt "$RECEIPT" --output "$LOG_ROOT/a-s2-attempt1"
```

Thực hiện B11 với `METHOD=P1-DEFICIT`, `ROUND=2` và `ATTEMPT=$LOG_ROOT/a-s2-attempt1`. A S2 vẫn phải có `train_log.json` 26 steps và hash adapter trùng bản seal. Summary phải có 500 ID duy nhất đúng split và tag S2; tính strict accuracy từ kết quả thực tế.

## B7. Run A S3 — LoRA từ A S2

Chỉ sau B11 xác nhận A S2 PASS. Round 3 chọn bằng capability state của A S2, train LoRA từ adapter A S2, đánh giá D_dev, ghi checkpoint log, chạy hook và ghi capability state cuối. Preview yêu cầu parent có 0 action. So khớp adapter cha với A S2, và kiểm tra plan không có NLL.

```bash
bash "$SOURCE/deployment/run_a_s3.sh" --package "$P1P2_PACKAGE" --work "$WORK"
```

**Live, phê duyệt riêng A S3:**

```bash
test "${APPROVED_A_S3:-}" = 'P1-DEFICIT:13:S3' &&
  bash "$SOURCE/deployment/run_a_s3.sh" --package "$P1P2_PACKAGE" --work "$WORK" \
  --execute --approve P1-DEFICIT:13:S3 --receipt "$RECEIPT" --output "$LOG_ROOT/a-s3-attempt1"
```

## B8. Run B S2 — learnability từ B S1

Sau Linux CPU PASS, preview phải xác nhận B S1 được dùng lại và NLL có tag S1 gắn với B S1 adapter. Round 2 dùng NLL mới tại S1 để xếp hạng combined selection với alpha 0.5, train LoRA từ B S1, đánh giá D_dev rồi chạy hook/state. Khi resume, dùng lại NLL S1 đã đủ coverage và đúng digest; NLL S0 không tương đương.

```bash
bash "$SOURCE/deployment/run_b_s2.sh" --package "$P1P2_PACKAGE" --work "$WORK"
```

**Live, phê duyệt riêng B S2:**

```bash
test "${APPROVED_B_S2:-}" = 'P1P2:13:S2' &&
  bash "$SOURCE/deployment/run_b_s2.sh" --package "$P1P2_PACKAGE" --work "$WORK" \
  --execute --approve P1P2:13:S2 --receipt "$RECEIPT" --output "$LOG_ROOT/b-s2-attempt1"
```

## B9. Run B S3 — learnability từ B S2

Chỉ sau B S2 PASS. Preview phải có NLL tag S2 và cùng B S2 adapter cho tính NLL và LoRA parent. Controller dùng combined selection round 3, đánh giá D_dev rồi xuất hook/state. B S1 adapter và NLL S1 không phải đầu vào thay thế của vòng này.

```bash
bash "$SOURCE/deployment/run_b_s3.sh" --package "$P1P2_PACKAGE" --work "$WORK"
```

**Live, phê duyệt riêng B S3:**

```bash
test "${APPROVED_B_S3:-}" = 'P1P2:13:S3' &&
  bash "$SOURCE/deployment/run_b_s3.sh" --package "$P1P2_PACKAGE" --work "$WORK" \
  --execute --approve P1P2:13:S3 --receipt "$RECEIPT" --output "$LOG_ROOT/b-s3-attempt1"
```

## B10. Giao diện lệnh và scope

`setup_environment.sh` tạo bản sao mới, `linux_cpu_preflight.sh` kiểm tra và xuất receipt, bốn wrapper `run_{a,b}_s{2,3}.sh` xử lý đúng một checkpoint. Wrapper gọi controller với `--seed 13 --round N --resume --backend hf --dtype bf16 --micro-batch 1 --nll-batch 1 --eval-batch 1`, cùng manual root và mapping lấy từ `manifests/path_mapping_manifest.json`. Giữ nguyên các tham số khoa học đã khóa. Planned rounds sử dụng D_dev và không gọi D_test.

Kiểm tra giao diện trên checkout đã nhận. Các lệnh này chỉ in trợ giúp:

```bash
bash "$SOURCE/deployment/setup_environment.sh" --help
bash "$SOURCE/deployment/linux_cpu_preflight.sh" --help
bash "$SOURCE/deployment/run_a_s2.sh" --help
bash "$SOURCE/deployment/run_a_s3.sh" --help
bash "$SOURCE/deployment/run_b_s2.sh" --help
bash "$SOURCE/deployment/run_b_s3.sh" --help
"$P1P2_PYTHON" -B "$MANUAL/scripts/run_p1_p2.py" --help
"$P1P2_PYTHON" -B "$MANUAL/scripts/run_p1p2_post_eval.py" --help
```

Preview chỉ nhận `--package` và `--work` trong các ví dụ trên. Live thêm `--execute --approve METHOD:13:CHECKPOINT --receipt ... --output ...`. Mỗi lệnh live cần phê duyệt thật tương ứng. Sau khi có phê duyệt, đặt biến `APPROVED_A_S2`, `APPROVED_A_S3`, `APPROVED_B_S2` hoặc `APPROVED_B_S3` đúng scope in cạnh lệnh. Token scope và biến shell giúp ngăn chạy nhầm. Wrapper đã xác minh checkpoint hoàn tất sẽ in `"actions": []` rồi kết thúc, không tạo receipt mới. Khi đó giữ receipt PASS trước đó.

## B11. Kiểm chứng sau từng checkpoint

Điền `METHOD`, `ROUND` và `ATTEMPT` cho một lần chạy hoàn tất. Bảo toàn stdout của wrapper, `intent.json`, `execution.log`, `exit_code.txt` và `execution.json`. Receipt phải có đúng scope, PASS và exit 0. Chạy preview lại: yêu cầu 0 action. Đó là kiểm chứng lại SHA/collision, checkpoint log prefix, train/selection lineage, prediction, sidecar và capability state bằng controller.

```bash
set -euo pipefail
: "${METHOD:?set P1-DEFICIT or P1P2}"
: "${ROUND:?set 2 or 3}"
: "${ATTEMPT:?set the successful attempt directory}"
case "$METHOD:$ROUND" in
  P1-DEFICIT:2) wrapper=run_a_s2.sh ;;
  P1-DEFICIT:3) wrapper=run_a_s3.sh ;;
  P1P2:2) wrapper=run_b_s2.sh ;;
  P1P2:3) wrapper=run_b_s3.sh ;;
  *) echo 'Invalid scope' >&2; exit 2 ;;
esac
test "$(cat "$ATTEMPT/exit_code.txt")" = 0
grep -F 'P1P2_CONTROLLER=PASS' "$ATTEMPT/execution.log"
preview=$(bash "$SOURCE/deployment/$wrapper" --package "$P1P2_PACKAGE" --work "$WORK")
printf '%s\n' "$preview"
printf '%s\n' "$preview" | grep -F '"actions": []'
"$P1P2_PYTHON" -B - "$WORK" "$MANUAL" "$P1P2_PACKAGE" "$ATTEMPT" "$METHOD" "$ROUND" <<'PY'
from pathlib import Path
import json, sys

work, root, package, attempt = [Path(x).resolve() for x in sys.argv[1:5]]
method, number = sys.argv[5], int(sys.argv[6])
sys.path.insert(0, str(root / "scripts"))
from p1p2_artifact_manager import hash_path

def read(path):
    return json.loads(path.read_bytes())

def rows(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]

group, label = f"{method}_seed13", f"S{number}"
tag = f"{group}_{label}"
runs = root / "runs/p1p2_integration" / group
models = root / "models/p1p2_integration" / group
reports = root / "reports/p1p2_integration"
adapter = models / f"student_ckpt_{number:03d}"
parent = models / f"student_ckpt_{number - 1:03d}"
selected = runs / f"round_{number:03d}"
pred = runs / label / "eval_dev.jsonl"
side = reports / "capability_sidecars" / tag
state = reports / "capability_state" / group / f"selection_round_{number + 1:03d}.json"
receipt = read(attempt / "execution.json")
assert (receipt["scope"], receipt["status"], receipt["exit_code"]) == (f"{method}:13:{label}", "PASS", 0)
assert Path(receipt["work"]).resolve() == work
dev = (root / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").split()
prediction = rows(pred)
ids = {row["problem_id"] for row in prediction}
allowed = {"valid", "invalid_format", "invalid_answer"}
assert len(prediction) == len(ids) == len(set(dev)) == 500 and ids == set(dev)
assert all(r["checkpoint"] == tag and r["status"] in allowed for r in prediction)
correct = sum(r["status"] == "valid" for r in prediction)
summary = read(pred.with_suffix(".summary.json"))
assert (summary["checkpoint"], summary["split"], summary["n_problems"], summary["n_valid"]) == (tag, "dev", 500, correct)
assert summary["accuracy"] == correct / 500
assert pred.with_name("eval_dev.intent.json").is_file()
train_log = read(adapter / "train_log.json")
assert train_log["seed"] == 13 and train_log["checkpoint_parent_sha256"] == hash_path(parent)
matches = [r for r in rows(runs / "checkpoint_log.jsonl") if r["checkpoint"] == label]
assert len(matches) == 1
ckpt = matches[0]
assert (ckpt["method"], ckpt["training_seed"], ckpt["round"], ckpt["parent_checkpoint"]) == (method, 13, number, f"S{number - 1}")
assert ckpt["checkpoint_sha256"] == hash_path(adapter)
for key, path in (("train_set", selected / "train_set.json"), ("selection_log", selected / "selection_log.jsonl"), ("train_log", adapter / "train_log.json")):
    assert ckpt[f"{key}_sha256"] == hash_path(path), path
lineage = read(side / "checkpoint_lineage.json")
assert (lineage["method"], lineage["seed"], lineage["round"]) == (method, 13, number)
assert lineage["prediction_sha256"] == hash_path(pred) and lineage["checkpoint_sha256"] == hash_path(adapter)
coverage = read(side / "prediction_coverage_report.json")
assert coverage["prediction_unique_ids"] == 500 and coverage["gold_matched_prediction_ids"] == 85
assert len(rows(side / "capability_metrics.jsonl")) == 7 and state.is_file()
if method == "P1-DEFICIT" and number == 2:
    prefix = (package / pred.relative_to(work)).read_bytes()
    assert len(prefix.splitlines()) == 75 and pred.read_bytes().startswith(prefix)
    assert hash_path(package / adapter.relative_to(work)) == hash_path(adapter) and train_log["steps"] == 26
if method == "P1P2":
    nll = runs / f"S{number - 1}" / "nll.jsonl"
    nll_summary = read(nll.with_suffix(".summary.json"))
    assert (nll_summary["checkpoint"], nll_summary["adapter_sha256"]) == (f"S{number - 1}", hash_path(parent))
    assert read(selected / "train_set.json")["nll_sha256"] == hash_path(nll)
    print("NLL SHA-256", hash_path(nll))
print(f"{tag} strict D_dev = {correct}/500 = {correct / 500:.4%}")
for path in (adapter, pred, side, state):
    print(hash_path(path), path.relative_to(root))
PY
```

SHA adapter và sidecar thư mục dùng `hash_path` theo định dạng lineage của controller; SHA prediction và state là SHA file. Với A S2 lần chạy đầu, summary `problems_this_run` phải là 425. Nếu hook/state đã hoàn tất trong attempt trước rồi resume, log có thể ghi reuse; kiểm chứng bằng sidecar/state hợp lệ và preview 0 action. Nếu một kiểm tra lỗi, lưu evidence và chuyển B17. Chỉ ghi PASS khi receipt, kết quả strict, Gold/state và lineage đều đạt. Sau bốn scope, xác minh lại sealed package để đóng audit bảo toàn đầu vào:

```bash
bash "$SOURCE/deployment/verify_package.sh" --package "$P1P2_PACKAGE"
```


## B12. G6 — Capability learning dynamics

Sau khi A S2, A S3, B S2 và B S3 đều PASS, tạo thư mục phân tích mới trên volume, ngoài seal và work. Giữ nguyên bản PARTIAL cũ. Mapping phải lấy từ bundle đã xác minh.

```bash
set -euo pipefail
export ANALYSIS="$LOG_ROOT/analysis-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir "$ANALYSIS"
export LEGACY_WINDOWS_ROOT
LEGACY_WINDOWS_ROOT=$("$P1P2_PYTHON" -B -c \
  'import json,sys; from pathlib import Path; print(json.loads(Path(sys.argv[1]).read_bytes())["windows_manual_root"])' \
  "$P1P2_PACKAGE/manifests/path_mapping_manifest.json")
export CUDA_VISIBLE_DEVICES='' MPLBACKEND=Agg
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_capability_learning_dynamics.py" \
  --manual "$MANUAL" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" \
  --seed 13 --inventory-only --output "$ANALYSIS/g6-inventory"
"$P1P2_PYTHON" -B - "$ANALYSIS/g6-inventory/g6_pretraining_inventory.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["status"] == "PASS" and not r["missing_method_checkpoint_pairs"], r["missing_method_checkpoint_pairs"]
assert r["accepted_sidecars"] == r["raw_sidecars"]
PY
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_capability_learning_dynamics.py" \
  --manual "$MANUAL" --legacy-windows-root "$LEGACY_WINDOWS_ROOT" \
  --seed 13 --output "$ANALYSIS/g6"
"$P1P2_PYTHON" -B - "$ANALYSIS/g6/capability_learning_dynamics_seed13.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["g6_status"] == "PASS" and r["seed"] == 13 and not r["missing_method_checkpoint_pairs"]
assert len(r["capabilities"]) == 7 and r["shared_S0_included_once"]
assert all(x["n_gold_records"] == 85 for x in r["rows"])
assert r["correctness_policy"] == "status == valid" and r["confidence_interval"] == "Wilson 95%"
PY
```

Kết quả đủ dữ liệu tại `$ANALYSIS/g6/` gồm `capability_learning_dynamics_seed13.csv`, `capability_learning_dynamics_seed13.json`, `capability_learning_dynamics_seed13.md`, `capability_sidecar_inventory_seed13.csv`. Builder xác minh 85 approved Gold ID, bảy capability, SHA prediction, Gold và checkpoint lineage; giữ các nguồn trùng trong inventory và gộp theo logical checkpoint khi phân tích. S0 dùng chung được tính một lần. Soát alias B4/B5 bằng checkpoint SHA trước khi gọi là cùng trọng số. Báo cáo chỉ dùng seed 13. Inventory có thể trả exit 0 dù PARTIAL; phải đọc JSON. Builder thiếu ứng viên có thể xuất `g6_partial_*` và exit 4. Kiểm tra log nếu có sidecar bị từ chối; không đổi hash hoặc đưa bản PARTIAL thành FINAL.

## B13. G7 — khóa checkpoint bằng D_dev_select

```bash
set -euo pipefail
CUDA_VISIBLE_DEVICES='' "$P1P2_PYTHON" -B "$MANUAL/scripts/select_checkpoint_on_dev.py" \
  --manual-root "$MANUAL" --output "$ANALYSIS/g7"
"$P1P2_PYTHON" -B - "$ANALYSIS/g7/checkpoint_selection_seed13.json" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1]).read_bytes())
assert r["status"] == "FINAL" and not r["missing_checkpoints"]
rows = r["rows"]
assert len(rows) == 16 and {(x["method"], x["checkpoint"]) for x in rows} == {
    (m, f"S{i}") for m in ("B4", "B5", "P1-DEFICIT", "P1P2") for i in range(4)
}
assert all(x["denominator"] == 415 and x["missing"] == 0 and x["tie_break"] == "earliest checkpoint" for x in rows)
assert len({x["prediction_sha256"] for x in rows if x["checkpoint"] == "S0"}) == 1
for m in ("B4", "B5", "P1-DEFICIT", "P1P2"):
    candidates = [x for x in rows if x["method"] == m]
    best = min(candidates, key=lambda x: (-x["correct"], int(x["checkpoint"][1:])))["checkpoint"]
    assert all(x["selected_checkpoint"] == best for x in candidates)
    print(m, best)
PY
(
  cd "$ANALYSIS/g7"
  sha256sum checkpoint_selection_seed13.json checkpoint_selection_seed13.csv
)
```

Hai file xuất là `$ANALYSIS/g7/checkpoint_selection_seed13.csv` và `$ANALYSIS/g7/checkpoint_selection_seed13.json`. Chính JSON FINAL là frozen selection manifest. Người duyệt lưu và ký xác nhận SHA-256 của JSON qua kênh độc lập trước mọi truy cập D_test. Cả bốn method cần S0–S3 đã xác thực. S0 là một prediction nguồn, được dùng làm ứng viên cho từng phương pháp. Score strict trên đúng 415 ID từ `splits/p1p2_vfinal_2026-11-16/d_dev_select_ids.txt` và split manifest. Hòa chọn checkpoint sớm nhất. Không dùng lenient hoặc D_test. Nếu thiếu ứng viên chỉ dùng `--partial` ở output mới để chẩn đoán, nhận `checkpoint_selection_seed13_partial.csv` và `checkpoint_selection_seed13_partial.json`. Chế độ PARTIAL không khóa winner. Nếu SHA prediction lịch sử B4 lệch, builder chỉ chấp nhận bản derived đã được khai báo và đúng SHA.

## B14. G8 — tạo lại bảy hình từ dữ liệu đã xác minh

Hiện có bảy PNG và CSV coverage PARTIAL ở `P1P2-Unified/analysis/g8/`, kèm `figure_manifest.json`. Bộ mới dùng lệnh chung dưới đây cho cả bảy hình, vào `$ANALYSIS/figures/`. Khi không truyền `--output`, thư mục mặc định là `$MANUAL/reports/p1p2_integration/final_validation/figures/`. Chạy preflight trước; exit 0 của `--preflight` chỉ cho biết lệnh chạy được, cần kiểm tra từng figure AVAILABLE.

```bash
set -euo pipefail
export CUDA_VISIBLE_DEVICES='' MPLBACKEND=Agg
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_p1p2_analysis_figures.py" \
  --manual-root "$MANUAL" --preflight > "$ANALYSIS/g8-preflight.json"
"$P1P2_PYTHON" -B - "$ANALYSIS/g8-preflight.json" <<'PY'
import json, sys
from pathlib import Path
figures = json.loads(Path(sys.argv[1]).read_bytes())["figures"]
assert len(figures) == 7
for name, item in figures.items():
    assert item["status"] == "AVAILABLE" and not item["partial"] and item["observations"] > 0, (name, item)
PY
"$P1P2_PYTHON" -B "$MANUAL/scripts/build_p1p2_analysis_figures.py" \
  --manual-root "$MANUAL" --output "$ANALYSIS/figures"
"$P1P2_PYTHON" -B - "$ANALYSIS/figures" "$MANUAL/scripts/build_p1p2_analysis_figures.py" <<'PY'
import hashlib, json, sys
from pathlib import Path

out, script = map(Path, sys.argv[1:])
def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

r = json.loads((out / "figure_manifest.json").read_bytes())
assert r["script_sha256"] == sha(script)
assert len(r["figures"]) == 7 and "single seed 13" in r["scope"]
for name, fig in r["figures"].items():
    assert fig["status"] == "GENERATED" and not fig["partial"] and not fig["missing"]
    assert fig["observations"] > 0 and set(fig["outputs"]) == {name + ".png", name + ".csv"}
    for path, digest in fig["inputs"].items():
        assert sha(Path(path)) == digest, path
    for filename, digest in fig["outputs"].items():
        assert sha(out / filename) == digest, filename
    print(name, fig["observations"])
PY
```

Đường dẫn dưới đây đều tính từ `$ANALYSIS/figures/`. Mỗi CSV có `seed_scope` và SHA nguồn. Đối chiếu thêm nội dung của từng hình:

| PNG | CSV nguồn hình | Artifact đầu vào và kiểm chứng |
| --- | --- | --- |
| `selection_jaccard_seed13.png` | `selection_jaccard_seed13.csv` | `train_set.json` và `selection_log.jsonl` theo round của B4/B5/A/B. Đối chiếu giao/hợp của tập trajectory, Jaccard trong [0,1]. |
| `selection_composition_seed13.png` | `selection_composition_seed13.csv` | Tập chọn cùng thứ tự round, gồm new, retained, readmitted. Tổng các nhóm quan sát bằng số được chọn; vòng đầu không có nhóm giữ/chọn lại. |
| `student_accuracy_seed13.png` | `student_accuracy_seed13.csv` | Prediction S0–S3 đã kiểm SHA/lineage, đúng 500 D_dev ID. Kiểm tra denominator 500 và strict accuracy, khác phép chọn 415 ID của G7. |
| `capability_mastery_seed13.png` | `capability_mastery_seed13.csv` | Sidecar Gold, lineage và prediction đã xác minh của S0, B4/B5/A/B. Soát bảy capability, kiểm support và tỷ lệ mastery. |
| `capability_makeup_seed13.png` | `capability_makeup_seed13.csv` | `trajectory/pool/pool_v1_verified.jsonl` cùng selection train/log. Soát selected là tập con eligible đã gắn nhãn, fraction đúng denominator của từng nhóm. |
| `learnability_distribution_seed13.png` | `learnability_distribution_seed13.csv` | L_proxy quan sát trong selection logs của B4/B5/P1P2; đối chiếu round và lineage NLL. Run A không có learnability; L_proxy là score, không phải phần trăm. |
| `p1_capability_learning_curves_seed13.png` | `p1_capability_learning_curves_seed13.csv` | S0 chung và sidecar/prediction Gold của P1-DEFICIT, P1P2 qua S1–S3. Soát đúng hai run và bảy capability. |

Nếu preflight báo thiếu hoặc có fingerprint sai, giữ PARTIAL hoặc BLOCKED và điều tra. Có thể thêm `--preflight --allow-partial` để xem coverage; khi cần vẽ quan sát có sẵn dùng `--allow-partial` trong namespace riêng. Builder trả exit 4 khi sinh bộ chưa đủ. Không biến phần thiếu thành zero, không báo phân tích nhiều seed, không suy ra cạnh graph từ co-occurrence hay mastery.

## B15. D_test — đánh giá cuối cần phê duyệt riêng

D_test không nằm trong controller round S0–S3. Chỉ dùng wrapper `run_final_d_test.py` sau khi G7 **FINAL**, JSON frozen và SHA được duyệt độc lập, evaluator fingerprint/version trùng manifest, selected adapter hoặc S0 reference trùng SHA, output path chưa tồn tại và có phê duyệt final test theo method. Wrapper hiện hỗ trợ `P1-DEFICIT` và `P1P2`; B4/B5 cần quy trình provenance adapter riêng. Không dùng kết quả test để chọn checkpoint hoặc hiệu chỉnh.

Có thể chuẩn bị audit ID/SHA thuần CPU trước. Nó không suy luận và phải báo `D_TEST_EXECUTION=NOT_RUN` với 1.319 ID. So sánh evaluator fingerprint với file audit trong seal:

```bash
set -euo pipefail
CUDA_VISIBLE_DEVICES='' "$P1P2_PYTHON" -B "$MANUAL/scripts/run_final_d_test.py" \
  --audit-only > "$LOG_ROOT/d-test-readiness.json"
"$P1P2_PYTHON" -B - "$LOG_ROOT/d-test-readiness.json" "$P1P2_PACKAGE/manifests/d_test_input_audit.json" <<'PY'
import json, sys
from pathlib import Path
a, b = (json.loads(Path(x).read_bytes()) for x in sys.argv[1:])
assert a["D_TEST_EXECUTION"] == "NOT_RUN" and a["n_test"] == 1319
assert a == b
PY
```

**Lệnh chuẩn bị cho lần thực thi tương lai. Chỉ chạy sau khi được duyệt D_test riêng.** Đặt `G7_FROZEN_SHA` từ reviewer và `EVALUATOR_SHA` từ audit đã được pin, không tạo pin mới từ file đang bị nghi ngờ. Dùng GPU/BF16 đã được phê duyệt. `APPROVED_FINAL_D_TEST` phải bằng method đã được duyệt.

```bash
(
  set -euo pipefail
  : "${FINAL_METHOD:?set approved P1-DEFICIT or P1P2}"
  : "${G7_FROZEN_SHA:?set independently pinned FINAL selection SHA}"
  : "${EVALUATOR_SHA:?set approved evaluator fingerprint}"
  test "${APPROVED_FINAL_D_TEST:-}" = "$FINAL_METHOD"
  "$P1P2_PYTHON" -B "$MANUAL/scripts/run_final_d_test.py" --execute \
    --method "$FINAL_METHOD" --selection "$ANALYSIS/g7/checkpoint_selection_seed13.json" \
    --selection-sha256 "$G7_FROZEN_SHA" --evaluator-sha256 "$EVALUATOR_SHA"
)
```

Sau lần được duyệt, kết quả ở `$MANUAL/reports/p1p2_integration/final_d_test/<method>_seed13_<checkpoint>/` có `predictions.jsonl`, `summary.json` và `provenance.json`. Báo strict accuracy bằng số `status == "valid"` chia 1.319 và Wilson 95% CI. Pending dir hoặc collision thì bảo toàn output và chuyển B17.

## B16. Thu kết quả và trả về Windows

Tạo từng return bundle từ receipt PASS ngay sau B11, trước khi checkpoint tiếp theo nối thêm vào run checkpoint log. Một receipt cũ ghi SHA của trạng thái tại thời điểm nó được tạo; collect sau khi log đã thay đổi sẽ fail. Nếu đã chạy vòng sau, dùng receipt PASS mới nhất của cùng run để thu các output hiện tại và giữ receipt/log cũ làm evidence riêng.

```bash
set -euo pipefail
: "${ATTEMPT:?set PASS checkpoint attempt directory}"
: "${RETURN_ROOT:?set persistent transfer directory outside work and package}"
: "${RETURN_LABEL:?set a fresh label, e.g. a-s2}"
mkdir -p "$RETURN_ROOT"
bash "$SOURCE/deployment/collect_results.sh" --package "$P1P2_PACKAGE" \
  --receipt "$ATTEMPT/execution.json" --output "$RETURN_ROOT/$RETURN_LABEL"
sha256sum "$RETURN_ROOT/$RETURN_LABEL/RESULTS_SHA256SUMS.txt"
```

Pin SHA index theo từng scope qua kênh độc lập. Sau G6–G8, tạo index cho báo cáo, manifest và hình từ vùng phân tích mới:

```bash
(
  set -euo pipefail
  set -o noclobber
  cd "$ANALYSIS"
  LC_ALL=C find g6-inventory g6 g7 figures g8-preflight.json -type f -print0 |
    LC_ALL=C sort -z | xargs -0 -r sha256sum > FINAL_ANALYSIS_SHA256SUMS.txt
  sha256sum -c FINAL_ANALYSIS_SHA256SUMS.txt
  sha256sum FINAL_ANALYSIS_SHA256SUMS.txt
)
```

Trên Windows, dùng PowerShell, SSH alias, Python 3.11 và bản source duyệt với `deployment/ops.py`. Đặt các biến môi trường như tên chỉ ra. Download vào hai thư mục **mới** dưới incoming; kiểm tra exit code tại từng bước.

```powershell
$ErrorActionPreference = 'Stop'
$Incoming = $env:P1P2_INCOMING
$Python = $env:P1P2_PYTHON
$Source = $env:P1P2_SOURCE
if (!$Incoming -or !(Test-Path -LiteralPath $Incoming -PathType Container)) { throw 'Set an existing incoming parent' }
foreach ($Label in @($env:P1P2_RETURN_LABEL, $env:P1P2_ANALYSIS_LABEL)) {
    if ($Label -cnotmatch '^[a-zA-Z0-9][a-zA-Z0-9_-]*$') { throw 'Use a simple incoming directory label' }
}
$Result = Join-Path $Incoming $env:P1P2_RETURN_LABEL
$Analysis = Join-Path $Incoming $env:P1P2_ANALYSIS_LABEL
if ((Test-Path -LiteralPath $Result) -or (Test-Path -LiteralPath $Analysis) -or $Result -eq $Analysis) { throw 'Use distinct fresh incoming paths' }
scp -r "$($env:RUNPOD_SSH):$($env:REMOTE_RESULT_DIR)" $Result
if ($LASTEXITCODE -ne 0) { throw 'Result transfer failed' }
& $Python -B (Join-Path $Source 'deployment/ops.py') verify-results --results $Result --expected-sha $env:TRUSTED_RESULTS_SHA
if ($LASTEXITCODE -ne 0) { throw 'Result bundle verification failed' }
scp -r "$($env:RUNPOD_SSH):$($env:REMOTE_ANALYSIS_DIR)" $Analysis
if ($LASTEXITCODE -ne 0) { throw 'Analysis transfer failed' }
$Index = Join-Path $Analysis 'FINAL_ANALYSIS_SHA256SUMS.txt'
if ((Get-FileHash -LiteralPath $Index -Algorithm SHA256).Hash -ne $env:TRUSTED_ANALYSIS_SHA) { throw 'Analysis index SHA mismatch' }
foreach ($Line in Get-Content -LiteralPath $Index) {
    if ($Line -notmatch '^([a-f0-9]{64})  ((g6-inventory|g6|g7|figures)/[a-zA-Z0-9_.-]+|g8-preflight\.json)$') { throw 'Unexpected index entry' }
    $Digest = $Matches[1]
    $File = Join-Path $Analysis $Matches[2]
    if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash -ne $Digest) { throw "SHA mismatch: $File" }
}
```

Trước khi scp, đặt `P1P2_RETURN_LABEL` và `P1P2_ANALYSIS_LABEL` thành tên thư mục đơn đã duyệt. Đối chiếu 75 dòng đầu A S2 byte-for-byte với seal, checkpoint cha/con, số Gold và hash report trước khi nhập vào workflow Windows. Dùng namespace incoming; giữ nguyên file gốc và các absolute locator trong evidence. Ghi mapping Linux → Windows riêng nếu cần tái nhập lineage. Cập nhật recovery với scope, receipt, trạng thái, đường dẫn, SHA, log, checkpoint còn thiếu và bước kế. Bàn giao PNG, CSV, manifest và báo cáo qua kênh được duyệt. Không đưa dữ liệu, weights hoặc runtime logs lên GitHub.

## B17. Xử lý gián đoạn và lỗi

```bash
ps -eo pid,ppid,lstart,args | grep -E '[r]un_p1_p2|[t]rain_round|[e]val_student|[c]ompute_nll'
find "$MANUAL/runs/p1p2_integration" -name .controller.lock -print
find "$LOG_ROOT" -maxdepth 2 \( -name intent.json -o -name execution.json -o -name exit_code.txt \) -print
```

| Tình huống | Hành động |
| --- | --- |
| Mất SSH hoặc pod restart | Giữ cùng persistent volume, mount và work root. Kiểm tra process thật, log và intent trước mọi resume. Nếu job còn chạy, đợi và theo dõi. Lưu stdout/stderr ở terminal multiplexer được host chấp nhận. |
| GPU OOM | Dừng scope, lưu traceback và thông số GPU/VRAM nếu được phép. Đổi sang thiết bị đủ bộ nhớ theo phê duyệt. Mọi thay đổi frozen protocol cần duyệt riêng. |
| Evaluation bị ngắt, partial JSONL | Giữ JSONL, intent và adapter. Xác minh mỗi dòng parse được, newline cuối, ID duy nhất, byte prefix và provenance. Preview scope với work cũ. Nếu dòng hỏng hoặc bị trùng, bảo toàn nguyên file và xin hướng phục hồi từ người chịu trách nhiệm lineage. |
| Lock chưa rõ | Kiểm tra PID, lệnh, thời điểm, host và lần chạy. Không tự xóa lock. Nếu chưa xác minh được chủ hoặc tiến trình còn sống, dừng scope. |
| Cache thiếu hoặc SHA lệch | Đối chiếu seal/transfer manifest với nguồn đã được duyệt. Chuyển lại vào destination mới đã xác minh. Dừng nếu chưa giải được fingerprint. |
| Adapter thiếu, NLL mismatch hoặc sidecar chưa đủ | Kiểm tra train log, NLL tag/adapter SHA, prefix, checkpoint log và hook artifacts. NLL sai không dùng lại. Không tạo sidecar thủ công. Nếu stage hợp lệ có thể tiếp tục, dùng đúng wrapper ở chế độ preview rồi xin phép retry với attempt mới. |
| Collision hoặc adapter đã train | Giữ file hiện có. Chỉ tiếp tục khi wrapper xác minh có thể reuse hoặc kế hoạch đúng scope. Không tái huấn luyện adapter hoàn tất, đè checkpoint, tái chạy S1 hoặc sang S3 khi S2 chưa PASS. |

## B18. Checklist bàn giao theo thứ tự

| Bước | Lệnh hoặc mục thực thi | Đầu ra và điều kiện PASS | Nếu lỗi |
| --- | --- | --- | --- |
| Linux CPU preflight | B5 · `linux_cpu_preflight.sh` | `preflight.json` platform Linux, 103 tests, plans 0/0/4/16; cache, seal và scope đúng | Dừng trước GPU, lưu log và xử lý dependency/paths |
| Run A S2 | B6 · `run_a_s2.sh` và B11 | 75 dòng prefix giữ nguyên từng byte, 500 ID, adapter 26-step đúng SHA, hook/state và receipt PASS | Giữ prefix, adapter, log; preview trước retry |
| Run A S3 | B7 · `run_a_s3.sh` và B11 | A S2 PASS, parent A S2, LoRA, 500 ID, sidecar/state và receipt PASS | Dừng Run A, kiểm tra parent provenance |
| Run B S2 | B8 · `run_b_s2.sh` và B11 | B S1 đã reuse, NLL S1 và alpha 0.5, parent B S1, 500 ID, hook/state PASS | Bảo toàn NLL/artifact, xác minh S1 trước retry |
| Run B S3 | B9 · `run_b_s3.sh` và B11 | B S2 PASS, NLL S2 và parent B S2, LoRA, 500 ID, hook/state PASS | Dừng Run B, xác minh cả hai parent references |
| G6 | B12 · `build_capability_learning_dynamics.py` | CSV/JSON/MD/inventory, 85 Gold, 7 capability, đủ candidate, single seed | Giữ PARTIAL; lưu inventory và lỗi validation |
| G7 | B13 · `select_checkpoint_on_dev.py` | CSV/JSON FINAL, 415 ID, SHA pinned độc lập, đủ candidate | Giữ PARTIAL và chặn D_test |
| G8 | B14 · `build_p1p2_analysis_figures.py` | Bảy PNG + CSV + manifest, SHA và coverage đầy đủ | Giữ PARTIAL, ghi input thiếu hoặc sai SHA |
| Result transfer | B16 · `collect_results.sh` và `verify-results` | Bản incoming mới, SHA và lineage khớp, PNG/CSV/report đã bàn giao | Cách ly incoming, giữ original và điều tra |
| D_test readiness | B15 · `run_final_d_test.py --audit-only` | 1.319 ID, evaluator pin khớp và có FINAL selection pin để xin phê duyệt riêng; execution vẫn NOT_RUN | Chặn final test |
| Final handoff | B16 · cập nhật recovery và gửi evidence cho reviewer | Receipt, environment, SHA, kết quả strict D_dev, G6/G7/G8, blocker và phê duyệt có thể kiểm chứng | Ghi trạng thái thực tế, checkpoint và thao tác tiếp theo |
