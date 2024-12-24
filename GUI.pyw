import os
import shutil
import subprocess
import threading
import locale
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

process = None
is_running = False

i18n = {
    "en": {
        "title": "Dark Themed Auto Subtitle Generator - Overwrite Prevention",
        "lbl_file": "Video File:",
        "btn_file": "Browse...",
        "lbl_model": "Model:",
        "lbl_task": "Task:",
        "lbl_source_lang": "Source Language:",
        "lbl_target_lang": "Target Language:",
        "lbl_output_dir": "Output Folder:",
        "btn_output_browse": "Browse...",
        "chk_srt_only": "Generate .srt only (no overlayed video)",
        "lbl_cmd_preview": "Command Preview:",
        "lbl_terminal": "Terminal Output:",
        "btn_run": "Run",
        "btn_abort": "Abort",
        "warn_no_cmd": "No command to run.",
        "warn_no_video": "Please select a video file.",
        "err_temp_dir": "Failed to create 'temp' folder:",
        "err_copy_video": "Error copying video to temp folder:",
        "msg_aborted": "\nProcess aborted by user.\n",
        "msg_completed": "\nProcess completed successfully.\n",
        "msg_errorcode": "\nProcess exited with error code ",
        "msg_temp_del_err": "\nError removing temp folder: ",
        "lang_switch": "Language Switch:"
    },
    "tr": {
        "title": "Koyu Temalı Otomatik Altyazı Oluşturma - Çakışma Önleyici",
        "lbl_file": "Video Dosyası:",
        "btn_file": "Gözat...",
        "lbl_model": "Model Seç:",
        "lbl_task": "İşlem Türü:",
        "lbl_source_lang": "Kaynak Dil:",
        "lbl_target_lang": "Hedef Dil:",
        "lbl_output_dir": "Çıkış Klasörü:",
        "btn_output_browse": "Gözat...",
        "chk_srt_only": ".srt dosyası oluştur (gömülü altyazı olmayacak)",
        "lbl_cmd_preview": "Komut Önizleme:",
        "lbl_terminal": "Terminal Çıktısı:",
        "btn_run": "Çalıştır",
        "btn_abort": "Durdur",
        "warn_no_cmd": "Çalıştırılacak komut yok.",
        "warn_no_video": "Lütfen bir video dosyası seçiniz.",
        "err_temp_dir": "'temp' klasörü oluşturulamadı:",
        "err_copy_video": "Geçici klasöre kopyalama hatası:",
        "msg_aborted": "\nİşlem kullanıcı tarafından durduruldu.\n",
        "msg_completed": "\nİşlem başarıyla tamamlandı.\n",
        "msg_errorcode": "\nİşlem hata kodu ile sonlandı: ",
        "msg_temp_del_err": "\nGeçici klasör silinirken hata: ",
        "lang_switch": "Dil Değiştirici:"
    }
}

def create_dark_style(root):
    style = ttk.Style(root)
    style.theme_use('clam')
    
    bg_color = "#2B2B2B"
    fg_color = "#FFFFFF"
    entry_bg = "#3C3F41"
    select_bg = "#4C5052"

    style.configure(".",
                    background=bg_color,
                    foreground=fg_color,
                    fieldbackground=entry_bg)
    
    style.map("TCombobox",
              fieldbackground=[("readonly", entry_bg)],
              selectbackground=[("readonly", select_bg)],
              selectforeground=[("readonly", fg_color)])
    
    style.configure("TButton",
                    background=bg_color,
                    foreground=fg_color,
                    borderwidth=1,
                    focusthickness=3,
                    focustcolor="none")
    style.map("TButton",
              background=[("active", select_bg)])
    
    style.configure("TCheckbutton",
                    background=bg_color,
                    foreground=fg_color)

    style.configure("Vertical.TScrollbar", background=bg_color, troughcolor=bg_color)
    style.configure("Horizontal.TScrollbar", background=bg_color, troughcolor=bg_color)


def get_first_available_basename(base, output_dir, check_srt=True, check_video=True):
    candidate_base = base
    counter = 0
    while True:
        srt_ok = True
        vid_ok = True

        if check_srt:
            srt_path = os.path.join(output_dir, candidate_base + ".srt")
            if os.path.exists(srt_path):
                srt_ok = False

        if check_video:
            vid_path = os.path.join(output_dir, candidate_base + ".mp4")
            if os.path.exists(vid_path):
                vid_ok = False

        if srt_ok and vid_ok:
            return candidate_base

        counter += 1
        candidate_base = f"{base}-{counter}"


def browse_file():
    filename = filedialog.askopenfilename(
        title=i18n[current_lang]["lbl_file"],
        filetypes=[("Video Files", "*.mp4 *.mov *.avi *.mkv *.flv *.wmv *.m4v"), ("All Files", "*.*")]
    )
    if filename:
        video_path_var.set(filename)

def browse_output_dir():
    directory = filedialog.askdirectory(title=i18n[current_lang]["lbl_output_dir"])
    if directory:
        output_dir_var.set(directory)

def on_model_change(*args):
    model_name = model_var.get()
    if model_name.endswith(".en"):
        source_language_var.set("en")
        source_lang_combo.config(state="disabled")
    else:
        source_language_var.set("auto")
        source_lang_combo.config(state="readonly")
    
    update_lang_combo_states()
    update_command_preview()

def on_task_change(*args):
    update_lang_combo_states()
    update_command_preview()

def update_lang_combo_states():
    current_task = task_var.get()
    current_model = model_var.get()

    if current_model.endswith(".en"):
        source_lang_combo.config(state="disabled")
    else:
        source_lang_combo.config(state="readonly")

    if current_task == "transcribe":
        target_lang_combo.config(state="disabled")
    else:
        target_lang_combo.config(state="readonly")

def update_command_preview(*args):
    video_path = video_path_var.get()
    model = model_var.get()
    srt_only = srt_only_var.get()
    task = task_var.get()

    if not output_dir_var.get() and video_path:
        default_dir = os.path.dirname(video_path)
        output_dir_var.set(default_dir)

    out_dir = output_dir_var.get()

    source_lang = source_language_var.get()
    target_lang = target_language_var.get()

    parts = ["auto_subtitle"]

    if video_path:
        parts.append(f'"{video_path}"')
    if model:
        parts.append(f"--model {model}")
    if out_dir:
        parts.append(f'--output_dir "{out_dir}"')

    parts.append("--output_srt True")
    parts.append(f"--srt_only {srt_only}")

    if task == "translate":
        parts.append("--task translate")
        if source_lang:
            parts.append(f"--language {source_lang}")
        if target_lang:
            parts.append(f"--language_out {target_lang}")
    else:
        if source_lang:
            parts.append(f"--language {source_lang}")

    cmd_str = " ".join(parts)

    command_preview.configure(state="normal")
    command_preview.delete("1.0", tk.END)

    tokens = cmd_str.split()
    for token in tokens:
        if token.startswith("--"):
            command_preview.insert(tk.END, token + " ", "option")
        elif token.startswith('"') and token.endswith('"'):
            command_preview.insert(tk.END, token + " ", "path")
        else:
            command_preview.insert(tk.END, token + " ", "normal")

    command_preview.configure(state="disabled")

def get_command_string():
    command_preview.configure(state="normal")
    cmd = command_preview.get("1.0", tk.END).strip()
    command_preview.configure(state="disabled")
    return cmd

def run_or_abort():
    global is_running

    run_button.config(state='disabled')
    if not is_running:
        run_command()
    else:
        abort_command()

    root.after(2000, lambda: run_button.config(state='normal'))

def run_command():
    global is_running

    cmd = get_command_string()
    if not cmd:
        messagebox.showwarning("Warning", i18n[current_lang]["warn_no_cmd"])
        return
    if not video_path_var.get():
        messagebox.showwarning("Warning", i18n[current_lang]["warn_no_video"])
        return
    
    original_video = video_path_var.get()
    video_dir, video_file = os.path.split(original_video)
    base, ext = os.path.splitext(video_file)
    out_dir = output_dir_var.get() or video_dir

    do_srt_only = srt_only_var.get()

    new_base = get_first_available_basename(
        base,
        out_dir,
        check_srt=True,
        check_video=(not do_srt_only)
    )

    temp_folder = os.path.join(video_dir, "temp")
    try:
        os.makedirs(temp_folder, exist_ok=True)
    except Exception as e:
        messagebox.showerror("Error", f"{i18n[current_lang]['err_temp_dir']} {e}")
        return

    temp_video_filename = new_base + ext
    temp_video_path = os.path.join(temp_folder, temp_video_filename)

    try:
        shutil.copy2(original_video, temp_video_path)
    except Exception as e:
        messagebox.showerror("Error", f"{i18n[current_lang]['err_copy_video']} {e}")
        return

    cmd = cmd.replace(f'"{original_video}"', f'"{temp_video_path}"')

    output_text.configure(state="normal")
    output_text.delete("1.0", tk.END)
    output_text.configure(state="disabled")

    run_button.config(text=i18n[current_lang]["btn_abort"])
    is_running = True

    thread = threading.Thread(target=run_subprocess, args=(cmd, temp_folder))
    thread.start()

def abort_command():
    global process, is_running
    if process and is_running:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            process.terminate()
        append_to_terminal(i18n[current_lang]["msg_aborted"], "error")

    run_button.config(text=i18n[current_lang]["btn_run"])
    is_running = False
    process = None

def run_subprocess(cmd, temp_folder):
    global process, is_running

    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    try:
        for raw_line in process.stdout:
            raw_line = raw_line.rstrip('\n')
            parts = raw_line.split('\r')
            for i, segment in enumerate(parts):
                if i > 0:
                    remove_last_line_in_terminal()
                append_to_terminal(segment + "\n", "normal")
            output_text.see(tk.END)
    except Exception as e:
        append_to_terminal(f"\n{i18n[current_lang]['msg_errorcode']}{e}\n", "error")

    retcode = process.wait()
    process = None
    is_running = False

    if retcode == 0:
        append_to_terminal(i18n[current_lang]["msg_completed"], "success")
    else:
        append_to_terminal(f"{i18n[current_lang]['msg_errorcode']}{retcode}.\n", "error")

    try:
        shutil.rmtree(temp_folder)
    except Exception as e:
        append_to_terminal(f"{i18n[current_lang]['msg_temp_del_err']}{e}\n", "error")

    root.after(0, lambda: run_button.config(text=i18n[current_lang]["btn_run"]))

def remove_last_line_in_terminal():
    output_text.configure(state="normal")
    last_index = output_text.index(tk.END)
    line_start = output_text.index(f"{last_index}-1l linestart")
    output_text.delete(line_start, tk.END)
    output_text.configure(state="disabled")

def append_to_terminal(text, tag_name="normal"):
    output_text.configure(state="normal")
    output_text.insert(tk.END, text, tag_name)
    output_text.configure(state="disabled")
    output_text.see(tk.END)

def on_lang_change(*args):
    sel = lang_switch_var.get()
    new_lang = "en" if sel == "English" else "tr"
    set_language_texts(new_lang)
    update_command_preview()

def set_language_texts(lang):
    global current_lang
    current_lang = lang

    root.title(i18n[lang]["title"])
    lbl_file["text"] = i18n[lang]["lbl_file"]
    btn_file["text"] = i18n[lang]["btn_file"]
    lbl_model["text"] = i18n[lang]["lbl_model"]
    lbl_task["text"] = i18n[lang]["lbl_task"]
    lbl_source_lang["text"] = i18n[lang]["lbl_source_lang"]
    lbl_target_lang["text"] = i18n[lang]["lbl_target_lang"]
    lbl_output_dir["text"] = i18n[lang]["lbl_output_dir"]
    btn_output_dir["text"] = i18n[lang]["btn_output_browse"]
    chk_srt_only["text"] = i18n[lang]["chk_srt_only"]
    lbl_preview["text"] = i18n[lang]["lbl_cmd_preview"]
    lbl_output["text"] = i18n[lang]["lbl_terminal"]

    if not is_running:
        run_button["text"] = i18n[lang]["btn_run"]
    else:
        run_button["text"] = i18n[lang]["btn_abort"]

    lbl_lang_switch["text"] = i18n[lang]["lang_switch"]

def main():
    global root, current_lang
    system_locale, _ = locale.getdefaultlocale() or ("", "")
    if system_locale and "tr" in system_locale.lower():
        default_lang = "tr"
    else:
        default_lang = "en"

    root = tk.Tk()

    current_lang = default_lang

    create_dark_style(root)

    global video_path_var, model_var, srt_only_var, output_dir_var
    global command_preview, task_var, output_text, run_button
    global source_lang_combo, target_lang_combo
    global source_language_var, target_language_var
    global lbl_file, btn_file, lbl_model, lbl_task, lbl_source_lang
    global lbl_target_lang, lbl_output_dir, btn_output_dir, chk_srt_only
    global lbl_preview, lbl_output, main_frame, lang_switch_var, lbl_lang_switch

    video_path_var = tk.StringVar()
    model_var = tk.StringVar(value="medium.en")
    srt_only_var = tk.BooleanVar(value=True)
    output_dir_var = tk.StringVar()
    task_var = tk.StringVar(value="transcribe")

    source_language_var = tk.StringVar(value="auto")
    target_language_var = tk.StringVar(value="tr")

    main_frame = ttk.Frame(root, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    source_language_options = ["auto", "tr", "en"]
    target_language_options = ["tr", "en"]
    model_options = [
        "tiny.en","tiny","base.en","base",
        "small.en","small","medium.en","medium",
        "large-v1","large-v2","large-v3","large",
        "large-v3-turbo","turbo"
    ]

    lbl_file = ttk.Label(main_frame)
    lbl_file.grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0,10))

    entry_file = ttk.Entry(main_frame, textvariable=video_path_var, width=50)
    entry_file.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)

    btn_file = ttk.Button(main_frame, command=browse_file)
    btn_file.grid(row=0, column=2, sticky=tk.E, pady=5, padx=5)

    lbl_model = ttk.Label(main_frame)
    lbl_model.grid(row=1, column=0, sticky=tk.W, pady=5)

    combo_model = ttk.Combobox(
        main_frame,
        textvariable=model_var,
        values=model_options,
        state="readonly",
        width=47,
        height=len(model_options)
    )
    combo_model.grid(row=1, column=1, sticky=tk.W, pady=5)

    lbl_task = ttk.Label(main_frame)
    lbl_task.grid(row=2, column=0, sticky=tk.W, pady=5)

    combo_task = ttk.Combobox(
        main_frame,
        textvariable=task_var,
        values=["transcribe", "translate"],
        state="readonly",
        width=47,
        height=2
    )
    combo_task.grid(row=2, column=1, sticky=tk.W, pady=5)

    lbl_source_lang = ttk.Label(main_frame)
    lbl_source_lang.grid(row=3, column=0, sticky=tk.W, pady=5)

    source_lang_combo = ttk.Combobox(
        main_frame,
        textvariable=source_language_var,
        values=source_language_options,
        state="readonly",
        width=47
    )
    source_lang_combo.grid(row=3, column=1, sticky=tk.W, pady=5)

    lbl_target_lang = ttk.Label(main_frame)
    lbl_target_lang.grid(row=4, column=0, sticky=tk.W, pady=5)

    target_lang_combo = ttk.Combobox(
        main_frame,
        textvariable=target_language_var,
        values=target_language_options,
        state="disabled",
        width=47
    )
    target_lang_combo.grid(row=4, column=1, sticky=tk.W, pady=5)

    lbl_output_dir = ttk.Label(main_frame)
    lbl_output_dir.grid(row=5, column=0, sticky=tk.W, pady=5)

    entry_output_dir = ttk.Entry(main_frame, textvariable=output_dir_var, width=50)
    entry_output_dir.grid(row=5, column=1, sticky=tk.W+tk.E, pady=5)

    btn_output_dir = ttk.Button(main_frame, command=browse_output_dir)
    btn_output_dir.grid(row=5, column=2, sticky=tk.E, pady=5, padx=5)

    chk_srt_only = ttk.Checkbutton(
        main_frame,
        variable=srt_only_var
    )
    chk_srt_only.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5)

    lbl_preview = ttk.Label(main_frame)
    lbl_preview.grid(row=7, column=0, sticky=tk.W, pady=(10,5))

    command_preview = tk.Text(
        main_frame,
        height=4,
        width=80,
        wrap=tk.WORD,
        background="#252526",
        foreground="#D4D4D4",
        state="disabled"
    )
    command_preview.grid(row=8, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
    command_preview.tag_configure("normal", foreground="#D4D4D4")
    command_preview.tag_configure("option", foreground="#C586C0")
    command_preview.tag_configure("path", foreground="#4FC1FF")

    lbl_output = ttk.Label(main_frame)
    lbl_output.grid(row=9, column=0, sticky=tk.W, pady=(10,5))

    output_frame = ttk.Frame(main_frame)
    output_frame.grid(row=10, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)

    output_scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL)
    output_text = tk.Text(
        output_frame,
        height=10,
        wrap=tk.WORD,
        yscrollcommand=output_scrollbar.set,
        background="#1E1E1E",
        foreground="#DCDCDC"
    )
    output_scrollbar.config(command=output_text.yview)
    output_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    output_text.tag_configure("normal", foreground="#DCDCDC")
    output_text.tag_configure("error", foreground="#F44747")
    output_text.tag_configure("success", foreground="#A5DF69")

    lbl_lang_switch = ttk.Label(main_frame)
    lbl_lang_switch.grid(row=11, column=0, sticky=tk.W, pady=(10,5), padx=(0,5))

    lang_switch_var = tk.StringVar()
    lang_switch_var.set("English" if default_lang == "en" else "Türkçe")

    combo_lang_switch = ttk.Combobox(
        main_frame,
        textvariable=lang_switch_var,
        values=["English", "Türkçe"],
        state="readonly",
        width=10
    )
    combo_lang_switch.grid(row=11, column=1, sticky=tk.W, pady=(10,5))
    combo_lang_switch.bind("<<ComboboxSelected>>", on_lang_change)

    run_button = ttk.Button(main_frame, command=run_or_abort)
    run_button.grid(row=11, column=2, sticky=tk.E, pady=(10,5))

    main_frame.columnconfigure(1, weight=1)

    model_var.trace_add("write", on_model_change)
    task_var.trace_add("write", on_task_change)
    video_path_var.trace_add("write", update_command_preview)
    srt_only_var.trace_add("write", update_command_preview)
    output_dir_var.trace_add("write", update_command_preview)
    source_language_var.trace_add("write", update_command_preview)
    target_language_var.trace_add("write", update_command_preview)

    set_language_texts(default_lang)

    on_model_change()
    on_task_change()
    update_command_preview()

    root.mainloop()

if __name__ == "__main__":
    main()
