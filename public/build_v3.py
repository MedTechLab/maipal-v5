#!/usr/bin/env python3
"""Build index-v3.html: v3 mobile UI (pixel-perfect replica of Maipalappfinalv3) + original JS logic"""

import re

# Read original for JS
with open('index.html', 'r') as f:
    orig = f.read()

js_start = orig.find('<script>')
js_end = orig.rfind('</script>')
orig_js = orig[js_start + len('<script>'):js_end].strip()

# Build HTML
html_parts = []
html_parts.append('''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>脉大夫</title>
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap");
    :root{--green:#7b8c76;--beige:#D7C8B0;--beige-l:#f8f3ee;--text-dk:#2a2a2a;--text-1:#5a4a3a;--text-2:#6b5d4f;}
    *{margin:0;padding:0;box-sizing:border-box;}
    html,body{height:100%;overflow:hidden;font-family:"Noto Sans SC",-apple-system,sans-serif;background:#faf5f0;color:var(--text-dk);-webkit-font-smoothing:antialiased;-webkit-tap-highlight-color:transparent;}
    .app-shell{position:relative;width:100%;max-width:430px;height:100%;max-height:100dvh;margin:0 auto;background:#fff;overflow:hidden;}

    /* Background */
    .bg-layer{position:absolute;inset:0;z-index:0;pointer-events:none;}.bg-layer img{width:100%;height:100%;object-fit:cover;}
    .bg-gradient{position:absolute;top:475px;left:0;width:100%;height:378px;z-index:0;pointer-events:none;
      background:linear-gradient(to bottom,rgba(248,243,238,0) 0%,rgba(248,243,238,.5)11.6%,rgba(249,244,239,.8)21.6%,rgba(249,244,239,.97)34.2%,#faf5f0 79.4%,#faf5f0 100%);}

    /* Header */
    .header{position:absolute;top:0;left:0;right:0;z-index:10;padding:53px 23px 16px;display:flex;justify-content:space-between;align-items:flex-start;pointer-events:auto;}
    .header-greeting p{filter:drop-shadow(0 3px 3px rgba(0,0,0,.12));height:36px;line-height:36px;font-size:32px;color:var(--green);margin:0;font-weight:normal;}
    .settings-btn{background:#f0e6dc;box-shadow:0 4px 4.75px rgba(185,185,185,.23);width:50px;height:66px;border-radius:10px;border:none;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;transition:transform .15s;}
    .settings-btn:active{transform:scale(.95);}
    .settings-btn svg{width:24px;height:24px;margin-bottom:4px;}
    .settings-btn span{font-size:12px;color:var(--text-1);line-height:1;}

    /* Doctor */
    .doctor-wrap{position:absolute;top:260px;left:50%;transform:translateX(-50%);z-index:20;pointer-events:none;}
    .doctor-img{height:422px;width:190px;object-fit:bottom;object-position:bottom;display:block;}
    .listening-badge{position:absolute;top:40px;left:50%;transform:translateX(-50%);background:#ef4444;color:#fff;padding:8px 16px;border-radius:9999px;font-size:14px;font-weight:500;box-shadow:0 4px 12px rgba(239,68,68,.35);white-space:nowrap;animation:lp 1s ease-in-out infinite;pointer-events:none;}
    @keyframes lp{0%,100%{transform:translateX(-50%) scale(1);}50%{transform:translateX(-50%) scale(1.08);}}

    /* Messages */
    .messages-area{position:absolute;left:24px;right:24px;top:145px;bottom:110px;z-index:30;overflow-y:auto;-webkit-overflow-scrolling:touch;
      -webkit-mask-image:linear-gradient(to bottom,transparent 0%,black 10%,black 92%,transparent 100%);mask-image:linear-gradient(to bottom,transparent 0%,black 10%,black 92%,transparent 100%);
      scrollbar-width:none;}.messages-area::-webkit-scrollbar{display:none;}
    .messages-inner{min-height:100%;display:flex;flex-direction:column;justify-content:flex-end;gap:12px;padding:16px 4px;}

    /* Bubbles - exact v3 spec */
    .msg-row{display:flex;animation:mIn .6s ease-out both;}.msg-row.user{justify-content:flex-end;}.msg-row.ai{justify-content:flex-start;}
    @keyframes mIn{from{opacity:0;transform:translateY(28px) scale(.98);}to{opacity:1;transform:translateY(0) scale(1);}}
    .msg-row.old .ai-bubble{opacity:.65;}
    .msg-bubble{max-width:72%;padding:13px 17px;border-radius:20px;font-size:14px;line-height:26px;word-break:break-word;}
    .ai-bubble{background:rgba(255,255,255,.78);color:var(--text-dk);border:1.18px solid rgba(111,184,153,.12);box-shadow:0 2px 4px 0 rgba(0,0,0,.05);backdrop-filter:blur(2px);}
    .user-bubble{background:var(--green);color:#fff;box-shadow:0 3px 5px 0 rgba(0,0,0,.08);}

    .sp-btn{display:inline-flex;align-items:center;gap:4px;margin-top:8px;padding:4px 10px;font-size:11px;color:var(--text-2);background:transparent;border:1px solid rgba(123,140,118,.25);border-radius:12px;cursor:pointer;transition:all .2s;}
    .sp-btn:hover{color:var(--green);border-color:var(--green);}.sp-btn.on{color:#fff;background:var(--green);border-color:var(--green);}

    /* Loading dots */
    .loading-row{display:flex;justify-content:flex-start;animation:mIn .6s both;}
    .lbub{background:rgba(255,255,255,.78);padding:13px 17px;border-radius:20px;border:1.18px solid rgba(111,184,153,.12);backdrop-filter:blur(2px);display:flex;align-items:center;gap:8px;}
    .ld{width:8px;height:8px;border-radius:50%;background:var(--green);animation:lbd .8s ease-in-out infinite;}
    .ld:nth-child(2){animation-delay:.2s;}.ld:nth-child(3){animation-delay:.4s;}
    @keyframes lbd{0%,100%{transform:scale(1);}50%{transform:scale(1.3);}}
    .ltxt{font-size:14px;color:var(--text-2);}

    /* Diagnosis card */
    .dcard{background:linear-gradient(135deg,#fdf6ec,#faf0df);border:1px solid #e8d4a8;border-radius:12px;padding:10px 12px;margin-top:4px;font-size:13px;line-height:1.65;}
    .dcard .tag{display:inline-block;background:var(--green);color:#fff;padding:2px 10px;border-radius:10px;font-size:11px;margin-bottom:6px;font-weight:500;}

    /* Markdown */
    .msg-bubble strong{font-weight:600;}.msg-bubble em{font-style:italic;opacity:.85;}
    .msg-bubble code{background:rgba(123,140,118,.1);padding:1px 5px;border-radius:4px;font-size:13px;}
    .msg-bubble pre{background:rgba(123,140,118,.08);border:1px solid rgba(123,140,118,.15);border-radius:8px;padding:10px;font-size:12px;overflow-x:auto;margin:6px 0;}
    .msg-bubble pre code{background:none;padding:0;}

    /* Quick Replies */
    .quick-replies{position:absolute;left:25px;right:25px;z-index:40;display:flex;gap:16px;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;top:641px;transition:top .3s;}
    .quick-replies::-webkit-scrollbar{display:none;}
    .qrp{display:flex;align-items:center;gap:4px;height:35px;padding:0 12px;background:rgba(255,255,255,.9);box-shadow:0 4px 4px rgba(107,93,79,.1);border-radius:30px;border:none;font-size:14px;color:var(--text-1);white-space:nowrap;cursor:pointer;flex-shrink:0;transition:transform .15s;font-family:inherit;}
    .qrp:active{transform:scale(.95);}

    /* Input Area */
    .input-area{position:absolute;left:25px;right:25px;z-index:40;height:51px;display:flex;align-items:center;top:690px;transition:top .3s;}
    .io{position:absolute;inset:0;background:rgba(255,255,255,.5);border-radius:30px;box-shadow:0 4px 8px 0 rgba(107,93,79,.05);}
    .ii{position:absolute;left:4px;right:55px;top:3px;bottom:3px;background:#fff;border-radius:30px;display:flex;align-items:center;padding:0 16px;gap:8px;}
    .ifield{flex:1;border:none;outline:none;background:transparent;font-size:14px;font-family:inherit;color:rgba(42,42,42,.8);min-width:0;}
    .ifield::placeholder{color:rgba(42,42,42,.5);}
    .micbtn{width:28px;height:28px;flex-shrink:0;border:none;background:none;cursor:pointer;padding:0;display:flex;align-items:center;justify-content:center;margin-right:2px;}
    .sbtn{position:absolute;right:0;width:40px;height:40px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .15s;background:none;padding:0;}
    .sbtn:active:not(:disabled){transform:scale(.95);}.sbtn:disabled{opacity:.45;}
    .rhint{position:absolute;left:25px;right:25px;z-index:39;text-align:center;font-size:12px;color:#ef4444;opacity:0;transition:opacity .2s;pointer-events:none;top:668px;}
    .rhint.show{opacity:1;}

    /* Perm Modal */
    .pmbg{position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:200;animation:fI .45s forwards;backdrop-filter:blur(3px);}
    .pmmd{position:fixed;left:50%;top:50%;transform:translate(-50%,calc(-50%+28px));z-index:200;width:calc(100%-56px);max-width:340px;background:rgba(255,255,255,.95);backdrop-filter:blur(4px);border-radius:28px;box-shadow:0 16px 40px rgba(0,0,0,.18);padding:28px 26px 24px;animation:mII .55s forwards;overflow:hidden;}
    @keyframes fI{from{opacity:0;}to{opacity:1;}}
    @keyframes mII{from{opacity:0;transform:translate(-50%,calc(-50%+52px)) scale(.94);}to{opacity:1;transform:translate(-50%,calc(-50%+28px)) scale(1);}}
    .pmbar{position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(to right,var(--green),var(--beige));}
    .pmttl{text-align:center;font-size:20px;font-weight:500;color:var(--text-1);margin-bottom:10px;}
    .pmdesc{text-align:center;font-size:16px;color:var(--text-2);line-height:1.6;margin-bottom:26px;}
    .pmok{width:100%;height:52px;background:var(--green);color:#fff;border:none;border-radius:30px;font-size:16px;font-weight:500;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:transform .15s;box-shadow:0 4px 6px 0 rgba(107,93,79,.15);}
    .pmok:active{transform:scale(.95);}
    .pmno{width:100%;height:44px;background:var(--beige-l);color:var(--text-2);border:1px solid rgba(123,140,118,.2);border-radius:30px;font-size:16px;font-weight:500;cursor:pointer;display:flex;align-items:center;justify-content:center;margin-top:8px;transition:transform .15s;}
    .pmno:active{transform:scale(.95);}''')

html_parts.append('''
    /* Face Observation Modal (v3 exact) */
    .fmbg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;animation:fI .45s forwards;backdrop-filter:blur(4px);}
    .fmdl{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:200;width:85%;max-width:360px;}
    .fpnl{background:rgba(248,243,238,.95);backdrop-filter:blur(4px);border-radius:28px;padding:24px;box-shadow:0 12px 28px 0 rgba(107,93,79,.25);position:relative;overflow:hidden;}
    .fcls{position:absolute;top:16px;right:16px;z-index:10;width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,.6);backdrop-filter:blur(4px);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;color:var(--text-1);line-height:1;}
    .ftitle{text-align:center;margin-bottom:20px;position:relative;z-index:10;}
    .ftitle h2{font-size:24px;font-weight:500;color:var(--green);margin-bottom:6px;}
    .ftitle p{font-size:15px;color:var(--text-2);}
    .cprev{position:relative;width:100%;height:260px;border-radius:22px;overflow:hidden;margin-bottom:16px;background:linear-gradient(135deg,rgba(215,200,176,.4),rgba(123,140,118,.2));box-shadow:inset 0 2px 8px rgba(0,0,0,.06);}
    .cprev video,.cprev canvas{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}
    .cprev canvas{display:none;}
    .ffwrap{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;}
    .ffr{width:160px;height:200px;border-radius:28px;border:2px dashed rgba(215,200,176,.8);position:relative;}
    .ffc{position:absolute;width:24px;height:24px;border-color:var(--beige);border-style:solid;}
    .ffc.tl{top:-2px;left:-2px;border-width:3px 0 0 3px;border-top-left-radius:28px;}
    .ffc.tr{top:-2px;right:-2px;border-width:3px 3px 0 0;border-top-right-radius:28px;}
    .ffc.bl{bottom:-2px;left:-2px;border-width:0 0 3px 3px;border-bottom-left-radius:28px;}
    .ffc.br{bottom:-2px;right:-2px;border-width:0 3px 3px 0;border-bottom-right-radius:28px;}
    .chint{position:absolute;bottom:16px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,.3);backdrop-filter:blur(4px);padding:8px 16px;border-radius:9999px;pointer-events:none;}
    .chint p{font-size:13px;color:rgba(255,255,255,.9);margin:0;}
    .fscard{background:rgba(255,255,255,.8);backdrop-filter:blur(4px);border-radius:18px;padding:16px;margin-bottom:20px;display:flex;align-items:center;gap:12px;box-shadow:0 4px 8px 0 rgba(107,93,79,.08);}
    .favtr{width:48px;height:48px;border-radius:50%;overflow:hidden;flex-shrink:0;background:var(--beige-l);}
    .favtr img{width:100%;height:100%;object-fit:cover;object-position:top;transform:scale(1.5) translateY(8px);}
    .fsmain{font-size:15px;font-weight:500;color:var(--text-1);margin-bottom:4px;}
    .fssub{font-size:13px;color:rgba(107,93,79,.64);}
    .fdots{display:flex;justify-content:center;gap:8px;margin-bottom:20px;}
    .fdot{width:8px;height:8px;border-radius:50%;transition:all .3s;}.fdot.on{background:var(--green);}.fdot.off{background:rgba(215,200,176,.4);}
    .fabtn{width:100%;background:var(--green);color:#fff;border:none;border-radius:16px;font-size:16px;font-weight:500;padding:14px 0;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .2s;box-shadow:0 4px 8px 0 rgba(107,93,79,.2);}
    .fabtn:disabled{opacity:.5;cursor:default;}
    .fcst{font-size:13px;text-align:center;margin-top:8px;min-height:18px;}
    .fcst.err{color:#ef4444;}.fcst.ok{color:#22c55e;}''')

html_parts.append('''
    /* Voice Listening Modal (v3 exact) */
    .vmbg{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:200;animation:fI .45s forwards;backdrop-filter:blur(4px);}
    .vmdl{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:200;width:85%;max-width:360px;}
    .vpnl{background:rgba(248,243,238,.95);backdrop-filter:blur(4px);border-radius:28px;padding:24px;box-shadow:0 12px 28px 0 rgba(107,93,79,.25);position:relative;overflow:hidden;}
    .vcls{position:absolute;top:16px;right:16px;z-index:10;width:32px;height:32px;border-radius:50%;background:rgba(255,255,255,.6);backdrop-filter:blur(4px);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px;color:var(--text-1);line-height:1;}
    .vhdr{text-align:center;margin-bottom:20px;position:relative;z-index:10;}
    .vhdr h2{font-size:24px;font-weight:500;color:var(--green);margin-bottom:6px;}
    .vhdr p{font-size:15px;color:var(--text-2);}
    .vscript{background:rgba(255,255,255,.9);border-radius:20px;padding:24px;margin-bottom:12px;box-shadow:0 4px 8px 0 rgba(107,93,79,.06);}
    .vscript p{font-size:22px;font-weight:500;color:var(--text-1);text-align:center;line-height:1.6;margin:0;}
    .vhint{text-align:center;font-size:13px;color:rgba(107,93,79,.48);margin-bottom:24px;}
    .vmicarea{display:flex;flex-direction:column;align-items:center;margin-bottom:24px;position:relative;}
    .vbreathe{position:absolute;inset:-16px;border-radius:50%;background:var(--green);animation:bG 2s ease-in-out infinite;pointer-events:none;}
    @keyframes bG{0%,100%{transform:scale(1);opacity:.3;}50%{transform:scale(1.3);opacity:0;}}
    .vmicbtn{width:76px;height:76px;border-radius:50%;background:var(--green);border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 12px 0 rgba(107,93,79,.2);position:relative;z-index:10;transition:transform .15s;}
    .vmicbtn:disabled{opacity:.5;cursor:default;}
    .vmicbtn.recording{animation:mSc 1.5s ease-in-out infinite;}
    @keyframes mSc{0%,100%{transform:scale(1);}50%{transform:scale(1.05);}}
    .vwaves{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);display:flex;align-items:center;gap:6px;pointer-events:none;}
    .vwaves.l{margin-right:80px;}.vwaves.r{margin-left:80px;}
    .swb{width:4px;height:24px;border-radius:2px;background:rgba(123,140,118,.3);animation:swB .8s ease-in-out infinite;}
    .swb:nth-child(2){animation-delay:.1s;}.swb:nth-child(3){animation-delay:.2s;}
    @keyframes swB{0%,100%{transform:scaleY(1);}50%{transform:scaleY(1.5);}}
    .vmstat p{font-size:15px;color:var(--text-2);margin:0;}
    .vtimer{font-size:13px;color:var(--green);margin-top:4px;}
    .vskip{width:100%;background:rgba(255,255,255,.8);color:var(--text-2);border:none;border-radius:16px;font-size:15px;font-weight:500;padding:14px 0;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:transform .15s;box-shadow:0 4px 6px 0 rgba(107,93,79,.08);}
    .vlvl{width:100%;margin-top:8px;}
    .vlvlbar{width:100%;height:6px;border-radius:3px;background:rgba(215,200,176,.5);overflow:hidden;}
    .vlvlin{height:100%;background:linear-gradient(90deg,#22c55e,var(--green));width:0%;transition:width .08s linear;}
    .vrst{font-size:13px;text-align:center;margin-top:8px;min-height:18px;}
    .vrst.err{color:#ef4444;}.vrst.ok{color:#22c55e;}
    .hidden{display:none!important;}
  </style>
</head>
<body>
<div class="app-shell" id="appShell">
  <div class="bg-layer"><img src="assets/bg-shanshui.png" alt="" /></div>
  <div class="bg-gradient"></div>

  <!-- Header -->
  <div class="header">
    <div class="header-greeting"><p>你好，朋友</p><p>我是脉医生</p></div>
    <button class="settings-btn" id="clearBtn" title="新问诊">
      <svg viewBox="0 0 24 24" fill="none" stroke="#7b8c76" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      <span>设置</span>
    </button>
  </div>

  <!-- Doctor Character -->
  <div class="doctor-wrap" id="doctorWrap">
    <img class="doctor-img" src="assets/doctor-oldman.png" alt="脉医生" />
    <div class="listening-badge hidden" id="listeningBadge">正在聆听...</div>
  </div>

  <!-- Messages -->
  <div class="messages-area" id="messagesArea">
    <div class="messages-inner" id="messagesInner"></div>
  </div>

  <!-- Quick Replies -->
  <div class="quick-replies" id="quickReplies"></div>

  <!-- Recording Hint -->
  <div class="recording-hint-bar" id="recordingHint">🎤 正在听您说话... 再次点击麦克风结束</div>

  <!-- Input Area -->
  <div class="input-area">
    <div class="io"></div>
    <div class="ii">
      <input class="ifield" id="userInput" placeholder="输入您的回答..." />
      <button class="micbtn" id="voiceBtn" title="语音输入">
        <svg viewBox="0 0 10 18" width="10" height="18" fill="none" stroke="#7b8c76" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.61854 1.16642C3.70298 1.16642 2.82492 1.53509 2.17752 2.19132C1.53012 2.84756 1.16642 3.73761 1.16642 4.66567V12.8306C1.16642 13.7586 1.53012 14.6487 2.17752 15.3049C2.82492 15.9612 3.70298 16.3298 4.61854 16.3298C5.5341 16.3298 6.41216 15.9612 7.05956 15.3049C7.70696 14.6487 8.07066 13.7586 8.07066 12.8306V4.66567C8.07066 3.73761 7.70696 2.84756 7.05956 2.19132C6.41216 1.53509 5.5341 1.16642 4.61854 1.16642Z"/><path d="M1.16642 1.16642V3.49925C1.16642 5.66472 2.4277 7.7415 4.27999 9.27272C6.13227 10.8039 8.42994 11.6642 10.8824 11.6642" transform="translate(0.5,0)"/></svg>
      </button>
    </div>
    <button class="sbtn" id="sendBtn">
      <svg viewBox="0 0 37 37" width="40" height="40" fill="none"><circle cx="18.5" cy="18.5" r="17" fill="#D7C8B0"/><path d="M12 12L26 26M12 26L26 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="rotate(-45 19 19) translate(-1,2)"/></svg>
    </button>
  </div>

  <!-- Camera Permission Modal -->
  <div class="pmbg hidden" id="camPermBg"></div>
  <div class="pmmd hidden" id="camPermMd">
    <div class="pmbar"></div>
    <div class="pmttl">"脉伴"想访问您的相机</div>
    <div class="pmdesc">用于面部气色分析，帮助更好地了解您的健康状况</div>
    <button class="pmok" id="camPermOk">允许</button>
    <button class="pmno" id="camPermNo">不允许</button>
  </div>

  <!-- Mic Permission Modal -->
  <div class="pmbg hidden" id="micPermBg"></div>
  <div class="pmmd hidden" id="micPermMd">
    <div class="pmbar"></div>
    <div class="pmttl">"脉伴"想访问您的麦克风</div>
    <div class="pmdesc">用于声音分析，帮助更好地了解您的健康状况</div>
    <button class="pmok" id="micPermOk">允许</button>
    <button class="pmno" id="micPermNo">不允许</button>
  </div>

  <!-- Face Observation Modal (v3 exact) -->
  <div class="fmbg hidden" id="faceBg"></div>
  <div class="fmdl hidden" id="faceModal">
    <div class="fpnl">
      <button class="fcls" id="faceCloseBtn">&#10005;</button>
      <div class="ftitle">
        <h2>我先看看您的气色</h2>
        <p>请看向屏幕，保持自然表情</p>
      </div>
      <div class="cprev">
        <video id="faceVideo" autoplay playsinline muted></video>
        <canvas id="faceCanvas"></canvas>
        <div class="ffwrap"><div class="ffr" id="faceFrame">
          <div class="ffc tl"></div><div class="ffc tr"></div><div class="ffc bl"></div><div class="ffc br"></div>
        </div></div>
        <div class="chint"><p>请将面部保持在框内</p></div>
      </div>
      <div class="fscard">
        <div class="favtr"><img src="assets/doctor-oldman.png" alt="脉医生" /></div>
        <div><p class="fsmain" id="faceStMain">脉医生准备看一看</p><p class="fssub" id="faceStSub">建议在光线自然的环境下进行</p></div>
      </div>
      <div class="fdots"><div class="fdot on" id="fd0"></div><div class="fdot off" id="fd1"></div><div class="fdot off" id="fd2"></div></div>
      <button class="fabtn" id="faceActionBtn">开始</button>
      <div class="fcst" id="faceCamStatus"></div>
    </div>
  </div>

  <!-- Voice Listening Modal (v3 exact) -->
  <div class="vmbg hidden" id="voiceBg"></div>
  <div class="vmdl hidden" id="voiceModalBox">
    <div class="vpnl">
      <button class="vcls" id="voiceCloseBtn">&#10005;</button>
      <div class="vhdr">
        <h2>听听您的声音</h2>
        <p>请自然读出这句话</p>
      </div>
      <div class="vscript"><p id="voiceScriptText">今天天气很好，我现在感觉还可以。</p></div>
      <p class="vhint">用平时说话的方式读就好</p>
      <div class="vmicarea">
        <div class="vbreathe hidden" id="voiceBreath"></div>
        <div class="vwaves hidden" id="voiceWavesL"><div class="swb"></div><div class="swb"></div><div class="swb"></div></div>
        <div class="vwaves hidden" id="voiceWavesR"><div class="swb"></div><div class="swb"></div><div class="swb"></div></div>
        <button class="vmicbtn" id="voiceMicBtn">
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
        </button>
      </div>
      <div class="vmicstat"><p id="voiceMicStatus">点击开始</p><p class="vtimer hidden" id="voiceTimer"></p></div>
      <div class="vlvl"><div class="vlvlbar" id="voiceLevelBar"></div></div>
      <button class="vskip" id="voiceSkipBtn">稍后再说</button>
      <div class="vrst" id="voiceRecStatus"></div>
    </div>
  </div>
</div>

<script>
''' + orig_js + '''
</script>
</body>
</html>''')

with open('index-v3.html', 'w') as f:
    f.write('\n'.join(html_parts))

output = '\n'.join(html_parts)
print(f'OK! Total: {len(output)} chars')
