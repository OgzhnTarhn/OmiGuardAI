# OmniGuard AI Scenario Matrix

## Amac

Bu dokumanin amaci, OmniGuard AI projesinde hangi yeteneklerin ortak platform uzerinde
calisacagini, hangi use-case'lerin ayri senaryo modulu olarak gelistirilmesi gerektigini,
hangi islerin demo kapsaminda oldugunu ve hangi islerin daha sonraki fazlara kalmasi
gerektigini netlestirmektir.

Ana prensip:

- Tek bir YOLO modeli butun guvenlik problemlerini cozmeyecek.
- Ortak bir goruntu isleme platformu kurulacak.
- Her is problemi ayri bir "scenario module" olarak ele alinacak.
- Backend tarafinda tum event'ler ortak bir contract ile toplanacak.

## Mevcut Durum

Su an sistemin fiilen yaptigi is:

- Kamera veya video kaynagini acmak
- YOLOv8 ile insan tespiti yapmak
- Tracking ile kisiye ID atamak
- Sanal cizgi gecisini tek seferlik ihlal olarak uretmek
- Snapshot almak
- Backend API'ye ihlal event'i gondermek
- Dashboard'da ihlal kaydini gostermek

Su an sistemin yapmadigi is:

- Oda kapasitesi veya rezervasyon mantigi
- Yetkili / yetkisiz kisi ayrimi
- Kasa davranis analizi
- Duman / ates analizi
- Birden fazla senaryoyu ayni anda konfigurable sekilde yonetmek
- Risk seviyesine gore kural motoru calistirmak

## Cekirdek Platform

Asagidaki katmanlar tum senaryolar tarafindan ortak kullanilmalidir:

1. Video ingest
2. Detection
3. Tracking
4. Zone / ROI tanimlari
5. Event contract
6. Snapshot / evidence uretimi
7. Backend delivery
8. Dashboard feed
9. Logging / health / configuration

Bu katmanlar sabit platform olarak dusunulmeli, senaryo bazli mantiklar bunun ustune
eklenmelidir.

## Senaryo Modulleri

| Senaryo | Is amaci | Ortak altyapiyi kullanir mi | Ek input ihtiyaci | Algoritma / mantik | Yanlis alarm riski | Demo uygunlugu | Tahmini efor |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Line crossing | Yasak gecis veya giris-cikis kontrolu | Evet | Cizgi veya zone tanimi | Detection + tracking + line crossing rule | Dusuk | Cok yuksek | 1-2 gun |
| Occupancy overflow | Oda kapasitesi veya rezervasyon limiti asimi | Evet | Zone tanimi, kapasite bilgisi, tercihen backend rezervasyon verisi | Detection + tracking + inside count + business rule | Orta | Cok yuksek | 2-4 gun |
| Restricted zone intrusion | Yetkisiz alana giris | Evet | Yasak alan ROI, kural seti | Detection + tracking + polygon ROI + dwell / cross rule | Dusuk-Orta | Yuksek | 2-4 gun |
| Loitering | Belirli bolgede fazla sure bekleme | Evet | Zone tanimi, sure esigi | Tracking + per-track dwell timer | Orta | Orta-Yuksek | 2-3 gun |
| Tailgating | Pes pese gecis veya tek yetki ile coklu giris | Kismen | Gate mantigi, zaman penceresi, giris yonu | Tracking + ordered crossing events + temporal rule | Orta-Yuksek | Orta | 3-5 gun |
| Cashier anomaly | Kasa cevresinde supheli davranis | Kismen | Kasa ROI, el / obje analizi, POS veya transaction verisi ideal | ROI-based action analysis + temporal anomaly logic | Yuksek | Orta, dikkatli sunulursa | 1-2 hafta |
| Smoke / fire | Yangin veya duman erken uyari | Hayir, ayri inference akisi gerekir | Duman / ates modeli, ayri threshold, alarm policy | Specialized detector veya dedicated classification pipeline | Orta | Yuksek | 3-7 gun |
| Abandoned object | Supheli bir cisim birakilmasi | Kismen | Object classes, zaman bilgisi, zone | Detection + tracking + stationary object logic | Yuksek | Dusuk-Orta | 1-2 hafta |

## Kritik Mimari Kararlar

### 1. Tek model her seyi cozmez

Line crossing, occupancy ve restricted zone gibi use-case'ler ayni insan tespiti ve
tracking altyapisini paylasabilir.

Cashier anomaly ve smoke/fire ise ayri problem tipleridir:

- Cashier anomaly:
  - Davranis analizi ister
  - Sadece "insan var" tespiti yetmez
  - El, kasa alani ve zaman baglami gerekir
  - Mumkunse POS / satis verisi ile desteklenmelidir

- Smoke/fire:
  - Ayrica egitilmis veya ayri optimize edilmis model ister
  - Threshold ve alarm mantigi farklidir
  - Ana insan tespit hattina karistirilmamasi daha sagliklidir

Sonuc:

- Occupancy ile cashier mantigi ayni modul olmamali
- Cashier ile smoke/fire ayni inference karari icinde karistirilmamali
- Event formati ortak olabilir, karar motorlari ayri olmalidir

### 2. Event contract senaryo-tipli olmali

Backend tarafinda tek tip "violation" toplamak yeterli degil. Event contract asagidaki
alanlari desteklemelidir:

- `eventType`
- `severity`
- `cameraId`
- `siteId`
- `zoneId`
- `trackId`
- `occurredAtUtc`
- `snapshotPath`
- `metadata`

Ornek `eventType` degerleri:

- `line_crossing`
- `occupancy_overflow`
- `restricted_zone_intrusion`
- `loitering`
- `tailgating`
- `cashier_anomaly`
- `smoke_detected`
- `fire_detected`

### 3. Zone-first tasarim gerekli

Senaryolarin buyuk bolumu kamera genelinden degil, tanimli bolgelerden cikar:

- oda
- kapi
- koridor
- kasa
- raf alani
- depo girisi

Bu nedenle orta vadede ROI / polygon zone konfigurasyonu ayri bir katman olarak
eklenmelidir.

## MVP Kapsami

Demo icin satilabilir bir ilk kapsam su olmali:

1. Line crossing
2. Occupancy overflow
3. Restricted zone intrusion
4. Dashboard incident feed
5. Snapshot evidence

Bu kombinasyon:

- Teknik olarak gercekci
- Demo'da kolay anlatilir
- Operasyonel faydasi nettir
- Ayni detection/tracking altyapisini tekrar kullanir

## Faz Sonrasi Kapsam

Asagidaki use-case'ler MVP sonrasi ele alinmali:

1. Cashier anomaly
2. Smoke / fire
3. Tailgating
4. Abandoned object

Sebep:

- Daha fazla veri ve tuning isterler
- Yanlis alarm riski daha yuksektir
- Demo hazirligini yavaslatirlar

## Onerilen Yol Haritasi

### Faz 1: Demo Stabilizasyonu

Hedef:

- Line crossing hattini tamamen stabilize etmek
- Snapshot, backend, dashboard zincirini canli test etmek
- Baslatma ve konfigurasyon adimlarini netlestirmek

Teslimatlar:

- Sabit `yolov8m` demo konfigi
- E2E test provasi
- Demo startup checklist

Tahmini sure:

- 2-4 gun

### Faz 2: Occupancy ve Zone Mantigi

Hedef:

- Oda veya alan bazli kisi sayimi
- Rezervasyon veya kapasite limiti asim event'i
- Zone tanimlari icin ilk konfigurasyon katmani

Teslimatlar:

- `occupancy_overflow` event tipi
- Zone counting mantigi
- Dashboard'da kapasite kartlari

Tahmini sure:

- 2-4 gun

### Faz 3: Restricted Zone ve Loitering

Hedef:

- Belirli alanlara izinsiz giris tespiti
- Belirli sure boyunca bolgede kalma tespiti

Teslimatlar:

- Polygon ROI altyapisi
- `restricted_zone_intrusion`
- `loitering`

Tahmini sure:

- 3-5 gun

### Faz 4: Cashier Prototype

Hedef:

- Kasa bolgesini ayri bir senaryo modulu olarak ele almak
- Basit "supheli hareket" seviyesinde bir prototip cikarmak

Teslimatlar:

- Cash desk ROI
- Event tipleri icin net tanim
- Video tabanli ilk anomali kural seti

Not:

"Para caldi" gibi iddiali bir sonuca tek video ile gitmek yerine,
"cashier_anomaly" seviyesinde baslamak daha dogru olur.

Tahmini sure:

- 1-2 hafta

### Faz 5: Smoke / Fire

Hedef:

- Ayrik alarm hattini kurmak
- Duman ve ates gibi guvenlik senaryolarini ayri model ile calistirmak

Teslimatlar:

- Ayri inference pipeline
- Alarm severity ve escalation rule'lari

Tahmini sure:

- 3-7 gun

## Iki Haftalik Uygulama Plani

### Hafta 1

1. AI line crossing hattini canli test et
2. Snapshot ve dashboard kanit akisini dogrula
3. Startup adimlarini dokumante et
4. Event contract'a `eventType` ve `severity` ekle
5. Occupancy counting altyapisina basla

### Hafta 2

1. Occupancy overflow senaryosunu bitir
2. Restricted zone icin ROI mantigini ekle
3. Dashboard'a zone ve capacity gorunurleri ekle
4. Demo script ve sunum akisini netlestir

## Teknik Borclar

Asagidaki konular yakinda ele alinmalidir:

- AI config'inin koddan ayrilip dosya veya env tabanli hale getirilmesi
- Senaryo bazli configuration schema
- Standart event severity modeli
- Kalici veri saklama stratejisi
- Dashboard polling yerine gercek zamanli bildirim
- Snapshot retention politikasi
- Demo ve production ayri config profilleri

## Son Karar

Su an en dogru urun stratejisi su:

- Cekirdek platformu sabitle
- Demo icin 2-3 guclu senaryo sec
- Kasa ve yangin gibi zor use-case'leri ayri moduller olarak planla
- Tum olasi durumlari ayni anda cozmeye calisma

Bu projede bir sonraki teknik hedef:

1. `eventType` ve `severity` alanlarini backend + ai_engine + dashboard tarafinda resmi hale getirmek
2. Occupancy overflow senaryosunu cekirdek platform ustunde eklemek
