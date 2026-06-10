#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kịch bản cào dữ liệu (Web Scraper) Thế Giới Di Động (thegioididong.com)
Phục vụ cho đề tài luận văn: "Hệ thống gợi ý sản phẩm thương mại điện tử dựa trên mô hình Hybrid"
Thu thập 2 bảng dữ liệu:
1. products.csv: product_id, title, category, price, description, image_url, brand, specs
2. reviews.csv: review_id, user_id, product_id, rating, review_text, date
"""

import os
import re
import csv
import json
import time
import hashlib
import argparse
import requests
import urllib.parse
from bs4 import BeautifulSoup

# Cấu hình Headers mặc định để giả lập trình duyệt và tránh bị chặn
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
}

class TGDDScraper:
    def __init__(self, delay=1.5, output_dir='data'):
        self.delay = delay
        self.output_dir = output_dir
        self.headers = DEFAULT_HEADERS
        
        # Đảm bảo thư mục đầu ra tồn tại
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"[*] Đã tạo thư mục đầu ra: {self.output_dir}")

    def sleep(self, custom_delay=None):
        """Tạm dừng giữa các request để lịch sự và tránh bị block"""
        time.sleep(custom_delay if custom_delay is not None else self.delay)

    def get_product_links_from_category(self, category_name, category_urls, max_products=100):
        """
        Lấy danh sách link chi tiết sản phẩm từ danh sách các trang danh mục & thương hiệu
        """
        links = []
        for url in category_urls:
            print(f"[+] Đang quét lấy liên kết cho '{category_name}' từ: {url}...")
            try:
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code != 200:
                    print(f"    [!] Lỗi tải trang danh mục. Mã lỗi: {res.status_code}")
                    continue
                
                soup = BeautifulSoup(res.text, 'html.parser')
                page_links_count = 0
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    # Xác định các liên kết sản phẩm dựa trên danh mục tương ứng
                    is_valid_link = False
                    if category_name == 'Điện thoại' and '/dtdd/' in href:
                        is_valid_link = True
                    elif category_name == 'Laptop' and '/laptop/' in href:
                        is_valid_link = True
                    elif category_name == 'Máy tính bảng' and '/may-tinh-bang/' in href:
                        is_valid_link = True
                    elif category_name == 'Đồng hồ' and any(kw in href for kw in ['/dong-ho-thong-minh/', '/dong-ho-deo-tay/']):
                        is_valid_link = True
                    elif category_name == 'Âm thanh' and any(kw in href for kw in ['/tai-nghe/', '/loa/', '/loa-laptop/']):
                        is_valid_link = True
                    elif category_name == 'Phụ kiện' and any(kw in href for kw in ['/loa-laptop/', '/sac-dtdd/', '/camera-giam-sat/', '/tai-nghe/', '/chuot-ban-phim/', '/ban-phim/', '/chuot/', '/op-lung-', '/mieng-dan-man-hinh/']):
                        is_valid_link = True
                    
                    if is_valid_link:
                        # Chuyển đổi thành URL tuyệt đối
                        full_url = urllib.parse.urljoin('https://www.thegioididong.com', href)
                        # Bỏ các tham số UTM hoặc query
                        cleaned_url = full_url.split('?')[0]
                        if cleaned_url not in links:
                            links.append(cleaned_url)
                            page_links_count += 1
                
                print(f"    [v] Quét xong trang: Thu được {page_links_count} liên kết mới.")
                # Tạm nghỉ ngắn giữa các trang danh mục để an toàn
                self.sleep(0.5)
                
            except Exception as e:
                print(f"    [!] Đã xảy ra lỗi khi lấy danh sách sản phẩm từ {url}: {e}")
            
        # Lọc bớt các link rác
        filtered_links = []
        for link in links:
            slug = link.split('/')[-1]
            if slug and slug not in ['dtdd', 'laptop', 'may-tinh-bang', 'dong-ho-thong-minh', 'dong-ho-deo-tay', 'tai-nghe', 'loa', 'phu-kien', 'cap-dien-thoai', 'chuot-ban-phim', 'tin-tuc', 'so-sanh', 'chinh-sach', 'pin-sac-du-phong']:
                filtered_links.append(link)
        
        print(f"[*] Tìm thấy tổng cộng {len(filtered_links)} sản phẩm duy nhất cho danh mục '{category_name}'.")
        print(f"[*] Lấy tối đa {max_products} sản phẩm để tiến hành cào chi tiết.")
        return filtered_links[:max_products]

    def scrape_product_details(self, product_url, category_name):
        """
        Scrape thông tin chi tiết và đánh giá từ trang sản phẩm qua JSON-LD
        """
        print(f"  -> Đang cào dữ liệu từ: {product_url}")
        try:
            res = requests.get(product_url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                print(f"    [!] Lỗi tải trang. Status code: {res.status_code}")
                return None, []
            
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # 1. Tìm script chứa JSON-LD của Product
            ld_scripts = soup.find_all('script', type='application/ld+json')
            product_data = None
            
            for script in ld_scripts:
                try:
                    js_data = json.loads(script.string or '')
                    if isinstance(js_data, list):
                        for item in js_data:
                            if isinstance(item, dict) and (item.get('@type') == 'Product' or 'sku' in item):
                                product_data = item
                                break
                    elif isinstance(js_data, dict):
                        if js_data.get('@type') == 'Product' or 'sku' in js_data:
                            product_data = js_data
                            break
                except:
                    continue
            
            if not product_data:
                print("    [!] Không tìm thấy cấu trúc JSON-LD Product trên trang này.")
                return None, []
            
            # 2. Trích xuất thông tin sản phẩm
            product_id = product_data.get('sku')
            if not product_id:
                # Nếu thiếu SKU, tạo ID từ slug URL
                slug = product_url.split('/')[-1]
                product_id = hashlib.md5(slug.encode('utf-8')).hexdigest()[:8]
            
            # Trích xuất và chuẩn hóa dữ liệu
            title = product_data.get('name') or soup.find('h1').text.strip() if soup.find('h1') else 'Sản phẩm không tên'
            
            # Trích xuất giá
            price = 0
            offers = product_data.get('offers')
            if isinstance(offers, dict):
                price = offers.get('price', 0)
            elif isinstance(offers, list) and offers:
                price = offers[0].get('price', 0)
            
            try:
                price = int(float(price))
            except:
                price = 0
            
            description = product_data.get('description') or ''
            if not description:
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                description = meta_desc.get('content', '') if meta_desc else ''
            
            # Trích xuất hình ảnh
            image_url = ''
            img_data = product_data.get('image')
            if isinstance(img_data, dict):
                image_url = img_data.get('contentUrl') or img_data.get('url') or ''
            elif isinstance(img_data, list) and img_data:
                first_img = img_data[0]
                image_url = first_img.get('contentUrl') if isinstance(first_img, dict) else str(first_img)
            elif isinstance(img_data, str):
                image_url = img_data
            
            # Trích xuất thương hiệu
            brand = ''
            brand_data = product_data.get('brand')
            if isinstance(brand_data, dict):
                name_val = brand_data.get('name', '')
                brand = name_val[0] if isinstance(name_val, list) and name_val else str(name_val)
            elif isinstance(brand_data, str):
                brand = brand_data
            
            # Chuẩn hóa thương hiệu
            brand = brand.strip()
            if not brand:
                # Trích xuất thương hiệu từ tiêu đề
                for b_name in ['Apple', 'Samsung', 'OPPO', 'Xiaomi', 'vivo', 'realme', 'Asus', 'HP', 'Acer', 'Lenovo', 'Dell', 'MSI', 'Masstel', 'iPad', 'Huawei', 'Garmin', 'Sony', 'JBL', 'Sennheiser']:
                    if b_name.lower() in title.lower():
                        brand = b_name
                        break
            if 'iPhone' in brand or 'iPad' in brand or 'Apple' in brand:
                brand = 'Apple'
            
            # Trích xuất thông số kỹ thuật (specs)
            props = product_data.get('additionalProperty', [])
            specs_list = []
            if isinstance(props, list):
                for prop in props:
                    if isinstance(prop, dict) and prop.get('name') and prop.get('value'):
                        specs_list.append(f"{prop.get('name')}: {prop.get('value')}")
            specs = " | ".join(specs_list)
            
            product_info = {
                'product_id': product_id,
                'title': title.strip(),
                'category': category_name,
                'price': price,
                'description': description.strip(),
                'image_url': image_url.strip(),
                'brand': brand.strip() or 'Khác',
                'specs': specs
            }
            
            # 3. Trích xuất bình luận/đánh giá
            reviews = []
            raw_reviews = product_data.get('review') or []
            if isinstance(raw_reviews, dict):
                raw_reviews = [raw_reviews]
                
            for rev in raw_reviews:
                if not isinstance(rev, dict):
                    continue
                
                # Trích xuất tên người dùng
                author_name = ''
                author_data = rev.get('author')
                if isinstance(author_data, dict):
                    author_name = author_data.get('name') or ''
                elif isinstance(author_data, str):
                    author_name = author_data
                author_name = author_name.strip() or 'Khách hàng ẩn danh'
                
                # Tạo user_id duy nhất dạng hash
                user_id = f"u_{hashlib.md5(author_name.encode('utf-8')).hexdigest()[:8]}"
                
                review_text = rev.get('reviewBody') or rev.get('description') or ''
                review_text = review_text.strip()
                
                # Tạo review_id duy nhất
                content_hash = hashlib.md5(f"{author_name}_{review_text}".encode('utf-8')).hexdigest()[:8]
                review_id = f"r_{product_id}_{content_hash}"
                
                # Trích xuất số sao đánh giá (rating)
                rating = 5
                rating_data = rev.get('reviewRating')
                if isinstance(rating_data, dict):
                    try:
                        rating = int(float(rating_data.get('ratingValue', 5)))
                    except:
                        rating = 5
                
                # Trích xuất ngày đánh giá
                raw_date = rev.get('datePublished') or ''
                date = raw_date.split(': ')[0] if ': ' in raw_date else raw_date
                date = date.strip()
                
                reviews.append({
                    'review_id': review_id,
                    'user_id': user_id,
                    'product_id': product_id,
                    'rating': rating,
                    'review_text': review_text,
                    'date': date
                })
                
            print(f"    [v] Thành công: Lấy được thông tin sản phẩm và {len(reviews)} đánh giá.")
            return product_info, reviews
            
        except Exception as e:
            print(f"    [!] Lỗi khi cào chi tiết sản phẩm: {e}")
            return None, []

    def run(self, max_products_per_cat=100):
        """
        Hàm điều khiển toàn bộ tiến trình cào dữ liệu
        """
        # Thêm danh mục Đồng hồ thông minh và Âm thanh để nhân rộng lượng dữ liệu
        categories = {
            'Điện thoại': [
                'https://www.thegioididong.com/dtdd',
                'https://www.thegioididong.com/dtdd-samsung',
                'https://www.thegioididong.com/dtdd-oppo',
                'https://www.thegioididong.com/dtdd-xiaomi',
                'https://www.thegioididong.com/dtdd-vivo',
                'https://www.thegioididong.com/dtdd-realme'
            ],
            'Laptop': [
                'https://www.thegioididong.com/laptop',
                'https://www.thegioididong.com/laptop-asus',
                'https://www.thegioididong.com/laptop-hp',
                'https://www.thegioididong.com/laptop-lenovo',
                'https://www.thegioididong.com/laptop-acer',
                'https://www.thegioididong.com/laptop-dell',
                'https://www.thegioididong.com/laptop-msi'
            ],
            'Máy tính bảng': [
                'https://www.thegioididong.com/may-tinh-bang',
                'https://www.thegioididong.com/may-tinh-bang-apple-ipad',
                'https://www.thegioididong.com/may-tinh-bang-samsung',
                'https://www.thegioididong.com/may-tinh-bang-xiaomi',
                'https://www.thegioididong.com/may-tinh-bang-lenovo',
                'https://www.thegioididong.com/may-tinh-bang-masstel'
            ],
            'Đồng hồ': [
                'https://www.thegioididong.com/dong-ho-thong-minh',
                'https://www.thegioididong.com/dong-ho-thong-minh-apple',
                'https://www.thegioididong.com/dong-ho-thong-minh-samsung',
                'https://www.thegioididong.com/dong-ho-thong-minh-xiaomi',
                'https://www.thegioididong.com/dong-ho-thong-minh-realme',
                'https://www.thegioididong.com/dong-ho-deo-tay'
            ],
            'Âm thanh': [
                'https://www.thegioididong.com/tai-nghe',
                'https://www.thegioididong.com/loa'
            ],
            'Phụ kiện': [
                'https://www.thegioididong.com/phu-kien',
                'https://www.thegioididong.com/cap-dien-thoai',
                'https://www.thegioididong.com/chuot-ban-phim'
            ]
        }
        
        all_products = []
        all_reviews = []
        
        print("="*60)
        print(" BẮT ĐẦU CÀO DỮ LIỆU THẾ GIỚI DI ĐỘNG (THEGIOIDIDONG.COM)")
        print(f" - Số lượng sản phẩm yêu cầu tối đa/danh mục: {max_products_per_cat}")
        print(f" - Thời gian chờ (delay): {self.delay} giây")
        print(f" - Thư mục lưu trữ: {self.output_dir}")
        print("="*60)
        
        for cat_name, cat_urls in categories.items():
            product_links = self.get_product_links_from_category(cat_name, cat_urls, max_products_per_cat)
            
            for link in product_links:
                prod_info, prod_reviews = self.scrape_product_details(link, cat_name)
                if prod_info:
                    all_products.append(prod_info)
                    all_reviews.extend(prod_reviews)
                
                # Tạm nghỉ để bảo mật/lịch sự
                self.sleep()
        
        # Lưu trữ dữ liệu vào CSV
        self.save_products(all_products)
        self.save_reviews(all_reviews)
        
        print("\n" + "="*60)
        print(" HOÀN THÀNH TIẾN TRÌNH CÀO DỮ LIỆU!")
        print(f" - Tổng số sản phẩm thu được: {len(all_products)}")
        print(f" - Tổng số đánh giá thu được: {len(all_reviews)}")
        print(f" - File sản phẩm: {os.path.join(self.output_dir, 'products.csv')}")
        print(f" - File đánh giá: {os.path.join(self.output_dir, 'reviews.csv')}")
        print("="*60)

    def save_products(self, products):
        """Lưu danh sách sản phẩm vào file products.csv (chế độ cộng dồn và loại bỏ trùng lặp)"""
        file_path = os.path.join(self.output_dir, 'products.csv')
        headers = ['product_id', 'title', 'category', 'price', 'description', 'image_url', 'brand', 'specs']
        
        existing_products = {}
        # Đọc dữ liệu cũ nếu file đã tồn tại
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('product_id'):
                            existing_products[row['product_id']] = row
            except Exception as e:
                print(f"[!] Không thể đọc dữ liệu products.csv cũ: {e}")
        
        # Ghi đè/Cập nhật bằng sản phẩm mới cào
        new_count = 0
        for prod in products:
            pid = prod.get('product_id')
            if pid:
                if pid not in existing_products:
                    new_count += 1
                existing_products[pid] = {k: prod.get(k, '') for k in headers}
                
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for prod_id, prod_data in existing_products.items():
                    writer.writerow(prod_data)
            print(f"[v] Đã cập nhật products.csv thành công. Số sản phẩm mới thêm: {new_count}. Tổng số hiện tại: {len(existing_products)}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu file products.csv: {e}")

    def save_reviews(self, reviews):
        """Lưu danh sách đánh giá vào file reviews.csv (chế độ cộng dồn và loại bỏ trùng lặp)"""
        file_path = os.path.join(self.output_dir, 'reviews.csv')
        headers = ['review_id', 'user_id', 'product_id', 'rating', 'review_text', 'date']
        
        existing_reviews = {}
        # Đọc dữ liệu cũ nếu file đã tồn tại
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('review_id'):
                            existing_reviews[row['review_id']] = row
            except Exception as e:
                print(f"[!] Không thể đọc dữ liệu reviews.csv cũ: {e}")
                
        # Ghi đè/Cập nhật bằng đánh giá mới cào
        new_count = 0
        for rev in reviews:
            rid = rev.get('review_id')
            if rid:
                if rid not in existing_reviews:
                    new_count += 1
                existing_reviews[rid] = {k: rev.get(k, '') for k in headers}
                
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for rev_id, rev_data in existing_reviews.items():
                    writer.writerow(rev_data)
            print(f"[v] Đã cập nhật reviews.csv thành công. Số đánh giá mới thêm: {new_count}. Tổng số hiện tại: {len(existing_reviews)}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu file reviews.csv: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Cào dữ liệu Thế Giới Di Động cho Luận Văn Hệ thống Gợi ý")
    parser.add_argument('--max-products', type=int, default=100, help='Số lượng sản phẩm tối đa trên mỗi danh mục (Mặc định: 100)')
    parser.add_argument('--delay', type=float, default=1.5, help='Thời gian chờ giữa các request bằng giây (Mặc định: 1.5)')
    parser.add_argument('--output-dir', type=str, default='data', help='Thư mục lưu trữ các file CSV kết quả (Mặc định: data)')
    
    args = parser.parse_args()
    
    scraper = TGDDScraper(delay=args.delay, output_dir=args.output_dir)
    scraper.run(max_products_per_cat=args.max_products)
