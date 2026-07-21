import os
from extract_entities import process_file

INPUT_DIR = r"d:\Project\Viettel AI\input\input"
OUTPUT_DIR = r"d:\Project\Viettel AI\output"

file_path = os.path.join(INPUT_DIR, "1.txt")
output_path = os.path.join(OUTPUT_DIR, "1.json")

print("Processing 1.txt...")
process_file(file_path, output_path)
print("Done. Check", output_path)
