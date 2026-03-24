import cv2
from ultralytics import YOLO

# Modeli yükle
model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)

# Sanal sınır çizgisinin Y koordinatı (Ekranın ortasından geçen yatay bir çizgi)
# Eğer ekranın 480 piksel yüksekliğindeyse, çizgi 240. pikselde olacak
SINIR_CİZGİSİ_Y = 240

print("OmniGuard AI Sistemi Başlatıldı. Sınır İhlali Aktif.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Ekrana sanal bir çizgi çiz (Mavi renk, kalınlık 2)
    cv2.line(frame, (0, SINIR_CİZGİSİ_Y), (frame.shape[1], SINIR_CİZGİSİ_Y), (255, 0, 0), 2)
    
    # YOLO ile nesneleri tespit et
    # stream=True ve verbose=False kullanarak terminaldeki gereksiz logları kapatıyoruz
    results = model(frame, stream=True, verbose=False)

    for r in results:
        boxes = r.boxes
        
        for box in boxes:
            # Sadece insanları tespit et (YOLO'da insanın class id'si 0'dır)
            if int(box.cls[0]) == 0:
                # Tespit edilen kişinin kutu koordinatlarını al
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Kişinin tam orta noktasını (merkezini) hesapla
                merkez_y = (y1 + y2) // 2
                
                # Kutuyu yeşil çiz
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Eğer kişinin merkez noktası, sınır çizgisini geçtiyse uyar!
                if merkez_y > SINIR_CİZGİSİ_Y:
                    # Kırmızıya çevir
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, "IHLAL: SINIRI GECTI", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                    
                    # İleride buraya API isteği ekleyeceğiz
                    print("DİKKAT: BİRİ SINIRI GEÇTİ!")

    # Görüntüyü ekrana yansıt
    cv2.imshow("OmniGuard AI - Sınır Kontrolü", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()