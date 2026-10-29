# Etki Alanı Denetleyicisi Güvenlik Yapılandırması Denetimi — DC01 (sentetik senaryo)

**Tarih:** 2026-10-28 · **Skill:** config-audit · **Hazırlayan:** agent (config-auditor)

## Kapsam
- Girdi: `samples/dc01-senaryo/` içindeki 15 yapılandırma çıktısı: `auditpol.txt`, `lsa.txt`, `wdigest.txt`, `deviceguard.txt`, `rdp.txt`, `firewall_rdp.txt`, `password_policy.txt`, `powershell_config.txt`, `privileged_groups.txt`, `ad_users.txt`, `laps.txt`, `services.txt`, `systeminfo.txt`, `hotfix.txt`, `ubr.txt`. Bağlam: `TOPLAMA_NOTU.txt`.
- **Veriler SENTETİKTİR:** `TOPLAMA_NOTU.txt:1` — "SENTETİK SENARYO VERİSİ — uydurmadır, gerçek bir sunucudan alınmamıştır." Host: DC01, corp.local, Windows Server 2019 (`systeminfo.txt:1,2,7`). Toplama zamanı 2026-10-27 09:40 yerel (`TOPLAMA_NOTU.txt:8`); yaş hesapları bu tarihe (27.10.2026) göredir.
- Olay bağlamı (kullanıcının SOC uyarısı): ahmet.yilmaz 02:17'de 103.148.72.41 dış IP'sinden giriş yaptı, Domain Admins'e kullanıcı eklendi, DC01'de Invoke-Mimikatz benzeri PowerShell çalıştı. Denetim, bu olayı **mümkün kılan** ve **tespit etmeye yarayacak** ayarlara odaklanır.
- **Yöntem:** config-audit skill'inde Windows/Active Directory kontrol listesi yoktur. Değerlendirme genel güvenlik ilkelerine (en az ayrıcalık, kimlik bilgisi koruması, saldırı yüzeyini daraltma, tespit edilebilirlik) göre yapıldı; bu raporda 44 maddelik bir kontrol listesi tanımlandı (aşağıdaki tablo). Her madde üç durumdan birini alır: Uyumlu, Uyumsuz, Değerlendirilemedi (mevcut değer çıktıdan okunamadı).
- **Beklenen değerler:** Microsoft güvenlik temel çizgisi (security baseline) veya CIS Benchmark'tan anılan değerler bu oturumda kaynaktan çekilmedi (ağ erişimi yok). Bu nedenle beklenen değerler [ÖNERİ] olarak ya da kaynağa dayandığında [DOĞRULANMAMIŞ] olarak verilmiştir. Mevcut değerler [OLGU]'dur (dosya:satır).
- **Eksik veri (değerlendirilemedi, sayıma girmedi):**
  - GPO dışa aktarımı yok (`gpresult /h`, Default Domain Controllers Policy, RSoP). Ayarların GPO'dan mı yerelden mi geldiği bilinmiyor.
  - `auditpol.txt` yalnızca 7 kategori içeriyor; **Policy Change** (Denetim İlkesi Değişikliği), **System** (Güvenlik Durumu Değişikliği, Sistem Bütünlüğü), Account Management altındaki "Computer Account Management" / "Other Account Management Events", Logon/Logoff altındaki "Account Lockout" yok. Toplama eksik mi yoksa ayar mı yok, ayırt edilemez.
  - Süreç oluşturma kaydında komut satırı ekleme ayarı (`ProcessCreationIncludeCmdLine_Enabled`), PowerShell Modül Kaydı (Module Logging), Sysmon (toplama notuna göre kurulu değil, `TOPLAMA_NOTU.txt:14`).
  - `lsa.txt` çıktısı süzülmüş görünüyor (yalnızca 8 değer); `RunAsPPL` sorgulanmamış olabilir → C05 **Değerlendirilemedi**, uyumsuz sayılmadı.
  - LAPS: yalnız eski LAPS özniteliğinin (`ms-Mcs-AdmPwd`) şemada olmadığı görüldü; Windows LAPS (`msLAPS-Password`) aynı komutta hata nedeniyle sorgulanamadı → C41 **Değerlendirilemedi**.
  - Kullanıcı hakları ataması (User Rights Assignment, ör. "Allow log on through Remote Desktop Services"), ince taneli parola ilkeleri (PSO), LDAP imzalama / kanal bağlama, SMB imzalama, NTLM denetimi, AdminSDHolder, DSRM parolası, Defender imza sürümü, ağ çevresi (VPN/kenar güvenlik duvarı, NAT) toplanmadı.
- Kapsam dışı: `security.csv`, `powershell.csv`, `netstat.txt`, `processes.txt`, `run_keys.txt`, `scheduled_tasks.txt` (zaman çizelgesi ve kalıcılık başka ajanlarda: log-analyst, incident-responder). CVE eşlemesi cve-researcher'da. Hiçbir dosya değiştirilmedi, hiçbir komut hedefte çalıştırılmadı.

## Bulgular

### Özet sayım
- [OLGU] 44 kontrol maddesinden **17'si uyumlu**, **25'i uyumsuz**, **2'si değerlendirilemedi** (17 + 25 + 2 = 44).
- [OLGU] Uyumsuz (25): C01 RDP NLA, C02 RDP SecurityLayer, C03 RDP güvenlik duvarı kapsamı, C04 WDigest, C06 VBS/Credential Guard, C07 LmCompatibilityLevel, C11 RestrictAnonymous, C12 Domain Admins üyeliği, C13 Protected Users, C15 Administrator parola yaşı, C16 krbtgt parola yaşı, C17 Hesap kilitleme eşiği, C18 En kısa parola uzunluğu, C19 Parola geçmişi, C28 Kerberos Service Ticket Operations, C29 Kerberos Authentication Service, C31 Security Group Management (Failure yok), C32 Directory Service Access, C33 Directory Service Changes, C34 Sensitive Privilege Use, C37 Execution Policy, C39 PowerShell Transcription, C40 PowerShell 2.0, C42 İşletim sistemi yama seviyesi, C43 Defender platform sürümü (sürüm tarihlemesi doğrulanmadı, bkz. Yama seviyesi).
- [OLGU] Uyumlu (17): C08 NoLmHash, C09 RestrictAnonymousSAM, C10 EveryoneIncludesAnonymous, C14 Enterprise Admins üyeliği, C20 Parola karmaşıklığı, C21 Tersinir şifreleme, C22 En uzun parola yaşı, C23 En kısa parola yaşı, C24 Logon, C25 Logoff, C26 Special Logon, C27 Credential Validation, C30 User Account Management, C35 Process Creation, C36 Other Object Access Events, C38 Script Block Logging, C44 Defender hizmeti.
- [DOĞRULANMAMIŞ] Değerlendirilemedi (2): C05 LSA RunAsPPL (değer süzülmüş çıktıda yok, `lsa.txt:1-9`), C41 LAPS (Windows LAPS sorgulanamadı, `laps.txt:2-3`). Bu iki madde ne uyumlu ne uyumsuz sayıldı.

### Kontrol listesi

| # | Alan | Madde | Mevcut değer (dosya:satır) | Beklenen | Durum |
|---|---|---|---|---|---|
| C01 | Dış erişim | RDP Ağ Düzeyinde Kimlik Doğrulama (NLA) | `UserAuthentication 0x0` (`rdp.txt:6`) | 1 | Uyumsuz |
| C02 | Dış erişim | RDP güvenlik katmanı | `SecurityLayer 0x1` (Negotiate) (`rdp.txt:7`) | 2 (TLS) | Uyumsuz |
| C03 | Dış erişim | RDP güvenlik duvarı kuralı kapsamı | `Profile Any`, `RemoteAddress Any`, `Action Allow` (`firewall_rdp.txt:4-7`) | Yalnız yönetim ağı / atlama sunucusu | Uyumsuz |
| C04 | Kimlik bilgisi | WDigest düz metin önbelleği | `UseLogonCredential 0x1` (`wdigest.txt:2`) | 0 | Uyumsuz |
| C05 | Kimlik bilgisi | LSA koruması (RunAsPPL) | Süzülmüş çıktıda değer yok (`lsa.txt:1-9`); doğrudan sorgulanmadı | 1 (veya 2) | Değerlendirilemedi |
| C06 | Kimlik bilgisi | VBS / Credential Guard | `SecurityServicesConfigured {0}`, `Running {0}`, `VirtualizationBasedSecurityStatus 0` (`deviceguard.txt:3-5`) | VBS açık | Uyumsuz |
| C07 | Kimlik bilgisi | LmCompatibilityLevel | `0x2` (`lsa.txt:6`) | 5 (yalnız NTLMv2) | Uyumsuz |
| C08 | Kimlik bilgisi | NoLmHash | `0x1` (`lsa.txt:7`) | 1 | Uyumlu |
| C09 | Anonim erişim | RestrictAnonymousSAM | `0x1` (`lsa.txt:9`) | 1 | Uyumlu |
| C10 | Anonim erişim | EveryoneIncludesAnonymous | `0x0` (`lsa.txt:5`) | 0 | Uyumlu |
| C11 | Anonim erişim | RestrictAnonymous | `0x0` (`lsa.txt:8`) | 1 | Uyumsuz |
| C12 | Ayrıcalıklı grup | Domain Admins üyeliği | 4 üye: Administrator, ahmet.yilmaz, mehmet.kaya, svc_backup2 (`privileged_groups.txt:4-7`) | Asgari, kişisel günlük hesap yok, servis hesabı yok | Uyumsuz |
| C13 | Ayrıcalıklı grup | Protected Users | "(üye yok)" (`privileged_groups.txt:10`) | Yönetici insan hesapları üye | Uyumsuz |
| C14 | Ayrıcalıklı grup | Enterprise Admins üyeliği | Yalnız Administrator (`privileged_groups.txt:15`) | Asgari | Uyumlu |
| C15 | Hesap | Yerleşik Administrator parola yaşı | PasswordLastSet 12.02.2019 (`ad_users.txt:4`) → 2814 gün | Düzenli döndürülmüş | Uyumsuz |
| C16 | Hesap | krbtgt parola yaşı | PasswordLastSet 12.02.2019 (`ad_users.txt:5`) → 2814 gün | Düzenli döndürülmüş, olay sonrası iki kez | Uyumsuz |
| C17 | Parola ilkesi | Hesap kilitleme eşiği | `LockoutThreshold 0` (`password_policy.txt:6`) | > 0 (ör. 5–10) | Uyumsuz |
| C18 | Parola ilkesi | En kısa parola uzunluğu | `7` (`password_policy.txt:9`) | ≥ 14 | Uyumsuz |
| C19 | Parola ilkesi | Parola geçmişi | `5` (`password_policy.txt:10`) | 24 | Uyumsuz |
| C20 | Parola ilkesi | Karmaşıklık | `True` (`password_policy.txt:3`) | True | Uyumlu |
| C21 | Parola ilkesi | Tersinir şifreleme | `False` (`password_policy.txt:11`) | False | Uyumlu |
| C22 | Parola ilkesi | En uzun parola yaşı | `180 gün` (`password_policy.txt:7`) | 0'dan büyük, ≤ 365 | Uyumlu |
| C23 | Parola ilkesi | En kısa parola yaşı | `1 gün` (`password_policy.txt:8`) | ≥ 1 | Uyumlu |
| C24 | Denetim | Logon | Success and Failure (`auditpol.txt:4`) | Success and Failure | Uyumlu |
| C25 | Denetim | Logoff | Success (`auditpol.txt:5`) | Success | Uyumlu |
| C26 | Denetim | Special Logon | Success (`auditpol.txt:6`) | Success | Uyumlu |
| C27 | Denetim | Credential Validation | Success and Failure (`auditpol.txt:8`) | Success and Failure | Uyumlu |
| C28 | Denetim | Kerberos Service Ticket Operations | No Auditing (`auditpol.txt:9`) | Success and Failure | Uyumsuz |
| C29 | Denetim | Kerberos Authentication Service | No Auditing (`auditpol.txt:10`) | Success and Failure | Uyumsuz |
| C30 | Denetim | User Account Management | Success and Failure (`auditpol.txt:12`) | Success and Failure | Uyumlu |
| C31 | Denetim | Security Group Management | Success (`auditpol.txt:13`) | Success and Failure | Uyumsuz |
| C32 | Denetim | Directory Service Access | No Auditing (`auditpol.txt:15`) | Success and Failure | Uyumsuz |
| C33 | Denetim | Directory Service Changes | No Auditing (`auditpol.txt:16`) | Success and Failure | Uyumsuz |
| C34 | Denetim | Sensitive Privilege Use | No Auditing (`auditpol.txt:18`) | Success and Failure | Uyumsuz |
| C35 | Denetim | Process Creation | Success (`auditpol.txt:20`) | Success | Uyumlu |
| C36 | Denetim | Other Object Access Events | Success (`auditpol.txt:22`) | Success (veya S&F) | Uyumlu |
| C37 | PowerShell | Execution Policy (LocalMachine) | `Unrestricted` (`powershell_config.txt:9`) | RemoteSigned / AllSigned | Uyumsuz |
| C38 | PowerShell | Script Block Logging | `EnableScriptBlockLogging 0x1` (`powershell_config.txt:12`) | 1 | Uyumlu |
| C39 | PowerShell | Transcription | "(anahtar yok)" (`powershell_config.txt:14`) | Açık, merkezi konuma | Uyumsuz |
| C40 | PowerShell | Windows PowerShell 2.0 motoru | `Installed` (`powershell_config.txt:19`) | Kaldırılmış | Uyumsuz |
| C41 | Yerel yönetici | LAPS | Eski LAPS özniteliği şemada yok (`laps.txt:2`); Windows LAPS sorgulanamadı (`laps.txt:1-2`) | LAPS (tercihen Windows LAPS) devrede | Değerlendirilemedi |
| C42 | Yama | İşletim sistemi güncelleme seviyesi | Son güncelleme KB5001342, 14.04.2021 (`hotfix.txt:4`); UBR `0x757` = 1879 (`ubr.txt:3`) → 2022 gün | Son aylık toplu güncelleme | Uyumsuz |
| C43 | Yama | Defender platform sürümü | `platform\4.18.2104.14-0` (`services.txt:11`); Nisan 2021 tarihlemesi doğrulanmadı | Güncel platform | Uyumsuz (tarihlemeye dayanır) |
| C44 | Koruma | Defender hizmeti | `WinDefend Auto Running` (`services.txt:11`) | Auto, Running | Uyumlu |

### Olayı mümkün kılan ayarlar (dış erişim)
- [OLGU] DC01'de RDP açık: `fDenyTSConnections 0x0` (`rdp.txt:2`), port `0xd3d` = 3389 (`rdp.txt:5`), `TermService ... Running` (`services.txt:9`).
- [OLGU] RDP güvenlik duvarı kuralı her profil ve her uzak adres için izin veriyor: `Profile Any`, `RemoteAddress Any` (`firewall_rdp.txt:5,7`). Kural düzeyinde dış IP'ler (ör. 103.148.72.41) engellenmiyor. Kenarda NAT/VPN/güvenlik duvarı olup olmadığı veri setinde yok (`TOPLAMA_NOTU.txt:14`).
- [OLGU] NLA kapalı (`UserAuthentication 0x0`, `rdp.txt:6`) ve güvenlik katmanı Negotiate (`SecurityLayer 0x1`, `rdp.txt:7`).
- [DOĞRULANMAMIŞ] NLA kapalıyken kimlik doğrulama oturum açılmadan önce yapılmaz ve oturum ekranı kimliği doğrulanmamış bağlantılara açılır; bu davranış Microsoft belgesinden bu oturumda doğrulanmadı.
- [OLGU] Hesap kilitleme kapalı: `LockoutThreshold 0` (`password_policy.txt:6`). En kısa parola 7 karakter (`password_policy.txt:9`).
- [DOĞRULANMAMIŞ] Eşik 0 iken hesap kilitlenmez, sınırsız parola denemesi yapılabilir (genel bilgi, kaynaktan doğrulanmadı).
- [ÖNERİ] DC üzerinde RDP'yi ya kapatın ya da güvenlik duvarı kuralını yalnızca yönetim ağı / ayrıcalıklı erişim iş istasyonu (PAW) / atlama sunucusu adresleriyle sınırlayın (`RemoteAddress`), `Profile` değerini `Domain` yapın. İnternetten DC'ye doğrudan RDP olmamalı; kenar güvenlik duvarında 3389 yönlendirmesini kontrol edin.
- [ÖNERİ] `UserAuthentication = 1` (NLA), `SecurityLayer = 2` (TLS) ayarlayın; GPO ile zorlayın.
- [ÖNERİ] Hesap kilitleme eşiği tanımlayın (ör. 5–10 deneme, 15–30 dk) ve parola uzunluğunu en az 14'e çıkarın; parola geçmişini 24'e çıkarın.
- [DOĞRULANMAMIŞ] "Kilitleme eşiği 10 veya daha az, parola uzunluğu 14, geçmiş 24" değerleri CIS / Microsoft temel çizgisinde geçen değerlere dayanır; bu oturumda kaynaktan doğrulanmadı.

### Kimlik bilgisi hırsızlığını kolaylaştıran ayarlar
- [OLGU] WDigest ayarı açık: `UseLogonCredential 0x1` (`wdigest.txt:2`).
- [DOĞRULANMAMIŞ] Bu ayarla etkileşimli oturum açan kullanıcıların parolalarının LSASS belleğinde düz metin tutulduğu ve Mimikatz `sekurlsa::logonpasswords` türü araçlarla okunabildiği genel bilgiye dayanır; kaynaktan doğrulanmadı.
- [DOĞRULANMAMIŞ] LSA koruması (C05) değerlendirilemedi: `lsa.txt` 8 değer listeliyor ve `RunAsPPL` aralarında değil (`lsa.txt:2-9`), ancak çıktı süzülmüş olabileceğinden değerin yokluğu kanıtlanmış sayılmaz.
- [OLGU] Sanallaştırma tabanlı güvenlik (VBS) kapalı: `VirtualizationBasedSecurityStatus 0`, yapılandırılmış/çalışan hizmet `{0}` (`deviceguard.txt:3-5`).
- [OLGU] Protected Users grubu boş (`privileged_groups.txt:10`).
- [DOĞRULANMAMIŞ] Bu nedenle Domain Admins üyeleri Protected Users korumalarından (NTLM/WDigest/zayıf Kerberos şifrelemesi engeli, kimlik bilgisi önbelleği yok) yararlanmıyor; korumaların kapsamı kaynaktan doğrulanmadı.
- [OLGU] `LmCompatibilityLevel 0x2` (`lsa.txt:6`).
- [DOĞRULANMAMIŞ] Bu seviyede NTLMv1 yanıtlarının sunucu tarafında reddedilmediği genel bilgiye dayanır; kaynaktan doğrulanmadı.
- [ÖNERİ] `UseLogonCredential = 0` yapın (veya değeri silin) ve GPO ile zorlayın; ardından ayrıcalıklı hesapların oturumlarını kapatıp parolalarını değiştirin (değer 1 iken bellekte bulunan parolalar ele geçmiş sayılmalı).
- [ÖNERİ] `HKLM\SYSTEM\CurrentControlSet\Control\Lsa\RunAsPPL = 1` ayarlayın (yeniden başlatma gerekir); öncesinde `reg query ... /v RunAsPPL` ile değerin gerçekten yok olduğunu doğrulayın. LSA'ya yüklenen üçüncü taraf eklentilerin uyumluluğunu test edin.
- [ÖNERİ] Yönetici insan hesaplarını (servis hesapları hariç) Protected Users grubuna ekleyin; önce bir test hesabıyla deneyin.
- [ÖNERİ] `LmCompatibilityLevel = 5` yapın; öncesinde NTLM denetimi ile NTLMv1 kullanan istemcileri belirleyin.
- [DOĞRULANMAMIŞ] Credential Guard'ın etki alanı denetleyicisinde ek koruma sağlamadığı / desteklenmediği bilinir; bu nedenle C06 için asıl öneri VBS ve HVCI (bellek bütünlüğü) açılmasıdır, Credential Guard üye sunucu ve iş istasyonlarında önceliklidir. Bu ifade Microsoft belgesinden bu oturumda doğrulanmadı.
- [DOĞRULANMAMIŞ] `RunAsPPL` değerinin varsayılanı (yoksa koruma kapalı) Windows Server 2019 için genel bilgiye dayanır; GPO/RSoP verisi olmadan kesinleşmez.
- [ÖNERİ] `RestrictAnonymous = 1` (C11) değerlendirin; DC'de eski istemci/güven ilişkisi uyumluluğunu önce test edin.

### Ayrıcalıklı grup ve hesap hijyeni
- [OLGU] Domain Admins'te 4 üye var: Administrator, ahmet.yilmaz, mehmet.kaya, svc_backup2 (`privileged_groups.txt:4-7`).
- [DOĞRULANMAMIŞ] Adlandırmaya göre ahmet.yilmaz ve mehmet.kaya kişisel kullanıcı hesabı, svc_backup2 servis hesabı gibi görünüyor; hesap türü veri setinde belirtilmiyor, yalnızca addan çıkarım.
- [OLGU] svc_backup2 hesabı: whenCreated `27.10.2026 02:22:47`, PasswordLastSet `27.10.2026 02:22:47` (oluşturulma ile aynı an), LastLogonDate `27.10.2026 02:31:56` (`ad_users.txt:9`).
- [DOĞRULANMAMIŞ] Bu oluşturulma zamanı, SOC uyarısındaki "Domain Admins'e kullanıcı eklendi" bilgisiyle tutarlı görünüyor (uyarı bu veri setinde değil, kullanıcı bağlamından).
- [OLGU] ahmet.yilmaz Domain Admins üyesi (`privileged_groups.txt:5`) ve son oturumu `27.10.2026 02:17:03` (`ad_users.txt:6`).
- [DOĞRULANMAMIŞ] Bu son oturum zamanı, SOC uyarısındaki 02:17 dış IP girişiyle aynı dakikadır (uyarı bu veri setinde değil, kullanıcı bağlamından).
- [ÖNERİ] Bir kullanıcı hesabının aynı zamanda etki alanı yöneticisi olması, o hesabın tek bir parola ele geçişini etki alanı düzeyinde yetkiye çevirebilir; hesabın günlük kullanımda olup olmadığını doğrulayın ve yönetici yetkisini ayrı bir hesaba taşıyın (veri setinde günlük kullanımı gösteren kayıt incelenmedi).
- [OLGU] krbtgt parolası 12.02.2019'dan beri değişmemiş (`ad_users.txt:5`), 27.10.2026 itibarıyla 2814 gün. Hesap `Enabled False` (`ad_users.txt:5`).
- [DOĞRULANMAMIŞ] krbtgt hesabının devre dışı olması olağan kabul edilir ve bu raporda bulgu sayılmadı; bu genel bilgi kaynaktan doğrulanmadı.
- [OLGU] Yerleşik Administrator parolası 12.02.2019'dan beri değişmemiş, hesap 01.09.2026'da kullanılmış (`ad_users.txt:4`).
- [ÖNERİ] svc_backup2'yi hemen devre dışı bırakın ve Domain Admins'ten çıkarın (olay müdahale ekibiyle eşgüdümlü, kanıt korunarak). ahmet.yilmaz hesabının parolasını sıfırlayın, oturumlarını sonlandırın.
- [ÖNERİ] Yönetici ayrımı: kişisel günlük hesaplar Domain Admins'te olmamalı; ayrı yönetici hesapları (ör. `adm-<ad>`) ve katmanlı yönetim modeli kullanın. Servis hesapları için gMSA ve en az ayrıcalık uygulayın.
- [ÖNERİ] krbtgt parolasını **iki kez** sıfırlayın; iki sıfırlama arasında tüm DC'lere çoğaltmanın tamamlanmasını ve en az bir bilet ömrü süresini (varsayılan 10 saat) bekleyin. SOC uyarısında Mimikatz kullanımı geçtiği için krbtgt anahtarının ele geçtiği varsayılmalı (altın bilet riski). Ardından düzenli döndürme takvimi (ör. 180 günde bir) belirleyin.
- [ÖNERİ] Yerleşik Administrator parolasını uzun, rastgele bir parolayla değiştirin, kasada saklayın ve günlük kullanımdan çıkarın.

### Denetim (audit) ilkesi boşlukları — hangi olaylar eksik kalır
- [OLGU] `Kerberos Authentication Service` No Auditing (`auditpol.txt:10`).
- [DOĞRULANMAMIŞ] Bu ayarla 4768 (TGT isteği), 4771 (ön kimlik doğrulama hatası) olayları üretilmez; Kerberos üzerinden parola deneme ve sahte TGT kullanımı izlenemez.
- [OLGU] `Kerberos Service Ticket Operations` No Auditing (`auditpol.txt:9`).
- [DOĞRULANMAMIŞ] Bu ayarla 4769 (servis bileti) üretilmez; Kerberoasting ve altın bilet ile alınan servis biletleri görünmez.
- [OLGU] `Directory Service Access` No Auditing (`auditpol.txt:15`).
- [DOĞRULANMAMIŞ] Bu ayarla 4662 üretilmez; DCSync (dizin çoğaltma haklarının kötüye kullanımı, ör. krbtgt karmasının çekilmesi) DC güvenlik günlüğünde tespit edilemez.
- [OLGU] `Directory Service Changes` No Auditing (`auditpol.txt:16`).
- [DOĞRULANMAMIŞ] Bu ayarla 5136/5137/5141 üretilmez; AdminSDHolder, GPO, ACL değişiklikleri izlenemez.
- [OLGU] `Sensitive Privilege Use` No Auditing (`auditpol.txt:18`).
- [DOĞRULANMAMIŞ] Bu ayarla 4673/4674 üretilmez; SeDebugPrivilege kullanımı (Mimikatz `privilege::debug`) kaydedilmez.
- [OLGU] `Security Group Management` yalnız Success (`auditpol.txt:13`).
- [DOĞRULANMAMIŞ] Bu ayarla başarılı grup üyeliği eklemeleri (4728/4732/4756) kaydedilir, başarısız denemeler kaydedilmez.
- [OLGU] Açık olan denetim alt kategorileri: Logon, Logoff, Special Logon (`auditpol.txt:4-6`), Credential Validation (`auditpol.txt:8`), User Account Management (`auditpol.txt:12`), Process Creation (`auditpol.txt:20`), Other Object Access Events (`auditpol.txt:22`).
- [DOĞRULANMAMIŞ] Bu alt kategorilerin oturum açma/kapama, kimlik doğrulama, hesap yönetimi, süreç oluşturma ve zamanlanmış görev oluşturma olaylarını ürettiği genel bilgiye dayanır; kaynaktan doğrulanmadı.
- [OLGU] Toplama notuna göre Sysmon kurulu değil ve güvenlik duvarı/VPN kayıtları toplanmadı (`TOPLAMA_NOTU.txt:14`).
- [ÖNERİ] C28, C29, C31, C32, C33, C34 için Success and Failure açın (Gelişmiş Denetim İlkesi, GPO ile). Directory Service Access için ayrıca etki alanı kökünde çoğaltma haklarına (DS-Replication-Get-Changes / -All) SACL tanımlayın; aksi halde 4662 üretilmez.
- [ÖNERİ] Toplanmamış kategorileri `auditpol /get /category:*` ile tam toplayın; özellikle Audit Policy Change, Security State Change, Security System Extension, Computer Account Management, Other Account Management Events, Account Lockout.
- [ÖNERİ] Süreç oluşturma olaylarına komut satırı eklenmesini (`ProcessCreationIncludeCmdLine_Enabled = 1`) doğrulayın; Sysmon kurulumunu ve güvenlik günlüğünün merkezi SIEM'e iletilmesini değerlendirin (yerel günlük silinebilir).
- [DOĞRULANMAMIŞ] Hangi alt kategorinin hangi olay kimliğini ürettiği Microsoft belgelerindeki genel bilgiye dayanır; bu oturumda kaynaktan doğrulanmadı.

### PowerShell denetimleri
- [OLGU] Script Block Logging açık: `EnableScriptBlockLogging 0x1` (`powershell_config.txt:12`) — C38 uyumlu.
- [DOĞRULANMAMIŞ] Bu ayar, Invoke-Mimikatz benzeri betiklerin PowerShell Operational günlüğünde (olay 4104) görünmesini sağlayan başlıca kaynak olabilir; olay kimliği eşlemesi ve tespit etkisi kaynaktan doğrulanmadı.
- [OLGU] Transcription yapılandırılmamış (`powershell_config.txt:13-14`).
- [OLGU] Windows PowerShell 2.0 motoru kurulu (`powershell_config.txt:19`).
- [DOĞRULANMAMIŞ] PowerShell 2.0 Script Block Logging ve AMSI desteklemediği için `powershell -version 2` ile kayıt atlatılabilir; bu davranış kaynaktan doğrulanmadı.
- [OLGU] LocalMachine Execution Policy `Unrestricted`, MachinePolicy `Undefined` (`powershell_config.txt:5,9`).
- [ÖNERİ] PowerShell 2.0'ı kaldırın (`Uninstall-WindowsFeature PowerShell-V2`). Transcription'ı GPO ile açıp yazma korumalı merkezi bir paylaşıma yönlendirin. Modül kaydını (Module Logging) da açın. PowerShell Operational günlük boyutunu büyütün ve SIEM'e iletin.
- [ÖNERİ] Execution Policy'yi GPO ile `RemoteSigned` veya `AllSigned` yapın. [DOĞRULANMAMIŞ] Execution Policy bir güvenlik sınırı değildir (`-ep bypass` ile atlanabilir); asıl kontrol uygulama denetimi (AppLocker / WDAC) ve kayıttır.

### LAPS
- [OLGU] Eski LAPS özniteliği şemada yok: `Get-ADComputer` sorgusu `ms-Mcs-AdmPwd` için "One or more properties are invalid" hatası verdi (`laps.txt:2`); toplayan notu: "LAPS şeması etki alanında yok" (`laps.txt:3`).
- [DOĞRULANMAMIŞ] C41 değerlendirilemedi: komut ilk geçersiz öznitelikte durduğu için Windows LAPS özniteliğinin (`msLAPS-Password`) varlığı belirlenemedi; toplayan notu yalnız eski şema hatasına dayanıyor olabilir.
- [ÖNERİ] Windows LAPS'ı devreye alın; üye sunucu ve iş istasyonlarında yerel yönetici parolalarını benzersiz ve döndürülen hale getirin (yanal hareketi zorlaştırır). DC'lerde Windows LAPS ile DSRM parolasının yönetimini değerlendirin.
- [DOĞRULANMAMIŞ] DC'lerde yerel hesap bulunmadığından LAPS'ın DC01'in kendisi için değil, etki alanının geneli için önemli olduğu genel bilgiye dayanır. Sonraki toplamada `Get-ADComputer DC01 -Properties msLAPS-Password` ayrı çalıştırılmalı.

### Yama seviyesi
- [OLGU] Kurulu yalnızca 2 güncelleme var; sonuncusu KB5001342, `14.04.2021` (`hotfix.txt:3-4`, `systeminfo.txt:8-10`). 27.10.2026 itibarıyla 2022 gün (yaklaşık 5,5 yıl) güncelleme yok.
- [OLGU] Derleme 17763, UBR `0x757` = 1879 (`ubr.txt:2-3`). Sunucu 3.10.2026'da yeniden başlatılmış (`systeminfo.txt:5`) ama güncelleme almamış.
- [OLGU] Defender platformu `4.18.2104.14-0` (`services.txt:11`). C43'ün uyumsuz sayılması bu sürümün Nisan 2021 dönemine ait olduğu tarihlemesine dayanır; bu tarihleme doğrulanmadı (aşağıdaki [DOĞRULANMAMIŞ] madde).
- [ÖNERİ] DC01'e son kümülatif güncellemeyi uygulayın; öncesinde yedek ve test. Güncelleme altyapısının (WSUS/Windows Update) neden 2021'den beri çalışmadığını araştırın; diğer DC'leri de kontrol edin.
- [DOĞRULANMAMIŞ] 17763.1879'un Nisan 2021 toplu güncellemesine (KB5001342) karşılık geldiği ve Defender platform `4.18.2104` sürümünün Nisan 2021 dönemine ait olduğu genel bilgiye dayanır. Bu seviyede açık kalan ayrıcalık yükseltme / kimlik bilgisi CVE'leri bu raporda eşlenmedi → cve-researcher'a yardım isteği yazıldı.
- [DOĞRULANMAMIŞ] Windows Server 2019'un ana akım desteği sona ermiş, genişletilmiş destek sürüyor olabilir; destek tarihi bu oturumda doğrulanmadı.

### Öncelik sırası (öneri)
- [ÖNERİ] 1) svc_backup2'yi devre dışı bırakın, ahmet.yilmaz ve tüm Domain Admins parolalarını sıfırlayın, krbtgt'yi iki kez sıfırlayın. 2) RDP'yi dış erişime kapatın, NLA'yı açın. 3) WDigest'i kapatın, RunAsPPL'yi açın, yöneticileri Protected Users'a ekleyin. 4) Hesap kilitlemeyi açın. 5) Kerberos, DS Access/Changes, Sensitive Privilege Use denetimini açın. 6) PowerShell 2.0'ı kaldırın, Transcription açın. 7) Yamaları uygulayın. 8) Windows LAPS'ı devreye alın.

## Kanıt
Tüm satırlar bu oturumda `cat -n samples/dc01-senaryo/<dosya>` ile okundu. Tarih farkları `python -c "from datetime import date"` ile hesaplandı (`27.10.2026 − 12.02.2019 = 2814 gün`, `27.10.2026 − 14.04.2021 = 2022 gün`); onaltılık dönüşüm `printf '%d' 0x757 0xd3d` → `1879`, `3389`.
- `samples/dc01-senaryo/TOPLAMA_NOTU.txt:1` — `SENTETİK SENARYO VERİSİ — uydurmadır, gerçek bir sunucudan alınmamıştır.`
- `samples/dc01-senaryo/TOPLAMA_NOTU.txt:14` — `Eksik: bellek imajı alınmadı; Sysmon kurulu değil; güvenlik duvarı/VPN kayıtları toplanmadı.`
- `samples/dc01-senaryo/rdp.txt:2` — `fDenyTSConnections    REG_DWORD    0x0`
- `samples/dc01-senaryo/rdp.txt:5` — `PortNumber    REG_DWORD    0xd3d`
- `samples/dc01-senaryo/rdp.txt:6` — `UserAuthentication    REG_DWORD    0x0`
- `samples/dc01-senaryo/rdp.txt:7` — `SecurityLayer    REG_DWORD    0x1`
- `samples/dc01-senaryo/firewall_rdp.txt:4-7` — `Enabled : True` / `Profile : Any` / `Action : Allow` / `RemoteAddress : Any`
- `samples/dc01-senaryo/wdigest.txt:2` — `UseLogonCredential    REG_DWORD    0x1`
- `samples/dc01-senaryo/lsa.txt:2-9` — `auditbasedirectories 0x0`, `crashonauditfail 0x0`, `disabledomaincreds 0x0`, `everyoneincludesanonymous 0x0`, `LmCompatibilityLevel 0x2`, `NoLmHash 0x1`, `restrictanonymous 0x0`, `restrictanonymoussam 0x1` (RunAsPPL yok)
- `samples/dc01-senaryo/deviceguard.txt:3-5` — `SecurityServicesConfigured : {0}`, `SecurityServicesRunning : {0}`, `VirtualizationBasedSecurityStatus : 0`
- `samples/dc01-senaryo/password_policy.txt:3` — `ComplexityEnabled : True`
- `samples/dc01-senaryo/password_policy.txt:6` — `LockoutThreshold : 0`
- `samples/dc01-senaryo/password_policy.txt:7-8` — `MaxPasswordAge : 180.00:00:00`, `MinPasswordAge : 1.00:00:00`
- `samples/dc01-senaryo/password_policy.txt:9` — `MinPasswordLength : 7`
- `samples/dc01-senaryo/password_policy.txt:10` — `PasswordHistoryCount : 5`
- `samples/dc01-senaryo/password_policy.txt:11` — `ReversibleEncryptionEnabled : False`
- `samples/dc01-senaryo/privileged_groups.txt:4-7` — `Administrator`, `ahmet.yilmaz`, `mehmet.kaya`, `svc_backup2`
- `samples/dc01-senaryo/privileged_groups.txt:10` — `(üye yok)` (Protected Users)
- `samples/dc01-senaryo/privileged_groups.txt:15` — `Administrator` (Enterprise Admins)
- `samples/dc01-senaryo/ad_users.txt:4` — `Administrator  True    12.02.2019 10:03:11  12.02.2019 10:05:40  01.09.2026 11:20:05`
- `samples/dc01-senaryo/ad_users.txt:5` — `krbtgt         False   12.02.2019 10:21:47  12.02.2019 10:21:47`
- `samples/dc01-senaryo/ad_users.txt:6` — `ahmet.yilmaz   True    04.05.2021 09:14:20  18.07.2026 09:02:33  27.10.2026 02:17:03`
- `samples/dc01-senaryo/ad_users.txt:9` — `svc_backup2    True    27.10.2026 02:22:47  27.10.2026 02:22:47  27.10.2026 02:31:56`
- `samples/dc01-senaryo/auditpol.txt:4-6` — `Logon Success and Failure`, `Logoff Success`, `Special Logon Success`
- `samples/dc01-senaryo/auditpol.txt:8-10` — `Credential Validation Success and Failure`, `Kerberos Service Ticket Operations No Auditing`, `Kerberos Authentication Service No Auditing`
- `samples/dc01-senaryo/auditpol.txt:12-13` — `User Account Management Success and Failure`, `Security Group Management Success`
- `samples/dc01-senaryo/auditpol.txt:15-16` — `Directory Service Access No Auditing`, `Directory Service Changes No Auditing`
- `samples/dc01-senaryo/auditpol.txt:18` — `Sensitive Privilege Use No Auditing`
- `samples/dc01-senaryo/auditpol.txt:20` — `Process Creation Success`
- `samples/dc01-senaryo/auditpol.txt:22` — `Other Object Access Events Success`
- `samples/dc01-senaryo/powershell_config.txt:9` — `LocalMachine    Unrestricted`
- `samples/dc01-senaryo/powershell_config.txt:12` — `EnableScriptBlockLogging    REG_DWORD    0x1`
- `samples/dc01-senaryo/powershell_config.txt:14` — `(anahtar yok)` (Transcription)
- `samples/dc01-senaryo/powershell_config.txt:19` — `[X] Windows PowerShell 2.0 Engine  PowerShell-V2  Installed`
- `samples/dc01-senaryo/laps.txt:2-3` — `Get-ADComputer : One or more properties are invalid. Parameter name: ms-Mcs-AdmPwd` / `(LAPS şeması etki alanında yok)`
- `samples/dc01-senaryo/services.txt:9` — `TermService      Manual    Running`
- `samples/dc01-senaryo/services.txt:11` — `WinDefend        Auto      Running "C:\ProgramData\Microsoft\Windows Defender\platform\4.18.2104.14-0\MsMpEng.exe"`
- `samples/dc01-senaryo/systeminfo.txt:2-5` — `Microsoft Windows Server 2019 Standard`, `10.0.17763 N/A Build 17763`, `Primary Domain Controller`, `System Boot Time: 3.10.2026, 04:12:55`
- `samples/dc01-senaryo/systeminfo.txt:8-10` — `2 Hotfix(s) Installed.` `KB5000859`, `KB5001342`
- `samples/dc01-senaryo/hotfix.txt:3-4` — `KB5000859 10.03.2021`, `KB5001342 14.04.2021`
- `samples/dc01-senaryo/ubr.txt:2-3` — `CurrentBuild 17763`, `UBR    REG_DWORD    0x757`

## Doğrulama Durumu
KABUL — Sayılan 42 maddenin (17 uyumlu + 25 uyumsuz) her birinin mevcut değeri dosya:satır ile eşleştirildi; toplam 17 + 25 + 2 değerlendirilemedi = 44. C05 (RunAsPPL) ve C41 (LAPS) için mevcut değer çıktıdan okunamadığından (süzülmüş `lsa.txt`, sorgulanamayan Windows LAPS özniteliği) bu iki madde "Değerlendirilemedi" olarak işaretlendi, uyumlu/uyumsuz sayımına girmedi. Sınırlar: veriler sentetik; beklenen değerler ve davranış açıklamaları kaynaktan doğrulanmadı ([DOĞRULANMAMIŞ]); C43'ün uyumsuzluğu Defender platform sürümünün doğrulanmamış tarihlemesine dayanır; GPO dışa aktarımı ve auditpol'ün bir kısmı eksik (Kapsam).

## Reviewer Kararı
ONAY — tur 4 (kullanıcı onaylı ek tur) · satır 107-110 düzeldi (olgu/yorum ayrıldı), kaynak değerleri birebir, sayımlar 17/25/2 = 44 doğru; engelleyici olmayan not: satır 79 örnek IP SOC uyarısından
