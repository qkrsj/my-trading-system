import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from config import Config

class BinanceClient:
    def __init__(self):
        """Binance 클라이언트 초기화"""
        self.exchange = ccxt.binance({
            'apiKey': Config.BINANCE_API_KEY,
            'secret': Config.BINANCE_SECRET_KEY,
            'sandbox': False,  # 실제 거래용 (테스트용은 True)
            'enableRateLimit': True,
        })
        
        self.logger = logging.getLogger(__name__)
        
    def get_account_balance(self):
        """계정 잔고 조회"""
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")
            return None
    
    def get_current_price(self, symbol):
        """현재 가격 조회"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            self.logger.error(f"가격 조회 실패: {e}")
            return None
    
    def get_historical_data(self, symbol, timeframe, limit=100):
        """과거 데이터 조회"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            self.logger.error(f"과거 데이터 조회 실패: {e}")
            return None
    
    def place_market_buy_order(self, symbol, amount):
        """시장가 매수 주문"""
        try:
            order = self.exchange.create_market_buy_order(symbol, amount)
            self.logger.info(f"매수 주문 성공: {order}")
            return order
        except Exception as e:
            self.logger.error(f"매수 주문 실패: {e}")
            return None
    
    def place_market_sell_order(self, symbol, amount):
        """시장가 매도 주문"""
        try:
            order = self.exchange.create_market_sell_order(symbol, amount)
            self.logger.info(f"매도 주문 성공: {order}")
            return order
        except Exception as e:
            self.logger.error(f"매도 주문 실패: {e}")
            return None
    
    def place_limit_buy_order(self, symbol, amount, price):
        """지정가 매수 주문"""
        try:
            order = self.exchange.create_limit_buy_order(symbol, amount, price)
            self.logger.info(f"지정가 매수 주문 성공: {order}")
            return order
        except Exception as e:
            self.logger.error(f"지정가 매수 주문 실패: {e}")
            return None
    
    def place_limit_sell_order(self, symbol, amount, price):
        """지정가 매도 주문"""
        try:
            order = self.exchange.create_limit_sell_order(symbol, amount, price)
            self.logger.info(f"지정가 매도 주문 성공: {order}")
            return order
        except Exception as e:
            self.logger.error(f"지정가 매도 주문 실패: {e}")
            return None
    
    def cancel_order(self, order_id, symbol):
        """주문 취소"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            self.logger.info(f"주문 취소 성공: {result}")
            return result
        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")
            return None
    
    def get_open_orders(self, symbol=None):
        """미체결 주문 조회"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            self.logger.error(f"미체결 주문 조회 실패: {e}")
            return []
    
    def get_order_status(self, order_id, symbol):
        """주문 상태 조회"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return order
        except Exception as e:
            self.logger.error(f"주문 상태 조회 실패: {e}")
            return None
    
    def get_trading_fees(self, symbol):
        """거래 수수료 조회"""
        try:
            fees = self.exchange.fetch_trading_fees(symbol)
            return fees
        except Exception as e:
            self.logger.error(f"거래 수수료 조회 실패: {e}")
            return None
    
    def calculate_order_amount(self, symbol, usdt_amount):
        """USDT 금액을 기반으로 주문 수량 계산"""
        try:
            current_price = self.get_current_price(symbol)
            if current_price:
                # 거래 수수료 고려 (0.1%)
                fee_rate = 0.001
                adjusted_amount = usdt_amount * (1 - fee_rate)
                amount = adjusted_amount / current_price
                return amount
            return None
        except Exception as e:
            self.logger.error(f"주문 수량 계산 실패: {e}")
            return None
