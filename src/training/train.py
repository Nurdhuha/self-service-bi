from unsloth import FastLanguageModel
import torch
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# 1. Konfigurasi Model & LoRA
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/Llama-3.2-1B-Instruct",
    max_seq_length = 2048,
    load_in_4bit = True, 
)

model = FastLanguageModel.get_peft_model(
    model,
    r = 16, 
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha = 16,
    lora_dropout = 0,
)

# 2. Template Alpaca
alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{}

### Input:
{}

### Response:
{}"""

EOS_TOKEN = tokenizer.eos_token

def formatting_prompts_func(examples):
    instructions = examples["instruction"]
    contexts     = examples["context"]
    responses    = examples["response"]
    texts = []
    for instruction, context, response in zip(instructions, contexts, responses):
        text = alpaca_prompt.format(instruction, context, response) + EOS_TOKEN
        texts.append(text)
    return { "text" : texts, }

# 3. Load Dataset Baru (Pastikan nama file sesuai dengan yang Anda buat)
dataset = load_dataset("json", data_files={"train": "../../data/processed/dataset_latih.jsonl"}, split="train")
dataset = dataset.map(formatting_prompts_func, batched = True,)

# 4. Setup Trainer - Mode Full Epoch
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text", 
    max_seq_length = 2048,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 15,           # Dinaikkan untuk kelancaran fase awal di dataset yang lebih besar
        num_train_epochs = 3,         # Model akan membaca seluruh 500 data sebanyak 3 kali putaran
        learning_rate = 2e-4,
        fp16 = not torch.cuda.is_bf16_supported(),
        logging_steps = 5,            # Log muncul setiap 5 steps agar terminal rapi
        save_strategy = "epoch",      # Menyimpan checkpoint di setiap akhir epoch
        output_dir = "outputs_full",  # Hasil disimpan di folder baru
    ),
)

# 5. Jalankan Training
trainer.train()

# 6. Simpan LoRA Adapter Secara Permanen setelah training selesai
model.save_pretrained("sql_llama_lora_model")
tokenizer.save_pretrained("sql_llama_lora_model")
print("Pelatihan selesai! Model LoRA telah disimpan di folder 'sql_llama_lora_model'")