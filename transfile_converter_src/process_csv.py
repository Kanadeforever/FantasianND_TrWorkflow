#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import locale
import platform
import ctypes
import chardet

def detect_file_encoding_and_newline(file_path, num_bytes=10000):
    """
    检测文件的编码和换行符类型（CRLF 或 LF）。
    返回 (encoding, newline_str)。
    """
    with open(file_path, 'rb') as f:
        raw = f.read(num_bytes)

    result = chardet.detect(raw)
    encoding = result.get('encoding') or 'utf-8'

    if b'\r\n' in raw:
        newline = '\r\n'
    elif b'\n' in raw:
        newline = '\n'
    else:
        newline = os.linesep

    return encoding, newline

def detect_system_language():
    """
    按平台检测系统语言：
      - Windows：调用 Windows API 获取系统区域设置名称
      - macOS/Linux：读取环境变量 LC_ALL, LANG, LANGUAGE
      - 其他平台：同 Linux/Mac
    返回语言代码字符串（如 "zh-CN"、"en_US"），或 None。
    """
    sys_name = platform.system()

    # Windows: 用 GetUserDefaultLocaleName 获取区域设置
    if sys_name == 'Windows':
        try:
            LOCALE_NAME_MAX_LENGTH = 85
            buf = ctypes.create_unicode_buffer(LOCALE_NAME_MAX_LENGTH)
            length = ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, LOCALE_NAME_MAX_LENGTH)
            if length > 0:
                return buf.value  # e.g. "zh-CN"
        except Exception:
            pass

    # macOS / Linux / 其他：读环境变量
    for env in ('LC_ALL', 'LANG', 'LANGUAGE'):
        val = os.environ.get(env)
        if val:
            return val.split('.')[0]  # 去掉编码后缀

    # 最后尝试 locale.getlocale（fallback）
    try:
        locale.setlocale(locale.LC_CTYPE, '')
        lang, _ = locale.getlocale(locale.LC_CTYPE)
        if lang:
            return lang
    except Exception:
        pass

    return None

def is_chinese_language(lang_code):
    """
    判断是否为任何中文环境（简体/繁体、中国大陆/台湾/香港/澳门/新加坡 等）。
    """
    return bool(lang_code) and lang_code.lower().startswith('zh')

def show_message(chinese_msg, english_msg, lang_code):
    """
    根据系统语言输出中/英提示。
    """
    print(chinese_msg if is_chinese_language(lang_code) else english_msg)

def process_csv(input_file, encoding, newline, lang_code):
    """
    删除第二列并生成输出文件 input_file_done.csv，保持原编码与换行符不变。
    """
    base, ext = os.path.splitext(input_file)
    output_file = f"{base}_done{ext}"

    try:
        with open(input_file, 'r', encoding=encoding, newline='') as infile, \
             open(output_file, 'w', encoding=encoding, newline='') as outfile:

            reader = csv.reader(infile)
            writer = csv.writer(outfile, lineterminator=newline)

            for row in reader:
                if len(row) > 1:
                    del row[1]
                writer.writerow(row)

        show_message(f"✅ 已成功生成：{output_file}",
                     f"✅ File generated: {output_file}",
                     lang_code)

    except Exception as e:
        show_message(f"❌ 出错：{e}",
                     f"❌ Error: {e}",
                     lang_code)

def main():
    lang_code = detect_system_language()

    # 校验命令行参数
    if len(sys.argv) != 2:
        show_message(
            "用法：python delete_second_column.py 文件名.csv",
            f"Usage: python {os.path.basename(sys.argv[0])} filename.csv",
            lang_code
        )
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.isfile(input_file):
        show_message("❌ 未找到指定文件。", "❌ File not found.", lang_code)
        sys.exit(1)

    # 检测编码和换行
    encoding, newline = detect_file_encoding_and_newline(input_file)
    show_message(
        f"📄 检测到编码：{encoding}，换行符：{'CRLF' if newline=='\\r\\n' else 'LF'}",
        f"📄 Detected encoding: {encoding}, newline: {'CRLF' if newline=='\\r\\n' else 'LF'}",
        lang_code
    )

    # 处理 CSV
    process_csv(input_file, encoding, newline, lang_code)

if __name__ == "__main__":
    main()
