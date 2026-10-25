# OpenSSH sshd_config güvenlik denetimi — samples/sshd_config

**Tarih:** 2026-10-25 · **Skill:** config-audit · **Hazırlayan:** config-auditor (agent)

## Kapsam
- Girdi: `samples/sshd_config`. Dosya 12 satır, UTF-8 ve LF satır sonlu. Türü içerikten belirlendi: dosya adı, satır 1'deki açıklama ve OpenSSH anahtar kelimeleri sonucunda OpenSSH sunucu yapılandırması (sshd_config).
- Kontrol listesi: `config-audit` skill'inin "OpenSSH sshd_config" listesi, **8 madde**. Maddeler: PermitRootLogin, PasswordAuthentication, PermitEmptyPasswords, MaxAuthTries, X11Forwarding, PubkeyAuthentication, LoginGraceTime, AllowUsers / AllowGroups.
- Yöntem: Denetim salt-okunurdu (`cat -n`, `grep -n`, `wc -l`, `sha256sum`). `#` ile başlayan yorum satırları etkin ayar sayılmadı.
- Kapsam dışı:
  - Canlı sunucu ve etkin yapılandırma (`sshd -T` çıktısı alınmadı).
  - OpenSSH sürümü bilinmiyor.
  - `Include` ile eklenebilecek harici dosyalar. Dosyada `Include` yok.
  - Kriptografik algoritmalar (Ciphers, MACs, KexAlgorithms). Kontrol listesinde yer almıyorlar.
  - Ağ eylemleri yapılmadı. `reports/` içindeki eski raporlar okunmadı. Denetlenen dosya değiştirilmedi; sha256 değeri işin başında ve sonunda aynı (bkz. Kanıt).

## Bulgular

### Kontrol listesi (8 madde)
- [OLGU] 1/8 PermitRootLogin **UYUMSUZ**. Satır 4'teki değer `yes`, beklenen `no` veya `prohibit-password`. Satır 3'teki `#PermitRootLogin prohibit-password` bir yorum satırı, bu yüzden etkin değil.
- [OLGU] 2/8 PasswordAuthentication **UYUMSUZ**. Satır 6'daki değer `yes`, beklenen `no`.
- [OLGU] 3/8 PermitEmptyPasswords **UYUMLU**. Satır 7'deki değer `no`, beklenen de `no`.
- [OLGU] 4/8 MaxAuthTries **UYUMSUZ**. Satır 8'deki değer `6`, beklenen aralık 3–4.
- [OLGU] 5/8 X11Forwarding **UYUMSUZ**. Satır 10'daki değer `yes`, beklenen `no`.
- [OLGU] 6/8 PubkeyAuthentication **UYUMLU**. Satır 5'teki değer `yes`, beklenen de `yes`.
- [OLGU] 7/8 LoginGraceTime **UYUMSUZ**. Satır 9'daki değer `120`, beklenen ≤ 60.
- [OLGU] 8/8 AllowUsers / AllowGroups **UYUMSUZ**. Dosyanın 12 satırının hiçbirinde `AllowUsers` veya `AllowGroups` yok; beklenen "tanımlı". Beklenti doğrudan "tanımlı olmak" olduğu için bu yokluk sürüme bağlı değil ve uyumsuzluk sayıldı.
- [OLGU] Sayım:
  - Uyumlu **2**: PermitEmptyPasswords, PubkeyAuthentication.
  - Uyumsuz **6**: PermitRootLogin, PasswordAuthentication, MaxAuthTries, X11Forwarding, LoginGraceTime, AllowUsers / AllowGroups.
  - Tanımsız **0**: Dosyada yer almayan ve uygunluğu varsayılan değere bağlı kalan madde yok. İlk 7 madde dosyada açıkça ayarlanmış.
  - Toplam 2 + 6 + 0 = **8**, kontrol listesindeki madde sayısına eşit.
- [OLGU] Kontrol listesindeki anahtar kelimelerin hiçbiri dosyada iki kez geçmiyor. Dosyada `Match` veya `Include` bloğu da yok. Bu nedenle değerler yalnızca yukarıda adı geçen satırlardan geliyor.

### Kontrol listesi dışı gözlemler (sayıma dahil değil)
- [OLGU] Satır 11'de `UsePAM yes` var. `KbdInteractiveAuthentication` ve eski adıyla `ChallengeResponseAuthentication` dosyada tanımlı değil.
- [DOĞRULANMAMIŞ] Bu ayarlar açıkça `no` yapılmazsa, `PasswordAuthentication no` yapıldıktan sonra bile PAM üzerinden keyboard-interactive yöntemiyle parola girişi açık kalabilir. Bu ayarların varsayılan değeri sürüme ve dağıtıma göre değişir (upstream'de `yes` olduğu biliniyor, bazı dağıtımlar `no` ile gönderir). Sürüm bilinmediği ve birincil kaynak bu oturumda okunmadığı için bu bilgi doğrulanmadı.
- [DOĞRULANMAMIŞ] Upstream OpenSSH varsayılanlarına göre (sürüme bağlı; birincil kaynakla doğrulanmadı) dosyadaki `MaxAuthTries 6` ve `LoginGraceTime 120` değerleri varsayılanla aynı. `PermitRootLogin yes` ise OpenSSH 7.0'dan beri geçerli olan `prohibit-password` varsayılanından daha gevşek. `X11Forwarding yes` de upstream varsayılanı `no` değerinden daha gevşek.
- [OLGU] Satır 2'de `Port 22` (standart port) ve satır 12'de `Subsystem sftp /usr/lib/openssh/sftp-server` var. Bu ayarlar kontrol listesinde yer almıyor; yalnızca bilgi olarak not edildi.

### Öneriler (dosya değiştirilmedi; uygulama kullanıcıya ait)
- [ÖNERİ] PermitRootLogin için satır 4'ü `PermitRootLogin no` yapın. Root ile anahtar tabanlı giriş zorunluysa `prohibit-password` kullanın.
- [ÖNERİ] PasswordAuthentication için satır 6'yı `PasswordAuthentication no` yapın. Aynı anda `KbdInteractiveAuthentication no` satırını ekleyin; bu, PAM üzerinden parola girişini de kapatır. Bunu yapmadan önce yetkili her kullanıcının çalışan bir açık anahtarı olduğundan emin olun ve mevcut oturumu açık tutun. Aksi halde sunucuya erişim kaybedilebilir.
- [ÖNERİ] MaxAuthTries için satır 8'i `MaxAuthTries 3` yapın.
- [ÖNERİ] X11Forwarding için satır 10'u `X11Forwarding no` yapın.
- [ÖNERİ] LoginGraceTime için satır 9'u `LoginGraceTime 30` yapın (60 veya altındaki herhangi bir değer uygun).
- [ÖNERİ] SSH ile girmesi gereken hesapları `AllowGroups <ssh-grubu>` veya `AllowUsers <kullanıcı1> <kullanıcı2>` satırıyla sınırlayın. Grup ve kullanıcı adlarını sistem sahibi belirler; bu rapor ad önermez.
- [ÖNERİ] Değişiklikten sonra servisi yeniden yüklemeden önce `sshd -t` ile sözdizimini kontrol edin. Ardından `sshd -T` çıktısıyla etkin değerlerin beklenen değerlerle eşleştiğini doğrulayın. Bu adımları kullanıcı uygular; agent servise dokunmadı.

## Kanıt
- `samples/sshd_config:3` — `#PermitRootLogin prohibit-password` (yorum satırı, etkin değil)
- `samples/sshd_config:4` — `PermitRootLogin yes`
- `samples/sshd_config:5` — `PubkeyAuthentication yes`
- `samples/sshd_config:6` — `PasswordAuthentication yes`
- `samples/sshd_config:7` — `PermitEmptyPasswords no`
- `samples/sshd_config:8` — `MaxAuthTries 6`
- `samples/sshd_config:9` — `LoginGraceTime 120`
- `samples/sshd_config:10` — `X11Forwarding yes`
- `samples/sshd_config:11` — `UsePAM yes`
- `samples/sshd_config:2` — `Port 22`; `samples/sshd_config:12` — `Subsystem sftp /usr/lib/openssh/sftp-server`
- `samples/sshd_config:1-12` — AllowUsers / AllowGroups yok. Komut ve çıktısı:
  ```
  $ wc -l samples/sshd_config
  12 samples/sshd_config
  $ grep -nEi 'AllowUsers|AllowGroups' samples/sshd_config; echo "grep exit=$?"
  grep exit=1
  ```
- `samples/sshd_config:1-12` — KbdInteractiveAuthentication, ChallengeResponseAuthentication, Include ve Match yok. Komut ve çıktısı:
  ```
  $ grep -nEi 'KbdInteractive|ChallengeResponse|Include|Match' samples/sshd_config; echo "grep exit=$?"
  grep exit=1
  ```
- Kontrol listesi anahtar kelimeleri tek tek geçiyor (yinelenen yok). Komut ve çıktısı:
  ```
  $ grep -nE '^\s*(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|MaxAuthTries|X11Forwarding|PubkeyAuthentication|LoginGraceTime|AllowUsers|AllowGroups)\b' samples/sshd_config
  4:PermitRootLogin yes
  5:PubkeyAuthentication yes
  6:PasswordAuthentication yes
  7:PermitEmptyPasswords no
  8:MaxAuthTries 6
  9:LoginGraceTime 120
  10:X11Forwarding yes
  ```
- Denetlenen dosya değişmedi. Komut ve çıktısı:
  ```
  $ sha256sum samples/sshd_config
  9076d4239909758249633d9d30f005cf055f61fb496247e658a12901d8bb7d8a *samples/sshd_config
  ```

## Doğrulama Durumu
KABUL — Kontrol listesindeki 8 maddenin her biri dosyadaki satırlarla değerlendirildi. Sayım 2 uyumlu + 6 uyumsuz + 0 tanımsız = 8 ve madde sayısına eşit. Her [OLGU] için satır numaralı kanıt ya da komut çıktısı verildi. Sürüme bağlı varsayılanlar ve PAM/keyboard-interactive davranışı [DOĞRULANMAMIŞ] olarak ayrıldı ve sayıma girmedi. Kapsam yalnızca statik dosya içeriği; canlı sunucudaki etkin yapılandırma (`sshd -T`) doğrulanmadı. Reviewer'ın bağımsız yeniden sayımı bekleniyor.
