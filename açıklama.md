SSCFLP Projesi
===================================================

Hikâye: Mahallede dondurma (veya oyuncak) dağıtmak istiyoruz. Bazı büyük ambarlar (tesisler) var, her birinin taşıyabileceği kadar ürün (kapasite) ve açmak için ödememiz gereken bir kirası (sabit maliyet) var. Mahalledeki çocuklar (müşteriler) dondurma istiyor; her çocuğa götürmenin de bir yol ücreti (atama maliyeti) var. Ama her çocuk yalnızca **tek** ambardan hizmet alabilir (Single Source). Amaç: tüm çocukları doyururken hem kira hem yol ücretini en küçük yapmak.

Bu klasördeki kodlar, `Docs/Project Definition Fall 2025-2026.pdf`’teki bu problemi üç adımda çözüyor:
1) **Hayalî en iyi ihtimali ölç** (Lower Bound – “daha iyisi olamaz” çizgisi)
2) **Hızlı bir başlangıç kur** (Greedy initial solution – “ilk yerleşim”)
3) **Akıllı deneme-yanılma ile iyileştir** (Iterated Tabu Search – “kurallı oyun”)

Her adımı aşağıda tek tek ve günlük hayat benzetmesiyle anlattım; en sonda da tüm dosyaları özetledim.

---------------------------------------
1) Neden Lower Bound buluyoruz, nasıl buluyoruz? (`src/relaxation.py`)
---------------------------------------
Neden: Bir çocuk lego kulesi yaparken “en az şu kadar parça gerekir” diye düşünür. Lower bound tam bu: Mükemmel bir dünya hayal edip “masraf en az şu kadar olur” diyoruz. Bu, ileride bulduğumuz gerçek çözümlerin ne kadar iyi olduğunu kıyaslamak için bir çıta.

Nasıl: İkisini de biraz yumuşatıyoruz (LP relaxation):
- Çocukların bir kısmını bir ambara, diğer kısmını başka ambara bölünebilir varsayıyoruz (gerçekte bölünemez, ama hayalde serbest). Kodda bu `x[i][j]` değişkeni (satır 57): müşteri j’nin ne kadarı tesis i’den alıyor, 0 ile 1 arası serbest.
- Bir tesisi yarım açılmış sayabiliyoruz (`y[i]`, satır 62). Bu da hayal gücü.
- Ama kurallar duruyor:
  - Her çocuk toplamda tam 1 almalı (`∑_i x[i][j] = 1`, satır 73).
  - Her tesisin yükü kapasitesini aşamaz (`∑_j dem[j]*x[i][j] ≤ cap[i]*y[i]`, satır 77).
  - Bir çocuğa hizmet eden tesis en az o kadar “açık” olmalı (`x[i][j] ≤ y[i]`, satır 81).
- Amaç fonksiyonu: Kira + yol ücretlerini en aza indirmek (satır 67-70).
- Çözüm: `pulp` ile sessizce çözüyoruz (`self.prob.solve(...)`, satır 87) ve değer `objective_value` olarak dönüyor (satır 90).

Gerçek hayat benzetmesi: “Şimdilik her bakkaldan yarım ekmek alabilirsin” diye hayal ediyoruz. Bu mümkün değil ama bize “en az kaç adımda doyarız?” sorusunun cevabını verir.

---------------------------------------
2) Başlangıç çözümü nasıl kuruluyor? (`src/initial_solution.py`)
---------------------------------------
Mantık: “Önce en ucuz kira başına en çok kapasite veren depoları aç, sonra her çocuğu en yakındaki açık depoya gönder.”

Adımlar:
1. Her tesis için verim oranı hesaplanıyor: `R_i = sabit_maliyet / kapasite` (satır 68). Bu, “kira başına kaç ürün taşıyabiliyor?” demek.
2. Bu oran artan sırayla sıralanıyor (satır 71) ve toplam kapasite tüm talebi karşılayana kadar tesis açılıyor (satır 78-83).
3. Her çocuk, açık tesisler içinde taşıma maliyeti en düşük olana atanıyor (satır 91-105).
4. Toplam kira ve yol ücretleri hesaplanıyor, toplam maliyet bulunuyor (satır 106-113).
5. Kapasite aşımı var mı diye bakılıyor, ihlaller listeleniyor (satır 114-121).

Gerçek hayat benzetmesi: Pasta dağıtacaksın. Önce “kirası ucuz ama kocaman mutfağı olan pastaneleri” seçiyorsun. Sonra her çocuğa “en yakın pastane”den pasta gönderiyorsun. Eğer bir pastane tepsiye sığmayacak kadar fazla pasta göndermeye kalktıysa “taştı” diye not alıyorsun.

---------------------------------------
3) Komşuluk, Tabu Search ve Perturbation nasıl çalışıyor? (`src/tabu_search.py`)
---------------------------------------
Ana fikir: Bir oyunda piyonları (çocuk-atama kararlarını) ufak ufak oynatarak daha ucuz bir düzen arıyoruz. Aynı hamleyi tekrar tekrar yapmamak için “yasaklı hareket listesi” (tabu) tutuyoruz. Uzun süre ilerleme olmazsa oyunu biraz karıştırıp yeni yollara bakıyoruz (perturbation).

3.1 Durum ve puanlama
- Çözümün içinde: hangi tesisler açık (`open_facilities`), her çocuğun gittiği tesis (`assignments`), her tesisin yükü (`load`), kapasite taşmaları (`total_violation`) var (satır 51-94).
- Puan (objective): `kira + yol + alpha * toplam_taşma` (satır 72-76). `alpha` kapasiteyi aşmanın ceza katsayısı; ceza büyükse sistem taşmayı istemez.

3.2 Komşuluk (neighborhood)
- `beta` kadar (oran) rastgele müşteri seçiyoruz (`_sample_customers`, satır 127-129). Örn. beta=0.4 ise müşterilerin %40’ı çekilişle seçilir.
- **Relocate**: Bir çocuğu şu anki tesisten başka bir tesise taşıma hamlesi (satır 131-141).
- **Swap**: İki çocuğun tesislerini karşılıklı değiştirme hamlesi (satır 143-155).
- Tüm bu hamleler karıştırılıyor (`get_neighbors`, satır 618-621).

3.3 Hamle değerlendirme (delta)
- Bir hamle yapılırsa yeni maliyet ne olur, kapasite taşması nasıl değişir, hızlıca hesaplanıyor (`_evaluate_move_delta`, satır 163-232). Böylece her hamleyi uygulamadan “provada” görüyoruz.

3.4 Tabu listesi ve dinamik süre
- Aynı müşteriyi kısa sürede eski tesisine döndürmek tabu. `tabu_dict` bunu tutuyor (satır 43-47, 326-335).
- Tabu süresi (tenure) dinamik: Aynı hamle çok yapıldıysa süresi uzuyor (`_dynamic_tenure`, satır 337-347). Hamle sıklıkları `move_frequencies` ile tutuluyor.
- İstisna (aspiration): Bir tabu hamle gerçekten daha iyi ve **feasible** bir çözüme götürüyorsa yine de yapılabiliyor (satır 659-666).

3.5 Perturbation (karıştırma)
- Uzun süre iyileşme yoksa (`stagnation >= max_stagnation`, satır 684-688), çözüm biraz sarsılıyor (`perturb`, satır 481-511).
- Hafif karıştırmalar (stagnation küçükken): bir tesis kapat, aç, değiştir; atamaları karıştır vb. (`_op1`…`_op5`, satır 395-455).
- Sert karıştırmalar (stagnation büyükken): 1 kapat 2 aç veya tersi (`_op6`, `_op7`, satır 456-479).
- Her karıştırmadan sonra “açık tesislere tekrar en ucuzdan ata” ile düzen tazeleniyor (`_reassign_all_to_open`, satır 367-394).

3.6 Ana döngü
- `run` fonksiyonu (satır 623-694) şu akışta:
  1. Başlangıç çözümünü iç duruma çevir (`_build_state`).
  2. Komşu hamleleri tara, tabu kontrolü yap, en iyi hamleyi uygula.
  3. Her adımda `alpha` cezasını güncelle (`_update_alpha`, satır 112-123): çözüm uygun ise alpha biraz düşer, değilse artar.
  4. En iyi **uygun** çözümü hatırla.
  5. Çok duraksarsak perturbation ile sars.
  6. Döngü bitince son bir “kira pahalı tesisi kapatmayı dene” adımıyla temizle (`_greedy_drop`, satır 513-545).

Gerçek hayat benzetmesi: Lego şehrinde çocukları evlere dağıtıyorsun. Bir çocuğu başka eve taşımak (relocate) ya da iki çocuğun evlerini değiştirmek (swap) gibi hamleler yapıyorsun. “Az önce bu çocuğu oraya yollamıştın, hemen geri gönderme” diye kısa süreli yasak koyuyorsun (tabu). Uzun süre yeni güzel bir düzen bulamazsan, “herkes kalksın biraz yer değiştirsin” diyerek odayı karıştırıyorsun (perturbation). En son, “bu pahalı ev boş kalsın, çocukları diğer evlere taşıyalım” diyerek maliyeti düşürüyorsun.

---------------------------------------
4) Parametrelerin mantığı ve kodda nerede kullanılıyor?
---------------------------------------
- **alpha (varsayılan 1000.0)**: Kapasite aşım cezası katsayısı. Ne kadar büyükse taşmak çok pahalı olur. Kullanım: amaç fonksiyonunda (`objective`, satır 72-76) ve tüm delta hesaplarında (`new_obj = ... + alpha * violation`, örn. satır 205-230). Güncelleme: `_update_alpha` (satır 112-123) uygun çözümde alpha’yı biraz azaltır, uygunsuzda artırır. Benzetme: Halıya su dökmenin cezası; çok yüksekse kimse su dökmek istemez.
- **epsilon (varsayılan 0.1)**: Alpha’nın ne hızla değişeceğini belirleyen oran. `_update_alpha` içinde `factor = 1+epsilon` (satır 117-122). Benzetme: Cezayı artırıp azaltırken atılan adım büyüklüğü; 0.1 demek %10 art/azalt.
- **beta (varsayılan 0.4)**: Her iterasyonda kaç müşterinin komşulukta deneneceğini belirleyen örnekleme oranı. `_sample_customers` (satır 127-129) `ceil(beta * n)` kadar müşteri seçer. Benzetme: Sınıfta kaç çocuğun yerini değiştirmeyi deniyorsun; beta yükseldikçe daha çok çocukla oynarsın (daha büyük komşuluk, daha pahalı hesap).
- **max_stagnation (varsayılan 40)**: Kaç ardışık “iyileşmedi” adımından sonra pertürbasyon yapılacağını söyler. Ana döngüde kontrol (satır 684-688); ayrıca seçilecek operatörün hafif/sert olmasını belirler (`perturb`, satır 481-505). Benzetme: Oyun sıkıcılaşınca “hadi baştan karıştıralım” deme eşiği.
- **max_iterations (varsayılan 300)**: Ana döngünün üst sınırı (`run`, satır 623, 638). Benzetme: Oyunu kaç tur oynayacağın.
- **random_seed**: Rastgeleliğin tekrar edilebilir olması için kullanılıyor (satır 41). Benzetme: Zarın hep aynı sırayla düşmesi için hafif manyetik zar kullanmak.

---------------------------------------
5) Adım adım akış (Project Definition’a göre)
---------------------------------------
1. **Veriyi oku** (notebooklarda ilk hücreler): Kapasiteler, talepler, sabit maliyetler, taşıma maliyetleri.
2. **Hayalî en iyi değer (Lower Bound)**: `SSCFLPLowerBound.solve()` ile LP çözülür, çıta değeri alınır.
3. **İlk çözüm**: `SSCFLPInitialSolution.construct()` ile ucuz/kârlı tesisler açılır, çocuklar en ucuz açık tesise atanır.
4. **Tabu Search’ü başlat**: `SSCFLPTabuSearch.run(initial, lower_bound=...)` çağrılır.
   - Her 100 adımda özet basılır (satır 639-645).
   - Komşu hamleler denenir, tabu/aspiration uygulanır.
   - `alpha` uyarlanır; stagnation sayacı tutulur; gerekirse perturbation yapılır.
5. **Son düzenleme**: `run` bittiğinde `greedy_drop` pahalı tesisleri kapatmayı dener.
6. **Raporla**: `print_detailed_report` çözümü insan okuyacağı şekilde listeler.

---------------------------------------
6) Dosyaları tek tek özet
---------------------------------------
- `src/relaxation.py`: LP gevşetmesiyle lower bound hesaplar; `pulp` kullanır.
- `src/initial_solution.py`: Greedy başlangıç kurar; tesisleri verim oranına göre açar, çocukları en ucuz açık tesise yollar.
- `src/tabu_search.py`: Tüm iyileştirme burada; tabu listesi, dinamik tabu süresi, ceza güncellemesi, komşuluk (relocate/swap), perturbation, son kapanış temizliği.
- `51-instance.ipynb`, `55-instance.ipynb`, `63-instance.ipynb`: Üç örnek veri seti için uçtan uca çalıştırma; okuma → lower bound → initial → tabu → rapor.
- `README.md`: Kısa proje tanıtımı ve çalışma talimatı.

---------------------------------------
7) Kısa gerçek hayat analojisi özet
---------------------------------------
- Lower bound: “Hayal dünyasında, herkes ekmeği bölüşebilir; en az kaç liraya doyarız?”
- Initial solution: “Önce kira/kapasite oranı en iyi fırınları aç, herkesi en yakına gönder.”
- Tabu search: “Herkesi az az yer değiştir, son hamleleri unutmayacak bir yasak listesi tut, sıkılırsan oyunu karıştır, pahalı fırınları kapatmayı son kez dene.”

Bu dosya, proje kodlarını arkadaşlarının kolayca takip etmesi için hazırlanmıştır. Kod içi satır referansları yukarıda verilmiştir; detaylı davranış için ilgili `src` dosyalarındaki fonksiyonlara bakabilirsin.

---------------------------------------
8) Satır satır kod açıklamaları (`src` klasörü)
---------------------------------------

Not: Satır numaraları mevcut dosya sürümüne göredir; küçük kaymalar olabilir. Her satır aralığını kısa yorumla açıkladım.

8.1 `src/initial_solution.py`
- 1: `numpy` importu.
- 4-8: Sınıf tanımı ve docstring; problemin ne yaptığı.
- 10-35: Kurucu (`__init__`); giriş verilerini saklar, çözüm alanlarını None başlatır.
- 37-45: Çözüm alanlarının açıklaması (açık tesisler, atamalar, maliyetler, ihlaller).
- 46-66: `construct` başlar; algoritma adımlarını belgeleyen docstring.
- 67: Verim oranı hesabı `fixed_costs / capacities`.
- 70-72: Tesisleri verime göre sırala.
- 73-83: Toplam kapasite talebi geçene kadar tesis aç.
- 84-90: Açık tesis kümesi; atama sözlüğü ve talep sayaçları hazırla.
- 91-105: Her müşteri için en ucuz açık tesisi bul ve ata; tesis yükünü güncelle.
- 106-113: Toplam sabit ve atama maliyeti, toplam maliyet hesapla.
- 114-121: Kapasite aşımı kontrolü ve ihlal sözlüğü.
- 122-132: Feasible bayrağı, çözümü sözlük olarak döndür.
- 134-171: `print_solution_summary`; özet metin çıktısı, kapasite kullanım hesapları.

8.2 `src/relaxation.py`
- 1-2: `numpy`, `pulp` importları.
- 5-9: Sınıf ve docstring.
- 11-37: Kurucu; boyutlar ve verileri saklar, LP değişkenleri başlatılacak alanlar.
- 44-93: `solve` fonksiyonu.
  - 54: LP problemi minimize olarak kuruluyor.
  - 57-61: `x[i][j]` sürekli değişkenleri (0-1 arası) tanımlanıyor.
  - 62-64: `y[i]` sürekli açma değişkeni tanımlanıyor.
  - 66-70: Amaç: sabit + atama maliyeti toplamı.
  - 72-75: Her müşteri tam 1 olmalı kısıtı.
  - 76-79: Kapasite kısıtı (talep ≤ kapasite*y).
  - 81-84: Güçlü bağlama kısıtı `x ≤ y`.
  - 86-88: CBC çözücü çağrısı (sessiz).
  - 89-93: Amaç değeri saklanır ve döndürülür.
- 95-118: `get_open_facilities`; y değerlerinden açık tesis listesi.
- 119-144: `get_customer_assignments`; her müşteri için anlamlı `x` değerlerini döndürür.
- 146-166: `get_facility_utilization`; kullanılan kapasite ve yüzde.
- 168-197: Toplam talep ve kapasite kullanım hesaplayan yardımcılar.
- 199-247: `print_solution_summary`; alt fonksiyonları çağırarak rapor basar.

8.3 `src/tabu_search.py`
- 1-8: Importlar (`math`, `random`, `defaultdict`, `deepcopy`, `typing`, `numpy`).
- 10-15: Sınıf ve kısa docstring.
- 16-47: Kurucu; parametrelerin saklanması, RNG, tabu ve frekans sözlükleri.
- 51-95: `_build_state`; verilen başlangıç çözümünden dahili mutasyon yapılabilir durum kurar (açık set, yükler, maliyetler, ihlaller, objective).
- 96-111: `_clone_solution`; saklamak için hafif kopya üretir.
- 112-123: `_update_alpha`; epsilon oranıyla ceza katsayısını arttırır/azaltır, min-max sınırlar.
- 127-129: `_sample_customers`; beta oranında müşteri seçer.
- 131-141: `_relocate_moves`; seçilen müşteriler için tüm olası yeni tesislere taşıma hamleleri üretir.
- 143-155: `_swap_moves`; seçilen müşterilerden ikililer için tesis değiş tokuş hamleleri.
- 160-162: `_delta_violation`; kapasite ihlali değişimini hesaplar.
- 163-232: `_evaluate_move_delta`; relocate/swap hamlesinin maliyet, ihlal ve feasibility etkisini simüle eder, uygulamadan döner.
- 237-320: `_apply_move_in_place`; seçilen hamleyi gerçek çözüme uygular, maliyetleri, açık seti, yükleri, ihlalleri ve objective’i günceller.
- 324-335: `_is_tabu`; hamlenin tabu olup olmadığını kontrol eder (müşteri, önceki tesis anahtarı).
- 337-347: `_dynamic_tenure`; hamle frekansına göre tabu süresini belirler.
- 348-363: `_update_tabu`; yapılan hamleyi tabu sözlüğüne ekler, frekansları artırır.
- 365-394: `_reassign_all_to_open`; açık tesislere en ucuzdan yeniden atama, maliyet ve ihlal reseti.
- 395-479: Perturbation operatörleri `_op1`…`_op7`; tesis aç/kapat/karıştır varyantları.
- 481-511: `perturb`; stagnation’a göre hafif/sert operatör seçer, sonra yeniden atar.
- 513-545: `_greedy_drop`; pahalı tesisleri kapatmayı deneyerek son iyileştirme yapar.
- 550-614: `print_detailed_report`; bulunan çözümün okunaklı raporu.
- 618-621: `get_neighbors`; relocate+swap hamle listesini döndürür.
- 623-694: `run`; ana iterasyon döngüsü, komşu tarama, tabu/aspiration, alpha güncelleme, stagnation sayacı, perturbation tetikleme ve final greedy_drop.

Bu satır özetleri, her kod parçasının ne yaptığını hızlıca bulman için hazırlandı. Daha derin inceleme için ilgili fonksiyonların içinde yorumlarda belirtilen matematiksel karşılıkları takip edebilirsin.

---------------------------------------------------------------------------------------------------------------------------
Operatörler (1..7)

_op1_close — "Rastgele 1 open kapat"
Ne yapar: new_sol["open_facilities"] içinden rastgele bir açık tesisi seçip kapatır (sadece eğer en az 2 açık tesis varsa).
Kısıt: açık tesis sayısı 1'e düşürülmez (en az bir açık tesis bırakılır).
Etki: tesis sayısını bir azaltır; bu durum atama maliyetlerini artırıp sabit maliyetleri azaltabilir. Sonrasında reassign ile müşteriler en iyi kalan açık tesislere yönlendirilir.
Amaç: hafif çeşitlendirme / yoğunlaştırma dengesi (küçük değişiklik).
_op2_open — "Rastgele 1 closed aç"
Ne yapar: şu an kapalı olan tesislerden rastgele birini açar (eğer kapalı varsa).
Etki: açık tesis sayısını bir artırır; sabit maliyet artar, atama maliyetleri azalabilir.
Amaç: kapasite/atama maliyetlerini düzeltmek veya yeni bölgeler keşfetmek.
_op3_swap_open_close — "Rastgele 1 open kapat, 1 closed aç (swap)"
Ne yapar: mevcut açık tesislerden rastgele birini kapatıp, kapalı tesislerden rastgele birini açar (her iki küme doluysa).
Etki: açık-set'te tek bir tesis değişimi yapar — sabit maliyet değişimi küçük olabilir ama müşteri atamalar değişir.
Amaç: mevcut açık tesis kombinasyonunu hafifçe değiştirmek; bölgesel yeniden yapılandırma.
_op4_shuffle_assignments — "Açık tesisler korunur, rastgele atama (sonrasında yeniden atama)"
Ne yapar (kodda):
Önce tüm müşteri atamalarını rastgele açık tesisler arasından seçerek doldurur (counts, load, assign_cost güncellenir).
Ardından fonksiyon içinde self._reassign_all_to_open(new_sol) çağırılır — bu, her müşteriyi açık tesisler arasından EN UCUZ tesisine yeniden atar ve önceki rastgele atamayı geçersiz kılar.
Net etki: Sonuçta new_sol müşterileri yine en ucuz açık tesise atanmış olur; dolayısıyla rastgele atamanın bir etkisi kalmaz. Ancak perturb() dışındaki diğer akışlar veya farklı versiyonlarda rastgele atamanın kalıcı olması istenmiş olabilir.
Amaç (muhtemel niyet): atamaları karıştırıp ardından yeniden dengeli bir atamaya izin vererek çeşitlendirme. (Gerçekte kodda reassign ile rastgele atama iptal ediliyor — bunu dikkat etmek gerek.)
Not: Kodun şu haliyle _op4 içindeki rastgele atama adımı gereksiz görünüyor çünkü hemen sonra greedy reassign yapılıyor.
_op5_close_half — "Açık tesislerin yaklaşık yarısını kapat"
Ne yapar: eğer açık tesis sayısı > 1 ise, açık tesislerin yaklaşık yarısını (k = max(1, len(open)//2)) rastgele seçip kapatır; kapatma sırasında yine en az 1 açık tesis bırakılır.
Etki: Açık tesis sayısını önemli ölçüde azaltır; bu güçlü bir perturbasyondur (çok sayıda müşteri yeniden atanmak zorunda kalır).
Amaç: orta-şiddette çeşitlendirme — lokal minimumlardan sıyrılmak için daha büyük bir değişiklik.
_op6_close1_open2 — "1 open kapat, 2 closed aç (güçlü)"
Ne yapar: bir açık tesis rastgele kapatılır (varsa) ve kapalı tesislerden en fazla 2 tane rastgele açılır.
Etki: net olarak açık tesis sayısını bir artırır ( -1 + up to +2 = +1 veya +0). Oldukça agresif bir değişiklik; açık set hem daraltılıp hem genişletilebiliyor.
Amaç: stagnasyon durumunda daha agresif çeşitlendirme — yeni bölgelere açılmak ve mevcut kötü yapılandırmaları bozmak.
_op7_open1_close2 — "1 closed aç, 2 open kapat (güçlü)"
Ne yapar: önce kapalı tesislerden rastgele 1 açar (eğer kapalı varsa). Sonra açık setten (en az 1 açık kalacak şekilde) 1 veya 2 tesis rastgele kapatır (close_count=min(2, max(0, len(open)-1))).
Etki: net olarak açık tesis sayısını azaltma eğiliminde olabilir (önce +1 sonra -1 veya -2). Oldukça agresif; bazı bölgeleri kapatıp farklı bir tesis açarak büyük yeniden atamalar tetikler.
Amaç: stagnasyon durumunda radikal yeniden düzenleme — hem çeşitlendirme hem spesifik yapıların yıkılması.
Ek detaylar / kullanışlı gözlemler

Basit vs güçlü operatörler: perturb() basitleri (op1..op5) normal stagnasyonlarda, güçlüleri (op6..op7) uzun stagnasyonlarda kullanır. Bu klasik bir strateji: önce hafif değişikliklerle iyileşme denenir; uzun süre ilerleme yoksa daha büyük bozmalar yapılır.
Her operasyon rastgele seçimlere dayanır (self.rng), dolayısıyla her çalıştırmada farklı etkiler üretilir.
perturb() sonunda kesinlikle self._reassign_all_to_open çağrılır — bu, yalnızca open_facilities değişikliklerinin kalıcı olacağı, müşteri atamalarının her zaman bu yeni açık tesislere göre yeniden belirleneceği anlamına gelir.
_op4 içindeki rastgele atama + hemen kapanıp greedy reassign davranışı muhtemelen bir küçük kodsel tutarsızlıktır: rastgele atama yapılmış olsa bile hemen üzerine greedy reassign ile kaybolur.
Tüm operatörler "open_facilities" set'ini garantiye alır (en az 1 açık tesis bırakmak gibi) — bu, geçersiz çözümler oluşmasını engeller.
Pratik etkiler / ne zaman hangi operatör işe yarar

Küçük lokal düzeltmeler: op1, op2, op3 — yerel iyileştirme için uygundur.
Orta çaplı yeniden düzenleme: op5 (yarısını kapat) — radikal ama hala kontrollü.
Agresif çeşitlendirme (stagnasyonda): op6, op7 — yeni bölgeleri keşfetmek, yerel tuzaklardan çıkmak.
op4 mantıklı yazılsaydı atamalar üzerinden çeşitlendirme sağlar; mevcut implementasyonda etkisi sınırlı çünkü reassign ile siliniyor.
İyileştirme önerileri (opsiyonel)

_op4: eğer amaç gerçekten rastgele atama yaratıp onu değerlendirmekse, _reassign_all_to_open çağrısını op4 içinde değil yalnızca perturb() sonunda yapmak mantıklı; ya da op4'ün rastgele ataması korunmalı (yani op4 sonunda greedy reassign iptal edilmeli) — aksi halde rastgele adım boşa gider.
Operatör ağırlıkları: şu an seçim tamamen eşit olasılıklı; belirli problemlerde bazı operatörler daha faydalıdır. Ağırlıklı seçim (örn. op5 daha seyrek) denenebilir.
Güçlü operatörleri parametrik yapmak: op6/op7 şiddetini (açılacak/kapancak tesis sayısı) parametreleştirebilirsiniz.
Determinizm kontrolü için RNG seed ve reproducibility logları tutulabilir.
İsterseniz her bir operatörün öncesi/sonrası open_facilities ve birkaç müşteri ataması gösteren küçük örnek (örnek veri üzerinde) hazırlayıp adım adım nasıl değiştiğini gösterebilirim. Hangi boyutta (ör. m=10, n=20) bir örnek istersiniz?
