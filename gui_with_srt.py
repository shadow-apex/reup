import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import json
import re
import sys
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

# ─── CONFIG ───────────────────────────────────────────────────────────
CONFIG_FILE = "reup_config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

# ─── COLORS ───────────────────────────────────────────────────────────
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

# ─── TOOLTIP ──────────────────────────────────────────────────────────
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

# ─── HELPERS ──────────────────────────────────────────────────────────
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

# ─── SRT UTILITIES ────────────────────────────────────────────────────
def parse_srt(srt_path):
    """Parse SRT file to dict: {index: (start, end, text)}"""
    if not os.path.exists(srt_path):
        return {}
    subs = {}
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    blocks = content.strip().split('\n\n')
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0])
            ts = lines[1]
            text = '\n'.join(lines[2:]).strip()
            if '-->' in ts:
                times = ts.split('-->')
                start = _parse_ts(times[0].strip())
                end = _parse_ts(times[1].strip())
                subs[idx] = (start, end, text)
        except:
            pass
    return subs

def _parse_ts(ts_str):
    """Parse HH:MM:SS,mmm to seconds"""
    try:
        parts = ts_str.replace(',', '.').split(':')
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except:
        return 0.0

def _format_ts(seconds):
    """Format seconds to HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ─── SRT SEGMENT TRANSLATION (keeps ORIGINAL timestamps) ──────────────
def build_translation_prompt(segments):
    """segments: list of dict {start,end,text} -> numbered text for the AI."""
    lines = []
    for i, seg in enumerate(segments, 1):
        text = " ".join(seg["text"].strip().splitlines())
        lines.append(f"{i}. {text}")
    return "\n".join(lines)

def parse_translation_response(response, expected_count):
    """Parse a numbered '1. ...\\n2. ...' response back into {index: text}."""
    result = {}
    pattern = re.compile(r'^\s*(\d+)[.\):]\s*(.*)$')
    current_idx = None
    for raw_line in response.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            current_idx = int(m.group(1))
            if 1 <= current_idx <= expected_count:
                result[current_idx] = m.group(2).strip()
            else:
                current_idx = None
        elif current_idx is not None and current_idx in result:
            result[current_idx] += " " + line
    return result

def make_translated_segments(segments, translations):
    """Combine ORIGINAL timing with translated text -> new list of dict.
    Falls back to the original-language text for any line the model
    skipped, so the segment count/timing never drifts."""
    out = []
    for i, seg in enumerate(segments, 1):
        translated = translations.get(i, "").strip()
        out.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": translated or seg["text"],
        })
    return out

class ReupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🎬 Video Reup Tool (with SRT)"); self.configure(bg=BG); self.resizable(False,False)
        c=load_config()
        self.ai_provider=tk.StringVar(value=c.get("ai_provider","DeepSeek"))
        self.api_key=tk.StringVar(value=c.get("api_key",""))
        self.api_base=tk.StringVar(value=c.get("api_base",AI_PRESETS["DeepSeek"]["url"]))
        self.api_model=tk.StringVar(value=c.get("api_model",AI_PRESETS["DeepSeek"]["model"]))
        self.src_lang=tk.StringVar(value=c.get("src_lang","zh"))
        self.tgt_lang=tk.StringVar(value=c.get("tgt_lang","vi"))
        self.vol_orig=tk.IntVar(value=c.get("vol_orig",15))
        self.dl_link=tk.StringVar()
        self.cookie_file=tk.StringVar(value=c.get("cookie_file",""))
        self.out_dir=tk.StringVar(value=c.get("out_dir",os.path.expanduser("~/Videos")))
        self.out_name=tk.StringVar(value=c.get("out_name","{title}_{n}"))
        self.subtitle=tk.StringVar(value=c.get("subtitle",""))
        self.files=[]; self.running=False; self._cancel=False
        self.prog=tk.DoubleVar(value=0); self.status=tk.StringVar(value="Sẵn sàng")
        self.stage=tk.StringVar(value="")
        self._current_srt_zh = None  # Track current SRT file
        self._srt_segments = None      # list[{start,end,text}] gốc, timestamp thật từ file SRT
        self._srt_segments_vi = None   # list[{start,end,text}] đã dịch, CÙNG timestamp với bản gốc
        self._build_ui(); self.geometry("+100+50")

    def _build_ui(self):
        hdr=tk.Frame(self,bg=PANEL,height=38); hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr,text="🎬 VIDEO REUP TOOL (with SRT)",bg=PANEL,fg=ACCENT2,font=FONT_LG).pack(side="left",padx=12)
        btn(hdr,"💾 Lưu",self._save_cfg,"#334155",7,True).pack(side="right",padx=8,pady=6)

        cv=tk.Canvas(self,bg=BG,width=540,height=620,highlightthickness=0)
        sc=tk.Scrollbar(self,orient="vertical",command=cv.yview); cv.configure(yscrollcommand=sc.set)
        sc.pack(side="right",fill="y"); cv.pack(side="left",fill="both",expand=True)
        self.main=tk.Frame(cv,bg=BG,width=520)
        w=cv.create_window((0,0),window=self.main,anchor="nw")
        self.main.bind("<Configure>",lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>",lambda e: cv.itemconfig(w,width=e.width))
        cv.bind_all("<MouseWheel>",lambda e: cv.yview_scroll(int(-1*(e.delta/120)),"units"))
        self._build_sections()

        sb=tk.Frame(self,bg=PANEL); sb.pack(fill="x",side="bottom")
        r1=tk.Frame(sb,bg=PANEL); r1.pack(fill="x",pady=(6,0))
        bar=ttk.Progressbar(r1,variable=self.prog,maximum=100,length=310)
        bar.pack(side="left",padx=(8,2))
        s=ttk.Style(); s.theme_use("clam"); s.configure("TProgressbar",troughcolor=CARD,background=ACCENT,thickness=6)
        tk.Label(r1,textvariable=self.stage,bg=PANEL,fg=ACCENT2,font=("Consolas",8)).pack(side="left",padx=2)
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

        rt=tk.Frame(b1,bg=CARD); rt.pack(fill="x",pady=(4,1))
        tk.Label(rt,text="Dịch thử",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        self._ti=tk.StringVar(value="Xin chào, đây là video hôm nay của tôi.")
        tk.Entry(rt,textvariable=self._ti,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=16).pack(side="left",padx=(0,4))
        btn(rt,"▶ Dịch AI",self._test_ai,ACCENT,8,True).pack(side="left")
        self._tr=tk.Label(b1,text="",bg=CARD,fg="#4ade80",font=("Consolas",8),wraplength=480)
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

        ck=tk.Frame(b2,bg=CARD); ck.pack(fill="x",pady=1)
        tk.Label(ck,text="Cookies",bg=CARD,fg=SUBTEXT,font=FONT_SM,width=12,anchor="w").pack(side="left")
        tk.Entry(ck,textvariable=self.cookie_file,bg="#13131c",fg=TEXT,insertbackground=TEXT,
                 relief="flat",font=FONT_BASE,bd=0,highlightthickness=1,highlightbackground=BORDER,
                 highlightcolor=ACCENT,width=24).pack(side="left",padx=(0,4))
        btn(ck,"📁",lambda: self.cookie_file.set(filedialog.askopenfilename(filetypes=[("Cookies","*.txt *.cookies"),("All","*.*")])) ,"#334155",3,True).pack(side="left")
        ToolTip(ck,"Nhập file cookies cho Douyin nếu video cần đăng nhập / yêu cầu cookies.")
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

        # ─── 4. NỘI DUNG THUYẾT MINH + SRT ────────────────────────────
        b3b=self._sec(p,"📝 NỘI DUNG THUYẾT MINH + SRT")
        tk.Label(b3b,text="Script gốc hoặc nhập nội dung để dịch:",bg=CARD,fg=SUBTEXT,font=FONT_SM).pack(anchor="w")
        
        # SRT buttons — 2 luồng song song:
        #  (1) Nhập SRT gốc -> Dịch SRT bằng API
        #  (2) Nhập thẳng SRT đã dịch sẵn (tự dịch thủ công ở ngoài) -> bỏ qua API
        srt_btn_frame=tk.Frame(b3b,bg=CARD); srt_btn_frame.pack(fill="x",pady=(2,2))
        btn(srt_btn_frame,"📥 Nhập SRT gốc",self._import_srt,ACCENT,12,True).pack(side="left",padx=2)
        btn(srt_btn_frame,"� Tạo SRT gốc từ video",self._create_srt_from_video,"#8b5cf6",18,True).pack(side="left",padx=2)
        btn(srt_btn_frame,"�🌐 Dịch SRT (API)",self._translate_srt,"#0891b2",12,True).pack(side="left",padx=2)
        btn(srt_btn_frame,"💾 Xuất SRT",self._export_srt,"#334155",10,True).pack(side="left",padx=2)
        btn(srt_btn_frame,"🔄 Xóa SRT",self._clear_srt,"#ef4444",8,True).pack(side="left")

        srt_btn_frame2=tk.Frame(b3b,bg=CARD); srt_btn_frame2.pack(fill="x",pady=(0,2))
        btn(srt_btn_frame2,"📥 Nhập SRT ĐÃ DỊCH (bỏ qua API)",self._import_translated_srt,"#16a34a",26,True).pack(side="left",padx=2)
        ToolTip(srt_btn_frame2,"Dùng khi bạn đã tự dịch SRT ở ngoài (ChatGPT, DeepSeek web...)\nvà chỉ muốn chương trình TTS + ghép video, không gọi API dịch nữa.")
        
        self._script=scrolledtext.ScrolledText(b3b,height=4,bg="#0a0a12",fg=TEXT,insertbackground=TEXT,
                                                relief="flat",font=("Consolas",8),bd=0,wrap="word")
        self._script.pack(fill="x",pady=(2,0))
        self._script.insert("1.0","")
        self._script.config(state="normal")
        self._srt_label=tk.Label(b3b,text="SRT không được tải",bg=CARD,fg="#ef4444",font=FONT_SM)
        self._srt_label.pack(anchor="w",pady=(2,0))
        ToolTip(self._script,"Để trống = dùng TTS mặc định\nNhập text tay = dịch cả khối, TTS 1 track liên tục\nNhập SRT + bấm '🌐 Dịch SRT' = dịch từng dòng, TTS đồng bộ đúng timestamp gốc")

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
        self._log("✅ Sẵn sàng. Chọn AI + nhập Key → chọn video → BẮT ĐẦU.\n📝 Quy trình SRT: 📥 Nhập SRT → 🌐 Dịch SRT → BẮT ĐẦU (TTS sẽ tự đồng bộ đúng timestamp gốc).")

    def _sec(self,p,t,pad=(4,2)):
        f=tk.Frame(p,bg=CARD,bd=0,highlightthickness=1,highlightbackground=BORDER)
        f.pack(fill="x",padx=8,pady=pad)
        tk.Frame(f,bg=BORDER,height=1).pack(fill="x")
        t2=tk.Frame(f,bg=CARD); t2.pack(fill="x",padx=6,pady=(3,1))
        tk.Label(t2,text=t,bg=CARD,fg=ACCENT2,font=FONT_MED).pack(side="left")
        b=tk.Frame(f,bg=CARD); b.pack(fill="x",padx=6,pady=(0,5))
        return b

    # ─── SRT MANAGEMENT ──────────────────────────────────────────────
    def _import_translated_srt(self):
        """Nhập thẳng 1 file SRT ĐÃ ĐƯỢC DỊCH SẴN (ví dụ bạn tự dán SRT gốc
        cho ChatGPT/DeepSeek dịch thủ công rồi lưu lại). Timestamp lấy
        nguyên từ chính file này — KHÔNG gọi API dịch nữa, đi thẳng tới
        bước TTS đồng bộ + ghép video.
        """
        file = filedialog.askopenfilename(filetypes=[("SRT", "*.srt"), ("All", "*.*")])
        if not file:
            return
        try:
            subs = parse_srt(file)
            if not subs:
                messagebox.showerror("Lỗi", "File SRT rỗng hoặc sai định dạng.")
                return
            ordered_idx = sorted(subs.keys())
            segments = sorted([
                {"start": subs[i][0], "end": subs[i][1], "text": subs[i][2]}
                for i in ordered_idx
            ], key=lambda seg: seg["start"])

            # Coi đây là bản ĐÃ DỊCH — dùng thẳng, không qua API
            self._srt_segments = segments
            self._srt_segments_vi = segments
            self._current_srt_zh = file

            full_text = " ".join(seg["text"] for seg in segments)
            self._script.config(state="normal")
            self._script.delete("1.0", "end")
            self._script.insert("1.0", full_text)

            self._srt_label.config(
                text=f"✅ SRT ĐÃ DỊCH (thủ công): {os.path.basename(file)} "
                     f"({len(segments)} dòng, sẵn sàng TTS — KHÔNG cần API)",
                fg="#4ade80",
            )
            self._log(f"📥 Đã nhập SRT ĐÃ DỊCH: {os.path.basename(file)} ({len(segments)} dòng).")
            self._log("   ✅ Bỏ qua bước gọi API dịch — có thể bấm BẮT ĐẦU để TTS + ghép video ngay.")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc SRT: {str(e)}")

    def _import_srt(self):
        """Import SRT file: keep the REAL timestamps (self._srt_segments),
        only put the plain text into the script box as a preview/edit area."""
        file = filedialog.askopenfilename(filetypes=[("SRT", "*.srt"), ("All", "*.*")])
        if not file:
            return

        try:
            subs = parse_srt(file)
            ordered_idx = sorted(subs.keys())
            # ✅ Giữ nguyên start/end thật của từng dòng — KHÔNG nối thành 1 chuỗi
            self._srt_segments = sorted([
                {"start": subs[i][0], "end": subs[i][1], "text": subs[i][2]}
                for i in ordered_idx
            ], key=lambda seg: seg["start"])
            self._srt_segments_vi = None  # bản dịch cũ (nếu có) không còn hợp lệ

            full_text = " ".join(seg["text"] for seg in self._srt_segments)
            self._script.config(state="normal")
            self._script.delete("1.0", "end")
            self._script.insert("1.0", full_text)

            self._current_srt_zh = file
            self._srt_label.config(
                text=f"✅ SRT: {os.path.basename(file)} ({len(self._srt_segments)} dòng, chưa dịch)",
                fg="#4ade80",
            )
            self._log(f"📥 Đã nhập SRT: {os.path.basename(file)} ({len(self._srt_segments)} subtitle, giữ nguyên timestamp)")
            self._log("   ℹ️ Bấm '🌐 Dịch SRT' để dịch từng dòng (giữ đúng thời gian gốc).")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc SRT: {str(e)}")

    def _create_srt_from_video(self):
        """Create an original SRT file from the selected video using ASR.
        Requires faster-whisper installed via: pip install -e '.[asr]'.
        """
        if not self.files:
            messagebox.showwarning("", "Chọn ít nhất 1 video trước.")
            return

        video_path = self.files[0]
        if not os.path.exists(video_path):
            messagebox.showerror("Lỗi", f"File không tồn tại: {video_path}")
            return

        self._srt_label.config(text="⏳ Đang tạo SRT gốc từ video…", fg=YELLOW)
        self._log(f"🎙 Đang tạo SRT gốc từ: {os.path.basename(video_path)}")

        def _do():
            try:
                # ✅ FIX: dò nhiều vị trí khả dĩ thay vì chỉ 1 đường dẫn cố
                # định. Trước đây nếu cấu trúc thư mục không đúng y hệt
                # "<script>/worker/src/video_worker/..." thì import fail
                # và người dùng chỉ thấy lỗi ImportError chung chung.
                here = Path(__file__).resolve().parent
                candidates = [
                    here / "worker" / "src",
                    here.parent / "worker" / "src",
                    here,             # video_worker/ nằm cùng cấp với GUI
                    here.parent,
                ]
                found = False
                for cand in candidates:
                    if (cand / "video_worker").is_dir() and str(cand) not in sys.path:
                        sys.path.insert(0, str(cand))
                        found = True
                        break

                try:
                    from video_worker.pipeline import _asr_faster_whisper
                    from video_worker.settings import Settings
                except ImportError as e:
                    searched = "\n".join(f"  - {c}" for c in candidates)
                    raise RuntimeError(
                        "Không tìm thấy package 'video_worker' (cần cho ASR tạo SRT gốc).\n"
                        f"Đã dò các thư mục:\n{searched}\n"
                        "Hãy đặt gui_with_srt.py cùng gốc với thư mục worker/src/video_worker, "
                        f"hoặc cài đặt package đó. Chi tiết: {e}"
                    ) from e

                # ✅ FIX: trước đây thư mục làm việc tạm (chứa file audio.wav
                # trung gian) bị bắt buộc tạo BÊN TRONG thư mục Output do
                # người dùng chọn, và không bao giờ được xoá sau khi dùng
                # xong (rác tồn đọng). Nếu thư mục Output chưa tồn tại, sai
                # định dạng đường dẫn, hoặc bị hạn chế quyền (ví dụ nằm
                # trong OneDrive) thì việc tạo temp dir ở đó sẽ báo lỗi
                # WinError 3/5. Giờ dùng thư mục tạm hệ thống (luôn ghi
                # được, tự dọn sạch) — hoàn toàn tách biệt với Output.
                with tempfile.TemporaryDirectory(prefix="srt_gen_") as td:
                    wav_path = Path(td) / "audio.wav"
                    run_ffmpeg([
                        "-y", "-i", video_path,
                        "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(wav_path)
                    ], timeout=3600)

                    settings = Settings(
                        whisper_model="tiny",
                        whisper_device="cpu",
                        whisper_compute_type="int8",
                    )
                    _, segments = _asr_faster_whisper(wav_path, settings)
                    srt_segments = [
                        {"start": getattr(seg, "start", 0), "end": getattr(seg, "end", 0), "text": getattr(seg, "text", "").strip()}
                        for seg in segments
                        if getattr(seg, "text", "").strip()
                    ]

                self._srt_segments = srt_segments
                self._srt_segments_vi = None
                full_text = " ".join(seg["text"] for seg in srt_segments)
                self._script.config(state="normal")
                self._script.delete("1.0", "end")
                self._script.insert("1.0", full_text)

                # ✅ FIX: nếu thư mục Output người dùng chọn/nhập bị lỗi
                # (không tạo được, không có quyền ghi — ví dụ do OneDrive,
                # ổ đĩa không tồn tại, đường dẫn sai…), rơi về thư mục cùng
                # cấp với video nguồn thay vì crash toàn bộ tiến trình.
                out_dir = Path(self.out_dir.get().strip() or os.path.expanduser("~/Videos"))
                try:
                    out_dir.mkdir(parents=True, exist_ok=True)
                except OSError as dir_err:
                    fallback_dir = Path(video_path).resolve().parent
                    self._log(
                        f"   ⚠️ Không dùng được thư mục Output '{out_dir}' ({dir_err}). "
                        f"Chuyển sang lưu cùng thư mục video: {fallback_dir}"
                    )
                    out_dir = fallback_dir
                out_srt = out_dir / f"{Path(video_path).stem}_zh.srt"
                with open(out_srt, "w", encoding="utf-8") as f:
                    for i, seg in enumerate(srt_segments, 1):
                        f.write(f"{i}\n{_format_ts(seg['start'])} --> {_format_ts(seg['end'])}\n{seg['text']}\n\n")

                self._current_srt_zh = str(out_srt)
                self._srt_label.config(
                    text=f"✅ SRT gốc: {os.path.basename(out_srt)} ({len(srt_segments)} dòng)",
                    fg="#4ade80",
                )
                self._log(f"✅ Đã tạo SRT gốc: {os.path.basename(out_srt)}")
                self._log(f"   📍 Lưu tại: {out_srt}")
            except Exception as e:
                # ✅ FIX: chuyển exception thành chuỗi NGAY trong khối except,
                # vì biến 'e' sẽ bị Python tự xoá khi khối except kết thúc.
                # self.after() chạy lambda này SAU đó (khi mainloop rảnh),
                # lúc đó 'e' không còn tồn tại nữa -> NameError.
                err_msg = str(e)
                def _err(err=err_msg):
                    self._srt_label.config(text=f"✕ Không tạo được SRT gốc: {err}", fg=RED)
                    self._log(f"✕ Không tạo được SRT gốc: {err}")
                self.after(0, _err)

        threading.Thread(target=_do, daemon=True).start()

    def _translate_srt_now(self, segments):
        """Dịch đồng bộ (blocking) danh sách SRT segments, giữ nguyên
        start/end gốc. Dùng chung bởi nút '🌐 Dịch SRT' (qua thread riêng)
        VÀ bởi bước xử lý video (_process_one) khi phát hiện người dùng
        đã có SRT gốc nhưng quên bấm dịch trước khi bấm BẮT ĐẦU — nhờ vậy
        SRT dịch + audio đồng bộ vẫn luôn được xuất ra thay vì âm thầm bị
        bỏ qua.
        """
        src = self.src_lang.get() or "zh"
        tgt = self.tgt_lang.get() or "vi"
        numbered = build_translation_prompt(segments)
        system_prompt = (
            "Bạn là dịch giả phụ đề chuyên nghiệp. "
            f"Dịch các dòng phụ đề {src} được đánh số sau sang {tgt} tự nhiên, "
            "phù hợp để lồng tiếng. "
            "BẮT BUỘC trả về ĐÚNG SỐ DÒNG như đầu vào, mỗi dòng bắt đầu bằng "
            "số thứ tự gốc rồi dấu chấm (vd '1. ...'). "
            "KHÔNG gộp, KHÔNG tách, KHÔNG thêm/bớt dòng, không thêm lời giải thích."
        )
        raw = self._call_ai(system_prompt, numbered)
        translations = parse_translation_response(raw, len(segments))

        missing = [i for i in range(1, len(segments) + 1)
                   if not translations.get(i, "").strip()]
        for i in missing:
            seg = segments[i - 1]
            if not seg["text"].strip():
                continue
            try:
                translations[i] = self._call_ai(
                    f"Dịch {src} → {tgt} tự nhiên. Chỉ ra kết quả, không thêm gì khác.",
                    seg["text"],
                )
            except Exception:
                pass

        translated = make_translated_segments(segments, translations)
        if missing:
            self._log(f"   ⚠️ {len(missing)} dòng phải dịch lẻ do model bỏ sót ở lần gọi gộp.")
        return translated

    def _try_use_manual_script_translation(self):
        """If user entered line-by-line translated text in the script box,
        build translated SRT segments from it and keep original timestamps.
        """
        if not self._srt_segments or self._srt_segments_vi is not None:
            return False
        script_text = self._script.get("1.0", "end-1c").strip()
        if not script_text:
            return False
        lines = [line.strip() for line in re.split(r'\r?\n', script_text) if line.strip()]
        if len(lines) != len(self._srt_segments):
            return False
        if all(line == seg["text"] for line, seg in zip(lines, self._srt_segments)):
            return False
        self._srt_segments_vi = [
            {"start": seg["start"], "end": seg["end"], "text": lines[i]}
            for i, seg in enumerate(self._srt_segments)
        ]
        self._log("   ✅ Đã dùng nội dung script để tạo SRT dịch thủ công.")
        return True

    def _translate_srt(self):
        """Translate every SRT line in one AI call, keeping each line's
        ORIGINAL start/end. This is what makes the exported SRT and the
        synced TTS audio actually line up with the source timing."""
        if not self._srt_segments:
            messagebox.showwarning("", "Chưa nhập SRT! Bấm '📥 Nhập SRT' trước.")
            return
        key = self.api_key.get().strip()
        if not key:
            return messagebox.showwarning("", "Nhập API Key!")

        self._srt_label.config(text="⏳ Đang dịch SRT…", fg=YELLOW)
        self._log(f"🌐 Đang dịch {len(self._srt_segments)} dòng SRT…")

        def _do():
            try:
                translated = self._translate_srt_now(self._srt_segments)

                def _up():
                    self._srt_segments_vi = translated
                    full_vi = " ".join(seg["text"] for seg in translated)
                    self._script.config(state="normal")
                    self._script.delete("1.0", "end")
                    self._script.insert("1.0", full_vi)
                    self._srt_label.config(
                        text=f"✅ SRT: {os.path.basename(self._current_srt_zh)} "
                             f"({len(translated)} dòng, ĐÃ DỊCH — timestamp giữ nguyên)",
                        fg="#4ade80",
                    )
                    self._log(f"✅ Đã dịch xong {len(translated)} dòng SRT (giữ nguyên timestamp).")
                self.after(0, _up)
            except Exception as e:
                err_msg = str(e)
                def _err(err=err_msg):
                    self._srt_label.config(text=f"✕ Lỗi dịch: {err}", fg=RED)
                    self._log(f"✕ Lỗi dịch SRT: {err}")
                self.after(0, _err)

        threading.Thread(target=_do, daemon=True).start()

    def _export_srt(self):
        """Export SRT.

        - Nếu đã dịch SRT (self._srt_segments_vi): xuất với timestamp THẬT
          lấy từ file SRT gốc — đây là bản phụ đề dịch đúng nghĩa.
        - Nếu mới nhập nhưng chưa dịch: xuất lại bản gốc với timestamp thật.
        - Nếu không có SRT nào được nhập (chỉ gõ tay trong ô script): dùng
          ước lượng thời lượng theo số ký tự như trước — CHỈ mang tính tham
          khảo, không đảm bảo khớp với audio TTS thực tế.
        """
        segments = self._srt_segments_vi or self._srt_segments
        file = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SRT", "*.srt"), ("Text", "*.txt")]
        )
        if not file:
            return

        if segments:
            with open(file, 'w', encoding='utf-8') as f:
                for i, seg in enumerate(segments, 1):
                    f.write(f"{i}\n{_format_ts(seg['start'])} --> {_format_ts(seg['end'])}\n{seg['text']}\n\n")
            label = "bản dịch" if self._srt_segments_vi else "bản gốc"
            messagebox.showinfo("", f"✅ Đã xuất SRT ({label}, timestamp thật): {file}")
            self._log(f"💾 Xuất SRT ({label}, timestamp thật): {os.path.basename(file)}")
            return

        text = self._script.get("1.0", "end-1c").strip()
        if not text:
            messagebox.showwarning("", "Script trống! Nhập nội dung trước.")
            return
        messagebox.showwarning(
            "",
            "Chưa có SRT gốc nên KHÔNG có timestamp thật.\n"
            "SRT xuất ra dưới đây chỉ là ước lượng theo độ dài câu,\n"
            "có thể lệch so với audio lồng tiếng thực tế."
        )
        sentences = re.split(r'(?<=[.。!！?？])', text)
        with open(file, 'w', encoding='utf-8') as f:
            time_pos = 0
            for i, sent in enumerate(sentences, 1):
                sent = sent.strip()
                if not sent:
                    continue
                duration = len(sent) * 0.15
                end = time_pos + duration
                f.write(f"{i}\n{_format_ts(time_pos)} --> {_format_ts(end)}\n{sent}\n\n")
                time_pos = end
        self._log(f"💾 Xuất SRT (ước lượng, KHÔNG có timestamp thật): {os.path.basename(file)}")

    def _clear_srt(self):
        """Clear SRT and reset"""
        self._current_srt_zh = None
        self._srt_segments = None
        self._srt_segments_vi = None
        self._srt_label.config(text="SRT không được tải", fg="#ef4444")
        self._log("🔄 Đã xóa SRT")

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
                cmd=["yt-dlp","--no-playlist","-o",f"{out}/%(title)s.%(ext)s",link]
                cookie_file=self.cookie_file.get().strip()
                if cookie_file:
                    cmd.insert(1, cookie_file)
                    cmd.insert(1, "--cookies")
                    self._log(f"   ℹ️ Dùng cookies: {cookie_file}")
                r=subprocess.run(cmd,
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

    # ─── RUN ──────────────────────────────────────────────────────────
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

    async def _tts(self, text, out_mp3, max_retries=3, per_call_timeout=25):
        """Gọi edge-tts với retry + backoff + TIMEOUT.

        ✅ FIX: bản gốc gọi 1 lần duy nhất, không retry. edge-tts thỉnh
        thoảng trả lỗi thoáng qua "No audio was received..." do bị
        Microsoft giới hạn tốc độ (throttle) khi gọi liên tục hàng trăm
        dòng — chỉ cần thử lại là thường qua. Giờ thử lại tối đa
        `max_retries` lần với thời gian chờ tăng dần trước khi thực sự
        báo lỗi.

        ✅ FIX 2 (quan trọng): trước đây `communicate.save()` KHÔNG có
        timeout. Nếu máy chủ Microsoft "treo" giữa chừng (không trả lỗi,
        không trả dữ liệu — hay gặp khi gọi liên tục hàng trăm dòng),
        coroutine sẽ chờ VÔ HẠN và app đứng hình luôn, không bao giờ tới
        lượt retry tiếp theo. Giờ mỗi lần gọi bị giới hạn
        `per_call_timeout` giây; hết giờ thì coi như 1 lần thử thất bại
        và retry/bỏ qua như bình thường, thay vì treo cả chương trình.
        """
        import edge_tts
        voice = "vi-VN-HoaiMyNeural"
        last_exc = None
        for attempt in range(max_retries):
            try:
                communicate = edge_tts.Communicate(text, voice)
                await asyncio.wait_for(
                    communicate.save(str(out_mp3)), timeout=per_call_timeout
                )
                if out_mp3.exists() and out_mp3.stat().st_size > 0:
                    return
                raise RuntimeError("edge-tts trả về file rỗng")
            except Exception as e:
                last_exc = e
                if attempt + 1 < max_retries:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"edge-tts thất bại sau {max_retries} lần thử: {last_exc}")

    async def _tts_segments_synced(self, segments, out_audio, tdir):
        """Sinh TTS cho từng dòng SRT rồi đặt đúng vào vị trí `start` gốc
        trên timeline bằng ffmpeg `adelay`, sau đó mix tất cả lại thành 1
        track duy nhất. Nhờ vậy audio lồng tiếng luôn khớp với timestamp
        của phụ đề đã dịch, thay vì 1 track liên tục dễ bị trôi so với
        video khi tổng thời lượng TTS khác tổng thời lượng thoại gốc.
        Yêu cầu ffmpeg >= 4.4 (tham số `all=1` của adelay).
        """
        usable = [seg for seg in segments if seg["text"].strip()]
        if not usable:
            raise RuntimeError("Không có dòng nào để đọc (text rỗng).")

        chunk_paths = []
        failed = []
        total_lines = len(usable)
        for i, seg in enumerate(usable):
            tmp = tdir / f"seg_{i:04d}.mp3"
            try:
                # ✅ FIX: trước đây nếu 1 trong hàng trăm dòng bị lỗi
                # edge-tts, toàn bộ tiến trình dừng ngay (mất hết công
                # sức của các dòng đã đọc xong). Giờ log rõ dòng nào lỗi
                # và BỎ QUA dòng đó, tiếp tục các dòng còn lại — video
                # vẫn xuất ra được, chỉ thiếu tiếng ở đúng đoạn đó.
                await self._tts(seg["text"], tmp)
                chunk_paths.append((seg["start"], tmp))
            except Exception as e:
                preview = seg["text"][:40].replace("\n", " ")
                failed.append(i)
                self._log(f"   ⚠️ Bỏ qua dòng {i+1}/{len(usable)} (lỗi TTS): {preview}… ({e})")

            # ✅ FIX: trước đây KHÔNG log gì khi 1 dòng thành công, nên
            # với vài trăm dòng chạy tuần tự, màn hình đứng im hàng phút
            # trông y hệt bị treo dù thực ra vẫn đang chạy bình thường.
            # Giờ báo tiến trình mỗi 5 dòng (và luôn báo dòng cuối) +
            # cập nhật progress bar theo % số dòng đã xử lý.
            if (i + 1) % 5 == 0 or (i + 1) == total_lines:
                self._log(f"   🔊 TTS: đã xử lý {i+1}/{total_lines} dòng…")
                self._set_stage(f"🔊 TTS {i+1}/{total_lines}", 40 + int(30 * (i + 1) / total_lines))

        if not chunk_paths:
            raise RuntimeError("Tất cả các dòng TTS đều thất bại.")
        if failed:
            self._log(f"   ⚠️ Tổng cộng {len(failed)}/{len(usable)} dòng bị bỏ qua do lỗi TTS.")

        input_args = []
        for _, f in chunk_paths:
            input_args += ["-i", str(f)]

        if len(chunk_paths) == 1:
            delay_ms = max(0, int(chunk_paths[0][0] * 1000))
            filter_complex = f"[0:a:0]adelay={delay_ms}:all=1[outa]"
        else:
            delay_parts = []
            mix_labels = []
            for idx, (start, _) in enumerate(chunk_paths):
                delay_ms = max(0, int(start * 1000))
                delay_parts.append(f"[{idx}:a:0]adelay={delay_ms}:all=1[d{idx}]")
                mix_labels.append(f"[d{idx}]")
            filter_complex = (
                ";".join(delay_parts) + ";" + "".join(mix_labels)
                + f"amix=inputs={len(chunk_paths)}:duration=longest:dropout_transition=0,"
                  f"volume={len(chunk_paths)}[outa]"
            )

        run_ffmpeg(["-y", *input_args, "-filter_complex", filter_complex,
                    "-map", "[outa]", "-ar", "44100", str(out_audio)])

    def _process_one(self,fp,idx):
        name=os.path.basename(fp)
        try:
            # ✅ FIX: nếu đã có SRT gốc (nhập tay hoặc tạo từ ASR) nhưng
            # người dùng quên bấm "🌐 Dịch SRT" trước khi bấm BẮT ĐẦU, tự
            # động dịch ngay tại đây. Trước đây trường hợp này rơi vào
            # luồng cũ (dịch cả khối text, TTS 1 track liên tục) và
            # KHÔNG BAO GIỜ xuất file .srt nào cả, dù đã có SRT gốc.
            if self._srt_segments and not self._srt_segments_vi:
                if self._try_use_manual_script_translation():
                    self._log("   🌐 Đã dùng nội dung script để tạo SRT dịch thủ công.")
                elif not self.api_key.get().strip():
                    raise RuntimeError(
                        "Đã có SRT gốc nhưng chưa dịch và chưa nhập API Key. "
                        "Nhập API Key rồi bấm '🌐 Dịch SRT' (hoặc bấm BẮT ĐẦU lại)."
                    )
                else:
                    self._log("   🌐 Có SRT gốc nhưng chưa dịch — tự động dịch trước khi TTS…")
                    self._srt_segments_vi = self._translate_srt_now(self._srt_segments)
                    self._log(f"   ✅ Đã tự động dịch {len(self._srt_segments_vi)} dòng SRT.")

            use_srt = bool(self._srt_segments_vi)  # đã có SRT dịch, giữ timestamp thật

            if not use_srt:
                # ─ Luồng cũ: không có SRT -> dịch cả khối text, TTS 1 track liên tục ─
                self._set_stage("🤖 Dịch 0%",0)
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
            else:
                self._log(f"   📝 Dùng {len(self._srt_segments_vi)} dòng SRT đã dịch (timestamp thật).")
                self._set_stage("🤖 Dịch 100%",40)

            self._set_stage("🔊 TTS 0%",40)
            with tempfile.TemporaryDirectory() as td:
                tdir=Path(td)
                mp3=tdir/"voice.mp3"

                loop=asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    if use_srt:
                        self._log(f"   🔊 Đang tạo giọng đọc đồng bộ theo {len(self._srt_segments_vi)} dòng…")
                        loop.run_until_complete(self._tts_segments_synced(self._srt_segments_vi, mp3, tdir))
                    else:
                        self._log(f"   🔊 Đang tạo giọng đọc ({len(tts_text)} ký tự)…")
                        loop.run_until_complete(self._tts(tts_text, mp3))
                finally:
                    loop.close()

                self._set_stage("🔊 TTS 100%",70)
                if not mp3.exists():
                    raise RuntimeError("TTS không tạo được file")

                self._set_stage("🎬 Ghép audio 0%",70)
                self._log(f"   🎬 Đang ghép audio…")
                out=self._out_path(fp,idx)
                # ✅ FIX: cùng vấn đề như lúc xuất SRT — nếu thư mục Output
                # không tạo/ghi được (quyền, đường dẫn sai…), rơi về thư
                # mục chứa video gốc thay vì làm cả job lỗi ngay bước cuối.
                try:
                    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
                except OSError as dir_err:
                    fallback_dir = os.path.dirname(os.path.abspath(fp))
                    self._log(
                        f"   ⚠️ Không dùng được thư mục Output '{os.path.dirname(out)}' ({dir_err}). "
                        f"Chuyển sang lưu cùng thư mục video: {fallback_dir}"
                    )
                    out = os.path.join(fallback_dir, os.path.basename(out))

                vol=self.vol_orig.get()/100.0
                run_ffmpeg([
                    "-i",fp,
                    "-i",str(mp3),
                    "-filter_complex",
                    f"[0:a:0]volume={vol}[orig];[1:a:0]volume=1.0[tts];[orig][tts]amix=inputs=2:duration=first[outa]",
                    "-map","0:v:0","-map","[outa]",
                    "-c:v","libx264","-crf","23","-c:a","aac","-shortest",out,
                ])
                self._set_stage("🎬 Ghép 100%",100)

                if use_srt:
                    srt_out = os.path.splitext(out)[0] + ".srt"
                    with open(srt_out, "w", encoding="utf-8") as f:
                        for i, seg in enumerate(self._srt_segments_vi, 1):
                            f.write(f"{i}\n{_format_ts(seg['start'])} --> {_format_ts(seg['end'])}\n{seg['text']}\n\n")
                    self._log(f"   💾 Xuất kèm SRT: {os.path.basename(srt_out)}")

                return True, out

        except Exception as e:
            self._set_stage("✕ Lỗi",100)
            return False, str(e)

    def _process(self):
        total=len(self.files); ok=0; fail=0
        for i,fp in enumerate(self.files):
            if self._cancel: break
            self._vid=i+1
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