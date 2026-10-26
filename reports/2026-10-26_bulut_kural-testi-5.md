# Bulut kural testi (5. tur) — Permission denetim kaydı

**Tarih:** 2026-10-26 · **Skill:** kabul-testi (skill kullanılmadı) · **Hazırlayan:** agent

## Kapsam
- Girdi: `governance/audit.jsonl`, `.claude/hooks/denial_log.py` (PR #6) davranışı
- Kapsam dışı: D14'ün alt agent içindeki Edit(/.git/config) reddi — alt agent hiç başlatılamadığı için denenemedi

## Bulgular
- [OLGU] Hazırlık: son commit `97b3fa8` (PR #6 birleşti); `tests/test_governance.py` "tüm testler geçti"; başlangıçta `"event": "Permission"` sayısı 0.
- [OLGU] D4: `curl -sI https://example.com` Policy Gate tarafından DENY edildi (ASK → bulutta DENY). Kayıt 403. satırda `PreToolUse`/`deny` olarak yazıldı. Beklenen buydu.
- [OLGU] D14 — BEKLENENDEN FARKLI: `general-purpose` alt agent'ı başlatılamadı. Policy Gate (`PreToolUse:Agent`) "agent reyestrinde kayıtlı değil" gerekçesiyle ASK→DENY verdi (kayıt 404). Alt agent hiç çalışmadığı için Edit(/.git/config) denemesi yapılmadı; talimat gereği başka yoldan denenmedi.
- [OLGU] D15 — BEKLENENDEN FARKLI: `grep -n '"event": "Permission"' governance/audit.jsonl | tail -5` çıktısı boş; Permission satırı yok (başlangıçtan bir fazla beklenirdi).
- [OLGU] D16: Permission sayısı 0 (D15 ile tutarlı); curl içeren Permission satırı sayısı 0 → beklenen sonuç sağlandı (Gate reti Permission olarak tekrar yazılmadı).
- [OLGU] D9: `python3 tools/verify_audit.py` → "408 kayıt, 0 hata".
- [DOĞRULANMAMIŞ] Ana amaç (izin kuralı retinin Stop/SubagentStop anında `Permission` olarak yazılması) bu turda test edilemedi; `denial_log.py`'nin çalıştığı ya da çalışmadığı hakkında sonuç çıkarılamaz.
- [ÖNERİ] `general-purpose` agent'ı `governance/agents_registry.json`'a kayıtlı değil; D14'ü yeniden denemek için ya kaydı kullanıcı onayıyla eklemek ya da alt agent'ı kayıtlı bir tiple (ör. `log-analyst`, ancak aracı Edit içermez) çalıştırmak gerekir. Karar kullanıcıya aittir.

## Kanıt
- `governance/audit.jsonl:403` — `"tool": "Bash", "decision": "deny", "reason": "ASK: Kapsam dışı adrese HTTP isteği: example.com. | DENY: Bulut oturumunda onaylayan kullanıcı yok; onay gerektiren işlem reddedildi.", "detail": "command=curl -sI https://example.com"`
- `governance/audit.jsonl:404` — `"tool": "Agent", "decision": "deny", "reason": "ASK: 'general-purpose' agent reyestrinde kayıtlı değil (governance/agents_registry.json). | DENY: Bulut oturumunda onaylayan kullanıcı yok; onay gerektiren işlem reddedildi."`
- `git log --oneline -1` → `97b3fa8 Merge pull request #6 from elikomkr-works/denetim-reddi-kaydi`
- `python3 tests/test_governance.py 2>&1 | tail -3` → `GEÇTİ  kurulum betiği her durumda 0 ile çıkar` / `Sonuç: tüm testler geçti`
- `grep -c '"event": "Permission"' governance/audit.jsonl` (başlangıç) → `0`
- D4 hata metni: `[Policy Gate] ASK: Kapsam dışı adrese HTTP isteği: example.com. | DENY: Bulut oturumunda onaylayan kullanıcı yok; onay gerektiren işlem reddedildi.`
- D14 hata metni: `[Policy Gate] ASK: 'general-purpose' agent reyestrinde kayıtlı değil (governance/agents_registry.json). | DENY: Bulut oturumunda onaylayan kullanıcı yok; onay gerektiren işlem reddedildi.`
- D15 `grep -n '"event": "Permission"' governance/audit.jsonl | tail -5` → (çıktı yok)
- D16 `grep -c '"event": "Permission"' governance/audit.jsonl` → `0`
- D16 `grep '"event": "Permission"' governance/audit.jsonl | grep -c curl` → `0`
- D9 `python3 tools/verify_audit.py` → `governance/audit.jsonl: 408 kayıt, 0 hata`

## Doğrulama Durumu
BELİRSİZ — D4, D16 ve D9 beklenenle uyumlu; ancak D14 Gate tarafından engellendiği için D15 doğrulanamadı ve Permission kaydı özelliği bu turda test edilemedi.
