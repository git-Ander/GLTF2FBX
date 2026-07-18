#!/usr/bin/env python3
"""GLTF to FBX Converter GUI - CustomTkinter with i18n (CN/EN toggle)."""

import subprocess, sys, os, threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinterdnd2
from tkinterdnd2 import TkinterDnD

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
    # ── decimate mode ──
    "mode_conv":  {"cn":"GLTF → FBX",   "en":"GLTF → FBX"},
    "mode_dec":   {"cn":"FBX 减面",     "en":"FBX Decimate"},
    "title_dec":  {"cn":"FBX 减面工具",  "en":"FBX Decimator"},
    "input_fb":   {"cn":"输入 (FBX):",   "en":"Input (FBX):"},
    "dec_lbl":    {"cn":"减面比例:",     "en":"Decimate ratio:"},
    "dec_hint":   {"cn":"保留原始面数的百分比", "en":"Keep % of original faces"},
    "decimate":   {"cn":"开始减面",      "en":"Decimate"},
    "decimating": {"cn":"减面中...",     "en":"Decimating..."},
    "ready_dec":  {"cn":"就绪 — 拖拽或浏览选择 FBX", "en":"Ready — drag-drop or browse FBX"},
    "done_dec":   {"cn":"减面完成",      "en":"Decimation done"},
    "failed_dec": {"cn":"减面失败",      "en":"Decimation failed"},
    "err_input_dec": {"cn":"请选择 FBX 输入文件", "en":"Please select an FBX input file"},
    "err_mismatch":{"cn":"文件格式不匹配！\n\n拖入的文件后缀: {}\n需要的后缀: {}", "en":"File format mismatch!\n\nDropped: {}\nRequired: {}"},
    "log_ratio":  {"cn":"  减面: {}%",  "en":"  Ratio:  {}%"},
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
        self.mode = "convert"
        self._build_ui()
        self._update_blender_status()
        self._setup_dnd()

    def tr(self, key, *args):
        s = T[key][self.lang]
        if args: s = s.format(*args)
        return s

    def _build_ui(self):
        r = self; t = self.tr; w = self._widgets
        r.title(t("title")); r.geometry("780x620"); r.minsize(660,540)
        pd = {"padx":16, "pady":(16,0)}

        # top row: lang toggle + blender path
        tr = ctk.CTkFrame(r, fg_color="transparent")
        tr.pack(fill="x", **pd)
        w["lang_btn"] = ctk.CTkButton(tr, text=t("lang_lbl"), width=40, height=32,
                                       fg_color="#2b2b3d", command=self._toggle_lang)
        w["lang_btn"].pack(side="left")
        w["blender_lbl"] = ctk.CTkLabel(tr, text=t("blender_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["blender_lbl"].pack(side="left", padx=(12,0))
        self.blender_var = ctk.StringVar(value=self.blender_path)
        self.blender_entry = ctk.CTkEntry(tr, textvariable=self.blender_var, height=32)
        self.blender_entry.pack(side="left", fill="x", expand=True, padx=(8,0))
        w["detect_btn"] = ctk.CTkButton(tr, text=t("detect"), width=48, height=32, fg_color=A2, command=self._detect_blender)
        w["detect_btn"].pack(side="left", padx=(8,0))
        w["blender_status"] = ctk.CTkLabel(tr, text="", font=ctk.CTkFont(size=10), text_color="#f9e2af")
        w["blender_status"].pack(side="left", padx=(8,0))

        # mode selector
        mr = ctk.CTkFrame(r, fg_color="transparent")
        mr.pack(fill="x", padx=16, pady=(8,0))
        self.mode_var = ctk.StringVar(value=t("mode_conv"))
        w["mode_seg"] = ctk.CTkSegmentedButton(mr, values=[t("mode_conv"), t("mode_dec")],
            variable=self.mode_var, command=self._on_mode_change, height=30)
        w["mode_seg"].pack(fill="x")

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

        # right - settings (Blender moved to top, so this is now mode-specific only)
        Rf = ctk.CTkFrame(cols); Rf.grid(row=0, column=1, sticky="nsew")
        w["settings_lbl"] = ctk.CTkLabel(Rf, text=t("settings"), font=ctk.CTkFont(size=13, weight="bold"))
        w["settings_lbl"].pack(anchor="w", padx=12, pady=(12,10))

        # convert-specific settings (packed directly into Rf)
        self._convert_widgets = []
        w["scale_lbl"] = ctk.CTkLabel(Rf, text=t("scale_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        w["scale_lbl"].pack(anchor="w", padx=12, pady=(14,0)); self._convert_widgets.append(w["scale_lbl"])
        sr = ctk.CTkFrame(Rf, fg_color="transparent"); sr.pack(fill="x", padx=12, pady=(4,0)); self._convert_widgets.append(sr)
        self.scale_slider = ctk.CTkSlider(sr, from_=0.01, to=1000, command=self._on_scale)
        self.scale_slider.pack(side="left", fill="x", expand=True)
        self.scale_var = ctk.StringVar(value="1.0")
        self.scale_entry = ctk.CTkEntry(sr, textvariable=self.scale_var, width=72, height=28)
        self.scale_entry.pack(side="left", padx=(10,0)); self.scale_slider.set(1.0)
        pr = ctk.CTkFrame(Rf, fg_color="transparent"); pr.pack(fill="x", padx=12, pady=(8,0)); self._convert_widgets.append(pr)
        for lb, v in [("1:1",1.0),("cm→m",100),("m→cm",0.01),("mm→m",1000)]:
            ctk.CTkButton(pr, text=lb, width=48, height=26, fg_color="#2b2b3d",
                          command=lambda v=v: self._set_scale(v)).pack(side="left", padx=(0,6))
        sp1 = ctk.CTkLabel(Rf, text=""); sp1.pack(); self._convert_widgets.append(sp1)
        self.bake_var = ctk.BooleanVar(value=True)
        w["bake_cb"] = ctk.CTkCheckBox(Rf, text=t("bake"), variable=self.bake_var, font=ctk.CTkFont(size=12))
        w["bake_cb"].pack(anchor="w", padx=12, pady=(14,0)); self._convert_widgets.append(w["bake_cb"])
        self.modifier_var = ctk.BooleanVar(value=True)
        w["mod_cb"] = ctk.CTkCheckBox(Rf, text=t("modifiers"), variable=self.modifier_var, font=ctk.CTkFont(size=12))
        w["mod_cb"].pack(anchor="w", padx=12, pady=(6,12)); self._convert_widgets.append(w["mod_cb"])

        # decimate-specific settings (created but not packed initially)
        self._decimate_widgets = []
        w["dec_lbl"] = ctk.CTkLabel(Rf, text=t("dec_lbl"), font=ctk.CTkFont(size=11), text_color="#aaa")
        self._decimate_widgets.append(w["dec_lbl"])
        dr = ctk.CTkFrame(Rf, fg_color="transparent")
        self._decimate_widgets.append(dr)
        self.dec_slider = ctk.CTkSlider(dr, from_=1, to=99, command=self._on_decimate)
        self.dec_slider.pack(side="left", fill="x", expand=True)
        self.dec_var = ctk.StringVar(value="50%")
        self.dec_entry = ctk.CTkEntry(dr, textvariable=self.dec_var, width=72, height=28)
        self.dec_entry.pack(side="left", padx=(10,0)); self.dec_slider.set(50)
        w["dec_hint"] = ctk.CTkLabel(Rf, text=t("dec_hint"), font=ctk.CTkFont(size=10), text_color="#666")
        self._decimate_widgets.append(w["dec_hint"])
        pr2 = ctk.CTkFrame(Rf, fg_color="transparent")
        self._decimate_widgets.append(pr2)
        for lb, v in [("10%",10),("25%",25),("50%",50),("75%",75),("90%",90)]:
            ctk.CTkButton(pr2, text=lb, width=48, height=26, fg_color="#2b2b3d",
                          command=lambda v=v: self._set_decimate(v)).pack(side="left", padx=(0,4))
        sp2 = ctk.CTkLabel(Rf, text="")
        self._decimate_widgets.append(sp2)

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
        for key, wk in [("files","files_lbl"),("input_lbl","input_lbl"),
                         ("output_lbl","output_lbl"),("browse","browse_btn"),
                         ("save","save_btn"),("settings","settings_lbl"),
                         ("blender_lbl","blender_lbl"),("detect","detect_btn"),
                         ("scale_lbl","scale_lbl"),("bake","bake_cb"),
                         ("modifiers","mod_cb"),("lang_lbl","lang_btn"),
                         ("dec_lbl","dec_lbl"),("dec_hint","dec_hint")]:
            w[wk].configure(text=t(key))
        # mode-dependent widgets
        self.title(t("title_dec") if self.mode == "decimate" else t("title"))
        w["input_lbl"].configure(text=t("input_fb") if self.mode == "decimate" else t("input_lbl"))
        self.btn.configure(text=t("decimate") if self.mode == "decimate" else t("convert"))
        self.status_var.set(t("ready_dec") if self.mode == "decimate" else t("ready"))
        w["mode_seg"].configure(values=[t("mode_conv"), t("mode_dec")])
        w["mode_seg"].set(t("mode_dec") if self.mode == "decimate" else t("mode_conv"))
        self._update_blender_status()

    def _setup_dnd(self):
        """Load tkdnd and register all widgets as drop targets."""
        try:
            import tkinter as tk
            import platform
            # DnDWrapper monkey-patches BaseWidget at import time,
            # but tk.Tk does NOT inherit from BaseWidget — copy methods manually
            bw = tk.BaseWidget
            for name in ("drop_target_register","dnd_bind","_dnd_bind","_substitute_dnd",
                         "_subst_format_dnd","_subst_format_str_dnd",
                         "drag_source_register","drop_target_unregister","drag_source_unregister"):
                if hasattr(bw, name) and not hasattr(tk.Tk, name):
                    setattr(tk.Tk, name, getattr(bw, name))
            # Load tkdnd library into the root window
            td = os.path.join(os.path.dirname(tkinterdnd2.__file__), "tkdnd")
            raw = os.environ.get("PROCESSOR_ARCHITECTURE", platform.machine())
            arch = {"AMD64":"x64","ARM64":"arm64","x86":"x86"}.get(raw, raw.lower())
            pp = os.path.join(td, "win-" + arch)
            if not os.path.isdir(pp):
                TkinterDnD.require(self)
            else:
                self.tk.call("lappend", "auto_path", pp)
                self.tk.call("package", "require", "tkdnd")
            # Register root + all children
            self._register_dnd_recursive(self)
        except Exception as e:
            print(f"DnD setup failed: {e}")

    def _register_dnd_recursive(self, widget):
        """Recursively register widget and all children as drop targets."""
        try:
            widget.drop_target_register("*")
            widget.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._register_dnd_recursive(child)

    def _on_scale(self, val): self.scale_var.set(f"{float(val):.2f}")
    def _set_scale(self, val): self.scale_slider.set(val); self.scale_var.set(f"{val:.2f}")

    def _on_decimate(self, val): self.dec_var.set(f"{int(val)}%")
    def _set_decimate(self, val): self.dec_slider.set(val); self.dec_var.set(f"{val}%")
    def _get_decimate_ratio(self):
        try: return float(self.dec_var.get().replace("%","").strip()) / 100.0
        except: return 0.5

    def _on_mode_change(self, value):
        self.mode = "decimate" if value == self.tr("mode_dec") else "convert"
        self._apply_mode()

    def _apply_mode(self):
        t = self.tr; w = self._widgets
        if self.mode == "convert":
            for widget in self._decimate_widgets:
                widget.pack_forget()
            # re-pack convert widgets (order matters)
            w["scale_lbl"].pack(anchor="w", padx=12, pady=(14,0))
            self._convert_widgets[1].pack(fill="x", padx=12, pady=(4,0))  # sr
            self._convert_widgets[2].pack(fill="x", padx=12, pady=(8,0))  # pr
            self._convert_widgets[3].pack()  # spacer
            w["bake_cb"].pack(anchor="w", padx=12, pady=(14,0))
            w["mod_cb"].pack(anchor="w", padx=12, pady=(6,12))
            self.title(t("title"))
            w["input_lbl"].configure(text=t("input_lbl"))
            self.btn.configure(text=t("convert"))
            self.status_var.set(t("ready"))
        else:
            for widget in self._convert_widgets:
                widget.pack_forget()
            # re-pack decimate widgets
            w["dec_lbl"].pack(anchor="w", padx=12, pady=(14,0))
            self._decimate_widgets[1].pack(fill="x", padx=12, pady=(4,0))  # dr
            w["dec_hint"].pack(anchor="w", padx=12, pady=(4,0))
            self._decimate_widgets[3].pack(fill="x", padx=12, pady=(8,0))  # pr2
            self._decimate_widgets[4].pack()  # spacer
            self.title(t("title_dec"))
            w["input_lbl"].configure(text=t("input_fb"))
            self.btn.configure(text=t("decimate"))
            self.status_var.set(t("ready_dec"))
        self.input_var.set(""); self.output_var.set("")
        self.input_path = ""; self.output_path = ""
        self._register_dnd_recursive(self)

    def _log(self, text):
        self.log.configure(state="normal"); self.log.insert("end", text+"\n")
        self.log.see("end"); self.log.configure(state="disabled")
    def _clear_log(self):
        self.log.configure(state="normal"); self.log.delete("1.0","end")
        self.log.configure(state="disabled")

    def _browse_input(self):
        if self.mode == "decimate":
            p = filedialog.askopenfilename(title="FBX", filetypes=[("FBX","*.fbx"),("All","*.*")])
            if p:
                self.input_var.set(p); self.input_path = p
                stem = Path(p).stem; o = str(Path(p).with_name(stem + "_low.fbx"))
                self.output_var.set(o); self.output_path = o
                self.status_var.set(self.tr("input_status", Path(p).name))
        else:
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
        exts = (".fbx",) if self.mode == "decimate" else (".gltf",".glb")
        for c in cand:
            if Path(c).suffix.lower() in exts:
                self.input_var.set(c); self.input_path = c
                if self.mode == "decimate":
                    stem = Path(c).stem
                    o = str(Path(c).with_name(stem + "_low.fbx"))
                else:
                    o = str(Path(c).with_suffix(".fbx"))
                self.output_var.set(o); self.output_path = o
                self.status_var.set(self.tr("input_status", Path(c).name))
                return
        if cand:
            messagebox.showwarning("",
                self.tr("err_mismatch", Path(cand[0]).suffix, "/".join(exts)))

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
        is_dec = self.mode == "decimate"
        if not inp: return messagebox.showerror("Error", t("err_input_dec") if is_dec else t("err_input"))
        if not os.path.isfile(inp): return messagebox.showerror("Error", t("err_file", inp))
        if not out: return messagebox.showerror("Error", t("err_output"))
        if not bl or not os.path.isfile(bl): return messagebox.showerror("Error", t("err_blender"))
        self.input_path = inp; self.output_path = out; self.blender_path = bl
        self.btn.configure(state="disabled", text=t("decimating") if is_dec else t("converting"))
        self.progress.configure(mode="indeterminate"); self.progress.start(); self._clear_log()
        header = "  FBX Decimate" if is_dec else "  GLTF -> FBX"
        self._log("="*46); self._log(header); self._log("="*46)
        self._log(t("log_input", inp)); self._log(t("log_output", out))
        if is_dec:
            self._log(t("log_ratio", self.dec_var.get().strip()))
        else:
            self._log(t("log_scale", self.scale_var.get()))
            self._log(t("log_bake", "Yes" if self.bake_var.get() else "No"))
        self._log("-"*46)
        threading.Thread(target=self._run_convert, daemon=True).start()

    def _run_convert(self):
        t = self.tr; is_dec = self.mode == "decimate"
        sp = Path(__file__).parent / "gltf2fbx.py"
        if not sp.exists(): sp = Path.cwd() / "gltf2fbx.py"
        cmd = [self.blender_path, "--background", "--python", str(sp.resolve()),
               "--", "--input", self.input_path, "--output", self.output_path]
        if is_dec:
            cmd.extend(["--mode", "decimate", "--ratio", str(self._get_decimate_ratio())])
        else:
            cmd.extend(["--scale", self.scale_var.get()])
            if not self.bake_var.get(): cmd.append("--no-bake")
            if not self.modifier_var.get(): cmd.append("--no-modifiers")
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
                done_key = "done_dec" if is_dec else "done"
                self.after(0, lambda: [self._log("-"*46), self._log(t("log_done")),
                    self._log(f"  Output: {self.output_path}"),
                    self._log(f"  Size:   {kb:.1f} KB"), self.status_var.set(t(done_key))])
                self.after(0, lambda: messagebox.showinfo("Done", t("done_msg", self.output_path, kb)))
            else:
                fail_key = "failed_dec" if is_dec else "failed"
                self.after(0, lambda: [self._log(t("log_fail", proc.returncode)),
                    self.status_var.set(t(fail_key))])
        except Exception as e:
            self.after(0, lambda: [self._log(t("log_err", e)), self.status_var.set(t("error"))])
        finally:
            self.after(0, self._convert_done)

    def _convert_done(self):
        is_dec = self.mode == "decimate"
        self.btn.configure(state="normal", text=self.tr("decimate") if is_dec else self.tr("convert"))
        self.progress.stop(); self.progress.configure(mode="determinate"); self.progress.set(0)

if __name__ == "__main__":
    App().mainloop()
