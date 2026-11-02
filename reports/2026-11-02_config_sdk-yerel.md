# SSH Sunucu Yapılandırma Denetimi — samples/sshd_config

**Tarih:** 2026-11-02 · **Skill:** config-audit · **Hazırlayan:** agent

## Kapsam
- Girdi: `samples/sshd_config` (OpenSSH `sshd_config`, örnek/zayıf yapılandırma; 12 satır, 10 etkin yönerge)
- Kontrol listesi: config-audit skill'i — OpenSSH sshd_config (8 madde)
- Sayım: Uyumlu + Uyumsuz = uygulanan madde sayısı (8). Uyumlu: 2 · Uyumsuz: 6.
- Kapsam dışı: Dosya değiştirilmedi; servis yeniden başlatma, güvenlik duvarı ve canlı sunucu erişimi yapılmadı. Yorum satırları (`#`, satır 1 ve 3) etkin ayar sayılmadı. Sunucudaki OpenSSH sürümü girdide yer almıyor.
- Not: Yönlendirme, ölü bağlantı tespiti, bağlantı limitleri, kayıt düzeyi ve şifreleme algoritmaları 8 maddelik listenin dışındadır; "Ek sertleştirme bulguları" başlığında ayrıca verilmiş ve 8'lik sayıma dahil edilmemiştir.

## Bulgular

### Kontrol listesi — 8 madde

Uyumsuz (6):
- [OLGU] `PermitRootLogin yes` (satır 4) — root hesabı SSH ile doğrudan oturum açabiliyor. Satır 3'teki `#PermitRootLogin prohibit-password` yorum satırıdır, etkisi yoktur. Beklenen: `no` (veya `prohibit-password`).
- [ÖNERİ] `PermitRootLogin no` olarak ayarlayın; yönetim yetkili bir kullanıcı + `sudo` üzerinden yapılsın.
- [OLGU] `PasswordAuthentication yes` (satır 6) — parola ile kimlik doğrulama açık; kaba kuvvet (brute-force) ve sızdırılmış parola riskini artırır. Beklenen: `no`. Ayrıca `UsePAM yes` (satır 11) etkin ve `KbdInteractiveAuthentication` satırı yok (varsayılan: `yes`); bu yüzden yalnızca `PasswordAuthentication no` yapılsa bile parola PAM üzerinden klavye-etkileşimli (keyboard-interactive) yöntemle sorulmaya devam edebilir.
- [ÖNERİ] `PasswordAuthentication no` yapın ve `KbdInteractiveAuthentication no` ekleyin (OpenSSH 8.7 öncesinde eşdeğeri `ChallengeResponseAuthentication no`); böylece yalnızca açık anahtar (public key) doğrulaması kalır.
- [OLGU] `MaxAuthTries 6` (satır 8) — bağlantı başına 6 deneme. Beklenen: 3–4.
- [ÖNERİ] `MaxAuthTries 3` (veya 4) olarak düşürün.
- [OLGU] `LoginGraceTime 120` (satır 9) — kimlik doğrulama için 120 sn tanınıyor; yarım kalmış bağlantılar birikip kaynak tüketebilir. Beklenen: ≤ 60.
- [ÖNERİ] `LoginGraceTime 30` (veya ≤ 60) olarak ayarlayın.
- [OLGU] `X11Forwarding yes` (satır 10) — X11 yönlendirme açık; sunucuda gerekmiyorsa saldırı yüzeyini genişletir. Beklenen: `no`.
- [ÖNERİ] `X11Forwarding no` olarak ayarlayın.
- [OLGU] `AllowUsers` / `AllowGroups` tanımlı değil (Kanıt: eşleşme sayısı 0) — SSH erişimi belirli kullanıcı/gruplarla sınırlanmamış. Beklenen: tanımlı.
- [ÖNERİ] Yalnızca yetkili hesapları listeleyen bir `AllowUsers` ya da `AllowGroups` yönergesi ekleyin (ör. `AllowGroups ssh-users`).

Uyumlu (2):
- [OLGU] `PubkeyAuthentication yes` (satır 5) — açık anahtar doğrulama etkin (beklenen: `yes`).
- [OLGU] `PermitEmptyPasswords no` (satır 7) — boş parolayla oturum açma kapalı (beklenen: `no`).

### Ek sertleştirme bulguları (8'lik kontrol listesi dışında)
- [OLGU] `AllowTcpForwarding` ve `AllowAgentForwarding` satırları yok (varsayılan: ikisi de `yes`) — TCP ve SSH agent yönlendirme açık; ele geçirilmiş bir sunucuda yanal hareket (pivoting) ve yönlendirilen agent soketinin kötüye kullanımı mümkün.
- [ÖNERİ] İhtiyaç yoksa `AllowTcpForwarding no` ve `AllowAgentForwarding no` ekleyin.
- [OLGU] `ClientAliveInterval` / `ClientAliveCountMax` satırları yok (varsayılan: `ClientAliveInterval 0`) — kopmuş istemci bağlantıları SSH katmanında tespit edilmiyor.
- [ÖNERİ] `ClientAliveInterval 300` ve `ClientAliveCountMax 2` ekleyin; gerçek boşta zaman aşımı için (OpenSSH ≥ 9.2) `ChannelTimeout session=15m` ve `UnusedConnectionTimeout 15m` kullanın (süreler kurum politikasına göre).
- [OLGU] `MaxStartups` ve `MaxSessions` satırları yok — varsayılanlar geçerli (`MaxStartups 10:30:100`, `MaxSessions 10`).
- [ÖNERİ] `MaxStartups 10:30:60` ve ihtiyaca göre `MaxSessions` 2–4 ayarlayın.
- [OLGU] `LogLevel` satırı yok (varsayılan: `INFO`).
- [ÖNERİ] `LogLevel VERBOSE` ekleyin; oturum açan anahtarın parmak izi kayda geçer, denetim kolaylaşır.
- [OLGU] `Ciphers`, `MACs`, `KexAlgorithms` satırları yok — algoritmalar sürümün varsayılanına bırakılmış.
- [DOĞRULANMAMIŞ] Varsayılan algoritma listesi OpenSSH sürümüne bağlıdır; sürüm girdide olmadığı için zayıf algoritma olup olmadığı bu dosyadan söylenemez. Sunucuda `sshd -T | grep -iE '^(ciphers|macs|kexalgorithms)'` çıktısıyla kontrol edilmeli; Terrapin (CVE-2023-48795) koruması için OpenSSH ≥ 9.6 önerilir.
- [OLGU] `Port 22` (satır 2) — standart port. Port değiştirmek yalnızca otomatik tarama gürültüsünü azaltır; tek başına güvenlik önlemi değildir.
- [DOĞRULANMAMIŞ] Sürüme bağlı öneriler (`KbdInteractiveAuthentication` adı ≥ 8.7, `ChannelTimeout`/`UnusedConnectionTimeout` ≥ 9.2) uygulanmadan önce `sshd -V` ile sürüm ve `sshd -t` ile yapılandırma testi yapılmalıdır.

## Kanıt
- `samples/sshd_config:1` — `# Örnek (zayıf) OpenSSH sunucu yapılandırması — config-audit skill'ini denemek için` (yorum)
- `samples/sshd_config:2` — `Port 22`
- `samples/sshd_config:3` — `#PermitRootLogin prohibit-password` (yorum, etkisiz)
- `samples/sshd_config:4` — `PermitRootLogin yes`
- `samples/sshd_config:5` — `PubkeyAuthentication yes`
- `samples/sshd_config:6` — `PasswordAuthentication yes`
- `samples/sshd_config:7` — `PermitEmptyPasswords no`
- `samples/sshd_config:8` — `MaxAuthTries 6`
- `samples/sshd_config:9` — `LoginGraceTime 120`
- `samples/sshd_config:10` — `X11Forwarding yes`
- `samples/sshd_config:11` — `UsePAM yes`
- `samples/sshd_config:12` — `Subsystem sftp /usr/lib/openssh/sftp-server`
- Bulunmayan yönergeler (komut → çıktı):
  - `grep -ciE '^\s*allow(users|groups)' samples/sshd_config` → `0`
  - `grep -ciE '^\s*KbdInteractiveAuthentication' samples/sshd_config` → `0`
  - `grep -ciE '^\s*ChallengeResponseAuthentication' samples/sshd_config` → `0`
  - `grep -ciE '^\s*AllowAgentForwarding' samples/sshd_config` → `0`
  - `grep -ciE '^\s*AllowTcpForwarding' samples/sshd_config` → `0`
  - `grep -ciE '^\s*ClientAlive' samples/sshd_config` → `0`
  - `grep -ciE '^\s*(MaxStartups|MaxSessions)' samples/sshd_config` → `0`
  - `grep -ciE '^\s*LogLevel' samples/sshd_config` → `0`
  - `grep -ciE '^\s*(Ciphers|MACs|KexAlgorithms)' samples/sshd_config` → `0`
- Dosya boyutu: `wc -l < samples/sshd_config` → `12`; etkin satır sayısı `grep -cvE '^\s*(#|$)' samples/sshd_config` → `10`

## Doğrulama Durumu
KABUL — Tüm [OLGU] bulguları dosyadaki birebir satırlara veya yukarıdaki grep çıktılarına dayanıyor; 8 maddelik sayım tutarlı (Uyumlu 2 + Uyumsuz 6 = 8). Sürüme bağlı konular [DOĞRULANMAMIŞ] olarak işaretlendi.

## Reviewer Kararı
BEKLİYOR — reviewer henüz çalışmadı.
