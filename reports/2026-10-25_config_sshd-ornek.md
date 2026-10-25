# SSH Sunucu Yapılandırma Denetimi — samples/sshd_config

**Tarih:** 2026-10-25 · **Skill:** config-audit · **Hazırlayan:** agent

## Kapsam
- Girdi: `samples/sshd_config` (OpenSSH sunucu yapılandırması, 12 satır, sentetik örnek)
- Kontrol listesi: config-audit skill'indeki OpenSSH listesi (8 madde)
- Kapsam dışı: `Include` ile eklenen başka dosyalar (yok), `Match` blokları (yok), anahtar algoritmaları (Ciphers/MACs/KexAlgorithms) ve sunucunun gerçek çalışan ayarları (`sshd -T` çalıştırılmadı)

## Bulgular
- [OLGU] Kontrol listesindeki 8 maddeden 2'si uyumlu (PubkeyAuthentication, PermitEmptyPasswords), **6'sı uyumsuz** (PermitRootLogin, PasswordAuthentication, MaxAuthTries, LoginGraceTime, X11Forwarding, AllowUsers/AllowGroups).
- [OLGU] `PermitRootLogin yes` (satır 4): root hesabına doğrudan giriş açık. Beklenen: `no` veya `prohibit-password`. Satır 3'teki `#PermitRootLogin prohibit-password` yorum satırı olduğu için etkisiz.
- [OLGU] `PasswordAuthentication yes` (satır 6): parolayla giriş açık. Bu ayar parola deneme (brute-force) saldırılarına kapı açar. Beklenen: `no`.
- [OLGU] `MaxAuthTries 6` (satır 8): bağlantı başına 6 deneme hakkı var. Beklenen: 3–4.
- [OLGU] `LoginGraceTime 120` (satır 9): kimlik doğrulama için 120 saniye bekleniyor. Beklenen: ≤ 60.
- [OLGU] `X11Forwarding yes` (satır 10): grafik oturum yönlendirmesi açık. Beklenen: `no`.
- [OLGU] `AllowUsers` / `AllowGroups` tanımlı değil (0 etkin satır): kimlik doğrulayabilen her hesap SSH ile girebilir.
- [ÖNERİ] Şu değişiklikleri yapın: `PermitRootLogin no`, `PasswordAuthentication no` (önce kullanıcıların anahtarla girebildiğini doğrulayın, yoksa dışarıda kalırsınız), `MaxAuthTries 3`, `LoginGraceTime 30`, `X11Forwarding no`, `AllowUsers <izinli-hesaplar>`.
- [ÖNERİ] Değişiklikten sonra `sshd -t` ile sözdizimini, `sshd -T` ile etkin ayarları kontrol edin. Mevcut oturumu kapatmadan yeni bir oturumla giriş denemesi yapın.
- [ÖNERİ] Ek koruma için fail2ban veya benzeri bir hız sınırlama aracı ekleyin. auth.log raporundaki (2026-10-25_log_auth-ornek.md) saldırı kalıbı, `PasswordAuthentication yes` ile `PermitRootLogin yes` ayarlarının istismar edildiği senaryoyla örtüşüyor.
- [DOĞRULANMAMIŞ] `UsePAM yes` (satır 11) PAM üzerinden parola girişine ayrıca yol açabilir (KbdInteractiveAuthentication / ChallengeResponseAuthentication). Bu ayarların varsayılanı OpenSSH sürümüne ve dağıtıma göre değişiyor; dosyada açıkça belirtilmemiş.
- [DOĞRULANMAMIŞ] `Port 22` standart port. Portu değiştirmek otomatik tarama gürültüsünü azaltır ama gerçek bir güvenlik önlemi değildir.

## Kanıt
- Çıkarma komutu (bu oturumda çalıştırıldı): `grep -nE '^\s*#?\s*(PermitRootLogin|PasswordAuthentication|...)' samples/sshd_config`
- `samples/sshd_config:3` — `#PermitRootLogin prohibit-password` (yorum, etkisiz)
- `samples/sshd_config:4` — `PermitRootLogin yes`
- `samples/sshd_config:5` — `PubkeyAuthentication yes` (uyumlu)
- `samples/sshd_config:6` — `PasswordAuthentication yes`
- `samples/sshd_config:7` — `PermitEmptyPasswords no` (uyumlu)
- `samples/sshd_config:8` — `MaxAuthTries 6`
- `samples/sshd_config:9` — `LoginGraceTime 120`
- `samples/sshd_config:10` — `X11Forwarding yes`
- `samples/sshd_config:11` — `UsePAM yes`
- `grep -cE '^\s*(AllowUsers|AllowGroups)'` → 0

## Doğrulama Durumu
KABUL — 8 kontrol maddesinin her biri dosya satırıyla eşleştirildi. Sürüme bağlı varsayılanlar [DOĞRULANMAMIŞ] olarak ayrıldı.
