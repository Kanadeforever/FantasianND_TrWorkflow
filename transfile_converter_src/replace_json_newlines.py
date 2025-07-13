import sys
import json
import os
import chardet
import locale

# 多语言文本
LANG_TEXTS = {
    'zh': {
        'encoding_detected': "检测到编码：{encoding}",
        'process_done': "✔ 处理完成：{output_path}",
        'usage': "请拖入一个 JSON 文件以处理",
    },
    'en': {
        'encoding_detected': "Encoding detected: {encoding}",
        'process_done': "✔ Done: {output_path}",
        'usage': "Please drag a JSON file to process",
    }
}

def get_lang():
    lang = locale.getdefaultlocale()[0] or ''
    # 简体/繁体中文环境
    if lang.startswith('zh'):
        return 'zh'
    return 'en'

TEXTS = LANG_TEXTS[get_lang()]

def detect_encoding(filepath):
    import chardet
    with open(filepath, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def recursive_replace(obj):
    if isinstance(obj, str):
        return obj.replace("\\n", "\n")
    elif isinstance(obj, list):
        return [recursive_replace(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: recursive_replace(value) for key, value in obj.items()}
    else:
        return obj

def process_json(input_path):
    encoding = detect_encoding(input_path)
    print(TEXTS['encoding_detected'].format(encoding=encoding))

    with open(input_path, 'r', encoding=encoding) as f:
        data = json.load(f)

    updated_data = recursive_replace(data)

    output_path = os.path.splitext(input_path)[0] + "_fixed.json"
    with open(output_path, 'w', encoding=encoding) as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)

    print(TEXTS['process_done'].format(output_path=output_path))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(TEXTS['usage'])
    else:
        process_json(sys.argv[1])