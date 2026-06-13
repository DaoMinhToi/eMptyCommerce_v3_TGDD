"""
SCRIPT ĐO THỜI GIAN THỰC NGHIỆM - eMpTyCommerce
=================================================
Tự động đo 3 kịch bản, mỗi kịch bản 5 lần
"""
import time
import statistics

# ── Số thật từ dataset ────────────────────────────────────────
COLD_CUSTOMER   = "99999999"   # không tồn tại → Cold-Start
WARM_CUSTOMER   = "u_3a475137"   # tồn tại, có ratings trong clean_reviews.csv
NO_PROD_CUST    = "88888888"   # không tồn tại, không xem gì
PRODUCT_CAY_CAM = 74021317   # "Cây Cam Ngọt Của Tôi"
N_RUNS          = 5

# ── BƯỚC 0: Khởi tạo mô hình ──────────────────────────────────
print("=" * 68)
print("BƯỚC 0 — KHỞI TẠO MÔ HÌNH (chỉ 1 lần khi khởi động app)")
print("=" * 68)
t0 = time.time()
from recommender import HybridRecommender
rec = HybridRecommender()
init_ms = (time.time() - t0) * 1000
print(f"\n✅ Khởi tạo xong: {init_ms:.0f} ms ({init_ms/1000:.1f} giây)\n")

# ── Hàm đo lặp N lần ──────────────────────────────────────────
def do_lap(ten, func, n=N_RUNS):
    print("-" * 68)
    print(f"▶  {ten}")
    print("-" * 68)
    times = []
    result = None
    for i in range(n):
        t = time.time()
        result = func()
        ms = (time.time() - t) * 1000
        times.append(ms)
        n_ret = len(result) if result is not None else 0
        print(f"   Lần {i+1}: {ms:8.2f} ms  │  Số gợi ý trả về: {n_ret}")

    tb  = statistics.mean(times)
    mn  = min(times)
    mx  = max(times)
    std = statistics.stdev(times) if n > 1 else 0.0
    print(f"\n   Trung bình    : {tb:8.2f} ms")
    print(f"   Nhanh nhất    : {mn:8.2f} ms")
    print(f"   Chậm nhất     : {mx:8.2f} ms")
    print(f"   Độ lệch chuẩn : {std:8.2f} ms")

    try:
        if result is not None and not result.empty and 'title' in result.columns:
            sc_col = next((c for c in
                ['similarity_score','hybrid_score','popularity_score']
                if c in result.columns), None)
            print(f"\n   Top-5 gợi ý (lần {n}):")
            for idx, row in result.head(5).iterrows():
                sc = f"{float(row[sc_col]):.4f}" if sc_col else "N/A"
                print(f"   {idx+1}. {str(row['title'])[:55]:<57} score={sc}")
    except Exception as e:
        print(f"   (Không hiển thị top-5: {e})")
    print()
    return tb, mn, mx, std

# ── KỊCH BẢN 1: Cold-Start có sản phẩm xem ───────────────────
print("=" * 68)
print("KỊCH BẢN 1 — COLD-START (có sản phẩm xem)")
print(f"  User mới (ID={COLD_CUSTOMER}) xem 'Cây Cam Ngọt' (ID={PRODUCT_CAY_CAM})")
print("  → Content-Based 100% (TF-IDF + Cosine Similarity)")
print("=" * 68)
tb1,mn1,mx1,std1 = do_lap(
    "get_hybrid_recommendations(cold_start + product_viewed)",
    lambda: rec.get_hybrid_recommendations(
        customer_id=COLD_CUSTOMER,
        product_id_viewed=PRODUCT_CAY_CAM,
        top_n=5
    )
)

# ── KỊCH BẢN 2: Warm-Start ────────────────────────────────────
print("=" * 68)
print("KỊCH BẢN 2 — WARM-START (người dùng cũ)")
print(f"  User cũ (ID={WARM_CUSTOMER}), 7 ratings, avg=5.0")
print("  → Hybrid: SVD 60% + Content-Based 40%")
print("  ⚠  Chậm hơn vì SVD.predict ~1,800 sản phẩm")
print("=" * 68)
tb2,mn2,mx2,std2 = do_lap(
    "get_hybrid_recommendations(warm_start)",
    lambda: rec.get_hybrid_recommendations(
        customer_id=WARM_CUSTOMER,
        top_n=5
    )
)

# ── KỊCH BẢN 3: Cold-Start không có sản phẩm ─────────────────
print("=" * 68)
print("KỊCH BẢN 3 — COLD-START (không có sản phẩm xem)")
print(f"  User mới (ID={NO_PROD_CUST}) chưa xem gì")
print("  → Bayesian Average Popular fallback")
print("=" * 68)
tb3,mn3,mx3,std3 = do_lap(
    "get_hybrid_recommendations(cold_start + no product)",
    lambda: rec.get_hybrid_recommendations(
        customer_id=NO_PROD_CUST,
        product_id_viewed=None,
        top_n=5
    )
)

# ── BẢNG TỔNG HỢP ─────────────────────────────────────────────
SEP = "=" * 68
print(SEP)
print("BẢNG TỔNG HỢP KẾT QUẢ ĐO THỰC TẾ")
print(SEP)
print(f"{'Kịch bản':<40} {'TB(ms)':>8} {'Min(ms)':>8} {'Max(ms)':>8} {'Std':>7}")
print("-" * 73)
print(f"{'Khởi tạo mô hình (1 lần)':<40} {init_ms:>8.0f} {'—':>8} {'—':>8} {'—':>7}")
print(f"{'KB1: Cold-Start + có SP xem (CB 100%)':<40} {tb1:>8.2f} {mn1:>8.2f} {mx1:>8.2f} {std1:>7.2f}")
print(f"{'KB2: Warm-Start (SVD 60% + CB 40%)':<40} {tb2:>8.2f} {mn2:>8.2f} {mx2:>8.2f} {std2:>7.2f}")
print(f"{'KB3: Cold-Start + không có SP xem':<40} {tb3:>8.2f} {mn3:>8.2f} {mx3:>8.2f} {std3:>7.2f}")
print(SEP)

fastest = min([(tb1,"KB1"),(tb2,"KB2"),(tb3,"KB3")], key=lambda x: x[0])
slowest = max([(tb1,"KB1"),(tb2,"KB2"),(tb3,"KB3")], key=lambda x: x[0])
print(f"→ Nhanh nhất: {fastest[1]} ({fastest[0]:.2f} ms)")
print(f"→ Chậm nhất : {slowest[1]} ({slowest[0]:.2f} ms)")
if fastest[0] > 0:
    print(f"→ Tỉ lệ chênh lệch nhanh/chậm: {slowest[0]/fastest[0]:.1f}x")
else:
    print(f"→ Tỉ lệ chênh lệch nhanh/chậm: ∞ (KB1 quá nhanh, không đo được)")
print(SEP)
print("✅ XONG. Copy toàn bộ bảng trên gửi Claude để viết báo cáo.")
