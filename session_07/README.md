# Buổi 7 — Hugging Face `transformers` và Reasoning Prompting

Ngày học: 24/07/2026

> **Trạng thái:** thư mục hiện chỉ có `docs/` — chưa có notebook/app bài làm. README này tóm tắt nội dung suy ra từ hai tài nguyên trong `docs/`.

## Mục tiêu

Sáu buổi đầu, LLM luôn là một **API trả phí ở xa** (OpenAI, Groq). Buổi 7 rẽ sang hai hướng mới:

1. **Chạy model open-source bằng `transformers`** — tải weight về, tự tokenize, tự decode. Xuống một tầng trừu tượng so với LangChain, để thấy bên trong `.invoke()` thực sự có gì.
2. **Reasoning prompting** — các kỹ thuật prompt giúp model giải bài toán cần suy luận nhiều bước: Chain-of-Thought, Tree-of-Thought, Self-Consistency.

Hai tài nguyên: `docs/[Resource] 1. BART HuggingFace` và `docs/[Resource] 3. Reasoning Prompting`.

## Phần A — BART và thư viện `transformers`

### 1. Một base model, nhiều "đầu" (head) khác nhau

BART là kiến trúc **encoder-decoder**. Cùng một bộ weight `facebook/bart-*`, nhưng gắn head khác nhau thì làm được tác vụ khác nhau:

| Class | Tác vụ | Output thô |
| --- | --- | --- |
| `BartForConditionalGeneration` | Mask filling, Summarization | Sinh chuỗi token mới |
| `BartForSequenceClassification` | Phân loại văn bản | `logits` trên tập nhãn |
| `BartForQuestionAnswering` | Hỏi đáp trích xuất | `start_logits`, `end_logits` |

Đây là ý tưởng nền của transfer learning: phần encoder-decoder học hiểu ngôn ngữ được dùng chung, chỉ lớp cuối là chuyên biệt hoá theo tác vụ.

### 2. Cặp bài trùng `AutoTokenizer` + model

```python
from transformers import AutoTokenizer, BartForConditionalGeneration

tokenizer = AutoTokenizer.from_pretrained(...)
model     = BartForConditionalGeneration.from_pretrained(...)
```

Quy trình luôn gồm 3 bước, khác hẳn với `.invoke("câu hỏi")` của LangChain:

```
text  --tokenizer-->  input_ids (số)  --model-->  logits (số)  --tokenizer.decode-->  text
```

**Tokenizer và model phải cùng một checkpoint.** Dùng lệch nhau thì `input_ids` ánh xạ sai từ vựng và output thành vô nghĩa.

### 3. Mask filling — model đoán từ bị che

```python
TXT = "My friends are <mask> but they eat too many carbs."

masked_index = (input_ids[0] == tokenizer.mask_token_id).nonzero().item()
probs = logits[0, masked_index].softmax(dim=0)
values, predictions = probs.topk(5)

tokenizer.decode(predictions).split()
```

Đoạn này bóc trần cách một language model hoạt động:

- `logits` là điểm số **thô** cho **toàn bộ từ vựng** tại vị trí đó.
- `.softmax(dim=0)` chuyển logits thành phân phối xác suất (tổng = 1).
- `.topk(5)` lấy 5 ứng viên xác suất cao nhất.
- `tokenizer.decode()` dịch id ngược lại thành chữ.

Hiểu chuỗi này rồi thì `temperature`, `top_k`, `top_p` ở các buổi trước không còn là tham số ma thuật: chúng chỉ là cách can thiệp vào bước lấy mẫu từ phân phối này.

### 4. Text classification — `argmax` và `id2label`

```python
with torch.no_grad():
    logits = model(**inputs).logits

predicted_class_id = logits.argmax().item()
model.config.id2label[predicted_class_id]
```

- **`torch.no_grad()`** — tắt tính gradient. Chỉ suy luận chứ không huấn luyện, nên bỏ gradient để tiết kiệm bộ nhớ và chạy nhanh hơn. Đây là thói quen bắt buộc khi inference.
- **`model.config.id2label`** — model trả về **số** (index của nhãn); `id2label` là dict ánh xạ số đó về tên nhãn người đọc được.
- **`**inputs`** — tokenizer trả về dict (`input_ids`, `attention_mask`), unpack thẳng vào model.

### 5. Extractive QA — trả lời bằng cách chỉ vào đoạn văn

```python
question, text = "Who was Jim Henson?", "Jim Henson was a nice puppet"

answer_start_index = outputs.start_logits.argmax()
answer_end_index   = outputs.end_logits.argmax()

predict_answer_tokens = inputs.input_ids[0, answer_start_index : answer_end_index + 1]
tokenizer.decode(predict_answer_tokens, skip_special_tokens=True)
```

Khác biệt cốt lõi so với các buổi trước: model **không sinh chữ mới**, nó chỉ dự đoán **vị trí bắt đầu và kết thúc** của câu trả lời trong đoạn văn gốc.

Hệ quả thực tế: extractive QA **không thể bịa** — câu trả lời bắt buộc là một đoạn nguyên văn từ context. Đánh đổi là nó không tổng hợp hay diễn giải được, và câu trả lời không có sẵn trong văn bản thì chịu.

### 6. Thoáng qua về huấn luyện

```python
target_start_index = torch.tensor([14])
target_end_index   = torch.tensor([15])

outputs = model(**inputs, start_positions=target_start_index, end_positions=target_end_index)
loss = outputs.loss
```

Truyền thêm **nhãn đúng** thì model trả về `loss` — độ lệch giữa dự đoán và đáp án. Đây là con số mà quá trình fine-tuning tìm cách giảm dần. Notebook chỉ dừng ở mức cho thấy nó tồn tại, không huấn luyện thật.

### 7. Summarization và `model.generate()`

```python
summary_ids = model.generate(inputs["input_ids"], num_beams=2, min_length=0, max_length=20)
tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
```

`generate()` là hàm sinh chuỗi. Ba tham số điều khiển:

| Tham số | Ý nghĩa |
| --- | --- |
| `num_beams=2` | **Beam search** — giữ 2 chuỗi ứng viên tốt nhất tại mỗi bước thay vì chỉ chọn token tốt nhất (greedy). Chất lượng cao hơn, chậm hơn |
| `min_length` / `max_length` | Khống chế độ dài output |
| `skip_special_tokens=True` | Bỏ các token kỹ thuật (`<s>`, `</s>`, `<pad>`) khỏi kết quả |

BART được huấn luyện sẵn cho summarization, nên đây là tóm tắt **không cần prompt** — khác hẳn cách buổi 3 phải viết cả đoạn chỉ dẫn cho LLM.

## Phần B — Reasoning Prompting

### 8. Chuẩn bị: `pipeline`, dataset và tính lặp lại

```python
from transformers import pipeline
from datasets import load_dataset

def set_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

set_seed(42)

dataset = load_dataset("HuggingFaceH4/MATH-500", split="test")
data = dataset.to_list()
```

- **`pipeline`** — API cấp cao của `transformers`, gộp tokenizer + model + hậu xử lý vào một lời gọi. Nhận thẳng `messages` dạng `[{"role": ..., "content": ...}]` giống các buổi trước.
- **`set_seed`** — cố định mọi nguồn ngẫu nhiên để chạy lại ra cùng kết quả. Bắt buộc khi muốn **so sánh công bằng** giữa các kỹ thuật prompt.
- **MATH-500** — 500 bài toán có đáp án chuẩn, dùng làm thước đo. Notebook chạy trên GPU T4 (metadata `"accelerator": "GPU"`).

Điểm phương pháp luận đáng học: muốn kết luận "kỹ thuật A tốt hơn B" thì phải có **bộ dữ liệu có đáp án** + **seed cố định**, chứ không thể thử vài câu rồi cảm nhận.

### 9. Bốn cấp độ prompt, cùng một bài toán

**(a) Normal prompt** — hỏi thẳng, đòi đáp án luôn:

```python
system_prompt = """You will be given a math problem and need to provide a concise factoid answer in Markdown format.
Answer in the form: `Answer: <answer>`. The answer must be a single number or a mathematical expression."""
```

Model phải "nhảy" thẳng tới đáp án. Với bài nhiều bước, đây là nơi nó sai nhiều nhất.

**(b) Chain-of-Thought (CoT)** — thêm đúng một câu:

```python
system_prompt_cot = """You will be given a math problem. Let's think step by step before answering
and provide a concise factoid answer in Markdown format.
Answer in the form: `Answer: <answer>`. ..."""
```

Câu thần chú **"Let's think step by step"** buộc model viết ra các bước trung gian trước khi kết luận. Cơ chế: mỗi token sinh ra đều nằm trong context của token sau, nên viết ra bước 1 giúp model "có chỗ tựa" để làm bước 2 — thay vì phải nhẩm hết trong một lần dự đoán.

Chi phí: output dài hơn nhiều → tốn token và thời gian hơn.

**(c) Tree-of-Thought (ToT)** — mô phỏng nhiều hướng suy nghĩ song song:

```python
prompt_tree = """
Imagine three different experts are independently solving the question.
All experts will write down 1 step of their thinking, then share it with the group.
Then all experts will go on to the next step, etc.
If any expert realises they're wrong at any point, they leave."""
```

CoT đi theo **một** mạch suy luận — sai ở bước đầu là hỏng cả bài. ToT yêu cầu model dựng ra nhiều "chuyên gia" cùng suy luận và loại bỏ hướng sai giữa chừng, tức là mô phỏng việc **quay lui** (backtracking) trong một lần gọi model.

**(d) Self-Consistency** — không đổi prompt, đổi cách lấy kết quả:

```python
answers = []
samples = 10
for _ in range(samples):
    out = pipe(messages, max_new_tokens=2000, do_sample=True)   # do_sample=True → mỗi lần khác nhau
    text = out[0]["generated_text"][-1]["content"].strip()
    if "Answer:" in text:
        ans = text.split("Answer:")[-1].strip().split()[0]
    else:
        ans = re.sub(r'[^0-9]+', '', text.split()[-1])
    answers.append(ans)

final = Counter(answers).most_common(1)[0][0]
```

Chạy CoT **10 lần** với `do_sample=True` (bật ngẫu nhiên), rồi lấy đáp án **xuất hiện nhiều nhất** bằng `Counter.most_common(1)`.

Ý tưởng: có nhiều đường sai khác nhau nhưng thường chỉ có một đường đúng, nên đáp án đúng có xu hướng lặp lại nhiều nhất qua các lần chạy. Đây là "bỏ phiếu đa số" áp cho LLM.

Chi phí: **đắt gấp `samples` lần**. Đổi tiền và thời gian lấy độ chính xác.

### 10. Định dạng đáp án là một quyết định thiết kế

Cả bốn prompt đều ép ``Answer: <answer>`` — không phải để đẹp, mà để **chấm điểm tự động được**:

```python
ans = text.split("Answer:")[-1].strip().split()[0]
```

Và luôn có nhánh dự phòng khi model không tuân thủ format:

```python
else:
    ans = text.split()[-1]
    ans = re.sub(r'[^0-9]+', '', ans)
```

Bài học: khi output của LLM sẽ bị máy đọc, hãy quy định format ngay trong prompt **và** viết fallback cho trường hợp model không nghe lời. (Buổi 4 giải cùng vấn đề này bằng một cách chắc chắn hơn — structured output.)

### 11. Tổng kết: chọn kỹ thuật nào

| Kỹ thuật | Chi phí | Khi nào dùng |
| --- | --- | --- |
| Normal | 1× | Câu hỏi tra cứu, một bước |
| Chain-of-Thought | ~2–4× (output dài) | Bài cần suy luận nhiều bước — mặc định nên dùng |
| Tree-of-Thought | ~3–6× | Bài dễ đi sai hướng ngay từ đầu, cần cân nhắc nhiều cách |
| Self-Consistency | ~10× (theo `samples`) | Cần độ chính xác cao nhất, chấp nhận đắt |

Lưu ý thực tế: các model **reasoning** đời mới (o-series, GPT-5, Qwen3 với `<think>`) đã tự làm CoT bên trong — bạn đã thấy khối `<think>` trong output ở buổi 4. Với những model này, ép CoT bằng prompt vừa thừa vừa có thể phản tác dụng. Kỹ thuật ở đây phát huy giá trị nhất với model **thường**, không có reasoning tích hợp.

## Các file trong thư mục

| File | Nội dung |
| --- | --- |
| `docs/[Resource] 1. BART HuggingFace` | Notebook đề bài — mask filling, classification, QA, summarization với BART |
| `docs/[Resource] 3. Reasoning Prompting` | Notebook đề bài — MATH-500, Normal / CoT / ToT / Self-Consistency |
| `docs/STEM_Reasoning_Lab_Test_Cases.pdf` | Bộ test case cho project "STEM Reasoning Lab" |
| `docs/docker-compose.yaml` | Stack Postgres + backend + frontend của project |

Tài nguyên được đánh số **1** và **3** — bản số 2 chưa có trong thư mục.

## Project đi kèm: STEM Reasoning Lab

Đọc `docs/docker-compose.yaml` thấy rõ project ứng dụng trực tiếp phần B:

```yaml
HF_EXECUTION_MODE: inference
HF_TOKEN: ${HF_TOKEN:-}
HF_MODEL_ID: ${HF_MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}
HF_INFERENCE_PROVIDER: ${HF_INFERENCE_PROVIDER:-auto}
HF_MAX_NEW_TOKENS: ${HF_MAX_NEW_TOKENS:-1400}
HF_TEMPERATURE: ${HF_TEMPERATURE:-0.35}
SELF_CONSISTENCY_SAMPLES: ${SELF_CONSISTENCY_SAMPLES:-5}
```

Vài điểm đáng chú ý:

- **`HF_EXECUTION_MODE: inference`** — gọi Hugging Face Inference API thay vì tải weight về chạy local. Container không cần GPU, chỉ cần `HF_TOKEN`.
- **`SELF_CONSISTENCY_SAMPLES: 5`** — chính là biến `samples` trong notebook, giờ thành tham số cấu hình. 5 thay vì 10 là đánh đổi chi phí/độ chính xác cho môi trường production.
- **`HF_MAX_NEW_TOKENS: 1400`** — phải rộng rãi vì CoT sinh ra output rất dài.
- **`HF_TEMPERATURE: 0.35`** — thấp nhưng khác 0, vì self-consistency **cần** một chút ngẫu nhiên để 5 lần chạy khác nhau.
- Cấu trúc còn lại (healthcheck, `depends_on: service_healthy`, `${VAR:-default}`) giống hệt buổi 5. Điểm mới: `init: true` (chạy init process để xử lý zombie process) và `depends_on: ... restart: true` cho frontend.

Code backend/frontend chưa có trong repo.

## Cách chạy (khi có notebook)

```bash
pip install transformers datasets torch

# Notebook reasoning cần GPU — chạy trên Google Colab với runtime T4 là phù hợp nhất
```
