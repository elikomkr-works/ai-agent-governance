"""Müşteri teslimini (Markdown) PDF'e çevirir.

Kullanım:
    python tools/to_pdf.py deliverables/<dosya>.md [-o <çıktı.pdf>] [--html]

Teslim belgesi müşteriye PDF olarak gider; kaynak her zaman @deliverables
altındaki Markdown dosyasıdır. Betik hiçbir içerik üretmez, eklemez ya da
çıkarmaz: yalnızca biçimler.

  - Frontmatter (dil, kaynak_rapor, musteri, teslim_tarihi) izlenebilirlik
    verisidir ve müşteriye giden dosyada görünmez (CLAUDE.md → "Customer
    deliverable"); betik onu çıkarır ve yalnızca gövdeyi basar.
  - Etiketler (FACT/FIX/CHECK ve dilin kendi karşılıkları) renkli nişan
    olarak basılır; metin değişmez.
  - PDF, Chrome/Edge headless ile üretilir (Windows'ta ek paket gerekmez).
    Chrome'a mutlak bir file:/// URL'i verilir; çıplak dosya adını Chrome
    makine adı sanar.

Çıktı, aksi belirtilmezse Markdown'ın yanında aynı adla <dosya>.pdf olur.
Dosya varsa üzerine yazılır; yeniden çalıştırmak bedavadır.
Hata varsa çıkış kodu 1'dir.
"""
import argparse
import html as html_mod
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".claude" / "hooks"))
import govlib  # noqa: E402

# Teslim şablonlarıyla aynı görünüm; portföy örnekleri de bu CSS'i kullanır.
CSS = """
  :root { --ink:#1b1f24; --muted:#5b6470; --line:#dde2e8; --bad:#b42318; --ok:#067647; --info:#175cd3; --warn:#b54708; }
  @page { size: A4; margin: 16mm 14mm; }
  body { font: 10.5pt/1.45 "Segoe UI", Arial, sans-serif; color: var(--ink); background:#fff; margin:0; }
  @media screen { body { padding: 28px 40px; } }
  h1 { font-size: 19pt; margin: 0 0 4px; border-bottom: 3px solid var(--ink); padding-bottom: 8px; }
  h2 { font-size: 13pt; margin: 18px 0 6px; border-bottom: 1px solid var(--line); padding-bottom: 3px; }
  h3 { font-size: 11pt; margin: 12px 0 4px; }
  p { margin: 6px 0; }
  ul, ol { margin: 4px 0; padding-left: 18px; } li { margin: 3px 0; }
  code { font-family: Consolas, monospace; font-size: 9.2pt; background:#f3f5f7; padding:0 3px; border-radius:2px; }
  table { border-collapse: collapse; width:100%; font-size:9.2pt; margin:6px 0; }
  td, th { border:1px solid var(--line); padding:4px 6px; text-align:left; vertical-align:top; }
  th { background:#f3f5f7; }
  pre { background:#f3f5f7; border:1px solid var(--line); border-radius:6px; padding:8px 10px; font-family: Consolas, monospace; font-size:8.6pt; line-height:1.4; white-space:pre-wrap; word-break:break-all; break-inside: avoid; }
  .badge { display:inline-block; font-size:8pt; font-weight:700; padding:1px 6px; border-radius:3px; color:#fff; vertical-align:1px; }
  .b-fact { background: var(--info); } .b-fix { background: var(--ok); } .b-check { background: var(--warn); }
  .sev-critical, .sev-kritik { color:#7a1511; font-weight:700; }
  .sev-high, .sev-yuksek { color: var(--bad); font-weight:700; }
  .sev-medium, .sev-orta { color: var(--warn); font-weight:700; }
"""

# Nişan olarak basılacak etiketler: deliverable_languages.json'daki her dilin
# fact/action/check etiketleri. Tablo oradan okunur; burada liste tutulmaz.
BADGE_CLASS = {"fact_label": "b-fact", "action_label": "b-fix", "check_label": "b-check"}


def badge_labels():
    data = govlib.load_json(govlib.path("deliverable_languages"))
    labels = {}
    for block in data["languages"].values():
        for key, cls in BADGE_CLASS.items():
            if block.get(key):
                labels[block[key]] = cls
    # Uzun etiket kısa olanın içinde geçebilir; uzundan kısaya eşleştir.
    return sorted(labels.items(), key=lambda kv: -len(kv[0]))


def split_frontmatter(text):
    """(frontmatter satırları, gövde). Frontmatter yoksa gövde metnin tamamıdır."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], "\n".join(lines[i + 1:])
    return [], text


def inline(text, labels):
    """Satır içi Markdown → HTML.

    Kod parçaları ilk adımda yer tutucuya alınır: kalın yazı ya da etiket
    nişanı kodun içine giremez, ama bir `**kalın**` çifti kod parçasının iki
    yanına düşerse de bozulmaz (teslim şablonlarında sık görülen durum).
    """
    spans = []

    def stash(m):
        spans.append(f"<code>{html_mod.escape(m.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    stashed = re.sub(r"`([^`]+)`", stash, text)
    esc = html_mod.escape(stashed)
    esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
    esc = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', esc)
    for label, cls in labels:
        esc = re.sub(rf"(?<![\w-]){re.escape(label)}(?![\w-])",
                     f'<span class="badge {cls}">{label}</span>', esc)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], esc)


def cells(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in row.split("|")]


def is_separator(row):
    return bool(row.strip()) and all(re.fullmatch(r":?-{2,}:?", c) for c in cells(row) if c != "")


def to_html_body(body, labels):
    """Teslim şablonlarının kullandığı Markdown alt kümesini HTML'e çevirir:
    başlıklar, paragraflar, madde listeleri, tablolar, çitli kod blokları."""
    lines = body.replace("\r\n", "\n").split("\n")
    out, i = [], 0
    para, lst = [], []

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para), labels)}</p>")
            para.clear()
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x, labels)}</li>" for x in lst) + "</ul>")
            lst.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush()
            i += 1
            block = []
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            out.append(f"<pre>{html_mod.escape(chr(10).join(block))}</pre>")
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            flush()
            level = len(heading.group(1))
            out.append(f"<h{level}>{inline(heading.group(2), labels)}</h{level}>")
            i += 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]):
            flush()
            head = cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            thead = "".join(f"<th>{inline(c, labels)}</th>" for c in head)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline(c, labels)}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f"<table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table>")
            continue
        item = re.match(r"^\s*[-*]\s+(.*)$", line)
        if item:
            if para:
                out.append(f"<p>{inline(' '.join(para), labels)}</p>")
                para.clear()
            lst.append(item.group(1))
            i += 1
            continue
        if not line.strip():
            flush()
            i += 1
            continue
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x, labels)}</li>" for x in lst) + "</ul>")
            lst.clear()
        para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out)


def build_html(md_text, title):
    labels = badge_labels()
    _, body = split_frontmatter(md_text)
    return (f"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{html_mod.escape(title)}</title>\n<style>{CSS}</style></head>\n<body>\n"
            f"{to_html_body(body, labels)}\n</body></html>\n")


def show(p):
    """Yazdırmak için yol: proje içindeyse köke göre, değilse mutlak."""
    try:
        return str(Path(p).relative_to(ROOT))
    except ValueError:
        return str(p)


def find_browser():
    """Chrome ya da Edge; CHROME ortam değişkeni her şeyin önündedir."""
    env = os.environ.get("CHROME")
    if env and Path(env).exists():
        return env
    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    bases = [os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""),
             os.environ.get("LOCALAPPDATA", "")]
    rels = [r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe"]
    for base in bases:
        for rel in rels:
            if base and (Path(base) / rel).exists():
                return str(Path(base) / rel)
    return None


def main():
    govlib.setup_io()
    ap = argparse.ArgumentParser(description="Müşteri teslimini PDF'e çevirir.")
    ap.add_argument("markdown", help="Teslim dosyası (@deliverables altındaki .md)")
    ap.add_argument("-o", "--out", help="PDF yolu (varsayılan: Markdown'ın yanında aynı ad)")
    ap.add_argument("--html", action="store_true", help="PDF üretmeden yalnızca HTML yaz")
    args = ap.parse_args()

    src = Path(args.markdown)
    if not src.is_absolute():
        src = ROOT / src
    if not src.is_file():
        print(f"HATA: dosya yok: {args.markdown}", file=sys.stderr)
        return 1

    md_text = src.read_text(encoding="utf-8")
    front, body = split_frontmatter(md_text)
    heading = re.search(r"^#\s+(.*)$", body, re.M)
    title = heading.group(1).strip() if heading else src.stem
    out_html = build_html(md_text, title)

    if args.html:
        target = Path(args.out) if args.out else src.with_suffix(".html")
        if not target.is_absolute():
            target = ROOT / target
        target.write_text(out_html, encoding="utf-8")
        print(f"HTML yazıldı: {show(target)}")
        return 0

    browser = find_browser()
    if not browser:
        print("HATA: Chrome/Edge bulunamadı. CHROME ortam değişkenine tam yolu yazın "
              "ya da --html ile yalnızca HTML üretip tarayıcıdan yazdırın.", file=sys.stderr)
        return 1

    target = Path(args.out) if args.out else src.with_suffix(".pdf")
    if not target.is_absolute():
        target = ROOT / target

    # Chrome, geçici HTML'i mutlak file:/// URL'i olarak alır.
    with tempfile.TemporaryDirectory() as tmp:
        tmp_html = Path(tmp) / (src.stem + ".html")
        tmp_html.write_text(out_html, encoding="utf-8")
        cmd = [browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
               f"--print-to-pdf={target}", tmp_html.as_uri()]
        proc = subprocess.run(cmd, capture_output=True, text=True)
    if not target.is_file():
        print(f"HATA: PDF üretilemedi (çıkış {proc.returncode}).\n{proc.stderr[-2000:]}",
              file=sys.stderr)
        return 1

    size = target.stat().st_size
    kaynak = next((l.split(":", 1)[1].strip() for l in front if l.startswith("kaynak_rapor:")), "—")
    print(f"PDF yazıldı: {show(target)} ({size // 1024} KB)")
    print(f"Kaynak rapor: {kaynak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
