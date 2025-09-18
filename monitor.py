import time
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import logging
from trading_engine import TradingEngine
from logger import logger

class TradingMonitor:
    def __init__(self, trading_engine):
        """
        거래 모니터링 시스템 초기화
        
        Args:
            trading_engine (TradingEngine): 거래 엔진 인스턴스
        """
        self.trading_engine = trading_engine
        self.logger = logging.getLogger(__name__)
        
        # 모니터링 데이터 저장
        self.monitoring_data = {
            'start_time': datetime.now(),
            'last_update': datetime.now(),
            'system_status': 'stopped',
            'trades_history': [],
            'performance_metrics': {},
            'alerts': []
        }
        
        # 알림 임계값
        self.alert_thresholds = {
            'max_drawdown': 10.0,  # 최대 손실 10%
            'consecutive_losses': 5,  # 연속 손실 5회
            'low_balance': 100.0,  # 잔고 100 USDT 미만
            'api_errors': 10  # API 오류 10회
        }
        
        # 오류 카운터
        self.error_counters = {
            'api_errors': 0,
            'consecutive_losses': 0,
            'last_reset_time': datetime.now()
        }
    
    def start_monitoring(self):
        """모니터링 시작"""
        self.logger.info("거래 모니터링 시작")
        self.monitoring_data['system_status'] = 'running'
        self.monitoring_data['start_time'] = datetime.now()
        
        # 모니터링 루프 시작
        self.run_monitoring_loop()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.logger.info("거래 모니터링 중지")
        self.monitoring_data['system_status'] = 'stopped'
        self.monitoring_data['last_update'] = datetime.now()
    
    def run_monitoring_loop(self):
        """모니터링 루프 실행"""
        while self.trading_engine.is_running:
            try:
                # 시스템 상태 확인
                self.check_system_health()
                
                # 성과 지표 업데이트
                self.update_performance_metrics()
                
                # 알림 확인
                self.check_alerts()
                
                # 데이터 저장
                self.save_monitoring_data()
                
                # 5분마다 모니터링
                time.sleep(300)
                
            except Exception as e:
                self.logger.error(f"모니터링 루프 오류: {e}")
                time.sleep(60)  # 오류 발생 시 1분 대기
    
    def check_system_health(self):
        """시스템 상태 확인"""
        try:
            # API 연결 상태 확인
            balance = self.trading_engine.binance_client.get_account_balance()
            if not balance:
                self.error_counters['api_errors'] += 1
                self.add_alert('api_error', f"API 연결 실패 (오류 횟수: {self.error_counters['api_errors']})")
            else:
                self.error_counters['api_errors'] = 0
            
            # 잔고 확인
            usdt_balance = balance.get('USDT', {}).get('free', 0) if balance else 0
            if usdt_balance < self.alert_thresholds['low_balance']:
                self.add_alert('low_balance', f"잔고 부족: {usdt_balance} USDT")
            
            # 거래 엔진 상태 확인
            if not self.trading_engine.is_running:
                self.add_alert('engine_stopped', "거래 엔진이 중지됨")
            
        except Exception as e:
            self.logger.error(f"시스템 상태 확인 실패: {e}")
    
    def update_performance_metrics(self):
        """성과 지표 업데이트"""
        try:
            stats = self.trading_engine.get_trading_stats()
            
            # 성과 지표 계산
            metrics = {
                'total_trades': stats['total_trades'],
                'winning_trades': stats['winning_trades'],
                'losing_trades': stats['losing_trades'],
                'win_rate': stats.get('win_rate', 0),
                'total_profit': stats['total_profit'],
                'current_drawdown': stats['current_drawdown'],
                'max_drawdown': stats['max_drawdown'],
                'last_update': datetime.now()
            }
            
            self.monitoring_data['performance_metrics'] = metrics
            
            # 연속 손실 확인
            if stats['losing_trades'] > 0:
                recent_trades = self.get_recent_trades(10)
                consecutive_losses = self.count_consecutive_losses(recent_trades)
                self.error_counters['consecutive_losses'] = consecutive_losses
                
                if consecutive_losses >= self.alert_thresholds['consecutive_losses']:
                    self.add_alert('consecutive_losses', 
                                 f"연속 손실 {consecutive_losses}회 발생")
            
            # 최대 손실 확인
            if stats['max_drawdown'] > self.alert_thresholds['max_drawdown']:
                self.add_alert('max_drawdown', 
                             f"최대 손실 {stats['max_drawdown']:.2f}% 초과")
            
        except Exception as e:
            self.logger.error(f"성과 지표 업데이트 실패: {e}")
    
    def check_alerts(self):
        """알림 확인 및 처리"""
        try:
            current_time = datetime.now()
            
            # 1시간 이상 된 알림 제거
            self.monitoring_data['alerts'] = [
                alert for alert in self.monitoring_data['alerts']
                if (current_time - alert['timestamp']).seconds < 3600
            ]
            
            # 새로운 알림이 있으면 로깅
            for alert in self.monitoring_data['alerts']:
                if alert.get('notified', False) == False:
                    self.logger.warning(f"알림: {alert['message']}")
                    alert['notified'] = True
            
        except Exception as e:
            self.logger.error(f"알림 확인 실패: {e}")
    
    def add_alert(self, alert_type, message):
        """알림 추가"""
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now(),
            'notified': False
        }
        
        # 중복 알림 방지
        existing_alerts = [a for a in self.monitoring_data['alerts'] 
                          if a['type'] == alert_type and 
                          (datetime.now() - a['timestamp']).seconds < 300]
        
        if not existing_alerts:
            self.monitoring_data['alerts'].append(alert)
    
    def get_recent_trades(self, limit=10):
        """최근 거래 내역 조회"""
        try:
            # 실제 구현에서는 거래 엔진에서 거래 내역을 가져와야 함
            # 여기서는 예시로 빈 리스트 반환
            return []
        except Exception as e:
            self.logger.error(f"최근 거래 내역 조회 실패: {e}")
            return []
    
    def count_consecutive_losses(self, trades):
        """연속 손실 횟수 계산"""
        consecutive_losses = 0
        
        for trade in reversed(trades):
            if trade.get('profit', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        return consecutive_losses
    
    def save_monitoring_data(self):
        """모니터링 데이터 저장"""
        try:
            # 데이터 디렉토리 생성
            data_dir = 'monitoring_data'
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # JSON 파일로 저장
            filename = f"monitoring_data_{datetime.now().strftime('%Y%m%d')}.json"
            filepath = os.path.join(data_dir, filename)
            
            # datetime 객체를 문자열로 변환
            data_to_save = self.monitoring_data.copy()
            data_to_save['start_time'] = data_to_save['start_time'].isoformat()
            data_to_save['last_update'] = data_to_save['last_update'].isoformat()
            
            for alert in data_to_save['alerts']:
                alert['timestamp'] = alert['timestamp'].isoformat()
            
            if 'last_update' in data_to_save['performance_metrics']:
                data_to_save['performance_metrics']['last_update'] = \
                    data_to_save['performance_metrics']['last_update'].isoformat()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            self.logger.error(f"모니터링 데이터 저장 실패: {e}")
    
    def generate_report(self):
        """거래 보고서 생성"""
        try:
            stats = self.trading_engine.get_trading_stats()
            
            report = {
                'report_date': datetime.now().isoformat(),
                'trading_period': {
                    'start_time': self.monitoring_data['start_time'].isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'duration_hours': (datetime.now() - self.monitoring_data['start_time']).total_seconds() / 3600
                },
                'performance_summary': {
                    'total_trades': stats['total_trades'],
                    'winning_trades': stats['winning_trades'],
                    'losing_trades': stats['losing_trades'],
                    'win_rate': stats.get('win_rate', 0),
                    'total_profit': stats['total_profit'],
                    'max_drawdown': stats['max_drawdown']
                },
                'system_status': {
                    'status': self.monitoring_data['system_status'],
                    'api_errors': self.error_counters['api_errors'],
                    'consecutive_losses': self.error_counters['consecutive_losses'],
                    'active_alerts': len([a for a in self.monitoring_data['alerts'] if not a.get('notified', False)])
                },
                'strategy_info': stats.get('strategy_info', {})
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"보고서 생성 실패: {e}")
            return None
    
    def get_monitoring_summary(self):
        """모니터링 요약 정보 반환"""
        return {
            'system_status': self.monitoring_data['system_status'],
            'uptime_hours': (datetime.now() - self.monitoring_data['start_time']).total_seconds() / 3600,
            'active_alerts': len([a for a in self.monitoring_data['alerts'] if not a.get('notified', False)]),
            'performance_metrics': self.monitoring_data['performance_metrics'],
            'error_counters': self.error_counters
        }
