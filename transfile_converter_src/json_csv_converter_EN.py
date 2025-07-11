#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fantasian ND Exclusive JSON ↔ CSV Conversion GUI Tool
(Full Format Validation, Asynchronous Log Queue, Batch Refresh, Clear Logs)
Dependencies: Python Standard Library (tkinter, json, csv, logging, threading, queue, os, re, codecs)
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

# Global log queue
log_queue = queue.Queue()

# Log Handler: Push logs into queue
class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put(msg)
        except Exception:
            pass

# --- File format validation functions ---

def detect_bom(path):
    with open(path, 'rb') as f:
        head = f.read(3)
    if head.startswith(codecs.BOM_UTF8):
        raise ValueError(f"{path}: UTF-8 BOM detected. Please resave the file with UTF-8 encoding without BOM (recommended: use VSCode for a simple and intuitive fix).")

def detect_newlines(path, expected=b'\r\n'):
    with open(path, 'rb') as f:
        data = f.read()
    if expected == b'\r\n':
        if re.search(rb'(?<!\r)\n', data) or re.search(rb'\r(?!\n)', data):
            raise ValueError(f"{path}: Line endings are not strictly CRLF (\\r\\n). Please convert them consistently (recommended: use VSCode).")

def validate_json(path):
    detect_bom(path)
    with open(path, 'r', encoding='utf-8', newline='') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines, 1):
        if i < len(lines) and not ln.endswith('\r\n'):
            raise ValueError(f"{path}: Line {i} has incorrect line ending. Expected CRLF")
    text = ''.join(lines)
    try:
        data = json.loads(text)
    except JSONDecodeError as e:
        raise ValueError(f"{path}: JSON syntax error at line {e.lineno}, column {e.colno} — {e.msg}")
    md = data.get("messageDictionary")
    if not isinstance(md, dict):
        raise ValueError(f"{path}: Missing top-level field: 'messageDictionary'")
    ent = md.get("entries")
    if not isinstance(ent, dict):
        raise ValueError(f"{path}: Field 'entries' is missing from 'messageDictionary'")
    arr = ent.get("Array")
    if not isinstance(arr, list):
        raise ValueError(f"{path}: 'Array' is missing from 'entries' or is not a list")
    return data

def validate_csv(path):
    detect_bom(path)
    with open(path, 'rb') as f:
        raw = f.read()
    if re.search(rb'(?<!\r)\n', raw) or re.search(rb'\r(?!\n)', raw):
        raise ValueError(f"{path}: Line endings are not strictly CRLF (\\r\\n). Please convert them consistently.")
    text = raw.decode('utf-8')
    lines = text.splitlines()
    reader0 = csv.reader(lines)
    header = next(reader0, None)
    if not header:
        raise ValueError(f"{path}: CSV file is empty or missing a header row.")
    required = ["key", "Message", "VoiceId"]
    missing = set(required) - set(header)
    if missing:
        raise ValueError(f"{path}: Missing required columns: {missing}")
    exp_cols = len(header)
    for idx, row in enumerate(reader0, start=2):
        if len(row) != exp_cols:
            raise ValueError(f"{path}: Row {idx} has {len(row)} columns; expected {exp_cols}.")
    return lines

# --- Utility functions ---

def ensure_ext(path: str, ext: str):
    if not path.lower().endswith(ext):
        raise ValueError(f"File must end with {ext}: {path}")

def sniff_csv(csv_path: str):
    try:
        with open(csv_path, 'rb') as f:
            sample = f.read(2048).decode('utf-8', 'ignore')
            return csv.Sniffer().sniff(sample)
    except Exception:
        return csv.get_dialect('excel')

# --- Conversion logic ---

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
                logging.info(f"[JSON→CSV] Processed {idx}/{total}")

    logging.info(f"JSON→CSV completed. Output saved to: {csv_file}")

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
            logging.info(f"[CSV→JSON] Processed {idx}/{total}")

    if updated == 0:
        raise RuntimeError("No entries were updated. Please check if keys match.")
    if unmatched:
        logging.warning(f"The following keys were not matched: {set(unmatched)}")

    with open(out_json, 'w', encoding='utf-8', newline='\r\n') as f_out:
        json.dump(data, f_out, ensure_ascii=False, indent=4)

    logging.info(f"CSV→JSON completed. {updated} entries updated. Output saved to: {out_json}")

# --- GUI Main Application ---

class App:
    def __init__(self, root):
        self.root = root
        root.title("FANTASIAN Neo Dimension Localization JSON ↔ CSV Converter")
        root.geometry("700x600")

        log_frame = tk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_txt = scrolledtext.ScrolledText(log_frame, state=tk.DISABLED)
        self.log_txt.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = tk.Frame(root)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=5)

        self.mode = tk.StringVar(value="to_csv")
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

        btn_clear = tk.Button(ctrl_frame, text="Clear Log", command=self.clear_log)
        btn_clear.pack(side=tk.RIGHT)

        handler = QueueHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)
        self.root.after(100, self.poll_log_queue)

        self.frm_params = tk.Frame(root)
        self.frm_params.pack(fill=tk.X, padx=5, pady=5)
        self.params = {}
        self.build_params()

        btn_run = tk.Button(root, text="Run", command=self.on_run)
        btn_run.pack(pady=5)

    def build_params(self):
        for w in self.frm_params.winfo_children():
            w.destroy()

        mode = self.mode.get()
        rows = []
        if mode == "to_csv":
            rows = [("Input JSON:", "json_in"), ("Output CSV:", "csv_out")]
        else:
            rows = [
                ("Original JSON:", "json_in"),
                ("Input CSV:",     "csv_in"),
                ("Output JSON:",   "json_out")
            ]

        for label, key in rows:
            frm = tk.Frame(self.frm_params)
            frm.pack(fill=tk.X, pady=2)
            tk.Label(frm, text=label, width=12).pack(side=tk.LEFT)
            var = tk.StringVar()
            self.params[key] = var
            tk.Entry(frm, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(
                frm, text="Browse",
                command=lambda k=key: self.browse_file(k)
            ).pack(side=tk.RIGHT)

    def browse_file(self, key):
        filetypes = {
            "json_in": [("JSON File", "*.json")],
            "csv_in":  [("CSV File",  "*.csv")],
            "csv_out": [("CSV File",  "*.csv")],
            "json_out":[("JSON File", "*.json")],
        }
        if key in ("csv_out", "json_out"):
            f = filedialog.asksaveasfilename(
                initialdir=os.getcwd(),
                title="Select Output File",
                defaultextension=filetypes[key][0][1],
                filetypes=filetypes[key]
            )
        else:
            f = filedialog.askopenfilename(
                initialdir=os.getcwd(),
                title="Select Input File",
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
            logging.info(f"Starting mode: {mode}")

            if mode == "to_csv":
                json_in = self.params["json_in"].get().strip()
                csv_out = self.params["csv_out"].get().strip()

                if not json_in:
                    messagebox.showerror("Error", "Please specify the input JSON file.")
                    return

                if not csv_out:
                    csv_out = os.path.abspath("original_text_output.csv")
                    self.params["csv_out"].set(csv_out)
                    logging.info(f"Output CSV not specified. Using default file: {csv_out}")

                convert_to_csv(json_in, csv_out)

            else:
                json_in  = self.params["json_in"].get().strip()
                csv_in   = self.params["csv_in"].get().strip()
                json_out = self.params["json_out"].get().strip()

                if not json_in:
                    messagebox.showerror("Error", "Please specify the original JSON file.")
                    return
                if not csv_in:
                    messagebox.showerror("Error", "Please specify the input CSV file.")
                    return
                if not json_out:
                    json_out = os.path.abspath("translated_text_output.json")
                    self.params["json_out"].set(json_out)
                    logging.info(f"Output JSON not specified. Using default file: {json_out}")

                convert_to_json(json_in, csv_in, json_out)

            messagebox.showinfo("Done", "Operation completed successfully.")

        except Exception as e:
            logging.error(e)
            messagebox.showerror("Error", str(e))

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
