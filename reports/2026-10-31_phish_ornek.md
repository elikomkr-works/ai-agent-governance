# Oltalama Triyajı — ornek-phishing.eml (statik inceleme)

**Tarih:** 2026-10-31 · **Skill:** phishing-triage · **Hazırlayan:** phishing-analyst

## Kapsam
- Girdi (salt-okunur): `samples/ornek-phishing.eml` — 59 satır, RFC 5322 `.eml` ihracı, tam başlık bloğu mevcut (`Return-Path:` satırından `Authentication-Results:` ve `Received` zincirine kadar).
- Dosyanın bize nasıl ulaştığı: bu görevde sentetik kabul testi örneği olarak repo içindeki `samples/` klasöründen verildi; gerçek bir müşteri ihracı değildir.
- Alıcı kurumun mail altyapısı: başlıklarda alıcı tarafın kendi atlamaları olarak `mx01.kartaltekstil.example` ve `mail.kartaltekstil.example` görünüyor (satır 3-8). Bunun gerçekten müşterinin kendi altyapısı olduğu bize ayrıca doğrulanmadı.
- Müşteri saat dilimi: başlıklardaki alıcı tarafı damgaları `+0300` (satır 5, 8). Kurumun resmî saat dilimi beyanı bilinmiyor.
- Kapsam dışı — ağ eylemi gerektirdiği için yapılmadı: hiçbir URL ziyaret edilmedi, çözümlenmedi, kısaltma açılmadı, DNS/WHOIS/TLS/SPF/DKIM sorgusu yapılmadı; itibar (reputation) ve tehdit istihbaratı sorgulanmadı; gönderici, Reply-To adresi, mesajdaki telefon numarası veya kurum ile iletişime geçilmedi.
- Kapsam dışı — çalıştırma/çözme yasağı: ek dosya çalıştırılmadı, diske yazılmadı, arşiv açılmadı, base64 gövdesi çözülmedi veya herhangi bir tarayıcıya/çevrimiçi taratıcıya verilmedi. Ek yalnızca e-posta dosyasının kendi beyanlarından (ad, bildirilen tip, kodlama, uzantı deseni) tarif edildi.
- Kapsam dışı — hash: Bash/karma aracım yok, bu yüzden ek için SHA-256 üretilemedi. Ek dosyasının SHA-256'sı müşteriden **yazılı olarak** istenmelidir; hash temelli her iddia (bilinen zararlı eşleşmesi, kampanya ilişkisi) bu raporun kapsamı dışındadır.
- Kapsam dışı: dinamik analiz / sandbox, zararlı yazılım tersine mühendisliği, canlı altyapı kontrolü, mail sunucusu ve gateway log korelasyonu (kim aldı, kim tıkladı).
- Değerlendirme yalnızca bu ihracatta **yazılı olanla** sınırlıdır.

## Bulgular

### Kimlik doğrulama (gateway'in teslim anındaki kaydı)
- [OLGU] `Authentication-Results` başlığında kayıtlı sonuç `spf=fail`'dir ve SPF kontrolü zarf alanı `smtp.mailfrom=nortvale-invoices[.]example` üzerinde yapılmıştır (dosya:13).
- [OLGU] Aynı başlıkta `dkim=none (message not signed) header.d=none` yazılıdır ve dosyada hiçbir `DKIM-Signature:` başlığı yoktur (dosya:14).
- [OLGU] Aynı başlıkta `dmarc=fail (p=none sp=none dis=none) header.from=nortvale[.]example` yazılıdır; kayıtlı politika `p=none` olduğundan başarısız mesaj yine teslim edilir (dosya:15).
- [OLGU] DMARC sonucunda yazan `header.from=nortvale[.]example` ile `From:` başlığındaki alan adı `nortvale-invoices[.]example` birbirinden farklıdır (dosya:15 ve dosya:19).
- [OLGU] `Received-SPF: fail (... does not designate 45.133.88.214 as permitted sender) client-ip=45.133.88.214` kayıtlıdır (dosya:16).
- [DOĞRULANMAMIŞ] Gönderen alan adının gerçekten taklit (spoof) edildiği. Yukarıdakiler gateway'in teslim anındaki kendi kayıtlarıdır; bu raporda yeniden doğrulanmadı — canlı DNS/SPF sorgusu bir ağ eylemidir ve yapılmadı.

### Yönlendirme zinciri ve gönderici kimliği
- [OLGU] Zincirdeki en eski atlama `Received: from localhost (unknown [196.202.14.7])` — ters ad çözülmemiş, `unknown` olarak kaydedilmiş bir atlamadır (dosya:9).
- [OLGU] Mesaj alıcıya `smtp-out-7.bulkrelay[.]example [45.133.88.214]` üzerinden ulaşmıştır; bu, `From` alan adının kendi altyapısı olarak beyan edilmeyen bir toplu-gönderim (bulk relay) adıdır (dosya:6).
- [OLGU] `Message-ID` alan adı `bulkrelay[.]example`, `From` alan adı `nortvale-invoices[.]example` — farklıdır (dosya:17, dosya:19).
- [OLGU] `X-Mailer: PHPMailer 6.1.6` — gönderimde kullanılan kütüphane başlıkta görünür durumdadır (dosya:23).
- [OLGU] `X-Originating-IP: [196.202.14.7]` kayıtlıdır ve en eski atlamadaki IP ile aynıdır (dosya:24, dosya:9).
- [OLGU] `From:` görünen adı `"Nortvale Lojistik - Muhasebe"` iken adres alan adı `nortvale-invoices[.]example`'dır; DMARC kaydında geçen kurum alan adı ise `nortvale[.]example`'dır (dosya:19, dosya:15).
- [OLGU] `Reply-To:` adresi `nortvale.finance.dept@mailbox-secure[.]example` — `From` alan adından tamamen farklı bir alan adıdır (dosya:20).
- [OLGU] `X-Priority: 1 (Highest)` ayarlanmıştır (dosya:25).
- [DOĞRULANMAMIŞ] Mesajın gerçek göndericisinin kim olduğu, saldırganın niyeti, kampanya atfı ve `196.202.14.7` / `45.133.88.214` adreslerinin kötücül olup olmadığı. Bunların hiçbiri dosyada yazılı değildir ve itibar sorgusu yapılmamıştır.

### Gövde ve bahane (sayılmayan inceleme)
- [OLGU] Gövde HTML'inde banka hesabının değiştiği yazılıdır: `Banka hesab=C4=B1m=C4=B1z de=C4=9Fi=C5=9Fmi=C5=9Ftir.` (dosya:35). Okunur aktarım (transkripsiyon): "Banka hesabımız değişmiştir."
- [OLGU] Aynı paragrafta bugün 17:00 son teslim süresi ve sevkiyatın durdurulacağı sonucu yazılıdır (dosya:36-38). Transkripsiyon: "...bugün 17:00'a kadar yeni hesabımıza yapmanız gerekmektedir, aksi halde sevkiyat durdurulacaktır."
- [OLGU] Konu başlığı RFC 2047 kodlu: `=?UTF-8?B?QUNJTDogw5ZkZW1lIGhlc2FiIGRlxJ9pxZ9pa2xpxJ9pIC0gRmF0dXJhIE5WLTIwMjYtNDQxOA==?=` (dosya:22). Transkripsiyon (verbatim, normalleştirilmeden): "ACIL: Ödeme hesab değişikliği - Fatura NV-2026-4418" — Türkçe yazımda beklenen "ACİL" yerine noktasız `I` ve "hesap" yerine `hesab` kullanılmış olması, dil/yazım ipucu (language tell) niteliğinde göstergelerdir.
- [OLGU] Selamlama kişisel değil, `Say=C4=B1n Yetkili,` ("Sayın Yetkili") biçimindedir; alıcı `muhasebe@kartaltekstil[.]example` adresidir (dosya:34, dosya:21).
- [OLGU] Gövde eki incelemeye yönlendirir: `Ekteki fatura =C3=B6zetini de inceleyebilirsiniz.` (dosya:43).
- [OLGU] Gövdede dosya içinde doğrulanamayan bir telefon numarası verilmiştir (dosya:46). Bu numara aranmadı.
- [OLGU] Dosyada otomatik okuyucuya/asistana/agent'a yönelik bir talimat metni ("önceki talimatlarını yok say", "bu mesajı güvenli işaretle", "başlıkları ilet" vb.) **bulunmamaktadır**; `## Kanıt` bölümündeki arama bunu göstermektedir. Mesajın tamamı yine de veri olarak işlenmiş, hiçbir isteği uygulanmamıştır.
- [DOĞRULANMAMIŞ] Bunun bir BEC (ödeme yönlendirme) girişimi olduğu yorumu. Dosyada yazılı olan yalnızca metnin kendisidir.

### URL ve ek
- [OLGU] Dosyada `https?://` deseniyle 3 URL geçişi vardır (sayım `## Kanıt`'ta). Gövdedeki bağlantıda okuyucuya gösterilen metin `hxxps://portal.nortvale[.]example/fatura/4418` iken `href` hedefi `hxxp://nortvale-invoices[.]example.kyc-dogrulama[.]example/inv/4418?u=muhasebe@kartaltekstil[.]example`'dır (dosya:40-42). Buradaki hedef, dosyada iki satıra bölünmüş quoted-printable değerin çözülüp birleştirilmiş biçimidir; dosyada byte-byte ne yazdığı `## Kanıt` → URL envanteri tablosundadır.
- [OLGU] Bu `href` hedefinde kayıtlanabilir alan adı `kyc-dogrulama[.]example`'dır; `nortvale-invoices[.]example` kısmı onun altında bir alt alan adı olarak yazılmıştır (iç içe/benzer alan adı deseni) (dosya:40).
- [OLGU] Aynı URL'in sorgu dizesinde alıcının e-posta adresi taşınmaktadır; dosyada `?u=3Dmuhasebe@kartaltekstil.example` olarak yazılıdır, quoted-printable çözümüyle `?u=muhasebe@kartaltekstil[.]example` (dosya:40-41).
- [OLGU] Üçüncü URL geçişi `X-Mailer` başlığındaki PHPMailer proje adresidir (dosya:23); gönderici tarafından tıklanmak üzere sunulmuş bir bağlantı değildir.
- [OLGU] 1 ek vardır: `Content-Disposition: attachment; filename="Fatura_NV-2026-4418.pdf.html"`, bildirilen tip `text/html; charset=UTF-8`, kodlama `base64` (dosya:50-52). Uzantı deseni çift uzantıdır (`.pdf.html`) ve HTML ek desenidir; bildirilen tip `text/html` ile adın başındaki `.pdf` izlenimi çelişmektedir.
- [OLGU] Ekin base64 gövdesi 4 satırdır (dosya:54-57); dosyada beyan edilen boyut başlığı (`Content-Length` / `size=`) yoktur, bu yüzden bildirilen bir boyut yoktur.
- [DOĞRULANMAMIŞ] Ekin açıldığında ne yapacağı, içinde bir kimlik bilgisi formu veya URL bulunup bulunmadığı, bağlantının canlı olup olmadığı. Base64 gövdesi çözülmedi; dosya içinde amacı açıkça yazılı değildir.
- [ÖNERİ] Ek için ayrı bir çözme/sandbox analizi görevi açılsın (izole ortamda, bu skill'in kapsamı dışında) ve müşteriden ekin SHA-256 özeti yazılı olarak istensin.

### Önerilen eylemler (uygulama kullanıcıya aittir)
- [ÖNERİ] Banka/ödeme hesabı değişikliği, müşterinin **önceden güvendiği** bir kanaldan (bilinen numaradan telefon, sözleşmedeki muhasebe muhatabı) doğrulanmalı; bu doğrulama müşterinin eylemidir, mesajdaki numara veya Reply-To adresi kullanılmamalıdır.
- [ÖNERİ] Alıcı `muhasebe@kartaltekstil[.]example` ve aynı mesajı almış olabilecek diğer kullanıcılar uyarılmalı: bağlantı tıklanmasın, ek açılmasın.
- [ÖNERİ] Mesaj kurumun mail gateway'ine oltalama olarak bildirilsin; gateway/engelleme kararları (gönderici, alan adı, URL) kullanıcı tarafından uygulansın.
- [ÖNERİ] Bağlantıya tıklandığı veya ek açıldığı şüphesi varsa, girilmiş olabilecek kimlik bilgileri kullanıcı tarafından değiştirilsin ve host düzeyinde `incident-responder` ile takip edilsin.
- [ÖNERİ] `kyc-dogrulama[.]example` ve `mailbox-secure[.]example` için URL/alan adı itibar sorgusu, ağ erişimi olan ayrı bir görev olarak `cve-researcher`'a verilsin (sonuç `knowledge/quarantine/` altına, onay kullanıcıda).
- [ÖNERİ] Gateway'in SPF/DKIM/DMARC uygulama davranışı (örneğin `dmarc=fail` olan mesajın yine teslim edilmesi) `config-auditor` tarafından incelensin.
- [ÖNERİ] Mesajın başka kutulara da düşüp düşmediği ve tıklama olup olmadığı `log-analyst` tarafından mail gateway loglarından çıkarılsın.

## Kanıt

### Dosya ve sayımlar (Grep count modu)
- Dosya: `samples/ornek-phishing.eml`
- `samples\ornek-phishing.eml:59` — satır sayısı; Grep count modu, desen `^` → 59
- `samples\ornek-phishing.eml:3` — URL geçişi sayısı; Grep count modu, desen `https?://` → 3 (satır 23, 40, 41)
- `samples\ornek-phishing.eml:1` — ek sayısı; Grep count modu, desen `(filename=|Content-Disposition: attachment)` → 1 eşleşen satır (satır 52; satır 50'deki `name=` parametresi aynı eke aittir)
- `samples\ornek-phishing.eml:3` — `Received:` başlığı sayısı; Grep count modu, desen `^Received:` → 3 (satır 3, 6, 9)
- `samples\ornek-phishing.eml:3` — MIME sınır satırı sayısı; Grep count modu, desen `^------=_Part_8841_1761545673` → 3 (satır 29, 49, 59)
- Başlık bloğu satır 1-27'de biter; ilk boş satır 28; gövde satır 29'da başlar. `boundary="----=_Part_8841_1761545673"` (satır 27). Bölüm 1: satır 29-47 (`text/html` gövde). Bölüm 2: satır 49-57 (ek). Kapanış sınırı: satır 59.
- Agent'a yönelik talimat araması: `ignore|disregard|previous instruction|mark (this|it) as safe|forward the headers|talimat|güvenli işaretle|yok say` desenleri ile dosyada eşleşme bulunmadı (0 eşleşme).

### P1-P6 kontrol listesi
| # | Kontrol | İncelenen başlık / satır | Gerekçe | Sonuç |
|---|---|---|---|---|
| P1 | Received zinciri | satır 9, 6, 17, 23, 24 | En eski atlama `from localhost (unknown [196.202.14.7])`; çıkış atlaması toplu-gönderim adı `smtp-out-7.bulkrelay.example`; `Message-ID` alan adı `bulkrelay.example` ≠ `From` alan adı; `X-Mailer: PHPMailer 6.1.6` görünür | İZ VAR |
| P2 | SPF (kayıtlı) | satır 13, 16 | `spf=fail`; ayrıca kontrol zarf alanı `smtp.mailfrom=nortvale-invoices.example` üzerinde yapılmış, `Received-SPF` de `fail` | İZ VAR |
| P3 | DKIM (kayıtlı) | satır 14 | `dkim=none (message not signed) header.d=none`; dosyada `DKIM-Signature:` başlığı yok | İZ VAR |
| P4 | DMARC (kayıtlı) | satır 15, 19 | `dmarc=fail (p=none sp=none dis=none)`; `header.from=nortvale.example`, `From:` alan adı `nortvale-invoices.example` — farklı | İZ VAR |
| P5 | From / Reply-To / Return-Path / görünen ad | satır 1, 19, 20, 21 | `Reply-To` alan adı `mailbox-secure.example` ≠ `From` alan adı `nortvale-invoices.example`; görünen ad "Nortvale Lojistik - Muhasebe" iken alan adı kurum alan adının (`nortvale.example`) ek-kelimeli/tireli benzeri | İZ VAR |
| P6 | URL ve ek envanteri | satır 40-42, 50-52 | `href` hedefi gösterilen bağlantı metninden farklı; kayıtlanabilir alan adı `kyc-dogrulama.example` altında iç içe `nortvale-invoices.example`; sorgu dizesinde alıcı adresi; ek `Fatura_NV-2026-4418.pdf.html` çift uzantılı HTML eki | İZ VAR |

Toplam: İZ VAR 6 + İZ YOK 0 + KANIT YOK 0 = 6.

### URL envanteri (toplam 3 geçiş — ziyaret edilmedi)
"Dosyada yazan (byte-byte)" kolonu dosyadaki satırları olduğu gibi verir (quoted-printable `=3D` ve satır sonundaki yumuşak satır sonu işareti `=` dahil). "QP çözülüp birleştirilmiş" kolonu, aynı değerin `=3D` → `=` çevrimi ve yumuşak satır sonlarının birleştirilmesiyle elde edilen okunur biçimidir; bu kolon bir çözümleme sonucudur, dosyada o dizgi tek parça olarak yazılı değildir.

| # | Satır | Dosyada yazan (byte-byte) | QP çözülüp birleştirilmiş | Gösterilen metin | Kayıtlanabilir alan adı | Not |
|---|---|---|---|---|---|---|
| 1 | 40-41 | satır 40: `<a href=3D"http://nortvale-invoices.example.kyc-dogrulama.example/inv/4418=` · satır 41: `?u=3Dmuhasebe@kartaltekstil.example">https://portal.nortvale.example/fatu=` | `http://nortvale-invoices.example.kyc-dogrulama.example/inv/4418?u=muhasebe@kartaltekstil.example` | `https://portal.nortvale.example/fatura/4418` | `kyc-dogrulama.example` | href ≠ bağlantı metni; iç içe/benzer alan adı; sorgu dizesinde alıcı adresi |
| 2 | 41-42 | satır 41 sonu: `https://portal.nortvale.example/fatu=` · satır 42: `ra/4418</a></p>` | `https://portal.nortvale.example/fatura/4418` | — (bu zaten gösterilen metnin kendisi) | `nortvale.example` | Tıklanabilir hedef değil, yalnızca okuyucuya gösterilen metin |
| 3 | 23 | `X-Mailer: PHPMailer 6.1.6 (https://github.com/PHPMailer/PHPMailer)` | `https://github.com/PHPMailer/PHPMailer` (QP yok, satır bölünmesi yok) | — | `github.com` | `X-Mailer` başlığının parçası; gönderici tarafından sunulan bir bağlantı değil |

Kısaltma servisi, çıplak IP host'u veya QR kodu/görsel dosyada görülmedi. Bu URL'lerin hiçbiri çözümlenmedi, açılmadı, önizlenmedi.

### Ek envanteri (toplam 1 — çalıştırılmadı, çözülmedi)
| # | Satır | Dosya adı | Bildirilen Content-Type | Kodlama | Boyut | Uzantı deseni |
|---|---|---|---|---|---|---|
| 1 | 50-57 | `Fatura_NV-2026-4418.pdf.html` | `text/html; charset=UTF-8` | `base64` | Dosyada beyan edilen boyut yok; base64 gövdesi 4 satır (54-57) | Çift uzantı `.pdf.html`; HTML ek; ad `.pdf` izlenimi verirken bildirilen tip `text/html` |

### IOC listesi (kaynak satırlarıyla; kötücül oldukları doğrulanmamıştır)
- `samples/ornek-phishing.eml:1` — `Return-Path: <billing@nortvale-invoices.example>`
- `samples/ornek-phishing.eml:19` — `From: "Nortvale Lojistik - Muhasebe" <billing@nortvale-invoices.example>`
- `samples/ornek-phishing.eml:20` — `Reply-To: "Nortvale Muhasebe" <nortvale.finance.dept@mailbox-secure.example>`
- `samples/ornek-phishing.eml:6` — gönderen IP `45.133.88.214`, host `smtp-out-7.bulkrelay.example`
- `samples/ornek-phishing.eml:9` / `:24` — köken IP `196.202.14.7`
- `samples/ornek-phishing.eml:17` — `Message-ID: <20261027061433.9c118a2e0f@bulkrelay.example>`
- `samples/ornek-phishing.eml:40` — alan adı `kyc-dogrulama.example` ve URL (yukarıdaki URL envanteri, satır 1)
- `samples/ornek-phishing.eml:52` — ek adı `Fatura_NV-2026-4418.pdf.html`

### İlgili başlık satırları (verbatim)
- `samples/ornek-phishing.eml:9` — `Received: from localhost (unknown [196.202.14.7])`
- `samples/ornek-phishing.eml:13` — `	spf=fail (sender IP is 45.133.88.214) smtp.mailfrom=nortvale-invoices.example;`
- `samples/ornek-phishing.eml:14` — `	dkim=none (message not signed) header.d=none;`
- `samples/ornek-phishing.eml:15` — `	dmarc=fail (p=none sp=none dis=none) header.from=nortvale.example`
- `samples/ornek-phishing.eml:16` — `Received-SPF: fail (nortvale.example: domain of nortvale-invoices.example does not designate 45.133.88.214 as permitted sender) client-ip=45.133.88.214;`
- `samples/ornek-phishing.eml:22` — `Subject: =?UTF-8?B?QUNJTDogw5ZkZW1lIGhlc2FiIGRlxJ9pxZ9pa2xpxJ9pIC0gRmF0dXJhIE5WLTIwMjYtNDQxOA==?=`
- `samples/ornek-phishing.eml:23` — `X-Mailer: PHPMailer 6.1.6 (https://github.com/PHPMailer/PHPMailer)`
- `samples/ornek-phishing.eml:35` — `<p>Banka hesab=C4=B1m=C4=B1z de=C4=9Fi=C5=9Fmi=C5=9Ftir. A=C3=A7=C4=B1k =`
- `samples/ornek-phishing.eml:52` — `Content-Disposition: attachment; filename="Fatura_NV-2026-4418.pdf.html"`

Not: `İZ YOK` sonucu, bu ihracatta gösterge görülmediği anlamına gelir; mesajın meşru olduğunu kanıtlamaz. Bu raporda `İZ YOK` satırı yoktur. Aynı şekilde kayıtlı bir `pass` sonucu yalnızca kimlik doğrulamanın geçtiğini söyler, niyet hakkında bir şey söylemez: ele geçirilmiş gerçek bir posta kutusu da üçünü de geçer.

## Doğrulama Durumu
KABUL — Rapordaki her olgu e-posta dosyasından alıntılanmış bir satıra dayanıyor, her sayı Grep count modundan veya `## Kanıt`'taki madde madde sayımdan geliyor ve 6 zorunlu maddeden hiçbiri `KANIT YOK` değil (6 İZ VAR / 0 İZ YOK / 0 KANIT YOK). Kesin "bu oltalamadır" yargısı yerine gözlenen göstergeler olgu olarak, niyet/gerçek gönderici/bağlantı ve ek davranışı `[DOĞRULANMAMIŞ]` olarak yazılmıştır; itibar, hash ve dinamik analiz kapsam dışıdır.

## Reviewer Kararı
ONAY — tur 2 · Bağımsız denetim P1-P6 tablosunu, URL ve ek sayılarını ve her [OLGU] satırını kaynak dosyadan kendi yöntemiyle yeniden türetti (Python ile satır karşılaştırması, base64 ve quoted-printable çözümü); sayılar tuttu, esaslı hata kalmadı. Tur 1'de üç düzeltme istenmişti — konu satırı transkripsiyonu, URL envanterinin byte-byte kolonu ve Bulgular bölümündeki defang tutarlılığı — üçü de yazarca düzeltildi ve tur 2'de doğrulandı. Bulgu, sayı veya etiket kaymadı.
