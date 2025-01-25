import requests
import csv
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_products(page):
    url = f"https://api.digikala.com/v1/categories/mobile-phone/search/?page={page}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()['data']['products']  # لیست محصولات
    else:
        print(f"خطا در دریافت صفحه {page}. کد وضعیت: {response.status_code}")
        return None
    
def extract_value(data, keys, default=None):
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data

def export_csv(items, csv_filename):
    # ذخیره اطلاعات محصولات در یک فایل CSV
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # نوشتن سطر عنوان‌ ها
        writer.writerow([
            'عنوان انگلیسی', 'عنوان فارسی', 'قیمت اصلی', 'قیمت فروش', 'درصد تخفیف',
            'امتیاز', 'تعداد نظرات', 'نام فروشنده', 'امتیاز فروشنده', 'موجودی', 'گارانتی'
        ])
        # نوشتن هر محصول به عنوان یک سطر
        for product in items:
            row = [
                extract_value(product, ['title_en']),
                extract_value(product, ['title_fa']),
                extract_value(product, ['default_variant', 'price', 'rrp_price']),
                extract_value(product, ['default_variant', 'price', 'selling_price']),
                extract_value(product, ['default_variant', 'price', 'discount_percent']),
                extract_value(product, ['rating', 'rate']),
                extract_value(product, ['rating', 'count']),
                extract_value(product, ['default_variant', 'seller', 'title']),
                extract_value(product, ['default_variant', 'seller', 'rating', 'total_rate']),
                extract_value(product, ['default_variant', 'price', 'marketable_stock']),
                extract_value(product, ['default_variant', 'warranty', 'title_fa'])
            ]
            writer.writerow(row)
    print(f"داده‌ها در '{csv_filename}' ذخیره شدند.")

def export_sqlite(items, db_filename):
    # ذخیره اطلاعات محصولات در یک پایگاه داده SQLite
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    
    # ایجاد جدول اگر وجود نداشته باشد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            title_en TEXT, title_fa TEXT, rrp_price REAL, selling_price REAL,
            discount_percent REAL, rating REAL, reviews_count INTEGER,
            seller_name TEXT, seller_rating REAL, stock INTEGER, warranty TEXT
        )
    ''')
    
    conn.execute('BEGIN TRANSACTION')
    try:
        for product in items:
            cursor.execute('''
                INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                extract_value(product, ['title_en']),
                extract_value(product, ['title_fa']),
                extract_value(product, ['default_variant', 'price', 'rrp_price']),
                extract_value(product, ['default_variant', 'price', 'selling_price']),
                extract_value(product, ['default_variant', 'price', 'discount_percent']),
                extract_value(product, ['rating', 'rate']),
                extract_value(product, ['rating', 'count']),
                extract_value(product, ['default_variant', 'seller', 'title']),
                extract_value(product, ['default_variant', 'seller', 'rating', 'total_rate']),
                extract_value(product, ['default_variant', 'price', 'marketable_stock']),
                extract_value(product, ['default_variant', 'warranty', 'title_fa'])
            ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"خطا در ذخیره داده‌ها: {e}")
    finally:
        conn.close()
    print(f"داده‌ها در '{db_filename}' ذخیره شدند.")

def main():
    # دریافت ورودی از کاربر برای تعداد صفحات، نوع ذخیره‌ سازی و نام فایل
    num_pages = int(input("تعداد صفحات را وارد کنید: "))
    storage_type = input("نوع ذخیره‌ سازی را انتخاب کنید (csv یا sqlite): ").strip().lower()
    filename = input("نام فایل را وارد کنید (بدون پسوند): ").strip()
    
    if storage_type == 'csv':
        filename = f"{filename}.csv"
    else:
        filename = f"{filename}.db"

    concurrent = input("آیا از همزمانی استفاده شود؟ (بله/خیر): ").strip().lower() == 'بله'
    products_list = []

    if concurrent:
        with ThreadPoolExecutor(max_workers=10) as executor:
            tasks = []
            for page in range(1, num_pages + 1):
                future = executor.submit(get_products, page)
                tasks.append(future)
            
            for future in as_completed(tasks):
                items = future.result()
                if items:
                    products_list.extend(items)
                    print(f"صفحه {tasks.index(future) + 1} دریافت شد.")
    else:
        # دریافت صفحات به ترتیب
        for page in range(1, num_pages + 1):
            print(f"در حال دریافت صفحه {page}...")
            items = get_products(page)
            if items:
                products_list.extend(items)
                print(f"صفحه {page} با موفقیت دریافت شد.")

    # ذخیره داده‌ ها در نوع ذخیره‌ سازی انتخاب شده
    if storage_type == 'csv':
        export_csv(products_list, filename)
    else:
        export_sqlite(products_list, filename)

if __name__ == "__main__":
    main()
