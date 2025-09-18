import time
import schedule
import threading
from datetime import datetime, timedelta
import pandas as pd
import logging
from binance_client import BinanceClient
from trading_strategy import GoldenCrossStrategy
from config import Config

class TradingEngine:
    def __init__(self):
        """거래 엔진 초기화"""
        self.binance_client = BinanceClient()
        self.strategy = GoldenCrossStrategy(
            short_period=Config.SHORT_MA_PERIOD,
            long_period=Config.LONG_MA_PERIOD
        )
        
        self.logger = logging.getLogger(__name__)
        self.is_running = False
        self.last_signal_time = None
        
        # 거래 통계
        self.trade_stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'max_drawdown': 0.0,
            'current_drawdown': 0.0
        }
        
    def start_trading(self):
        """거래 시작"""
        self.logger.info("자동 거래 시스템 시작")
        self.is_running = True
        
        # 설정 검증
        try:
            Config.validate_config()
        except ValueError as e:
            self.logger.error(f"설정 오류: {e}")
            return False
        
        # API 연결 테스트
        if not self.test_connection():
            self.logger.error("Binance API 연결 실패")
            return False
        
        # 스케줄러 설정
        self.setup_scheduler()
        
        # 메인 거래 루프 시작
        self.run_trading_loop()
        
        return True
    
    def stop_trading(self):
        """거래 중지"""
        self.logger.info("자동 거래 시스템 중지")
        self.is_running = False
        
    def test_connection(self):
        """API 연결 테스트"""
        try:
            balance = self.binance_client.get_account_balance()
            if balance:
                self.logger.info("Binance API 연결 성공")
                return True
            return False
        except Exception as e:
            self.logger.error(f"API 연결 테스트 실패: {e}")
            return False
    
    def setup_scheduler(self):
        """스케줄러 설정"""
        # 1분마다 거래 신호 확인
        schedule.every(1).minutes.do(self.check_trading_signals)
        
        # 1시간마다 포지션 상태 확인
        schedule.every(1).hours.do(self.check_position_status)
        
        # 매일 자정에 통계 리셋
        schedule.every().day.at("00:00").do(self.reset_daily_stats)
        
    def run_trading_loop(self):
        """메인 거래 루프"""
        self.logger.info("거래 루프 시작")
        
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(10)  # 10초마다 스케줄 확인
            except KeyboardInterrupt:
                self.logger.info("사용자에 의해 거래 중지")
                break
            except Exception as e:
                self.logger.error(f"거래 루프 오류: {e}")
                time.sleep(30)  # 오류 발생 시 30초 대기
        
        self.logger.info("거래 루프 종료")
    
    def check_trading_signals(self):
        """거래 신호 확인"""
        try:
            # 최신 데이터 가져오기
            df = self.binance_client.get_historical_data(
                Config.SYMBOL, 
                Config.TIMEFRAME, 
                limit=100
            )
            
            if df is None or len(df) < self.strategy.long_period:
                self.logger.warning("데이터 부족으로 신호 확인 불가")
                return
            
            # 지표 계산
            df = self.strategy.calculate_indicators(df)
            df = self.strategy.generate_signals(df)
            
            # 현재 인덱스 (가장 최근 데이터)
            current_index = len(df) - 1
            current_price = df.iloc[current_index]['close']
            
            # 손절매/익절매 확인
            if self.strategy.position:
                sl_tp_result = self.strategy.check_stop_loss_take_profit(current_price)
                if sl_tp_result:
                    self.execute_exit_trade(sl_tp_result, current_price)
                    return
            
            # 새로운 거래 신호 확인
            if self.strategy.should_buy(df, current_index):
                self.execute_buy_trade(current_price)
            elif self.strategy.should_sell(df, current_index):
                self.execute_sell_trade(current_price)
                
        except Exception as e:
            self.logger.error(f"신호 확인 중 오류: {e}")
    
    def execute_buy_trade(self, current_price):
        """매수 거래 실행"""
        try:
            # 이미 포지션이 있는지 확인
            if self.strategy.position:
                self.logger.info("이미 포지션이 있어 매수 건너뜀")
                return
            
            # 거래 수량 계산
            balance = self.binance_client.get_account_balance()
            if not balance:
                self.logger.error("잔고 조회 실패")
                return
            
            usdt_balance = balance['USDT']['free']
            if usdt_balance < Config.TRADE_AMOUNT:
                self.logger.warning(f"USDT 잔고 부족: {usdt_balance}")
                return
            
            # 주문 수량 계산
            amount = self.binance_client.calculate_order_amount(
                Config.SYMBOL, 
                Config.TRADE_AMOUNT
            )
            
            if not amount:
                self.logger.error("주문 수량 계산 실패")
                return
            
            # 매수 주문 실행
            order = self.binance_client.place_market_buy_order(Config.SYMBOL, amount)
            
            if order:
                self.strategy.update_position('long', current_price)
                self.trade_stats['total_trades'] += 1
                self.last_signal_time = datetime.now()
                
                self.logger.info(f"매수 주문 성공: {amount} {Config.SYMBOL} @ {current_price}")
                
        except Exception as e:
            self.logger.error(f"매수 거래 실행 실패: {e}")
    
    def execute_sell_trade(self, current_price):
        """매도 거래 실행"""
        try:
            # 포지션이 있는지 확인
            if not self.strategy.position:
                self.logger.info("포지션이 없어 매도 건너뜀")
                return
            
            # 현재 보유 수량 확인
            balance = self.binance_client.get_account_balance()
            if not balance:
                self.logger.error("잔고 조회 실패")
                return
            
            # 심볼에서 기본 자산 추출 (예: BTCUSDT -> BTC)
            base_asset = Config.SYMBOL.replace('USDT', '')
            asset_balance = balance[base_asset]['free']
            
            if asset_balance <= 0:
                self.logger.warning(f"{base_asset} 잔고 없음")
                return
            
            # 매도 주문 실행
            order = self.binance_client.place_market_sell_order(Config.SYMBOL, asset_balance)
            
            if order:
                # 수익/손실 계산
                if self.strategy.position == 'long':
                    profit = (current_price - self.strategy.entry_price) * asset_balance
                else:
                    profit = (self.strategy.entry_price - current_price) * asset_balance
                
                self.trade_stats['total_profit'] += profit
                
                if profit > 0:
                    self.trade_stats['winning_trades'] += 1
                else:
                    self.trade_stats['losing_trades'] += 1
                
                self.strategy.clear_position()
                self.last_signal_time = datetime.now()
                
                self.logger.info(f"매도 주문 성공: {asset_balance} {Config.SYMBOL} @ {current_price}, "
                               f"수익: {profit:.2f} USDT")
                
        except Exception as e:
            self.logger.error(f"매도 거래 실행 실패: {e}")
    
    def execute_exit_trade(self, exit_reason, current_price):
        """손절매/익절매 실행"""
        try:
            self.logger.info(f"{exit_reason} 조건 만족으로 포지션 청산")
            self.execute_sell_trade(current_price)
            
        except Exception as e:
            self.logger.error(f"포지션 청산 실패: {e}")
    
    def check_position_status(self):
        """포지션 상태 확인"""
        try:
            if not self.strategy.position:
                return
            
            current_price = self.binance_client.get_current_price(Config.SYMBOL)
            if not current_price:
                return
            
            # 손절매/익절매 확인
            sl_tp_result = self.strategy.check_stop_loss_take_profit(current_price)
            if sl_tp_result:
                self.execute_exit_trade(sl_tp_result, current_price)
            
            # 포지션 정보 로깅
            unrealized_pnl = 0
            if self.strategy.position == 'long':
                unrealized_pnl = (current_price - self.strategy.entry_price) * Config.TRADE_AMOUNT / current_price
            else:
                unrealized_pnl = (self.strategy.entry_price - current_price) * Config.TRADE_AMOUNT / current_price
            
            self.logger.info(f"포지션 상태: {self.strategy.position}, "
                           f"진입가: {self.strategy.entry_price:.2f}, "
                           f"현재가: {current_price:.2f}, "
                           f"미실현 손익: {unrealized_pnl:.2f} USDT")
            
        except Exception as e:
            self.logger.error(f"포지션 상태 확인 실패: {e}")
    
    def reset_daily_stats(self):
        """일일 통계 리셋"""
        self.logger.info("일일 통계 리셋")
        # 필요한 경우 일일 통계 초기화 로직 추가
    
    def get_trading_stats(self):
        """거래 통계 반환"""
        win_rate = 0
        if self.trade_stats['total_trades'] > 0:
            win_rate = (self.trade_stats['winning_trades'] / self.trade_stats['total_trades']) * 100
        
        return {
            **self.trade_stats,
            'win_rate': win_rate,
            'strategy_info': self.strategy.get_strategy_info(),
            'last_signal_time': self.last_signal_time
        }
    
    def emergency_stop(self):
        """긴급 중지 및 포지션 청산"""
        self.logger.warning("긴급 중지 실행")
        
        try:
            # 현재 포지션이 있으면 시장가로 청산
            if self.strategy.position:
                current_price = self.binance_client.get_current_price(Config.SYMBOL)
                if current_price:
                    self.execute_sell_trade(current_price)
            
            # 거래 중지
            self.stop_trading()
            
        except Exception as e:
            self.logger.error(f"긴급 중지 실행 중 오류: {e}")
