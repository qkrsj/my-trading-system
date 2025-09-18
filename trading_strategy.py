import pandas as pd
import numpy as np
import ta
from datetime import datetime
import logging
from config import Config

class GoldenCrossStrategy:
    def __init__(self, short_period=10, long_period=30):
        """
        골든크로스 전략 초기화
        
        Args:
            short_period (int): 단기 이동평균선 기간
            long_period (int): 장기 이동평균선 기간
        """
        self.short_period = short_period
        self.long_period = long_period
        self.logger = logging.getLogger(__name__)
        
        # 전략 상태
        self.position = None  # 'long', 'short', None
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
    def calculate_indicators(self, df):
        """
        기술적 지표 계산
        
        Args:
            df (pd.DataFrame): OHLCV 데이터
            
        Returns:
            pd.DataFrame: 지표가 추가된 데이터프레임
        """
        try:
            # 이동평균선 계산
            df['MA_short'] = ta.trend.sma_indicator(df['close'], window=self.short_period)
            df['MA_long'] = ta.trend.sma_indicator(df['close'], window=self.long_period)
            
            # RSI 계산 (추가 필터링용)
            df['RSI'] = ta.momentum.rsi(df['close'], window=14)
            
            # 볼린저 밴드 (추가 필터링용)
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['BB_upper'] = bb.bollinger_hband()
            df['BB_lower'] = bb.bollinger_lband()
            df['BB_middle'] = bb.bollinger_mavg()
            
            # MACD (추가 필터링용)
            macd = ta.trend.MACD(df['close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_histogram'] = macd.macd_diff()
            
            # 거래량 이동평균
            df['Volume_MA'] = ta.volume.volume_sma(df['close'], df['volume'], window=20)
            
            return df
            
        except Exception as e:
            self.logger.error(f"지표 계산 실패: {e}")
            return df
    
    def generate_signals(self, df):
        """
        거래 신호 생성
        
        Args:
            df (pd.DataFrame): 지표가 포함된 OHLCV 데이터
            
        Returns:
            pd.DataFrame: 신호가 추가된 데이터프레임
        """
        try:
            df = df.copy()
            
            # 골든크로스/데드크로스 신호
            df['golden_cross'] = (
                (df['MA_short'] > df['MA_long']) & 
                (df['MA_short'].shift(1) <= df['MA_long'].shift(1))
            )
            
            df['dead_cross'] = (
                (df['MA_short'] < df['MA_long']) & 
                (df['MA_short'].shift(1) >= df['MA_long'].shift(1))
            )
            
            # 추가 필터링 조건
            # RSI 조건 (과매수/과매도 방지)
            rsi_oversold = df['RSI'] < 30
            rsi_overbought = df['RSI'] > 70
            
            # 볼린저 밴드 조건
            bb_oversold = df['close'] < df['BB_lower']
            bb_overbought = df['close'] > df['BB_upper']
            
            # MACD 조건
            macd_bullish = (df['MACD'] > df['MACD_signal']) & (df['MACD'].shift(1) <= df['MACD_signal'].shift(1))
            macd_bearish = (df['MACD'] < df['MACD_signal']) & (df['MACD'].shift(1) >= df['MACD_signal'].shift(1))
            
            # 거래량 조건 (평균 거래량보다 높아야 함)
            volume_condition = df['volume'] > df['Volume_MA']
            
            # 최종 신호 생성
            df['buy_signal'] = (
                df['golden_cross'] & 
                ~rsi_overbought & 
                ~bb_overbought & 
                macd_bullish & 
                volume_condition
            )
            
            df['sell_signal'] = (
                df['dead_cross'] & 
                ~rsi_oversold & 
                ~bb_oversold & 
                macd_bearish & 
                volume_condition
            )
            
            # 강제 청산 신호 (손절매/익절매)
            df['force_sell'] = (
                (df['RSI'] > 80) |  # 극도 과매수
                (df['close'] > df['BB_upper'] * 1.02)  # 볼린저 밴드 상단 돌파
            )
            
            return df
            
        except Exception as e:
            self.logger.error(f"신호 생성 실패: {e}")
            return df
    
    def should_buy(self, df, current_index):
        """
        매수 조건 확인
        
        Args:
            df (pd.DataFrame): 신호가 포함된 데이터프레임
            current_index (int): 현재 인덱스
            
        Returns:
            bool: 매수 여부
        """
        if current_index < self.long_period:
            return False
            
        current_row = df.iloc[current_index]
        
        # 매수 신호 확인
        if current_row['buy_signal']:
            self.logger.info(f"매수 신호 감지: 가격={current_row['close']:.2f}, "
                           f"단기MA={current_row['MA_short']:.2f}, "
                           f"장기MA={current_row['MA_long']:.2f}")
            return True
            
        return False
    
    def should_sell(self, df, current_index):
        """
        매도 조건 확인
        
        Args:
            df (pd.DataFrame): 신호가 포함된 데이터프레임
            current_index (int): 현재 인덱스
            
        Returns:
            bool: 매도 여부
        """
        if current_index < self.long_period:
            return False
            
        current_row = df.iloc[current_index]
        
        # 매도 신호 확인
        if current_row['sell_signal'] or current_row['force_sell']:
            signal_type = "매도 신호" if current_row['sell_signal'] else "강제 청산"
            self.logger.info(f"{signal_type} 감지: 가격={current_row['close']:.2f}, "
                           f"단기MA={current_row['MA_short']:.2f}, "
                           f"장기MA={current_row['MA_long']:.2f}")
            return True
            
        return False
    
    def calculate_stop_loss_take_profit(self, entry_price, position_type='long'):
        """
        손절매/익절매 가격 계산
        
        Args:
            entry_price (float): 진입 가격
            position_type (str): 포지션 타입 ('long' 또는 'short')
            
        Returns:
            tuple: (stop_loss_price, take_profit_price)
        """
        if position_type == 'long':
            stop_loss = entry_price * (1 - Config.STOP_LOSS_PERCENT / 100)
            take_profit = entry_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
        else:
            stop_loss = entry_price * (1 + Config.STOP_LOSS_PERCENT / 100)
            take_profit = entry_price * (1 - Config.TAKE_PROFIT_PERCENT / 100)
            
        return stop_loss, take_profit
    
    def check_stop_loss_take_profit(self, current_price):
        """
        손절매/익절매 조건 확인
        
        Args:
            current_price (float): 현재 가격
            
        Returns:
            str: 'stop_loss', 'take_profit', 또는 None
        """
        if self.position == 'long':
            if current_price <= self.stop_loss_price:
                return 'stop_loss'
            elif current_price >= self.take_profit_price:
                return 'take_profit'
        elif self.position == 'short':
            if current_price >= self.stop_loss_price:
                return 'stop_loss'
            elif current_price <= self.take_profit_price:
                return 'take_profit'
                
        return None
    
    def update_position(self, position_type, entry_price):
        """
        포지션 업데이트
        
        Args:
            position_type (str): 포지션 타입
            entry_price (float): 진입 가격
        """
        self.position = position_type
        self.entry_price = entry_price
        self.stop_loss_price, self.take_profit_price = self.calculate_stop_loss_take_profit(
            entry_price, position_type
        )
        
        self.logger.info(f"포지션 업데이트: {position_type}, "
                        f"진입가: {entry_price:.2f}, "
                        f"손절가: {self.stop_loss_price:.2f}, "
                        f"익절가: {self.take_profit_price:.2f}")
    
    def clear_position(self):
        """포지션 초기화"""
        self.position = None
        self.entry_price = None
        self.stop_loss_price = None
        self.take_profit_price = None
        
    def get_strategy_info(self):
        """전략 정보 반환"""
        return {
            'strategy_name': 'Golden Cross Strategy',
            'short_period': self.short_period,
            'long_period': self.long_period,
            'current_position': self.position,
            'entry_price': self.entry_price,
            'stop_loss_price': self.stop_loss_price,
            'take_profit_price': self.take_profit_price
        }
