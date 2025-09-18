import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from config import Config

class TradingLogger:
    def __init__(self):
        """로깅 시스템 초기화"""
        self.setup_logging()
    
    def setup_logging(self):
        """로깅 설정"""
        # 로그 디렉토리 생성
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 로그 파일 경로
        log_file = os.path.join(log_dir, Config.LOG_FILE)
        
        # 로거 설정
        self.logger = logging.getLogger('trading_system')
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 기존 핸들러 제거
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 파일 핸들러 (회전 로그)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # 외부 라이브러리 로그 레벨 조정
        logging.getLogger('ccxt').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
    
    def get_logger(self):
        """로거 인스턴스 반환"""
        return self.logger
    
    def log_trade(self, trade_type, symbol, amount, price, profit=None):
        """거래 로그 기록"""
        message = f"거래 실행 - {trade_type}: {amount} {symbol} @ {price}"
        if profit is not None:
            message += f" (수익: {profit:.2f} USDT)"
        
        self.logger.info(message)
    
    def log_signal(self, signal_type, symbol, price, indicators=None):
        """신호 로그 기록"""
        message = f"신호 감지 - {signal_type}: {symbol} @ {price}"
        if indicators:
            message += f" (지표: {indicators})"
        
        self.logger.info(message)
    
    def log_error(self, error_msg, exception=None):
        """오류 로그 기록"""
        if exception:
            self.logger.error(f"{error_msg}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(error_msg)
    
    def log_performance(self, stats):
        """성과 로그 기록"""
        self.logger.info(f"거래 성과 - 총 거래: {stats['total_trades']}, "
                        f"승률: {stats.get('win_rate', 0):.1f}%, "
                        f"총 수익: {stats['total_profit']:.2f} USDT")
    
    def log_balance(self, balance_info):
        """잔고 로그 기록"""
        self.logger.info(f"계정 잔고 - {balance_info}")
    
    def log_system_status(self, status):
        """시스템 상태 로그 기록"""
        self.logger.info(f"시스템 상태 - {status}")

# 전역 로거 인스턴스
trading_logger = TradingLogger()
logger = trading_logger.get_logger()
