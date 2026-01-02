Tabu Search Motoru (SSCFLPTabuSearch) — Ayrıntılı Açıklama
==========================================================

Bu dosya, `src/tabu_search.py` içindeki **SSCFLPTabuSearch** sınıfının nasıl çalıştığını, hangi veri yapılarını kullandığını ve her adımın amacını detaylı biçimde özetler.

1) Girdi, çıktı ve amaç
-----------------------
- Girdi dizileri (numpy): `capacities[m]`, `demands[n]`, `fixed_costs[m]`, `assignment_costs[m][n]`.
- Parametreler (varsayılan): `max_iterations=300`, `alpha=1000.0`, `epsilon=0.1`, `beta=0.4`, `max_stagnation=40`, `tabu_tenure_min=10`, `tabu_tenure_max=30`, `random_seed=None`.
- Amaç: Toplam sabit maliyet + atama maliyeti + `alpha * kapasite_ihlali` ifadesini minimize etmek; mümkünse ihlalsiz (feasible) çözüm bulup sonradan pahalı depoları kapatarak iyileştirmek.
- Çıktı: En iyi **uygun** çözüm sözlüğü (veya hiç uygun bulunmazsa eldeki son çözümün klonu).

2) İç durum (state) temsilı
--------------------------
`_build_state(initial_solution)`:
- `assignments`: Liste [0..n-1] → depo.
- `open_set` / `open_facilities`: Ataması olan depolar da otomatik açık kabul edilir; liste sıralıdır.
- `counts`: Depo başına müşteri sayısı.
- `load`: Depo başına toplanan talep.
- `capacity_violations`: Yük - kapasite > 0 ise fazlalık.
- `total_fixed_cost`: Açık depoların sabit toplamı.
- `total_assignment_cost`: Atama maliyetleri toplamı.
- `total_violation`: Fazlalıkların toplamı.
- `objective`: sabit + atama + `alpha * total_violation`.
- `is_feasible`: `total_violation == 0`.
- `lower_bound`: Başlangıç sözlüğünde varsa aynen taşınır.

Kopyalama: `_clone_solution` rapor/sonuç için hafif kopya döndürür (`assignments` tekrar sözlüğe çevrilir, toplam maliyet alanı eklenir).

3) Ceza katsayısı (alpha) dinamiği
----------------------------------
`_update_alpha(feasible)`:
- Feasible ise `alpha = alpha / (1+epsilon)`.
- Değilse `alpha = alpha * (1+epsilon)`.
- `[1e-6, 1e9]` aralığına sıkıştırılır. Böylece ihlale karşı ceza adaptif biçimde artar/azalır.

4) Komşuluk üretimi
-------------------
`_sample_customers`: `ceil(beta * n)` kadar müşteri rastgele seçer (en az 1).
- `_relocate_moves`: Seçilen her müşteri j için mevcut depo k’dan tüm diğer depolara l taşıma hamleleri üretir.
- `_swap_moves`: Seçilen müşteri çiftleri (j1, j2) farklı depolardaysa yer değişim hamlesi üretir.
- `get_neighbors`: Relocate + swap hamlelerini birleştirir ve karıştırır (shuffle).

5) Hızlı delta değerlendirme
----------------------------
`_evaluate_move_delta(solution, move)` çözümü değiştirmeden geri döner:
- Hesaplananlar: yeni objective, yeni feasibility, delta_objective.
- Relocate:
  - Atama maliyeti farkı.
  - Sabit maliyet farkı: Yeni depo ilk kez açılıyorsa eklenir; mevcut depo boşalırsa çıkarılır.
  - İhlal farkı: Sadece ilgili iki depo (k, l) için yük değişimiyle hesaplanır.
  - Yeni objective = sabit + atama + `alpha * yeni_ihlâl`.
- Swap: Sabit maliyet değişmez; iki deponun yük değişimi ve ihlâl farkı hesaplanır.
- Tabu/aspiration kararları bu değerlerle yapılır.

6) Hamleyi uygulama
-------------------
`_apply_move_in_place`:
- Atama ve sabit maliyetleri günceller; depo açma/kapatma durumlarını değiştirir.
- Yükler, ihlaller, objective ve feasibility yeniden hesaplanır.
- `capacity_violations` yalnızca değişen depolar için güncellenir; `open_facilities` sıralanır.

7) Tabu listesi
---------------
- Yapı: `tabu_dict[(müşteri, önceki_depo)] = bitiş_iterasyonu`.
- Tenure: `_get_tabu_tenure` her hamlede `tabu_tenure_min..max` aralığından **rastgele** seçer (dinamik frekans yok).
- `_is_tabu`: Relocate için (j, eski depo), swap için iki müşteri-eski depo ikilisi kontrol edilir.
- Aspiration: Hamle tabu olsa bile **feasible** ve şimdiye kadarki en iyi feasible objective’i iyileştiriyorsa izin verilir.
- `_update_tabu`: Seçilen hamleyi sözlüğe yazar.

8) Perturbation (sarsma) operatörleri
-------------------------------------
Amaç: Stagnation (art arda iyileşmeme) olduğunda aramayı farklı bir bölgeye atmak.
- `_op1_close`: Rastgele bir açık depoyu kapat (>=1 depo bırakır).
- `_op2_open`: Rastgele kapalı bir depoyu aç.
- `_op3_swap_open_close`: Bir açık depoyu kapatıp rastgele kapalı bir depoyu aç.
- `_op4_shuffle_assignments`: Açık seti korur, müşterileri rastgele açık depolara dağıtır; ardından yeniden en ucuzdan atar.
- `_op5_close_half`: Açık depoların yaklaşık yarısını rastgele kapat (>=1 depo).
- `_op6_close1_open2`: Tanımlı fakat `perturb` içinde çağrılmıyor.
- `_op7_open1_close2`: Bir kapalı depoyu aç, sonra mümkünse iki depoyu kapat (>=1 depo); sert maliyet düşürücü hamle.

`perturb(solution, stagnation_counter)`:
- Eğer `stagnation_counter < max_stagnation`: 1–5 arasından rastgele seçer.
- Aksi halde: Her zaman `_op7` kullanır.
- Operatör sonrası `open_facilities`/`open_set` eşsiz ve sıralı hale getirilir, sonra `_reassign_all_to_open` çalışır:
  - Mevcut açık set için her müşteri en ucuz açık depoya atanır.
  - Maliyet, ihlâl, feasibility ve objective baştan hesaplanır.

9) Son temizlik (greedy drop)
-----------------------------
`_greedy_drop(best_feasible)`:
- İyi bir feasible çözüm üzerinde çalışır.
- Sabit maliyeti yüksek depolardan başlayarak, açık sayısı >1 iken tek tek kapatmayı dener.
- Kapatma sonrası herkesi açık depolara en ucuzdan tekrar atar.
- Feasible kalır ve objective iyileşirse kapatma kalıcı olur; iyileşme durana kadar döner.
- Çıkan çözüm clone edilerek dışarı verilir.

10) Ana döngü (`run`)
---------------------
- Opsiyonel alt sınır: `lower_bound` argümanı varsa başlangıç çözümüne eklenir.
- Başlangıç state: `_build_state(initial_solution)`.
- Başlangıç feasible ise `best_feasible` ve objective tutulur, değilse None.
- Her 100 iterasyonda kısa log basılır.
- Her iterasyonda:
  1) Komşular üretilir ve karıştırılır.
  2) Her hamle için tabu kontrolü + aspiration yapılır; en düşük objective’li aday seçilir.
  3) Seçilen hamle uygulanır; tabu listesi güncellenir; `alpha` feasibility’ye göre güncellenir.
  4) Feasible ve objective iyileştiriyorsa en iyi çözüm güncellenir, stagnation=0; aksi halde stagnation++.
  5) `stagnation >= max_stagnation` ise `perturb` çağrılır, stagnation sıfırlanır.
- Döngü sonu:
  - Hiç feasible bulunmadıysa mevcut çözümün klonu döner (ihlalli olabilir).
  - Feasible bulunduysa `_greedy_drop` çalıştırılır ve sonuç döner.

11) Karmaşıklık ve pratik notlar
--------------------------------
- Komşu sayısı yaklaşık `O(beta * n * m + beta^2 * n^2)` civarında (relocate + swap), beta büyüdükçe hız düşer ama arama genişler.
- Tenure rastgele seçildiğinden, aynı parametrelerle deterministik tekrar için `random_seed` verilmelidir (Python `random`, numpy değil).
- Perturbation yalnızca açık seti kullanarak yeniden atama yapar; kapalı depo açmak için op2/op3/op7 gerekir.
- `_op6_close1_open2` şu an kullanılmıyor; ek çeşitlilik istenirse `perturb` içine eklenebilir.
- `_reassign_all_to_open` her çalıştığında sabit maliyeti de yeniden hesaplar; objective tamamen tutarlı hale gelir.

12) Hızlı kullanım özeti
------------------------
```python
from src.tabu_search import SSCFLPTabuSearch

ts = SSCFLPTabuSearch(capacities, demands, fixed_costs, assignment_costs,
                      max_iterations=300, alpha=1000.0, epsilon=0.1,
                      beta=0.4, max_stagnation=40,
                      tabu_tenure_min=10, tabu_tenure_max=30,
                      random_seed=42)

best = ts.run(initial_solution, lower_bound=lb)  # lb opsiyonel
ts.print_detailed_report(best)
```

Bu belge, `tabu_search.py` içindeki mekanizmaları ayrıntılı ve güncel haliyle açıklar; algoritmanın davranışını değiştirmek için hangi fonksiyonun ne yaptığını hızlıca bulmanıza yardımcı olur.

