from skyfield.api import load, Star
from datetime import datetime, timezone
from numpy import arccos, degrees, dot, clip
from numpy.linalg import norm
import time
import schedule
from telegram import Bot
from telegram.error import TelegramError
import asyncio

# تنظیمات تلگرام
TELEGRAM_BOT_TOKEN = '7494441060:AAGv1j_mubDiPoTs1z0v83Ll7Wf_9R8S_V4'
TELEGRAM_CHANNEL_ID = '-1002571693738'  # یا آیدی عددی کانال

async def send_to_telegram(message):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        # تقسیم پیام به بخش‌های کوچکتر اگر طولانی باشد
        max_length = 4096  # حداکثر طول مجاز برای هر پیام تلگرام
        for i in range(0, len(message), max_length):
            chunk = message[i:i+max_length]
            await bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=chunk)
    except TelegramError as e:
        print(f"خطا در ارسال به تلگرام: {e}")

def format_results(results):
    """فرمت‌بندی نتایج برای نمایش در تلگرام"""
    formatted = []
    
    # اطلاعات سیستم خورشیدمرکزی
    formatted.append("🌞 سیستم خورشیدمرکزی 🌞")
    formatted.append(f"📅 تاریخ و زمان: {results['heliocentric']['time']}")
    formatted.append("\n📍 موقعیت اجرام:")
    for name, data in results['heliocentric']['positions'].items():
        formatted.append(f"{name}: RA={data['ra']:.2f}°, Dec={data['dec']:.2f}°, فاصله={data['distance']:.2f} AU")
    
    formatted.append("\n📐 زوایای بین اجرام:")
    for pair, angle in results['heliocentric']['angles'].items():
        formatted.append(f"{pair}: {angle:.2f}°")
    
    # اطلاعات سیستم زمین‌مرکزی
    formatted.append("\n🌍 سیستم زمین‌مرکزی 🌍")
    formatted.append(f"📅 تاریخ و زمان: {results['geocentric']['time']}")
    formatted.append("\n📍 موقعیت اجرام و ستارگان:")
    for name, data in results['geocentric']['positions'].items():
        formatted.append(f"{name}: RA={data['ra']:.2f}°, Dec={data['dec']:.2f}°")
    
    formatted.append("\n📐 زوایای جدایی:")
    for pair, angle in results['geocentric']['angles'].items():
        formatted.append(f"{pair}: {angle:.2f}°")
    
    return "\n".join(formatted)

def run_astronomical_calculations():
    # زمان فعلی با منطقه زمانی
    now = datetime.now(timezone.utc)
    time_str = now.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # بارگذاری ephemeris
    eph = load('de421.bsp')
    ts = load.timescale()
    t = ts.from_datetime(now)
    
    results = {
        'heliocentric': {'time': time_str, 'positions': {}, 'angles': {}},
        'geocentric': {'time': time_str, 'positions': {}, 'angles': {}}
    }
    
    # ======================================================================
    # بخش اول: محاسبات سیستم خورشیدمرکزی
    # ======================================================================
    
    # تعریف اجرام در سیستم خورشیدمرکزی
    sun = eph['sun']
    bodies_heliocentric = {
        'Sun': sun,
        'Mercury': eph['mercury barycenter'],
        'Venus': eph['venus barycenter'],
        'Earth': eph['earth barycenter'],
        'Moon': eph['moon'],
        'Mars': eph['mars barycenter'],
        'Jupiter': eph['jupiter barycenter'],
        'Saturn': eph['saturn barycenter'],
        'Uranus': eph['uranus barycenter'],
        'Neptune': eph['neptune barycenter'],
        'Pluto': eph['pluto barycenter']
    }
    
    # محاسبه موقعیت در سیستم خورشیدمرکزی
    positions_heliocentric = {}
    for name, body in bodies_heliocentric.items():
        pos = body.at(t).observe(sun)
        ra, dec, distance = pos.radec()
        positions_heliocentric[name] = pos
        
        results['heliocentric']['positions'][name] = {
            'ra': ra._degrees,
            'dec': dec.degrees,
            'distance': distance.au
        }
    
    # محاسبه زوایای بین اجرام در سیستم خورشیدمرکزی
    body_names = list(bodies_heliocentric.keys())
    for i in range(len(body_names)):
        for j in range(i+1, len(body_names)):
            name1 = body_names[i]
            name2 = body_names[j]
            
            pos1 = positions_heliocentric[name1].ecliptic_position().au
            pos2 = positions_heliocentric[name2].ecliptic_position().au
            
            if norm(pos1) == 0 or norm(pos2) == 0:
                continue
                
            cos_theta = dot(pos1, pos2) / (norm(pos1) * norm(pos2))
            angle = degrees(arccos(clip(cos_theta, -1, 1)))
            
            pair_name = f"{name1}-{name2}"
            results['heliocentric']['angles'][pair_name] = angle
    
    # ======================================================================
    # بخش دوم: محاسبات سیستم زمین‌مرکزی با ستارگان
    # ======================================================================
    
    # تعریف اجرام و ستارگان در سیستم زمین‌مرکزی
    bodies_geocentric = {
        'Sun': eph['sun'],
        'Moon': eph['moon'],
        'Mercury': eph['mercury barycenter'],
        'Venus': eph['venus barycenter'],
        'Mars': eph['mars barycenter'],
        'Jupiter': eph['jupiter barycenter'],
        'Saturn': eph['saturn barycenter'],
        'Uranus': eph['uranus barycenter'],
        'Neptune': eph['neptune barycenter'],
        'Pluto': eph['pluto barycenter'],
    }
    
    # اضافه کردن ستارگان مهم
    stars = {
        'Sirius': Star(ra_hours=(6, 45, 8.9), dec_degrees=(-16, 42, 58)),
        'Canopus': Star(ra_hours=(6, 23, 57.1), dec_degrees=(-52, 41, 44)),
        'Arcturus': Star(ra_hours=(14, 15, 39.7), dec_degrees=(19, 10, 57)),
        'Vega': Star(ra_hours=(18, 36, 56.3), dec_degrees=(38, 47, 1)),
    }
    
    all_objects = {**bodies_geocentric, **stars}
    earth = eph['earth']
    
    # محاسبه RA و Dec برای هر جرم
    positions_geocentric = {}
    for name, obj in all_objects.items():
        ra, dec, _ = earth.at(t).observe(obj).radec()
        positions_geocentric[name] = {
            'ra': ra._degrees,
            'dec': dec.degrees,
            'position': earth.at(t).observe(obj)
        }
        results['geocentric']['positions'][name] = {
            'ra': ra._degrees,
            'dec': dec.degrees
        }
    
    # محاسبه زاویه جدایی بین تمام جفت‌ها
    names = list(all_objects.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            name1 = names[i]
            name2 = names[j]
            
            p1 = positions_geocentric[name1]['position'].position.au
            p2 = positions_geocentric[name2]['position'].position.au
            
            dot_product = dot(p1, p2)
            norm_p1 = norm(p1)
            norm_p2 = norm(p2)
            
            denominator = norm_p1 * norm_p2
            if denominator == 0:
                separation_angle_deg = 0.0
            else:
                cos_angle = dot_product / denominator
                cos_angle = clip(cos_angle, -1.0, 1.0)
                separation_angle_deg = degrees(arccos(cos_angle))
            
            pair_name = f"{name1}-{name2}"
            results['geocentric']['angles'][pair_name] = separation_angle_deg
    
    # فرمت‌بندی و ارسال نتایج
    formatted_message = format_results(results)
    asyncio.run(send_to_telegram(formatted_message))
    
    # همچنین چاپ در کنسول برای مشاهده محلی
    print(formatted_message)

# اجرای اولیه
run_astronomical_calculations()

# تنظیم زمان‌بندی برای اجرای هر ساعت
schedule.every().hour.do(run_astronomical_calculations)

# حلقه اصلی برای اجرای زمان‌بندی شده
while True:
    schedule.run_pending()
    time.sleep(1)