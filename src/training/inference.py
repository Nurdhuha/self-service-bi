from unsloth import FastLanguageModel
from transformers import TextStreamer

# 1. Load model yang baru saja selesai dilatih
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "outputs/checkpoint-60", # Memanggil folder hasil training Anda
    max_seq_length = 2048,
    load_in_4bit = True,
)

# Optimasi Unsloth agar proses tanya-jawab 2x lebih cepat
FastLanguageModel.for_inference(model) 

# 2. Template yang sama dengan saat training
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
"""

# 3. Mari kita uji dengan skenario Text-to-SQL (Ganti instruksi sesuai keinginan Anda)
instruksi = "Buatkan query SQL untuk menampilkan semua nama pelanggan yang berasal dari kota Surabaya."
konteks_skema = "CREATE TABLE pelanggan (id_pelanggan INT, nama VARCHAR(100), kota VARCHAR(50));"

# Memformat pertanyaan
inputs = tokenizer(
[
    alpaca_prompt.format(instruksi, konteks_skema, "")
], return_tensors = "pt").to("cuda")

# 4. Generate dan tampilkan jawaban secara real-time (streaming)
print("\n--- Jawaban Model Llama 3.2 SQL ---\n")
text_streamer = TextStreamer(tokenizer, skip_prompt=True)
_ = model.generate(**inputs, streamer = text_streamer, max_new_tokens = 128)