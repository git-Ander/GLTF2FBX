#!/usr/bin/env python3
"""GLTF to FBX Converter GUI - CustomTkinter with i18n (CN/EN toggle)."""

import subprocess, sys, os, threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")
A2 = "#144870"

# ═══ i18n dictionary ══════════════════════════════════════════════════════
T = {
    "title":      {"cn":"GLTF → FBX 转换器",     "en":"GLTF → FBX Converter"},
    "files":      {"cn":"📂 文件选择",           "en":"📂 File Selection"},
    "input_lbl":  {"cn":"输入 (GLB / GLTF):",     "en":"Input (GLB / GLTF):"},
    "output_lbl": {"cn":"输出 (FBX):",            "en":"Output (FBX):"},
    "browse":     {"cn":"浏览",                   "en":"Browse"},
    "save":       {"cn":"另存",                   "en":"Save"},
    "settings":   {"cn":"⚙ 设置",                "en":"⚙ Settings"},
    "blender_lbl":{"cn":"Blender 路径:",          "en":"Blender path:"},
    "detect":     {"cn":"检测",                   "en":"Detect"},
    "detected":   {"cn":"✓ 已检测到",             "en":"✓ Detected"},
    "not_found":  {"cn":"⚠ 未找到 — 请手动指定",  "en":"⚠ Not found - set path"},
    "not_found2": {"cn":"✗ 未找到",               "en":"✗ Not found"},
    "scale_lbl":  {"cn":"缩放因子:",              "en":"Scale factor:"},
    "bake":       {"cn":"烘焙动画",               "en":"Bake animations"},
    "modifiers":  {"cn":"应用修改器",             "en":"Apply modifiers"},
    "convert":    {"cn":"开始转换",               "en":"Convert"},
    "converting": {"cn":"转换中...",              "en":"Converting..."},
    "ready":      {"cn":"就绪 — 拖拽或浏览选择 GLB/GLTF", "en":"Ready — drag-drop or browse GLB/GLTF"},
    "done":       {"cn":"转换完成",               "en":"Done"},
    "failed":     {"cn":"转换失败",               "en":"Failed"},
    "error":      {"cn":"转换出错",               "en":"Error"},
    "input_status":{"cn":"输入: {}",              "en":"Input: {}"},
    "err_input":  {"cn":"请选择输入文件",          "en":"Please select an input file"},
    "err_file":   {"cn":"文件不存在:\n{}",         "en":"File not found:\n{}"},
    "err_output": {"cn":"请指定输出路径",          "en":"Please specify an output path"},
    "err_blender":{"cn":"Blender 路径无效",       "en":"Invalid Blender path"},
    "done_msg":   {"cn":"转换成功!\n\n{}\n{:.1f} KB","en":"Done!\n\n{}\n{:.1f} KB"},
    "log_input":  {"cn":"  输入: {}","en":"  Input:  {}"},
    "log_output": {"cn":"  输出: {}","en":"  Output: {}"},
    "log_scale":  {"cn":"  缩放: {}","en":"  Scale:  {}"},
    "log_bake":   {"cn":"  烘焙: {}","en":"  Bake:   {}"},
    "log_done":   {"cn":"✓ 转换成功!","en":"✓ Done!"},
    "log_fail":   {"cn":"✗ 转换失败 (退出码: {})","en":"✗ Failed (exit: {})"},
    "log_err":    {"cn":"✗ 错误: {}","en":"✗ Error: {}"},
    "lang_lbl":   {"cn":"🇨🇳","en":"🇺🇸"},
}
L = list(T.keys())

def find_blender():
    candidates = []
    if sys.platform == "win32":
        for ver in ["4.5","4.4","4.3","4.2","4.1","4.0","3.6","3.5"]:
            candidates.append(rf"C:\Program Files\Blender Foundation\Blender {ver}\blender.exe")
            candidates.append(rf"D:\Program Files\Blender Foundation\Blender {ver}\blender.exe")
        import glob
        for pat in [r"C:\Program Files\blender-*\blender.exe",
                     r"D:\Program Files\blender-*\blender.exe",
                     r"C:\Program Files\Blender\blender.exe",
                     r"D:\Program Files\Blender\blender.exe"]:
            candidates.extend(glob.glob(pat))
        candidates.append(r"C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe")
        w = __import__("shutil").which("blender.exe")
        if w: candidates.insert(0, w)
    elif sys.platform == "darwin":
        candidates = ["/Applications/Blender.app/Contents/MacOS/Blender"]
    else:
        candidates = ["/usr/bin/blender","/usr/local/bin/blender","/snap/bin/blender"]
    for c in candidates:
        if c and os.path.isfile(c): return c
    return None

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.lang = "cn"
        self._widgets = {}
        self.blender_path = find_blender() or ""
        self.input_path = ""; self.output_path = ""
        self._build_ui()
        self._update_blender_status()
        self._setup_dnd()

    def tr(self, key, *args):
        s = T[key][self.lang]
        if args: s = s.format(*args)
        return s

    def _build_ui(self):
        r = self; t = self.tr; w = self._widgets
        r.title(t("title")); r.geometry("780x540"); r.minsize(660,460)
        pd = {"padx":16, "pady":(16,0)}

        # title row with lang toggle
        tr = ctk.CTkFrame(r, fg_color="transparent")
        tr.pack(fill="x", **pd)
        ctk.CTkLabel(tr, text="GLTF -> FBX", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
        w["lang_btn"] = ctk.CTkButton(tr, text=t("lang_lbl"), width=40, height=28,
                                       fg_color="#2b2b3d", command=self._toggle_lang)
        w["lang_btn"].pack(side="right")

        cols = ctk.CTkFrame(r, fg_color="transparent")
        cols.pack(fill="x", padx=16, pady=(12,0))
        cols.grid_columnconfigure(0, weight=1); cols.grid_columnconfigure(1, weight=0)

        # left - files
        Lf = ctk.CTkFrame(cols); Lf.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        w["files_lbl"] = ctk.CTkLabel(Lf, text=t("files"), font=ctk.CTkFont(size=13, weight="bold"))
        w["files_lbl"].pack(anchor="w", padx=12, pady=(12,10))
        w["input_lbl"] = ctk.CTkLabel(Lf, text=t("input_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["input_lbl"].pack(anchor="w", padx=12)
        ir = ctk.CTkFrame(Lf, fg_color="transparent"); ir.pack(fill="x", padx=12, pady=(4,0))
        self.input_var = ctk.StringVar()
        self.input_entry = ctk.CTkEntry(ir, textvariable=self.input_var, height=32, state="readonly")
        self.input_entry.pack(side="left", fill="x", expand=True)
        w["browse_btn"] = ctk.CTkButton(ir, text=t("browse"), width=56, height=32, fg_color=A2, command=self._browse_input)
        w["browse_btn"].pack(side="left", padx=(8,0))
        w["output_lbl"] = ctk.CTkLabel(Lf, text=t("output_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["output_lbl"].pack(anchor="w", padx=12, pady=(12,0))
        o2 = ctk.CTkFrame(Lf, fg_color="transparent"); o2.pack(fill="x", padx=12, pady=(4,12))
        self.output_var = ctk.StringVar()
        self.output_entry = ctk.CTkEntry(o2, textvariable=self.output_var, height=32)
        self.output_entry.pack(side="left", fill="x", expand=True)
        w["save_btn"] = ctk.CTkButton(o2, text=t("save"), width=56, height=32, fg_color=A2, command=self._browse_output)
        w["save_btn"].pack(side="left", padx=(8,0))

        # right - settings
        Rf = ctk.CTkFrame(cols); Rf.grid(row=0, column=1, sticky="nsew")
        w["settings_lbl"] = ctk.CTkLabel(Rf, text=t("settings"), font=ctk.CTkFont(size=13, weight="bold"))
        w["settings_lbl"].pack(anchor="w", padx=12, pady=(12,10))
        w["blender_lbl"] = ctk.CTkLabel(Rf, text=t("blender_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["blender_lbl"].pack(anchor="w", padx=12)
        br = ctk.CTkFrame(Rf, fg_color="transparent"); br.pack(fill="x", padx=12, pady=(4,0))
        self.blender_var = ctk.StringVar(value=self.blender_path)
        self.blender_entry = ctk.CTkEntry(br, textvariable=self.blender_var, height=32)
        self.blender_entry.pack(side="left", fill="x", expand=True)
        w["detect_btn"] = ctk.CTkButton(br, text=t("detect"), width=48, height=32, fg_color=A2, command=self._detect_blender)
        w["detect_btn"].pack(side="left", padx=(8,0))
        w["blender_status"] = ctk.CTkLabel(Rf, text="", font=ctk.CTkFont(size=10), text_color="#f9e2af")
        w["blender_status"].pack(anchor="w", padx=12, pady=(2,0))

        w["scale_lbl"] = ctk.CTkLabel(Rf, text=t("scale_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["scale_lbl"].pack(anchor="w", padx=12, pady=(14,0))
        sr = ctk.CTkFrame(Rf, fg_color="transparent"); sr.pack(fill="x", padx=12, pady=(4,0))
        self.scale_slider = ctk.CTkSlider(sr, from_=0.01, to=1000, command=self._on_scale)
        self.scale_slider.pack(side="left", fill="x", expand=True)
        self.scale_var = ctk.StringVar(value="1.0")
        self.scale_entry = ctk.CTkEntry(sr, textvariable=self.scale_var, width=72, height=28)
        self.scale_entry.pack(side="left", padx=(10,0)); self.scale_slider.set(1.0)
        pr = ctk.CTkFrame(Rf, fg_color="transparent"); pr.pack(fill="x", padx=12, pady=(8,0))
        for lb, v in [("1:1",1.0),("cm→m",100),("m→cm",0.01),("mm→m",1000)]:
            ctk.CTkButton(pr, text=lb, width=48, height=26, fg_color="#2b2b3d",
                          command=lambda v=v: self._set_scale(v)).pack(side="left", padx=(0,6))
        ctk.CTkLabel(Rf, text="").pack()
        self.bake_var = ctk.BooleanVar(value=True)
        w["bake_cb"] = ctk.CTkCheckBox(Rf, text=t("bake"), variable=self.bake_var, font=ctk.CTkFont(size=12))
        w["bake_cb"].pack(anchor="w", padx=12, pady=(14,0))
        self.modifier_var = ctk.BooleanVar(value=True)
        w["mod_cb"] = ctk.CTkCheckBox(Rf, text=t("modifiers"), variable=self.modifier_var, font=ctk.CTkFont(size=12))
        w["mod_cb"].pack(anchor="w", padx=12, pady=(6,12))

        # action bar
        bar = ctk.CTkFrame(r, fg_color="transparent"); bar.pack(fill="x", padx=16, pady=(14,0))
        self.btn = ctk.CTkButton(bar, text=t("convert"), font=ctk.CTkFont(size=14, weight="bold"),
                                  height=40, width=140, command=self._start_convert)
        self.btn.pack(side="left")
        self.progress = ctk.CTkProgressBar(bar, width=260, height=10)
        self.progress.pack(side="left", padx=(16,0)); self.progress.set(0)

        # log
        lf = ctk.CTkFrame(r); lf.pack(fill="both", expand=True, padx=16, pady=(10,6))
        self.log = ctk.CTkTextbox(lf, font=ctk.CTkFont(size=11, family="Consolas"),
                                   fg_color="#0d0d15", border_width=0, wrap="word")
        self.log.pack(fill="both", expand=True, padx=1, pady=1)

        self.status_var = ctk.StringVar(value=t("ready"))
        ctk.CTkLabel(r, textvariable=self.status_var, font=ctk.CTkFont(size=11), text_color="#666").pack(
            fill="x", padx=18, pady=(6,10))

    def _toggle_lang(self):
        self.lang = "en" if self.lang == "cn" else "cn"
        t = self.tr; w = self._widgets
        self.title(t("title"))
        for key, wk in [("files","files_lbl"),("input_lbl","input_lbl"),
                         ("output_lbl","output_lbl"),("browse","browse_btn"),
                         ("save","save_btn"),("settings","settings_lbl"),
                         ("blender_lbl","blender_lbl"),("detect","detect_btn"),
                         ("scale_lbl","scale_lbl"),("bake","bake_cb"),
                         ("modifiers","mod_cb"),("lang_lbl","lang_btn")]:
            w[wk].configure(text=t(key))
        self.btn.configure(text=t("convert"))
        self.status_var.set(t("ready"))
        self._update_blender_status()

    def _setup_dnd(self):
        try:
            import tkinterdnd2, platform
            import tkinter as tk
            bw = tk.BaseWidget
            for name in ("drop_target_register","dnd_bind","_dnd_bind","_substitute_dnd",
                         "_subst_format_dnd","_subst_format_str_dnd",
                         "drag_source_register","drop_target_unregister","drag_source_unregister"):
                if hasattr(bw, name) and not hasattr(tk.Tk, name):
                    setattr(tk.Tk, name, getattr(bw, name))
            td = os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd")
            raw = os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())
            arch = {"AMD64":"x64","ARM64":"arm64","x86":"x86"}.get(raw, raw.lower())
            pp = os.path.join(td, "win-" + arch)
            if not os.path.isdir(pp):
                tkinterdnd2.TkinterDnD.require(self)
            else:
                self.tk.call("lappend", "auto_path", pp)
                self.tk.call("package", "require", "tkdnd")
            self.drop_target_register("*")
            self.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_scale(self, val): self.scale_var.set(f"{float(val):.2f}")
    def _set_scale(self, val): self.scale_slider.set(val); self.scale_var.set(f"{val:.2f}")

    def _log(self, text):
        self.log.configure(state="normal"); self.log.insert("end", text+"\n")
        self.log.see("end"); self.log.configure(state="disabled")
    def _clear_log(self):
        self.log.configure(state="normal"); self.log.delete("1.0","end")
        self.log.configure(state="disabled")

    def _browse_input(self):
        p = filedialog.askopenfilename(title="GLTF/GLB", filetypes=[("GLTF","*.gltf *.glb"),("All","*.*")])
        if p:
            self.input_var.set(p); self.input_path = p
            o = str(Path(p).with_suffix(".fbx")); self.output_var.set(o); self.output_path = o
            self.status_var.set(self.tr("input_status", Path(p).name))
    def _browse_output(self):
        p = filedialog.asksaveasfilename(title="FBX", defaultextension=".fbx",
                                          filetypes=[("FBX","*.fbx"),("All","*.*")])
        if p: self.output_var.set(p); self.output_path = p

    def _on_drop(self, event):
        raw = event.data; cand = []
        if os.path.isfile(raw): cand.append(raw)
        s = raw.strip("{}").strip()
        if s and os.path.isfile(s): cand.append(s)
        for part in raw.replace("\\","/").split():
            p = part.strip("{}").strip()
            if p and os.path.isfile(p): cand.append(p)
        for c in cand:
            if Path(c).suffix.lower() in (".gltf",".glb"):
                self.input_var.set(c); self.input_path = c
                o = str(Path(c).with_suffix(".fbx")); self.output_var.set(o); self.output_path = o
                self.status_var.set(self.tr("input_status", Path(c).name))
                return

    def _detect_blender(self):
        p = find_blender(); t = self.tr
        if p:
            self.blender_var.set(p); self.blender_path = p
            self._widgets["blender_status"].configure(text=t("detected"), text_color="#a6e3a1")
        else:
            self._widgets["blender_status"].configure(text=t("not_found2"), text_color="#f38ba8")

    def _update_blender_status(self):
        t = self.tr
        if self.blender_path and os.path.isfile(self.blender_path):
            self._widgets["blender_status"].configure(text=t("detected"), text_color="#a6e3a1")
        else:
            self._widgets["blender_status"].configure(text=t("not_found"), text_color="#f9e2af")

    def _start_convert(self):
        t = self.tr; inp = self.input_var.get().strip()
        out = self.output_var.get().strip(); bl = self.blender_var.get().strip()
        if not inp: return messagebox.showerror("Error", t("err_input"))
        if not os.path.isfile(inp): return messagebox.showerror("Error", t("err_file", inp))
        if not out: return messagebox.showerror("Error", t("err_output"))
        if not bl or not os.path.isfile(bl): return messagebox.showerror("Error", t("err_blender"))
        self.input_path = inp; self.output_path = out; self.blender_path = bl
        self.btn.configure(state="disabled", text=t("converting"))
        self.progress.configure(mode="indeterminate"); self.progress.start(); self._clear_log()
        self._log("="*46); self._log("  GLTF -> FBX"); self._log("="*46)
        self._log(t("log_input", inp)); self._log(t("log_output", out))
        self._log(t("log_scale", self.scale_var.get()))
        self._log(t("log_bake", "Yes" if self.bake_var.get() else "No"))
        self._log("-"*46)
        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self):
        t = self.tr; scale = self.scale_var.get(); bake = self.bake_var.get()
        mod = self.modifier_var.get()
        sp = Path(__file__).parent / "gltf2fbx.py"
        if not sp.exists(): sp = Path.cwd() / "gltf2fbx.py"
        cmd = [self.blender_path, "--background", "--python", str(sp.resolve()),
               "--", "--input", self.input_path, "--output", self.output_path, "--scale", scale]
        if not bake: cmd.append("--no-bake")
        if not mod: cmd.append("--no-modifiers")
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, encoding="utf-8", errors="replace", bufsize=1,
                                     creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0)
            for line in proc.stdout:
                line = line.rstrip()
                if line: self.after(0, lambda l=line: self._log(l))
            proc.wait()
            if proc.returncode == 0 and os.path.isfile(self.output_path):
                kb = os.path.getsize(self.output_path) / 1024
                self.after(0, lambda: [self._log("-"*46), self._log(t("log_done")),
                    self._log(f"  Output: {self.output_path}"),
                    self._log(f"  Size:   {kb:.1f} KB"), self.status_var.set(t("done"))])
                self.after(0, lambda: messagebox.showinfo("Done", t("done_msg", self.output_path, kb)))
            else:
                self.after(0, lambda: [self._log(t("log_fail", proc.returncode)),
                    self.status_var.set(t("failed"))])
        except Exception as e:
            self.after(0, lambda: [self._log(t("log_err", e)), self.status_var.set(t("error"))])
        finally:
            self.after(0, self._convert_done)

    def _convert_done(self):
        self.btn.configure(state="normal", text=self.tr("convert"))
        self.progress.stop(); self.progress.configure(mode="determinate"); self.progress.set(0)

if __name__ == "__main__":
    App().mainloop()
