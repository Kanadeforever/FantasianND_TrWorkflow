#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import locale
import platform
import ctypes
import chardet
import io

def detect_system_language():
    sys_name = platform.system()
    if sys_name == 'Windows':
        try:
            buf = ctypes.create_unicode_buffer(85)
            length = ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, len(buf))
            if length > 0:
                return buf.value
        except Exception:
            pass
    for env in ('LC_ALL', 'LANG', 'LANGUAGE'):
        v = os.environ.get(env)
        if v:
            return v.split('.')[0]
    try:
        locale.setlocale(locale.LC_CTYPE, '')
        lang, _ = locale.getlocale(locale.LC_CTYPE)
        if lang:
            return lang
    except Exception:
        pass
    return None

def is_chinese_language(lang):
    return bool(lang) and lang.lower().startswith('zh')

def show_message(zh, en, lang):
    print(zh if is_chinese_language(lang) else en)

def detect_file_encoding(path, sniff_bytes=10000):
    with open(path, 'rb') as f:
        raw = f.read(sniff_bytes)
    det = chardet.detect(raw)
    enc = det.get('encoding') or 'utf-8'
    if raw.startswith(b'\xef\xbb\xbf') and 'utf-8' in enc.lower():
        return 'utf-8-sig'
    return enc

def process_and_repair_csv(input_file, lang_code):
    base, ext = os.path.splitext(input_file)
    temp_file = f"{base}_done_temp{ext}"
    final_file = f"{base}_done{ext}"

    # 1. 读取并删除原文件第二列，剥除 BOM 残留
    encoding = detect_file_encoding(input_file)
    rows = []
    with open(input_file, 'r', encoding=encoding, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            clean = [cell.lstrip('\ufeff') for cell in row]
            if len(clean) > 1:
                del clean[1]
            rows.append(clean)

    # 2. 写入临时文件：表头 + 删除后的数据，UTF-8 无 BOM + CRLF
    buf = io.StringIO()
    # 初步使用固定三列表头
    buf.write("key,Message,VoiceId\r\n")
    writer = csv.writer(buf, lineterminator='\r\n')
    writer.writerows(rows)
    with open(temp_file, 'wb') as f:
        f.write(buf.getvalue().encode('utf-8'))

    # 3. 读取临时文件，动态扩充表头，修复所有行列数
    repaired = []
    with open(temp_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            repaired.append(row)

    # 计算最大列数
    max_cols = max(len(r) for r in repaired)

    # 构建最终表头：固定三列 + 多余列自动命名 Extra1, Extra2...
    base_header = ['key', 'Message', 'VoiceId']
    extra_count = max_cols - len(base_header)
    extra_headers = [f"Extra{i}" for i in range(1, extra_count + 1)]
    final_header = base_header + extra_headers

    # 对每一行不足部分补空
    for i, row in enumerate(repaired):
        if len(row) < max_cols:
            repaired[i] = row + [''] * (max_cols - len(row))

    # 4. 写入最终文件
    with open(final_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\r\n')
        writer.writerow(final_header)
        writer.writerows(repaired[1:])  # 跳过临时文件已经写入的表头

    # 5. 删除临时文件
    try:
        os.remove(temp_file)
    except OSError:
        pass

    show_message(
        f"✅ 最终文件已生成并修复列数：{final_file}",
        f"✅ Final CSV created and columns repaired: {final_file}",
        lang_code
    )

def main():
    lang = detect_system_language()
    if len(sys.argv) != 2:
        show_message(
            "用法：将 CSV 文件拖入此程序，或执行：python delete_second_column.py 文件.csv",
            f"Usage: Drag a CSV onto this exe or run: python {os.path.basename(sys.argv[0])} file.csv",
            lang
        )
        sys.exit(1)

    src = sys.argv[1]
    if not os.path.isfile(src):
        show_message("❌ 文件未找到。", "❌ File not found.", lang)
        sys.exit(1)

    process_and_repair_csv(src, lang)

if __name__ == "__main__":
    main()
