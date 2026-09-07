#!/usr/bin/env python3
"""원고를 전달용 웹페이지(HTML) 하나로 묶는다.

drafts/ 아래의 모든 날짜를 담고, 페이지에서 날짜를 골라 볼 수 있게 한다.
인자로 날짜를 주면 그 날짜가 처음 열릴 때 선택된다 (기본값은 가장 최근 날짜).

사용:
    python3 scripts/build_page.py            # 최신 날짜가 열린 상태
    python3 scripts/build_page.py 2026-09-05 # 그 날짜가 열린 상태
결과:
    delivery/page.html   (Artifact 로 발행할 파일)
"""
import glob
import json
import os
import re
import sys

ALL_DATES = sorted(
    os.path.basename(d) for d in glob.glob("drafts/*")
    if os.path.isdir(d) and re.match(r"^\d{4}-\d{2}-\d{2}$", os.path.basename(d))
)
if not ALL_DATES:
    sys.exit("drafts/ 아래에 날짜 폴더가 없습니다.")

DATE = sys.argv[1] if len(sys.argv) > 1 else ALL_DATES[-1]
if DATE not in ALL_DATES:
    sys.exit(f"{DATE} 폴더가 없습니다. 가능한 날짜: {', '.join(ALL_DATES)}")

WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]


def parse(path):
    raw = open(path, encoding="utf-8").read()
    _, fm, rest = raw.split("---", 2)
    meta, key, buf = {}, None, []
    for line in fm.strip().split("\n"):
        if re.match(r"^\s*-\s", line) and key:
            meta.setdefault(key, []).append(line.strip()[2:].strip())
        elif ":" in line:
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            meta[key] = val if val else []
    body = rest.split("## 이미지 삽입 지시")[0].replace("## 본문", "").strip()
    images = re.findall(r"^\d+\.\s*(.+)$", rest.split("## 이미지 삽입 지시")[-1]
                        .split("## 태그")[0], re.M)
    tags = rest.split("## 태그")[-1].strip()
    blocks = [b.strip() for b in body.split("\n\n") if b.strip()]
    plain = re.sub(r"\s", "", re.sub(r"\[[^\]]*\]", "", body))
    return {
        "slot": meta.get("slot", "?"),
        "keyword": meta.get("keyword", ""),
        "target": meta.get("target", ""),
        "structure": meta.get("structure", ""),
        "titles": [
            {"type": s.split("|", 1)[0].strip(), "text": s.split("|", 1)[1].strip()}
            if "|" in s else {"type": "", "text": s}
            for s in meta.get("titles", [])
        ],
        "flags": meta.get("flags", []) if isinstance(meta.get("flags"), list) else [],
        "chars": len(plain),
        "blocks": len(blocks),
        "body": blocks,
        "images": images,
        "tags": tags,
    }


def weekday_of(date_str):
    y, m, d = (int(x) for x in date_str.split("-"))
    # Zeller 없이 datetime 사용
    import datetime
    return WEEKDAY[datetime.date(y, m, d).weekday()]


days = []
for ds in ALL_DATES:
    items = [parse(p) for p in sorted(glob.glob(f"drafts/{ds}/*.md"))]
    if not items:
        continue
    days.append({
        "date": ds,
        "weekday": weekday_of(ds),
        "drafts": items,
        "flags": sum(len(x["flags"]) for x in items),
    })
days.reverse()  # 최신이 앞으로

queue_ready = 0
if os.path.exists("keywords/queue.tsv"):
    for line in open("keywords/queue.tsv", encoding="utf-8").read().splitlines()[1:]:
        if line.split("\t")[-1:] == ["ready"]:
            queue_ready += 1

DATA = json.dumps({"selected": DATE, "days": days, "queueReady": queue_ready},
                  ensure_ascii=False)

HTML = """<title>보이스닥터 원고함</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nanum+Myeongjo:wght@700;800&family=Noto+Sans+KR:wght@400;500;700&family=IBM+Plex+Mono:wght@500&display=swap">
<style>
:root{
  --bg:#F3F5F2; --surface:#FFFFFF; --sunk:#EDF0EC;
  --ink:#191E1B; --muted:#5C635E; --faint:#858C87;
  --line:#DCE1DB; --line-strong:#C3CAC2;
  --accent:#1E5F58; --accent-ink:#0F3B36; --accent-soft:#E1EDEA;
  --warn:#8A5A0B; --warn-soft:#F7EFDC; --warn-line:#E0CB9C;
  --ok:#2C6B45; --ok-soft:#E3EFE6;
  --shadow:0 1px 2px rgba(20,32,26,.05),0 6px 20px -12px rgba(20,32,26,.28);
  --display:"Nanum Myeongjo",Georgia,"Apple SD Gothic Neo",serif;
  --body:"Noto Sans KR","Apple SD Gothic Neo",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#111512; --surface:#191E1B; --sunk:#141814;
    --ink:#E7EBE6; --muted:#9CA49E; --faint:#79817B;
    --line:#282F2A; --line-strong:#3A433C;
    --accent:#63B5AA; --accent-ink:#9BD3CA; --accent-soft:#16302C;
    --warn:#D8A64C; --warn-soft:#2B2317; --warn-line:#4A3A1C;
    --ok:#7FBE95; --ok-soft:#18291D;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px -12px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --bg:#111512; --surface:#191E1B; --sunk:#141814;
  --ink:#E7EBE6; --muted:#9CA49E; --faint:#79817B;
  --line:#282F2A; --line-strong:#3A433C;
  --accent:#63B5AA; --accent-ink:#9BD3CA; --accent-soft:#16302C;
  --warn:#D8A64C; --warn-soft:#2B2317; --warn-line:#4A3A1C;
  --ok:#7FBE95; --ok-soft:#18291D;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 6px 20px -12px rgba(0,0,0,.7);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);
  font-size:15px;line-height:1.75;-webkit-font-smoothing:antialiased}
.wrap{max-width:980px;margin:0 auto;padding:38px 22px 90px}

/* masthead */
.mast{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;
  gap:18px;padding-bottom:20px;border-bottom:2px solid var(--ink)}
.mast h1{font-family:var(--display);font-weight:800;font-size:33px;line-height:1.2;
  margin:0 0 6px;letter-spacing:-.01em;text-wrap:balance}
.mast .sub{color:var(--muted);font-size:13.5px;margin:0}
.stamp{font-family:var(--mono);font-size:12px;color:var(--muted);text-align:right;
  line-height:1.9;font-variant-numeric:tabular-nums}
.stamp b{display:block;font-size:19px;color:var(--ink);letter-spacing:.02em}

/* date picker */
.dates{display:flex;flex-wrap:wrap;gap:7px;margin:20px 0 0}
.dates button{appearance:none;cursor:pointer;font-family:var(--mono);font-size:12.5px;
  letter-spacing:.02em;padding:7px 12px;border-radius:2px;border:1px solid var(--line-strong);
  background:var(--surface);color:var(--muted);display:inline-flex;align-items:center;gap:7px;
  transition:background .12s,color .12s,border-color .12s}
.dates button:hover{border-color:var(--accent);color:var(--accent)}
.dates button[aria-current="true"]{background:var(--accent);border-color:var(--accent);
  color:#fff;font-weight:500}
.dates .wd{font-family:var(--body);font-size:11.5px;opacity:.75}
.dates .dot{width:5px;height:5px;border-radius:50%;background:var(--warn);flex:0 0 auto}
.dates button[aria-current="true"] .dot{background:#fff}
.dates .more{color:var(--faint);font-size:12px;align-self:center;padding-left:4px}
.dates button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* status strip */
.strip{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0}
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:2px;
  font-size:12.5px;font-weight:500;border:1px solid var(--line-strong);background:var(--surface)}
.pill.ok{background:var(--ok-soft);border-color:transparent;color:var(--ok)}
.pill.warn{background:var(--warn-soft);border-color:var(--warn-line);color:var(--warn)}
.pill .n{font-family:var(--mono);font-variant-numeric:tabular-nums}

/* how-to */
.howto{margin:26px 0 0;padding:16px 18px;background:var(--sunk);border-radius:3px;
  border-left:3px solid var(--accent)}
.howto h2{margin:0 0 8px;font-size:13px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--accent)}
.howto ol{margin:0;padding-left:19px;color:var(--muted);font-size:13.5px;line-height:1.85}
.howto b{color:var(--ink)}

/* spacing control */
.gapctl{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:22px 0 0;
  padding:13px 16px;border:1px solid var(--line);border-radius:3px;background:var(--surface)}
.gapctl .lbl{font-size:13px;font-weight:700}
.gapctl .hint{font-size:12.5px;color:var(--faint);flex:1 1 260px}
.seg{display:inline-flex;border:1px solid var(--line-strong);border-radius:2px;overflow:hidden}
.seg button{appearance:none;border:0;background:var(--surface);color:var(--muted);
  font-family:var(--mono);font-size:12.5px;padding:6px 13px;cursor:pointer}
.seg button + button{border-left:1px solid var(--line-strong)}
.seg button[aria-pressed="true"]{background:var(--accent);color:#fff}

/* article */
.art{margin:30px 0 0;background:var(--surface);border:1px solid var(--line);
  border-radius:4px;box-shadow:var(--shadow);overflow:hidden}
.art > header{padding:20px 22px 0}
.slotline{display:flex;flex-wrap:wrap;align-items:center;gap:9px;margin-bottom:13px}
.slot{font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;color:#fff;
  background:var(--accent);padding:3px 9px;border-radius:2px}
.kw{font-size:13px;font-weight:700}
.tgt{font-size:12.5px;color:var(--muted)}
.tgt::before{content:"·";margin-right:8px;color:var(--line-strong)}

.titles{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:3px;overflow:hidden}
.titles li{display:flex;align-items:center;gap:12px;background:var(--surface);
  padding:11px 13px}
.titles li:first-child{background:var(--accent-soft)}
.rank{font-family:var(--mono);font-size:11px;color:var(--faint);flex:0 0 42px;
  letter-spacing:.02em}
.tlen{font-family:var(--mono);font-size:11px;color:var(--faint);flex:0 0 auto;
  font-variant-numeric:tabular-nums}
.titles li:first-child .rank{color:var(--accent);font-weight:700}
.ttxt{flex:1;font-size:14.5px;line-height:1.5}
.titles li:first-child .ttxt{font-weight:700}

.metrics{display:flex;flex-wrap:wrap;gap:0;margin:16px 0 0;border-top:1px solid var(--line);
  border-bottom:1px solid var(--line)}
.metric{flex:1 1 140px;padding:11px 4px 11px 0}
.metric + .metric{padding-left:16px;border-left:1px solid var(--line)}
.metric .k{display:block;font-size:11px;letter-spacing:.05em;color:var(--faint);
  text-transform:uppercase}
.metric .v{font-family:var(--mono);font-size:16px;font-variant-numeric:tabular-nums}
.metric .v small{font-family:var(--body);font-size:11.5px;color:var(--faint);margin-left:3px}

.flagbox{margin:14px 0 0;padding:10px 13px;background:var(--warn-soft);
  border:1px solid var(--warn-line);border-radius:3px;font-size:13px;color:var(--warn)}
.flagbox b{display:block;margin-bottom:3px}

.bodywrap{margin:18px 0 0;border-top:1px solid var(--line)}
.bodybar{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;
  gap:10px;padding:12px 0 10px}
.bodybar h3{margin:0;font-size:12px;font-weight:700;letter-spacing:.07em;
  text-transform:uppercase;color:var(--faint)}
.preview{background:var(--sunk);border:1px solid var(--line);border-radius:3px;
  padding:16px 18px;max-height:330px;overflow:auto;font-size:14px;line-height:1.85}
.preview p{margin:0 0 13px}
.preview p:last-child{margin:0}
.preview p.ins{color:var(--accent);font-family:var(--mono);font-size:12.5px}
.preview p.sum{background:var(--accent-soft);padding:11px 13px;border-radius:3px;
  font-size:13px;color:var(--accent-ink)}

.tail{display:grid;grid-template-columns:1fr;gap:0;border-top:1px solid var(--line);
  margin-top:18px}
@media(min-width:680px){.tail{grid-template-columns:1.15fr 1fr}}
.tailbox{padding:15px 22px 18px}
.tail .tailbox + .tailbox{border-top:1px solid var(--line)}
@media(min-width:680px){.tail .tailbox + .tailbox{border-top:0;border-left:1px solid var(--line)}}
.tailbox h4{margin:0 0 9px;font-size:12px;font-weight:700;letter-spacing:.07em;
  text-transform:uppercase;color:var(--faint)}
.tailbox ol{margin:0;padding-left:18px;font-size:13px;color:var(--muted);line-height:1.8}
.tagline{font-size:13.5px;color:var(--muted);word-break:keep-all;line-height:1.9}
.art > .padded{padding:0 22px}
.art > .padded.last{padding-bottom:0}

/* buttons */
.btn{appearance:none;cursor:pointer;font-family:var(--body);font-size:12.5px;font-weight:700;
  border-radius:2px;border:1px solid var(--accent);background:transparent;color:var(--accent);
  padding:6px 13px;white-space:nowrap;transition:background .12s,color .12s}
.btn:hover{background:var(--accent-soft)}
.btn.solid{background:var(--accent);color:#fff}
.btn.solid:hover{opacity:.88}
.btn.copied{background:var(--ok);border-color:var(--ok);color:#fff}
.btn:focus-visible,.seg button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

footer.foot{margin:44px 0 0;padding-top:18px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--faint);display:flex;flex-wrap:wrap;gap:14px;
  justify-content:space-between}
footer.foot code{font-family:var(--mono);color:var(--muted)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
  <div class="mast">
    <div>
      <h1>보이스닥터 원고함</h1>
      <p class="sub">네이버 블로그 <b>blog.naver.com/voicedr</b> · 월·화 아침 3편 갱신</p>
    </div>
    <div class="stamp"><b id="d-date"></b><span id="d-sub">선택한 날짜</span></div>
  </div>

  <nav class="dates" id="dates" aria-label="원고 날짜 선택"></nav>

  <div class="strip" id="strip"></div>

  <div class="howto">
    <h2>붙여넣는 순서</h2>
    <ol>
      <li>원고 3편 중 오늘 올릴 것을 <b>고르기</b></li>
      <li>제목 후보 6개 중 하나를 골라 <b>복사</b> → 네이버 글쓰기 제목란에 붙여넣기</li>
      <li><b>본문 복사</b> → 스마트에디터 본문에 붙여넣기 (줄바꿈 그대로 들어갑니다)</li>
      <li>이미지 지시에 따라 사진과 비포&amp;애프터 영상을 자리에 넣기</li>
      <li>태그 복사 후 발행 또는 예약</li>
    </ol>
  </div>

  <div class="howto" style="border-left-color:var(--line-strong)">
    <h2 style="color:var(--muted)">제목 후보 6개를 나눈 기준</h2>
    <p style="margin:0;color:var(--muted);font-size:13.5px;line-height:1.85">
      네이버는 VIEW 탭 대신 <b>스마트블록</b>으로 검색 의도별 결과를 나눕니다.
      같은 키워드도 의도가 갈리므로 유형이 다른 6개를 뽑았습니다.
      <b>원인형</b>은 지금 상위노출 중인 글들의 형태라 1순위로 두었고,
      나머지 5개는 아직 잡지 못한 블록을 노리는 확장용입니다.
      전부 메인 키워드를 맨 앞에 1회만 넣고 20~30자로 맞췄습니다.
    </p>
  </div>

  <div class="gapctl">
    <span class="lbl">줄바꿈 간격</span>
    <span class="hint">문단 사이 빈 줄 개수입니다. 복사할 때 이 간격으로 들어갑니다.</span>
    <span class="seg" id="seg">
      <button type="button" data-gap="2">좁게</button>
      <button type="button" data-gap="4" aria-pressed="true">기본</button>
      <button type="button" data-gap="6">넓게</button>
    </span>
  </div>

  <main id="arts"></main>

  <footer class="foot">
    <span>원고·키워드 이력은 저장소 <code>drafts/</code> 와 <code>keywords/used.tsv</code> 에 쌓입니다.</span>
    <span id="qinfo"></span>
  </footer>
</div>

<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('payload').textContent);
  var gap = 4;
  try{ var s = localStorage.getItem('vd-gap'); if(s) gap = +s; }catch(e){}

  document.getElementById('d-date').textContent = D.date;

  function el(t,c,x){var n=document.createElement(t); if(c)n.className=c;
    if(x!=null)n.textContent=x; return n;}

  function copy(text,btn){
    var done=function(){var o=btn.textContent; btn.textContent='복사됨';
      btn.classList.add('copied');
      setTimeout(function(){btn.textContent=o; btn.classList.remove('copied');},1400);};
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done,function(){fallback(text,done);});
    } else { fallback(text,done); }
  }
  function fallback(text,done){
    var ta=document.createElement('textarea'); ta.value=text;
    ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta);
    ta.select();
    try{ document.execCommand('copy'); done(); }catch(e){}
    document.body.removeChild(ta);
  }
  function bodyText(d){
    return d.body.join('\\n'.repeat(gap+1));
  }

  var day = D.days.filter(function(x){return x.date===D.selected;})[0] || D.days[0];

  function paintHeader(){
    document.getElementById('d-date').textContent = day.date;
    document.getElementById('d-sub').textContent =
      (day===D.days[0] ? '최신 원고' : '지난 원고') + ' · ' + day.weekday + '요일';
    var strip = document.getElementById('strip');
    strip.textContent='';
    [['ok','원고 '+day.drafts.length+'편'],
     ['ok','유사문서 검사 통과'],
     [day.flags?'warn':'ok', day.flags? '검수 필요 '+day.flags+'건' : '검수 신호 없음'],
     ['','키워드 잔여 '+D.queueReady+'개']].forEach(function(pz){
      strip.appendChild(el('span','pill '+pz[0],pz[1]));
    });
  }
  document.getElementById('qinfo').textContent='전체 '+D.days.length+'일치 보관 중';

  // date picker
  var datesEl=document.getElementById('dates');
  D.days.forEach(function(dd){
    var b=el('button'); b.type='button';
    b.appendChild(document.createTextNode(dd.date.slice(5)));
    b.appendChild(el('span','wd',dd.weekday));
    if(dd.flags) b.appendChild(el('span','dot'));
    b.addEventListener('click',function(){
      day=dd; D.selected=dd.date;
      [].forEach.call(datesEl.children,function(x){
        x.setAttribute('aria-current', x===b ? 'true':'false');});
      paintHeader(); renderDay();
      document.getElementById('arts').scrollIntoView({block:'start',
        behavior: matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'});
    });
    b.setAttribute('aria-current', dd===day ? 'true':'false');
    datesEl.appendChild(b);
  });
  paintHeader();

  // gap segment
  var seg=document.getElementById('seg');
  function paint(){ [].forEach.call(seg.children,function(b){
      b.setAttribute('aria-pressed', (+b.dataset.gap===gap)?'true':'false'); }); }
  paint();
  seg.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    gap=+b.dataset.gap; paint();
    try{ localStorage.setItem('vd-gap',gap); }catch(err){}
  });

  var host=document.getElementById('arts');
  function renderDay(){
  host.textContent='';
  day.drafts.forEach(function(d){
    var art=el('article','art'), h=el('header');

    var line=el('div','slotline');
    line.appendChild(el('span','slot','원고 '+d.slot));
    line.appendChild(el('span','kw',d.keyword));
    line.appendChild(el('span','tgt',d.target));
    h.appendChild(line);

    var ul=el('ul','titles');
    d.titles.forEach(function(t,i){
      var li=el('li');
      li.appendChild(el('span','rank',t.type||((i+1)+'순위')));
      li.appendChild(el('span','ttxt',t.text));
      li.appendChild(el('span','tlen',t.text.length+'자'));
      var b=el('button','btn','복사');
      b.type='button';
      b.addEventListener('click',function(){copy(t.text,b);});
      li.appendChild(b); ul.appendChild(li);
    });
    h.appendChild(ul);

    var m=el('div','metrics');
    [['글자수',d.chars,'자 (공백 제외)'],['줄바꿈 블록',d.blocks,'개'],
     ['제목 후보',d.titles.length,'개 (유형별)']].forEach(function(x){
      var w=el('div','metric');
      w.appendChild(el('span','k',x[0]));
      var v=el('span','v',String(x[1]));
      var sm=el('small',null,x[2]); v.appendChild(sm); w.appendChild(v); m.appendChild(w);
    });
    h.appendChild(m);

    if(d.flags.length){
      var f=el('div','flagbox');
      f.appendChild(el('b',null,'발행 전 확인해 주세요'));
      f.appendChild(document.createTextNode(d.flags.join(' / ')));
      h.appendChild(f);
    }

    var bw=el('div','bodywrap');
    var bar=el('div','bodybar');
    bar.appendChild(el('h3',null,'본문'));
    var cb=el('button','btn solid','본문 복사'); cb.type='button';
    cb.addEventListener('click',function(){copy(bodyText(d),cb);});
    bar.appendChild(cb); bw.appendChild(bar);

    var pv=el('div','preview');
    d.body.forEach(function(p){
      var cls = /^\\[접기/.test(p) ? 'sum' : (/^\\[/.test(p) ? 'ins' : '');
      pv.appendChild(el('p',cls,p));
    });
    bw.appendChild(pv);
    h.appendChild(bw);
    art.appendChild(h);
    h.className='padded';

    var tail=el('div','tail');
    var t1=el('div','tailbox');
    t1.appendChild(el('h4',null,'이미지 삽입 위치'));
    var ol=el('ol');
    d.images.forEach(function(s){ ol.appendChild(el('li',null,s)); });
    t1.appendChild(ol); tail.appendChild(t1);

    var t2=el('div','tailbox');
    var hd=el('h4',null,'태그'); t2.appendChild(hd);
    t2.appendChild(el('p','tagline',d.tags));
    var tb=el('button','btn','태그 복사'); tb.type='button';
    tb.addEventListener('click',function(){copy(d.tags,tb);});
    t2.appendChild(tb); tail.appendChild(t2);

    art.appendChild(tail);
    host.appendChild(art);
  });
  }
  renderDay();
})();
</script>
"""

os.makedirs("delivery", exist_ok=True)
open("delivery/page.html", "w", encoding="utf-8").write(HTML.replace("__DATA__", DATA))
sel = [d for d in days if d["date"] == DATE][0]
print(f"delivery/page.html 생성 — 보관 {len(days)}일치, "
      f"열릴 날짜 {DATE}({sel['weekday']}) 원고 {len(sel['drafts'])}편, "
      f"검수 신호 {sel['flags']}건")
