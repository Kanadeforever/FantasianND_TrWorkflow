import sys
import json
import os
import chardet
import locale
import platform

# 多语言文本
LANG_TEXTS = {
    'zh': {
        'encoding_detected': "检测到编码：{encoding}",
        'process_done': "✔ 处理完成：{output_path}",
        'usage': "请拖入一个 JSON 文件以处理",
        'wait_exit': "按Enter键退出…",
        'lang_from_windows': "[语言识别] 来自 Windows API：中文环境",
        'lang_from_locale': "[语言识别] 来自 locale：{lang}，中文环境",
        'lang_from_encoding': "[语言识别] 编码偏好：{encoding}，判定为中文环境",
        'lang_fallback': "[语言识别] 未识别为中文环境，默认使用英文",
    },
    'en': {
        'encoding_detected': "Encoding detected: {encoding}",
        'process_done': "✔ Done: {output_path}",
        'usage': "Please drag a JSON file to process",
        'wait_exit': "Press Enter to exit…",
        'lang_from_windows': "[Language Detection] From Windows API: Chinese detected",
        'lang_from_locale': "[Language Detection] From locale: {lang}, Chinese detected",
        'lang_from_encoding': "[Language Detection] From encoding preference: {encoding}, assumed Chinese",
        'lang_fallback': "[Language Detection] Fallback to English",
    }
}

# ✅ Windows: 使用 ctypes 检测系统语言 ID
def is_windows_language_chinese():
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        # 所有常见中文区域 LCID
        chinese_lcids = {
            0x0804,  # zh-CN 简体
            0x0404,  # zh-TW 繁体
            0x0C04,  # zh-HK
            0x1004,  # zh-SG
            0x1404,  # zh-MO
        }
        return lang_id in chinese_lcids
    except Exception:
        return False





# ✅ 跨平台语言检测函数
def detect_lang():
    if platform.system() == "Windows":
        if is_windows_language_chinese():
            print(LANG_TEXTS['zh']['lang_from_windows'])
            return 'zh'

    try:
        lang_code, _ = locale.getlocale()
        if lang_code and lang_code.startswith('zh'):
            print(LANG_TEXTS['zh']['lang_from_locale'].format(lang=lang_code))
            return 'zh'
    except Exception:
        pass

    try:
        encoding = locale.getpreferredencoding()
        if 'gb' in encoding.lower() or 'utf' in encoding.lower():
            print(LANG_TEXTS['zh']['lang_from_encoding'].format(encoding=encoding))
            return 'zh'
    except Exception:
        pass

    print(LANG_TEXTS['en']['lang_fallback'])
    return 'en'

# 🌐 全局语言缓存
CURRENT_LANG = detect_lang()
TEXTS = LANG_TEXTS[CURRENT_LANG]

def detect_encoding(filepath):
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
    input(TEXTS['wait_exit'])
