#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fantasian ND 专用 JSON 与 CSV 双向转换 GUI 工具（全面格式校验、队列异步日志、批量刷新、清空日志）
依赖：Python 标准库（tkinter, json, csv, logging, threading, queue, os, re, codecs）
"""

import os
import re
import json
import csv
import codecs
import logging
import threading
import queue
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from json import JSONDecodeError



# 全局日志队列
log_queue = queue.Queue()

# 日志 Handler：把日志放到队列（类型+消息）
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg_type = record.levelname.lower()
            msg = self.format(record)
            log_queue.put((msg_type, msg))
        except Exception:
            pass

# --- 文件格式校验函数集 ---

def detect_bom(path):
    texts = LANG_TEXTS[App.current_lang]
    with open(path, 'rb') as f:
        head = f.read(3)
    if head.startswith(codecs.BOM_UTF8):
        raise ValueError(texts['err_bom'].format(path=path))

def detect_newlines(path, expected=b'\r\n'):
    texts = LANG_TEXTS[App.current_lang]
    with open(path, 'rb') as f:
        data = f.read()
    if expected == b'\r\n':
        if re.search(rb'(?<!\r)\n', data) or re.search(rb'\r(?!\n)', data):
            raise ValueError(texts['err_crlf'].format(path=path))

def validate_json(path):
    texts = LANG_TEXTS[App.current_lang]
    detect_bom(path)
    with open(path, 'r', encoding='utf-8', newline='') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines, 1):
        if i < len(lines) and not ln.endswith('\r\n'):
            raise ValueError(texts['err_json_crlf'].format(path=path, line=i))
    text = ''.join(lines)
    try:
        data = json.loads(text)
    except JSONDecodeError as e:
        raise ValueError(texts['err_json_syntax'].format(path=path, line=e.lineno, col=e.colno, msg=e.msg))
    md = data.get("messageDictionary")
    if not isinstance(md, dict):
        raise ValueError(texts['err_json_missing_dict'].format(path=path))
    ent = md.get("entries")
    if not isinstance(ent, dict):
        raise ValueError(texts['err_json_missing_entries'].format(path=path))
    arr = ent.get("Array")
    if not isinstance(arr, list):
        raise ValueError(texts['err_json_missing_array'].format(path=path))
    return data

def validate_csv(path):
    texts = LANG_TEXTS[App.current_lang]
    detect_bom(path)
    with open(path, 'rb') as f:
        raw = f.read()
    if re.search(rb'(?<!\r)\n', raw) or re.search(rb'\r(?!\n)', raw):
        raise ValueError(texts['err_csv_crlf'].format(path=path))
    text = raw.decode('utf-8')
    lines = text.splitlines()
    reader0 = csv.reader(lines)
    header = next(reader0, None)
    if not header:
        raise ValueError(texts['err_csv_header'].format(path=path))
    required = ["key", "Message", "VoiceId"]
    missing = set(required) - set(header)
    if missing:
        raise ValueError(texts['err_csv_missing_col'].format(path=path, missing=missing))
    exp_cols = len(header)
    for idx, row in enumerate(reader0, start=2):
        if len(row) != exp_cols:
            raise ValueError(texts['err_csv_col_count'].format(path=path, line=idx, count=len(row), expected=exp_cols))
    return lines

def ensure_ext(path: str, ext: str):
    texts = LANG_TEXTS[App.current_lang]
    if not path.lower().endswith(ext):
        raise ValueError(texts['err_csv_ext'].format(ext=ext, path=path))

# --- 转换逻辑 ---

def convert_to_csv(json_file: str, csv_file: str):
    texts = LANG_TEXTS[App.current_lang]
    ensure_ext(json_file, '.json')
    ensure_ext(csv_file, '.csv')

    data = validate_json(json_file)
    entries = data["messageDictionary"]["entries"]["Array"]

    total = len(entries)
    with open(csv_file, 'w', newline='', encoding='utf-8') as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=["key", "Message", "VoiceId"])
        writer.writeheader()
        for idx, entry in enumerate(entries, 1):
            key = entry.get("key", "")
            val = entry.get("value", {}) or {}
            writer.writerow({
                "key":     key,
                "Message": val.get("Message", ""),
                "VoiceId": val.get("VoiceId", "")
            })
            if idx % 10 == 0 or idx == total:
                logging.info(texts['info_json2csv_progress'].format(idx=idx, total=total))

    logging.info(texts['info_json2csv_done'].format(csv_file=csv_file))

def convert_to_json(orig_json: str, csv_file: str, out_json: str):
    texts = LANG_TEXTS[App.current_lang]
    ensure_ext(orig_json, '.json')
    ensure_ext(csv_file, '.csv')
    ensure_ext(out_json, '.json')

    data = validate_json(orig_json)
    lines = validate_csv(csv_file)
    reader = csv.DictReader(lines)

    mapping = {row["key"]: row for row in reader}
    entries = data["messageDictionary"]["entries"]["Array"]

    total = len(entries)
    updated = 0
    unmatched = []
    for idx, entry in enumerate(entries, 1):
        k = entry.get("key")
        val = entry.get("value", {}) or {}
        if k in mapping:
            entry["value"]["Message"] = mapping[k].get("Message", "")
            entry["value"]["VoiceId"] = mapping[k].get("VoiceId", "")
            updated += 1
        else:
            unmatched.append(k)
        if idx % 10 == 0 or idx == total:
            logging.info(texts['info_csv2json_progress'].format(idx=idx, total=total))

    if updated == 0:
        raise RuntimeError(texts['err_json_update_none'])
    if unmatched:
        logging.warning(texts['warn_json_unmatched'].format(unmatched=set(unmatched)))

    with open(out_json, 'w', encoding='utf-8', newline='\r\n') as f_out:
        json.dump(data, f_out, ensure_ascii=False, indent=4)

    logging.info(texts['info_csv2json_done'].format(updated=updated, out_json=out_json))

# --- GUI 主应用 ---

# 多语言文本字典
LANG_TEXTS = {
    'zh': {
        'title': "FANTASIAN Neo Dimension 本地化 JSON ↔ CSV 转换工具 Ver.1.1.0",
        'mode_json2csv': "JSON 转换到 CSV",
        'mode_csv2json': "CSV 转换到 JSON",
        'clear_log': "清空日志",
        'run': "运行",
        'input_json': "输入 JSON:",
        'output_csv': "输出 CSV:",
        'origin_json': "原始 JSON:",
        'input_csv': "输入 CSV:",
        'output_json': "输出 JSON:",
        'browse': "浏览",
        'select_output': "请选择输出文件",
        'select_input': "请选择输入文件",
        'json_file': "JSON 文件",
        'csv_file': "CSV 文件",
        'error': "错误",
        'success': "完成",
        'msg_input_json': "请填写 输入 JSON 文件",
        'msg_output_csv_default': "未指定输出 CSV，使用默认文件：{file}",
        'msg_origin_json': "请填写 原始 JSON 文件",
        'msg_input_csv': "请填写 输入 CSV 文件",
        'msg_output_json_default': "未指定输出 JSON，使用默认文件：{file}",
        'msg_success': "操作成功",
        'msg_start_mode': "开始模式：{mode}",
        'lang_label': "Language:",
        'lang_zh': "中文",
        'lang_en': "English",
        'err_bom': "{path}: 发现 UTF-8 BOM，请重新保存为无 BOM 的 UTF-8 编码！（推荐使用VSCode修改，简单直观。）",
        'err_crlf': "{path}: 换行格式不是纯 CRLF (\\r\\n)，请统一转换！（推荐使用VSCode修改，简单直观。）",
        'err_json_crlf': "{path}: 第 {line} 行结束符错误，应为 CRLF",
        'err_json_syntax': "{path}: JSON 语法错误，行 {line} 列 {col} — {msg}",
        'err_json_missing_dict': "{path}: 缺少顶层字段 'messageDictionary'",
        'err_json_missing_entries': "{path}: messageDictionary 缺少 'entries'",
        'err_json_missing_array': "{path}: entries 缺少 'Array' 或者 Array 不是列表",
        'err_csv_crlf': "{path}: 换行格式不是纯 CRLF (\\r\\n)，请统一转换",
        'err_csv_header': "{path}: CSV 文件为空或缺少表头",
        'err_csv_missing_col': "{path}: 缺少必要列 {missing}",
        'err_csv_col_count': "{path}: 第 {line} 行 列数 {count}，应为 {expected}",
        'err_csv_ext': "文件应以 {ext} 结尾: {path}",
        'err_json_update_none': "未更新任何记录，检查 key 是否匹配",
        'warn_json_unmatched': "以下 key 未匹配：{unmatched}",
        'info_json2csv_progress': "[JSON→CSV] 已处理 {idx}/{total}",
        'info_csv2json_progress': "[CSV→JSON] 已处理 {idx}/{total}",
        'info_json2csv_done': "JSON→CSV 完成，输出：{csv_file}",
        'info_csv2json_done': "CSV→JSON 完成，共更新 {updated} 条，输出：{out_json}",
    },
    'en': {
        'title': "FANTASIAN Neo Dimension Localization JSON ↔ CSV Converter Ver.1.1.0",
        'mode_json2csv': "JSON → CSV",
        'mode_csv2json': "CSV → JSON",
        'clear_log': "Clear Log",
        'run': "Run",
        'input_json': "Input JSON:",
        'output_csv': "Output CSV:",
        'origin_json': "Original JSON:",
        'input_csv': "Input CSV:",
        'output_json': "Output JSON:",
        'browse': "Browse",
        'select_output': "Select Output File",
        'select_input': "Select Input File",
        'json_file': "JSON File",
        'csv_file': "CSV File",
        'error': "Error",
        'success': "Success",
        'msg_input_json': "Please specify input JSON file",
        'msg_output_csv_default': "No output CSV specified, using default file: {file}",
        'msg_origin_json': "Please specify original JSON file",
        'msg_input_csv': "Please specify input CSV file",
        'msg_output_json_default': "No output JSON specified, using default file: {file}",
        'msg_success': "Operation succeeded",
        'msg_start_mode': "Start mode: {mode}",
        'lang_label': "显示语言:",
        'lang_zh': "中文",
        'lang_en': "English",
        'err_bom': "{path}: Found UTF-8 BOM, please save as UTF-8 without BOM! (Recommended: VSCode)",
        'err_crlf': "{path}: Line endings are not pure CRLF (\\r\\n), please convert! (Recommended: VSCode)",
        'err_json_crlf': "{path}: Line {line} ending error, should be CRLF",
        'err_json_syntax': "{path}: JSON syntax error, line {line} col {col} — {msg}",
        'err_json_missing_dict': "{path}: Missing top-level field 'messageDictionary'",
        'err_json_missing_entries': "{path}: messageDictionary missing 'entries'",
        'err_json_missing_array': "{path}: entries missing 'Array' or Array is not a list",
        'err_csv_crlf': "{path}: Line endings are not pure CRLF (\\r\\n), please convert",
        'err_csv_header': "{path}: CSV file is empty or missing header",
        'err_csv_missing_col': "{path}: Missing required columns {missing}",
        'err_csv_col_count': "{path}: Line {line} column count {count}, expected {expected}",
        'err_csv_ext': "File should end with {ext}: {path}",
        'err_json_update_none': "No records updated, check if key matches",
        'warn_json_unmatched': "Unmatched keys: {unmatched}",
        'info_json2csv_progress': "[JSON→CSV] Processed {idx}/{total}",
        'info_csv2json_progress': "[CSV→JSON] Processed {idx}/{total}",
        'info_json2csv_done': "JSON→CSV done, output: {csv_file}",
        'info_csv2json_done': "CSV→JSON done, updated {updated} records, output: {out_json}",
    }
}

class App:
    current_lang = 'zh'  # 静态属性，供校验函数使用

    def __init__(self, root):
        self.root = root
        self.lang = tk.StringVar(value='zh')
        App.current_lang = self.lang.get()
        self.texts = LANG_TEXTS[self.lang.get()]
        root.title(self.texts['title'])
        root.geometry("700x550")

        # 语言选择区（使用 Radiobutton 风格）
        lang_frame = tk.Frame(root)
        lang_frame.pack(fill=tk.X, padx=5, pady=2)
        self.lbl_lang = tk.Label(lang_frame, text=self.texts['lang_label'])
        self.lbl_lang.pack(side=tk.LEFT)
        self.rb_lang_zh = tk.Radiobutton(
            lang_frame, text=LANG_TEXTS['zh']['lang_zh'],
            variable=self.lang, value='zh',
            command=self.on_lang_change
        )
        self.rb_lang_zh.pack(side=tk.LEFT, padx=10)
        self.rb_lang_en = tk.Radiobutton(
            lang_frame, text=LANG_TEXTS['en']['lang_en'],
            variable=self.lang, value='en',
            command=self.on_lang_change
        )
        self.rb_lang_en.pack(side=tk.LEFT, padx=10)
        self.lang_frame = lang_frame

        # 日志区
        log_frame = tk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_txt = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED)
        self.log_txt.pack(fill=tk.BOTH, expand=True)

        # 控制区：模式选择 + 清空日志
        ctrl_frame = tk.Frame(root)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        self.mode = tk.StringVar(value="to_csv")
        mode_frame = tk.Frame(ctrl_frame)
        mode_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.rb_json2csv = tk.Radiobutton(
            mode_frame, text=self.texts['mode_json2csv'],
            variable=self.mode, value="to_csv",
            command=self.build_params
        )
        self.rb_json2csv.pack(side=tk.LEFT, padx=10)
        self.rb_csv2json = tk.Radiobutton(
            mode_frame, text=self.texts['mode_csv2json'],
            variable=self.mode, value="to_json",
            command=self.build_params
        )
        self.rb_csv2json.pack(side=tk.LEFT, padx=10)

        self.btn_clear = tk.Button(ctrl_frame, text=self.texts['clear_log'], command=self.clear_log)
        self.btn_clear.pack(side=tk.RIGHT)

        handler = QueueHandler()
        handler.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        self.root.after(100, self.poll_log_queue)

        self.frm_params = tk.Frame(root)
        self.frm_params.pack(fill=tk.X, padx=5, pady=5)
        self.params = {}
        self.build_params()

        self.btn_run = tk.Button(root, text=self.texts['run'], command=self.on_run)
        self.btn_run.pack(pady=5)

    def on_lang_change(self, *_):
        App.current_lang = self.lang.get()
        self.texts = LANG_TEXTS[self.lang.get()]
        self.root.title(self.texts['title'])
        self.lbl_lang.config(text=self.texts['lang_label'])
        self.rb_lang_zh.config(text=self.texts['lang_zh'])
        self.rb_lang_en.config(text=self.texts['lang_en'])
        self.rb_json2csv.config(text=self.texts['mode_json2csv'])
        self.rb_csv2json.config(text=self.texts['mode_csv2json'])
        self.btn_clear.config(text=self.texts['clear_log'])
        self.btn_run.config(text=self.texts['run'])
        self.build_params()
        # 刷新日志区内容为当前语言
        self.refresh_log_language()

    def refresh_log_language(self):
        # 只刷新已知的提示文本（如“完成”、“错误”等），不翻译用户日志内容
        # 可根据需要扩展
        pass  # 日志内容一般为运行时动态生成，不做翻译

    def build_params(self):
        for w in self.frm_params.winfo_children():
            w.destroy()

        mode = self.mode.get()
        rows = []
        if mode == "to_csv":
            rows = [(self.texts['input_json'], "json_in"), (self.texts['output_csv'], "csv_out")]
        else:
            rows = [
                (self.texts['origin_json'], "json_in"),
                (self.texts['input_csv'],   "csv_in"),
                (self.texts['output_json'], "json_out")
            ]

        for label, key in rows:
            frm = tk.Frame(self.frm_params)
            frm.pack(fill=tk.X, pady=2)
            tk.Label(frm, text=label, width=16).pack(side=tk.LEFT)
            var = tk.StringVar()
            self.params[key] = var
            tk.Entry(frm, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(
                frm, text=self.texts['browse'],
                command=lambda k=key: self.browse_file(k)
            ).pack(side=tk.RIGHT)

    def browse_file(self, key):
        filetypes = {
            "json_in": [(self.texts['json_file'], "*.json")],
            "csv_in":  [(self.texts['csv_file'],  "*.csv")],
            "csv_out": [(self.texts['csv_file'],  "*.csv")],
            "json_out":[(self.texts['json_file'], "*.json")],
        }
        if key in ("csv_out", "json_out"):
            f = filedialog.asksaveasfilename(
                initialdir=os.getcwd(),
                title=self.texts['select_output'],
                defaultextension=filetypes[key][0][1],
                filetypes=filetypes[key]
            )
        else:
            f = filedialog.askopenfilename(
                initialdir=os.getcwd(),
                title=self.texts['select_input'],
                filetypes=filetypes[key]
            )
        if f:
            self.params[key].set(f)

    def clear_log(self):
        self.log_txt.config(state=tk.NORMAL)
        self.log_txt.delete('1.0', tk.END)
        self.log_txt.config(state=tk.DISABLED)

    def poll_log_queue(self):
        while not log_queue.empty():
            msg_type, msg = log_queue.get_nowait()
            # 根据类型加前缀，始终用当前语言
            if msg_type == "error":
                msg = f"{self.texts['error']}: {msg}"
            elif msg_type == "info":
                msg = f"{self.texts['success']}: {msg}"
            elif msg_type == "warning":
                msg = f"WARNING: {msg}"  # 可扩展为多语言
            self.log_txt.config(state=tk.NORMAL)
            self.log_txt.insert(tk.END, msg + '\n')
            self.log_txt.yview(tk.END)
            self.log_txt.config(state=tk.DISABLED)
        self.root.after(100, self.poll_log_queue)

    def on_run(self):
        threading.Thread(target=self.run_task, daemon=True).start()

    def run_task(self):
        try:
            mode = self.mode.get()
            logging.info(self.texts['msg_start_mode'].format(mode=self.texts['mode_json2csv'] if mode == "to_csv" else self.texts['mode_csv2json']))

            if mode == "to_csv":
                json_in = self.params["json_in"].get().strip()
                csv_out = self.params["csv_out"].get().strip()

                if not json_in:
                    messagebox.showerror(self.texts['error'], self.texts['msg_input_json'])
                    logging.error(self.texts['msg_input_json'])
                    return

                if not csv_out:
                    csv_out = os.path.abspath("original_text_output.csv")
                    self.params["csv_out"].set(csv_out)
                    msg = self.texts['msg_output_csv_default'].format(file=csv_out)
                    logging.info(msg)

                convert_to_csv(json_in, csv_out)

            else:
                json_in  = self.params["json_in"].get().strip()
                csv_in   = self.params["csv_in"].get().strip()
                json_out = self.params["json_out"].get().strip()

                if not json_in:
                    messagebox.showerror(self.texts['error'], self.texts['msg_origin_json'])
                    logging.error(self.texts['msg_origin_json'])
                    return
                if not csv_in:
                    messagebox.showerror(self.texts['error'], self.texts['msg_input_csv'])
                    logging.error(self.texts['msg_input_csv'])
                    return

                if not json_out:
                    json_out = os.path.abspath("translated_text_output.json")
                    self.params["json_out"].set(json_out)
                    msg = self.texts['msg_output_json_default'].format(file=json_out)
                    logging.info(msg)

                convert_to_json(json_in, csv_in, json_out)

            messagebox.showinfo(self.texts['success'], self.texts['msg_success'])
            logging.info(self.texts['msg_success'])

        except Exception as e:
            logging.error(str(e))
            messagebox.showerror(self.texts['error'], str(e))

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
