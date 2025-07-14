# 说明

这里是储存本项目使用工具的源码，或未编译为exe的脚本源文件。

# 文件说明

## [json_csv_converter.py](json_csv_converter.py)

`json_csv_converter.exe` 文件的源码。

## [replace_json_newlines.py](replace_json_newlines.py)

`replace_json_newlines.exe` 文件的源码。

## [process_csv.py](process_csv.py)

用于预处理从 `ParaTranz` 下载回翻译好的csv文件，作用是删除原文列后，追加原本的表头，以简化工作流程。

- 用法:
  - `python process_csv.py [your download csv file]`
  - 举例: `python process_csv.py translated.csv`
  - 举例: `python process_csv.py E:\Desktop\translated.csv`

---

# Description

This directory stores the source code of tools used in this project, or uncompiled script source files.

# File Description

## [json_csv_converter.py](json_csv_converter.py)

Source code of the `json_csv_converter.exe` file.

## [replace_json_newlines.py](replace_json_newlines.py)

Source code of the `replace_json_newlines.exe` file.

## [process_csv.py](process_csv.py)

Used to preprocess the CSV files downloaded from `ParaTranz`, removing the source text column and appending the original headers to streamline the workflow.

- usage:
  - `python process_csv.py [your download csv file]`
  - e.g. `python process_csv.py translated.csv`
  - e.g. `python process_csv.py E:\Desktop\translated.csv`
