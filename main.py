# -*- coding: utf-8 -*-

import os
import logging
import random
import io
import asyncio
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberUpdated,
    MessageEntity,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ChatMemberHandler,
    ConversationHandler,
)
from telegram.constants import ParseMode
import psycopg2
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

# --- پیکربندی اصلی ---
OWNER_IDS = [7662192190, 6041119040] # آیدی‌های عددی مالک ربات
SUPPORT_USERNAME = "OLDKASEB" # یوزرنیم پشتیبانی بدون @
FORCED_JOIN_CHANNEL = "@RHINOSOUL_TM" # کانال عضویت اجباری با @
GROUP_INSTALL_LIMIT = 50
INITIAL_LIVES = 6
# --- تعریف حالت‌های مکالمه ---
# برای بازی قارچ
ASKING_GOD_USERNAME, CONFIRMING_GOD = range(2)
# برای بازی حدس عدد
SELECTING_RANGE, GUESSING = range(2)
# برای پنل جدید (حالت‌های دریافت ورودی از ادمین)
WAITING_FOR_CUSTOM_RANGE, WAITING_FOR_CUSTOM_ETERAF, WAITING_FOR_GHARCH_GOD = range(3, 6)
# برای پنل RSGAME (حالت‌های دریافت ورودی از ادمین)
RS_PANEL_WAITING_FOR_ETERAF_TEXT, RS_PANEL_WAITING_FOR_GHARCH_GOD = range(6, 8)

# --- لیست کلمات و جملات (بدون تغییر) ---
WORD_LIST = [
    "فضاپیما", "کهکشان", "الگوریتم", "کتابخانه", "دانشگاه", "کامپیوتر", "اینترنت", "برنامه", "نویسی", "هوش", "مصنوعی", "یادگیری", "ماشین", "شبکه", "عصبی", "داده", "کاوی", "پایتون", "جاوا", "اسکریپت", 
    "فناوری", "اطلاعات", "امنیت", "سایبری", "حمله", "ویروس", "بدافزار", "آنتی", "ویروس", "دیوار", "آتش", "رمزنگاری", "پروتکل", "دامنه", "میزبانی", "وب", "سرور", "کلاینت", "پایگاه", "داده", 
    "رابط", "کاربری", "تجربه", "کاربری", "طراحی", "گرافیک", "انیمیشن", "سه", "بعدی", "واقعیت", "مجازی", "افزوده", "بلاکچین", "ارز", "دیجیتال", "بیتکوین", "اتریوم", "قرارداد", "هوشمند", "متاورس", 
    "اشیاء", "رباتیک", "خودرو", "خودران", "پهپاد", "سنسور", "پردازش", "تصویر", "سیگنال", "مخابرات", "ماهواره", "فرکانس", "موج", "الکترومغناطیس", "فیزیک", "کوانتوم", "نسبیت", "انیشتین", "نیوتن", 
    "گرانش", "سیاهچاله", "ستاره", "نوترونی", "انفجار", "بزرگ", "کیهان", "شناسی", "اختر", "فیزیک", "شیمی", "آلی", "معدنی", "تجزیه", "بیوشیمی", "ژنتیک", "سلول", "بافت", "ارگان", "متابولیسم", 
    "فتوسنتز", "تنفس", "سلولی", "زیست", "شناسی", "میکروبیولوژی", "باکتری", "قارچ", "پزشکی", "داروسازی", "جراحی", "قلب", "مغز", "اعصاب", "روانشناسی", "جامعه", "شناسی", "اقتصاد", "بازار", 
    "سرمایه", "بورس", "سهام", "تورم", "رکود", "رشد", "اقتصادی", "تولید", "ناخالص", "داخلی", "صادرات", "واردات", "تجارت", "بین", "الملل", "سیاست", "دموکراسی", "دیکتاتوری", "جمهوری", "پادشاهی", 
    "انتخابات", "پارلمان", "دولت", "قوه", "قضائیه", "تاریخ", "باستان", "معاصر", "جنگ", "جهانی", "صلیبی", "رنسانس", "اصلاحات", "دینی", "انقلاب", "صنعتی", "فلسفه", "منطق", "اخلاق", "زیبایی", 
    "شناسی", "افلاطون", "ارسطو", "سقراط", "دکارت", "کانت", "نیچه", "ادبیات", "شعر", "رمان", "داستان", "کوتاه", "نمایشنامه", "حافظ", "سعدی", "فردوسی", "مولانا", "خیام", "شکسپیر", "تولستوی", 
    "داستایوفسکی", "هنر", "نقاشی", "مجسمه", "سازی", "معماری", "موسیقی", "سینما", "تئاتر", "عکاسی", "خورشید", "سیاره", "مریخ", "زمین", "مشتری", "اورانوس", "نپتون", "زهره", "عطارد", "ستاره", 
    "دنباله", "دار", "شهاب", "سنگ", "صورت", "فلکی", "تلسکوپ", "رصدخانه", "فیزیکدان", "شیمیدان", "زیست", "شناس", "ریاضیات", "هندسه", "جبر", "مثلثات", "حسابان", "دیفرانسیل", "انتگرال", "آمار", 
    "احتمال", "ماتریس", "بردار", "اقلیدس", "فیثاغورس", "خوارزمی", "ابن", "سینا", "رازی", "بیرونی", "عنصر", "جدول", "تناوبی", "اتم", "مولکول", "یون", "ایزوتوپ", "واکنش", "شیمیایی", "کاتالیزور", 
    "آنزیم", "پروتئین", "کربوهیدرات", "لیپید", "ویتامین", "ماده", "معدنی", "دی", "ان", "ای", "ژن", "کروموزوم", "جهش", "تکامل", "داروین", "لامارک", "محیط", "زیست", "اکوسیستم", "آلودگی", "گرمایش", 
    "جهانی", "بازیافت", "انرژی", "تجدیدپذیر", "خورشیدی", "بادی", "برق", "آبی", "زمین", "گرمایی", "جنگل", "بیابان", "اقیانوس", "دریا", "رودخانه", "دریاچه", "کوهستان", "آتشفشان", "زلزله", "سونامی", 
    "طوفان", "گردباد", "خشکسالی", "سیل", "قاره", "آسیا", "اروپا", "آفریقا", "آمریکا", "اقیانوسیه", "قطب", "شمال", "جنوب", "استوا", "نصف", "النهار", "مدار", "جغرافیا", "نقشه", "قطب", "نما", 
    "تمدن", "مصر", "یونان", "روم", "ایران", "چین", "هند", "بین", "النهرین", "سومر", "بابل", "آشور", "هخامنشیان", "اشکانیان", "ساسانیان", "اسلام", "مغول", "صفویه", "قاجار", "پهلوی", "جمهوری", 
    "اسلامی", "اسطوره", "افسانه", "حماسه", "رستم", "سهراب", "اسفندیار", "سیمرغ", "ضحاک", "کاوه", "آهنگر", "گیلگمش", "هرکول", "زئوس", "آپولو", "پوزیدون", "هرمس", "آفرودیت", "جشنواره", "کارناوال", 
    "فستیوال", "المپیک", "جام", "جهانی", "فوتبال", "بسکتبال", "والیبال", "کشتی", "وزنه", "برداری", "دو", "میدانی", "شنا", "ژیمناستیک", "ورزشگاه", "استادیوم", "قهرمان", "مدال", "طلا", "نقره", "برنز", 
    "رکورد", "پایتخت", "تهران", "پاریس", "لندن", "رم", "نیویورک", "توکیو", "پکن", "مسکو", "برلین", "مادرید", "قاهره", "استانبول", "سیدنی", "تورنتو", "دبی", "ریاض", "دوحه", "پادشاه", "ملکه", 
    "شاهزاده", "رئیس", "جمهور", "نخست", "وزیر", "سفیر", "دیپلمات", "دیپلماسی", "مذاکره", "قرارداد", "پیمان", "صلح", "آتش", "بس", "ارتش", "سپاه", "نیروی", "هوایی", "دریایی", "زمینی", "سرباز", 
    "افسر", "ژنرال", "فرمانده", "جنگ", "نبرد", "عملیات", "استراتژی", "تاکتیک", "سلاح", "موشک", "تانک", "هواپیما", "ناو", "زیردریایی", "جاسوسی", "اطلاعات", "پروپاگاندا", "سانسور", "آزادی", 
    "بیان", "حقوق", "بشر", "شهروند", "مهاجرت", "پناهنده", "مرز", "گذرنامه", "ویزا", "جهانگردی", "توریسم", "هتل", "رستوران", "فرودگاه", "بندر", "ایستگاه", "قطار", "اتوبوس", "تاکسی", "مترو", 
    "بزرگراه", "خیابان", "کوچه", "میدان", "چهارراه", "چراغ", "راهنمایی", "پل", "تونل", "ساختمان", "آسمان", "خراش", "برج", "آپارتمان", "ویلا", "کلبه", "قصر", "قلعه", "موزه", "گالری", "کتابفروشی", 
    "کنسرت", "اپرا", "باله", "نمایشگاه", "باغ", "وحش", "پارک", "جنگلی", "ساحل", "پلاژ", "اسکله", "قایق", "کشتی", "لنج", "جت", "اسکی", "غواصی", "موج", "سواری", "اسکی", "اسنوبرد", "کوهنوردی", 
    "صخره", "نوردی", "طبیعت", "گردی", "فیلمبرداری", "خوشنویسی", "سفالگری", "جواهرسازی", "خیاطی", "گلدوزی", "بافتنی", "آشپزی", "شیرینی", "پزی", "نانوایی", "قنادی", "کافه", "قهوه", "چای", "نوشیدنی", 
    "صبحانه", "ناهار", "شام", "دسر", "پیش", "غذا", "سالاد", "سوپ", "کباب", "پیتزا", "ساندویچ", "پاستا", "برنج", "خورش", "سبزیجات", "میوه", "خشکبار", "آجیل", "ادویه", "زعفران", "هل", "دارچین", 
    "زنجبیل", "فلفل", "نمک", "شکر", "عسل", "مربا", "شکلات", "بستنی", "کیک", "شیرینی", "بیمارستان", "درمانگاه", "مطب", "داروخانه", "پزشک", "پرستار", "جراح", "متخصص", "دندانپزشک", "چشم", "پزشک", 
    "داروساز", "آمبولانس", "اورژانس", "بیماری", "سلامتی", "درمان", "واکسن", "آنتی", "بیوتیک", "قرص", "شربت", "آمپول", "سرم", "آزمایشگاه", "رادیولوژی", "سونوگرافی", "سی", "تی", "اسکن", "ام", "آر", "آی", 
    "مدرسه", "دبیرستان", "هنرستان", "کالج", "آموزشگاه", "زبان", "معلم", "دبیر", "استاد", "دانش", "آموز", "دانشجو", "کلاس", "درس", "امتحان", "کنکور", "پایان", "نامه", "رساله", "دکترا", "کارشناسی", 
    "ارشد", "لیسانس", "دیپلم", "تحصیلات", "پژوهش", "مقاله", "علمی", "مجله", "کنفرانس", "سمینار", "کارگاه", "آموزشی", "شرکت", "کارخانه", "اداره", "سازمان", "موسسه", "بنیاد", "انجمن", "اتحادیه", 
    "سندیکا", "مدیر", "کارمند", "کارگر", "کارشناس", "مشاور", "تحلیلگر", "حسابدار", "وکیل", "قاضی", "دادگاه", "دادسرا", "زندان", "پلیس", "آگاهی", "جرم", "جنایت", "متهم", "شاکی", "شاهد", "مجازات", 
    "جریمه", "حبس", "اعدام", "خانواده", "پدر", "مادر", "فرزند", "برادر", "خواهر", "پدربزرگ", "مادربزرگ", "نوه", "عمو", "عمه", "دایی", "خاله", "ازدواج", "طلاق", "تولد", "مرگ", "عروسی", "عزاداری", 
    "جشن", "مهمانی", "دوست", "رفیق", "همکار", "همسایه", "عشق", "نفرت", "شادی", "غم", "خشم", "ترس", "امید", "ناامیدی", "اعتماد", "خیانت", "شجاعت", "بزدلی", "صداقت", "دروغ", "عدالت", "بی", 
    "عدالتی", "آرامش", "استرس", "موفقیت", "شکست", "ثروت", "فقر", "قدرت", "ضعف", "زیبایی", "زشتی", "جوانی", "پیری", "کودکی", "نوجوانی", "بزرگسالی", "خاطره", "رویا", "آرزو", "هدف", "برنامه", "ریزی", 
    "آینده", "گذشته", "حال", "زمان", "ساعت", "دقیقه", "ثانیه", "روز", "هفته", "ماه", "سال", "قرن", "دهه", "تقویم", "فصل", "بهار", "تابستان", "پاییز", "زمستان", "آب", "هوا", "آفتابی", "ابری", "بارانی", 
    "برفی", "باد", "مه", "رعد", "برق", "رنگین", "کمان", "رنگ", "قرمز", "آبی", "زرد", "سبز", "نارنجی", "بنفش", "صورتی", "قهوه", "ای", "سیاه", "سفید", "خاکستری", "طلا", "نقره", "مس", "آهن", "آلومینیوم", 
    "فولاد", "پلاستیک", "شیشه", "چوب", "سنگ", "پارچه", "لباس", "پوشاک", "کفش", "کیف", "کلاه", "عینک", "جواهرات", "عطر", "ادکلن", "لوازم", "آرایش", "بهداشتی", "شامپو", "صابون", "خمیر", "دندان", 
    "مسواک", "حوله", "خانه", "آشپزخانه", "اتاق", "خواب", "پذیرایی", "حمام", "دستشویی", "مبلمان", "فرش", "پرده", "لوستر", "تلویزیون", "یخچال", "اجاق", "گاز", "ماشین", "لباسشویی", "ظرفشویی", 
    "مایکروویو", "جاروبرقی", "تلفن", "همراه", "تبلت", "لپتاپ", "دوربین", "بلندگو", "هدفون", "کتاب", "دفتر", "خودکار", "مداد", "پاک", "کن", "تراش", "خط", "کش", "پرگار", "کاغذ", "مقوا", "چسب", "قیچی", "منگنه", "روزنامه"
]
TYPING_SENTENCES = [
    "در یک دهکده کوچک مردی زندگی میکرد که به شجاعت و دانایی مشهور بود", "فناوری بلاکچین پتانسیل ایجاد تحول در صنایع مختلف را دارد", 
    "یادگیری یک زبان برنامه نویسی جدید میتواند درهای جدیدی به روی شما باز کند", "کتاب خواندن بهترین راه برای سفر به دنیاهای دیگر بدون ترک کردن خانه است", 
    "شب های پرستاره کویر منظره ای فراموش نشدنی را به نمایش میگذارند", "تیم ما برای رسیدن به این موفقیت تلاش های شبانه روزی زیادی انجام داد", 
    "حفظ محیط زیست وظیفه تک تک ما برای نسل های آینده است", "موفقیت در زندگی نیازمند تلاش پشتکار و کمی شانس است", 
    "اینترنت اشیاء دنیایی را متصور میشود که همه چیز به هم متصل است", "بزرگترین ماجراجویی که میتوانی داشته باشی زندگی کردن رویاهایت است", 
    "برای حل مسائل پیچیده گاهی باید از زوایای مختلف به آنها نگاه کرد", "تاریخ پر از درس هایی است که میتوانیم برای ساختن آینده ای بهتر از آنها بیاموزیم", 
    "هوش مصنوعی به سرعت در حال تغییر چهره جهان ما است", "یک دوست خوب گنجی گرانبها در فراز و نشیب های زندگی است", "سفر کردن به نقاط مختلف جهان دیدگاه انسان را گسترش میدهد", 
    "ورزش منظم کلید اصلی برای داشتن بدنی سالم و روحی شاداب است", "موسیقی زبان مشترک تمام انسان ها در سراسر کره زمین است", 
    "هیچگاه برای یادگیری و شروع یک مسیر جدید دیر نیست", "احترام به عقاید دیگران حتی اگر با آنها مخالف باشیم نشانه بلوغ است", 
    "تغییر تنها پدیده ثابت در جهان هستی است باید خود را با آن وفق دهیم", "صبر و شکیبایی در برابر مشکلات آنها را در نهایت حل شدنی میکند", 
    "خلاقیت یعنی دیدن چیزی که دیگران نمیبینند و انجام کاری که دیگران جراتش را ندارند", "شادی واقعی در داشتن چیزهای زیاد نیست بلکه در لذت بردن از چیزهایی است که داریم", 
    "صداقت و راستگویی سنگ بنای هر رابطه پایدار و موفقی است", "کهکشان راه شیری تنها یکی از میلیاردها کهکشان موجود در کیهان است", 
    "برای ساختن یک ربات پیشرفته به دانش برنامه نویسی و الکترونیک نیاز است", "امنیت سایبری در دنیای دیجیتال امروز از اهمیت فوق العاده ای برخوردار است", 
    "هرگز قدرت یک ایده خوب را دست کم نگیر میتواند دنیا را تغییر دهد", "کار گروهی و همکاری میتواند منجر به نتایجی شگفت انگیز شود", 
    "شکست بخشی از مسیر موفقیت است از آن درس بگیرید و دوباره تلاش کنید", "جنگل های آمازون به عنوان ریه های کره زمین شناخته میشوند", 
    "کوه اورست بلندترین قله جهان در رشته کوه هیمالیا قرار دارد", "دیوار بزرگ چین یکی از شگفتی های ساخت بشر در طول تاریخ است", 
    "اهرام ثلاثه مصر نماد تمدن باستانی و معماری شگفت انگیز آن دوران هستند", "خورشید گرفتگی زمانی رخ میدهد که ماه بین زمین و خورشید قرار بگیرد", 
    "آب مایه حیات است و باید در مصرف آن صرفه جویی کنیم", "زنبورهای عسل نقش بسیار مهمی در گرده افشانی و حیات گیاهان دارند", 
    "بازیافت زباله به حفظ منابع طبیعی و کاهش آلودگی کمک میکند", "کهکشان آندرومدا نزدیکترین کهکشان مارپیچی به کهکشان ما است", 
    "سرعت نور بالاترین سرعت ممکن در جهان هستی محسوب میشود", "هر انسان دارای اثر انگشت منحصر به فردی است که او را از دیگران متمایز میکند", 
    "یوزپلنگ سریعترین حیوان روی خشکی است و میتواند به سرعت بالایی برسد", "قلب یک انسان بالغ به طور متوسط صد هزار بار در روز میتپد", 
    "خواب کافی برای سلامت جسم و روان و عملکرد بهتر مغز ضروری است", "ویتامین دی با قرار گرفتن در معرض نور خورشید در بدن تولید میشود", 
    "خنده بهترین دارو برای کاهش استرس و تقویت سیستم ایمنی بدن است", "یادگیری موسیقی میتواند به بهبود حافظه و هماهنگی اعضای بدن کمک کند", 
    "ارتباطات ماهواره ای امکان برقراری تماس در سراسر جهان را فراهم کرده است", "فیبر نوری با استفاده از پالس های نوری داده ها را با سرعت بالا منتقل میکند", 
    "واقعیت مجازی تجربه ای فراگیر از یک دنیای شبیه سازی شده را ارائه میدهد", "چاپگرهای سه بعدی قادر به ساخت اشیاء فیزیکی از روی مدل های دیجیتال هستند", 
    "خودروهای الکتریکی با هدف کاهش آلودگی هوا در حال گسترش هستند", "انرژی هسته ای از شکافت اتم ها برای تولید برق استفاده میکند", "قطره قطره جمع گردد وانگهی دریا شود", 
    "آینده ساختنی است نه یافتنی پس باید برای آن تلاش کرد", "بهترین زمان برای کاشتن یک درخت بیست سال پیش بود زمان بعدی همین امروز است", 
    "برای دیدن رنگین کمان باید هم باران را تحمل کنی هم آفتاب را", "موفقیت مجموعه ای از تلاش های کوچک است که هر روز تکرار میشوند", 
    "تنها محدودیت های زندگی آنهایی هستند که خودمان برای خودمان ایجاد میکنیم", "به جای نگرانی در مورد چیزهایی که نمیتوانی کنترل کنی روی چیزهایی که میتوانی تغییر دهی تمرکز کن", 
    "شجاعت نبودن ترس نیست بلکه عمل کردن با وجود ترس است", "یک سفر هزار کیلومتری با اولین قدم آغاز میشود", "زندگی مثل دوچرخه سواری است برای حفظ تعادل باید به حرکت ادامه دهی", 
    "انسان های موفق همیشه به دنبال فرصت هایی برای کمک به دیگران هستند", "هدف گذاری اولین قدم برای تبدیل نادیدنی ها به دیدنی ها است", 
    "راز پیشرفت شروع کردن است پس منتظر زمان مناسب نمان", "اگر میخواهی متفاوت باشی باید کارهای متفاوتی انجام دهی", "اشتباه کردن بخشی از انسان بودن است مهم درس گرفتن از آنها است", 
    "اجازه نده سر و صدای عقاید دیگران صدای درونی تو را خاموش کند", "خوشبختی یک مسیر است نه یک مقصد از لحظات خود لذت ببر", 
    "تنها راه انجام دادن کارهای بزرگ دوست داشتن کاری است که انجام میدهی", "فرصت ها مانند طلوع خورشید هستند اگر زیاد صبر کنی آنها را از دست میدهی", 
    "استعداد ذاتی فقط یک شروع است باید با تلاش آن را پرورش دهی", "با افکار مثبت دنیای خود را زیباتر کن چون زندگی انعکاس افکار تو است", 
    "برای رسیدن به قله باید سختی های مسیر را تحمل کرد", "سکوت گاهی بهترین پاسخ به سوالات بی معنی است", "برای داشتن دوست وفادار باید خودت یک دوست وفادار باشی", 
    "امید مانند چراغی در تاریکی مسیر را برایت روشن میکند", "کتاب ها بهترین دوستان خاموش ما هستند که هرگز ما را ترک نمیکنند", 
    "دانش قدرتی است که هیچکس نمیتواند آن را از تو بگیرد", "گذشته را نمیتوان تغییر داد اما آینده هنوز در دستان تو است", 
    "تفاوت بین یک فرد موفق و دیگران کمبود قدرت نیست بلکه کمبود اراده است", "انسان های بزرگ درباره ایده ها صحبت میکنند انسان های متوسط درباره رویدادها و انسان های کوچک درباره دیگران", 
    "برای پرواز کردن لازم نیست حتما بال داشته باشی داشتن اراده و رویا کافی است", "ساده ترین کارها اغلب درست ترین آنها هستند", 
    "تمرین زیاد باعث میشود کارهای سخت آسان به نظر برسند", "یک ذهن آرام میتواند قوی ترین طوفان ها را پشت سر بگذارد", 
    "هرگز اجازه نده دیروز بخش زیادی از امروز تو را به خود اختصاص دهد", "اگر به دنبال نتایج متفاوت هستی باید روش های متفاوتی را امتحان کنی", 
    "صبر کلید موفقیت در تمام مراحل زندگی است", "سعی نکن انسان موفقی باشی بلکه سعی کن انسان با ارزشی باشی", "راز شاد زیستن در لذت بردن از چیزهای کوچک است", 
    "همیشه به یاد داشته باش که مسیر موفقیت در حال ساخت است نه یک جاده آماده", "یک لبخند میتواند شروع یک دوستی زیبا باشد", 
    "اگر میخواهی دنیا را تغییر دهی از مرتب کردن تخت خودت شروع کن", "بخشیدن دیگران به معنای فراموش کردن گذشته نیست بلکه به معنای ساختن آینده ای بهتر است", 
    "مهربانی زبانی است که ناشنوایان میتوانند بشنوند و نابینایان میتوانند ببینند", "هر روز یک فرصت جدید برای شروع دوباره و بهتر شدن است", 
    "سعی نکن در برابر طوفان مقاومت کنی یاد بگیر در باران برقصی", "زندگی یک بوم نقاشی است سعی کن آن را با رنگ های شاد رنگ آمیزی کنی", 
    "اگر بتوانی چیزی را رویاپردازی کنی پس حتما میتوانی آن را انجام دهی", "مهم نیست چقدر آهسته حرکت میکنی تا زمانی که متوقف نشوی پیشرفت خواهی کرد", 
    "یک شمع میتواند هزاران شمع دیگر را روشن کند بدون آنکه از عمرش کاسته شود", "شادی زمانی دوچندان میشود که آن را با دیگران تقسیم کنی", 
    "بهترین راه برای پیش بینی آینده ساختن آن است", "هرگز برای تبدیل شدن به آن کسی که میتوانستی باشی دیر نیست", 
    "ذهن انسان مانند یک باغ است هرچه در آن بکاری همان را درو میکنی", "یک گفتگو صادقانه میتواند بسیاری از مشکلات را حل کند", 
    "سخاوت یعنی بخشیدن بیش از توانایی ات و غرور یعنی گرفتن کمتر از نیازت", "کسانی که به اندازه کافی دیوانه هستند که فکر کنند میتوانند دنیا را تغییر دهند همان هایی هستند که این کار را میکنند", 
    "انتقام گرفتن تو را با دشمنت برابر میکند اما بخشیدن او تو را برتر از او قرار میدهد", "کسی که سوال میپرسد برای یک دقیقه نادان است اما کسی که سوال نمیپرسد برای همیشه نادان باقی میماند", 
    "زندگی کوتاهتر از آن است که وقت خود را صرف متنفر بودن از دیگران کنی", "برای ساختن یک خانه محکم باید پایه های آن را قوی بنا کنی", 
    "یک کتاب خوب میتواند دیدگاه تو را نسبت به کل دنیا تغییر دهد", "قدرت واقعی در کنترل کردن دیگران نیست بلکه در کنترل کردن خود است", 
    "هرگز ارزش یک لحظه را نمیفهمی تا زمانی که به یک خاطره تبدیل شود", "برای شنا کردن در جهت مخالف رودخانه باید قویتر از جریان آب باشی", 
    "یک قهرمان واقعی کسی است که با وجود تمام سختی ها دوباره برمیخیزد", "آرامش را در درون خودت پیدا کن نه در دنیای بیرون", 
    "اولین قدم برای رسیدن به هر جایی تصمیم گرفتن برای حرکت است", "اگر به زیبایی اعتقاد داشته باشی آن را در همه جا خواهی دید", 
    "هیچ چیز ارزشمندی به آسانی به دست نمی آید", "یک دروغ ممکن است برای مدتی تو را نجات دهد اما در نهایت حقیقت آشکار میشود", 
    "برای شنیدن صدای فرصت ها باید گوش هایت را تیز کنی", "یک رهبر واقعی راه را بلد است راه را میرود و راه را نشان میدهد", 
    "هرگز اجازه نده موفقیت هایت تو را مغرور و شکست هایت تو را ناامید کند", "زیبایی واقعی در سادگی نهفته است", 
    "یک دوست خوب در روزهای سخت مانند آینه و در روزهای خوب مانند سایه است", "برای رسیدن به نور باید از تاریکی عبور کرد", 
    "دانش بدون عمل مانند ابری بی باران است", "زندگی یک بازی است سعی کن از آن لذت ببری و جوانمردانه بازی کنی", 
    "اعتماد مانند یک کاغذ است اگر مچاله شود دیگر هرگز صاف نخواهد شد", "یک قلب مهربان از تمام معابد و مساجد دنیا مقدس تر است", 
    "آینده متعلق به کسانی است که به زیبایی رویاهایشان ایمان دارند", "جاده ابریشم یک مسیر تجاری باستانی برای اتصال شرق و غرب بود", 
    "کوه دماوند بلندترین قله آتشفشانی در خاورمیانه است", "آرش کمانگیر مرز ایران و توران را با پرتاب یک تیر مشخص کرد", 
    "خلیج فارس یکی از مهمترین آبراه های استراتژیک جهان به شمار میرود", "راز تغییر کردن در این است که تمام انرژی خود را روی ساختن عادت های جدید بگذاری"
]

# --- تنظیمات لاگ ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- مدیریت دیتابیس ---
DATABASE_URL = os.environ.get("DATABASE_URL")
def get_db_connection():
    try: return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def setup_database():
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, first_name VARCHAR(255), username VARCHAR(255), start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW());")
                cur.execute("CREATE TABLE IF NOT EXISTS groups (group_id BIGINT PRIMARY KEY, title VARCHAR(255), member_count INT, added_time TIMESTAMP WITH TIME ZONE DEFAULT NOW());")
                cur.execute("CREATE TABLE IF NOT EXISTS start_message (id INT PRIMARY KEY, message_id BIGINT, chat_id BIGINT);")
                cur.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id BIGINT PRIMARY KEY);")
                cur.execute("CREATE TABLE IF NOT EXISTS banned_groups (group_id BIGINT PRIMARY KEY);")
            conn.commit()
            logger.info("Database setup complete.")
        except Exception as e: logger.error(f"Database setup failed: {e}")
        finally: conn.close()

# --- توابع کمکی ---
async def is_owner(user_id: int) -> bool: return user_id in OWNER_IDS
async def is_group_admin(user_id: int, chat_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if await is_owner(user_id): return True
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        return user_id in {admin.user.id for admin in admins}
    except Exception:
        return False
def convert_persian_to_english_numbers(text: str) -> str:
    if not text: return ""
    return text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))

# --- مدیریت وضعیت بازی‌ها ---
active_games = {'guess_number': {}, 'dooz': {}, 'hangman': {}, 'typing': {}, 'hokm': {}}
active_gharch_games = {}
# --- منطق عضویت اجباری و بن ---
async def pre_command_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if not user: return False

    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM banned_users WHERE user_id = %s;", (user.id,))
            if cur.fetchone(): return False
            if chat.type != 'private':
                cur.execute("SELECT 1 FROM banned_groups WHERE group_id = %s;", (chat.id,))
                if cur.fetchone(): 
                    try: await context.bot.leave_chat(chat.id)
                    except: pass
                    return False
        conn.close()
    
    return await force_join_middleware(update, context)

async def force_join_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not user: return False
    if await is_owner(user.id): return True
    try:
        member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
        if member.status in ['member', 'administrator', 'creator']: return True
    except Exception as e:
        logger.warning(f"Could not check channel membership for {user.id}: {e}")
    
    keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")]]
    text = f"❗️{user.mention_html()}، برای استفاده از ربات ابتدا باید در کانال ما عضو شوی و مجددا ربات را استارت کنی:\n\n{FORCED_JOIN_CHANNEL}"

    target_chat = update.effective_chat
    if update.callback_query:
        await update.callback_query.answer()
        await target_chat.send_message(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    elif update.message:
        await target_chat.send_message(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    return False

# --------------------------- RHINO GAME PANEL ---------------------------
async def show_game_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور اصلی برای نمایش پنل بازی‌ها به ادمین."""
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == 'private':
        return await update.message.reply_text("این دستور فقط در گروه‌ها کار می‌کند.")

    if not await is_group_admin(user.id, chat.id, context):
        return await update.message.reply_text("❌ این دستور مخصوص ادمین‌های گروه است.")
    
    keyboard = [
        [InlineKeyboardButton("🎮 نمایش لیست بازی‌ها", callback_data="rhino_panel_show_games")],
        [InlineKeyboardButton("👤 پشتیبانی", url=f"https.t.me/{SUPPORT_USERNAME}")]
    ]
    await update.message.reply_text("به پنل مدیریت بازی راینو خوش آمدید.", reply_markup=InlineKeyboardMarkup(keyboard))


async def rhino_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت تمام دکمه‌های پنل بازی."""
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    
    if not await is_group_admin(user.id, chat.id, context):
        return await query.answer("❌ فقط ادمین‌ها می‌توانند از این پنل استفاده کنند.", show_alert=True)

    await query.answer()
    data = query.data.split('_')
    action = data[2]

    # --- منوی اصلی و لیست بازی‌ها ---
    if action == "show": # rhino_panel_show_games
        keyboard = [
            [InlineKeyboardButton("🃏 حکم", callback_data="rhino_panel_hokm"), InlineKeyboardButton("⭕️ دوز", callback_data="rhino_panel_dooz")],
            [InlineKeyboardButton("🕵️‍♂️ حدس کلمه", callback_data="rhino_panel_hads_kalame"), InlineKeyboardButton("🔢 حدس عدد", callback_data="rhino_panel_hads_addad")],
            [InlineKeyboardButton("⌨️ تایپ سرعتی", callback_data="rhino_panel_type_speed"), InlineKeyboardButton("🤫 اعتراف", callback_data="rhino_panel_eteraf")],
            [InlineKeyboardButton("🍄 قارچ", callback_data="rhino_panel_gharch")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="rhino_panel_back_to_main")]
        ]
        await query.edit_message_text("یک بازی را برای شروع انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "back": # rhino_panel_back_to_main
        keyboard = [
            [InlineKeyboardButton("🎮 نمایش لیست بازی‌ها", callback_data="rhino_panel_show_games")],
            [InlineKeyboardButton("👤 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")]
        ]
        await query.edit_message_text("به پنل مدیریت بازی راینو خوش آمدید.", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # --- منطق بازی‌ها ---
    elif action == "hokm":
        keyboard = [
            [InlineKeyboardButton("😎 ۲ نفره", callback_data="rhino_panel_hokm_start_2p"), InlineKeyboardButton("👨‍👩‍👧‍👦 ۴ نفره", callback_data="rhino_panel_hokm_start_4p")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="rhino_panel_show_games")]
        ]
        await query.edit_message_text("حالت بازی حکم را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif action == "hokm_start":
        mode = data[3]
        max_players = 4 if mode == '4p' else 2
        
        text = (
            f" بازی حکم **{max_players} نفره** توسط {user.mention_html()} شروع شد.\n\n"
            f"برای پیوستن، ابتدا در کانال {FORCED_JOIN_CHANNEL} عضو شوید و سپس روی دکمه زیر کلیک کنید."
        )

        if chat.id not in active_games['hokm']: active_games['hokm'][chat.id] = {}
        game_id = query.message.message_id
        active_games['hokm'][chat.id][game_id] = {"status": "joining", "mode": mode, "players": [], "message_id": game_id}
        keyboard = [[InlineKeyboardButton(f"پیوستن به بازی (0/{max_players})", callback_data=f"hokm_join_{game_id}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    elif action == "dooz":
        text = (
            f" بازی دوز توسط {user.mention_html()} شروع شد.\n\n"
            f"نفر دوم برای پیوستن، ابتدا در کانال {FORCED_JOIN_CHANNEL} عضو شوید و سپس روی دکمه زیر کلیک کنید."
        )
        keyboard = [[InlineKeyboardButton("⚔️ پیوستن به بازی", callback_data=f"rhino_panel_dooz_join_{user.id}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

    elif action == "dooz_join": # این منطق قدیمی است و فقط برای پنل اولیه استفاده می‌شود
        challenger_id = int(data[3])
        if user.id == challenger_id:
            return await query.answer("شما نمی‌توانید به بازی خودتان بپیوندید!", show_alert=True)
        if not await force_join_middleware(update, context): return

        challenger = await context.bot.get_chat(challenger_id)
        
        chat_id = query.message.chat.id
        game_id = query.message.message_id
        if chat_id not in active_games['dooz']: active_games['dooz'][chat_id] = {}

        active_games['dooz'][chat_id][game_id] = {
            "players": {challenger_id: "❌", user.id: "⭕️"},
            "board": [[" "]*3 for _ in range(3)],
            "turn": challenger_id
        }
        text = f"بازی شروع شد!\n{challenger.mention_html()} (❌) vs {user.mention_html()} (⭕️)\n\nنوبت {challenger.mention_html()} است."
        keyboard = [[InlineKeyboardButton(" ", callback_data=f"dooz_move_{game_id}_{r*3+c}_{challenger_id}_{user.id}") for c in range(3)] for r in range(3)]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif action == "hads_kalame":
        await query.message.delete()
        await hads_kalame_command(query.message, context) 
    
    elif action == "type_speed":
        await query.message.delete()
        await type_command(query.message, context) 
    
    elif action == "hads_addad":
        keyboard = [
            [InlineKeyboardButton("😊 آسان (۱-۱۰۰)", callback_data="rhino_panel_hads_addad_start_1_100")],
            [InlineKeyboardButton("😎 متوسط (۱-۱۰۰۰)", callback_data="rhino_panel_hads_addad_start_1_1000")],
            [InlineKeyboardButton("🥵 سخت (۱-۹۹۹۹)", callback_data="rhino_panel_hads_addad_start_1_9999")],
            [InlineKeyboardButton("⚙️ سفارشی", callback_data="rhino_panel_hads_addad_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="rhino_panel_show_games")]
        ]
        await query.edit_message_text("سطح بازی حدس عدد را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
        
    elif action == "hads_addad_start":
        min_range, max_range = int(data[3]), int(data[4])
        if chat.id in active_games['guess_number']:
            return await query.edit_message_text("یک بازی حدس عدد در این گروه فعال است.")
        
        secret_number = random.randint(min_range, max_range)
        active_games['guess_number'][chat.id] = {"number": secret_number, "min": min_range, "max": max_range}
        await query.edit_message_text(
            f"🎲 **بازی حدس عدد شروع شد!** 🎲\n\nیک عدد بین **{min_range}** و **{max_range}** انتخاب شده.\n\n"
            "بازیکنان می‌توانند با ارسال عدد در گروه، شانس خود را امتحان کنند.",
            parse_mode=ParseMode.MARKDOWN
        )

    elif action == "hads_addad_custom":
        context.chat_data['waiting_for_input'] = {
            'type': WAITING_FOR_CUSTOM_RANGE,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً بازه بازی را مشخص کنید.\n(مثال: `1-1000`)",
            parse_mode=ParseMode.HTML
        )

    elif action == "eteraf":
        keyboard = [
            [InlineKeyboardButton("📜 متن پیش‌فرض", callback_data="rhino_panel_eteraf_default")],
            [InlineKeyboardButton("✍️ متن سفارشی", callback_data="rhino_panel_eteraf_custom")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="rhino_panel_show_games")]
        ]
        await query.edit_message_text("نوع بازی اعتراف را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif action == "eteraf_default":
        await query.message.delete()
        original_message = query.message
        original_message.text = "/eteraf"
        context.args = []
        await eteraf_command(original_message, context)
        
    elif action == "eteraf_custom":
        context.chat_data['waiting_for_input'] = {
            'type': WAITING_FOR_CUSTOM_ETERAF,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً متن دلخواه خود را برای شروع بازی اعتراف ارسال کنید.",
            parse_mode=ParseMode.HTML
        )

    elif action == "gharch":
        context.chat_data['waiting_for_input'] = {
            'type': WAITING_FOR_GHARCH_GOD,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً گاد بازی را مشخص کنید.\n"
            f"(می‌توانید یوزرنیم، آیدی عددی یا پیام کاربر مورد نظر را منشن/ریپلای کنید)",
            parse_mode=ParseMode.HTML
        )

async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش ورودی‌های متنی ادمین برای حالت‌های سفارشی پنل (rhinogame و rsgame)."""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # چک می‌کنیم که کدام پنل فعال است
    input_key = None
    if 'rsgame_waiting_for_input' in context.chat_data:
        input_key = 'rsgame_waiting_for_input'
    elif 'waiting_for_input' in context.chat_data:
        input_key = 'waiting_for_input'

    if not input_key:
        return

    waiting_info = context.chat_data[input_key]
    if waiting_info['user_id'] != user_id:
        return # ورودی از کاربر دیگری است

    input_type = waiting_info['type']
    message_id_to_edit = waiting_info['message_id']
    
    
    if input_type == WAITING_FOR_CUSTOM_RANGE or input_type == 3: # حدس عدد پنل rhino_panel یا rsgame
        del context.chat_data[input_key]
        try:
            min_str, max_str = convert_persian_to_english_numbers(update.message.text).split('-')
            min_range, max_range = int(min_str.strip()), int(max_str.strip())
            if min_range >= max_range: raise ValueError
            
            await update.message.delete()
            if chat_id in active_games['guess_number']:
                return await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id_to_edit, text="یک بازی حدس عدد در این گروه فعال است.")

            secret_number = random.randint(min_range, max_range)
            active_games['guess_number'][chat_id] = {"number": secret_number, "min": min_range, "max": max_range}
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id_to_edit,
                text=f"🎲 **بازی حدس عدد شروع شد!** 🎲\n\nیک عدد بین **{min_range}** و **{max_range}** انتخاب شده.",
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception:
            await update.message.delete()
            await context.bot.edit_message_text(
                chat_id=chat_id, message_id=message_id_to_edit,
                text="فرمت اشتباه است. بازی لغو شد. لطفاً دوباره از پنل تلاش کنید.",
            )

    elif input_type == WAITING_FOR_CUSTOM_ETERAF or input_type == 4: # اعتراف سفارشی پنل rhino_panel
        custom_text = update.message.text
        del context.chat_data[input_key]
        await update.message.delete()
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_edit)
        
        original_message = update.message
        original_message.text = f"/eteraf {custom_text}"
        context.args = custom_text.split()
        await eteraf_command(original_message, context)

    elif input_type == WAITING_FOR_GHARCH_GOD or input_type == 5: # قارچ پنل rhino_panel
        del context.chat_data[input_key]
        await update.message.delete()
        
        # برای بازی قارچ، پیام اصلی را برای فرآیند مکالمه جدید ارسال می‌کنیم
        if 'gharch_setup_message_id' in context.chat_data:
            del context.chat_data['gharch_setup_message_id']
            
        # شبیه سازی یک پیام با /gharch برای ورود به مکالمه
        original_message = update.message
        original_message.text = "/gharch " + update.message.text
        context.args = update.message.text.split()
        context.chat_data['starter_admin_id'] = user_id
        
        # برای ادامه مکالمه قارچ، ورودی کاربر را در context.user_data برای تابع receive_god_username ذخیره می‌کنیم
        context.chat_data['god_username_input'] = update.message.text
        await receive_god_username_from_panel(update, context)
        return
        
    # --- منطق جدید برای پنل RSGAME ---
    elif input_type == RS_PANEL_WAITING_FOR_ETERAF_TEXT or input_type == 6: # اعتراف سفارشی پنل rsgame
        custom_text = update.message.text
        del context.chat_data[input_key]
        await update.message.delete()
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id_to_edit)
        
        original_message = update.message
        original_message.text = f"/eteraf {custom_text}"
        context.args = custom_text.split()
        await eteraf_command(original_message, context)
        
    elif input_type == RS_PANEL_WAITING_FOR_GHARCH_GOD or input_type == 7: # قارچ پنل rsgame
        del context.chat_data[input_key]
        await update.message.delete()
        
        # پیام اصلی پنل را به عنوان پیام مکالمه در نظر می‌گیریم
        context.chat_data['gharch_setup_message_id'] = message_id_to_edit
        
        # برای ادامه مکالمه قارچ، ورودی کاربر را به تابع کمکی ارسال می‌کنیم
        await receive_god_username_from_panel(update, context)
        return

# --------------------------- GAME: HOKM ---------------------------
def create_deck():
    suits = ['S', 'H', 'D', 'C'] 
    ranks = list(range(2, 15)) 
    deck = [f"{s}{r}" for s in suits for r in ranks]
    random.shuffle(deck)
    return deck

def card_to_persian(card):
    """کارت را به فرمت فارسی با ایموجی تبدیل می‌کند."""
    if not card: return "🃏"
    suits = {'S': '♠️', 'H': '♥️', 'D': '♦️', 'C': '♣️'}
    ranks = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
    suit, rank = card[0], int(card[1:])
    # نمایش رنک کارت یا حرف معادل آن
    rank_display = str(ranks.get(rank, rank))
    return f"{suits[suit]} {rank_display}"

def get_card_value(card, hokm_suit, trick_suit):
    """ارزش عددی یک کارت را برای مقایسه و تعیین برنده دست محاسبه می‌کند."""
    suit, rank = card[0], int(card[1:])
    value = rank
    if suit == hokm_suit:
        value += 200  # کارت‌های حکم بالاترین ارزش را دارند
    elif suit == trick_suit:
        value += 100  # کارت‌های خال زمین ارزش بیشتری از سایر خال‌ها دارند
    return value

# --- تابع اصلی برای ساخت رابط کاربری (صفحه بازی) ---
async def render_hokm_board(game: dict, context: ContextTypes.DEFAULT_TYPE):
    """
    این تابع صفحه بازی (متن و دکمه‌ها) را بر اساس وضعیت فعلی بازی برای همه تولید می‌کند.
    """
    game_id = game['message_id']
    keyboard = []
    
    # --- بخش نمایش بازیکنان و کارت‌های روی میز ---
    if game['mode'] == '4p':
        p_names = [p['name'] for p in game['players']]
        p_ids = [p['id'] for p in game['players']]
        team_a_text = f"🔴 تیم 1: {p_names[0]} و {p_names[2]}"
        team_b_text = f"🔵 تیم 2: {p_names[1]} و {p_names[3]}"
        
        # استفاده از دیکشنری برای نگهداری کارت‌ها تا هر کارت دقیقاً جلوی بازیکن خودش قرار گیرد
        table_cards_map = {pid: "➖" for pid in p_ids}
        for play in game.get('current_trick', []):
            table_cards_map[play['player_id']] = card_to_persian(play['card'])

        table_cards = [table_cards_map[pid] for pid in p_ids]

        board_layout = [
            [InlineKeyboardButton(team_a_text, callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(team_b_text, callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton("بازیکن", callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton("کارت بازی شده", callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(p_names[0], callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards[0], callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(p_names[1], callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards[1], callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(p_names[2], callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards[2], callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(p_names[3], callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards[3], callback_data=f"hokm_noop_{game_id}")],
        ]
        keyboard.extend(board_layout)
    else: # حالت دو نفره
        p_names = [p['name'] for p in game['players']]
        p_ids = [p['id'] for p in game['players']]

        table_cards_map = {p_ids[0]: "➖", p_ids[1]: "➖"}
        for play in game.get('current_trick', []):
            table_cards_map[play['player_id']] = card_to_persian(play['card'])

        board_layout = [
            [InlineKeyboardButton(f"{p_names[0]}", callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards_map[p_ids[0]], callback_data=f"hokm_noop_{game_id}")],
            [InlineKeyboardButton(f"{p_names[1]}", callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(table_cards_map[p_ids[1]], callback_data=f"hokm_noop_{game_id}")],
        ]
        keyboard.extend(board_layout)

    # --- بخش نمایش وضعیت و امتیازات ---
    hokm_suit_fa = card_to_persian(f"{game['hokm_suit']}2")[0] if game.get('hokm_suit') else '❓'
    hakem_name = game.get('hakem_name', '...')
    
    if game['mode'] == '4p':
        trick_score_text = f"دست: 🔴 {game['trick_scores']['A']} - {game['trick_scores']['B']} 🔵"
        game_score_text = f"امتیاز کل: 🔴 {game['game_scores']['A']} - {game['game_scores']['B']} 🔵"
    else:
        p_ids = [p['id'] for p in game['players']]
        trick_score_text = f"دست: {p_names[0]} {game['trick_scores'][p_ids[0]]} - {game['trick_scores'][p_ids[1]]} {p_names[1]}"
        game_score_text = f"امتیاز کل: {p_names[0]} {game['game_scores'][p_ids[0]]} - {game['game_scores'][p_ids[1]]} {p_names[1]}"

    keyboard.append([InlineKeyboardButton(f"حاکم: {hakem_name}", callback_data=f"hokm_noop_{game_id}"), InlineKeyboardButton(f"حکم: {hokm_suit_fa}", callback_data=f"hokm_noop_{game_id}")])
    keyboard.append([InlineKeyboardButton(trick_score_text, callback_data=f"hokm_noop_{game_id}")])
    keyboard.append([InlineKeyboardButton(game_score_text, callback_data=f"hokm_noop_{game_id}")])

    # --- بخش دکمه‌های کنترلی ---
    keyboard.append([InlineKeyboardButton("🃏 نمایش دست من (خصوصی)", callback_data=f"hokm_showhand_{game_id}")])

    if game['status'] == 'hakem_choosing':
        suit_map = {'♠️': 'S', '♥️': 'H', '♦️': 'D', '♣️': 'C'}
        choose_buttons = [InlineKeyboardButton(emoji, callback_data=f"hokm_choose_{game_id}_{char}") for emoji, char in suit_map.items()]
        keyboard.append(choose_buttons)
    elif game['status'] == 'playing':
        current_turn_player_id = game['players'][game['turn_index']]['id']
        if current_turn_player_id in game['hands']:
            player_hand = sorted(game['hands'][current_turn_player_id])
            card_buttons = [InlineKeyboardButton(str(i + 1), callback_data=f"hokm_play_{game_id}_{i}") for i in range(len(player_hand))]
            for i in range(0, len(card_buttons), 7):
                keyboard.append(card_buttons[i:i+7])
    
    return InlineKeyboardMarkup(keyboard)

# --- تابع مدیریت دستور اولیه بازی (بدون تغییر) ---
async def hokm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور اولیه برای شروع بازی و انتخاب حالت ۲ یا ۴ نفره."""
    if not await pre_command_check(update, context): return
    if update.effective_chat.type == 'private':
        await update.message.reply_text("بازی حکم فقط در گروه‌ها قابل اجراست.")
        return

    keyboard = [
        [
            InlineKeyboardButton("😎 ۲ نفره", callback_data="hokm_start_2p"),
            InlineKeyboardButton("👨‍👩‍👧‍👦 ۴ نفره", callback_data="hokm_start_4p")
        ]
    ]
    await update.message.reply_text("حالت بازی حکم را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- تابع اصلی برای مدیریت تمام تعاملات بازی ---
async def hokm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat.id
    
    # چک بن کاربر
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM banned_users WHERE user_id = %s;", (user.id,))
            if cur.fetchone(): return
        conn.close()
    
    data = query.data.split('_'); action = data[1]

    if action == "start":
        await query.answer(); mode = data[2]; max_players = 4 if mode == '4p' else 2
        
        text = (
            f" بازی حکم **{max_players} نفره** شروع شد.\n\n"
            f"برای پیوستن، ابتدا در کانال {FORCED_JOIN_CHANNEL} عضو شوید و سپس روی دکمه زیر کلیک کنید."
        )
        msg = await query.edit_message_text(text, parse_mode=ParseMode.HTML)

        if chat_id not in active_games['hokm']: active_games['hokm'][chat_id] = {}
        game_id = msg.message_id
        active_games['hokm'][chat_id][game_id] = {"status": "joining", "mode": mode, "players": [], "message_id": game_id}
        keyboard = [[InlineKeyboardButton(f"پیوستن به بازی (0/{max_players})", callback_data=f"hokm_join_{game_id}")]]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard)); return

    game_id = int(data[2])
    if chat_id not in active_games['hokm'] or game_id not in active_games['hokm'][chat_id]:
        await query.answer("این بازی دیگر فعال نیست.", show_alert=True)
        try: await query.edit_message_text("این بازی تمام شده است.")
        except: pass
        return
    
    game = active_games['hokm'][chat_id][game_id]

    if action == "join":
        if any(p['id'] == user.id for p in game['players']): return await query.answer("شما قبلاً به بازی پیوسته‌اید!", show_alert=True)
        max_players = 4 if game['mode'] == '4p' else 2
        if len(game['players']) >= max_players: return await query.answer("ظرفیت بازی تکمیل است.", show_alert=True)
        
        # --- اعمال چک اجباری عضویت با آلرت ---
        if not await is_owner(user.id):
            try:
                member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
                if member.status not in ['member', 'administrator', 'creator']:
                    keyboard = [[InlineKeyboardButton(" عضویت در کانال ", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")]]
                    return await query.answer("⚠️ برای پیوستن به بازی، ابتدا باید در کانال عضو شوی.", reply_markup=InlineKeyboardMarkup(keyboard), show_alert=True)
            except Exception:
                pass
        # ------------------------------------

        await query.answer("به بازی پیوستید!")
        game['players'].append({'id': user.id, 'name': user.first_name})
        num_players = len(game['players'])
        
        player_names = "، ".join([p['name'] for p in game['players']])

        if num_players < max_players:
            keyboard = [[InlineKeyboardButton(f"پیوستن به بازی ({num_players}/{max_players})", callback_data=f"hokm_join_{game_id}")]]
            
            text = (
                f" بازی حکم **{max_players} نفره** \n"
                f"بازیکنان فعلی: {player_names}\n\n"
                f"برای پیوستن، ابتدا در کانال {FORCED_JOIN_CHANNEL} عضو شوید و سپس روی دکمه کلیک کنید."
            )
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            p_ids = [p['id'] for p in game['players']]
            game.update({
                "status": "dealing_first_5", "deck": create_deck(), "hands": {pid: [] for pid in p_ids},
                "hakem_id": None, "hakem_name": None, "turn_index": 0, "hokm_suit": None, "current_trick": [],
                "trick_scores": {'A': 0, 'B': 0} if game['mode'] == '4p' else {p_ids[0]: 0, p_ids[1]: 0},
                "game_scores": game.get('game_scores', {'A': 0, 'B': 0} if game['mode'] == '4p' else {p_ids[0]: 0, p_ids[1]: 0})
            })

            for _ in range(5):
                for p in game['players']: game['hands'][p['id']].append(game['deck'].pop(0))
            
            hakem_p = next((p for p in game['players'] if 'S14' in game['hands'][p['id']]), game['players'][0])
            game.update({"hakem_id": hakem_p['id'], "hakem_name": hakem_p['name'], "status": 'hakem_choosing'})
            
            reply_markup = await render_hokm_board(game, context)
            await query.edit_message_text(f"بازیکنان کامل شدند!\nحاکم: **{game['hakem_name']}**\n\nحاکم عزیز، بر اساس ۵ کارت اول خود، حکم را انتخاب کنید.", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    elif action == "choose":
        if user.id != game.get('hakem_id'): return await query.answer("شما حاکم نیستید!", show_alert=True)
        await query.answer(); game['hokm_suit'] = data[3]
        for p in game['players']:
            while len(game['hands'][p['id']]) < 13: game['hands'][p['id']].append(game['deck'].pop(0))
        game['status'] = 'playing'
        game['turn_index'] = next(i for i, p in enumerate(game['players']) if p['id'] == game['hakem_id'])
        turn_player_name = game['players'][game['turn_index']]['name']
        reply_markup = await render_hokm_board(game, context)
        await query.edit_message_text(f"بازی شروع شد! حکم: **{card_to_persian(game['hokm_suit']+'2')[0]}**\n\nنوبت **{turn_player_name}** است.", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    elif action == "showhand":
        if not any(p['id'] == user.id for p in game['players']): return await query.answer("شما بازیکن این مسابقه نیستید!", show_alert=True)
        hand = sorted(game['hands'].get(user.id, []))
        hand_str = "\n".join([f"{i+1}. {card_to_persian(c)}" for i, c in enumerate(hand)]) or "شما کارتی در دست ندارید."
        await query.answer(f"دست شما:\n{hand_str}", show_alert=True)

    elif action == "play":
        if user.id != game['players'][game['turn_index']]['id']: return await query.answer("نوبت شما نیست!", show_alert=True)
        card_index = int(data[3])
        hand = sorted(game['hands'][user.id]) 
        if not (0 <= card_index < len(hand)): return await query.answer("شماره کارت نامعتبر است.", show_alert=True)
        
        card_played = hand[card_index]
        if game['current_trick']:
            trick_suit = game['current_trick'][0]['card'][0]
            if any(c.startswith(trick_suit) for c in hand) and not card_played.startswith(trick_suit):
                return await query.answer(f"شما باید از خال زمین ({card_to_persian(trick_suit+'2')[0]}) بازی کنید!", show_alert=True)

        await query.answer(); game['hands'][user.id].remove(card_played)
        game['current_trick'].append({'player_id': user.id, 'card': card_played})

        num_players = len(game['players'])
        if len(game['current_trick']) == num_players:
            trick_suit = game['current_trick'][0]['card'][0]
            winner_play = max(game['current_trick'], key=lambda p: get_card_value(p['card'], game['hokm_suit'], trick_suit))
            winner_id = winner_play['player_id']
            winner_name = next(p['name'] for p in game['players'] if p['id'] == winner_id)
            
            if game['mode'] == '4p':
                winner_team = 'A' if winner_id in [game['players'][0]['id'], game['players'][2]['id']] else 'B'
                game['trick_scores'][winner_team] += 1
                round_over = game['trick_scores']['A'] == 7 or game['trick_scores']['B'] == 7
            else: # 2p
                game['trick_scores'][winner_id] += 1
                round_over = any(score == 7 for score in game['trick_scores'].values())

            game['turn_index'] = next(i for i, p in enumerate(game['players']) if p['id'] == winner_id)
            
            trick_cards_for_display = game['current_trick'][:]
            game['current_trick'] = []
            
            if round_over:
                if game['mode'] == '4p':
                    winning_team_name = 'A' if game['trick_scores']['A'] == 7 else 'B'
                    game['game_scores'][winning_team_name] += 1
                    winner_display_name = f"تیم {winning_team_name}"
                    game_over = game['game_scores'][winning_team_name] == 7
                else: # 2p
                    round_winner_id = next(pid for pid, score in game['trick_scores'].items() if score == 7)
                    winner_display_name = next(p['name'] for p in game['players'] if p['id'] == round_winner_id)
                    game['game_scores'][round_winner_id] += 1
                    game_over = game['game_scores'][round_winner_id] == 7

                if game_over:
                    await query.edit_message_text(f"🏆 **بازی تمام شد!** 🏆\n\nبرنده نهایی: **{winner_display_name}**", parse_mode=ParseMode.MARKDOWN)
                    del active_games['hokm'][chat_id][game_id]; return
                
                current_hakem_index = next(i for i, p in enumerate(game['players']) if p['id'] == game['hakem_id'])
                if game['mode'] == '4p':
                    hakem_team = 'A' if game['hakem_id'] in [game['players'][0]['id'], game['players'][2]['id']] else 'B'
                    next_hakem_index = current_hakem_index if winning_team_name == hakem_team else (current_hakem_index + 1) % 4
                else: # 2p
                    round_winner_id = next(pid for pid, score in game['trick_scores'].items() if score == 7)
                    next_hakem_index = current_hakem_index if round_winner_id == game['hakem_id'] else (current_hakem_index + 1) % 2
                
                p_ids = [p['id'] for p in game['players']]
                game.update({ "status": "dealing_first_5", "deck": create_deck(), "hands": {pid: [] for pid in p_ids},
                              "trick_scores": {'A': 0, 'B': 0} if game['mode'] == '4p' else {p_ids[0]: 0, p_ids[1]: 0} })
                for _ in range(5):
                    for p in game['players']: game['hands'][p['id']].append(game['deck'].pop(0))
                game['hakem_id'] = game['players'][next_hakem_index]['id']
                game['hakem_name'] = game['players'][next_hakem_index]['name']
                game['status'] = 'hakem_choosing'

                reply_markup = await render_hokm_board(game, context)
                await query.edit_message_text(f"دست تمام شد! برنده: **{winner_display_name}**\n\nحاکم جدید: **{game['hakem_name']}**\nمنتظر انتخاب حکم...", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
            else:
                turn_player_name = game['players'][game['turn_index']]['name']
                
                temp_game_state = game.copy()
                temp_game_state['current_trick'] = trick_cards_for_display
                temp_reply_markup = await render_hokm_board(temp_game_state, context)
                await query.edit_message_text(f"برنده این دست: **{winner_name}**\n\nنوبت **{turn_player_name}** است.", reply_markup=temp_reply_markup, parse_mode=ParseMode.MARKDOWN)
                
                await asyncio.sleep(2.5) 
                
                reply_markup = await render_hokm_board(game, context)
                await query.edit_message_text(f"حکم: **{card_to_persian(game['hokm_suit']+'2')[0]}**\n\nنوبت **{turn_player_name}** است.", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
        else:
            game['turn_index'] = (game['turn_index'] + 1) % num_players
            turn_player_name = game['players'][game['turn_index']]['name']
            reply_markup = await render_hokm_board(game, context)
            await query.edit_message_text(f"حکم: **{card_to_persian(game['hokm_suit']+'2')[0]}**\n\nنوبت **{turn_player_name}** است.", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            
    elif action == "noop":
        await query.answer()

# --------------------------- GAME: GUESS THE NUMBER (ConversationHandler) ---------------------------
async def hads_addad_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat, user = update.effective_chat, update.effective_user
    if chat.type == 'private':
        await update.message.reply_text("این بازی فقط در گروه قابل اجراست.")
        return ConversationHandler.END

    if not await is_group_admin(user.id, chat.id, context):
        await update.message.reply_text("❌ این بازی فقط توسط ادمین‌های گروه قابل شروع است.")
        return ConversationHandler.END
    if chat.id in active_games['guess_number']:
        await update.message.reply_text("یک بازی حدس عدد در این گروه فعال است.")
        return ConversationHandler.END
    await update.message.reply_text("بازه بازی را مشخص کنید. (مثال: `1-1000`)", parse_mode=ParseMode.MARKDOWN)
    return SELECTING_RANGE

async def receive_range(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.effective_chat
    try:
        min_str, max_str = convert_persian_to_english_numbers(update.message.text).split('-')
        min_range, max_range = int(min_str.strip()), int(max_str.strip())
        if min_range >= max_range: raise ValueError
    except:
        await update.message.reply_text("فرمت اشتباه است. لطفا به این صورت وارد کنید: `عدد کوچک-عدد بزرگ`", parse_mode=ParseMode.MARKDOWN)
        return SELECTING_RANGE
        
    secret_number = random.randint(min_range, max_range)
    active_games['guess_number'][chat.id] = {"number": secret_number}
    await update.message.reply_text(f"🎲 **بازی حدس عدد شروع شد!** 🎲\n\nیک عدد بین **{min_range}** و **{max_range}** انتخاب شده.", parse_mode=ParseMode.MARKDOWN)
    
    # پایان ConversationHandler و انتقال کنترل به MessageHandler عمومی
    return ConversationHandler.END


async def handle_guess_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت حدس‌ها برای بازی‌های حدس عدد فعال (پیام‌های معمولی)."""
    chat_id = update.effective_chat.id
    if chat_id not in active_games['guess_number']: return 
    
    game_data = active_games['guess_number'][chat_id]
    
    try:
        guess = int(convert_persian_to_english_numbers(update.message.text))
    except (ValueError, TypeError):
        return 

    secret_number = game_data['number']
    user = update.effective_user
    
    if guess < secret_number:
        await update.message.reply_text("بالاتر ⬆️")
    elif guess > secret_number:
        await update.message.reply_text("پایین‌تر ⬇️")
    else:
        await update.message.reply_text(f"🎉 **تبریک!** {user.mention_html()} برنده شد! 🎉\n\nعدد صحیح **{secret_number}** بود.", parse_mode=ParseMode.HTML)
        del active_games['guess_number'][chat_id]


async def cancel_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_chat.id in active_games['guess_number']: del active_games['guess_number'][update.effective_chat.id]
    await update.message.reply_text('بازی حدس عدد لغو شد.')
    return ConversationHandler.END

# --------------------------- GAME: DOOZ (TIC-TAC-TOE) ---------------------------
async def dooz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await pre_command_check(update, context): return
    if update.effective_chat.type == 'private':
        await update.message.reply_text("این بازی فقط در گروه‌ها قابل اجراست.")
        return
        
    challenger = update.effective_user
    challenged_user = None

    if update.message.reply_to_message:
        challenged_user = update.message.reply_to_message.from_user
        if challenged_user.is_bot or challenged_user.id == challenger.id:
            await update.message.reply_text("❌ دعوت نامعتبر: نمی‌توانید ربات یا خودتان را دعوت کنید.")
            return

    if challenged_user or (context.args and context.args[0].startswith('@')):
        if challenged_user:
            challenged_mention = challenged_user.mention_html()
            cb_info = challenged_user.username if challenged_user.username else str(challenged_user.id)
        else:
            cb_info = context.args[0][1:]
            challenged_mention = f"کاربر @{cb_info}"

        text = f"{challenger.mention_html()} {challenged_mention} را به بازی دوز دعوت کرد!"
        keyboard = [[
            InlineKeyboardButton("✅ قبول", callback_data=f"dooz_accept_{challenger.id}_{cb_info}"),
            InlineKeyboardButton("❌ رد", callback_data=f"dooz_decline_{challenger.id}_{cb_info}")
        ]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    else:
        chat_id = update.effective_chat.id
        if chat_id not in active_games['dooz']: active_games['dooz'][chat_id] = {}
        if any(g.get("status") == "joining_public" for g in active_games['dooz'][chat_id].values()):
             return await update.message.reply_text("یک بازی دوز عمومی در حال انتظار است.")

        text = (
            f"⭕️ **بازی دوز عمومی** توسط {challenger.mention_html()} آغاز شد.\n\n"
            "برای پیوستن به عنوان بازیکن دوم (❌)، روی دکمه زیر کلیک کنید."
        )
        msg = await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        game_id = msg.message_id
        
        active_games['dooz'][chat_id][game_id] = {
            "status": "joining_public", 
            "p1_id": challenger.id,
            "p1_name": challenger.first_name,
            "message_id": game_id
        }
        
        keyboard = [[InlineKeyboardButton("⚔️ پیوستن به بازی (❌)", callback_data=f"dooz_join_public_{game_id}")]]
        await msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

async def dooz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM banned_users WHERE user_id = %s;", (user.id,))
            if cur.fetchone(): return
        conn.close()

    await query.answer()
    
    data = query.data.split('_')
    action = data[1]

    if action == "join_public": # پیوستن به بازی دوز عمومی
        game_id = int(data[2])
        chat_id = query.message.chat.id
        
        if chat_id not in active_games.get('dooz', {}) or game_id not in active_games['dooz'][chat_id] or active_games['dooz'][chat_id][game_id].get("status") != "joining_public":
            return await query.answer("این بازی دوز دیگر فعال نیست یا شروع شده است.", show_alert=True)
            
        game = active_games['dooz'][chat_id][game_id]
        p1_id = game['p1_id']
        
        if user.id == p1_id:
            return await query.answer("شما نمی‌توانید به بازی خودتان بپیوندید!", show_alert=True)
        
        # --- چک اجباری عضویت (با آلرت) ---
        if not await is_owner(user.id):
            try:
                 member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
                 if member.status not in ['member', 'administrator', 'creator']:
                     keyboard = [[InlineKeyboardButton(" عضویت در کانال ", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")]]
                     return await query.answer("⚠️ برای پیوستن به بازی، ابتدا باید در کانال عضو شوی.", reply_markup=InlineKeyboardMarkup(keyboard), show_alert=True)
            except Exception:
                 pass
        # ----------------------------------
        
        await query.answer("به بازی پیوستید! بازی شروع شد.")
        
        p1_mention = f"[{game['p1_name']}](tg://user?id={p1_id})"
        
        game.update({
            "players": {p1_id: "❌", user.id: "⭕️"},
            "board": [[" "]*3 for _ in range(3)],
            "turn": p1_id,
            "status": "playing"
        })
        
        text = f"بازی شروع شد!\n{p1_mention} (❌) vs {user.mention_html()} (⭕️)\n\nنوبت {p1_mention} است."
        
        keyboard = [[
            InlineKeyboardButton(" ", callback_data=f"dooz_move_{game_id}_{r*3+c}_{p1_id}_{user.id}")  
            for c in range(3)] for r in range(3)
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    elif action in ["accept", "decline"]:
        p1_id, p2_info = int(data[2]), data[3]
        is_correct_user = (user.username and user.username.lower() == p2_info.lower()) or (str(user.id) == p2_info)
        
        if not is_correct_user:
            return await query.answer("این دعوت برای شما نیست!", show_alert=True)
        if user.id == p1_id and action == "accept":
            return await query.answer("شما نمی‌توانید دعوت خودتان را قبول کنید!", show_alert=True)
        
        try:
            p1_user = await context.bot.get_chat(p1_id)
            p1_mention = p1_user.mention_html()
        except:
            p1_mention = f"کاربر {p1_id}"

        if action == "accept":
            # --- چک اجباری عضویت (با آلرت) ---
            if not await is_owner(user.id):
                try:
                     member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
                     if member.status not in ['member', 'administrator', 'creator']:
                         keyboard = [[InlineKeyboardButton(" عضویت در کانال ", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")]]
                         return await query.answer("⚠️ برای پیوستن به بازی، ابتدا باید در کانال عضو شوی.", reply_markup=InlineKeyboardMarkup(keyboard), show_alert=True)
                except Exception:
                     pass
            # ----------------------------------

            chat_id = query.message.chat.id
            game_id = query.message.message_id

            if chat_id not in active_games['dooz']:
                active_games['dooz'][chat_id] = {}

            active_games['dooz'][chat_id][game_id] = {
                "players": {p1_id: "❌", user.id: "⭕️"},
                "board": [[" "]*3 for _ in range(3)],
                "turn": p1_id
            }

            text = f"بازی شروع شد!\n{p1_mention} (❌) vs {user.mention_html()} (⭕️)\n\nنوبت {p1_mention} است."
            
            keyboard = [[
                InlineKeyboardButton(" ", callback_data=f"dooz_move_{game_id}_{r*3+c}_{p1_id}_{user.id}")  
                for c in range(3)] for r in range(3)
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(f"{user.mention_html()} دعوت {p1_mention} را رد کرد.", parse_mode=ParseMode.HTML)

    elif action == "move":
        chat_id = query.message.chat.id
        game_id = int(data[2])
        p1_id = int(data[4])
        p2_id = int(data[5])

        if chat_id not in active_games['dooz'] or game_id not in active_games['dooz'][chat_id]:
            await query.answer("این بازی تمام شده است.", show_alert=True)
            return
        
        game = active_games['dooz'][chat_id][game_id]
        if user.id not in [p1_id, p2_id]:
            await query.answer("شما بازیکن این مسابقه نیستید!", show_alert=True)
            return
        if user.id != game['turn']:
            await query.answer("نوبت شما نیست!", show_alert=True)
            return

        cell_index = int(data[3])
        row, col = divmod(cell_index, 3)
        if game['board'][row][col] != " ":
            await query.answer("این خانه پر شده است!", show_alert=True)
            return
        
        symbol = game['players'][user.id]
        game['board'][row][col] = symbol
        
        b = game['board']
        win = any(all(c==symbol for c in r) for r in b) or \
              any(all(b[r][c]==symbol for r in range(3)) for c in range(3)) or \
              all(b[i][i]==symbol for i in range(3)) or \
              all(b[i][2-i]==symbol for i in range(3))
        
        is_draw = all(c!=" " for r in b for c in r) and not win
        winner = user.id if win else "draw" if is_draw else None
        
        game['turn'] = p2_id if user.id == p1_id else p1_id
        
        board_rows = []
        for r in range(3):
            row_buttons = []
            for c in range(3):
                row_buttons.append(InlineKeyboardButton(b[r][c], callback_data=f"dooz_move_{game_id}_{r*3+c}_{p1_id}_{p2_id}"))
            board_rows.append(row_buttons)

        if winner:
            text = "بازی مساوی شد!" if winner == "draw" else f"بازی تمام شد! برنده: {user.mention_html()} 🏆"
            del active_games['dooz'][chat_id][game_id]
            if not active_games['dooz'][chat_id]:
                del active_games['dooz'][chat_id]
        else:
            try:
                p_turn_user = await context.bot.get_chat(game['turn'])
                text = f"نوبت {p_turn_user.mention_html()} است."
            except:
                text = f"نوبت بازیکن بعدی است."
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(board_rows), parse_mode=ParseMode.HTML)

# --------------------------- GAME: HADS KALAME ---------------------------
async def hads_kalame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    if chat_id in active_games['hangman']: return await update.reply_text("یک بازی حدس کلمه فعال است.")
    
    word = random.choice(WORD_LIST)
    active_games['hangman'][chat_id] = {"word": word, "display": ["_"] * len(word), "guessed_letters": set(), "players": {}}
    game = active_games['hangman'][chat_id]
    text = f"🕵️‍♂️ **حدس کلمه (رقابتی) شروع شد!**\n\nهر کاربر {INITIAL_LIVES} جان دارد.\nکلمه: `{' '.join(game['display'])}`"
    await context.bot.send_message(chat_id, text, parse_mode=ParseMode.MARKDOWN)

async def handle_letter_guess(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id, user = update.effective_chat.id, update.effective_user
    if chat_id not in active_games['hangman']: return
    # حذف چک عضویت اجباری از این بازی
    # if not await force_join_middleware(update, context): return 

    guess = update.message.text.strip()
    game = active_games['hangman'][chat_id]
    
    if user.id not in game['players']: game['players'][user.id] = INITIAL_LIVES
    if game['players'][user.id] == 0: return await update.message.reply_text(f"{user.mention_html()}، شما تمام جان‌های خود را از دست داده‌اید!", parse_mode=ParseMode.HTML)
    if guess in game['guessed_letters']: return

    game['guessed_letters'].add(guess)
    if guess in game['word']:
        for i, letter in enumerate(game['word']):
            if letter == guess: game['display'][i] = letter
        if "_" not in game['display']:
            await update.message.reply_text(f"✅ **{user.mention_html()}** برنده شد! کلمه صحیح `{game['word']}` بود.", parse_mode=ParseMode.HTML)
            del active_games['hangman'][chat_id]
        else:
            await update.message.reply_text(f"`{' '.join(game['display'])}`", parse_mode=ParseMode.MARKDOWN)
    else:
        game['players'][user.id] -= 1
        lives_left = game['players'][user.id]
        if lives_left > 0:
            await update.message.reply_text(f"اشتباه بود {user.mention_html()}! شما **{lives_left}** جان دیگر دارید.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"{user.mention_html()} تمام جان‌های خود را از دست داد و از بازی حذف شد.", parse_mode=ParseMode.HTML)
            if all(lives == 0 for lives in game['players'].values() if lives is not None):
                await update.message.reply_text(f"☠️ همه باختید! کلمه صحیح `{game['word']}` بود.", parse_mode=ParseMode.MARKDOWN)
                del active_games['hangman'][chat_id]

# --------------------------- GAME: GHARCH & ETERAF ---------------------------
async def gharch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند بازی قارچ و ورود به حالت مکالمه."""
    if not await pre_command_check(update, context): return ConversationHandler.END
    if update.effective_chat.type == 'private':
        await update.message.reply_text("این بازی فقط در گروه‌ها قابل اجراست.")
        return ConversationHandler.END
        
    if not await is_group_admin(update.effective_user.id, update.effective_chat.id, context):
        await update.message.reply_text("❌ فقط ادمین‌های گروه می‌توانند این بازی را شروع کنند.")
        return ConversationHandler.END
    
    context.chat_data['starter_admin_id'] = update.effective_user.id
    
    sent_message = await update.message.reply_text(
        "🍄 **شروع بازی قارچ**\n\n"
        "لطفاً یوزرنیم گاد بازی را ارسال کنید."
    )
    context.chat_data['gharch_setup_message_id'] = sent_message.message_id
    
    return ASKING_GOD_USERNAME

async def receive_god_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت یوزرنیم گاد، حذف پیام و ویرایش پیام اولیه."""
    god_username = update.message.text.strip()
    
    # اگر ورودی یک یوزرنیم ساده نبود، می‌توانیم از منطق پیچیده receive_god_username_from_panel استفاده کنیم
    if not god_username.startswith('@'):
        # برای سادگی، فعلاً فقط یوزرنیم با @ را می‌پذیریم
        await update.message.reply_text("فرمت اشتباه است. لطفاً یوزرنیم را با @ ارسال کنید.", quote=True)
        return ASKING_GOD_USERNAME 
        
    context.chat_data['god_username'] = god_username
    setup_message_id = context.chat_data.get('gharch_setup_message_id')

    try:
        await update.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete admin's username message: {e}")

    if not setup_message_id:
        await context.bot.send_message(update.effective_chat.id, "خطایی در یافتن پیام اصلی رخ داد. لطفاً بازی را با /cancel لغو و مجدداً شروع کنید.")
        return ConversationHandler.END

    keyboard = [[
        InlineKeyboardButton("✅ تایید می‌کنم", callback_data=f"gharch_confirm_god_{god_username.lstrip('@')}")
    ]]
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=setup_message_id,
        text=(
            f"{god_username} عزیز،\n"
            f"شما به عنوان گاد بازی قارچ انتخاب شدید. لطفاً برای شروع بازی، این مسئولیت را تایید کنید.\n\n"
            f"⚠️ **نکته:** برای دریافت گزارش‌ها، باید ربات را استارت کرده باشید."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return CONFIRMING_GOD

async def confirm_god(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """گاد بازی را تایید کرده و بازی رسماً شروع می‌شود. (نسخه مقاوم در برابر خطای پین)"""
    query = update.callback_query
    user = query.from_user
    chat_id = query.message.chat.id
    
    # شناسه تایید از کال‌بک دیتا (می‌تواند آیدی عددی یا یوزرنیم بدون @ باشد)
    data = query.data.split('_')
    cb_data_identifier = data[3]
    
    # چک می‌کند که کاربر کلیک کننده همان گاد باشد
    is_correct_user = False
    if cb_data_identifier.isdigit() and user.id == int(cb_data_identifier):
         is_correct_user = True
    elif user.username and user.username.lower() == cb_data_identifier.lower():
         is_correct_user = True

    if not is_correct_user:
        await query.answer("این درخواست برای شما نیست.", show_alert=True)
        return ConversationHandler.END

    await query.answer("شما به عنوان گاد تایید شدید!")

    try:
        god_id = user.id
        god_username_display = f"@{user.username}" if user.username else user.mention_html()
        active_gharch_games[chat_id] = {'god_id': god_id, 'god_username': god_username_display}

        bot_username = (await context.bot.get_me()).username
        game_message_text = (
            f"**بازی قارچ 🍄 شروع شد!**\n\n"
            f"روی دکمه زیر کلیک کن و حرف دلت رو بنویس تا به صورت ناشناس در گروه ظاهر بشه!\n\n"
            f"*(فقط گاد بازی، {god_username_display}، از هویت ارسال‌کننده مطلع خواهد شد.)*"
        )
        keyboard = [[InlineKeyboardButton("🍄 ارسال پیام ناشناس", url=f"https://t.me/{bot_username}?start=gharch_{chat_id}")]]
        
        await query.edit_message_text(
            text=game_message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            await context.bot.pin_chat_message(chat_id, query.message.message_id)
            active_gharch_games[chat_id]['pinned_message_id'] = query.message.message_id
        except Exception as pin_error:
            logger.warning(f"Could not pin message in group {chat_id}. Reason: {pin_error}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ بازی با موفقیت شروع شد. ادمین‌های عزیز، لطفاً این پیام را پین کنید.",
                reply_to_message_id=query.message.message_id
            )

    except Exception as e:
        error_message = f"🚫 **خطای ناشناخته!**\n\nربات در ساخت بازی با یک خطای غیرمنتظره مواجه شد: `{e}`"
        await context.bot.send_message(chat_id=chat_id, text=error_message, parse_mode=ParseMode.MARKDOWN)
        logger.error(f"CRITICAL ERROR in confirm_god: {e}")
        return ConversationHandler.END

    return ConversationHandler.END

async def cancel_gharch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو فرآیند ساخت بازی قارچ."""
    await update.message.reply_text("فرآیند ساخت بازی قارچ لغو شد.")
    return ConversationHandler.END

async def eteraf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private':
        await update.message.reply_text("این دستور فقط در گروه‌ها قابل استفاده است.")
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    if not await is_group_admin(user.id, chat_id, context):
        await update.message.reply_text("❌ شما اجازه استفاده از این دستور را ندارید. این دستور مخصوص مدیران گروه است.")
        return

    if not await force_join_middleware(update, context): 
        return

    custom_text = " ".join(context.args)
    
    if custom_text:
        starter_text = custom_text
    else:
        starter_text = "یک موضوع اعتراف جدید شروع شد. برای ارسال اعتراف ناشناس (که به این پیام ریپلای می‌شود)، از دکمه زیر استفاده کنید."

    bot_username = (await context.bot.get_me()).username
    
    try:
        starter_message = await update.message.reply_text(starter_text)
        keyboard = [[InlineKeyboardButton("🤫 ارسال اعتراف", url=f"https://t.me/{bot_username}?start=eteraf_{chat_id}_{starter_message.message_id}")]]
        await starter_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in eteraf_command: {e}")
        await update.message.reply_text(f"خطایی در ارسال پیام رخ داد: {e}")


async def handle_anonymous_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if 'anon_target_chat' not in user_data:
        return await update.message.reply_text("لطفاً ابتدا از طریق دکمه‌ای که در گروه قرار دارد، فرآیند را شروع کنید.")
    
    target_info = user_data['anon_target_chat']
    target_chat_id = target_info['id']
    game_type = target_info['type']
    message_text = update.message.text

    try:
        if game_type == "gharch":
            if target_chat_id in active_gharch_games:
                sender = update.effective_user
                god_info = active_gharch_games[target_chat_id]
                god_id = god_info['god_id']

                await context.bot.send_message(
                    chat_id=target_chat_id,
                    text=f"#پیام_ناشناس 🍄\n\n{message_text}"
                )
                await update.message.reply_text("✅ پیام شما با موفقیت به صورت ناشناس در گروه ارسال شد.")

                report_text = (
                    f"📝 **گزارش پیام ناشناس جدید**\n\n"
                    f"👤 **ارسال کننده:**\n"
                    f"- نام: {sender.mention_html()}\n"
                    f"- یوزرنیم: @{sender.username}\n"
                    f"- آیدی: `{sender.id}`\n\n"
                    f"📜 **متن پیام:**\n"
                    f"{message_text}"
                )
                await context.bot.send_message(chat_id=god_id, text=report_text, parse_mode=ParseMode.HTML)
            else:
                await update.message.reply_text("این بازی قارچ دیگر فعال نیست یا منقضی شده است.")

        elif game_type == "eteraf":
            reply_to_id = target_info.get('reply_to')
            header = "#اعتراف_ناشناس 🤫"
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=f"{header}\n\n{message_text}",
                reply_to_message_id=reply_to_id
            )
            await update.message.reply_text("✅ اعتراف شما با موفقیت به صورت ناشناس در گروه ارسال شد.")
            
        else:
            await update.message.reply_text("نوع بازی ناشناس مشخص نیست.")

    except Exception as e:
        await update.message.reply_text(f"⚠️ ارسال پیام با خطا مواجه شد: {e}")
        logger.error(f"Error in handle_anonymous_message for game {game_type}: {e}")
    finally:
        if 'anon_target_chat' in context.user_data:
            del context.user_data['anon_target_chat']

# --------------------------- GAME: TYPE SPEED --------------------------
def create_typing_image(text: str) -> io.BytesIO:
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped_text)
    try:
        font = ImageFont.truetype("Vazir.ttf", 24)
    except IOError:
        logger.warning("Vazir.ttf font not found. Falling back to default.")
        font = ImageFont.load_default()
    
    dummy_img, draw = Image.new('RGB', (1, 1)), ImageDraw.Draw(Image.new('RGB', (1, 1)))
    _, _, w, h = draw.textbbox((0, 0), bidi_text, font=font)
    
    img = Image.new('RGB', (w + 40, h + 40), color=(255, 255, 255))
    ImageDraw.Draw(img).text((20, 20), bidi_text, fill=(0, 0, 0), font=font)
    
    bio = io.BytesIO()
    bio.name = 'image.jpeg'
    img.save(bio, 'JPEG')
    bio.seek(0)
    return bio

async def type_command(update: Update, context: ContextTypes.DEFAULT_TYPE): 
    chat_id = update.chat.id
    if chat_id in active_games['typing']: return await update.reply_text("یک بازی تایپ سرعتی فعال است.")
    
    sentence = random.choice(TYPING_SENTENCES)
    active_games['typing'][chat_id] = {"sentence": sentence, "start_time": datetime.now()}
    
    await context.bot.send_message(chat_id, "بازی تایپ سرعتی ۳... ۲... ۱...")
    
    image_file = create_typing_image(sentence)
    await context.bot.send_photo(chat_id, photo=image_file, caption="سریع تایپ کنید!")

async def handle_typing_attempt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_games['typing']: return
    # حذف چک عضویت اجباری از این بازی
    # if not await force_join_middleware(update, context): return 
    
    game = active_games['typing'][chat_id]
    
    user_input = update.message.text.strip()
    
    if user_input == game['sentence']:
        duration = (datetime.now() - game['start_time']).total_seconds()
        user = update.effective_user
        await update.message.reply_text(f"🏆 {user.mention_html()} برنده شد!\nزمان: **{duration:.2f}** ثانیه", parse_mode=ParseMode.HTML)
        del active_games['typing'][chat_id]

# --------------------------- RSGAME PANEL HANDLERS ---------------------------
async def rsgame_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کامند /rsgame برای نمایش پنل داینامیک."""
    user = update.effective_user
    chat = update.effective_chat
    if chat.type == 'private':
        return await update.message.reply_text("این دستور فقط در گروه‌ها کار می‌کند.")
    
    # --- مرحله ۱: چک عضویت ---
    if await is_owner(user.id):
        await show_rsgame_panel(update, context, is_callback=False, check_ok=True)
        return
        
    try:
        member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
        is_member = member.status in ['member', 'administrator', 'creator']
    except Exception:
        is_member = True 
        logger.warning(f"Could not check channel membership for {user.id}. Assuming member.")

    if is_member:
        await show_rsgame_panel(update, context, is_callback=False, check_ok=True)
    else:
        keyboard = [
            [InlineKeyboardButton(" عضویت در کانال ", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton("✅ عضو شدم (بررسی)", callback_data=f"rsgame_check_join_{user.id}")]
        ]
        text = f"❗️ {user.mention_html()} عزیز، برای استفاده از بازی‌ها ابتدا باید در کانال ما عضو شوی."
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)


async def show_rsgame_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool, check_ok: bool = False):
    """نمایش لیست بازی‌ها پس از تأیید عضویت یا مستقیماً."""
    user = update.effective_user
    chat = update.effective_chat
    
    if is_callback and not check_ok:
        try:
            member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                return await update.callback_query.answer("⚠️ هنوز عضو کانال نشده‌اید! لطفا ابتدا عضو شوید.", show_alert=True)
        except Exception:
            pass

    keyboard = [
        [InlineKeyboardButton("🃏 حکم (۲ نفره)", callback_data="rsgame_start_hokm_2p"), InlineKeyboardButton("🃏 حکم (۴ نفره)", callback_data="rsgame_start_hokm_4p")],
        [InlineKeyboardButton("🔢 حدس عدد", callback_data="rsgame_hads_addad"), InlineKeyboardButton("🕵️‍♂️ حدس کلمه", callback_data="rsgame_hads_kalame")],
        [InlineKeyboardButton("⌨️ تایپ سرعتی", callback_data="rsgame_type_speed"), InlineKeyboardButton("⭕️ دوز", callback_data="rsgame_dooz_public")],
        [InlineKeyboardButton("🤫 اعتراف (پیشفرض)", callback_data="rsgame_eteraf_default"), InlineKeyboardButton("✍️ اعتراف (سفارشی)", callback_data="rsgame_eteraf_custom")],
        [InlineKeyboardButton("🍄 قارچ", callback_data="rsgame_gharch")],
        [InlineKeyboardButton("👤 پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}"), InlineKeyboardButton("❌ بستن پنل", callback_data="rsgame_close")]
    ]
    
    text = f"**{user.first_name} عزیز، لیست بازی‌های گروه:**"
    
    if is_callback:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
    else:
        await context.bot.send_message(chat.id, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


async def rsgame_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دکمه‌های پنل /rsgame."""
    query = update.callback_query
    user = query.from_user
    chat = query.message.chat
    data = query.data.split('_')
    action = data[1]
    
    await query.answer()

    if action == "check":
        if str(user.id) != data[3]:
            return await query.answer("این دکمه برای شما نیست.", show_alert=True)
        await show_rsgame_panel(update, context, is_callback=True, check_ok=False)
        return
        
    elif action == "close":
        await query.message.delete()
        return

    # --- چک مجدد عضویت برای دکمه‌های بازی (آلرت) ---
    if not await is_owner(user.id):
        try:
            member = await context.bot.get_chat_member(chat_id=FORCED_JOIN_CHANNEL, user_id=user.id)
            if member.status not in ['member', 'administrator', 'creator']:
                keyboard = [[InlineKeyboardButton(" عضویت در کانال ", url=f"https://t.me/{FORCED_JOIN_CHANNEL.lstrip('@')}")]]
                return await query.answer("❌ برای شروع بازی باید عضو کانال باشی.", reply_markup=InlineKeyboardMarkup(keyboard), show_alert=True)
        except:
            pass

    # 1. حکم (مستقیم به انتظار)
    if action == "start" and data[2] == "hokm":
        mode = data[3]
        max_players = 4 if mode == '4p' else 2
        
        text = (
            f" بازی حکم **{max_players} نفره** توسط {user.mention_html()} شروع شد.\n\n"
            f"برای پیوستن، ابتدا در کانال {FORCED_JOIN_CHANNEL} عضو شوید و سپس روی دکمه زیر کلیک کنید."
        )
        game_id = query.message.message_id
        if chat.id not in active_games['hokm']: active_games['hokm'][chat.id] = {}
        active_games['hokm'][chat.id][game_id] = {"status": "joining", "mode": mode, "players": [], "message_id": game_id}
        keyboard = [[InlineKeyboardButton(f"پیوستن به بازی (0/{max_players})", callback_data=f"hokm_join_{game_id}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        
    # 2. حدس عدد (مستقیم به دریافت بازه)
    elif action == "hads_addad":
        context.chat_data['rsgame_waiting_for_input'] = {
            'type': WAITING_FOR_CUSTOM_RANGE,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً بازه بازی را مشخص کنید.\n(مثال: `1-1000`)",
            parse_mode=ParseMode.HTML
        )
    
    # 3. حدس کلمه (مستقیم به شروع بازی - حذف پنل)
    elif action == "hads_kalame":
        if chat.id in active_games['hangman']:
            return await query.edit_message_text("یک بازی حدس کلمه فعال است.")
        
        await query.message.delete()
        await hads_kalame_command(query.message, context)
        
    # 4. تایپ سرعتی (مستقیم به شروع بازی - حذف پنل)
    elif action == "type_speed":
        if chat.id in active_games['typing']:
            return await query.edit_message_text("یک بازی تایپ سرعتی فعال است.")
            
        await query.message.delete()
        await type_command(query.message, context)

    # 5. دوز (مستقیم به انتظار بازیکن عمومی)
    elif action == "dooz_public":
        chat_id = chat.id
        if chat_id not in active_games['dooz']: active_games['dooz'][chat_id] = {}
        if any(g.get("status") == "joining_public" for g in active_games['dooz'][chat_id].values()):
             return await query.edit_message_text("یک بازی دوز عمومی در حال انتظار است.")

        text = (
            f"⭕️ **بازی دوز عمومی** توسط {user.mention_html()} آغاز شد.\n\n"
            "برای پیوستن به عنوان بازیکن دوم (❌)، روی دکمه زیر کلیک کنید."
        )
        
        await query.edit_message_text(text, parse_mode=ParseMode.HTML)
        game_id = query.message.message_id
        
        active_games['dooz'][chat_id][game_id] = {
            "status": "joining_public", 
            "p1_id": user.id,
            "p1_name": user.first_name,
            "message_id": game_id
        }
        
        keyboard = [[InlineKeyboardButton("⚔️ پیوستن به بازی (❌)", callback_data=f"dooz_join_public_{game_id}")]]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
        
    # 6. اعتراف پیشفرض (حذف پنل و شروع)
    elif action == "eteraf_default":
        await query.message.delete()
        original_message = query.message
        original_message.text = "/eteraf"
        context.args = []
        await eteraf_command(original_message, context)

    # 7. اعتراف سفارشی (دریافت متن)
    elif action == "eteraf_custom":
        context.chat_data['rsgame_waiting_for_input'] = {
            'type': RS_PANEL_WAITING_FOR_ETERAF_TEXT,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً متن دلخواه خود را برای شروع بازی اعتراف ارسال کنید.",
            parse_mode=ParseMode.HTML
        )

    # 8. قارچ (دریافت گاد)
    elif action == "gharch":
        context.chat_data['rsgame_waiting_for_input'] = {
            'type': RS_PANEL_WAITING_FOR_GHARCH_GOD,
            'user_id': user.id,
            'message_id': query.message.message_id
        }
        await query.edit_message_text(
            f"{user.mention_html()} عزیز، لطفاً گاد بازی را مشخص کنید.\n"
            f"(می‌توانید یوزرنیم، آیدی عددی یا پیام کاربر مورد نظر را منشن/ریپلای کنید)",
            parse_mode=ParseMode.HTML
        )


async def receive_god_username_from_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت گاد با یوزرنیم، آیدی یا منشن (ورودی از پنل)."""
    god_info = None
    message = update.message
    text_input = message.text

    if message.entities and message.entities[0].type == MessageEntity.TEXT_MENTION:
        user_entity = message.entities[0].user
        god_info = {'id': user_entity.id, 'mention': user_entity.mention_html()}
    elif message.reply_to_message:
        user_reply = message.reply_to_message.from_user
        god_info = {'id': user_reply.id, 'mention': user_reply.mention_html()}
    elif text_input.isdigit():
        try:
            user_id = int(text_input)
            user_chat = await context.bot.get_chat(user_id)
            god_info = {'id': user_id, 'mention': user_chat.mention_html()}
        except Exception:
            await context.bot.edit_message_text(chat_id=message.chat.id, message_id=context.chat_data.get('gharch_setup_message_id'), text="آیدی عددی یافت نشد. بازی قارچ لغو شد.")
            return ConversationHandler.END
    elif text_input.startswith('@'):
        god_info = {'id': None, 'username': text_input, 'mention': text_input}
    else:
        await context.bot.edit_message_text(chat_id=message.chat.id, message_id=context.chat_data.get('gharch_setup_message_id'), text="فرمت ورودی نامعتبر است. بازی قارچ لغو شد.")
        return ConversationHandler.END
    
    context.chat_data['god_info'] = god_info
    setup_message_id = context.chat_data.get('gharch_setup_message_id')

    # اگر یوزرنیم در god_info موجود بود، برای تایید باید از آن استفاده شود
    cb_data_identifier = god_info.get('id', god_info.get('username').lstrip('@'))
    
    keyboard = [[InlineKeyboardButton("✅ تایید می‌کنم", callback_data=f"gharch_confirm_god_{cb_data_identifier}")]]
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=setup_message_id,
        text=(
            f"{god_info['mention']} عزیز،\n"
            f"شما به عنوان گاد بازی قارچ انتخاب شدید. لطفاً برای شروع بازی، این مسئولیت را تایید کنید.\n\n"
            f"⚠️ **نکته:** برای دریافت گزارش‌ها، باید ربات را استارت کرده باشید."
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )
    
    return CONFIRMING_GOD

# --------------------------- CORE & OWNER COMMANDS ---------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    if context.args:
        try:
            payload = context.args[0]
            parts = payload.split('_')
            game_type, target_chat_id = parts[0], int(parts[1])

            if game_type == "gharch":
                if target_chat_id in active_gharch_games:
                    god_username = active_gharch_games[target_chat_id]['god_username']
                    context.user_data['anon_target_chat'] = {'id': target_chat_id, 'type': game_type}
                    prompt = f"پیام خود را برای ارسال ناشناس بنویسید...\n\nتوجه: فقط گاد بازی ({god_username}) هویت شما را خواهد دید."
                    await update.message.reply_text(prompt)
                    return
                else:
                    await update.message.reply_text("این بازی قارچ دیگر فعال نیست."); return
            
            elif game_type == "eteraf":
                context.user_data['anon_target_chat'] = {'id': target_chat_id, 'type': game_type}
                if len(parts) > 2:
                    context.user_data['anon_target_chat']['reply_to'] = int(parts[2])
                prompt = "اعتراف خود را بنویسید تا به صورت ناشناس در grupo ارسال شود..."
                await update.message.reply_text(prompt)
                return

        except (ValueError, IndexError):
            pass 

    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur: 
            cur.execute("INSERT INTO users (user_id, first_name, username) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING;", (user.id, user.first_name, user.username))
            conn.commit()
    
    if not await force_join_middleware(update, context):
        if conn: conn.close()
        return

    keyboard = [
        [InlineKeyboardButton("➕ افزودن ربات به گروه", url=f"https://t.me/{(await context.bot.get_me()).username}?startgroup=true")],
        [InlineKeyboardButton("👤 ارتباط با پشتیبان", url=f"https://t.me/{SUPPORT_USERNAME}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    custom_welcome_sent = False
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT message_id, chat_id FROM start_message WHERE id = 1;")
                start_msg_data = cur.fetchone()
                if start_msg_data:
                    message_id, from_chat_id = start_msg_data
                    await context.bot.copy_message(chat_id=chat_id, from_chat_id=from_chat_id, message_id=message_id, reply_markup=reply_markup)
                    custom_welcome_sent = True
        except Exception as e:
            logger.error(f"Could not send custom start message in PV: {e}")
        finally:
            conn.close()

    if not custom_welcome_sent:
        await update.message.reply_text("سلام به راینوبازی خوش آمدید.", reply_markup=reply_markup)
    
    report_text = f"✅ کاربر جدید: {user.mention_html()} (ID: `{user.id}`)"
    for owner_id in OWNER_IDS:
        try:
            await context.bot.send_message(chat_id=owner_id, text=report_text, parse_mode=ParseMode.HTML)
        except:
            pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join_middleware(update, context): return
    help_text = "راهنمای ربات 🎮\n\n/hokm - بازی حکم\n/dooz @user - بازی دوز\n/hads_kalame - حدس کلمه\n/hads_addad - حدس عدد\n/type - تایپ سرعتی\n/gharch - پیام ناشناس\n/eteraf - اعتراف ناشناس"
    await update.message.reply_text(help_text)

async def set_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    if not update.message.reply_to_message: return await update.message.reply_text("روی یک پیام ریپلای کنید.")
    msg = update.message.reply_to_message
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur: cur.execute("INSERT INTO start_message (id, message_id, chat_id) VALUES (1, %s, %s) ON CONFLICT (id) DO UPDATE SET message_id = EXCLUDED.message_id, chat_id = EXCLUDED.chat_id;", (msg.message_id, msg.chat_id)); conn.commit()
        conn.close()
        await update.message.reply_text("✅ پیام خوشامدگویی تنظیم شد.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    conn = get_db_connection()
    if conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;"); user_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM groups;"); group_count = cur.fetchone()[0]
            cur.execute("SELECT SUM(member_count) FROM groups;"); total_members = cur.fetchone()[0] or 0
        stats = f"📊 **آمار ربات**\n\n👤 کاربران: {user_count}\n👥 گروه‌ها: {group_count}\n👨‍👩‍👧‍👦 مجموع اعضا: {total_members}"
        await update.message.reply_text(stats, parse_mode=ParseMode.MARKDOWN)
        conn.close()
        
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str):
    if not await is_owner(update.effective_user.id): return
    if not update.message.reply_to_message: return await update.message.reply_text("روی یک پیام ریپلای کنید.")
    conn, table, column = get_db_connection(), "users" if target == "users" else "groups", "user_id" if target == "users" else "group_id"
    if not conn: return
    with conn.cursor() as cur: cur.execute(f"SELECT {column} FROM {table};"); targets = cur.fetchall()
    conn.close()
    if not targets: return await update.message.reply_text("هدفی یافت نشد.")
    
    sent, failed = 0, 0
    status_msg = await update.message.reply_text(f"⏳ در حال ارسال به {len(targets)} {target}...")
    for (target_id,) in targets:
        try:
            await context.bot.forward_message(chat_id=target_id, from_chat_id=update.message.reply_to_message.chat.id, message_id=update.message.reply_to_message.message_id)
            sent += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed for {target_id}: {e}")
    await status_msg.edit_text(f"🏁 ارسال تمام شد.\n\n✅ موفق: {sent}\n❌ ناموفق: {failed}")

async def fwdusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await broadcast_command(update, context, "users")
async def fwdgroups_command(update: Update, context: ContextTypes.DEFAULT_TYPE): await broadcast_command(update, context, "groups")

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("استفاده: /ban_user <user_id>")
    try:
        user_id = int(context.args[0])
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur: cur.execute("INSERT INTO banned_users (user_id) VALUES (%s) ON CONFLICT DO NOTHING;", (user_id,))
            conn.commit(); conn.close()
            await update.message.reply_text(f"کاربر `{user_id}` با موفقیت مسدود شد.", parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text("آیدی نامعتبر است.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("استفاده: /unban_user <user_id>")
    try:
        user_id = int(context.args[0])
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur: cur.execute("DELETE FROM banned_users WHERE user_id = %s;", (user_id,))
            conn.commit(); conn.close()
            await update.message.reply_text(f"کاربر `{user_id}` با موفقیت از مسدودیت خارج شد.", parse_mode=ParseMode.MARKDOWN)
    except: await update.message.reply_text("آیدی نامعتبر است.")

async def ban_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("استفاده صحیح: /ban_group <group_id>")
    
    try:
        group_id = int(context.args[0])
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO banned_groups (group_id) VALUES (%s) ON CONFLICT DO NOTHING;", (group_id,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"گروه `{group_id}` با موفقیت مسدود شد.", parse_mode=ParseMode.MARKDOWN)
            
            try:
                await context.bot.leave_chat(group_id)
            except Exception as e:
                logger.warning(f"Could not leave the banned group {group_id}: {e}")

    except (ValueError, IndexError):
        await update.message.reply_text("لطفا یک آیدی عددی معتبر برای گروه وارد کنید.")

async def unban_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id): return
    if not context.args: return await update.message.reply_text("استفاده صحیح: /unban_group <group_id>")

    try:
        group_id = int(context.args[0])
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM banned_groups WHERE group_id = %s;", (group_id,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"گروه `{group_id}` با موفقیت از مسدودیت خارج شد.", parse_mode=ParseMode.MARKDOWN)
    except (ValueError, IndexError):
        await update.message.reply_text("لطفا یک آیدی عددی معتبر برای گروه وارد کنید.")

async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = update.chat_member
    if not result: return

    chat = result.chat
    user = result.from_user
    
    if result.new_chat_member.user.id != context.bot.id:
        return

    if result.new_chat_member.status == 'member' and result.old_chat_member.status != 'member':
        conn = get_db_connection()
        if not conn: return
        
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM groups;")
                group_count = cur.fetchone()[0]
            
            if group_count >= GROUP_INSTALL_LIMIT:
                await chat.send_message(f"⚠️ ظرفیت نصب این ربات تکمیل شده است! لطفاً با پشتیبانی (@{SUPPORT_USERNAME}) تماس بگیرید.")
                await context.bot.leave_chat(chat.id)
                for owner_id in OWNER_IDS:
                    await context.bot.send_message(owner_id, f"🔔 هشدار: سقف نصب ({GROUP_INSTALL_LIMIT}) تکمیل شد. ربات از گروه `{chat.title}` خارج شد.", parse_mode=ParseMode.MARKDOWN)
                conn.close()
                return
        except Exception as e:
            logger.error(f"Could not check group install limit: {e}")

        member_count = await chat.get_member_count()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO groups (group_id, title, member_count) VALUES (%s, %s, %s) ON CONFLICT (group_id) DO UPDATE SET title = EXCLUDED.title, member_count = EXCLUDED.member_count;", (chat.id, chat.title, member_count))
            conn.commit()

        custom_welcome_sent = False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT message_id, chat_id FROM start_message WHERE id = 1;")
                start_msg_data = cur.fetchone()
                if start_msg_data:
                    message_id, from_chat_id = start_msg_data
                    await context.bot.copy_message(chat_id=chat.id, from_chat_id=from_chat_id, message_id=message_id)
                    custom_welcome_sent = True
        except Exception as e:
            logger.error(f"Could not send custom start message: {e}")

        if not custom_welcome_sent:
            await chat.send_message("سلام! 👋 من با موفقیت نصب شدم.\nبرای مشاهده لیست بازی‌ها از دستور /help استفاده کنید.")
        
        conn.close()
        
        report = f"➕ **ربات به گروه جدید اضافه شد:**\n\n🌐 نام: {chat.title}\n🆔: `{chat.id}`\n👥 اعضا: {member_count}\n\n👤 توسط: {user.mention_html()} (ID: `{user.id}`)"
        for owner_id in OWNER_IDS:
            try: await context.bot.send_message(owner_id, report, parse_mode=ParseMode.HTML)
            except: pass

    elif result.new_chat_member.status == 'left':
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM groups WHERE group_id = %s;", (chat.id,))
                cur.execute("DELETE FROM banned_groups WHERE group_id = %s;", (chat.id,)) # پاک کردن از لیست بن در صورت خروج
                conn.commit()
            conn.close()
        report = f"❌ **ربات از گروه زیر اخراج شد:**\n\n🌐 نام: {chat.title}\n🆔: `{chat.id}`"
        for owner_id in OWNER_IDS:
            try: await context.bot.send_message(owner_id, report, parse_mode=ParseMode.MARKDOWN)
            except: pass
            
# ======================== MAIN FUNCTION (ساختار نهایی) ==========================
def main() -> None:
    setup_database()
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        logger.critical("BOT_TOKEN environment variable not set.")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    
    # --- Conversation Handlers ---
    gharch_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gharch", gharch_command)],
        states={
            ASKING_GOD_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_god_username)],
            CONFIRMING_GOD: [CallbackQueryHandler(confirm_god, pattern=r'^gharch_confirm_god_')],
        },
        fallbacks=[CommandHandler('cancel', cancel_gharch)],
        per_user=False, per_chat=True,
    )
    application.add_handler(gharch_conv_handler)
    
    guess_number_conv = ConversationHandler(
        entry_points=[CommandHandler("hads_addad", hads_addad_command)],
        states={
            SELECTING_RANGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_range)],
            # بعد از دریافت محدوده، ConversationHandler پایان می‌یابد و هندلر عمومی کار را ادامه می‌دهد.
            GUESSING: [MessageHandler(filters.Regex(r'^[\d۰-۹]+$'), handle_guess_message)], 
        },
        fallbacks=[CommandHandler('cancel', cancel_game)],
        per_user=False, per_chat=True
    )
    application.add_handler(guess_number_conv)

    # --- Command Handlers ---
    # پنل‌ها
    application.add_handler(CommandHandler("rhinogame", show_game_panel))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(بازی|شروع بازی|game|پنل)$') & filters.ChatType.GROUPS, show_game_panel))
    application.add_handler(CommandHandler("rsgame", rsgame_command))
    
    # دستورات اصلی
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    # دستورات بازی
    application.add_handler(CommandHandler("hokm", hokm_command))
    application.add_handler(CommandHandler("dooz", dooz_command))
    application.add_handler(CommandHandler("hads_kalame", hads_kalame_command))
    application.add_handler(CommandHandler("type", type_command))
    application.add_handler(CommandHandler("eteraf", eteraf_command))

    # دستورات مالک
    application.add_handler(CommandHandler("setstart", set_start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("fwdusers", fwdusers_command))
    application.add_handler(CommandHandler("fwdgroups", fwdgroups_command))
    application.add_handler(CommandHandler("ban_user", ban_user_command))
    application.add_handler(CommandHandler("unban_user", unban_user_command))
    application.add_handler(CommandHandler("ban_group", ban_group_command))
    application.add_handler(CommandHandler("unban_group", unban_group_command))

    # --- CallbackQuery Handlers ---
    application.add_handler(CallbackQueryHandler(rhino_panel_callback, pattern=r'^rhino_panel_'))
    application.add_handler(CallbackQueryHandler(rsgame_callback_handler, pattern=r'^rsgame_'))
    application.add_handler(CallbackQueryHandler(hokm_callback, pattern=r'^hokm_'))
    application.add_handler(CallbackQueryHandler(dooz_callback, pattern=r'^dooz_'))

    # --- Message Handlers (با اولویت) ---
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_admin_input), group=1)
    
    # هندلر حدس عدد برای پیام‌های معمولی بعد از شروع بازی (که ConversationHandler را نیز مدیریت می‌کند)
    application.add_handler(MessageHandler(filters.Regex(r'^[\d۰-۹]+$') & filters.ChatType.GROUPS, handle_guess_message), group=2) 
    
    application.add_handler(MessageHandler(filters.Regex(r'^[آ-ی]$') & filters.ChatType.GROUPS, handle_letter_guess), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS, handle_typing_attempt), group=2)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_anonymous_message))
    
    # --- سایر Handler ها ---
    application.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    
    logger.info("Bot is starting with the new Rhino Panel and RSGame Panel...")
    application.run_polling()

if __name__ == "__main__":
    main()
