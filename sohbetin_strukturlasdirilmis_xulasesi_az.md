# Universal AI Agent Governance System — söhbətin strukturlaşdırılmış xülasəsi

**Sənədin hazırlanma tarixi:** 25 oktyabr 2026  
**Dil:** Azərbaycan dili  
**İstinad söhbəti:** “Skills Anlamını Açıklama”  
**Söhbət ID-si:** `6adddb33-9618-83ed-bff5-a6396e4445d4`

## 1. Əhatə və sübut sərhədi

Bu sənəd təkrarı çıxarılmış mövzu və qərar xülasəsidir; sözbəsöz transkript deyil. Əsaslar: istinad söhbətindən oxunan istifadəçi mesajları, istifadəçinin təqdim etdiyi Google AI mətni və cari xülasə tələbi.

Əvvəlki assistant cavablarının tam mətni oxuma alətində açılmadı; onların yerinə məzmun istinadları qaytarıldı. Buna görə görünməyən cavablara dəqiq sitat, əlavə qərar və ya həyata keçirilmiş iş aid edilmir. Aşağıdakı texniki izahlar tələb olunan mövzuların sistemləşdirilməsidir; əvvəlki cavabların sözbəsöz bərpası deyil. Xarici mənbələr bu sənəd üçün ayrıca yoxlanılmayıb.

| İşarə | Mənası |
|---|---|
| **FAKT** | Əlçatan söhbətdə birbaşa görünən məlumat; xarici iddianın doğru olduğunu avtomatik göstərmir. |
| **QƏRAR** | İstifadəçinin ifadə etdiyi istiqamət və ya cari tələbdə qərar kimi göstərdiyi seçim. |
| **TƏKLİF** | İcra və təsdiq tələb edən həll, izah və ya qiymətləndirmə. |
| **YOXLANMAMIŞ İDDİA** | Müstəqil sübutu, ölçməsi və ya aktual yoxlaması olmayan fikir. |
| **AÇIQ MƏSƏLƏ** | Hələ müəyyənləşdirilməyən və ya əlçatan mətnlə həll olunmayan sual. |

## 2. Məqsəd və əsas qərar

**FAKT:** İstifadəçi sistemi universal qurmaq istədiyini bildirib. Əsas narahatlıq agentin yanlış skill seçməsi, təlimatı səhv tətbiq etməsi və nəticəni yoxlamadan təqdim etməsidir.

**QƏRAR — cari tələbdə təsdiqlənən istiqamət:** Universal **AI Agent Governance System**, yəni AI agentlərinin seçimini, səlahiyyətlərini, icrasını və nəticə yoxlamasını idarə edən ümumi sistem əsas götürülür. Quran və Səhih Sünnə Semantik Reyestr Agenti bu ümumi yanaşmanın sahə tətbiqi kimi qiymətləndirilir.

**Sərhəd:** Bu, istiqamət qərarıdır. İşlək sistemin qurulduğunu, sınaqdan keçdiyini və ya səhvsizliyinin təsdiqləndiyini göstərən sübut təqdim edilməyib.

## 3. Mühəndis, alət, skill və agent fərqi

**TƏKLİF — anlayışları ayırmaq üçün işçi model:**

| Anlayış | Rolu | Təkbaşına təmin etmədiyi şey |
|---|---|---|
| **Mühəndis** | Məqsədi, məhdudiyyətləri, arxitekturanı və qəbul meyarlarını müəyyənləşdirir. | Hər icranın avtomatik düzgünlüyü. |
| **Alət — tool** | Axtarış, fayl oxuma, hesablama və yazma kimi konkret əməliyyatı yerinə yetirir. | Nə vaxt və hansı məqsədlə istifadə edilməli olduğuna dair tam qərar. |
| **Skill — bacarıq paketi** | Müəyyən iş üçün təlimat, prosedur, nümunə və lazım gəldikdə köməkçi resursları birləşdirir. | Düzgün seçilməsi və bütün addımlarının məcburi icrası. |
| **Agent** | Tapşırığı şərh edir, skill və alətlər seçir, işi aparır. | Öz qərarının və nəticəsinin müstəqil təsdiqi. |

**FAKT:** İstifadəçinin əvvəlki mesajında seçdiyi mətn yanlış skill seçimi, səhv tətbiq və yoxlanmamış nəticə risklərini açıq qeyd edir.

## 4. İdarəetmə arxitekturası

**TƏKLİF — cari tələbdə adları verilən komponentlərin funksional bölgüsü:**

| Komponent | Vəzifə | Çıxış |
|---|---|---|
| **Skill Router** | Tapşırığa uyğun skill-i, onun əhatəsini və tələb etdiyi girişləri müəyyənləşdirir. Uyğunluq aydın deyilsə bunu bildirir. | Seçim və əsaslandırma, yaxud aydınlaşdırma ehtiyacı. |
| **Policy Gate** | İcradan əvvəl səlahiyyət, məlumat, mənbə və təsdiq şərtlərini yoxlayır. | İcazə, bloklama və ya təsdiq gözləmə. |
| **Executor** | İcazə verilmiş əməliyyatı müəyyən edilmiş sərhədlərdə yerinə yetirir. | Nəticə və icra qeydi. |
| **Validator** | Nəticəni əvvəlcədən müəyyən edilmiş meyarlar və sübutlarla müqayisə edir. | Qəbul, rədd və ya qeyri-müəyyənlik. |

İş axını: **Tapşırıq → Skill Router → Policy Gate → Executor → Validator → təqdimat və ya düzəliş.** Yeni əməliyyat və ya genişlənən əhatə yenidən uyğun yoxlama qapısından keçməlidir.

### Məcburi bloklama

**TƏKLİF:** Məcburi qaydalar yalnız modelə yazılmış xatırlatmalardan ibarət qalmamalıdır. İcra mühiti icazəsiz əməliyyatın başlamasını və yoxlamadan keçməyən nəticənin təsdiqlənmiş kimi təqdim edilməsini texniki olaraq dayandırmalıdır.

- Tələb olunan giriş, səlahiyyət və ya mənbə yoxdursa, asılı əməliyyat bloklanır.
- Məcburi insan təsdiqi yoxdursa, təsdiqdən asılı dəyişiklik gözləyir.
- Validator meyarı ödənmirsə, nəticə qəbul olunmuş kimi təqdim edilmir.
- Yoxlamanın özü işləmirsə, uğur fərz edilmir; səbəb qeyd olunur.

Bloklama səbəbi və davam üçün tələb olunan şərt görünən olmalıdır. Modelin “yoxladım” deməsi ayrıca yoxlama sübutunu əvəz etmir.

**YOXLANMAMIŞ İDDİA:** Bu arxitekturanın bütün səhvləri sıfırlayacağı barədə zəmanət yoxdur. Konkret qaydanın məcburi icrası ilə cavabın semantik doğruluğu ayrı qəbul meyarlarıdır.

**AÇIQ MƏSƏLƏ:** Əvvəlki mesajdakı `0-1-0` işarəsinin mənası və “ikincini seçirəm” ifadəsinin aid olduğu variantlar görünən mətndən müəyyənləşmir; onlara əlavə məna verilməyib.

## 5. Google AI-dən təqdim edilmiş Semantik Reyestr Agenti

### Təqdim olunan konsepsiya

**FAKT:** İstifadəçinin Google AI söhbətindən gətirdiyi mətn aşağıdakı modeli təqdim edir. Bunlar həmin mətnin iddialarıdır, həyata keçirilmiş sistemin sübutu deyil.

- Quranın mövzular üzrə strukturlaşdırılmış reyestr kimi indekslənməsi.
- `qr_db.md` daxilində `Q`, `Ar`, `Tr`, `Sem`, `Sun`, `Ctx` sahələri.
- Orijinal ərəb mətni, tərcümə, semantik şərh, hədis əlaqəsi və müasir tətbiq kontekstinin birləşdirilməsi.
- Custom GPT üzərində kod yazmadan qurulum; Coze-nin alternativ kimi göstərilməsi.
- Code Interpreter-in açıq, Web Search və DALL-E-nin bağlı saxlanması.
- Sıxlaşdırılmış formatla token və sürət üstünlüyü əldə ediləcəyi iddiası.

### Tənqidi qiymətləndirmə

**TƏKLİF — konsepsiyanın qiymətləndirilməsi:**

| Məsələ | Qiymətləndirmə və tələb olunan düzəliş |
|---|---|
| **Reyestr modeli** | Məlumatı tapmaq və müqayisə etmək üçün istifadə oluna bilər. İndeksləmə modeli dini mətnin bütün mənasını əhatə etdiyinin sübutu deyil. |
| **Orijinal mətn və tərcümə** | Ayrı saxlanmalı, tərcüməçi və nəşr göstərilməlidir. Qısa tərcümə tam mətnin əvəzi kimi təqdim edilməməlidir. |
| **`Sem` — semantik təminat** | Sahənin adı məna itkisini aradan qaldırmır. Şərhin müəllifi, mənbəsi və alternativ izahlar göstərilməlidir. |
| **`Sun` — hədis əlaqəsi** | Təkcə toplu adı kifayət sayılmamalıdır: dəqiq istinad, mətn və istifadə edilən qiymətləndirmə mənbəyi qeyd edilməlidir. Ayə–hədis əlaqəsi də ayrıca əsaslandırılmalıdır. |
| **`Ctx` — müasir tətbiq** | Mənbə mətnindən və tarixi şərhdən ayrılmalı; müəllifin və ya modelin çıxarışı kimi işarələnməlidir. |
| **Token optimallaşdırması** | Qısa açarların faktiki qənaəti və cavab keyfiyyətinə təsiri ölçülməlidir. Sıxlaşdırma mənbə və qeyri-müəyyənlik qeydlərini silməməlidir. |
| **“Sistem hazırdır”** | Verilən xülasə hazır məhsul, yoxlanmış məlumat bazası və ya keçilmiş test barədə sübut təqdim etmir. |

**YOXLANMAMIŞ İDDİALAR:** Code Interpreter-in bu iş üçün mütləq şərt olması, Coze-nin uyğun pulsuz alternativ olması və funksiyaları söndürməyin konkret token qənaəti verəcəyi ayrıca təsdiqlənməyib.

**YOXLANMAMIŞ İDDİA — zaman-həssas:** İstifadəçinin işarə etdiyi əvvəlki assistantın **Custom GPT planları haqqında iddiası təsdiqlənməmişdir**. Dəqiq ifadə əlçatan assistant mətnində görünmür. Hansı abunə planında yaratma və ya istifadə imkanının olduğu barədə burada aktual hökm verilmir; tətbiq qərarından əvvəl rəsmi mənbə və yoxlama tarixi ilə təsdiq tələb olunur.

## 6. Açıq Web Search və nəzarətli məlumat qəbulu

**FAKT:** İstifadəçi Web Search-in bağlanmasının yeni mənbə yoxlamasını məhdudlaşdırmasına alternativ istəyib.

**QƏRAR — cari tələbdə göstərilən istiqamət:** **Açıq Web Search + mənbə yoxlaması + quarantine + təsdiq qapısı.** Axtarışın mümkün olması tapılmış məlumatın avtomatik etibarlı bazaya daxil edilməsi demək deyil.

**TƏKLİF — qəbul prosesi:**

1. **Axtarış:** Yeni mənbə namizədləri tapılır; internet məzmunu məlumat kimi qəbul edilir, sistemə əmr kimi yox.
2. **Quarantine — karantin:** Yeni material yoxlanmış bazadan ayrı saxlanır və statusu görünür.
3. **Mənbə yoxlaması:** Müəllif/nəşriyyat, dəqiq istinad, orijinal mətnlə uyğunluq, tarix, kontekst və ziddiyyətlər yoxlanır. Domen adına etibar məzmun yoxlamasını əvəz etmir.
4. **Təsdiq qapısı:** Əvvəlcədən müəyyən edilmiş meyarlar ödənəndə və tələb olunan səlahiyyətli təsdiq alındıqda material qəbul olunur.
5. **Versiyalı qeyd:** Qəbul edilmiş məzmunun mənbəsi, yoxlama əsası və dəyişiklik tarixçəsi saxlanır. Yeni ziddiyyət çıxarsa yenidən baxılır.

Təklif edilən statuslar: **NAMİZƏD → KARANTİNDƏ → YOXLAMADAN KEÇİB → TƏSDİQLƏNİB**; alternativlər: **RƏDD EDİLİB** və **YENİDƏN BAXILIR**. Yoxlamadan keçmə ilə bazaya qəbul təsdiqi ayrıdır. Vaxtın keçməsi təsdiq sayılmır.

## 7. Qərarların qısa reyestri

| ID | Qərar və ya istiqamət | Əsas və vəziyyət |
|---|---|---|
| Q-01 | Universal agent idarəetmə sistemi qurmaq. | Əvvəlki istifadəçi mesajı və cari tələb; istiqamət təsdiqlənir, icra sübutu yoxdur. |
| Q-02 | Skill seçimi, icazə, icra və nəticə yoxlamasını ayırmaq. | Cari tələbdə komponentlər göstərilir; konkret texniki mexanizm açıqdır. |
| Q-03 | Məcburi şərt ödənməyəndə asılı əməliyyatı bloklamaq. | Cari tələbdə əhatə olunur; qaydaların dəqiq siyahısı hazırlanmalıdır. |
| Q-04 | Web Search-i açıq saxlayıb məlumat qəbulunu nəzarətə almaq. | Məhdudlaşdırmayan alternativ istəyi və cari tələb. |
| Q-05 | Faktı, şərhi, təklifi və yoxlanmamış iddianı ayırmaq. | Cari sənəd üçün birbaşa istifadəçi tələbi. |

## 8. Açıq məsələlər və növbəti addımlar

| Açıq məsələ | Növbəti addım |
|---|---|
| Universal nüvənin sərhədləri | İlk istifadə ssenarisini, giriş/çıxışı və uğur meyarlarını yazmaq. |
| Skill seçimi | Skill reyestri, uyğunluq meyarları və seçim qeyri-müəyyən olduqda davranışı müəyyənləşdirmək. |
| Məcburi nəzarət | Policy Gate qaydalarını, bloklama səbəblərini və onları tətbiq edəcək icra qatını seçmək. |
| Mənbə və təsdiq səlahiyyəti | Hansı mənbələrin hansı şərtlərlə qəbul olunacağını və kimin təsdiq verəcəyini müəyyənləşdirmək. |
| Reyestr məlumat modeli | Orijinal mətn, tərcümə, şərh, tətbiq çıxarışı, istinad və yoxlama statusunu ayrı sahələrdə saxlamaq. |
| Platforma seçimi | Custom GPT və digər variantların cari imkanlarını rəsmi mənbələrdən yoxlayıb tələb olunan nəzarətlə müqayisə etmək. |
| Etibarlılığın ölçülməsi | Yanlış skill, çatışmayan mənbə, ziddiyyətli məlumat, təsdiqsiz qəbul və uğursuz yoxlama ssenarilərini sınaqdan keçirmək. |
| Tarixi tamlıq | Əvvəlki assistant cavabları əlçatan olarsa sənədi onlarla tutuşdurmaq; naməlum hissələri təxminlə doldurmamaq. |

**Hazırkı nəticə:** Məqsəd və əsas idarəetmə istiqaməti sənədləşdirilib. Platforma, məlumat bazası, texniki bloklama və qəbul testləri hələ həyata keçirilmiş və təsdiqlənmiş nəticə kimi qeydə alınmır.
