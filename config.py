import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

class Config:
    # Binance API 설정
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # 거래 설정
    SYMBOL = 'BTCUSDT'  # 거래할 심볼
    TIMEFRAME = '1h'    # 시간 프레임 (1분, 5분, 15분, 1시간, 4시간, 1일)
    
    # 이동평균선 설정
    SHORT_MA_PERIOD = 10  # 단기 이동평균선 기간
    LONG_MA_PERIOD = 30   # 장기 이동평균선 기간
    
    # 거래 설정
    TRADE_AMOUNT = 0.001  # 거래할 BTC 수량 (USDT 기준으로 변경 가능)
    MAX_POSITION_SIZE = 0.01  # 최대 포지션 크기
    
    # 리스크 관리
    STOP_LOSS_PERCENT = 2.0  # 손절매 비율 (%)
    TAKE_PROFIT_PERCENT = 5.0  # 익절매 비율 (%)
    
    # 로그 설정
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'trading.log'
    
    # 백테스팅 설정
    BACKTEST_START_DATE = '2023-01-01'
    BACKTEST_END_DATE = '2024-01-01'
    INITIAL_BALANCE = 10000  # 초기 자본 (USDT)
    
    @classmethod
    def validate_config(cls):
        """설정 유효성 검사"""
        if not cls.BINANCE_API_KEY or not cls.BINANCE_SECRET_KEY:
            raise ValueError("Binance API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        if cls.SHORT_MA_PERIOD >= cls.LONG_MA_PERIOD:
            raise ValueError("단기 이동평균선 기간이 장기 이동평균선 기간보다 작아야 합니다.")
        
        return True
