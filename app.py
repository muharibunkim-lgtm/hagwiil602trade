# app.py  ─────────────────────────────────────────────────────────────────────
# 대항해시대 스타일 세계 무역 & 영토 점령 보드게임 (초등 6학년용)
# Streamlit + SQLite3 단일 파일 구현
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
import sqlite3
import pandas as pd
import random
import io
import threading
from datetime import datetime

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 상수 / 게임 데이터 정의
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DB_PATH = "trade_game.db"
_db_lock = threading.Lock()     # 동시 쓰기 충돌 방지용 락
INITIAL_MONEY = 1_000_000       # 초기 자금 100만 원
SHARE_PRICE   = 50_000          # 주당 5만 원
MAX_SHARES    = 100             # 도시당 최대 주식 수
LORD_MIN_SHARES = 20            # 영주가 되기 위한 최소 주식 수
TARIFF_RATE   = 0.10            # 관세율 10 %
INSURANCE_COST = 10_000         # 무역 보험료 1만 원
PIRATE_LOSS   = 0.30            # 해적 화물 손실 30 %

# 도시 목록
CITIES = ["상하이", "뭄바이", "런던", "카이로", "뉴욕", "상파울루", "시드니", "레이캬비크"]

CITY_INFO = {
    "상하이":   {"region": "🌏 아시아",      "flag": "🇨🇳", "level_up": [500_000, 1_500_000]},
    "뭄바이":   {"region": "🌏 아시아",      "flag": "🇮🇳", "level_up": [500_000, 1_500_000]},
    "런던":     {"region": "🌍 유럽",        "flag": "🇬🇧", "level_up": [600_000, 1_800_000]},
    "카이로":   {"region": "🌍 아프리카",    "flag": "🇪🇬", "level_up": [400_000, 1_200_000]},
    "뉴욕":     {"region": "🌎 북아메리카",  "flag": "🇺🇸", "level_up": [700_000, 2_000_000]},
    "상파울루": {"region": "🌎 남아메리카",  "flag": "🇧🇷", "level_up": [400_000, 1_200_000]},
    "시드니":   {"region": "🌏 오세아니아",  "flag": "🇦🇺", "level_up": [500_000, 1_500_000]},
    "레이캬비크":{"region":"🧊 북극권",      "flag": "🇮🇸", "level_up": [500_000, 1_500_000]},
}

# 무역품 정의: (도시, 상품명, 매수가, 매도가, 해금레벨)
GOODS_DATA = [
    # 상하이
    ("상하이", "비단",         80_000,  120_000, 1),
    ("상하이", "도자기",       60_000,   90_000, 1),
    ("상하이", "첨단섬유",    200_000,  320_000, 2),
    ("상하이", "AI칩",        500_000,  800_000, 3),
    # 뭄바이
    ("뭄바이", "향신료",       50_000,   80_000, 1),
    ("뭄바이", "홍차",         40_000,   65_000, 1),
    ("뭄바이", "보석원석",    150_000,  240_000, 2),
    ("뭄바이", "의약원료",    400_000,  640_000, 3),
    # 런던
    ("런던",   "정밀기계",    200_000,  300_000, 1),
    ("런던",   "위스키",      100_000,  160_000, 1),
    ("런던",   "항공부품",    400_000,  640_000, 2),
    ("런던",   "양자컴퓨터", 900_000, 1_440_000, 3),
    # 카이로
    ("카이로", "면화",         40_000,   65_000, 1),
    ("카이로", "석유",        120_000,  190_000, 1),
    ("카이로", "태양광패널",  250_000,  400_000, 2),
    ("카이로", "희토류",      600_000,  960_000, 3),
    # 뉴욕
    ("뉴욕",   "IT기기",      300_000,  450_000, 1),
    ("뉴욕",   "금융상품",    500_000,  750_000, 1),
    ("뉴욕",   "우주부품",    700_000, 1_100_000, 2),
    ("뉴욕",   "바이오칩",  1_000_000, 1_600_000, 3),
    # 상파울루
    ("상파울루","커피원두",    50_000,   80_000, 1),
    ("상파울루","카카오",      60_000,   95_000, 1),
    ("상파울루","바이오연료", 180_000,  290_000, 2),
    ("상파울루","열대의약품", 450_000,  720_000, 3),
    # 시드니
    ("시드니", "양모",         70_000,  110_000, 1),
    ("시드니", "철광석",      100_000,  160_000, 1),
    ("시드니", "리튬배터리",  300_000,  480_000, 2),
    ("시드니", "핵융합소재",  800_000, 1_280_000, 3),
    # 레이캬비크
    ("레이캬비크","수산물통조림", 40_000, 65_000, 1),
    ("레이캬비크","신재생에너지",150_000, 240_000, 1),
    ("레이캬비크","희귀광물",  350_000,  560_000, 2),
    ("레이캬비크","친환경수소", 700_000, 1_120_000, 3),
]

# 도시 간 거리 등급: 1=근거리(5만), 2=중거리(10만), 3=장거리(20만)
DISTANCE = {
    ("상하이",   "뭄바이"):    2,
    ("상하이",   "런던"):      3,
    ("상하이",   "카이로"):    3,
    ("상하이",   "뉴욕"):      3,
    ("상하이",   "상파울루"):  3,
    ("상하이",   "시드니"):    2,
    ("상하이",   "레이캬비크"):3,
    ("뭄바이",   "런던"):      2,
    ("뭄바이",   "카이로"):    1,
    ("뭄바이",   "뉴욕"):      3,
    ("뭄바이",   "상파울루"):  3,
    ("뭄바이",   "시드니"):    2,
    ("뭄바이",   "레이캬비크"):3,
    ("런던",     "카이로"):    2,
    ("런던",     "뉴욕"):      2,
    ("런던",     "상파울루"):  3,
    ("런던",     "시드니"):    3,
    ("런던",     "레이캬비크"):1,
    ("카이로",   "뉴욕"):      3,
    ("카이로",   "상파울루"):  3,
    ("카이로",   "시드니"):    3,
    ("카이로",   "레이캬비크"):3,
    ("뉴욕",     "상파울루"):  2,
    ("뉴욕",     "시드니"):    3,
    ("뉴욕",     "레이캬비크"):2,
    ("상파울루", "시드니"):    3,
    ("상파울루", "레이캬비크"):3,
    ("시드니",   "레이캬비크"):3,
}
MOVE_COST = {1: 30_000, 2: 50_000, 3: 100_000}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 도시별 상품 판매가 테이블
# 구조: CITY_SELL_PRICES[상품명][판매도시] = 판매가
# 생산도시 = 매수가의 70% (손실), 인근 = 소익, 원거리 수요도시 = 대익
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_sell_prices():
    """
    각 상품의 도시별 판매가 생성
    - 생산 도시:  매수가 × 0.70  (반드시 손해)
    - 일반 도시:  매수가 × 계수  (거리·수요에 따라 다름)
    """
    # (생산도시, 상품명, 매수가, -, -) 목록으로부터 계산
    # 계수 테이블: SELL_RATE[생산도시][판매도시]
    SELL_RATE = {
        "상하이": {
            "상하이":    0.70,   # 생산지 손해
            "뭄바이":    1.00,
            "런던":      1.50,
            "카이로":    1.40,
            "뉴욕":      1.70,
            "상파울루":  1.60,
            "시드니":    1.10,
            "레이캬비크":1.45,
        },
        "뭄바이": {
            "상하이":    1.05,
            "뭄바이":    0.70,   # 생산지
            "런던":      1.60,
            "카이로":    1.10,
            "뉴욕":      1.65,
            "상파울루":  1.55,
            "시드니":    1.15,
            "레이캬비크":1.50,
        },
        "런던": {
            "상하이":    1.45,
            "뭄바이":    1.30,
            "런던":      0.70,   # 생산지
            "카이로":    1.20,
            "뉴욕":      1.10,
            "상파울루":  1.55,
            "시드니":    1.50,
            "레이캬비크":0.95,
        },
        "카이로": {
            "상하이":    1.40,
            "뭄바이":    1.15,
            "런던":      1.30,
            "카이로":    0.70,   # 생산지
            "뉴욕":      1.55,
            "상파울루":  1.45,
            "시드니":    1.35,
            "레이캬비크":1.25,
        },
        "뉴욕": {
            "상하이":    1.65,
            "뭄바이":    1.55,
            "런던":      1.20,
            "카이로":    1.45,
            "뉴욕":      0.70,   # 생산지
            "상파울루":  1.10,
            "시드니":    1.50,
            "레이캬비크":1.40,
        },
        "상파울루": {
            "상하이":    1.55,
            "뭄바이":    1.45,
            "런던":      1.60,
            "카이로":    1.40,
            "뉴욕":      1.15,
            "상파울루":  0.70,   # 생산지
            "시드니":    1.35,
            "레이캬비크":1.50,
        },
        "시드니": {
            "상하이":    1.20,
            "뭄바이":    1.25,
            "런던":      1.55,
            "카이로":    1.45,
            "뉴욕":      1.50,
            "상파울루":  1.40,
            "시드니":    0.70,   # 생산지
            "레이캬비크":1.30,
        },
        "레이캬비크": {
            "상하이":    1.50,
            "뭄바이":    1.45,
            "런던":      0.95,
            "카이로":    1.35,
            "뉴욕":      1.40,
            "상파울루":  1.55,
            "시드니":    1.45,
            "레이캬비크":0.70,   # 생산지
        },
    }

    prices = {}  # prices[상품명][도시] = 판매가
    for (prod_city, good_name, buy_price, _, _) in GOODS_DATA:
        prices[good_name] = {}
        for sell_city in CITIES:
            rate = SELL_RATE.get(prod_city, {}).get(sell_city, 0.70)
            prices[good_name][sell_city] = int(buy_price * rate)
    return prices

# 전역 판매가 테이블 (앱 시작 시 1회 생성)
CITY_SELL_PRICES = build_sell_prices()


def get_sell_price(good_name, sell_city):
    """현재 도시에서 해당 상품의 판매가 조회 (DB 가격 변동 이벤트 반영)"""
    # 태풍/폭등 이벤트 등으로 DB goods 가격이 변경된 경우 배율을 반영
    base_good = fetchone("SELECT buy_price, city FROM goods WHERE name=? LIMIT 1", (good_name,))
    if not base_good:
        return CITY_SELL_PRICES.get(good_name, {}).get(sell_city, 0)

    prod_city = base_good["city"]
    # 원래 매수가 대비 현재 DB 매수가 배율 계산
    original_buy = next(
        (g[2] for g in GOODS_DATA if g[0] == prod_city and g[1] == good_name), None
    )
    if original_buy and original_buy > 0:
        current_buy = fetchone(
            "SELECT buy_price FROM goods WHERE name=? AND city=?", (good_name, prod_city)
        )
        if current_buy:
            event_rate = current_buy["buy_price"] / original_buy
        else:
            event_rate = 1.0
    else:
        event_rate = 1.0

    base_sell = CITY_SELL_PRICES.get(good_name, {}).get(sell_city, 0)
    return int(base_sell * event_rate)

def get_distance(c1, c2):
    """두 도시 간 거리 등급 반환"""
    key = (c1, c2) if (c1, c2) in DISTANCE else (c2, c1)
    return DISTANCE.get(key, 3)

def get_move_cost(c1, c2):
    """두 도시 간 이동 비용 반환"""
    return MOVE_COST[get_distance(c1, c2)]

# 운하 봉쇄 이벤트용 캐시
if "canal_blocked" not in st.session_state:
    st.session_state.canal_blocked = {}   # {(도시1, 도시2): True}
if "fta_cities" not in st.session_state:
    st.session_state.fta_cities = set()   # 관세 0% 도시

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. DB 초기화 / 공통 DB 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_conn():
    """호출할 때마다 새 연결을 생성 (캐시하지 않음)"""
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def run(sql, params=()):
    """쓰기 작업 전용. 매번 새 연결을 열고 반드시 닫는다."""
    with _db_lock:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            conn.commit()
            return cur
        finally:
            conn.close()


def fetchall(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def fetchone(sql, params=()):
    conn = get_conn()
    try:
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()


def init_db():
    conn = get_conn()
    try:
        cur = conn.cursor()

        # ── 테이블 생성 ──────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                student_id    INTEGER PRIMARY KEY,
                password      TEXT    DEFAULT '0000',
                money         INTEGER DEFAULT 1000000,
                location      TEXT    DEFAULT '상하이',
                insurance     INTEGER DEFAULT 0,
                tariff_income INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS cities (
            name         TEXT PRIMARY KEY,
            level        INTEGER DEFAULT 1,
            invest_total INTEGER DEFAULT 0
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS goods (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            city         TEXT,
            name         TEXT,
            buy_price    INTEGER,
            sell_price   INTEGER,
            unlock_level INTEGER DEFAULT 1
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS shares (
            student_id  INTEGER,
            city        TEXT,
            amount      INTEGER DEFAULT 0,
            PRIMARY KEY (student_id, city)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            student_id  INTEGER,
            good_name   TEXT,
            city        TEXT,
            quantity    INTEGER DEFAULT 0,
            avg_price   INTEGER DEFAULT 0,
            PRIMARY KEY (student_id, good_name, city)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        TEXT,
            student_id INTEGER,
            message   TEXT
        )""")

        conn.commit()   # 테이블 생성 커밋

        # ── 여기부터 전부 try 블록 안으로 이동! (conn.close() 이전) ──

        # 학생 1~23 초기 등록
        for sid in range(1, 24):
            cur.execute("INSERT OR IGNORE INTO users (student_id) VALUES (?)", (int(sid),))

        # 도시 초기 등록
        for city in CITIES:
            cur.execute("INSERT OR IGNORE INTO cities (name) VALUES (?)", (city,))

        # 무역품 초기 등록 (이미 있으면 건너뜀)
        exists = cur.execute("SELECT 1 FROM goods LIMIT 1").fetchone()
        if not exists:
            for row in GOODS_DATA:
                cur.execute(
                    "INSERT INTO goods (city, name, buy_price, sell_price, unlock_level) VALUES (?,?,?,?,?)",
                    row
                )

        # 지분 초기화 (student × city)
        for sid in range(1, 24):
            for city in CITIES:
                cur.execute(
                    "INSERT OR IGNORE INTO shares (student_id, city, amount) VALUES (?,?,0)",
                    (int(sid), city)
                )

        conn.commit()   # 초기 데이터 등록까지 최종 커밋

    finally:
        conn.close()   # ✅ 모든 작업이 끝난 뒤, 맨 마지막에 딱 한 번만 실행


def reset_db():
    """게임 데이터 전체 초기화"""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET money=1000000, location='상하이', insurance=0, tariff_income=0, password='0000'")
        cur.execute("UPDATE cities SET level=1, invest_total=0")
        cur.execute("UPDATE shares SET amount=0")
        cur.execute("DELETE FROM inventory")
        cur.execute("DELETE FROM event_log")
        cur.execute("DELETE FROM goods")
        for row in GOODS_DATA:
            cur.execute(
                "INSERT INTO goods (city, name, buy_price, sell_price, unlock_level) VALUES (?,?,?,?,?)",
                row
            )
        conn.commit()
    finally:
        conn.close()

    st.session_state.canal_blocked = {}
    st.session_state.fta_cities = set()
    
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 보조 / 게임 로직 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_user(sid):
    return fetchone("SELECT * FROM users WHERE student_id=?", (sid,))

def get_city(name):
    return fetchone("SELECT * FROM cities WHERE name=?", (name,))

def get_goods(city, level):
    return fetchall(
        "SELECT * FROM goods WHERE city=? AND unlock_level<=? ORDER BY unlock_level",
        (city, level)
    )

def get_shares(sid, city):
    row = fetchone("SELECT amount FROM shares WHERE student_id=? AND city=?", (sid, city))
    return row["amount"] if row else 0

def get_city_shares_all(city):
    return fetchall(
        "SELECT student_id, amount FROM shares WHERE city=? AND amount>0 ORDER BY amount DESC",
        (city,)
    )

def get_lord(city):
    """영주: 최고 지분 >= 20주 학생, 없으면 None"""
    rows = get_city_shares_all(city)
    if rows and rows[0]["amount"] >= LORD_MIN_SHARES:
        return rows[0]["student_id"]
    return None

def get_inventory(sid):
    return fetchall(
        "SELECT * FROM inventory WHERE student_id=? AND quantity>0",
        (sid,)
    )

def add_log(sid, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    run("INSERT INTO event_log (ts, student_id, message) VALUES (?,?,?)", (ts, sid, msg))

def check_city_levelup(city_name):
    """누적 투자금에 따라 도시 레벨업 처리"""
    city = get_city(city_name)
    info = CITY_INFO[city_name]
    lv = city["level"]
    inv = city["invest_total"]
    if lv == 1 and inv >= info["level_up"][0]:
        run("UPDATE cities SET level=2 WHERE name=?", (city_name,))
        add_log(0, f"🎉 [{city_name}] 이 Lv.2 로 레벨업! 새 무역품 해금!")
    elif lv == 2 and inv >= info["level_up"][1]:
        run("UPDATE cities SET level=3 WHERE name=?", (city_name,))
        add_log(0, f"🎉 [{city_name}] 이 Lv.3 으로 레벨업! 최고급 무역품 해금!")

def total_assets(sid):
    """학생 총 자산 = 잔고 + 재고 평가액(현위치 판매가 기준) + 지분 평가액"""
    user = get_user(sid)
    total = user["money"]
    cur_city = user["location"]
    # 재고: 현재 위치에서 팔 수 있는 가격으로 평가
    for inv in get_inventory(sid):
        sell_val = get_sell_price(inv["good_name"], cur_city)
        total += sell_val * inv["quantity"]
    # 지분
    shares_rows = fetchall("SELECT city, amount FROM shares WHERE student_id=?", (sid,))
    for s in shares_rows:
        total += s["amount"] * SHARE_PRICE
    return total

def format_won(n):
    return f"₩{n:,}"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 사이드바 로그인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def sidebar_login():
    st.sidebar.markdown("## 🌊 대항해시대 보드게임")
    st.sidebar.markdown("---")
    role = st.sidebar.radio("로그인 유형", ["👨‍🎓 학생", "👩‍🏫 교사 관리자"])

    if role == "👩‍🏫 교사 관리자":
        pw = st.sidebar.text_input("관리자 비밀번호", type="password", key="admin_pw")
        if st.sidebar.button("로그인", key="admin_login"):
            if pw == "1234":
                st.session_state.logged_in = "admin"
                st.session_state.student_id = None
                st.rerun()
            else:
                st.sidebar.error("비밀번호가 틀렸습니다.")
    else:
        sid = st.sidebar.selectbox("학생 번호 선택", list(range(1, 24)),
                                   format_func=lambda x: f"{x}번 학생", key="sel_sid")
        pw = st.sidebar.text_input("비밀번호 (초기: 0000)", type="password", key="stu_pw")
        if st.sidebar.button("로그인", key="stu_login"):
            db_pw = fetchone("SELECT password FROM users WHERE student_id=?", (sid,))
            if db_pw and db_pw["password"] == pw:
                st.session_state.logged_in = "student"
                st.session_state.student_id = sid
                st.rerun()
            else:
                st.sidebar.error("비밀번호가 틀렸습니다.")

    # 상태 표시
    if st.session_state.get("logged_in") == "student":
        sid = st.session_state.student_id
        user = get_user(sid)
        st.sidebar.success(f"✅ {sid}번 학생 로그인 중")
        st.sidebar.info(
            f"📍 현재 위치: **{user['location']}**\n\n"
            f"💰 잔고: **{format_won(user['money'])}**"
        )
        if st.sidebar.button("🚪 로그아웃"):
            st.session_state.logged_in = None
            st.rerun()

    elif st.session_state.get("logged_in") == "admin":
        st.sidebar.success("✅ 교사 관리자 로그인 중")
        if st.sidebar.button("🚪 로그아웃"):
            st.session_state.logged_in = None
            st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 학생 탭 1: 세계 지도 & 이동
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tab_map(sid):
    user = get_user(sid)
    cur_city = user["location"]
    has_insurance = bool(user["insurance"])

    st.subheader(f"🗺️ 현재 위치: {CITY_INFO[cur_city]['flag']} **{cur_city}** ({CITY_INFO[cur_city]['region']})")
    st.markdown("---")

    # 무역 보험 가입
    col_ins1, col_ins2 = st.columns([3, 1])
    with col_ins1:
        if has_insurance:
            st.success("🛡️ 무역 보험 가입 완료 (해적 출몰 시 화물 100% 보상)")
        else:
            st.warning("⚠️ 무역 보험 미가입 상태 (해적 출몰 시 화물 30% 손실)")
    with col_ins2:
        if not has_insurance:
            if st.button(f"보험 가입 ({format_won(INSURANCE_COST)})", key="buy_ins"):
                if user["money"] < INSURANCE_COST:
                    st.error("잔고가 부족합니다!")
                else:
                    run("UPDATE users SET money=money-?, insurance=1 WHERE student_id=?",
                        (INSURANCE_COST, sid))
                    add_log(sid, "🛡️ 무역 보험 가입")
                    st.success("무역 보험에 가입했습니다!")
                    st.rerun()
        else:
            if st.button("보험 해지", key="cancel_ins"):
                run("UPDATE users SET insurance=0 WHERE student_id=?", (sid,))
                add_log(sid, "보험 해지")
                st.rerun()

    st.markdown("---")
    st.markdown("### 🚢 이동할 도시 선택")

    # 도시를 3열로 배치
    other_cities = [c for c in CITIES if c != cur_city]
    cols = st.columns(3)
    for i, city in enumerate(other_cities):
        base_cost = get_move_cost(cur_city, city)
        # 운하 봉쇄 적용 여부
        key = (cur_city, city) if (cur_city, city) in st.session_state.canal_blocked else (city, cur_city)
        if key in st.session_state.canal_blocked and st.session_state.canal_blocked[key]:
            real_cost = base_cost * 2
            cost_label = f"⛔ 봉쇄 {format_won(real_cost)}"
        else:
            real_cost = base_cost
            dist = get_distance(cur_city, city)
            dist_emoji = ["", "🟢 근거리", "🟡 중거리", "🔴 장거리"][dist]
            cost_label = f"{dist_emoji} {format_won(real_cost)}"

        info = CITY_INFO[city]
        with cols[i % 3]:
            st.markdown(f"**{info['flag']} {city}**")
            st.caption(f"{info['region']} | 이동비용: {cost_label}")
            if st.button(f"✈️ {city}로 이동", key=f"move_{city}"):
                if user["money"] < real_cost:
                    st.error("이동 비용이 부족합니다!")
                else:
                    # 이동 비용 차감
                    run("UPDATE users SET money=money-?, location=? WHERE student_id=?",
                        (real_cost, city, sid))
                    add_log(sid, f"🚢 {cur_city} → {city} 이동 (비용: {format_won(real_cost)})")

                    # 리스크 이벤트 (20% 확률)
                    event_msg = ""
                    if random.random() < 0.20:
                        event = random.choice(["pirate", "typhoon", "canal"])
                        if event == "pirate":
                            inv_rows = get_inventory(sid)
                            if inv_rows:
                                if has_insurance:
                                    # 보험 있으면 보상 후 보험 해지
                                    run("UPDATE users SET insurance=0 WHERE student_id=?", (sid,))
                                    event_msg = "🏴‍☠️ 해적 출몰! 무역 보험으로 화물 100% 보호됨! (보험 해지)"
                                else:
                                    # 화물 30% 손실
                                    for inv in inv_rows:
                                        lost = max(1, int(inv["quantity"] * PIRATE_LOSS))
                                        new_qty = inv["quantity"] - lost
                                        if new_qty <= 0:
                                            run("DELETE FROM inventory WHERE student_id=? AND good_name=? AND city=?",
                                                (sid, inv["good_name"], inv["city"]))
                                        else:
                                            run("UPDATE inventory SET quantity=? WHERE student_id=? AND good_name=? AND city=?",
                                                (new_qty, sid, inv["good_name"], inv["city"]))
                                    event_msg = "🏴‍☠️ 해적 출몰! 화물 30% 손실!"
                            else:
                                event_msg = "🏴‍☠️ 해적 출몰! 하지만 화물이 없어 피해 없음."
                        elif event == "typhoon":
                            # 도착 도시 무역품 가격 2배
                            run("UPDATE goods SET buy_price=buy_price*2, sell_price=sell_price*2 WHERE city=?", (city,))
                            event_msg = f"🌀 태풍 발생! {city}의 무역품 가격이 2배로 폭등!"
                        elif event == "canal":
                            # 이미 이동 후이므로 다음 항로 봉쇄
                            key2 = (city, cur_city)
                            st.session_state.canal_blocked[key2] = True
                            event_msg = f"⛔ 운하 봉쇄! {city} ↔ {cur_city} 항로 이동 비용 2배!"

                    if event_msg:
                        add_log(sid, event_msg)
                        st.warning(event_msg)
                    else:
                        st.success(f"✅ {city}에 도착했습니다!")
                    st.rerun()

    # 최근 이벤트 로그
    st.markdown("---")
    st.markdown("### 📋 최근 항해 기록")
    logs = fetchall(
        "SELECT ts, message FROM event_log WHERE student_id=? ORDER BY id DESC LIMIT 10",
        (sid,)
    )
    if logs:
        for lg in logs:
            st.caption(f"[{lg['ts']}] {lg['message']}")
    else:
        st.caption("아직 기록이 없습니다.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 학생 탭 2: 무역 시장
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tab_trade(sid):
    user = get_user(sid)
    cur_city = user["location"]
    city_row = get_city(cur_city)
    city_level = city_row["level"]

    lord_id = get_lord(cur_city)
    fta_active = cur_city in st.session_state.fta_cities
    tariff_rate = 0.0 if fta_active else (TARIFF_RATE if lord_id and lord_id != sid else 0.0)

    # 영주 정보 표시
    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        st.metric("🏙️ 도시", f"{CITY_INFO[cur_city]['flag']} {cur_city}")
    with info_col2:
        st.metric("⚔️ 영주", f"{lord_id}번 학생" if lord_id else "없음 (공석)")
    with info_col3:
        tariff_label = "0% (FTA)" if fta_active else (f"{int(tariff_rate*100)}%" if tariff_rate > 0 else "0% (영주 없음)")
        st.metric("💸 관세율", tariff_label)

    st.markdown("---")

    goods = get_goods(cur_city, city_level)
    if not goods:
        st.info("거래 가능한 무역품이 없습니다.")
        return

    # 가격 차트 (바 차트)
    df_goods = pd.DataFrame([{
        "상품": g["name"],
        "매수가(구매)": g["buy_price"],
        "매도가(판매)": g["sell_price"],
        "해금 레벨": f"Lv.{g['unlock_level']}"
    } for g in goods])

       # ── 가격 정보 표시 (현재 도시 기준) ────────────────────────────────
    st.markdown("### 📊 현재 도시 무역품 가격")

    price_rows = []
    for g in goods:
        sell_here = get_sell_price(g["name"], cur_city)
        profit_rate = round((sell_here - g["buy_price"]) / g["buy_price"] * 100, 1)
        price_rows.append({
            "상품": g["name"],
            "매수가 (구매)": g["buy_price"],
            f"현 도시 판매가 ({cur_city})": sell_here,
            "현 도시 손익률": f"{'🟢 +' if profit_rate >= 0 else '🔴 '}{profit_rate}%",
            "해금 레벨": f"Lv.{g['unlock_level']}"
        })

    df_goods = pd.DataFrame(price_rows)
    chart_data = df_goods.set_index("상품")[
        ["매수가 (구매)", f"현 도시 판매가 ({cur_city})"]
    ]
    st.bar_chart(chart_data)
    st.dataframe(df_goods, use_container_width=True, hide_index=True)

    # ── 타 도시 판매가 비교표 ────────────────────────────────────────────
    with st.expander("🌍 도시별 판매가 비교 보기 (무역 루트 참고용)"):
        compare_good = st.selectbox(
            "비교할 상품 선택",
            [g["name"] for g in goods],
            key="compare_good"
        )
        sel_g = next(g for g in goods if g["name"] == compare_good)
        compare_rows = []
        for c in CITIES:
            sp = get_sell_price(compare_good, c)
            pnl = sp - sel_g["buy_price"]
            pnl_rate = round(pnl / sel_g["buy_price"] * 100, 1)
            compare_rows.append({
                "판매 도시": f"{CITY_INFO[c]['flag']} {c}",
                "판매가": format_won(sp),
                "손익": f"{'🟢 +' if pnl >= 0 else '🔴 '}{format_won(abs(pnl))}",
                "손익률": f"{'▲' if pnl_rate >= 0 else '▼'} {abs(pnl_rate)}%",
                "추천": "⭐ 강추" if pnl_rate >= 40 else ("👍 추천" if pnl_rate >= 15 else ("❌ 손해" if pnl_rate < 0 else "보통")),
            })
        st.dataframe(pd.DataFrame(compare_rows), use_container_width=True, hide_index=True)
        st.caption(f"💡 {compare_good}의 매수가: {format_won(sel_g['buy_price'])} (구매 도시: {sel_g['city']})")

    st.dataframe(df_goods, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🛒 매수 (구매)")

    good_names = [g["name"] for g in goods]
    sel_buy = st.selectbox("구매할 상품", good_names, key="buy_sel")
    sel_good = next(g for g in goods if g["name"] == sel_buy)
    buy_qty = st.number_input("수량", min_value=1, max_value=100, value=1, key="buy_qty")
    base_cost = sel_good["buy_price"] * buy_qty
    tariff_fee = int(base_cost * tariff_rate)
    total_cost = base_cost + tariff_fee

    st.info(
        f"📦 상품: **{sel_buy}** | 단가: {format_won(sel_good['buy_price'])} × {buy_qty}개\n\n"
        f"🧾 소계: {format_won(base_cost)} + 관세: {format_won(tariff_fee)} = **합계: {format_won(total_cost)}**"
    )

    if st.button("✅ 매수 확정", key="do_buy"):
        if user["money"] < total_cost:
            st.error("잔고가 부족합니다!")
        else:
            # 잔고 차감
            run("UPDATE users SET money=money-? WHERE student_id=?", (total_cost, sid))
            # 재고 갱신 (가중평균 단가)
            existing = fetchone(
                "SELECT quantity, avg_price FROM inventory WHERE student_id=? AND good_name=? AND city=?",
                (sid, sel_buy, cur_city)
            )
            if existing and existing["quantity"] > 0:
                total_qty = existing["quantity"] + buy_qty
                new_avg = (existing["quantity"] * existing["avg_price"] + buy_qty * sel_good["buy_price"]) // total_qty
                run("UPDATE inventory SET quantity=?, avg_price=? WHERE student_id=? AND good_name=? AND city=?",
                    (total_qty, new_avg, sid, sel_buy, cur_city))
            else:
                run("INSERT OR REPLACE INTO inventory (student_id, good_name, city, quantity, avg_price) VALUES (?,?,?,?,?)",
                    (sid, sel_buy, cur_city, buy_qty, sel_good["buy_price"]))
            # 도시 누적 투자금 갱신
            run("UPDATE cities SET invest_total=invest_total+? WHERE name=?", (base_cost, cur_city))
            # 관세 → 영주 지급
            if tariff_fee > 0 and lord_id:
                run("UPDATE users SET money=money+?, tariff_income=tariff_income+? WHERE student_id=?",
                    (tariff_fee, tariff_fee, lord_id))
                add_log(lord_id, f"💰 관세 수입 {format_won(tariff_fee)} ({sid}번 학생 → {cur_city})")
            # 레벨업 체크
            check_city_levelup(cur_city)
            add_log(sid, f"🛒 {cur_city}에서 {sel_buy} {buy_qty}개 매수 (총 {format_won(total_cost)})")
            st.success(f"✅ {sel_buy} {buy_qty}개 구매 완료!")
            st.rerun()

def get_share_price(city_name):
    """
    도시 레벨과 유통 비율에 따라 실시간으로 변하는 지분 가격을 계산합니다.
    - 도시 레벨이 오를수록 가격 상승 (성장한 도시 = 가치 있는 도시)
    - 이미 팔린 주식이 많을수록 가격 상승 (희소성 반영, 초반 매점매석 방지)
    """
    city_row = get_city(city_name)
    level = city_row["level"]

    shares_all = get_city_shares_all(city_name)
    total_sold = sum(s["amount"] for s in shares_all)
    supply_ratio = total_sold / MAX_SHARES   # 0.0 ~ 1.0

    price = SHARE_PRICE * level * (1 + supply_ratio)
    return int(round(price / 100) * 100)   # 100원 단위로 반올림


def get_share_sell_price(city_name):
    """매도가는 매수가의 90% (10% 스프레드로 단타 매매 방지)"""
    return int(get_share_price(city_name) * 0.9)

    st.markdown("---")
    st.markdown("### 💰 매도 (판매)")

    inv_rows = get_inventory(sid)
    if not inv_rows:
        st.info("📦 보유 화물이 없습니다. 먼저 다른 도시에서 무역품을 구매하세요!")
        return

    sell_options = {
        f"{i['good_name']} | 구매도시: {i['city']} | {i['quantity']}개 보유 | "
        f"평균매수가: {format_won(i['avg_price'])}": i
        for i in inv_rows
    }
    sel_sell_label = st.selectbox(
        "판매할 상품 선택",
        list(sell_options.keys()),
        key="sell_sel"
    )
    sel_inv = sell_options[sel_sell_label]

    sell_qty = st.number_input(
        "판매 수량",
        min_value=1,
        max_value=sel_inv["quantity"],
        value=1,
        key="sell_qty"
    )

    # ── 현재 도시 판매가 계산 (도시별 차등 적용) ─────────────────────────
    sell_price_here = get_sell_price(sel_inv["good_name"], cur_city)
    base_revenue    = sell_price_here * sell_qty
    tariff_fee_sell = int(base_revenue * tariff_rate)
    net_revenue     = base_revenue - tariff_fee_sell
    cost_basis      = sel_inv["avg_price"] * sell_qty
    profit          = net_revenue - cost_basis
    profit_rate     = round(profit / cost_basis * 100, 1) if cost_basis > 0 else 0

    # ── 구매 도시 vs 현재 도시 판매가 비교 안내 ────────────────────────
    home_sell_price = get_sell_price(sel_inv["good_name"], sel_inv["city"])

    if cur_city == sel_inv["city"]:
        location_msg = (
            f"⚠️ **구매한 도시({cur_city})에서 되팔면 손해입니다!**  \n"
            f"다른 도시로 이동해서 판매하면 더 높은 가격을 받을 수 있어요.  \n"
            f"현재 도시 판매가: {format_won(sell_price_here)} "
            f"(매수가 {format_won(sel_inv['avg_price'])}의 {round(sell_price_here/sel_inv['avg_price']*100)}%)"
        )
        st.warning(location_msg)
    else:
        location_msg = (
            f"📍 구매 도시({sel_inv['city']}) 판매가: {format_won(home_sell_price)}  \n"
            f"📍 현재 도시({cur_city}) 판매가: **{format_won(sell_price_here)}**"
        )
        if sell_price_here > home_sell_price:
            st.success(f"✅ 구매 도시보다 **{format_won(sell_price_here - home_sell_price)} 더 비싸게** 팔 수 있습니다! {location_msg}")
        else:
            st.info(location_msg)

    # ── 거래 요약 ────────────────────────────────────────────────────────
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("현재 도시 판매가", format_won(sell_price_here))
    with col_s2:
        st.metric("관세 공제", f"-{format_won(tariff_fee_sell)}" if tariff_fee_sell > 0 else "없음")
    with col_s3:
        st.metric(
            "예상 손익",
            f"{'🟢 +' if profit >= 0 else '🔴 '}{format_won(profit)}",
            delta=f"{'+' if profit_rate >= 0 else ''}{profit_rate}%"
        )

    st.info(
        f"📦 **{sel_inv['good_name']}** {sell_qty}개  \n"
        f"🧾 소계: {format_won(base_revenue)} "
        f"- 관세: {format_won(tariff_fee_sell)} "
        f"= **실수령: {format_won(net_revenue)}**  \n"
        f"📈 총 손익: **{'🟢 +' if profit >= 0 else '🔴 '}{format_won(profit)}** "
        f"({'이익' if profit >= 0 else '손실'})"
    )

    if profit < 0:
        st.error(
            f"🔴 이 거래는 **{format_won(abs(profit))} 손실**이 발생합니다.  \n"
            f"다른 도시로 이동하면 더 유리하게 판매할 수 있습니다!"
        )

    if st.button("✅ 매도 확정", key="do_sell"):
        # 잔고 증가
        run("UPDATE users SET money=money+? WHERE student_id=?", (net_revenue, sid))
        # 재고 감소
        new_qty = sel_inv["quantity"] - sell_qty
        if new_qty <= 0:
            run(
                "DELETE FROM inventory WHERE student_id=? AND good_name=? AND city=?",
                (sid, sel_inv["good_name"], sel_inv["city"])
            )
        else:
            run(
                "UPDATE inventory SET quantity=? WHERE student_id=? AND good_name=? AND city=?",
                (new_qty, sid, sel_inv["good_name"], sel_inv["city"])
            )
        # 도시 누적 투자금
        run("UPDATE cities SET invest_total=invest_total+? WHERE name=?",
            (base_revenue, cur_city))
        # 관세 → 영주 지급
        if tariff_fee_sell > 0 and lord_id:
            run(
                "UPDATE users SET money=money+?, tariff_income=tariff_income+? WHERE student_id=?",
                (tariff_fee_sell, tariff_fee_sell, lord_id)
            )
            add_log(lord_id,
                    f"💰 관세 수입 {format_won(tariff_fee_sell)} ({sid}번 학생 → {cur_city})")
        # 레벨업 체크
        check_city_levelup(cur_city)
        add_log(
            sid,
            f"💰 {cur_city}에서 {sel_inv['good_name']} {sell_qty}개 매도 "
            f"(실수령: {format_won(net_revenue)}, 손익: {'+' if profit>=0 else ''}{format_won(profit)})"
        )
        if profit >= 0:
            st.success(f"✅ 판매 완료! 실수령 {format_won(net_revenue)} (이익: +{format_won(profit)})")
        else:
            st.warning(f"⚠️ 판매 완료. 실수령 {format_won(net_revenue)} (손실: {format_won(profit)})")
        st.rerun()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. 학생 탭 3: 도시 투자
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tab_invest(sid):
    user = get_user(sid)
    cur_city = user["location"]
    city_row = get_city(cur_city)
    city_level = city_row["level"]
    city_invest = city_row["invest_total"]
    info = CITY_INFO[cur_city]

    # 레벨업 기준
    thresholds = info["level_up"]  # [Lv1→2 기준, Lv2→3 기준]
    if city_level == 1:
        next_threshold = thresholds[0]
        progress = min(city_invest / next_threshold, 1.0) if next_threshold > 0 else 1.0
        progress_label = f"Lv.1 → Lv.2: {format_won(city_invest)} / {format_won(next_threshold)}"
    elif city_level == 2:
        next_threshold = thresholds[1]
        progress = min(city_invest / next_threshold, 1.0) if next_threshold > 0 else 1.0
        progress_label = f"Lv.2 → Lv.3: {format_won(city_invest)} / {format_won(next_threshold)}"
    else:
        progress = 1.0
        progress_label = "🏆 최고 레벨 달성!"

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏙️ 도시", f"{info['flag']} {cur_city}")
    with col2:
        st.metric("📊 도시 레벨", f"Lv.{city_level}")
    with col3:
        lord_id = get_lord(cur_city)
        st.metric("👑 현재 영주", f"{lord_id}번 학생" if lord_id else "공석")

    st.markdown("#### 🏗️ 도시 발전 게이지")
    st.progress(progress)
    st.caption(progress_label)

    st.markdown("---")
    st.markdown("### 📈 지분 현황")

    shares_all = get_city_shares_all(cur_city)
    total_sold = sum(s["amount"] for s in shares_all)
    my_shares = get_shares(sid, cur_city)
    available = MAX_SHARES - total_sold

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("내 보유 지분", f"{my_shares}주")
    with col_b:
        st.metric("전체 발행 주식", f"{total_sold} / {MAX_SHARES}주")
    with col_c:
        st.metric("잔여 매수 가능", f"{available}주")

    # 지분 상위 표
    if shares_all:
        df_sh = pd.DataFrame([{"학생 번호": s["student_id"], "보유 주식 수": s["amount"],
                                "지분율(%)": round(s["amount"] / MAX_SHARES * 100, 1)} for s in shares_all])
       
        st.dataframe(df_sh, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🏦 지분 매수 · 매도")

    current_price = get_share_price(cur_city)
    current_sell_price = get_share_sell_price(cur_city)

    price_col1, price_col2 = st.columns(2)
    with price_col1:
        st.metric("📈 현재 매수가 (1주)", format_won(current_price))
    with price_col2:
        st.metric("📉 현재 매도가 (1주)", format_won(current_sell_price))
    st.caption("💡 지분 가격은 도시 레벨과 유통량에 따라 실시간으로 변동합니다. 도시가 성장할수록, 주식이 많이 팔릴수록 가격이 오릅니다.")

    buy_tab, sell_tab = st.tabs(["🛒 매수", "💰 매도"])

    # ── 매수 탭 ─────────────────────────────────────────────
    with buy_tab:
        buy_share_qty = st.number_input(
            f"매수할 주식 수 (주당 {format_won(current_price)}, 최대 {available}주 가능)",
            min_value=1, max_value=max(1, available), value=1, key="share_buy_qty"
        )
        share_total_cost = buy_share_qty * current_price

        st.info(
            f"💳 매수 수량: **{buy_share_qty}주** × {format_won(current_price)} = "
            f"**총 {format_won(share_total_cost)}**\n\n"
            f"📌 매수 후 내 지분: **{my_shares + buy_share_qty}주 "
            f"({round((my_shares + buy_share_qty) / MAX_SHARES * 100, 1)}%)**"
        )

        if available <= 0:
            st.error("이 도시의 모든 주식이 매진되었습니다!")
        elif st.button("✅ 지분 매수 확정", key="do_share_buy"):
            if user["money"] < share_total_cost:
                st.error("잔고가 부족합니다!")
            elif buy_share_qty > available:
                st.error(f"잔여 주식이 {available}주뿐입니다!")
            else:
                run("UPDATE users SET money=money-? WHERE student_id=?", (share_total_cost, sid))
                run("UPDATE shares SET amount=amount+? WHERE student_id=? AND city=?",
                    (buy_share_qty, sid, cur_city))
                run("UPDATE cities SET invest_total=invest_total+? WHERE name=?",
                    (share_total_cost, cur_city))
                check_city_levelup(cur_city)
                add_log(sid, f"📈 {cur_city} 지분 {buy_share_qty}주 매수 ({format_won(share_total_cost)})")

                new_lord = get_lord(cur_city)
                if new_lord == sid:
                    st.success(f"🎉 지분 매수 완료! 당신이 {cur_city}의 새 영주가 되었습니다!")
                else:
                    st.success(f"✅ {buy_share_qty}주 매수 완료! (총 보유: {my_shares + buy_share_qty}주)")
                st.rerun()

    # ── 매도 탭 (신규) ───────────────────────────────────────
    with sell_tab:
        if my_shares <= 0:
            st.info("보유한 지분이 없어 매도할 수 없습니다.")
        else:
            sell_qty = st.number_input(
                f"매도할 주식 수 (주당 {format_won(current_sell_price)}, 보유 {my_shares}주)",
                min_value=1, max_value=my_shares, value=1, key="share_sell_qty"
            )
            sell_revenue = sell_qty * current_sell_price

            st.info(
                f"💰 매도 수량: **{sell_qty}주** × {format_won(current_sell_price)} = "
                f"**총 {format_won(sell_revenue)}**\n\n"
                f"📌 매도 후 내 지분: **{my_shares - sell_qty}주**"
            )
            st.caption("⚠️ 매도가는 매수가의 90% 입니다 (거래 수수료 10%).")

            was_lord = (get_lord(cur_city) == sid)

            if st.button("✅ 지분 매도 확정", key="do_share_sell"):
                run("UPDATE shares SET amount=amount-? WHERE student_id=? AND city=?",
                    (sell_qty, sid, cur_city))
                run("UPDATE users SET money=money+? WHERE student_id=?",
                    (sell_revenue, sid))
                add_log(sid, f"📉 {cur_city} 지분 {sell_qty}주 매도 (+{format_won(sell_revenue)})")

                if was_lord and get_lord(cur_city) != sid:
                    st.warning(f"👑 지분 매도로 인해 {cur_city}의 영주 자리에서 물러났습니다.")
                st.success(f"✅ {sell_qty}주 매도 완료! {format_won(sell_revenue)}을 받았습니다.")
                st.rerun()

    # ── 전체 도시 투자 현황 요약 ─────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🌍 전체 도시 투자 현황")

    summary_rows = []
    for c in CITIES:
        c_row = get_city(c)
        c_lord = get_lord(c)
        c_my = get_shares(sid, c)
        summary_rows.append({
            "도시": f"{CITY_INFO[c]['flag']} {c}",
            "레벨": f"Lv.{c_row['level']}",
            "내 지분(주)": c_my,
            "지분율(%)": round(c_my / MAX_SHARES * 100, 1),
            "영주": f"{c_lord}번 학생" if c_lord else "공석",
            "내가 영주?": "👑" if c_lord == sid else "",
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. 학생 탭 4: 내 포트폴리오
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def tab_portfolio(sid):
    user = get_user(sid)
    assets = total_assets(sid)

    # ── 자산 요약 ────────────────────────────────────────────────────────
    st.markdown("### 💼 자산 요약")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 현재 잔고", format_won(user["money"]))
    with col2:
        st.metric("📊 총 자산 평가액", format_won(assets))
    with col3:
        profit = assets - INITIAL_MONEY
        st.metric(
            "📈 초기 자본 대비 손익",
            format_won(profit),
            delta=f"{round(profit / INITIAL_MONEY * 100, 1)}%"
        )

    st.markdown("---")

    # ── 보유 화물 ────────────────────────────────────────────────────────
    st.markdown("### 📦 보유 화물 현황")
    inv_rows = get_inventory(sid)
    if inv_rows:
        cargo_data = []
        for inv in inv_rows:
            # 현재 시장가 조회 (구매 도시 기준)
            g = fetchone("SELECT sell_price FROM goods WHERE name=? AND city=?",
                         (inv["good_name"], inv["city"]))
            cur_sell = g["sell_price"] if g else inv["avg_price"]
            eval_val = cur_sell * inv["quantity"]
            pnl = (cur_sell - inv["avg_price"]) * inv["quantity"]
            cargo_data.append({
                "상품명": inv["good_name"],
                "구매 도시": inv["city"],
                "수량": inv["quantity"],
                "평균 매수가": format_won(inv["avg_price"]),
                "현재 판매가": format_won(cur_sell),
                "평가액": format_won(eval_val),
                "평가 손익": f"{'🟢 +' if pnl >= 0 else '🔴 '}{format_won(pnl)}"
            })
        st.dataframe(pd.DataFrame(cargo_data), use_container_width=True, hide_index=True)
    else:
        st.info("보유 화물이 없습니다.")

    st.markdown("---")

    # ── 보유 지분 ────────────────────────────────────────────────────────
    st.markdown("### 🏙️ 보유 지분 현황")
    share_rows = fetchall(
        "SELECT city, amount FROM shares WHERE student_id=? AND amount>0", (sid,)
    )
    if share_rows:
        share_data = []
        for s in share_rows:
            c_lord = get_lord(s["city"])
            share_data.append({
                "도시": f"{CITY_INFO[s['city']]['flag']} {s['city']}",
                "보유 주식": f"{s['amount']}주",
                "지분율": f"{round(s['amount'] / MAX_SHARES * 100, 1)}%",
                "평가액": format_won(s["amount"] * SHARE_PRICE),
                "영주 여부": "👑 영주" if c_lord == sid else ("📌 " + str(c_lord) + "번 영주" if c_lord else "공석"),
            })
        st.dataframe(pd.DataFrame(share_data), use_container_width=True, hide_index=True)
    else:
        st.info("보유 지분이 없습니다.")

    st.markdown("---")

    # ── 관세 수입 내역 ───────────────────────────────────────────────────
    st.markdown("### 💸 관세 수입 내역")
    st.metric("누적 관세 수입", format_won(user["tariff_income"]))

    tariff_logs = fetchall(
        "SELECT ts, message FROM event_log WHERE student_id=? AND message LIKE '💰 관세%' ORDER BY id DESC LIMIT 20",
        (sid,)
    )
    if tariff_logs:
        for lg in tariff_logs:
            st.caption(f"[{lg['ts']}] {lg['message']}")
    else:
        st.info("아직 관세 수입이 없습니다.")

    st.markdown("---")

    # ── 비밀번호 변경 ────────────────────────────────────────────────────
    st.markdown("### 🔐 비밀번호 변경")
    with st.expander("비밀번호 변경하기"):
        old_pw  = st.text_input("현재 비밀번호", type="password", key="old_pw")
        new_pw  = st.text_input("새 비밀번호",   type="password", key="new_pw")
        new_pw2 = st.text_input("새 비밀번호 확인", type="password", key="new_pw2")
        if st.button("변경 확정", key="change_pw"):
            db_pw = fetchone("SELECT password FROM users WHERE student_id=?", (sid,))
            if db_pw["password"] != old_pw:
                st.error("현재 비밀번호가 틀렸습니다.")
            elif new_pw != new_pw2:
                st.error("새 비밀번호가 일치하지 않습니다.")
            elif len(new_pw) < 4:
                st.error("비밀번호는 4자리 이상으로 설정해 주세요.")
            else:
                run("UPDATE users SET password=? WHERE student_id=?", (new_pw, sid))
                st.success("✅ 비밀번호가 변경되었습니다!")

    # ── 최근 전체 활동 로그 ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📋 최근 활동 기록 (최대 15건)")
    all_logs = fetchall(
        "SELECT ts, message FROM event_log WHERE student_id=? ORDER BY id DESC LIMIT 15",
        (sid,)
    )
    if all_logs:
        for lg in all_logs:
            st.caption(f"[{lg['ts']}] {lg['message']}")
    else:
        st.caption("기록이 없습니다.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. 교사 관리자 화면
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def page_admin():
    st.title("👩‍🏫 교사 관리자 대시보드")
    st.markdown("---")

    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "🏆 학생 순위표",
        "⚡ 돌발 이벤트",
        "🔐 비밀번호 관리",
        "🔄 게임 초기화"
        "📦 물품 가격 현황"
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 탭 1: 학생 순위표
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with admin_tab1:
        st.subheader("📊 전체 학생 자산 순위표")

        rows = []
        for sid in range(1, 24):
            user = get_user(sid)
            assets = total_assets(sid)

            # 영주 도시 목록
            lord_cities = []
            for c in CITIES:
                if get_lord(c) == sid:
                    lord_cities.append(f"{CITY_INFO[c]['flag']}{c}")

            # 보유 화물 요약
            inv_cnt = len(get_inventory(sid))

            rows.append({
                "학생 번호": f"{sid}번",
                "현재 위치": user["location"],
                "잔고": user["money"],
                "총 자산": assets,
                "관세 수입": user["tariff_income"],
                "영주 도시": ", ".join(lord_cities) if lord_cities else "-",
                "보유 화물 종류": inv_cnt,
                "보험": "✅" if user["insurance"] else "❌",
            })

        df_rank = pd.DataFrame(rows)
        df_rank = df_rank.sort_values("총 자산", ascending=False).reset_index(drop=True)
        df_rank.insert(0, "순위", range(1, len(df_rank) + 1))

        # 표시용 포맷
        df_display = df_rank.copy()
        df_display["잔고"]     = df_display["잔고"].apply(format_won)
        df_display["총 자산"] = df_display["총 자산"].apply(format_won)
        df_display["관세 수입"] = df_display["관세 수입"].apply(format_won)

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # CSV 다운로드
        csv_buf = io.StringIO()
        df_rank.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="📥 CSV 다운로드",
            data=csv_buf.getvalue().encode("utf-8-sig"),
            file_name=f"trade_game_rank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        st.markdown("---")

        # 도시별 영주 현황
        st.subheader("👑 도시별 영주 현황")
        lord_rows = []
        for c in CITIES:
            c_row  = get_city(c)
            c_lord = get_lord(c)
            sh_all = get_city_shares_all(c)
            total_sh = sum(s["amount"] for s in sh_all)
            lord_rows.append({
                "도시": f"{CITY_INFO[c]['flag']} {c}",
                "레벨": f"Lv.{c_row['level']}",
                "누적 투자금": format_won(c_row["invest_total"]),
                "영주": f"{c_lord}번 학생" if c_lord else "공석",
                "발행 주식": f"{total_sh}/{MAX_SHARES}주",
                "FTA 적용": "✅" if c in st.session_state.fta_cities else "❌",
            })
        st.dataframe(pd.DataFrame(lord_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # 전체 이벤트 로그 최근 30건
        st.subheader("📋 최근 게임 이벤트 로그")
        all_logs = fetchall(
            "SELECT ts, student_id, message FROM event_log ORDER BY id DESC LIMIT 30"
        )
        if all_logs:
            log_df = pd.DataFrame([{
                "시각": lg["ts"],
                "학생": f"{lg['student_id']}번" if lg["student_id"] else "시스템",
                "내용": lg["message"]
            } for lg in all_logs])
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.info("아직 이벤트 기록이 없습니다.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 탭 2: 돌발 이벤트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with admin_tab2:
        st.subheader("⚡ 돌발 이벤트 수동 발동")
        st.warning("⚠️ 이벤트를 발동하면 즉시 게임에 반영됩니다!")

        event_col1, event_col2 = st.columns(2)

        # ── 무역품 가격 폭등 ──────────────────────────────────────────────
        with event_col1:
            st.markdown("#### 📈 무역품 가격 폭등")
            sel_city_boom = st.selectbox("대상 도시", CITIES, key="boom_city")
            boom_rate = st.slider("가격 배율", min_value=1.5, max_value=5.0,
                                  value=2.0, step=0.5, key="boom_rate")
            if st.button("🚀 가격 폭등 발동", key="do_boom"):
                run(
                    "UPDATE goods SET buy_price=CAST(buy_price*? AS INTEGER), "
                    "sell_price=CAST(sell_price*? AS INTEGER) WHERE city=?",
                    (boom_rate, boom_rate, sel_city_boom)
                )
                msg = f"📈 [관리자] {sel_city_boom} 무역품 가격 {boom_rate}배 폭등 이벤트 발동!"
                add_log(0, msg)
                st.success(msg)

        # ── 무역품 가격 폭락 ──────────────────────────────────────────────
        with event_col2:
            st.markdown("#### 📉 무역품 가격 폭락")
            sel_city_crash = st.selectbox("대상 도시", CITIES, key="crash_city")
            crash_rate = st.slider("가격 배율 (1 미만)", min_value=0.2, max_value=0.9,
                                   value=0.5, step=0.1, key="crash_rate")
            if st.button("💥 가격 폭락 발동", key="do_crash"):
                run(
                    "UPDATE goods SET buy_price=CAST(buy_price*? AS INTEGER), "
                    "sell_price=CAST(sell_price*? AS INTEGER) WHERE city=?",
                    (crash_rate, crash_rate, sel_city_crash)
                )
                msg = f"📉 [관리자] {sel_city_crash} 무역품 가격 {crash_rate}배 폭락 이벤트 발동!"
                add_log(0, msg)
                st.success(msg)

        st.markdown("---")
        event_col3, event_col4 = st.columns(2)

        # ── FTA 체결 (관세 0%) ────────────────────────────────────────────
        with event_col3:
            st.markdown("#### 🤝 FTA 체결 (관세 0%)")
            sel_fta_city = st.selectbox("FTA 적용 도시", CITIES, key="fta_city")
            fta_active_now = sel_fta_city in st.session_state.fta_cities
            if fta_active_now:
                st.info(f"✅ {sel_fta_city}는 현재 FTA 적용 중입니다.")
                if st.button("❌ FTA 해제", key="remove_fta"):
                    st.session_state.fta_cities.discard(sel_fta_city)
                    msg = f"🤝 [관리자] {sel_fta_city} FTA 해제 (관세 복구)"
                    add_log(0, msg)
                    st.success(msg)
                    st.rerun()
            else:
                if st.button("✅ FTA 체결 발동", key="do_fta"):
                    st.session_state.fta_cities.add(sel_fta_city)
                    msg = f"🤝 [관리자] {sel_fta_city} FTA 체결! 관세 0% 적용!"
                    add_log(0, msg)
                    st.success(msg)
                    st.rerun()

        # ── 운하 봉쇄 ────────────────────────────────────────────────────
        with event_col4:
            st.markdown("#### ⛔ 운하 봉쇄")
            canal_c1 = st.selectbox("출발 도시", CITIES, key="canal_c1")
            canal_c2 = st.selectbox("도착 도시",
                                    [c for c in CITIES if c != canal_c1],
                                    key="canal_c2")
            canal_key = (canal_c1, canal_c2)
            if canal_key in st.session_state.canal_blocked and st.session_state.canal_blocked[canal_key]:
                st.info(f"⛔ {canal_c1} ↔ {canal_c2} 항로 현재 봉쇄 중")
                if st.button("봉쇄 해제", key="remove_canal"):
                    st.session_state.canal_blocked[canal_key] = False
                    st.session_state.canal_blocked[(canal_c2, canal_c1)] = False
                    add_log(0, f"⛔ [관리자] {canal_c1} ↔ {canal_c2} 운하 봉쇄 해제")
                    st.rerun()
            else:
                if st.button("⛔ 운하 봉쇄 발동", key="do_canal"):
                    st.session_state.canal_blocked[canal_key] = True
                    st.session_state.canal_blocked[(canal_c2, canal_c1)] = True
                    msg = f"⛔ [관리자] {canal_c1} ↔ {canal_c2} 운하 봉쇄! 이동 비용 2배!"
                    add_log(0, msg)
                    st.success(msg)
                    st.rerun()

        st.markdown("---")

        # ── 도시 강제 레벨업 ─────────────────────────────────────────────
        st.markdown("#### 🎯 도시 강제 레벨업")
        lv_city = st.selectbox("레벨업 도시 선택", CITIES, key="lv_city")
        lv_row  = get_city(lv_city)
        st.info(f"현재 {lv_city} 레벨: **Lv.{lv_row['level']}**")
        if lv_row["level"] < 3:
            if st.button("⬆️ 레벨업 강제 실행", key="do_levelup"):
                run("UPDATE cities SET level=level+1 WHERE name=?", (lv_city,))
                msg = f"🎉 [관리자] {lv_city} 강제 레벨업! Lv.{lv_row['level']+1} 달성!"
                add_log(0, msg)
                st.success(msg)
                st.rerun()
        else:
            st.success("이미 최고 레벨(Lv.3)입니다.")

        st.markdown("---")

        # ── 특정 학생 자금 지급 ──────────────────────────────────────────
        st.markdown("#### 💰 학생 자금 지급 / 차감")
        money_sid = st.selectbox("대상 학생", list(range(1, 24)),
                                 format_func=lambda x: f"{x}번 학생", key="money_sid")
        money_amt = st.number_input("금액 (음수 입력 시 차감)",
                                    min_value=-5_000_000, max_value=5_000_000,
                                    value=100_000, step=10_000, key="money_amt")
        if st.button("💳 자금 지급/차감 실행", key="do_money"):
            run("UPDATE users SET money=money+? WHERE student_id=?", (money_amt, money_sid))
            action = "지급" if money_amt >= 0 else "차감"
            msg = f"💰 [관리자] {money_sid}번 학생에게 {format_won(abs(money_amt))} {action}"
            add_log(0, msg)
            add_log(money_sid, msg)
            st.success(msg)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 탭 3: 비밀번호 관리
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with admin_tab3:
        st.subheader("🔐 학생 비밀번호 관리")

        pw_sid = st.selectbox("대상 학생 선택", list(range(1, 24)),
                              format_func=lambda x: f"{x}번 학생", key="pw_sid")
        new_admin_pw = st.text_input("새 비밀번호 설정", type="password", key="new_admin_pw")

        if st.button("🔑 비밀번호 초기화/변경", key="do_admin_pw"):
            if len(new_admin_pw) < 4:
                st.error("비밀번호는 4자리 이상으로 설정해 주세요.")
            else:
                run("UPDATE users SET password=? WHERE student_id=?", (new_admin_pw, pw_sid))
                st.success(f"✅ {pw_sid}번 학생의 비밀번호가 변경되었습니다.")

        st.markdown("---")

        if st.button("🔄 전체 학생 비밀번호 '0000' 으로 초기화", key="reset_all_pw"):
            run("UPDATE users SET password='0000'")
            st.success("✅ 전체 학생 비밀번호가 '0000'으로 초기화되었습니다.")

        st.markdown("---")
        st.markdown("#### 📋 현재 학생 비밀번호 목록")
        pw_rows = fetchall("SELECT student_id, password FROM users ORDER BY student_id")
        pw_df = pd.DataFrame([{
            "학생 번호": f"{r['student_id']}번",
            "비밀번호": r["password"]
        } for r in pw_rows])
        st.dataframe(pw_df, use_container_width=True, hide_index=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 탭 4: 게임 초기화
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with admin_tab4:
        st.subheader("🔄 게임 데이터 초기화")
        st.error(
            "⚠️ **주의:** 초기화 버튼을 누르면 모든 학생의 자금, 위치, 재고, 지분, "
            "이벤트 로그가 완전히 리셋됩니다. 이 작업은 되돌릴 수 없습니다!"
        )

        confirm = st.checkbox("정말로 초기화하겠습니다. (체크 후 버튼 활성화)", key="reset_confirm")
        if confirm:
            if st.button("🔴 게임 전체 초기화 실행", key="do_reset"):
                reset_db()
                st.success("✅ 게임 데이터가 초기화되었습니다! 모든 학생이 1,000,000원으로 시작합니다.")
                st.balloons()
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 탭 5: 물품 가격 조정
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with admin_tab5:
        st.subheader("📦 도시별 물품 가격 현황")

        rows = fetchall(
            "SELECT city, name, buy_price, sell_price, unlock_level FROM goods ORDER BY city, name"
        )
        if not rows:
            st.info("등록된 물품이 없습니다.")
        else:
            df_goods = pd.DataFrame(
                [dict(r) for r in rows],
                columns=["city", "name", "buy_price", "sell_price", "unlock_level"]
            )
            df_goods.columns = ["도시", "물품명", "매입가", "판매가", "해금레벨"]

            city_filter = st.selectbox(
                "도시 선택", ["전체"] + sorted(df_goods["도시"].unique().tolist()),
                key="admin_price_city_filter"
            )
            view_df = df_goods if city_filter == "전체" else df_goods[df_goods["도시"] == city_filter]

            st.dataframe(view_df, use_container_width=True, hide_index=True)

            st.markdown("#### 📈 물품별 평균 가격 비교 (전체 도시 기준)")
            avg_df = df_goods.groupby("물품명")[["매입가", "판매가"]].mean().round(0)
            st.bar_chart(avg_df)

            st.markdown("#### ✏️ 물품 가격 직접 조정")
            st.caption("가격이 지나치게 높아진 물품을 선택해 초기화하거나 조정할 수 있습니다.")

            adjust_city = st.selectbox("도시", sorted(df_goods["도시"].unique().tolist()), key="adj_city")
            city_goods = df_goods[df_goods["도시"] == adjust_city]["물품명"].tolist()
            adjust_good = st.selectbox("물품", city_goods, key="adj_good")

            cur_row = fetchone(
                "SELECT buy_price, sell_price FROM goods WHERE city=? AND name=?",
                (adjust_city, adjust_good)
            )

            new_buy = st.number_input("새 매입가", min_value=0, value=cur_row["buy_price"], step=100, key="adj_buy")
            new_sell = st.number_input("새 판매가", min_value=0, value=cur_row["sell_price"], step=100, key="adj_sell")

            if st.button("💾 가격 적용", key="apply_price_adjust"):
                run(
                    "UPDATE goods SET buy_price=?, sell_price=? WHERE city=? AND name=?",
                    (new_buy, new_sell, adjust_city, adjust_good)
                )
                st.success(f"{adjust_city} - {adjust_good} 가격이 조정되었습니다.")
                st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. 학생 메인 페이지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def page_student(sid):
    user = get_user(sid)
    st.title(f"🌊 대항해시대 보드게임 — {sid}번 학생")
    st.caption(
        f"📍 현재 위치: **{user['location']}**  |  "
        f"💰 잔고: **{format_won(user['money'])}**  |  "
        f"🏦 총 자산: **{format_won(total_assets(sid))}**"
    )

    # 시스템 공지 (레벨업 등)
    sys_logs = fetchall(
        "SELECT ts, message FROM event_log WHERE student_id=0 ORDER BY id DESC LIMIT 3"
    )
    if sys_logs:
        for lg in sys_logs:
            st.info(f"📢 [{lg['ts']}] {lg['message']}")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🗺️ 세계 지도 & 이동",
        "🛒 무역 시장",
        "📈 도시 투자",
        "💼 내 포트폴리오"
    ])

    with tab1:
        tab_map(sid)
    with tab2:
        tab_trade(sid)
    with tab3:
        tab_invest(sid)
    with tab4:
        tab_portfolio(sid)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 11. 앱 메인 진입점
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    st.set_page_config(
        page_title="🌊 대항해시대 세계 무역 보드게임",
        page_icon="⚓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # CSS 스타일 보정
    st.markdown("""
    <style>
        .stMetric label { font-size: 0.85rem; }
        .stButton>button {
            width: 100%;
            border-radius: 8px;
            font-weight: bold;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1rem;
            font-weight: bold;
        }
    </style>
    """, unsafe_allow_html=True)

    # 세션 초기화
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = None
    if "student_id" not in st.session_state:
        st.session_state.student_id = None
    if "canal_blocked" not in st.session_state:
        st.session_state.canal_blocked = {}
    if "fta_cities" not in st.session_state:
        st.session_state.fta_cities = set()

    # DB 초기화 (최초 실행 시)
    init_db()

    # 사이드바 로그인
    sidebar_login()

    # 메인 화면 라우팅
    if st.session_state.logged_in == "admin":
        page_admin()
    elif st.session_state.logged_in == "student":
        page_student(st.session_state.student_id)
    else:
        # 로그인 전 메인 화면
        st.markdown("""
        <div style='text-align:center; padding: 60px 0 20px 0;'>
            <h1>⚓ 대항해시대 세계 무역 보드게임</h1>
            <h3>🌍 무역과 투자로 세계를 정복하라!</h3>
        </div>
        """, unsafe_allow_html=True)

        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
            ---
            ### 🎮 게임 소개
            - **8개 도시**를 항해하며 무역품을 사고팔아 부를 축적하세요!
            - **지분을 매수**하여 도시의 영주가 되면 관세 수입이 생깁니다!
            - **도시에 투자**할수록 레벨이 올라 더 좋은 무역품이 해금됩니다!
            - 해적, 태풍, 운하 봉쇄 등 **리스크 이벤트**를 조심하세요!

            ---
            ### 🌏 8개 무역 도시
            | 도시 | 지역 | 주요 무역품 |
            |------|------|------------|
            | 🇨🇳 상하이 | 아시아 | 비단, 도자기, AI칩 |
            | 🇮🇳 뭄바이 | 아시아 | 향신료, 홍차, 의약원료 |
            | 🇬🇧 런던 | 유럽 | 정밀기계, 위스키, 양자컴퓨터 |
            | 🇪🇬 카이로 | 아프리카 | 면화, 석유, 희토류 |
            | 🇺🇸 뉴욕 | 북아메리카 | IT기기, 금융상품, 바이오칩 |
            | 🇧🇷 상파울루 | 남아메리카 | 커피원두, 카카오, 열대의약품 |
            | 🇦🇺 시드니 | 오세아니아 | 양모, 철광석, 핵융합소재 |
            | 🇮🇸 레이캬비크 | 북극권 | 수산물통조림, 신재생에너지, 친환경수소 |

            ---
            ⬅️ **왼쪽 사이드바에서 로그인하세요!**
            """)


if __name__ == "__main__":
    main()

