---
name: config-audit
description: Yapılandırma dosyalarını (sshd_config, nginx/apache, dışa aktarılmış firewall kuralları vb.) güvenlik kontrol listesine göre salt-okunur denetler ve sertleştirme önerileri içeren rapor yazar. Kullanıcı bir config dosyası verip "güvenli mi", "denetle", "hardening" dediğinde kullan.
---

# Yapılandırma Denetimi

## Girdi
- Yapılandırma dosyasının yerel yolu ve türü. Tür belli değilse dosya içeriğinden çıkar; emin değilsen sor.

## Adımlar
1. Dosyayı oku. Yorum satırlarını (`#`) etkin ayar sayma; varsayılan değeri ayrıca not et.
2. İlgili kontrol listesini uygula (aşağıda). Her madde için: mevcut değer, beklenen değer, satır numarası.
3. Sonuçları yaz:
   - Uyumsuzluk → `[OLGU]`
   - Düzeltme önerisi → `[ÖNERİ]`
   - Sürüme bağlı varsayılan değerler gibi doğrulanamayan konular → `[DOĞRULANMAMIŞ]`
4. Raporu `reports/YYYY-MM-DD_config_<kisa-ad>.md` olarak yaz. Şablon: `governance/templates/report.md`.

## Kontrol listesi — OpenSSH sshd_config
| Ayar | Beklenen |
|---|---|
| PermitRootLogin | no (veya prohibit-password) |
| PasswordAuthentication | no |
| PermitEmptyPasswords | no |
| MaxAuthTries | 3–4 |
| X11Forwarding | no |
| PubkeyAuthentication | yes |
| LoginGraceTime | ≤ 60 |
| AllowUsers / AllowGroups | tanımlı |

Başka dosya türleri için kontrol listesi henüz yok. Genel ilkelerle değerlendir ve bunu raporun Kapsam bölümünde belirt.

## Sınırlar
- Dosyayı değiştirme. Bu skill yalnızca öneri üretir; değişikliği kullanıcı uygular.
- Servisi yeniden başlatma, firewall kuralı değiştirme.
