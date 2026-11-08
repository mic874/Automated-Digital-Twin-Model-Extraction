import torch
from transformers import (
    BartTokenizer,
    BartForConditionalGeneration,
    GenerationConfig,
)
import json
from datetime import datetime
import numpy as np
import random




def formalize_statement(category, original_input):
    

    model_path = f"../PLM_formalization/{category}/bart-manufacturing"

    tokenizer = BartTokenizer.from_pretrained(model_path)

    model = BartForConditionalGeneration.from_pretrained(model_path)

    model.generation_config = GenerationConfig.from_model_config(model.config)

    model.generation_config.max_length = 100
    #model.generation_config.num_beams = 1

    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.to(device)

    # -----------------------------------------------------
    # TOKENIZE INPUT
    # -----------------------------------------------------

    inputs = tokenizer(
        original_input,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128,
    )

    inputs = {k: v.to(device) for k, v in inputs.items()}

    # -----------------------------------------------------
    # GENERATE OUTPUT
    # -----------------------------------------------------

    with torch.no_grad():

        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            num_beams=1,
        )

    predicted_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    predicted_text = predicted_text.replace(" .", "").replace("\u2010", "_").replace("-", "_").replace("__", "_")

    save_formalization(original_input, predicted_text, category)

    return predicted_text


def save_formalization(original_input, predicted_text, category):
   
    entry = {
        "original": original_input,
        "formalization": predicted_text,
        "category": category,
        "timestamp": datetime.utcnow().isoformat(),
        "source": "expert input",
    }

    with open("../output/processed_expert_knowledge", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
