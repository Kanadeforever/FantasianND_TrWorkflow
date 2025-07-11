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

# 日志 Handler：把日志放到队列
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put(msg)
        except Exception:
            pass

# --- 文件格式校验函数集 ---

def detect_bom(path):
    with open(path, 'rb') as f:
        head = f.read(3)
    if head.startswith(codecs.BOM_UTF8):
        raise ValueError(f"{path}: 发现 UTF-8 BOM，请重新保存为无 BOM 的 UTF-8 编码！（推荐使用VSCode修改，简单直观。）")

def detect_newlines(path, expected=b'\r\n'):
    with open(path, 'rb') as f:
        data = f.read()
    # 检查有没有孤立的 \n 或 \r
    if expected == b'\r\n':
        if re.search(rb'(?<!\r)\n', data) or re.search(rb'\r(?!\n)', data):
            raise ValueError(f"{path}: 换行格式不是纯 CRLF (\\r\\n)，请统一转换！（推荐使用VSCode修改，简单直观。）")

def validate_json(path):
    # 1. BOM 检测
    detect_bom(path)
    # 2. 换行检测
    with open(path, 'r', encoding='utf-8', newline='') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines, 1):
        if i < len(lines) and not ln.endswith('\r\n'):
            raise ValueError(f"{path}: 第 {i} 行结束符错误，应为 CRLF")
    text = ''.join(lines)
    # 3. 语法检测
    try:
        data = json.loads(text)
    except JSONDecodeError as e:
        raise ValueError(f"{path}: JSON 语法错误，行 {e.lineno} 列 {e.colno} — {e.msg}")
    # 4. 结构检测
    md = data.get("messageDictionary")
    if not isinstance(md, dict):
        raise ValueError(f"{path}: 缺少顶层字段 'messageDictionary'")
    ent = md.get("entries")
    if not isinstance(ent, dict):
        raise ValueError(f"{path}: messageDictionary 缺少 'entries'")
    arr = ent.get("Array")
    if not isinstance(arr, list):
        raise ValueError(f"{path}: entries 缺少 'Array' 或者 Array 不是列表")
    return data

def validate_csv(path):
    # 1. BOM 检测
    detect_bom(path)
    # 2. 换行检测
    with open(path, 'rb') as f:
        raw = f.read()
    if re.search(rb'(?<!\r)\n', raw) or re.search(rb'\r(?!\n)', raw):
        raise ValueError(f"{path}: 换行格式不是纯 CRLF (\\r\\n)，请统一转换")
    # 3. 列名与列数检测
    text = raw.decode('utf-8')
    lines = text.splitlines()
    reader0 = csv.reader(lines)
    header = next(reader0, None)
    if not header:
        raise ValueError(f"{path}: CSV 文件为空或缺少表头")
    required = ["key", "Message", "VoiceId"]
    missing = set(required) - set(header)
    if missing:
        raise ValueError(f"{path}: 缺少必要列 {missing}")
    exp_cols = len(header)
    for idx, row in enumerate(reader0, start=2):
        if len(row) != exp_cols:
            raise ValueError(f"{path}: 第 {idx} 行 列数 {len(row)}，应为 {exp_cols}")
    # 4. 返回可供 DictReader 使用的行列表
    return lines

# --- 其他工具函数 ---

def ensure_ext(path: str, ext: str):
    if not path.lower().endswith(ext):
        raise ValueError(f"文件应以 {ext} 结尾: {path}")

def sniff_csv(csv_path: str):
    try:
        with open(csv_path, 'rb') as f:
            sample = f.read(2048).decode('utf-8', 'ignore')
            return csv.Sniffer().sniff(sample)
    except Exception:
        return csv.get_dialect('excel')

# --- 转换逻辑 ---

def convert_to_csv(json_file: str, csv_file: str):
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
                logging.info(f"[JSON→CSV] 已处理 {idx}/{total}")

    logging.info(f"JSON→CSV 完成，输出：{csv_file}")

def convert_to_json(orig_json: str, csv_file: str, out_json: str):
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
            logging.info(f"[CSV→JSON] 已处理 {idx}/{total}")

    if updated == 0:
        raise RuntimeError("未更新任何记录，检查 key 是否匹配")
    if unmatched:
        logging.warning(f"以下 key 未匹配：{set(unmatched)}")

    with open(out_json, 'w', encoding='utf-8', newline='\r\n') as f_out:
        json.dump(data, f_out, ensure_ascii=False, indent=4)

    logging.info(f"CSV→JSON 完成，共更新 {updated} 条，输出：{out_json}")

# --- GUI 主应用 ---

class App:
    def __init__(self, root):
        self.root = root
        root.title("FANTASIAN Neo Dimension 本地化 JSON ↔ CSV 转换工具")
        root.geometry("700x600")

        # 日志区
        log_frame = tk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_txt = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED)
        self.log_txt.pack(fill=tk.BOTH, expand=True)

        # 控制区：模式选择 + 清空日志
        ctrl_frame = tk.Frame(root)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        self.mode = tk.StringVar(value="to_csv")
        # 居中子 Frame
        mode_frame = tk.Frame(ctrl_frame)
        mode_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Radiobutton(
            mode_frame, text="JSON → CSV",
            variable=self.mode, value="to_csv",
            command=self.build_params
        ).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(
            mode_frame, text="CSV → JSON",
            variable=self.mode, value="to_json",
            command=self.build_params
        ).pack(side=tk.LEFT, padx=10)

        btn_clear = tk.Button(ctrl_frame, text="清空日志", command=self.clear_log)
        btn_clear.pack(side=tk.RIGHT)

        # 加载日志 handler 并启动队列轮询
        handler = QueueHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        self.root.after(100, self.poll_log_queue)

        # 参数区
        self.frm_params = tk.Frame(root)
        self.frm_params.pack(fill=tk.X, padx=5, pady=5)
        self.params = {}
        self.build_params()

        # 运行按钮
        btn_run = tk.Button(root, text="运行", command=self.on_run)
        btn_run.pack(pady=5)

    def build_params(self):
        for w in self.frm_params.winfo_children():
            w.destroy()

        mode = self.mode.get()
        rows = []
        if mode == "to_csv":
            rows = [("输入 JSON:", "json_in"), ("输出 CSV:", "csv_out")]
        else:
            rows = [
                ("原始 JSON:", "json_in"),
                ("输入 CSV:",   "csv_in"),
                ("输出 JSON:", "json_out")
            ]

        for label, key in rows:
            frm = tk.Frame(self.frm_params)
            frm.pack(fill=tk.X, pady=2)
            tk.Label(frm, text=label, width=12).pack(side=tk.LEFT)
            var = tk.StringVar()
            self.params[key] = var
            tk.Entry(frm, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(
                frm, text="浏览",
                command=lambda k=key: self.browse_file(k)
            ).pack(side=tk.RIGHT)

    def browse_file(self, key):
        filetypes = {
            "json_in": [("JSON 文件", "*.json")],
            "csv_in":  [("CSV 文件",  "*.csv")],
            "csv_out": [("CSV 文件",  "*.csv")],
            "json_out":[("JSON 文件", "*.json")],
        }
        if key in ("csv_out", "json_out"):
            f = filedialog.asksaveasfilename(
                initialdir=os.getcwd(),
                title="请选择输出文件",
                defaultextension=filetypes[key][0][1],
                filetypes=filetypes[key]
            )
        else:
            f = filedialog.askopenfilename(
                initialdir=os.getcwd(),
                title="请选择输入文件",
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
            msg = log_queue.get_nowait()
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
            logging.info(f"开始模式：{mode}")

            if mode == "to_csv":
                json_in = self.params["json_in"].get().strip()
                csv_out = self.params["csv_out"].get().strip()

                # 必填校验
                if not json_in:
                    messagebox.showerror("错误", "请填写 输入 JSON 文件")
                    return

                # 默认输出
                if not csv_out:
                    # csv_out = "original_text_output.csv"
                    csv_out = os.path.abspath("original_text_output.csv")
                    self.params["csv_out"].set(csv_out)
                    logging.info(f"未指定输出 CSV，使用默认文件：{csv_out}")

                convert_to_csv(json_in, csv_out)

            else:  # CSV -> JSON
                json_in  = self.params["json_in"].get().strip()
                csv_in   = self.params["csv_in"].get().strip()
                json_out = self.params["json_out"].get().strip()

                # 缺少原始 JSON
                if not json_in:
                    messagebox.showerror("错误", "请填写 原始 JSON 文件")
                    return
                # 缺少输入 CSV
                if not csv_in:
                    messagebox.showerror("错误", "请填写 输入 CSV 文件")
                    return

                # 默认输出 JSON
                if not json_out:
                    # json_out = "translated_text_output.json"
                    json_out = os.path.abspath("translated_text_output.json")
                    self.params["json_out"].set(json_out)
                    logging.info(f"未指定输出 JSON，使用默认文件：{json_out}")

                convert_to_json(json_in, csv_in, json_out)

            messagebox.showinfo("完成", "操作成功")

        except Exception as e:
            logging.error(e)
            messagebox.showerror("错误", str(e))

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
