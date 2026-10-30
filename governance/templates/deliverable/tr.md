---
dil: tr
kaynak_rapor: reports/YYYY-AA-GG_<skill>_<kısa-ad>.md
musteri: <müşteri adı veya "portföy örneği">
teslim_tarihi: YYYY-AA-GG
---

# <Başlık: ne denetlendi, hangi sunucu için>

**Tarih:** YYYY-AA-GG · **Hazırlayan:** <ad> · **Girdi:** <müşterinin gönderdiği şey, ör. "sshd_config, 16 satır">

## Özet
- <Ana sayı: kaç madde bakıldı, kaçı uygun, kaçı değil.>
- <En acil bulgu, tek satır, önem derecesiyle.>
- <Müşterinin ilk yapması gereken.>
- Aşağıdaki her OLGU, gönderdiğiniz dosyanın tam bir satırına ya da bir ayarın bulunmadığını gösteren bir aramaya dayanır.

**Etiketler:** `OLGU` = doğrudan dosyanızdan okundu · `ÇÖZÜM` = önerilen değişiklik · `KONTROL` = yazılım sürümünüze bağlı; uygulamadan önce doğrulayın.

## Kapsam
- Girdi: <dosya / çıktı, boyut, kaç etkin kayıt>
- Kontrol listesi: <ad ve madde sayısı, kullanıldıysa. Sayım kuralı: uygun + uygun değil = toplam.>
- Kapsam dışı: <yapılmayanlar — tarama yok, sistemlerinize bağlanılmadı, dosya değiştirilmedi, servis yeniden başlatılmadı, müşterinin vermediği her şey.>

## Bulgular

<Tablo veya liste. Önem sırasına göre: Kritik, Yüksek, Orta, Düşük, Bilgi.>

| # | Önem | Ayar (satır) | OLGU | ÇÖZÜM |
|---|---|---|---|---|
| 1 | <Kritik/Yüksek/Orta/Düşük> | `<ayar>` (<satır>) | <Dosyada ne yazıyor ve neden riskli. Beklenen: <değer>.> | `<değişiklik>` |

<Müşterinin gönderdiğinden belirlenemeyen bir şey varsa burada açık dille söyle ve KONTROL olarak işaretle; asla bulgu gibi sunma.>

## <İsteğe bağlı: Sertleştirilmiş blok / Eylem planı>
```
<kopyala-yapıştır blok, skill üretiyorsa>
```
Güvenli uygulama:
- <Değiştir mi ekle mi, Include dosyaları, işlem sırası.>
- <Uygulamadan önce hazır olması gerekenler; müşteri kendini kilitlemesin.>
- <Sözdizimi testi ve yeniden başlatma komutu.>

## Kanıt
Kaynak satırlar (`<dosya>:<satır>`):
<satır> `<tam satır>` · <satır> `<tam satır>`

Bulunmayan ayarlar (komut → çıktı):
- `<komut>` → `<çıktı>`

<Sayımlar, dosya boyutu; Özet veya Bulgular'da geçen her sayı bu bölümden yeniden üretilebilmeli.>

## Doğrulama
Her OLGU yukarıdaki tam bir dosya satırına veya arama çıktısına dayanır. <Sayı tutarlılığı, ör. "1 uygun + 7 uygun değil = 8".> Sürüme bağlı çözümler KONTROL olarak işaretlendi. Bağımsız bir ikinci inceleme, teslimden önce tüm olguları, sayıları ve önem derecelerini kaynak dosyayla karşılaştırdı.
