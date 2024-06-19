import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from spellchecker import SpellChecker

class FileSystemMonitorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TextTracker")
        self.geometry("800x600")
        self.create_widgets()
        self.total_added_text = 0
        self.total_deleted_text = 0
        self.text_info = []
        self.setup_plot()
        self.monitor_thread = None
        self.observer = None
        self.spell = SpellChecker()

    def create_widgets(self):
        self.heading_label = ttk.Label(self, text="TextTracker", font=("Helvetica", 16, "bold"))
        self.heading_label.pack(pady=10)

        self.directory_label = ttk.Label(self, text="Directory to Monitor:")
        self.directory_label.pack(pady=10)

        self.directory_entry = ttk.Entry(self, width=50)
        self.directory_entry.pack(pady=5)

        self.start_button = ttk.Button(self, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.pack(pady=10)

        self.stop_button = ttk.Button(self, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

        self.info_label = ttk.Label(self, text="Text Changes Information:", anchor="w")
        self.info_label.pack(pady=10, fill=tk.X)

        self.info_text = tk.Text(self, height=10, wrap=tk.WORD)
        self.info_text.pack(pady=5, fill=tk.BOTH, expand=True)

        self.figure_frame = ttk.Frame(self)
        self.figure_frame.pack(fill=tk.BOTH, expand=True)

        self.error_label = ttk.Label(self, text="Spelling Errors:", anchor="w", foreground="red")
        self.error_label.pack(pady=10, fill=tk.X)

        self.error_text = tk.Text(self, height=5, wrap=tk.WORD, foreground="red")
        self.error_text.pack(pady=5, fill=tk.BOTH, expand=True)

    def setup_plot(self):
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.figure_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.update_plot()

    def update_plot(self):
        self.ax.clear()
        if self.total_added_text == 0 and self.total_deleted_text == 0:
            self.ax.text(0.5, 0.5, 'No changes detected yet', horizontalalignment='center', verticalalignment='center', transform=self.ax.transAxes)
        else:
            self.ax.pie([self.total_added_text, self.total_deleted_text], labels=['Text Added', 'Text Deleted'], autopct='%1.1f%%', colors=['green', 'red'])
        self.ax.set_title('Text Changes Over Time')
        self.canvas.draw()

    def start_monitoring(self):
        directory = self.directory_entry.get().strip()
        if not os.path.isdir(directory):
            messagebox.showerror("Error", "Invalid directory path!")
            return

        self.total_added_text = 0
        self.total_deleted_text = 0
        self.text_info = []
        self.update_plot()

        self.event_handler = MyFileSystemEventHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.event_handler, directory, recursive=True)
        self.observer.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.monitor_thread = threading.Thread(target=self.monitor_directory)
        self.monitor_thread.start()
        messagebox.showinfo("Monitoring Started", f"Started monitoring the directory: {directory}")

    def stop_monitoring(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if self.monitor_thread:
            self.monitor_thread.join()
        messagebox.showinfo("Monitoring Stopped", "Stopped monitoring the directory.")

    def monitor_directory(self):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()

    def update_changes(self, file_path, added_text, deleted_text):
        self.total_added_text += len(added_text)
        self.total_deleted_text += len(deleted_text)
        self.text_info.append(f"{len(added_text)} characters added, {len(deleted_text)} characters deleted in {file_path}")
        self.check_spelling_errors(added_text)
        self.update_plot()
        self.update_info_text()

    def update_info_text(self):
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        for info in self.text_info:
            self.info_text.insert(tk.END, info + "\n")
        self.info_text.config(state=tk.DISABLED)

    def check_spelling_errors(self, text):
        errors = []
        if text:
            words = text.split()
            misspelled = self.spell.unknown(words)
            for word in misspelled:
                errors.append(f"Misspelled word: {word}")

        self.update_error_text(errors)

    def update_error_text(self, errors):
        self.error_text.config(state=tk.NORMAL)
        self.error_text.delete(1.0, tk.END)
        if errors:
            for error in errors:
                self.error_text.insert(tk.END, error + "\n")
        else:
            self.error_text.insert(tk.END, "No spelling errors detected.\n")
        self.error_text.config(state=tk.DISABLED)

class MyFileSystemEventHandler(FileSystemEventHandler):
    def __init__(self, app):
        self.app = app
        self.file_snapshots = {}

    def on_modified(self, event):
        if not event.is_directory:
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as file:
                new_content = file.read()
            old_content = self.file_snapshots.get(event.src_path, "")
            added_text, deleted_text = self.get_text_changes(old_content, new_content)
            self.app.update_changes(event.src_path, added_text, deleted_text)
            self.file_snapshots[event.src_path] = new_content

    def on_created(self, event):
        if not event.is_directory:
            with open(event.src_path, 'r', encoding='utf-8', errors='ignore') as file:
                self.file_snapshots[event.src_path] = file.read()

    def on_deleted(self, event):
        if not event.is_directory and event.src_path in self.file_snapshots:
            del self.file_snapshots[event.src_path]

    def get_text_changes(self, old_content, new_content):
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        added_text = ''.join([line for line in new_lines if line not in old_lines])
        deleted_text = ''.join([line for line in old_lines if line not in new_lines])
        return added_text, deleted_text

if __name__ == "__main__":
    app = FileSystemMonitorApp()
    app.mainloop()