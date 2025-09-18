#!/usr/bin/env python3
"""
백테스팅 시스템
과거 데이터를 사용하여 거래 전략의 성과를 검증
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from binance_client import BinanceClient
from trading_strategy import GoldenCrossStrategy
from config import Config

class BacktestEngine:
    def __init__(self, initial_balance=10000):
        """
        백테스팅 엔진 초기화
        
        Args:
            initial_balance (float): 초기 자본
        """
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        
        self.trades = []
        self.equity_curve = []
        
        self.logger = logging.getLogger(__name__)
        
        # 백테스팅 결과
        self.results = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0
        }
    
    def run_backtest(self, symbol, timeframe, start_date, end_date):
        """
        백테스팅 실행
        
        Args:
            symbol (str): 거래 심볼
            timeframe (str): 시간 프레임
            start_date (str): 시작 날짜 (YYYY-MM-DD)
            end_date (str): 종료 날짜 (YYYY-MM-DD)
        """
        try:
            self.logger.info(f"백테스팅 시작: {symbol} {timeframe} ({start_date} ~ {end_date})")
            
            # 전략 초기화
            strategy = GoldenCrossStrategy(
                short_period=Config.SHORT_MA_PERIOD,
                long_period=Config.LONG_MA_PERIOD
            )
            
            # 과거 데이터 가져오기
            df = self.get_historical_data(symbol, timeframe, start_date, end_date)
            
            if df is None or len(df) < strategy.long_period:
                self.logger.error("데이터 부족으로 백테스팅 불가")
                return None
            
            # 지표 계산
            df = strategy.calculate_indicators(df)
            df = strategy.generate_signals(df)
            
            # 백테스팅 실행
            self.execute_backtest(df, strategy)
            
            # 결과 계산
            self.calculate_results()
            
            # 결과 출력
            self.print_results()
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"백테스팅 실행 실패: {e}")
            return None
    
    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        """과거 데이터 가져오기"""
        try:
            # 실제 구현에서는 Binance API를 사용하여 데이터를 가져옴
            # 여기서는 예시로 더미 데이터 생성
            self.logger.info("과거 데이터 가져오기...")
            
            # 날짜 범위 생성
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            
            # 시간 프레임에 따른 주기 설정
            if timeframe == '1h':
                freq = 'H'
            elif timeframe == '4h':
                freq = '4H'
            elif timeframe == '1d':
                freq = 'D'
            else:
                freq = 'H'
            
            # 더미 데이터 생성 (실제로는 API에서 가져와야 함)
            dates = pd.date_range(start=start, end=end, freq=freq)
            
            # 랜덤 가격 데이터 생성 (실제로는 OHLCV 데이터)
            np.random.seed(42)
            base_price = 50000  # BTC 기준 가격
            returns = np.random.normal(0, 0.02, len(dates))  # 2% 변동성
            
            prices = [base_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # OHLCV 데이터 생성
            data = []
            for i, (date, price) in enumerate(zip(dates, prices)):
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                open_price = prices[i-1] if i > 0 else price
                volume = np.random.uniform(100, 1000)
                
                data.append({
                    'timestamp': date,
                    'open': open_price,
                    'high': high,
                    'low': low,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            self.logger.info(f"데이터 로드 완료: {len(df)}개 캔들")
            return df
            
        except Exception as e:
            self.logger.error(f"과거 데이터 가져오기 실패: {e}")
            return None
    
    def execute_backtest(self, df, strategy):
        """백테스팅 실행"""
        try:
            self.logger.info("백테스팅 실행 중...")
            
            for i in range(strategy.long_period, len(df)):
                current_price = df.iloc[i]['close']
                current_time = df.index[i]
                
                # 손절매/익절매 확인
                if self.position:
                    if self.check_exit_conditions(current_price, current_time):
                        continue
                
                # 매수 신호 확인
                if strategy.should_buy(df, i) and not self.position:
                    self.execute_buy(current_price, current_time)
                
                # 매도 신호 확인
                elif strategy.should_sell(df, i) and self.position:
                    self.execute_sell(current_price, current_time)
                
                # 자본 곡선 업데이트
                self.update_equity_curve(current_price, current_time)
            
            # 마지막 포지션 정리
            if self.position:
                final_price = df.iloc[-1]['close']
                final_time = df.index[-1]
                self.execute_sell(final_price, final_time)
            
            self.logger.info(f"백테스팅 완료: {len(self.trades)}개 거래 실행")
            
        except Exception as e:
            self.logger.error(f"백테스팅 실행 실패: {e}")
    
    def execute_buy(self, price, timestamp):
        """매수 실행"""
        try:
            # 거래 수량 계산 (잔고의 90% 사용)
            trade_amount = self.balance * 0.9
            self.position_size = trade_amount / price
            
            self.position = 'long'
            self.entry_price = price
            self.balance -= trade_amount
            
            trade = {
                'timestamp': timestamp,
                'type': 'buy',
                'price': price,
                'size': self.position_size,
                'amount': trade_amount,
                'balance': self.balance
            }
            
            self.trades.append(trade)
            self.logger.debug(f"매수: {price:.2f} @ {timestamp}")
            
        except Exception as e:
            self.logger.error(f"매수 실행 실패: {e}")
    
    def execute_sell(self, price, timestamp):
        """매도 실행"""
        try:
            if not self.position:
                return
            
            # 거래 금액 계산
            trade_amount = self.position_size * price
            self.balance += trade_amount
            
            # 수익/손실 계산
            if self.position == 'long':
                profit = trade_amount - (self.position_size * self.entry_price)
            else:
                profit = (self.position_size * self.entry_price) - trade_amount
            
            trade = {
                'timestamp': timestamp,
                'type': 'sell',
                'price': price,
                'size': self.position_size,
                'amount': trade_amount,
                'profit': profit,
                'balance': self.balance
            }
            
            self.trades.append(trade)
            
            # 통계 업데이트
            self.results['total_trades'] += 1
            if profit > 0:
                self.results['winning_trades'] += 1
            else:
                self.results['losing_trades'] += 1
            
            self.logger.debug(f"매도: {price:.2f} @ {timestamp}, 수익: {profit:.2f}")
            
            # 포지션 초기화
            self.position = None
            self.position_size = 0
            self.entry_price = 0
            
        except Exception as e:
            self.logger.error(f"매도 실행 실패: {e}")
    
    def check_exit_conditions(self, current_price, timestamp):
        """손절매/익절매 조건 확인"""
        try:
            if not self.position:
                return False
            
            # 손절매/익절매 계산
            if self.position == 'long':
                stop_loss = self.entry_price * (1 - Config.STOP_LOSS_PERCENT / 100)
                take_profit = self.entry_price * (1 + Config.TAKE_PROFIT_PERCENT / 100)
                
                if current_price <= stop_loss or current_price >= take_profit:
                    self.execute_sell(current_price, timestamp)
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"청산 조건 확인 실패: {e}")
            return False
    
    def update_equity_curve(self, current_price, timestamp):
        """자본 곡선 업데이트"""
        try:
            # 현재 자본 계산
            if self.position:
                if self.position == 'long':
                    current_equity = self.balance + (self.position_size * current_price)
                else:
                    current_equity = self.balance - (self.position_size * current_price)
            else:
                current_equity = self.balance
            
            self.equity_curve.append({
                'timestamp': timestamp,
                'equity': current_equity,
                'price': current_price
            })
            
        except Exception as e:
            self.logger.error(f"자본 곡선 업데이트 실패: {e}")
    
    def calculate_results(self):
        """백테스팅 결과 계산"""
        try:
            if not self.trades:
                self.logger.warning("거래 내역이 없습니다")
                return
            
            # 총 수익률
            self.results['total_return'] = ((self.balance - self.initial_balance) / self.initial_balance) * 100
            
            # 승률
            if self.results['total_trades'] > 0:
                self.results['win_rate'] = (self.results['winning_trades'] / self.results['total_trades']) * 100
            
            # 최대 낙폭 계산
            self.calculate_max_drawdown()
            
            # 샤프 비율 계산
            self.calculate_sharpe_ratio()
            
            # 수익 팩터 계산
            self.calculate_profit_factor()
            
        except Exception as e:
            self.logger.error(f"결과 계산 실패: {e}")
    
    def calculate_max_drawdown(self):
        """최대 낙폭 계산"""
        try:
            if not self.equity_curve:
                return
            
            equity_values = [point['equity'] for point in self.equity_curve]
            peak = equity_values[0]
            max_dd = 0
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak * 100
                if drawdown > max_dd:
                    max_dd = drawdown
            
            self.results['max_drawdown'] = max_dd
            
        except Exception as e:
            self.logger.error(f"최대 낙폭 계산 실패: {e}")
    
    def calculate_sharpe_ratio(self):
        """샤프 비율 계산"""
        try:
            if len(self.equity_curve) < 2:
                return
            
            # 일일 수익률 계산
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev_equity = self.equity_curve[i-1]['equity']
                curr_equity = self.equity_curve[i]['equity']
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)
            
            if returns:
                mean_return = np.mean(returns)
                std_return = np.std(returns)
                
                if std_return > 0:
                    # 무위험 수익률을 0으로 가정
                    self.results['sharpe_ratio'] = mean_return / std_return * np.sqrt(252)  # 연환산
            
        except Exception as e:
            self.logger.error(f"샤프 비율 계산 실패: {e}")
    
    def calculate_profit_factor(self):
        """수익 팩터 계산"""
        try:
            winning_profits = []
            losing_profits = []
            
            for trade in self.trades:
                if trade['type'] == 'sell' and 'profit' in trade:
                    if trade['profit'] > 0:
                        winning_profits.append(trade['profit'])
                    else:
                        losing_profits.append(abs(trade['profit']))
            
            total_wins = sum(winning_profits) if winning_profits else 0
            total_losses = sum(losing_profits) if losing_profits else 0
            
            if total_losses > 0:
                self.results['profit_factor'] = total_wins / total_losses
            
        except Exception as e:
            self.logger.error(f"수익 팩터 계산 실패: {e}")
    
    def print_results(self):
        """결과 출력"""
        try:
            print("\n" + "="*50)
            print("백테스팅 결과")
            print("="*50)
            print(f"초기 자본: {self.initial_balance:,.2f} USDT")
            print(f"최종 자본: {self.balance:,.2f} USDT")
            print(f"총 수익률: {self.results['total_return']:.2f}%")
            print(f"총 거래 횟수: {self.results['total_trades']}")
            print(f"승리 거래: {self.results['winning_trades']}")
            print(f"패배 거래: {self.results['losing_trades']}")
            print(f"승률: {self.results['win_rate']:.2f}%")
            print(f"최대 낙폭: {self.results['max_drawdown']:.2f}%")
            print(f"샤프 비율: {self.results['sharpe_ratio']:.2f}")
            print(f"수익 팩터: {self.results['profit_factor']:.2f}")
            print("="*50)
            
        except Exception as e:
            self.logger.error(f"결과 출력 실패: {e}")

def main():
    """백테스팅 메인 함수"""
    try:
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 백테스팅 엔진 생성
        backtest = BacktestEngine(initial_balance=Config.INITIAL_BALANCE)
        
        # 백테스팅 실행
        results = backtest.run_backtest(
            symbol=Config.SYMBOL,
            timeframe=Config.TIMEFRAME,
            start_date=Config.BACKTEST_START_DATE,
            end_date=Config.BACKTEST_END_DATE
        )
        
        if results:
            print("\n백테스팅이 성공적으로 완료되었습니다.")
        else:
            print("\n백테스팅 실행에 실패했습니다.")
            
    except Exception as e:
        print(f"백테스팅 실행 중 오류: {e}")

if __name__ == "__main__":
    main()
