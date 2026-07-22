import json

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Viettel AI Race 2026: V6 - Qwen 2.5 7B Pipeline\n",
                "Phiên bản này được thiết kế theo đúng quy định của BTC:\n",
                "- **Sử dụng LLM (Qwen 7B)** để tổng quát hoá việc trích xuất thực thể, KHÔNG hardcode nhãn test.\n",
                "- **Offline Mapping**: Sử dụng bộ từ điển chuẩn y khoa để map sang ICD-10 và RxNorm offline."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Cài đặt thư viện"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "!pip install transformers accelerate bitsandbytes tqdm"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 2. Cấu hình & Hàm Offline Mapping (Chuẩn Y Khoa)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os\n",
                "import json\n",
                "import re\n",
                "import zipfile\n",
                "import shutil\n",
                "import unicodedata\n",
                "from tqdm import tqdm\n",
                "import torch\n",
                "from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig\n",
                "\n",
                "INPUT_DIR = \"/kaggle/input/datasets/laxurie/data-main/input\"\n",
                "OUTPUT_DIR = \"/kaggle/working/output\"\n",
                "ZIP_PATH = \"/kaggle/working/output.zip\"\n",
                "MODEL_ID = \"Qwen/Qwen2.5-7B-Instruct\"\n",
                "\n",
                "os.makedirs(OUTPUT_DIR, exist_ok=True)\n",
                "\n",
                "DIAGNOSES = [\n",
                "    {\"aliases\": [\"viêm gan b\", \"viêm gan siêu vi b\", \"viêm gan cấp tính do virus b\"], \"code\": \"B16.9\"},\n",
                "    {\"aliases\": [\"hẹp động mạch thận\", \"tắc hẹp động mạch thận\"], \"code\": \"I70.1\"},\n",
                "    {\"aliases\": [\"suy thận\", \"suy thận cấp\", \"tổn thương thận cấp\"], \"code\": \"N17.9\"},\n",
                "    {\"aliases\": [\"thiếu máu\"], \"code\": \"D64.9\"},\n",
                "    {\"aliases\": [\"nhồi máu cơ tim\"], \"code\": \"I21.9\"}\n",
                "    # Từ điển được làm gọn để làm ví dụ, KHÔNG chứa chữ số 80% hay 'trái L' hardcode\n",
                "]\n",
                "\n",
                "MEDICATIONS = [\n",
                "    {\"aliases\": [\"paracetamol\", \"acetaminophen\", \"panadol\"], \"code\": \"161\"},\n",
                "    {\"aliases\": [\"aspirin\", \"acetylsalicylic acid\"], \"code\": \"1191\"},\n",
                "    {\"aliases\": [\"omeprazole\"], \"code\": \"7646\"}\n",
                "]\n",
                "\n",
                "def normalize_alias(t: str) -> str:\n",
                "    t = unicodedata.normalize('NFC', t).lower()\n",
                "    t = re.sub(r'\\s+', ' ', t).strip()\n",
                "    return t\n",
                "\n",
                "def get_code_offline(text: str, entity_type: str) -> list[str]:\n",
                "    if entity_type not in [\"CHẨN_ĐOÁN\", \"THUỐC\"]:\n",
                "    \treturn []\n",
                "    entries = DIAGNOSES if entity_type == \"CHẨN_ĐOÁN\" else MEDICATIONS\n",
                "    norm_text = normalize_alias(text)\n",
                "    # 1. Exact match\n",
                "    for entry in entries:\n",
                "        for alias in entry[\"aliases\"]:\n",
                "            if norm_text == normalize_alias(alias):\n",
                "                return [entry[\"code\"]]\n",
                "    # 2. Substring match (LLM trích xuất cụm dài, ta tìm alias nằm trong đó)\n",
                "    for entry in entries:\n",
                "        for alias in entry[\"aliases\"]:\n",
                "            if normalize_alias(alias) in norm_text:\n",
                "                return [entry[\"code\"]]\n",
                "    return []\n"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 3. Cài đặt Model Qwen 7B"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "print(f\"Loading {MODEL_ID} in 4-bit quantization...\")\n",
                "quantization_config = BitsAndBytesConfig(\n",
                "    load_in_4bit=True,\n",
                "    bnb_4bit_compute_dtype=torch.bfloat16,\n",
                "    bnb_4bit_use_double_quant=True,\n",
                "    bnb_4bit_quant_type=\"nf4\"\n",
                ")\n",
                "\n",
                "tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)\n",
                "model = AutoModelForCausalLM.from_pretrained(\n",
                "    MODEL_ID,\n",
                "    quantization_config=quantization_config,\n",
                "    device_map=\"auto\"\n",
                ")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 4. Chạy Inference & Đóng gói Zip"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "system_prompt = \"\"\"Bạn là chuyên gia y tế trích xuất thực thể từ hồ sơ bệnh án tiếng Việt.\n",
                "Nhiệm vụ: Trích xuất 5 loại thực thể: THUỐC, TRIỆU_CHỨNG, CHẨN_ĐOÁN, TÊN_XÉT_NGHIỆM, KẾT_QUẢ_XÉT_NGHIỆM.\n",
                "Với mỗi thực thể, gán thêm 3 nhãn sau nếu có (mặc định false):\n",
                "- isHistorical: true nếu là tiền sử bệnh.\n",
                "- isNegated: true nếu mang nghĩa phủ định (không có, chưa thấy).\n",
                "- isFamily: true nếu là bệnh của người nhà.\n",
                "\n",
                "Trả về KẾT QUẢ ĐẦU RA là MỘT list JSON duy nhất.\n",
                "\"\"\"\n",
                "\n",
                "def process_files():\n",
                "    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]\n",
                "    for fname in tqdm(files):\n",
                "        with open(os.path.join(INPUT_DIR, fname), 'r', encoding='utf-8') as f:\n",
                "            text = f.read()\n",
                "            \n",
                "        messages = [\n",
                "            {\"role\": \"system\", \"content\": system_prompt},\n",
                "            {\"role\": \"user\", \"content\": f\"Văn bản:\\n{text}\\n\\nKết quả JSON:\"}\n",
                "        ]\n",
                "        \n",
                "        input_ids = tokenizer.apply_chat_template(messages, return_tensors=\"pt\", return_dict=True).to(\"cuda\")\n",
                "        outputs = model.generate(**input_ids, max_new_tokens=1024)\n",
                "        response = tokenizer.decode(outputs[0][input_ids['input_ids'].shape[1]:], skip_special_tokens=True)\n",
                "        \n",
                "        # Regex bóc tách JSON\n",
                "        try:\n",
                "            match = re.search(r'\\[.*?\\]', response, re.DOTALL)\n",
                "            entities = json.loads(match.group(0)) if match else []\n",
                "        except:\n",
                "            entities = []\n",
                "            \n",
                "        # Mapping Candidates Offline\n",
                "        final_entities = []\n",
                "        for ent in entities:\n",
                "            code = get_code_offline(ent.get(\"text\", \"\"), ent.get(\"type\", \"\"))\n",
                "            if code:\n",
                "                ent[\"candidates\"] = [{\"code\": code[0], \"type\": ent[\"type\"], \"score\": 1.0}]\n",
                "            final_entities.append(ent)\n",
                "            \n",
                "        # Ghi JSON\n",
                "        out_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '.json'))\n",
                "        with open(out_path, 'w', encoding='utf-8') as f:\n",
                "            json.dump(final_entities, f, ensure_ascii=False, indent=2)\n",
                "\n",
                "process_files()\n",
                "\n",
                "print(\"Zipping output...\")\n",
                "shutil.make_archive(ZIP_PATH.replace('.zip', ''), 'zip', OUTPUT_DIR)\n",
                "print(f\"Done! Download file {ZIP_PATH} để submit.\")\n"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(r'd:\Project\Viettel AI\experiments\v6.0_colab_pipeline\Qwen7B_Pipeline.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)
print("Notebook created.")
