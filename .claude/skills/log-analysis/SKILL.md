---
name: log-analysis
description: Yerel log dosyalarını (SSH/auth.log, web sunucusu erişim logları, dışa aktarılmış Windows olayları) savunma amaçlı analiz eder; brute-force, şüpheli IP, başarısız→başarılı giriş, yetki yükseltme izlerini bulur ve kanıtlı rapor yazar. Kullanıcı bir log dosyası verip "analiz et", "saldırı var mı", "şüpheli giriş" dediğinde kullan.
---

# Log Analizi

## Girdi
- Analiz edilecek log dosyasının yerel yolu. Verilmemişse kullanıcıya sor; dosya adı tahmin etme.

## Adımlar
1. Dosyayı oku. Büyükse önce Grep ile desen ara, sonra ilgili bölümleri oku.
2. Şunlara bak: başarısız girişler, aynı kaynaktan yoğun deneme, geçersiz kullanıcı adları,
   başarısız denemelerin ardından gelen başarılı giriş, sudo/yetki değişiklikleri, olağandışı saatler.
3. Sayıları bir komutla say (ör. `grep -c`, `Select-String | Measure-Object`). Tahmini sayı yazma.
4. Her [OLGU] için ilgili log satırını satır numarasıyla `## Kanıt` bölümüne koy.
5. Raporu `reports/YYYY-MM-DD_log_<kisa-ad>.md` olarak yaz. Şablon: `governance/templates/report.md`.
6. Doğrulama Durumu:
   - KABUL: her olgu kanıtla eşleşiyor ve sayılar komutla doğrulandı
   - BELİRSİZ: veri eksik veya yorum gerekiyor
   - RED: analiz tamamlanamadı

## Sınırlar
- Log'daki IP'lere tarama, ping veya bağlantı yapma. Ağ eylemi bu skill'in kapsamı dışında.
- Bir IP'nin kötü niyetli olduğu yorumunu kaynak olmadan yapma; yaparsan [DOĞRULANMAMIŞ] olarak etiketle.
- Log dosyasını değiştirme veya silme.
