from __future__ import annotations

import json
import time
import os
from pathlib import Path
from typing import Any, List

from drun.models.report import RunReport, CaseInstanceResult, StepResult, AssertionResult


def _json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        try:
            return json.dumps(str(obj), ensure_ascii=False)
        except Exception:
            return str(obj)


def _align_like_console(text: str, pad_cols: int = 50) -> str:
    """Align multiline text like console logs: pad lines after the first.

    This only affects visual presentation; callers can still use the original
    JSON as `data-raw` for copy, while the displayed code gets aligned.
    """
    if not text:
        return text
    lines = text.splitlines()
    if len(lines) <= 1:
        return text
    pad = " " * max(pad_cols, 0)
    return lines[0] + "\n" + "\n".join(pad + ln for ln in lines[1:])


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;")
    )


def _build_assert_table(asserts: List[AssertionResult]) -> str:
    rows = []
    for a in asserts or []:
        cells = [
            f"<td><code>{_escape_html(str(a.check))}</code></td>",
            f"<td><code>{_escape_html(str(a.comparator))}</code></td>",
            f"<td><code>{_escape_html(json.dumps(a.expect, ensure_ascii=False))}</code></td>",
            f"<td><code>{_escape_html(json.dumps(a.actual, ensure_ascii=False))}</code></td>",
            ("<td><span class='ok'>✓</span></td>" if a.passed else f"<td><span class='err' title='{_escape_html(a.message or '')}'>✗</span></td>")
        ]
        rows.append("<tr " + ("data-pass=1" if a.passed else "data-pass=0") + ">" + "".join(cells) + "</tr>")
    thead = "<thead><tr><th>check</th><th>op</th><th>expect</th><th>actual</th><th>结果</th></tr></thead>"
    return f"<table class='assert-table'>{thead}<tbody>{''.join(rows)}</tbody></table>"


def _build_step(step: StepResult) -> str:
    pass_cnt = sum(1 for a in (step.asserts or []) if a.passed)
    fail_cnt = sum(1 for a in (step.asserts or []) if not a.passed)

    request_map = step.request if isinstance(step.request, dict) else {}
    response_map = step.response if isinstance(step.response, dict) else {}

    headers_payload = {}
    if isinstance(request_map, dict) and isinstance(request_map.get("headers"), dict):
        headers_payload = dict(request_map.get("headers") or {})

    body_payload: Any
    if isinstance(request_map, dict):
        if request_map.get("body") is not None:
            body_payload = request_map.get("body")
        elif request_map.get("data") is not None:
            body_payload = request_map.get("data")
        else:
            fallback = {k: v for k, v in request_map.items() if k != "headers"}
            body_payload = fallback or None
    else:
        body_payload = None

    resp_body_payload = response_map.get("body") if isinstance(response_map, dict) else None
    resp_status = response_map.get("status_code") if isinstance(response_map, dict) else None

    req_headers_json = _json(headers_payload)
    req_headers_display = _align_like_console(req_headers_json)
    req_body_json = _json(body_payload)
    req_body_display = _align_like_console(req_body_json)
    resp_body_json = _json(resp_body_payload)
    resp_body_display = _align_like_console(resp_body_json)

    method_text = request_map.get("method") if isinstance(request_map, dict) else None
    url_text = request_map.get("url") if isinstance(request_map, dict) else None
    request_meta_text = None
    if method_text and url_text:
        request_meta_text = f"{method_text} {url_text}"
    elif method_text:
        request_meta_text = str(method_text)
    elif url_text:
        request_meta_text = str(url_text)

    status_meta_text = None
    if resp_status is not None:
        status_meta_text = f"status={resp_status}"

    req_title = "请求体"
    resp_title = "响应体"

    ext_json = _json(step.extracts) if (step.extracts or {}) else None
    curl = step.curl or ""

    meta_snippets: List[str] = []
    if request_meta_text:
        meta_snippets.append(f"<span class='st-meta'>{_escape_html(request_meta_text)}</span>")
    if status_meta_text:
        meta_snippets.append(f"<span class='st-meta'>{_escape_html(status_meta_text)}</span>")
    left_meta_html = " ".join(meta_snippets)

    head_left = f"<div><b>步骤：</b>{_escape_html(step.name)}"
    if left_meta_html:
        head_left += f" {left_meta_html}"
    head_left += "</div>"

    head_right = (
        "<div>"
        f"<span class='pill {step.status}'>{step.status}</span>"
        f"<span class='muted' style='margin-left:8px;'>{step.duration_ms:.1f} ms</span>"
        f"<span class='muted' style='margin-left:8px;'>断言: {pass_cnt} ✓ / {fail_cnt} ✗</span>"
        "</div>"
    )

    head = (
        "<div class='st-head' onclick=\"window.toggleStepBody && window.toggleStepBody(this)\">"
        f"{head_left}{head_right}"
        "</div>"
    )

    panels = []
    request_panel = (
        "<div class='panel' data-section='request-body'>"
        f"<div class='p-head'><span>{req_title}</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
        f"<pre data-raw=\"{_escape_html(req_body_json)}\"><code>{_escape_html(req_body_display)}</code></pre>"
        "</div>"
    )

    response_panel = (
        "<div class='panel' data-section='response-body'>"
        f"<div class='p-head'><span>{resp_title}</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
        f"<pre data-raw=\"{_escape_html(resp_body_json)}\"><code>{_escape_html(resp_body_display)}</code></pre>"
        "</div>"
    )

    if headers_payload:
        panels.append(
            "<div class='panel' data-section='request-headers' style='margin-top:8px;'>"
            "<div class='p-head'><span>请求头</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
            f"<pre data-raw=\"{_escape_html(req_headers_json)}\"><code>{_escape_html(req_headers_display)}</code></pre>"
            "</div>"
        )

    panels.append(
        "<div class='grid' style='margin-top:8px;'>"
        + request_panel
        + response_panel
        + "</div>"
    )

    # Error panel (if any)
    if step.error:
        err_text = _escape_html(step.error)
        panels.append(
            "<div class='panel' data-section='error' style='margin-top:8px;'>"
            "<div class='p-head'><span>错误</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
            f"<pre data-raw=\"{err_text}\"><code>{err_text}</code></pre>"
            "</div>"
        )

    if ext_json and ext_json != "{}":
        panels.append(
            "<div class='panel' data-section='extracts' style='margin-top:8px;'>"
            "<div class='p-head'><span>提取变量</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
            f"<pre data-raw=\"{_escape_html(ext_json)}\"><code>{_escape_html(ext_json)}</code></pre>"
            "</div>"
        )

    # Asserts table
    panels.append(
        "<div class='panel' style='margin-top:8px;'>"
        "<div class='p-head'><span>断言</span></div>"
        + _build_assert_table(step.asserts or [])
        + "</div>"
    )

    # cURL section
    if curl:
        panels.append(
            "<div class='panel' data-section='curl' style='margin-top:8px;'>"
            "<div class='p-head'><span>cURL</span><span class='actions'><button onclick=\"window.copyPanel && window.copyPanel(this)\">复制</button></span></div>"
            f"<pre data-raw=\"{_escape_html(curl)}\"><code>{_escape_html(curl)}</code></pre>"
            "</div>"
        )

    body = "<div class='body'>" + "".join(panels) + "</div>"
    return f"<div class='step'><div>{head}</div>{body}</div>"


def _build_case(case: CaseInstanceResult) -> str:
    params = case.parameters or {}
    params_html = f"<div class='muted'>参数：<code>{_escape_html(_json(params))}</code></div>" if params else ""

    case_meta: str | None = None
    src = getattr(case, "source", None)
    if src:
        try:
            p = Path(src)
            cwd = Path.cwd().resolve()
            try:
                case_meta = str(p.resolve().relative_to(cwd))
            except Exception:
                try:
                    case_meta = os.path.relpath(str(p), str(cwd))
                except Exception:
                    case_meta = str(p)
        except Exception:
            case_meta = str(src)

    meta_html = f" <span class='case-meta st-meta'>{_escape_html(case_meta)}</span>" if case_meta else ""

    head = (
        "<div class='head'>"
        f"<div><div><b>用例：</b>{_escape_html(case.name)}{meta_html}</div>{params_html}</div>"
        f"<div><span class='pill {case.status}'>{case.status}</span>"
        f"<span class='muted' style='margin-left:8px;'>{case.duration_ms:.1f} ms</span></div>"
        "</div>"
    )

    steps_html = "".join(_build_step(s) for s in (case.steps or []))
    return f"<div class='case' data-status='{case.status}' data-duration='{case.duration_ms:.3f}'>{head}<div class='body'>{steps_html}</div></div>"


def write_html(report: RunReport, outfile: str | Path) -> None:
    s = report.summary or {}
    gen_time = time.strftime("%Y-%m-%d %H:%M:%S")

    # Header + styles (light theme, GitHub-like)
    head_parts = []
    head_parts.append("""
<!doctype html><html lang='zh-CN'><head><meta charset='utf-8' /><meta name='viewport' content='width=device-width, initial-scale=1' />
<title>Drun 测试报告</title>
<style>
  :root { --bg:#ffffff; --fg:#24292f; --muted:#57606a; --ok:#1a7f37; --fail:#cf222e; --skip:#6e7781; --card:#f6f8fa; --accent:#0969da; --border:#d0d7de; --panel-head-bg:#f6f8fa; --step-head-bg:#f6f8fa; --chip-bg:#f6f8fa; --btn-bg:#ffffff; --input-bg:#ffffff; --code-key:#0550ae; --code-str:#0a3069; --code-num:#953800; --code-bool:#1a7f37; --code-null:#6e7781; --code-punct:#57606a; }
  html, body { margin:0; padding:0; background:var(--bg); color:var(--fg); font: 14px/1.45 -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 0 16px 64px; }
  h1 { font-size: 20px; margin: 0; }
  .header-sticky { position: sticky; top: 0; z-index: 999; background: var(--bg); padding: 12px 0 10px; border-bottom: 1px solid var(--border); }
  .headbar { display:flex; justify-content: space-between; align-items: baseline; gap: 12px; margin-bottom: 8px; }
  .meta { color: var(--muted); font-size: 12px; }
  .summary { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin-bottom: 24px; }
  .badge { position:relative; padding:16px 18px; border-radius: 10px; background: var(--card); border:1px solid var(--border); box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .badge::before { content:''; position:absolute; top:0; left:0; width:4px; height:100%; border-radius:10px 0 0 10px; }
  .badge.total::before { background: var(--accent); }
  .badge.passed::before { background: var(--ok); }
  .badge.failed::before { background: var(--fail); }
  .badge.skipped::before { background: var(--skip); }
  .badge.duration::before { background: #8250df; }
  .badge-label { display:block; font-size:12px; color:var(--muted); margin-bottom:6px; }
  .badge-value { display:block; font-size:28px; font-weight:700; line-height:1; }
  .badge.passed .badge-value { color: var(--ok); }
  .badge.failed .badge-value { color: var(--fail); }
  .badge.skipped .badge-value { color: var(--skip); }
  .passed { color: var(--ok); }
  .failed { color: var(--fail); }
  .skipped { color: var(--skip); }
  .case { border: 1px solid var(--border); background: var(--card); border-radius: 10px; margin: 14px 0; overflow: hidden; }
  .case > .head { padding: 12px 12px; display:flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); }
  .case .case-meta { margin-left: 10px; font-size: inherit; font-weight: 500; color: var(--muted); }
  .pill { font-size: 12px; padding: 2px 8px; border-radius: 999px; border:1px solid var(--border); }
  .pill.passed { border-color: var(--ok); }
  .pill.failed { border-color: var(--fail); }
  .pill.skipped { border-color: var(--skip); }
  .body { padding: 10px 12px; }
  .step { border: 1px solid var(--border); border-radius: 8px; margin: 10px 0; overflow:hidden; }
  .step .st-head { padding: 8px 10px; display:flex; justify-content: space-between; align-items:center; background: var(--step-head-bg); cursor: pointer; }
  .step .st-head .st-meta { font-size: 12px; font-weight: 500; margin-left: 8px; color: var(--muted); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 8px; }
  .panel { border:1px solid var(--border); border-radius:8px; overflow:hidden; }
  .panel .p-head { padding:6px 8px; background:var(--panel-head-bg); color:var(--muted); font-size:12px; display:flex; justify-content:space-between; align-items:center; }
  .panel .p-head .actions { display:flex; gap:6px; }
  .panel pre, .panel table { margin:0; padding:10px; overflow:auto; max-height: 360px; }
  .panel[data-section='curl'] pre { white-space: pre-wrap; word-break: break-word; }
  table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  th { padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: top; text-align: left; font-weight: 600; }
  td { padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: top; word-break: break-word; }
  .assert-table th:nth-child(1), .assert-table td:nth-child(1) { width: 25%; }
  .assert-table th:nth-child(2), .assert-table td:nth-child(2) { width: 10%; }
  .assert-table th:nth-child(3), .assert-table td:nth-child(3) { width: 25%; }
  .assert-table th:nth-child(4), .assert-table td:nth-child(4) { width: 25%; }
  .assert-table th:nth-child(5), .assert-table td:nth-child(5) { width: 15%; text-align: center; }
  .ok { color: var(--ok); }
  .err { color: var(--fail); }
  .muted { color: var(--muted); }
  code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px; }
  details { border-top: 1px dashed var(--border); }
  details > summary { cursor: pointer; list-style: none; padding: 8px 10px; color: var(--muted); }
  details > summary::-webkit-details-marker { display: none; }
  .toolbar { display:grid; grid-template-columns: 1fr auto; gap:8px; align-items:center; margin-bottom: 8px; }
  .toolbar .filters { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
  .toolbar button { padding:6px 10px; border-radius:6px; border:1px solid var(--border); background:var(--btn-bg); color:var(--fg); cursor:pointer; transition: all 0.2s ease; }
  .toolbar button:hover { border-color:var(--accent); }
  .toolbar .chip { background:var(--chip-bg); border:1px solid var(--border); padding:4px 8px; border-radius:999px; display:inline-flex; align-items:center; gap:6px; }
  .toolbar input[type='radio']{ accent-color: var(--accent); }
  .panel .p-head button { padding:4px 8px; font-size:11px; border-radius:4px; border:1px solid var(--border); background:var(--btn-bg); color:var(--fg); cursor:pointer; transition: all 0.2s ease; }
  .panel .p-head button:hover { border-color:var(--accent); }
  .panel .p-head button.copied { border-color:var(--ok); background:#dafbe1; color:var(--ok); font-weight:500; }
  .panel .p-head button.copy-failed { border-color:var(--fail); background:#ffebe9; color:var(--fail); font-weight:500; }
  .footer { margin-top: 24px; color: var(--muted); font-size: 12px; }
  .collapsed .body { display: none; }
</style>
<script>(function(){
  function esc(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
  function highlightJSONSimple(text){
    // Keep it robust: just escape without fancy tokenization to avoid parser pitfalls.
    return esc(text);
  }
  function fallbackCopy(text){
    // Best-effort copy via hidden textarea; works in most browsers including file://
    try{
      var ta=document.createElement('textarea');
      ta.value=text;
      ta.setAttribute('readonly','');
      ta.style.position='fixed';
      ta.style.opacity='0';
      ta.style.left='-9999px';
      ta.style.top='0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      // iOS Safari requires explicit range selection
      try{ ta.setSelectionRange(0, ta.value.length); }catch(_){ /* ignore */ }
      var ok=false; try{ ok=document.execCommand('copy'); }catch(e){ ok=false; }
      document.body.removeChild(ta);
      return ok;
    }catch(e){ return false; }
  }
  function selectForManual(preEl, btn){
    try{
      var range=document.createRange();
      range.selectNodeContents(preEl);
      var sel=window.getSelection ? window.getSelection() : null;
      if(sel){ sel.removeAllRanges(); sel.addRange(range); }
      if(btn){ btn.innerText='已选中，按 Ctrl/Cmd+C'; btn.classList.add('copy-failed'); }
    }catch(_){ /* ignore */ }
  }
  function showCopied(btn){
    if(!btn) return;
    var old=btn.innerText;
    btn.innerText='已复制';
    btn.classList.remove('copy-failed');
    btn.classList.add('copied');
    setTimeout(function(){
      btn.innerText=old;
      btn.classList.remove('copied');
    }, 1500);
  }
  function showCopyFailed(btn){
    if(!btn) return;
    var old=btn.innerText;
    btn.innerText='复制失败';
    btn.classList.remove('copied');
    btn.classList.add('copy-failed');
    setTimeout(function(){
      btn.innerText=old;
      btn.classList.remove('copy-failed');
    }, 1500);
  }
  window.toggleStepBody = function(headEl){ var step=headEl && headEl.closest ? headEl.closest('.step') : null; if(!step) return; step.classList.toggle('collapsed'); };
  function closestPanel(el){
    if(!el) return null;
    if(el.closest) return el.closest('.panel');
    // Fallback for very old browsers
    var p=el; while(p){ if(p.classList && p.classList.contains('panel')) return p; p=p.parentElement; }
    return null;
  }
  window.copyPanel = function(btn){
    try{
      var panel=closestPanel(btn);
      if(!panel) return;
      var pre=panel.querySelector('pre');
      if(!pre) return;
      var text=pre.getAttribute('data-raw') || pre.innerText || pre.textContent || '';
      if(!text) return;
      var did=false;
      try{
        var canClipboard = (typeof navigator!=='undefined' && navigator.clipboard && typeof navigator.clipboard.writeText==='function');
        if(canClipboard){
          navigator.clipboard.writeText(text).then(function(){
            showCopied(btn);
          }).catch(function(){
            if(fallbackCopy(text)) { showCopied(btn); }
            else { selectForManual(pre, btn); }
          });
          did=true;
        }
      }catch(_){ /* ignore */ }
      if(!did){
        if(fallbackCopy(text)) { showCopied(btn); }
        else { selectForManual(pre, btn); }
      }
    }catch(e){
      showCopyFailed(btn);
      try{ console.warn('copy failed', e); }catch(_){}
    }
  };
  // Toggle all steps (ES5-friendly; avoids const/arrow/Array.from)
  window.toggleAllSteps = function(btn){
    try{
      var list = document.querySelectorAll ? document.querySelectorAll('.step') : [];
      var steps;
      try{ steps = Array.prototype.slice.call(list); }catch(_){
        steps = [];
        for(var i=0;i<list.length;i++){ steps.push(list[i]); }
      }
      var anyExpanded = false;
      for(var j=0;j<steps.length;j++){
        var st = steps[j];
        if(!st.classList || !st.classList.contains('collapsed')){ anyExpanded = true; break; }
      }
      if(anyExpanded){
        for(var k=0;k<steps.length;k++){ if(steps[k].classList){ steps[k].classList.add('collapsed'); } }
        if(btn){ btn.textContent = '展开全部'; }
      }else{
        for(var m=0;m<steps.length;m++){ if(steps[m].classList){ steps[m].classList.remove('collapsed'); } }
        if(btn){ btn.textContent = '收起全部'; }
      }
    }catch(e){ /* ignore */ }
  };
  window.applyFilters = function(){ var selEl=document.querySelector("input[name='status-filter']:checked"); var sel=(selEl && selEl.value) || 'all'; try{localStorage.setItem('drun_report_status', sel);}catch(e){} document.querySelectorAll('.case').forEach(function(c){ var st=(c.dataset && c.dataset.status)||''; c.style.display=(sel==='all'||st===sel)?'':''; }); };
  document.addEventListener('DOMContentLoaded', function(){
    try{ var saved=localStorage.getItem('drun_report_status')||'all'; var el=document.querySelector("input[name='status-filter'][value='"+saved+"']"); if(el) el.checked=true; }catch(e){}
    document.querySelectorAll("input[name='status-filter']").forEach(function(el){ el.addEventListener('change', window.applyFilters); });
    // JSON highlight (preserve original indentation)
    document.querySelectorAll('.panel pre code').forEach(function(code){
      var panel= code.closest ? code.closest('.panel') : null; if(panel && panel.dataset && panel.dataset.section==='curl') return;
      var pre = code.parentElement; var raw=(pre && pre.getAttribute('data-raw')) || code.innerText || code.textContent || '';
      var html = highlightJSONSimple(raw);
      code.innerHTML = html;
    });
    window.applyFilters();
  });
})();</script>
""")
    # style tag already closed in the header string above
    head_parts.append("</head><body>\n<div class='wrap'>\n  <div class='header-sticky'>\n    <div class='headbar'>\n      <h1>Drun 测试报告</h1>\n      <div class='meta'>生成时间：" + _escape_html(gen_time) + "</div>\n    </div>\n")
    # Summary badges
    total = str(s.get('total', 0))
    passed = str(s.get('passed', 0))
    failed = str(s.get('failed', 0))
    skipped = str(s.get('skipped', 0))
    duration = f"{float(s.get('duration_ms', 0.0)):.1f}"
    head_parts.append("    <div class='summary'>\n")
    head_parts.append("      <div class='badge total'><span class='badge-label'>用例总数</span><span class='badge-value'>" + total + "</span></div>\n")
    head_parts.append("      <div class='badge passed'><span class='badge-label'>通过</span><span class='badge-value'>" + passed + "</span></div>\n")
    head_parts.append("      <div class='badge failed'><span class='badge-label'>失败</span><span class='badge-value'>" + failed + "</span></div>\n")
    head_parts.append("      <div class='badge skipped'><span class='badge-label'>跳过</span><span class='badge-value'>" + skipped + "</span></div>\n")
    head_parts.append("      <div class='badge duration'><span class='badge-label'>耗时</span><span class='badge-value'>" + duration + "<span style='font-size:14px;font-weight:400;margin-left:4px;'>ms</span></span></div>\n")
    head_parts.append("    </div>\n")
    head_parts.append("    <div class='toolbar'>\n      <div class='filters'>\n        <label class='chip'><input type='radio' name='status-filter' id='f-all' value='all' checked /> 全部</label>\n        <label class='chip'><input type='radio' name='status-filter' id='f-passed' value='passed' /> 通过</label>\n        <label class='chip'><input type='radio' name='status-filter' id='f-failed' value='failed' /> 失败</label>\n        <label class='chip'><input type='radio' name='status-filter' id='f-skipped' value='skipped' /> 跳过</label>\n      </div>\n      <button id='btn-toggle-expand' title='展开/收起全部' onclick=\"window.toggleAllSteps && window.toggleAllSteps(this)\">展开全部</button>\n    </div>\n  </div>\n")

    # Cases
    body_cases = []
    for c in report.cases:
        body_cases.append(_build_case(c))

    tail = """
  <div class='footer'>由 Drun 生成</div>
</div>
</body></html>
"""

    html = "".join(head_parts) + "".join(body_cases) + tail
    p = Path(outfile)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
