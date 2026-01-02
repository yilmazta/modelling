SSCFLP Projesi — Güncel Kod Açıklaması (2026)
=============================================

Hikâye (kısa): Mahalledeki çocuklara dondurma dağıtıyoruz. Depolarımız (tesisler) var; her birinin açma kirası (sabit maliyet) ve taşıyabileceği maksimum ürün miktarı (kapasite) var. Her çocuğa bir depodan ürün gönderiyoruz; taşımanın da bir bedeli (atama maliyeti) var. Her çocuk **yalnızca tek** depodan hizmet alabilir (Single Source). Amaç: toplam kira + taşıma maliyetini en aza indirmek, kapasiteyi aşmadan (ya da aşarsak ağır ceza ödeyerek).

Bu klasördeki üç Python dosyası problemi sırasıyla çözüyor:
1) **Hayali en iyi sınır**: `src/relaxation.py` LP gevşetmesiyle alt sınır (lower bound) bulur.
2) **Greedy başlangıç**: `src/initial_solution.py` hızlı bir uygulanabilir/uygulanamaz başlangıç kurar.
3) **Iterated Tabu Search**: `src/tabu_search.py` başlangıcı iyileştirir, tabu listesi ve pertürbasyon kullanır, sonunda pahalı tesisleri kapatmayı dener.

----------------------------------------------------------------
1) Lower Bound nasıl kuruluyor? (`src/relaxation.py`)
----------------------------------------------------------------
Neden: “Mükemmel dünyada masraf en az kaç olur?” sorusunun cevabını verir. Bu değeri, bulduğumuz gerçek çözümlerle kıyaslayıp ne kadar yaklaştığımızı görürüz.

Nasıl:
- Karar değişkenleri sürekli: `x[i][j]` (müşteri j’nin ne kadarı tesis i’den servis alıyor, 0–1 arası) ve `y[i]` (tesis i ne kadar açık, 0–1 arası).
- Amaç: `∑ sabit_maliyet[i]*y[i] + ∑ atama_maliyeti[i][j]*x[i][j]` minimize.
- Kısıtlar:
  - Her müşteri tam 1 alır: `∑_i x[i][j] = 1`.
  - Kapasite: `∑_j talep[j]*x[i][j] ≤ kapasite[i]*y[i]`.
  - Güçlü bağlama: `x[i][j] ≤ y[i]` (bir çocuk o depodan hizmet alıyorsa depo o oranda “açık” olmalı).
- Çözüm: `pulp` ile CBC çözücüsü sessiz çalıştırılır; amaç değeri `objective_value` olarak saklanır.
- Yardımcılar: Açık tesis listesi (`get_open_facilities`), müşterilerin paylaştırılması (`get_customer_assignments`), kapasite kullanım raporu (`get_facility_utilization`) ve özet yazdırma (`print_solution_summary`).

Analojik ifade: “Ekmekleri bölüp paylaşmak serbest” diye hayal edip minimum masrafı hesaplıyoruz; gerçek dünyada bundan daha ucuza inemeyiz.

----------------------------------------------------------------
2) Greedy başlangıç çözümü (`src/initial_solution.py`)
----------------------------------------------------------------
Mantık: “Kira/kapasite oranı en iyi depoları sırayla aç, toplam kapasite talebi geçince dur; sonra her çocuğu en ucuz açık depoya bağla.”

Adımlar:
1. Verim oranı: `R_i = sabit_maliyet[i] / kapasite[i]`.
2. Depoları `R_i` artan şekilde sırala.
3. Toplam açık kapasite tüm talebi geçene kadar depo aç.
4. Her müşteri için açık depolar arasında en düşük atama maliyetine sahip olanı seç ve ata.
5. Maliyetleri hesapla: sabit + atama = toplam maliyet.
6. Her açık depo için yük > kapasite ise ihlal miktarını kaydet; `is_feasible` buna göre belirlenir.
7. Sonuç sözlüğü döner (`open_facilities`, `assignments`, maliyetler, ihlaller, uygulanabilirlik).
8. `print_solution_summary` çıktısı; kapasite kullanım yüzdelerini ve ihlalleri gösterir.

Analojik ifade: “Kirası ucuz ve büyük mutfaklı pastaneleri sırayla aç, çocukları en yakına gönder; taşma olursa not et.”

----------------------------------------------------------------
3) Tabu Search + Perturbation + Son Temizlik (`src/tabu_search.py`)
----------------------------------------------------------------
Ana fikir: Mevcut atamaları küçük hamlelerle değiştir, kısa süre önce geri dönülen hamleleri tabu say, uzun süre iyileşme olmazsa çözümü sars (perturb), sonunda pahalı depoları kapatmayı dene.

3.1 Durum (state) ve skor
- Dahili alanlar: `open_facilities` (sıralı liste), `open_set` (hızlı bakış), `assignments` (müşteri -> depo), `counts` (her depoya atanan müşteri sayısı), `load` (her deponun toplam talebi), `capacity_violations` (fazlalıklar), `total_fixed_cost`, `total_assignment_cost`, `total_violation`, `objective`.
- Puanlama: `objective = sabit + atama + alpha * toplam_ihlâl`. Feasible ise `total_violation = 0`, objective = gerçek toplam maliyet. Infeasible ise ceza eklenir.
- Başlangıç: `_build_state` verilen çözümü liste/array haline çevirir, ataması olan depoyu otomatik “açık” kabul eder, objective ve ihlalleri hesaplar. `lower_bound` varsa saklar.
- Kopyalama: `_clone_solution` raporlamaya uygun hafif kopya döner (toplam maliyet ve feasibility bilgisi içerir).

3.2 Komşuluk (neighborhood)
- Örnekleme: `_sample_customers` `ceil(beta * n)` kadar müşteriyi rastgele çeker.
- Relocate hamleleri: Seçilen her müşteri j için mevcut depo k’dan tüm diğer depolara l taşımayı dener (`_relocate_moves`).
- Swap hamleleri: Seçilen müşteri çiftleri (j1, j2) farklı depolardaysa yer değişimini dener (`_swap_moves`).
- Komşular: `get_neighbors` relocate + swap listesini karıştırır (shuffle) ve döner.

3.3 Hızlı değerlendirme (delta)
- `_evaluate_move_delta` çözümü değiştirmeden hamlenin etkisini hesaplar.
- Relocate:
  - Atama maliyeti farkı (`delta_assign`).
  - Sabit maliyet farkı: Yeni depo ilk kez açılıyorsa sabit maliyet eklenir; mevcut depo boşalıyorsa sabit maliyet düşülür.
  - İhlal farkı yalnızca etkilenen depolar (k, l) için hesaplanır.
  - Yeni objective = (sabit + atama + alpha * ihlal).
- Swap: Benzer ama sabit maliyet değişmez; iki deponun yük değişimleri ve ihlal farkı hesaplanır.
- Dönen değer: `(yeni_objective, yeni_feasible_mi, delta_objective)`.

3.4 Hamleyi uygulama ve tabu
- `_apply_move_in_place` seçilen hamleyi gerçekten uygular; maliyetler, yükler, ihlaller, açık set ve objective güncellenir.
- Tabu yapısı: `tabu_dict[(müşteri, önceki_depo)] = sona_erecek_iter`. Hem relocate hem swap için ilgili müşteri-eski depo ikilileri tutulur.
- Tenure: `_get_tabu_tenure` min–max aralığında rastgele tam sayı döner (`tabu_tenure_min`, `tabu_tenure_max`). Dinamik frekans hesabı yok; basit rastgele süre var.
- `_is_tabu` seçilen hamlenin tabu olup olmadığına bakar. Aspiration: Hamle tabu olsa bile **uygun** ve şimdiye kadarki en iyi objective’i iyileştiriyorsa kabul edilir.
- `_update_tabu` seçilen hamleyi tabu listesine ekler.

3.5 Ceza katsayısı güncellemesi
- `_update_alpha`: Eğer mevcut çözüm feasible ise `alpha` `1/(1+epsilon)` oranında azaltılır; değilse `(1+epsilon)` ile çarpılır. Aşırı değerleri önlemek için `[1e-6, 1e9]` aralığında sıkıştırılır.

3.6 Perturbation (çözümü sarsma)
- Amaç: Stagnation (art arda iyileşmeme) durumunda farklı bölgeye sıçramak.
- Operatörler:
  - `_op1_close`: Rastgele bir açık depoyu kapat (en az bir depo kalsın).
  - `_op2_open`: Rastgele bir kapalı depoyu aç.
  - `_op3_swap_open_close`: Açık bir depoyu kapatıp rastgele kapalı bir depoyu aç.
  - `_op4_shuffle_assignments`: Açık seti koruyup müşterileri rastgele açık depolara dağıt, ardından yeniden en ucuzdan ata.
  - `_op5_close_half`: Açık depoların yaklaşık yarısını rastgele kapat (en az bir depo kalsın).
  - `_op6_close1_open2`: Tanımlı ama mevcut pertürbasyon akışında çağrılmıyor.
  - `_op7_open1_close2`: Bir kapalı depoyu aç, sonra mümkünse iki depoyu kapat (en az bir depo kalsın); sabit maliyeti düşürmeye odaklı sert hamle.
- `perturb`: Stagnation < `max_stagnation` ise 1–5 arasından rastgele seçer; eşik veya üstü ise **hep `_op7`** kullanır. Sonrasında `_reassign_all_to_open` ile herkesi mevcut açık set içindeki en ucuz depoya yeniden atar, maliyet/ihlâl/feasibility baştan hesaplanır.

3.7 Son temizlik (greedy drop)
- `_greedy_drop`: En iyi feasible çözüm üzerinde çalışır. Sabit maliyeti yüksek depolardan başlayarak bir depoyu kapatmayı dener, ardından herkesi açık depolara en ucuzdan yeniden atar. Feasible kalır ve objective iyileşirse kapanış kalıcı olur; iyileşme bittiğinde çıkan çözüm clone’lanarak döner.

3.8 Raporlama
- `print_detailed_report`: Toplam maliyet, feasibility, açık depo sayısı, alt sınır farkı (lower_bound varsa) ve her depo için yük, kapasite, atanan müşteriler, ihlaller listesini yazar. `lower_bound` sağlanmadıysa boşluk “N/A” olarak belirtilir.

3.9 Ana döngü (`run`)
- Opsiyonel: Kullanıcı `lower_bound` verirse başlangıç sözlüğüne eklenir.
- Başlangıç: `_build_state(initial)` ile dahili durum kurulur.
- Başlangıç feasible ise `best_feasible` ve objective saklanır; değilse `best_feasible` None başlar.
- Her 100 iterasyonda kısa özet log basılır.
- Her iterasyonda:
  1) Komşular üret ve karıştır.
  2) Tabu kontrolü + aspiration ile en düşük objective’li hamleyi seç.
  3) Hamleyi uygula, tabu listesine ekle, `alpha`yı feasibility’ye göre güncelle.
  4) Feasible ve objective iyileştiriyorsa en iyi çözüme yaz, stagnation=0; aksi halde stagnation++.
  5) `stagnation >= max_stagnation` olursa `perturb` çağrılır, stagnation sıfırlanır.
- Döngü biterse:
  - Hiç feasible bulunamadıysa mevcut çözümün klonu döner (infeasible olabilir).
  - Feasible bulunduysa `_greedy_drop` ile son kapanış temizliği yapılıp döner.

Analojik ifade: Lego şehrinde çocukları evlere dağıtıyorsun; yakın zamanda geri dönüşü yasaklıyorsun (tabu). Uzun süre iyileşme yoksa “herkes biraz yer değiştiriyor” diye odayı karıştırıyorsun. Oyun bittiğinde “kirası pahalı evleri kapatabiliyor muyuz?” diye bakıp son kez düzenliyorsun.

----------------------------------------------------------------
4) Parametre rehberi (varsayılanlar)
----------------------------------------------------------------
- `max_iterations=300`: Ana döngü üst sınırı.
- `alpha=1000.0`: Kapasite ihlâl ceza katsayısı (objective’ta çarpılır).
- `epsilon=0.1`: `alpha` artış/azalış oranı (±%10).
- `beta=0.4`: Her iterasyonda rastgele denenecek müşteri oranı (`ceil(beta*n)`).
- `max_stagnation=40`: Bu kadar ardışık iyileşmeme sonrası pertürbasyon.
- `tabu_tenure_min=10`, `tabu_tenure_max=30`: Tabu süresi için alt/üst sınır; her hamlede bu aralıktan rastgele seçilir.
- `random_seed=None`: Verilirse tüm rastgelelik tekrar üretilebilir olur.

----------------------------------------------------------------
5) Uçtan uca akış (notebooklarda önerilen sıra)
----------------------------------------------------------------
1. Veriyi oku (kapasiteler, talepler, sabit maliyetler, atama maliyetleri).
2. `SSCFLPLowerBound.solve()` ile alt sınırı hesapla.
3. `SSCFLPInitialSolution.construct()` ile greedy başlangıç kur.
4. `SSCFLPTabuSearch.run(initial, lower_bound=lb)` ile iterated tabu’yu çalıştır:
   - Her 100 adımda kısa log; tabu/aspiration uygulanır; alpha güncellenir; duraksamada perturbation devreye girer.
5. Çıkışta `_greedy_drop` sonrası elde edilen çözümü `print_detailed_report` ile yazdır.

----------------------------------------------------------------
6) Dosya rehberi
----------------------------------------------------------------
- `src/relaxation.py`: LP gevşetmesiyle lower bound; CBC çözücü, raporlama yardımcıları.
- `src/initial_solution.py`: Greedy başlangıç; oran sıralama, talebi karşılama, ihlâl kontrolü, özet yazdırma.
- `src/tabu_search.py`: İyileştirme motoru; tabu listesi (rastgele tenure), delta hesapları, pertürbasyon, son kapanış temizliği, detaylı rapor.
- Notebooklar (`*-instance.ipynb`): Örnek veri setleriyle uçtan uca demo.
- `README.md`: Kısa proje tanıtımı ve çalışma talimatı.

----------------------------------------------------------------
7) Kısa gerçek hayat analojisi
----------------------------------------------------------------
- Lower bound: “Herkes ekmeği paylaşsa en az kaç liraya doyarız?”
- Greedy başlangıç: “Kirası ucuz ve kapasitesi büyük pastaneleri aç, herkesi en yakına gönder.”
- Tabu + perturbation: “Son hamleleri bir süre unut, oyun sıkıcılaşınca ortalığı karıştır, sonunda pahalı pastaneyi kapatmayı dene.”

Bu dosya, güncel kodun davranışını hızlıca kavramak için hazırlandı. Ayrıntı için ilgili fonksiyonların içine bakabilir veya `print_*` yardımcılarını çalıştırarak çıktıyı gözlemleyebilirsin.

