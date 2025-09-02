# 说明

这里是储存本项目使用工具的源码，或未编译为exe的脚本源文件。

# 文件说明

## [json_csv_converter.py](json_csv_converter.py)

`json_csv_converter.exe` 文件的源码。

## [replace_json_newlines.py](replace_json_newlines.py)

`replace_json_newlines.exe` 文件的源码。

## [process_csv.py](process_csv.py)

用于预处理从 `ParaTranz` 下载回翻译好的csv文件，作用是删除原文列后，追加原本的表头、修复格式编码与换行符问题，以简化工作流程。

- 注意:
  - 必须安装依赖项 **chardet** : `pip install chardet`

- 用法:
  - `python process_csv.py [your download csv file]`
  - 举例: `python process_csv.py translated.csv`
  - 举例: `python process_csv.py E:\Desktop\translated.csv`

如果希望编译成exe文件后直接拖拽csv到exe上使用，那么使用 `pyinstaller -F process_csv.py` 指令编译成exe可执行文件即可（请自行安装依赖，或使用 `venv` 指令构建虚拟环境编译）。

---

# Description

This directory stores the source code of tools used in this project, or uncompiled script source files.

# File Description

## [json_csv_converter.py](json_csv_converter.py)

Source code of the `json_csv_converter.exe` file.

## [replace_json_newlines.py](replace_json_newlines.py)

Source code of the `replace_json_newlines.exe` file.

## [process_csv.py](process_csv.py)

Used to pre-process the translated csv files downloaded from `ParaTranz`. Its function is to delete the original columns, append the original headers, and fix format encoding and line break issues to simplify the workflow.

- Notice:
  - Dependencies must be installed **chardet** : `pip install chardet`

- Usage:
  - `python process_csv.py [your download csv file]`
  - e.g. `python process_csv.py translated.csv`
  - e.g. `python process_csv.py E:\Desktop\translated.csv`

If you want to compile it into an exe file and then directly drag the csv to the exe for use, then use the `pyinstaller -F process_csv.py` command to compile it into an exe executable file (please install the dependencies yourself, or use the `venv` command to build a virtual environment for compilation).
