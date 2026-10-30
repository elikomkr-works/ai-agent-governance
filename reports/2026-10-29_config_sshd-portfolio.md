# SSH Sunucu Yapılandırma Denetimi — Portföy Örneği

**Tarih:** 2026-10-29 · **Hazırlayan:** Güvenlik analisti

## Kapsam
- Girdi: `examples/ornek-sshd_config` (OpenSSH `sshd_config`, sentetik/portföy örneği; 16 satır, 15 etkin yönerge)
- Kontrol listesi: OpenSSH temel sertleştirme (8 madde)
- Sayım: Uyumlu + Uyumsuz = uygulanan madde sayısı (8). Uyumlu: 1 · Uyumsuz: 7.
- Kapsam dışı: Dosya değiştirilmedi; servis yeniden başlatma, güvenlik duvarı ve canlı sunucu erişimi yapılmadı. Yorum satırları (`#`) etkin ayar sayılmadı. Sunucudaki OpenSSH sürümü girdide yer almıyor.
- Not: Şifreleme (Ciphers) ve MAC algoritmaları, ölü bağlantı tespiti/boşta zaman aşımı, yönlendirme, eskimiş yönergeler ve bağlantı limitleri 8 maddelik kontrol listesinin dışındadır; "Ek sertleştirme bulguları" başlığı altında ayrıca verilmiş ve 8'lik sayıma dahil edilmemiştir.

## Bulgular

### Kontrol listesi — 8 madde

Uyumsuz (7):
- [OLGU] `PermitRootLogin yes` — root hesabının SSH ile doğrudan oturum açmasına izin veriyor. Beklenen: `no` (veya `prohibit-password`).
- [ÖNERİ] `PermitRootLogin no` olarak ayarlayın; yönetim yetkili bir kullanıcı + `sudo` üzerinden yapılsın.
- [OLGU] `PasswordAuthentication yes` — parola ile kimlik doğrulama açık; kaba kuvvet (brute-force) ve sızdırılmış parola riskini artırır. Beklenen: `no`. Ayrıca `UsePAM yes` etkin ve `KbdInteractiveAuthentication` satırı yok (varsayılan: `yes`); bu nedenle yalnızca `PasswordAuthentication no` yapılsa bile parola, PAM üzerinden klavye-etkileşimli (keyboard-interactive) yöntemle sorulmaya devam eder.
- [ÖNERİ] `PasswordAuthentication no` yapın ve `KbdInteractiveAuthentication no` satırını ekleyin (OpenSSH 8.7 öncesi sürümlerde eşdeğeri `ChallengeResponseAuthentication no`); böylece yalnızca açık anahtar (public key) doğrulaması kalır.
- [OLGU] `PermitEmptyPasswords yes` — boş parolalı hesaplarla oturum açmaya izin veriyor; kritik risk. Beklenen: `no`.
- [ÖNERİ] `PermitEmptyPasswords no` olarak ayarlayın.
- [OLGU] `MaxAuthTries 10` — bağlantı başına 10 deneme, kaba kuvvet denemelerini kolaylaştırır. Beklenen: 3–4.
- [ÖNERİ] `MaxAuthTries 3` (veya 4) olarak düşürün.
- [OLGU] `X11Forwarding yes` — X11 yönlendirme açık; sunucuda gerekli değilse saldırı yüzeyini genişletir. Beklenen: `no`.
- [ÖNERİ] `X11Forwarding no` olarak ayarlayın.
- [OLGU] `LoginGraceTime 120` — kimlik doğrulama için tanınan 120 sn, yarım kalmış bağlantıların birikmesine ve kaynak tüketimine yol açabilir. Beklenen: ≤ 60.
- [ÖNERİ] `LoginGraceTime 30` (veya ≤ 60) olarak ayarlayın.
- [OLGU] `AllowUsers` / `AllowGroups` tanımlı değil — dosyada bu yönergelerin hiçbiri yok (Kanıt: eşleşme sayısı 0); SSH erişimi belirli kullanıcı/gruplarla sınırlandırılmamış. Beklenen: tanımlı.
- [ÖNERİ] Yalnızca yetkili hesapları listeleyen bir `AllowUsers` ya da `AllowGroups` yönergesi ekleyin (ör. `AllowGroups ssh-users`).

Uyumlu (1):
- [OLGU] `PubkeyAuthentication yes` — açık anahtar doğrulama etkin; kontrol listesiyle uyumlu (beklenen: `yes`).

### Ek sertleştirme bulguları (8'lik kontrol listesi dışında)
- [OLGU] `Ciphers aes128-cbc,3des-cbc,aes256-cbc` — yalnızca CBC modu şifrelemeler; `3des-cbc` zayıf, CBC modları bilinen zayıflıklara (ör. plaintext recovery) sahiptir. AEAD/CTR şifreleme yok.
- [ÖNERİ] AEAD/CTR tabanlı güçlü şifrelemelere geçin: `Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr`.
- [OLGU] `MACs hmac-md5,hmac-sha1` — `hmac-md5` zayıf; `hmac-sha1` eskimiş (SHA-1); ikisi de ETM (encrypt-then-MAC) değil.
- [ÖNERİ] SHA-2 ETM MAC'lere geçin: `MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com`.
- [ÖNERİ] Terrapin notu (CVE-2023-48795): `chacha20-poly1305` ve `*-etm` MAC'ler ancak strict KEX ile güvenlidir; bu, her iki tarafta OpenSSH ≥ 9.6 (veya strict KEX destekleyen eşdeğer istemci) gerektirir — sunucu ve istemcileri buna göre güncelleyin.
- [OLGU] `ClientAliveInterval 0` — sunucu istemciye canlılık sorgusu göndermiyor; yanıt vermeyen (kopmuş/ölü) istemci bağlantıları SSH katmanında tespit edilmiyor. Not: Bu ayar boşta zaman aşımı değildir; boşta ama bağlı bir istemci sorgulara yanıt verir ve oturumu açık kalır.
- [ÖNERİ] Ölü bağlantı tespiti için mevcut `ClientAliveInterval 0` değerini `ClientAliveInterval 300` olarak değiştirin ve `ClientAliveCountMax 2` ekleyin. Gerçek boşta oturum zaman aşımı için (OpenSSH ≥ 9.2) `ChannelTimeout session=15m` ve `UnusedConnectionTimeout 15m` kullanın (süreler kurum politikasına göre ayarlanmalı).
- [OLGU] `AllowTcpForwarding yes` — TCP yönlendirme açık; bastion/jump kullanımı yoksa yanal hareket (pivoting) yüzeyini genişletir.
- [ÖNERİ] İhtiyaç yoksa `AllowTcpForwarding no` yapın.
- [OLGU] `AllowAgentForwarding` satırı yok (varsayılan: `yes`) — SSH agent yönlendirme açık; ele geçirilmiş bir sunucuda yönlendirilen agent soketi kötüye kullanılabilir.
- [ÖNERİ] İhtiyaç yoksa `AllowAgentForwarding no` ekleyin.
- [OLGU] `MaxStartups` ve `MaxSessions` satırları yok — varsayılanlar geçerli (`MaxStartups 10:30:100`, `MaxSessions 10`).
- [ÖNERİ] Kimliği doğrulanmamış eşzamanlı bağlantıları sınırlamak için `MaxStartups 10:30:60`, bağlantı başına oturum sayısını kısmak için ihtiyaca göre `MaxSessions` (ör. 2–4) ayarlayın.
- [OLGU] `Protocol 2` — bu yönerge OpenSSH 7.4'ten beri eskimiştir ve sshd tarafından yok sayılır; SSH-1 desteği kaldırılmıştır. Satır zararsızdır ama yanıltıcıdır.
- [ÖNERİ] `Protocol 2` satırını kaldırın.
- [ÖNERİ] `LogLevel INFO` yerine `LogLevel VERBOSE` kullanmak, oturum açan anahtar parmak izlerini kayda alarak denetimi güçlendirir.
- [OLGU] `Port 22` — standart SSH portu kullanılıyor. Port değiştirmenin risk etkisi (otomatik tarama gürültüsünün azalması) kuruluşun tercihine bağlıdır; tek başına güvenlik önlemi değildir.
- [DOĞRULANMAMIŞ] Sunucunun OpenSSH sürümü girdide olmadığından sürüme bağlı öneriler (`KbdInteractiveAuthentication` adı ≥ 8.7, `ChannelTimeout`/`UnusedConnectionTimeout` ≥ 9.2, strict KEX ≥ 9.6) uygulamadan önce `sshd -V` ile ve `sshd -t` yapılandırma testiyle doğrulanmalıdır.

## Kanıt
- `examples/ornek-sshd_config:2` — `Port 22`
- `examples/ornek-sshd_config:3` — `Protocol 2`
- `examples/ornek-sshd_config:4` — `PermitRootLogin yes`
- `examples/ornek-sshd_config:5` — `PasswordAuthentication yes`
- `examples/ornek-sshd_config:6` — `PermitEmptyPasswords yes`
- `examples/ornek-sshd_config:7` — `PubkeyAuthentication yes`
- `examples/ornek-sshd_config:8` — `X11Forwarding yes`
- `examples/ornek-sshd_config:9` — `MaxAuthTries 10`
- `examples/ornek-sshd_config:10` — `LoginGraceTime 120`
- `examples/ornek-sshd_config:11` — `ClientAliveInterval 0`
- `examples/ornek-sshd_config:12` — `AllowTcpForwarding yes`
- `examples/ornek-sshd_config:13` — `LogLevel INFO`
- `examples/ornek-sshd_config:14` — `UsePAM yes`
- `examples/ornek-sshd_config:15` — `Ciphers aes128-cbc,3des-cbc,aes256-cbc`
- `examples/ornek-sshd_config:16` — `MACs hmac-md5,hmac-sha1`
- Bulunmayan yönergeler (komut → çıktı):
  - `grep -ciE '^\s*allow(users|groups)' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*KbdInteractiveAuthentication' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*ChallengeResponseAuthentication' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*ClientAliveCountMax' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*(ChannelTimeout|UnusedConnectionTimeout)' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*AllowAgentForwarding' examples/ornek-sshd_config` → `0`
  - `grep -ciE '^\s*(MaxStartups|MaxSessions)' examples/ornek-sshd_config` → `0`
- Dosya boyutu: `wc -l examples/ornek-sshd_config` → `16`; etkin satır sayısı `grep -cvE '^\s*(#|$)' examples/ornek-sshd_config` → `15`

## Doğrulama Durumu
KABUL — Tüm [OLGU] bulguları dosyadaki birebir satırlara veya yukarıdaki grep çıktılarına dayanıyor; 8 maddelik kontrol listesi sayımı tutarlı (Uyumlu 1 + Uyumsuz 7 = 8). Sürüme bağlı öneriler ayrıca [DOĞRULANMAMIŞ] olarak işaretlendi.

## Reviewer Kararı
ONAY — tur 3 · Kullanıcının onayladığı ek turda satır 49 düzeltildi; reviewer 16 olgu ve 14 sayıyı kaynakla yeniden karşılaştırdı, yeni hata bulmadı. (2026-10-31: olgu sayısı 17 yazılmıştı; iki bağımsız yöntemle yeniden sayıldı, gerçek sayı 16 — 17. geçiş Doğrulama Durumu metnindeki anıştırma. Onay değişmedi.)
