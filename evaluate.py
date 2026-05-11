"""
Đánh giá hiệu năng mô hình Collaborative Filtering (SVD)
Sử dụng chỉ số RMSE (Root Mean Square Error) để đo lường độ lỗi dự đoán

RMSE = √(Σ(y_true - y_pred)² / n)

RMSE càng nhỏ, mô hình dự đoán càng chính xác.
"""

import os
import pandas as pd
import numpy as np
from surprise import SVD, Dataset, Reader, accuracy
from sklearn.model_selection import train_test_split
import warnings

warnings.filterwarnings("ignore")


def evaluate_svd_model():
    """
    Đánh giá mô hình SVD bằng chỉ số RMSE.
    
    Quy trình:
    1. Đọc dữ liệu từ clean_reviews.csv
    2. Chia dữ liệu: 80% train, 20% test
    3. Huấn luyện mô hình SVD trên tập train
    4. Dự đoán trên tập test
    5. Tính RMSE (Root Mean Square Error)
    6. In kết quả đẹp bằng Tiếng Việt
    """
    
    print("=" * 100)
    print("📊 ĐÁNH GIÁ HIỆU NĂNG MÔ HÌNH COLLABORATIVE FILTERING (SVD)")
    print("=" * 100)
    
    # ========== BƯỚC 1: ĐỌC DỮ LIỆU ==========
    print("\n📖 Bước 1: Đọc dữ liệu từ file clean_reviews.csv...")
    try:
        DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eMptyCommerce', 'data', 'clean_reviews.csv')
        reviews_df = pd.read_csv(DATA_PATH)
        print(f"   ✓ Đã đọc {len(reviews_df)} bản ghi đánh giá")
        print(f"   ✓ Cột dữ liệu: {reviews_df.columns.tolist()}")
        print(f"   ✓ Khách hàng duy nhất: {reviews_df['customer_id'].nunique()}")
        print(f"   ✓ Sản phẩm duy nhất: {reviews_df['product_id'].nunique()}")
    except Exception as e:
        print(f"   ❌ Lỗi đọc dữ liệu: {e}")
        return
    
    # ========== BƯỚC 2: CHIA DỮ LIỆU (80/20) ==========
    print("\n🔀 Bước 2: Chia dữ liệu thành tập train (80%) và test (20%)...")
    try:
        train_df, test_df = train_test_split(
            reviews_df,
            test_size=0.2,
            random_state=42,
            shuffle=True
        )
        print(f"   ✓ Tập train: {len(train_df)} bản ghi ({len(train_df)/len(reviews_df)*100:.1f}%)")
        print(f"   ✓ Tập test: {len(test_df)} bản ghi ({len(test_df)/len(reviews_df)*100:.1f}%)")
    except Exception as e:
        print(f"   ❌ Lỗi chia dữ liệu: {e}")
        return
    
    # ========== BƯỚC 3: KHỞI TẠO READER VÀ DATASET ==========
    print("\n⚙️  Bước 3: Khởi tạo Reader và Dataset (Rating Scale: 1-5)...")
    try:
        # Định nghĩa Rating Scale
        reader = Reader(rating_scale=(1, 5))
        
        # Load toàn bộ dữ liệu vào Dataset (để sau này chia trainset và testset)
        full_dataset = Dataset.load_from_df(
            reviews_df[['customer_id', 'product_id', 'rating']],
            reader=reader
        )
        
        print(f"   ✓ Reader khởi tạo với rating scale: 1-5")
        print(f"   ✓ Dataset đã tải {len(reviews_df)} bản ghi")
    except Exception as e:
        print(f"   ❌ Lỗi khởi tạo Dataset: {e}")
        return
    
    # ========== BƯỚC 4: TẠO TRAINSET VÀ TESTSET ==========
    print("\n🔧 Bước 4: Tạo Trainset và Testset từ Surprise...")
    try:
        # Tạo trainset từ dữ liệu train
        train_dataset = Dataset.load_from_df(
            train_df[['customer_id', 'product_id', 'rating']],
            reader=reader
        )
        trainset = train_dataset.build_full_trainset()
        
        # Tạo testset từ dữ liệu test
        test_dataset = Dataset.load_from_df(
            test_df[['customer_id', 'product_id', 'rating']],
            reader=reader
        )
        testset = test_dataset.build_full_trainset().build_testset()
        
        print(f"   ✓ Trainset: {trainset.n_users} người dùng, {trainset.n_items} sản phẩm")
        print(f"   ✓ Testset: {len(testset)} bản ghi cần dự đoán")
    except Exception as e:
        print(f"   ❌ Lỗi tạo trainset/testset: {e}")
        return
    
    # ========== BƯỚC 5: KHỞI TẠO VÀ HUẤN LUYỆN SVD ==========
    print("\n🚀 Bước 5: Khởi tạo và huấn luyện mô hình SVD...")
    try:
        # Khởi tạo mô hình SVD
        svd_model = SVD(
            n_factors=50,      # Số latent factors
            n_epochs=40,       # Số epoch
            lr_all=0.005,      # Learning rate
            reg_all=0.02,      # Regularization
            random_state=42,
            verbose=False
        )
        
        # Huấn luyện trên tập train
        print("   ⏳ Đang huấn luyện mô hình SVD trên tập train...")
        svd_model.fit(trainset)
        
        print(f"   ✓ Mô hình SVD đã huấn luyện thành công!")
        print(f"   ✓ Cấu hình:")
        print(f"     - Số latent factors: 50")
        print(f"     - Số epoch: 40")
        print(f"     - Learning rate: 0.005")
        print(f"     - Regularization: 0.02")
    except Exception as e:
        print(f"   ❌ Lỗi huấn luyện SVD: {e}")
        return
    
    # ========== BƯỚC 6: DỰ ĐOÁN TRÊN TẬP TEST ==========
    print("\n🔮 Bước 6: Dự đoán rating trên tập test...")
    try:
        predictions = svd_model.test(testset)
        print(f"   ✓ Đã dự đoán {len(predictions)} bản ghi")
    except Exception as e:
        print(f"   ❌ Lỗi dự đoán: {e}")
        return
    
    # ========== BƯỚC 7: TÍNH RMSE ==========
    print("\n📈 Bước 7: Tính chỉ số RMSE (Root Mean Square Error)...")
    try:
        rmse_score = accuracy.rmse(predictions, verbose=False)
        print(f"   ✓ RMSE đã tính toán thành công!")
    except Exception as e:
        print(f"   ❌ Lỗi tính RMSE: {e}")
        return
    
    # ========== PHÂN TÍCH KẾT QUẢ ==========
    print("\n" + "=" * 100)
    print("📊 KẾT QUẢ ĐÁNH GIÁ MÔ HÌNH SVD")
    print("=" * 100)
    
    print(f"\n🎯 CHỈ SỐ RMSE: {rmse_score:.4f}")
    print(f"\n📝 Diễn giải:")
    print(f"   • RMSE = {rmse_score:.4f} nghĩa là trung bình, mô hình dự đoán sai {rmse_score:.4f} sao")
    print(f"   • Trên tập test gồm {len(test_df)} bản ghi")
    print(f"   • Rating thực tế nằm trong khoảng [1, 5] sao")
    
    # Đánh giá độ tốt
    print(f"\n✨ NHẬN XÉT CHỈ SỐ RMSE:")
    if rmse_score < 0.7:
        print(f"   🏆 XUẤT SẮC - Mô hình dự đoán rất chính xác (RMSE < 0.7)")
    elif rmse_score < 0.85:
        print(f"   ⭐ TỐT - Mô hình dự đoán tốt (RMSE < 0.85)")
    elif rmse_score < 1.0:
        print(f"   👍 CHẤP NHẬN ĐƯỢC - Mô hình dự đoán khá tốt (RMSE < 1.0)")
    else:
        print(f"   ⚠️  CẦN CẢI THIỆN - Mô hình cần tối ưu hóa (RMSE ≥ 1.0)")
    
    print(f"\n📋 THỐNG KÊ DỮ LIỆU:")
    print(f"   • Tập dữ liệu gốc: {len(reviews_df)} bản ghi")
    print(f"   • Tập train: {len(train_df)} bản ghi (80%)")
    print(f"   • Tập test: {len(test_df)} bản ghi (20%)")
    print(f"   • Số khách hàng duy nhất: {reviews_df['customer_id'].nunique()}")
    print(f"   • Số sản phẩm duy nhất: {reviews_df['product_id'].nunique()}")
    
    # Tính thêm một số chỉ số khác
    predictions_array = np.array([pred.est for pred in predictions])
    actual_array = np.array([pred.r_ui for pred in predictions])
    mae = np.mean(np.abs(predictions_array - actual_array))
    
    print(f"\n📊 CHỈ SỐ BỔ TRỢ:")
    print(f"   • MAE (Mean Absolute Error): {mae:.4f}")
    print(f"   • Min error: {np.min(np.abs(predictions_array - actual_array)):.4f}")
    print(f"   • Max error: {np.max(np.abs(predictions_array - actual_array)):.4f}")
    print(f"   • Mean error: {np.mean(predictions_array - actual_array):.4f}")
    
    print("\n" + "=" * 100)
    print("✅ ĐÁNH GIÁ MÔ HÌNH HOÀN TẤT - SẴN SÀNG COPY VÀO BÁO CÁO")
    print("=" * 100)


if __name__ == "__main__":
    evaluate_svd_model()
