# 설정값
BOT_TOKEN = os.getenv("TOKEN1")

# 경험치 설정
EXP_PER_VOICE_INTERVAL = 100  # 음성 5분당
VOICE_INTERVAL_SECONDS = 300   # 5분
EXP_PER_CHAT = 20

# 전환 비율
GACHA_TO_EXP_RATE = 10      # 가챠 100p -> 경험치 10
EXP_TO_GACHA_RATE = 100     # 경험치 10 -> 가챠 100p

# 가챠 제한
MAX_5050_BET = 1000  # 1/2 확률 게임 최대 배팅

# 역할 상점 (역할ID: 가격)
ROLE_SHOP = {
    # 123456789: 1000,  # 예시: 역할ID: 필요 경험치
}

# 역할 세트 보너스 (세트 역할들을 모두 가지면 보너스 역할 지급)
ROLE_SETS = {
    # 보너스역할ID: [필요역할ID1, 필요역할ID2, ...]
}

# 역할 선택권으로 교환 가능한 역할들
ROLE_TICKET_OPTIONS = {
    # 선택권ID: [교환가능역할ID1, 교환가능역할ID2, ...]
}
ROLE_TICKET_ROLES = {
    111111111111111111: {
        "name": "빨강 역할",
        "price": 1000,
        "emoji": "🔴",
        "rarity": "Common"
    },

    222222222222222222: {
        "name": "파랑 역할",
        "price": 3000,
        "emoji": "🔵",
        "rarity": "Rare"
    },

    333333333333333333: {
        "name": "초록 역할",
        "price": 10000,
        "emoji": "🟢",
        "rarity": "SSR"
    }
}
