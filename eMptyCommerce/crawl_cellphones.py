#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kịch bản cào dữ liệu (Web Scraper) CellphoneS (cellphones.com.vn)
Thu thập và bổ sung dữ liệu cho hệ thống gợi ý Hybrid
Cấu trúc đầu ra đồng bộ 100% với Thế Giới Di Động và FPT Shop:
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
from datetime import datetime

# Cấu hình Headers mô phỏng trình duyệt để tránh bị chặn bởi Cloudflare/WAF cơ bản
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0'
}

# Tập hợp các tên hiển thị chung chung, ẩn danh dễ bị hệ thống hoặc SEO template dùng làm đánh giá mẫu (ảo)
GENERIC_NAMES = {
    'khách', 'khách hàng', 'khách hàng ẩn danh', 'ẩn danh', 'người dùng', 
    'user', 'anonymous', 'guest', 'fpt', 'tgdd', 'cellphones', 'qtv', 
    'quản trị viên', 'member', 'thành viên', 'khách hàng viết tắt', 'khach hang'
}

class CellphoneSScraper:
    def __init__(self, delay=1.5, output_dir='data'):
        self.delay = delay
        self.output_dir = output_dir
        self.headers = DEFAULT_HEADERS
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"[*] Đã tạo thư mục đầu ra: {self.output_dir}")

    def sleep(self, custom_delay=None):
        time.sleep(custom_delay if custom_delay is not None else self.delay)

    def get_product_links_from_category(self, category_name, category_urls, max_products=100):
        links = []
        for url in category_urls:
            print(f"[+] Đang quét lấy liên kết cho '{category_name}' từ CellphoneS: {url}...")
            try:
                res = requests.get(url, headers=self.headers, timeout=15)
                if res.status_code != 200:
                    print(f"    [!] Lỗi tải trang danh mục. Mã lỗi: {res.status_code}")
                    continue
                
                soup = BeautifulSoup(res.text, 'html.parser')
                page_links_count = 0
                
                # Danh sách các trang danh mục chính cần lọc bỏ để không nhận nhầm làm sản phẩm
                exclude_slugs = [
                    'mobile.html', 'tablet.html', 'laptop.html', 'phu-kien.html', 
                    'thiet-bi-am-thanh.html', 'dong-ho-thong-minh.html', 'hang-cu.html', 
                    'tivi.html', 'do-gia-dung.html', 'man-hinh.html', 'may-tinh-de-ban.html', 
                    'may-in.html', 'dien-may.html', 'do-choi-cong-nghe.html', 'thu-cu-doi-moi',
                    'danh-sach-khuyen-mai', 'sforum'
                ]
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    # Chuyển đổi thành URL tuyệt đối nếu là link tương đối
                    full_url = urllib.parse.urljoin('https://cellphones.com.vn', href)
                    cleaned_url = full_url.split('?')[0].split('#')[0]
                    
                    if cleaned_url.startswith('https://cellphones.com.vn/') and cleaned_url.endswith('.html'):
                        slug = cleaned_url.replace('https://cellphones.com.vn/', '')
                        
                        # Điều kiện: Không nằm trong danh mục loại trừ và không chứa thư mục con (không chứa dấu gạch chéo '/')
                        if '/' not in slug and slug not in exclude_slugs:
                            if cleaned_url not in links:
                                links.append(cleaned_url)
                                page_links_count += 1
                
                print(f"    [v] Quét xong trang: Thu được {page_links_count} liên kết mới hợp lệ.")
                self.sleep(0.5)
                
            except Exception as e:
                print(f"    [!] Đã xảy ra lỗi khi lấy danh sách sản phẩm từ {url}: {e}")
            
        print(f"[*] Tìm thấy tổng cộng {len(links)} sản phẩm CellphoneS cho '{category_name}'.")
        print(f"[*] Lấy tối đa {max_products} sản phẩm để tiến hành cào chi tiết.")
        return links[:max_products]

    def scrape_product_details(self, product_url, category_name):
        print(f"  -> Đang cào dữ liệu từ CellphoneS: {product_url}")
        try:
            res = requests.get(product_url, headers=self.headers, timeout=15)
            if res.status_code != 200:
                print(f"    [!] Lỗi tải trang. Status code: {res.status_code}")
                return None, []
            
            soup = BeautifulSoup(res.text, 'html.parser')
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
            
            # Trích xuất thông tin sản phẩm
            product_id = product_data.get('sku')
            if not product_id:
                slug = product_url.split('/')[-1].replace('.html', '')
                product_id = hashlib.md5(slug.encode('utf-8')).hexdigest()[:8]
            
            title = product_data.get('name') or (soup.find('h1').text.strip() if soup.find('h1') else 'Sản phẩm không tên')
            
            # Trích xuất giá bán
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
                brand = brand_data.get('name', '')
            elif isinstance(brand_data, str):
                brand = brand_data
            
            brand = brand.strip()
            # Dự phòng nhận diện thương hiệu từ Title nếu trống
            if not brand:
                for b_name in ['Apple', 'Samsung', 'OPPO', 'Xiaomi', 'vivo', 'realme', 'Asus', 'HP', 'Acer', 'Lenovo', 'Dell', 'MSI', 'Masstel', 'iPad', 'Huawei', 'Garmin', 'Sony', 'JBL', 'Sennheiser', 'Razer', 'Logitech', 'Dareu', 'Baseus', 'Anker', 'Ugreen', 'Trusmi', 'Tomtoc', 'KingBag']:
                    if b_name.lower() in title.lower():
                        brand = b_name
                        break
            if 'iPhone' in brand or 'iPad' in brand or 'Apple' in brand or 'MacBook' in brand:
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
            
            # Trích xuất bình luận/đánh giá
            reviews = []
            raw_reviews = product_data.get('review') or []
            if isinstance(raw_reviews, dict):
                raw_reviews = [raw_reviews]
                
            for rev in raw_reviews:
                if not isinstance(rev, dict):
                    continue
                
                author_name = ''
                author_data = rev.get('author')
                if isinstance(author_data, dict):
                    author_name = author_data.get('name') or ''
                elif isinstance(author_data, str):
                    author_name = author_data
                author_name = author_name.strip()
                
                # CHỐNG ĐÁNH GIÁ ẢO: Lọc bỏ hoàn toàn các đánh giá vô danh hoặc ẩn danh
                if not author_name or author_name.lower() in GENERIC_NAMES:
                    continue
                
                user_id = f"u_{hashlib.md5(author_name.encode('utf-8')).hexdigest()[:8]}"
                
                # CellphoneS reviews trong JSON-LD thường không kèm review body, điền mặc định nếu trống
                review_text = rev.get('reviewBody') or rev.get('description') or 'Khách hàng không để lại ý kiến.'
                review_text = review_text.strip()
                
                content_hash = hashlib.md5(f"{author_name}_{review_text}".encode('utf-8')).hexdigest()[:8]
                review_id = f"r_{product_id}_{content_hash}"
                
                rating = 5
                rating_data = rev.get('reviewRating')
                if isinstance(rating_data, dict):
                    try:
                        rating = int(float(rating_data.get('ratingValue', 5)))
                    except:
                        rating = 5
                
                raw_date = rev.get('datePublished') or ''
                date = raw_date.split('T')[0] if 'T' in raw_date else raw_date
                date = date.strip() or datetime.now().strftime('%Y-%m-%d')
                
                reviews.append({
                    'review_id': review_id,
                    'user_id': user_id,
                    'product_id': product_id,
                    'rating': rating,
                    'review_text': review_text,
                    'date': date
                })
                
            print(f"    [v] Thành công: Lấy được thông tin sản phẩm và {len(reviews)} đánh giá hợp lệ.")
            return product_info, reviews
            
        except Exception as e:
            print(f"    [!] Lỗi khi cào chi tiết sản phẩm từ CellphoneS: {e}")
            return None, []

    def run(self, max_products_per_cat=100, target_category=None):
        categories = {
            'Điện thoại': ['https://cellphones.com.vn/mobile.html'],
            'Laptop': ['https://cellphones.com.vn/laptop.html'],
            'Máy tính bảng': ['https://cellphones.com.vn/tablet.html'],
            'Đồng hồ': ['https://cellphones.com.vn/do-choi-cong-nghe.html'],
            'Âm thanh': ['https://cellphones.com.vn/thiet-bi-am-thanh.html'],
            'Phụ kiện': ['https://cellphones.com.vn/phu-kien.html']
        }
        
        all_products = []
        all_reviews = []
        
        print("="*60)
        print(" BẮT ĐẦU CÀO DỮ LIỆU CELLPHONES (CELLPHONES.COM.VN)")
        print(f" - Số lượng sản phẩm yêu cầu tối đa/danh mục: {max_products_per_cat}")
        if target_category:
            print(f" - Danh mục mục tiêu: {target_category}")
        print(f" - Thời gian chờ (delay): {self.delay} giây")
        print(f" - Thư mục lưu trữ: {self.output_dir}")
        print("="*60)
        
        for cat_name, cat_urls in categories.items():
            if target_category and cat_name != target_category:
                continue
            product_links = self.get_product_links_from_category(cat_name, cat_urls, max_products_per_cat)
            
            for link in product_links:
                prod_info, prod_reviews = self.scrape_product_details(link, cat_name)
                if prod_info:
                    all_products.append(prod_info)
                    all_reviews.extend(prod_reviews)
                
                self.sleep()
        
        self.save_products(all_products)
        self.save_reviews(all_reviews)
        
        print("\n" + "="*60)
        print(" HOÀN THÀNH TIẾN TRÌNH CÀO DỮ LIỆU CELLPHONES!")
        print(f" - Tổng số sản phẩm thu được: {len(all_products)}")
        print(f" - Tổng số đánh giá thu được: {len(all_reviews)}")
        print(f" - File sản phẩm: {os.path.join(self.output_dir, 'products.csv')}")
        print(f" - File đánh giá: {os.path.join(self.output_dir, 'reviews.csv')}")
        print("="*60)

    def save_products(self, products):
        file_path = os.path.join(self.output_dir, 'products.csv')
        headers = ['product_id', 'title', 'category', 'price', 'description', 'image_url', 'brand', 'specs']
        
        existing_products = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('product_id'):
                            existing_products[row['product_id']] = row
            except Exception as e:
                print(f"[!] Không thể đọc dữ liệu products.csv cũ: {e}")
        
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
            print(f"[v] Đã cập nhật products.csv thành công. Số sản phẩm mới CellphoneS thêm: {new_count}. Tổng số hiện tại: {len(existing_products)}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu file products.csv: {e}")

    def save_reviews(self, reviews):
        file_path = os.path.join(self.output_dir, 'reviews.csv')
        headers = ['review_id', 'user_id', 'product_id', 'rating', 'review_text', 'date']
        
        existing_reviews = {}
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('review_id'):
                            existing_reviews[row['review_id']] = row
            except Exception as e:
                print(f"[!] Không thể đọc dữ liệu reviews.csv cũ: {e}")
                
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
            print(f"[v] Đã cập nhật reviews.csv thành công. Số đánh giá mới CellphoneS thêm: {new_count}. Tổng số hiện tại: {len(existing_reviews)}")
        except Exception as e:
            print(f"[!] Lỗi khi lưu file reviews.csv: {e}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Cào dữ liệu CellphoneS cho Luận Văn Hệ thống Gợi ý")
    parser.add_argument('--max-products', type=int, default=100, help='Số lượng sản phẩm tối đa trên mỗi danh mục (Mặc định: 100)')
    parser.add_argument('--delay', type=float, default=1.5, help='Thời gian chờ giữa các request bằng giây (Mặc định: 1.5)')
    parser.add_argument('--output-dir', type=str, default='data', help='Thư mục lưu trữ các file CSV kết quả (Mặc định: data)')
    parser.add_argument('--category', type=str, default=None, help='Chỉ cào danh mục cụ thể (Ví dụ: "Điện thoại")')
    
    args = parser.parse_args()
    
    scraper = CellphoneSScraper(delay=args.delay, output_dir=args.output_dir)
    scraper.run(max_products_per_cat=args.max_products, target_category=args.category)
