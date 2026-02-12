#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF密码移除工具
用已知密码打开PDF并保存为无密码版本
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path
import queue

try:
    import pikepdf
except ImportError:
    pikepdf = None


class PDFUnlockerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF密码移除工具")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        # 文件列表
        self.file_list = []
        # 进度队列
        self.progress_queue = queue.Queue()
        # 处理线程
        self.processing_thread = None
        self.is_processing = False

        self.setup_ui()
        self.check_dependencies()

    def check_dependencies(self):
        """检查依赖库"""
        if pikepdf is None:
            messagebox.showerror(
                "缺少依赖", "未安装 pikepdf 库！\n\n请在终端运行：\npip install pikepdf"
            )

    def setup_ui(self):
        """创建界面"""
        # 顶部按钮区
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="添加文件", command=self.add_files).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="移除选中", command=self.remove_selected).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(btn_frame, text="清空列表", command=self.clear_list).pack(
            side=tk.LEFT, padx=5
        )

        # 文件列表区
        list_frame = ttk.LabelFrame(self.root, text="待处理文件", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 滚动条
        scroll_y = ttk.Scrollbar(list_frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        scroll_x = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.file_listbox = tk.Listbox(
            list_frame,
            selectmode=tk.EXTENDED,
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set,
            font=("Microsoft YaHei UI", 9),
        )
        self.file_listbox.pack(fill=tk.BOTH, expand=True)

        scroll_y.config(command=self.file_listbox.yview)
        scroll_x.config(command=self.file_listbox.xview)

        # 密码输入区
        pwd_frame = ttk.Frame(self.root, padding="10")
        pwd_frame.pack(fill=tk.X)

        ttk.Label(pwd_frame, text="PDF密码:").pack(side=tk.LEFT, padx=5)

        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            pwd_frame, textvariable=self.password_var, show="*", width=30
        )
        self.password_entry.pack(side=tk.LEFT, padx=5)

        self.show_password_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pwd_frame,
            text="显示密码",
            variable=self.show_password_var,
            command=self.toggle_password_visibility,
        ).pack(side=tk.LEFT, padx=5)

        # 保存选项区
        save_frame = ttk.LabelFrame(self.root, text="保存选项", padding="10")
        save_frame.pack(fill=tk.X, padx=10, pady=5)

        self.save_mode_var = tk.StringVar(value="overwrite")

        ttk.Radiobutton(
            save_frame,
            text="覆盖源文件（原文件将被替换）",
            variable=self.save_mode_var,
            value="overwrite",
            command=self.toggle_output_dir,
        ).pack(anchor=tk.W)

        ttk.Radiobutton(
            save_frame,
            text="另存到新位置",
            variable=self.save_mode_var,
            value="saveas",
            command=self.toggle_output_dir,
        ).pack(anchor=tk.W, pady=5)

        # 输出目录选择
        dir_frame = ttk.Frame(save_frame)
        dir_frame.pack(fill=tk.X, padx=20)

        ttk.Label(dir_frame, text="输出目录:").pack(side=tk.LEFT, padx=5)

        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(
            dir_frame, textvariable=self.output_dir_var, state="disabled"
        )
        self.output_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        self.output_dir_btn = ttk.Button(
            dir_frame, text="选择目录", command=self.select_output_dir, state="disabled"
        )
        self.output_dir_btn.pack(side=tk.LEFT)

        # 文件命名选项
        naming_frame = ttk.Frame(save_frame)
        naming_frame.pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(naming_frame, text="文件命名:").pack(side=tk.LEFT, padx=5)

        self.naming_var = tk.StringVar(value="original")
        self.naming_original_rb = ttk.Radiobutton(
            naming_frame,
            text="原名",
            variable=self.naming_var,
            value="original",
            state="disabled",
        )
        self.naming_original_rb.pack(side=tk.LEFT, padx=5)

        self.naming_suffix_rb = ttk.Radiobutton(
            naming_frame,
            text="添加后缀 _unlocked",
            variable=self.naming_var,
            value="suffix",
            state="disabled",
        )
        self.naming_suffix_rb.pack(side=tk.LEFT, padx=5)

        # 开始处理按钮
        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.pack(fill=tk.X)

        self.process_btn = ttk.Button(
            action_frame,
            text="开始处理",
            command=self.start_processing,
            style="Accent.TButton",
        )
        self.process_btn.pack()

        # 进度条
        progress_frame = ttk.Frame(self.root, padding="10")
        progress_frame.pack(fill=tk.X)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="")
        self.progress_label.pack()

        # 日志区
        log_frame = ttk.LabelFrame(self.root, text="处理日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(
            log_frame,
            height=8,
            yscrollcommand=log_scroll.set,
            font=("Consolas", 9),
            state="disabled",
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.log_text.yview)

        # 配置日志颜色标签
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("info", foreground="blue")

    def toggle_password_visibility(self):
        """切换密码显示/隐藏"""
        if self.show_password_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def toggle_output_dir(self):
        """切换输出目录启用状态"""
        if self.save_mode_var.get() == "saveas":
            self.output_dir_entry.config(state="normal")
            self.output_dir_btn.config(state="normal")
            self.naming_original_rb.config(state="normal")
            self.naming_suffix_rb.config(state="normal")
        else:
            self.output_dir_entry.config(state="disabled")
            self.output_dir_btn.config(state="disabled")
            self.naming_original_rb.config(state="disabled")
            self.naming_suffix_rb.config(state="disabled")

    def add_files(self):
        """添加PDF文件"""
        files = filedialog.askopenfilenames(
            title="选择PDF文件", filetypes=[("PDF文件", "*.pdf"), ("所有文件", "*.*")]
        )

        for file in files:
            if file not in self.file_list:
                self.file_list.append(file)
                self.file_listbox.insert(tk.END, file)

    def remove_selected(self):
        """移除选中的文件"""
        selected = self.file_listbox.curselection()
        # 从后往前删除，避免索引变化
        for index in reversed(selected):
            self.file_listbox.delete(index)
            self.file_list.pop(index)

    def clear_list(self):
        """清空文件列表"""
        self.file_listbox.delete(0, tk.END)
        self.file_list.clear()

    def select_output_dir(self):
        """选择输出目录"""
        directory = filedialog.askdirectory(title="选择输出目录")
        if directory:
            self.output_dir_var.set(directory)

    def log_message(self, message, tag="info"):
        """添加日志消息"""
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def start_processing(self):
        """开始处理PDF文件"""
        if pikepdf is None:
            messagebox.showerror("错误", "未安装 pikepdf 库，无法处理PDF文件！")
            return

        if not self.file_list:
            messagebox.showwarning("警告", "请先添加PDF文件！")
            return

        password = self.password_var.get()
        if not password:
            messagebox.showwarning("警告", "请输入PDF密码！")
            return

        # 检查保存模式
        if self.save_mode_var.get() == "saveas":
            output_dir = self.output_dir_var.get()
            if not output_dir:
                messagebox.showwarning("警告", "请选择输出目录！")
                return
            if not os.path.exists(output_dir):
                messagebox.showerror("错误", "输出目录不存在！")
                return
        else:
            # 覆盖模式，确认提示
            result = messagebox.askyesno(
                "确认", "将覆盖源文件，原文件将被替换！\n\n是否继续？", icon="warning"
            )
            if not result:
                return

        # 清空日志
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

        # 禁用按钮
        self.process_btn.config(state="disabled")
        self.is_processing = True

        # 启动处理线程
        self.processing_thread = threading.Thread(
            target=self.process_files,
            args=(self.file_list.copy(), password),
            daemon=True,
        )
        self.processing_thread.start()

        # 启动进度检查
        self.root.after(100, self.check_progress)

    def process_files(self, files, password):
        """处理PDF文件（在后台线程中运行）"""
        total = len(files)
        success_count = 0
        error_count = 0

        for i, file_path in enumerate(files):
            if not self.is_processing:
                break

            try:
                # 更新进度
                progress = (i / total) * 100
                status = f"{i}/{total} 完成"
                self.progress_queue.put(("progress", progress, status))

                file_name = os.path.basename(file_path)
                self.progress_queue.put(("log", f"⧗ 处理中: {file_name}", "info"))

                # 确定输出路径
                if self.save_mode_var.get() == "overwrite":
                    output_path = file_path
                    # 先保存到临时文件
                    temp_path = file_path + ".tmp"
                else:
                    output_dir = self.output_dir_var.get()
                    if self.naming_var.get() == "suffix":
                        # 添加后缀
                        name = Path(file_path).stem
                        output_path = os.path.join(output_dir, f"{name}_unlocked.pdf")
                    else:
                        output_path = os.path.join(output_dir, file_name)
                    temp_path = None

                # 打开PDF并移除密码
                try:
                    pdf = pikepdf.open(file_path, password=password)

                    # 保存无密码版本
                    if temp_path:
                        pdf.save(temp_path)
                        pdf.close()
                        # 替换原文件
                        os.replace(temp_path, output_path)
                    else:
                        pdf.save(output_path)
                        pdf.close()

                    self.progress_queue.put(("log", f"✓ 成功: {file_name}", "success"))
                    success_count += 1

                except pikepdf.PasswordError:
                    self.progress_queue.put(
                        ("log", f"✗ 密码错误: {file_name}", "error")
                    )
                    error_count += 1
                    # 清理临时文件
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)

                except Exception as e:
                    self.progress_queue.put(
                        ("log", f"✗ 处理失败: {file_name} - {str(e)}", "error")
                    )
                    error_count += 1
                    # 清理临时文件
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)

            except Exception as e:
                self.progress_queue.put(
                    ("log", f"✗ 错误: {file_name} - {str(e)}", "error")
                )
                error_count += 1

        # 完成
        progress = 100
        status = f"{total}/{total} 完成"
        self.progress_queue.put(("progress", progress, status))
        self.progress_queue.put(
            (
                "log",
                f"\n处理完成！成功: {success_count}, 失败: {error_count}, 总计: {total}",
                "info" if error_count == 0 else "error",
            )
        )
        self.progress_queue.put(("done", None, None))

    def check_progress(self):
        """检查处理进度"""
        try:
            while True:
                msg_type, data, extra = self.progress_queue.get_nowait()

                if msg_type == "progress":
                    self.progress_var.set(data)
                    self.progress_label.config(text=extra)
                elif msg_type == "log":
                    self.log_message(data, extra)
                elif msg_type == "done":
                    self.process_btn.config(state="normal")
                    self.is_processing = False
                    messagebox.showinfo("完成", "所有文件处理完成！")
                    return

        except queue.Empty:
            pass

        if self.is_processing:
            self.root.after(100, self.check_progress)


def main():
    root = tk.Tk()
    app = PDFUnlockerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
