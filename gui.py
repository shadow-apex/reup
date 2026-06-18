import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import json
import re
import uuid
import time
import subprocess
import tempfile
import asyncio
import urllib.request
import urllib.error
import ssl
import shutil
from pathlib import Path

# ─── CONFIG ─────────────────────────────────────────────────────────────────
CONFIG_FILE = "reup_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ─── COLORS ─────────────────────────────────────────────────────────────────
BG, PANEL, CARD = "#0f0f13", "#1a1a22", "#22222e"
ACCENT, ACCENT2 = "#7c5cfc", "#a78bfa"
GREEN, RED, YELLOW = "#22c55e", "#ef4444", "#f59e0b"
TEXT, SUBTEXT, BORDER = "#e2e8f0", "#94a3b8", "#2e2e3e"
FONT_SM = ("Segoe UI", 8)
FONT_BASE = ("Segoe UI", 9)
FONT_MED = ("Segoe UI", 10, "bold")
FONT_LG = ("Segoe UI", 12, "bold")

LANGS = ["zh", "vi", "en", "ja", "ko", "fr", "de", "th", "id", "ms"]
LANG_NAMES = {"zh":"Trung","vi":"Việt","en":"Anh","ja":"Nhật","ko":"Hàn",
              "fr":"Pháp","de":"Đức","th":"Thái","id":"Indo","ms":"Mã Lai"}

AI_PRESETS = {
    "DeepSeek":     {"url": "https://api.deepseek.com",          "model": "deepseek-chat"},
    "OpenAI":       {"url": "https://api.openai.com/v1",         "model": "gpt-4o-mini"},
    "Groq (free)":  {"url": "https://api.groq.com/openai/v1",     "model": "llama-3.3-70b-versatile"},
    "Together AI":  {"url": "https://api.together.xyz/v1",        "model": "mistralai/Mixtral-8x22B-Instruct-v0.1"},
    "Gemini (proxy)":{"url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"},
    "Fireworks":    {"url": "https://api.fireworks.ai/inference/v1","model": "accounts/fireworks/models/llama-v3p1-405b-instruct"},
    "OpenRouter":   {"url": "https://openrouter.ai/api/v1",       "model": "openai/gpt-4o-mini"},
}

# ─── TOOLTIP ────────────────────────────────────────────────────────────────
class ToolTip:
    def __init__(self, w, text):
        self.w=w; self.text=text; self.tw=None
        w.bind("<Enter>",self.show); w.bind("<Leave>",self.hide)
    def show(self, e=None):
        x=self.w.winfo_rootx()+20; y=self.w.winfo_rooty()+self.w.winfo_height()+4
        self.tw=tw=tk.Toplevel(self.w); tw.wm_overrideredirect(True); tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw,text=self.text,bg="#2d2d3f",fg=TEXT,font=FONT_SM,padx=6,pady=3).pack()
    def hide(self, e=None):
        if self.tw: self.tw.destroy(); self.tw=None

# ─── HELPERS ────────────────────────────────────────────────────────────────
def btn(p,t,c,color=ACCENT,w=None,sm=False):
    f=FONT_SM if sm else FONT_BASE; w=w or (8 if sm else 10)
    return tk.Button(p,text=t,command=c,bg=color,fg="#fff",font=f,
                     relief="flat",bd=0,padx=6,pady=(3 if sm else 5),
                     cursor="hand2",activebackground=ACCENT2,activeforeground="#fff",width=w)

def http(url,method="GET",headers=None,data=None,timeout=30):
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req=urllib.request.Request(url,method=method)
    if headers:
        for k,v in headers.items(): req.add_header(k,v)
    if data is not None:
        req.data=json.dumps(data).encode("utf-8"); req.add_header("Content-Type","application/json; charset=utf-8")
    try:
        with urllib.request.urlopen(req,timeout=timeout,context=ctx) as r:
            return r.status,json.loads(r.read().decode("utf-8")),None
    except urllib.error.HTTPError as e:
        try: return e.code,json.loads(e.read().decode("utf-8")),None
        except: return e.code,None,f"HTTP {e.code}"
    except urllib.error.URLError as e: return 0,None,f"Không thể kết nối: {e.reason}"
    except Exception as e: return 0,None,str(e)

def run_ffmpeg(args,timeout=3600):
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error",*args]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    if r.returncode!=0:
        raise RuntimeError(f"ffmpeg lỗi {r.returncode}: {r.stderr[-500:]}")
    return r

class ReupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎬 Video Reup Tool"); self.configure(bg=BG); self.resizable(False,False)
        c=load_config()
        self.ai_provider=tk.StringVar(value=c.get("ai_provider","DeepSeek"))
        self.api_key=tk.StringVar(value=c.get("api_key",""))
        self.api_base=tk.StringVar(value=c.get("api_base",AI_PRESETS["DeepSeek"]["url"]))
        self.api_model=tk.StringVar(value=c.get("api_model",AI_PRESETS["DeepSeek"]["model"]))
        self.src_lang=tk.StringVar(value=c.get("src_lang","zh"))
        self.tgt_lang=tk.StringVar(value=c.get("tgt_lang","vi"))
        self.vol_orig=tk.IntVar(value=c.get("vol_orig",15))
        self.dl_link=tk.StringVar()
        self.out_dir=tk.StringVar(value=c.get("out_dir",os.path.expanduser("~/Videos")))
        self.out_name=tk.StringVar(value=c.get("out_name","{title}_{n}"))
        self.subtitle=tk.StringVar(value=c.get("subtitle",""))  # optional manual subtitle
        self.files=[]; self.running=False; self._cancel=False
        self.prog=tk.DoubleVar(value=0); self.status=tk.StringVar(value="Sẵn sàng")
        self.stage=tk.StringVar(value=""); self._build_ui(); self.geometry("+100+50")

    def _build_ui(self):
        hdr=tk.Frame(self,bg=PANEL,height=38); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr,text="🎬 VIDEO REUP TOOL",bg=PANEL,fg=ACCENT2,font=FONT_LG).pack(side="left",padx=12)
        btn(hdr,"💾 Lưu",self._save_cfg,"#334155",7,True).pack(side="right",padx=8,pady=6)

        cv=tk.Canvas(self,bg=BG,width=540,height=560,highlightthickness=0)
        sc=tk.Scrollbar(self,orient="vertical",command=cv.yview); cv.configure(yscrollcommand=sc.set)
        sc.pack(side="right",fill="y"); cv.pack(side="left",fill="both",expand=True)
        self.main=tk.Frame(cv,bg=BG,width=520)
        w=cv.create_window((0,0),window=self.main,anchor="nw")
        self.main.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(w,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        self._build_sections()

        sb=tk.Frame(self,bg=PANEL); sb.pack(fill="x",side="bottom")
        # row 1: progress bar + stage label
        r1=tk.Frame(sb,bg=PANEL); r1.pack(fill="x",pady=(6,0))
        bar=ttk.Progressbar(r1,variable=self.prog,maximum=100,length=310)
        bar.pack(side="left",padx=(8,2))
        s=ttk.Style(); s.theme_use("clam"); s.configure("TProgressbar",troughcolor=CARD,background=ACCENT,thickness=6)
        tk.Label(r1,textvariable=self.stage,bg=PANEL,fg=ACCENT2,font=("Consolas",8)).pack(side="left",padx=2)
        # row 2: status + buttons
        r2=tk.Frame(sb,bg=PANEL); r2.pack(fill="x")
        tk.Label(r2,textvariable=self.status,bg=PANEL,fg=SUBTEXT,font=FONT_SM).pack(side="left",padx=8)
        self.run_btn=btn(r2,"▶ BẮT ĐẦU",self._toggle_run,GREEN,10)
        self.run_btn.pack(side="right",padx=8,pady=6)
        btn(r2,"🗑 Log",self._clear_log,"#334155",7,True).pack(side="right",pady=6)

    def _build_sections(self):
        p=self.main
        # ─── 1. AI ──────────────────────────────────────────────────────
        b1=self._sec(p,"🤖 AI DỊCH THUẬT")
        r1=tk.Frame(b1,bg=CARD); r1.pack(fill="x",pady=1)
        tk.Label(r1,text="Cung cấp",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        ttk.Combobox(r1,textvariable=self.ai_provider,values=list(AI_PRESETS.keys()),
                     state="readonly",font=FONT_BASE,width=22).pack(side="left")
        def _pre(*_):
            p=AI_PRESETS.get(self.ai_provider.get())
            if p: self.api_base.set(p["url"]); self.api_model.set(p["model"])
        self.ai_provider.trace_add("write",_pre)

        r2=tk.Frame(b1,bg=CARD); r2.pack(fill="x",pady=1)
        tk.Label(r2,text="API Key",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        ek=tk.Entry(r2,textvariable=self.api_key,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                    relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                    highlightcolor=ACCENT,width=32,show="*")
        ek.pack(side="left",padx=(0,4))
        self._kv=False
        def _tk(): self._kv=not self._kv; ek.config(show="" if self._kv else "*")
        tk.Button(r2,text="👁",command=_tk,bg="#334155",fg="#fff",
                  font=FONT_SM,relief="flat",bd=0,padx=4,pady=1,cursor="hand2",width=3).pack(side="left")

        r3=tk.Frame(b1,bg=CARD); r3.pack(fill="x",pady=1)
        tk.Label(r3,text="Base URL",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(r3,textvariable=self.api_base,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=32).pack(side="left",padx=(0,4))
        r4=tk.Frame(b1,bg=CARD); r4.pack(fill="x",pady=1)
        tk.Label(r4,text="Model",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(r4,textvariable=self.api_model,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=32).pack(side="left",padx=(0,4))

        # Test AI
        rt=tk.Frame(b1,bg=CARD); rt.pack(fill="x",pady=(4,1))
        tk.Label(rt,text="Dịch thử",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        self._ti=tk.StringVar(value="Xin chào, đây là video hôm nay của tôi.")
        tk.Entry(rt,textvariable=self._ti,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=16).pack(side="left",padx=(0,4))
        btn(rt,"▶ Dịch AI",self._test_ai,ACCENT,8,True).pack(side="left")
        self._tr=tk.Label(b1,text="",bg=CARD,fg="#4ade80",font=("Consolas",8),wraplength=480)
        # hide initially, show on first test
        self._tr.pack_forget(); self._tr_shown=False

        # ─── 2. VIDEO ───────────────────────────────────────────────────
        b2=self._sec(p,"📁 NGUỒN VIDEO")
        lk=tk.Frame(b2,bg=CARD); lk.pack(fill="x",pady=1)
        tk.Label(lk,text="Link tải về",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(lk,textvariable=self.dl_link,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=24).pack(side="left",padx=(0,4))
        btn(lk,"⬇ Tải",self._dl,ACCENT,6,True).pack(side="left")
        btn(lk,"📋 Dán",lambda: self.dl_link.set(self.clipboard_get()),"#334155",4,True).pack(side="left",padx=2)
        tk.Label(b2,text="yt-dlp: YouTube · Douyin · TikTok · Facebook · Instagram …",
                 bg=CARD,fg=SUBTEXT,font=("Segoe UI",7,"italic")).pack(anchor="w",padx=1)
        fr=tk.Frame(b2,bg=CARD); fr.pack(fill="x",pady=2)
        btn(fr,"📂 Chọn file",self._pf,ACCENT,10,True).pack(side="left")
        btn(fr,"📁 Thư mục",self._pdir,"#334155",9,True).pack(side="left",padx=3)
        btn(fr,"✕ Xóa hết",self._clr,"#334155",8,True).pack(side="left")
        flf=tk.Frame(b2,bg="#13131c",highlightthickness=1,highlightbackground=BORDER); flf.pack(fill="x",pady=2)
        self.fl=tk.Listbox(flf,bg="#13131c",fg=TEXT,selectbackground=ACCENT,font=FONT_SM,
                           relief="flat",bd=0,height=3,activestyle="none")
        self.fl.pack(side="left",fill="both",expand=True)
        sb2=tk.Scrollbar(flf,orient="vertical",command=self.fl.yview); sb2.pack(side="right",fill="y")
        self.fl.config(yscrollcommand=sb2.set)
        self.fc=tk.Label(b2,text="0 file",bg=CARD,fg=SUBTEXT,font=FONT_SM); self.fc.pack(anchor="w")

        # ─── 3. TUỲ CHỈNH ──────────────────────────────────────────────
        b3=self._sec(p,"🎛 TUỲ CHỈNH")
        row_l=tk.Frame(b3,bg=CARD); row_l.pack(fill="x",pady=2)
        tk.Label(row_l,text="Ngôn ngữ",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        ttk.Combobox(row_l,textvariable=self.src_lang,values=LANGS,state="readonly",
                     font=FONT_BASE,width=7).pack(side="left")
        tk.Label(row_l,text="→",bg=CARD,fg=SUBTEXT,font=FONT_BASE).pack(side="left",padx=3)
        ttk.Combobox(row_l,textvariable=self.tgt_lang,values=LANGS,state="readonly",
                     font=FONT_BASE,width=7).pack(side="left")
        self._ll=tk.Label(row_l,text="",bg=CARD,fg=SUBTEXT,font=FONT_SM); self._ll.pack(side="left",padx=6)
        def _ul(*_): self._ll.config(text=f"{LANG_NAMES.get(self.src_lang.get(),'?')} → {LANG_NAMES.get(self.tgt_lang.get(),'?')}")
        self.src_lang.trace_add("write",_ul); self.tgt_lang.trace_add("write",_ul); _ul()

        row_v=tk.Frame(b3,bg=CARD); row_v.pack(fill="x",pady=1)
        tk.Label(row_v,text="Âm gốc",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Scale(row_v,variable=self.vol_orig,from_=0,to=100,orient="horizontal",
                 bg=CARD,fg=TEXT,troughcolor="#13131c",activebackground=ACCENT,
                 highlightthickness=0,bd=0,showvalue=False,sliderlength=14,length=180).pack(side="left")
        vl=tk.Label(row_v,textvariable=self.vol_orig,bg="#13131c",fg=TEXT,font=FONT_SM,width=3)
        vl.pack(side="left",padx=2); tk.Label(row_v,text="%",bg=CARD,fg=SUBTEXT,font=FONT_SM).pack(side="left")
        ToolTip(row_v,"Âm gốc giữ lại. 0% = tắt tiếng gốc, chỉ còn giọng TTS")

        # ─── 4. NỘI DUNG THUYẾT MINH ────────────────────────────────────
        b3b=self._sec(p,"📝 NỘI DUNG THUYẾT MINH")
        tk.Label(b3b,text="Nhập nội dung gốc (bỏ qua nếu muốn AI tự dịch từ audio)",bg=CARD,fg=SUBTEXT,font=FONT_SM).pack(anchor="w")
        self._script=scrolledtext.ScrolledText(b3b,height=3,bg="#0a0a12",fg=TEXT,insertbackground=TEXT,
                                                relief="flat",font=("Consolas",8),bd=0,wrap="word")
        self._script.pack(fill="x",pady=(2,0))
        self._script.insert("1.0","")
        self._script.config(state="normal")
        ToolTip(self._script,"Để trống = dùng TTS mặc định (giọng đọc tiếng Việt)\nNhập text = dịch nội dung này sang ngôn ngữ đích rồi TTS")

        # ─── 5. OUTPUT ──────────────────────────────────────────────────
        b4=self._sec(p,"💾 XUẤT RA")
        ro1=tk.Frame(b4,bg=CARD); ro1.pack(fill="x",pady=1)
        tk.Label(ro1,text="Thư mục",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(ro1,textvariable=self.out_dir,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=22).pack(side="left",padx=(0,4))
        btn(ro1,"📁",lambda: self.out_dir.set(filedialog.askdirectory()),"#334155",3,True).pack(side="left")
        ro2=tk.Frame(b4,bg=CARD); ro2.pack(fill="x",pady=1)
        tk.Label(ro2,text="Tên file",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(ro2,textvariable=self.out_name,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=22).pack(side="left")
        tk.Label(b4,text="{n}=số thứ tự  {title}=tên gốc",bg=CARD,fg=SUBTEXT,font=FONT_SM).pack(anchor="w")

        # ─── 6. LOG ─────────────────────────────────────────────────────
        b5=self._sec(p,"📋 LOG",pad=(4,6))
        self.log=scrolledtext.ScrolledText(b5,height=5,bg="#0a0a12",fg="#4ade80",
                                            insertbackground=TEXT,relief="flat",
                                            font=("Consolas",8),bd=0,wrap="word")
        self.log.pack(fill="x"); self.log.config(state="disabled")
        self._log("✅ Sẵn sàng. Chọn AI + nhập Key → chọn video → BẮT ĐẦU.")

    def _sec(self,p,t,pad=(4,2)):
        f=tk.Frame(p,bg=CARD,bd=0,highlightthickness=1,highlightbackground=BORDER)
        f.pack(fill="x",padx=8,pady=pad)
        tk.Frame(f,bg=BORDER,height=1).pack(fill="x")
        t2=tk.Frame(f,bg=CARD); t2.pack(fill="x",padx=6,pady=(3,1))
        tk.Label(t2,text=t,bg=CARD,fg=ACCENT2,font=FONT_MED).pack(side="left")
        b=tk.Frame(f,bg=CARD); b.pack(fill="x",padx=6,pady=(0,5))
        return b

    # ─── FILE / LINK ─────────────────────────────────────────────────────
    def _pf(self):
        fs=filedialog.askopenfilenames(title="Chọn video",filetypes=[("Video","*.mp4 *.mkv *.avi *.mov *.webm *.flv")])
        for f in fs:
            if f not in self.files: self.files.append(f); self.fl.insert("end",os.path.basename(f))
        self._uc()
    def _pdir(self):
        d=filedialog.askdirectory()
        if d:
            ex={".mp4",".mkv",".avi",".mov",".webm",".flv"}; a=0
            for fn in sorted(os.listdir(d)):
                if os.path.splitext(fn)[1].lower() in ex:
                    fp=os.path.join(d,fn)
                    if fp not in self.files: self.files.append(fp); self.fl.insert("end",fn); a+=1
            self._uc(); self._log(f"📁 Thêm {a} video.")
    def _clr(self): self.files.clear(); self.fl.delete(0,"end"); self._uc()
    def _uc(self): self.fc.config(text=f"{len(self.files)} file")

    def _dl(self):
        link=self.dl_link.get().strip()
        if not link: return messagebox.showwarning("","Nhập link video!")
        self._log(f"⬇ Đang tải: {link[:60]}…"); self.status.set("Đang tải…")
        def _do():
            out=self.out_dir.get().strip() or os.path.expanduser("~/Videos")
            os.makedirs(out,exist_ok=True)
            try:
                r=subprocess.run(["yt-dlp","--no-playlist","-o",f"{out}/%(title)s.%(ext)s",link],
                                 capture_output=True,text=True,timeout=600)
                if r.returncode!=0:
                    self.after(0,lambda: self._log(f"✕ Lỗi: {r.stderr[-400:]}"))
                    self.after(0,lambda: self.status.set("Lỗi tải")); return
                for fn in os.listdir(out):
                    if fn.endswith((".mp4",".mkv",".webm")):
                        fp=os.path.join(out,fn)
                        if fp not in self.files:
                            self.files.append(fp)
                            self.after(0,lambda f=fn: self.fl.insert("end",f))
                self.after(0,self._uc); self.after(0,lambda: self._log(f"✅ Tải xong → {out}"))
                self.after(0,lambda: self.status.set("Sẵn sàng"))
            except FileNotFoundError: self.after(0,lambda: self._log("✕ Cài yt-dlp: pip install yt-dlp"))
            except subprocess.TimeoutExpired: self.after(0,lambda: self._log("✕ Quá giờ (10 phút)"))
        threading.Thread(target=_do,daemon=True).start()

    # ─── TEST AI ─────────────────────────────────────────────────────────
    def _test_ai(self):
        txt=self._ti.get().strip()
        if not txt: return
        key=self.api_key.get().strip()
        if not key: return messagebox.showwarning("","Nhập API Key!")
        self._tr.config(text="⏳ Đang dịch…",fg=YELLOW)
        self._tr.pack(fill="x",padx=14,pady=(0,2)); self._tr_shown=True
        def _do():
            base=self.api_base.get().strip().rstrip("/")
            model=self.api_model.get().strip()
            s,body,err=http(f"{base}/chat/completions","POST",
                            {"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                            {"model":model,"messages":[
                                {"role":"system","content":f"Dịch {self.src_lang.get()} → {self.tgt_lang.get()}. Chỉ ra kết quả, không thêm gì khác."},
                                {"role":"user","content":txt}],"temperature":0.3},60)
            def _up():
                if err: self._tr.config(text=f"✕ {err}",fg=RED)
                elif body and body.get("choices"):
                    self._tr.config(text=f"✅ {body['choices'][0]['message']['content'].strip()}",fg="#4ade80")
                else: self._tr.config(text=f"✕ {str(body)[:200]}",fg=RED)
            self.after(0,_up)
        threading.Thread(target=_do,daemon=True).start()

    # ─── RUN ─────────────────────────────────────────────────────────────
    def _toggle_run(self):
        if self.running: self._stop()
        else: self._start()

    def _start(self):
        if not self.files: return messagebox.showwarning("","Chọn ít nhất 1 video!")
        self.running=True; self._cancel=False; self.run_btn.config(text="⏹ DỪNG",bg=RED)
        self.status.set("Đang xử lý…"); self._log(f"🚀 Xử lý {len(self.files)} video…")
        threading.Thread(target=self._process,daemon=True).start()

    def _stop(self):
        self._cancel=True; self.running=False
        self.run_btn.config(text="▶ BẮT ĐẦU",bg=GREEN); self.status.set("Đã dừng"); self._log("⏹ Đã dừng.")

    def _set_stage(self,text,subpct):
        """Update stage label + progress bar (subpct 0-100 within current video)."""
        total=len(self.files)
        vid=getattr(self,'_vid',1) or 1
        overall=((vid-1)+subpct/100)/total*100 if total>0 else subpct
        self.prog.set(overall); self.stage.set(text)

    def _clear_stage(self):
        self.stage.set("")

    def _out_path(self,inp,idx):
        title=os.path.splitext(os.path.basename(inp))[0]
        t=self.out_name.get().strip() or "{title}_{n}"
        n=t.replace("{title}",title).replace("{n}",str(idx))
        n=re.sub(r'[<>:"/\\|?*]',"_",n)
        return os.path.join(self.out_dir.get().strip() or os.path.expanduser("~/Videos"),f"{n}.mp4")

    def _call_ai(self,system_prompt,user_text):
        """Call AI API. Returns translated text string."""
        base=self.api_base.get().strip().rstrip("/")
        key=self.api_key.get().strip()
        model=self.api_model.get().strip()
        s,body,err=http(f"{base}/chat/completions","POST",
                        {"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                        {"model":model,"messages":[
                            {"role":"system","content":system_prompt},
                            {"role":"user","content":user_text}],"temperature":0.3},120)
        if err: raise RuntimeError(f"AI lỗi: {err}")
        if not body or not body.get("choices"): raise RuntimeError(f"AI phản hồi lạ: {str(body)[:200]}")
        return body["choices"][0]["message"]["content"].strip()

    async def _tts(self,text,out_mp3):
        """Generate TTS via edge-tts."""
        import edge_tts
        voice = "vi-VN-HoaiMyNeural"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_mp3))

    def _process_one(self,fp,idx):
        """Process a single video: generate TTS voiceover, mix with ffmpeg.
        Returns (success_bool, message)."""
        name=os.path.basename(fp)
        try:
            self._set_stage("🤖 Dịch 0%",0)
            # ── Step 1: Get text for TTS ──
            script_text = self._script.get("1.0","end-1c").strip()
            if script_text:
                self._log(f"   🤖 Đang dịch nội dung…")
                lang_src=self.src_lang.get() or "zh"
                lang_tgt=self.tgt_lang.get() or "vi"
                system_prompt = f"Bạn là dịch giả video. Dịch đoạn văn {lang_src} sau sang {lang_tgt} tự nhiên, chỉ ra kết quả."
                self._set_stage("🤖 Dịch 0%",1)
                tts_text = self._call_ai(system_prompt, script_text)
                self._set_stage("🤖 Dịch 100%",40)
                self._log(f"   ✅ Đã dịch ({len(tts_text)} ký tự)")
            else:
                tts_text = f"Đây là video số {idx}. Cảm ơn bạn đã xem."

            # ── Step 2: Generate TTS ──
            self._set_stage("🔊 TTS 0%",40)
            self._log(f"   🔊 Đang tạo giọng đọc ({len(tts_text)} ký tự)…")
            with tempfile.TemporaryDirectory() as td:
                tdir=Path(td)
                mp3=tdir/"voice.mp3"

                loop=asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._tts(tts_text, mp3))
                finally:
                    loop.close()

                self._set_stage("🔊 TTS 100%",70)
                if not mp3.exists():
                    raise RuntimeError("TTS không tạo được file")

                # ── Step 3: Mix with ffmpeg ──
                self._set_stage("🎬 Ghép audio 0%",70)
                self._log(f"   🎬 Đang ghép audio…")
                out=self._out_path(fp,idx)
                os.makedirs(os.path.dirname(out) or ".",exist_ok=True)

                vol=self.vol_orig.get()/100.0  # 0.0 – 1.0
                run_ffmpeg([
                    "-i",fp,
                    "-i",str(mp3),
                    "-filter_complex",
                    f"[0:a:0]volume={vol}[orig];[1:a:0]volume=1.0[tts];[orig][tts]amix=inputs=2:duration=first[outa]",
                    "-map","0:v:0","-map","[outa]",
                    "-c:v","libx264","-crf","23","-c:a","aac","-shortest",out,
                ])
                self._set_stage("🎬 Ghép 100%",100)
                return True, out

        except Exception as e:
            self._set_stage("✕ Lỗi",100)
            return False, str(e)

    def _process(self):
        total=len(self.files); ok=0; fail=0
        for i,fp in enumerate(self.files):
            if self._cancel: break
            self._vid=i+1  # 1-based, used by _set_stage
            name=os.path.basename(fp)
            self._log(f"[{i+1}/{total}] 🎬 {name}"); self.status.set(f"File {i+1}/{total}")

            self._set_stage("⏳ Đang khởi tạo…",0)
            success,result=self._process_one(fp,i+1)
            if success:
                self._log(f"   ✅ Xong → {os.path.basename(result)}"); ok+=1
            else:
                self._log(f"   ✕ LỖI: {result}"); fail+=1

        if self._cancel: self._log("⏹ Đã dừng.")
        self._clear_stage()
        if not self._cancel: self.prog.set(100); self._log(f"🎉 Xong: ✅{ok} ❌{fail} / {total}")
        self.status.set(f"✅{ok} ❌{fail}")
        self.running=False; self.run_btn.config(text="▶ BẮT ĐẦU",bg=GREEN)

    def _clear_log(self):
        self.log.config(state="normal"); self.log.delete(1.0,"end"); self.log.config(state="disabled")

    def _log(self,msg):
        def _do():
            self.log.config(state="normal"); self.log.insert("end",msg+"\n"); self.log.see("end")
            self.log.config(state="disabled")
        self.after(0,_do)

    def _save_cfg(self):
        save_config({"ai_provider":self.ai_provider.get(),"api_key":self.api_key.get(),
                     "api_base":self.api_base.get(),"api_model":self.api_model.get(),
                     "src_lang":self.src_lang.get(),"tgt_lang":self.tgt_lang.get(),
                     "vol_orig":self.vol_orig.get(),"out_dir":self.out_dir.get(),
                     "out_name":self.out_name.get()})
        self._log("💾 Đã lưu cấu hình!"); self.status.set("Đã lưu")

if __name__=="__main__":
    ReupApp().mainloop()
