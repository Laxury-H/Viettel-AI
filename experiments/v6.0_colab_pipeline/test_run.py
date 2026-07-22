system_prompt = """Bạn là một trợ lý AI y tế chuyên nghiệp và xuất sắc (Expert Medical AI Assistant), được tối ưu hóa đặc biệt cho nhiệm vụ Nhận diện Thực thể Y khoa (Medical Named Entity Recognition) từ hồ sơ bệnh án tiếng Việt.

Nhiệm vụ của bạn:
1. Đọc kỹ đoạn văn bản hồ sơ bệnh án được cung cấp.
2. Trích xuất CHÍNH XÁC và NGẮN GỌN các thực thể y tế thuộc 5 loại sau: THUỐC, TRIỆU_CHỨNG, CHẨN_ĐOÁN, TÊN_XÉT_NGHIỆM, KẾT_QUẢ_XÉT_NGHIỆM.
3. Tuyệt đối KHÔNG trích xuất cả một câu dài (ví dụ: không lấy "đau ngực trái lan ra sau lưng", chỉ lấy "đau ngực").
4. Với mỗi thực thể, xác định mảng "assertions" (các thuộc tính ngữ cảnh) chứa các nhãn sau nếu có:
   - "isHistorical": nếu thực thể là tiền sử bệnh, thuốc từng dùng trước đây.
   - "isNegated": nếu thực thể mang nghĩa phủ định (ví dụ: không ho, chưa thấy, không có).
   - "isFamily": nếu thực thể là bệnh của người nhà bệnh nhân.
   - (Nếu không có thuộc tính nào, hãy trả về mảng rỗng []).

QUAN TRỌNG: BẮT BUỘC trả về kết quả là MỘT mảng JSON duy nhất. KHÔNG giải thích thêm.

Dưới đây là một ví dụ MẪU (Few-shot Example) cực kỳ quan trọng về cách trích xuất:
Văn bản:
'Danh sách thuốc trước nhập viện chính xác và đầy đủ. 1. amlodipine 10 mg po daily 2. aspirin 81 mg po daily 3. metoprolol succinate xl 50 mg po daily 4. guaifenesin ml po q6h:prn điều trị ho 5. nystatin oral suspension 5 ml po qid:prn điều trị đau nhức 6. acetaminophen 325-650 mg po q6h:prn điều trị sốt đau 7. pravastatin 40 mg po daily 8. docusate sodium 100 mg po bid điều trị táo bón 9. senna 8.6 mg po bid:prn điều trị táo bón 10. clonazepam 0.5 mg po qam:prn điều trị lo âu 11. clonazepam 1.5 mg po qhs điều trị lo âu mất ngủ'

Kết quả JSON mẫu mong đợi:
[
  {"text": "amlodipine 10 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "aspirin 81 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "metoprolol succinate xl 50 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "guaifenesin ml po q6h:prn", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "ho", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "nystatin oral suspension 5 ml po qid:prn", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "đau nhức", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "acetaminophen 325-650 mg po q6h:prn", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "sốt đau", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "pravastatin 40 mg po daily", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "docusate sodium 100 mg po bid", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "táo bón", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "senna 8.6 mg po bid:prn", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "táo bón", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "clonazepam 0.5 mg po qam:prn", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "lo âu", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "clonazepam 1.5 mg po qhs", "type": "THUỐC", "assertions": ["isHistorical"]},
  {"text": "lo âu", "type": "TRIỆU_CHỨNG", "assertions": []},
  {"text": "mất ngủ", "type": "TRIỆU_CHỨNG", "assertions": []}
]
"""

def process_files():
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    for fname in tqdm(files):
        with open(os.path.join(INPUT_DIR, fname), 'r', encoding='utf-8') as f:
            text = f.read()
            
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Văn bản:\n{text}\n\nKết quả JSON duy nhất:"}
        ]
        
        input_ids = tokenizer.apply_chat_template(messages, return_tensors="pt", return_dict=True).to("cuda")
        outputs = model.generate(**input_ids, max_new_tokens=2048) # Đã tăng max_new_tokens
        response = tokenizer.decode(outputs[0][input_ids['input_ids'].shape[1]:], skip_special_tokens=True)
        
        # Regex bóc tách JSON cực kỳ linh hoạt
        entities = []
        try:
            # Loại bỏ markdown ticks nếu có
            clean_resp = response.replace('```json', '').replace('```', '').strip()
            match = re.search(r'\[\s*\{.*?\}\s*\]', clean_resp, re.DOTALL)
            if match:
                entities = json.loads(match.group(0))
            else:
                # Fallback: Thử lấy từ dấu [ đầu tiên đến ] cuối cùng
                start = clean_resp.find('[')
                end = clean_resp.rfind(']')
                if start != -1 and end != -1:
                    entities = json.loads(clean_resp[start:end+1])
        except Exception as e:
            print(f"\n[LỖI] Lỗi parse JSON ở file {fname}. Raw response:\n{response[:200]}...")
            # Fallback nếu bị cắt cụt do quá dài
            try:
                if '[' in response:
                    part = response[response.find('['):]
                    if not part.strip().endswith(']'):
                        if not part.strip().endswith('}'):
                            part += '"}'
                        part += ']'
                    entities = json.loads(part)
            except:
                pass
            
        # Post-processing: Position, Assertions, and Candidates
        final_entities = []
        occurrence_tracker = {} # Theo dõi số lần xuất hiện của các từ bị lặp lại
        
        for ent in entities:
            if "text" not in ent or "type" not in ent: continue
            
            ent_text = ent["text"]
            
            # 1. Tính toán position (xử lý triệt để lỗi từ lặp lại nhiều lần)
            import re
            matches = [m for m in re.finditer(re.escape(ent_text), text)]
            if not matches:
                continue # Bỏ qua nếu hallucination
                
            count = occurrence_tracker.get(ent_text, 0)
            if count < len(matches):
                match = matches[count]
                start_idx = match.start()
                end_idx = match.end()
                occurrence_tracker[ent_text] = count + 1
            else:
                # Lấy vị trí cuối cùng nếu LLM sinh lố số lượng thực tế
                match = matches[-1]
                start_idx = match.start()
                end_idx = match.end()
            
            # 2. Xử lý mảng Assertions
            assertions = ent.get("assertions", [])
            if not isinstance(assertions, list):
                assertions = []
            
            # 3. Chuẩn hóa format & Đảm bảo đúng TỨ TỰ KEY của BTC
            formatted_ent = {
                "text": ent_text,
                "type": ent["type"]
            }
            
            # 4. Gắn candidates offline (nếu có thì chèn vào ngay sau type)
            code = get_code_offline(ent_text, ent["type"])
            if code:
                formatted_ent["candidates"] = [code[0]]
                
            formatted_ent["assertions"] = assertions
            formatted_ent["position"] = [start_idx, end_idx]
                
            final_entities.append(formatted_ent)
            
        # Ghi JSON
        out_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '.json'))
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(final_entities, f, ensure_ascii=False, indent=2)

process_files()

print("Zipping output...")
shutil.make_archive(ZIP_PATH.replace('.zip', ''), 'zip', OUTPUT_DIR)
print(f"Done! Download file {ZIP_PATH} để submit.")

