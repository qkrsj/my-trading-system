#!/usr/bin/env python3
"""
Binance 자동화 거래 시스템 - 메인 실행 파일
이동평균선 골든크로스 전략을 사용한 BTC 자동 거래
"""

import sys
import signal
import time
import threading
from datetime import datetime
import logging

from config import Config
from trading_engine import TradingEngine
from monitor import TradingMonitor
from logger import logger

class TradingSystem:
    def __init__(self):
        """거래 시스템 초기화"""
        self.trading_engine = TradingEngine()
        self.monitor = TradingMonitor(self.trading_engine)
        self.is_running = False
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 등)"""
        logger.info(f"시그널 {signum} 수신, 시스템 종료 중...")
        self.stop_system()
        sys.exit(0)
    
    def start_system(self):
        """거래 시스템 시작"""
        try:
            logger.info("=" * 50)
            logger.info("Binance 자동화 거래 시스템 시작")
            logger.info("=" * 50)
            
            # 설정 검증
            Config.validate_config()
            logger.info("설정 검증 완료")
            
            # 시스템 시작
            self.is_running = True
            
            # 모니터링 스레드 시작
            monitor_thread = threading.Thread(target=self.monitor.start_monitoring)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # 거래 엔진 시작
            success = self.trading_engine.start_trading()
            
            if success:
                logger.info("거래 시스템이 성공적으로 시작되었습니다")
                self.run_main_loop()
            else:
                logger.error("거래 시스템 시작 실패")
                self.stop_system()
                
        except Exception as e:
            logger.error(f"시스템 시작 중 오류 발생: {e}")
            self.stop_system()
    
    def stop_system(self):
        """거래 시스템 중지"""
        logger.info("거래 시스템 중지 중...")
        
        self.is_running = False
        
        # 거래 엔진 중지
        self.trading_engine.stop_trading()
        
        # 모니터링 중지
        self.monitor.stop_monitoring()
        
        # 최종 보고서 생성
        self.generate_final_report()
        
        logger.info("거래 시스템이 안전하게 중지되었습니다")
    
    def run_main_loop(self):
        """메인 실행 루프"""
        try:
            while self.is_running:
                # 시스템 상태 확인
                self.check_system_status()
                
                # 1분마다 상태 체크
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 시스템 중지 요청")
            self.stop_system()
        except Exception as e:
            logger.error(f"메인 루프 오류: {e}")
            self.stop_system()
    
    def check_system_status(self):
        """시스템 상태 확인"""
        try:
            # 거래 통계 출력
            stats = self.trading_engine.get_trading_stats()
            
            logger.info(f"거래 통계 - 총 거래: {stats['total_trades']}, "
                       f"승률: {stats.get('win_rate', 0):.1f}%, "
                       f"총 수익: {stats['total_profit']:.2f} USDT")
            
            # 모니터링 요약 출력
            monitor_summary = self.monitor.get_monitoring_summary()
            
            if monitor_summary['active_alerts'] > 0:
                logger.warning(f"활성 알림: {monitor_summary['active_alerts']}개")
            
            # 시스템 가동 시간
            uptime = monitor_summary['uptime_hours']
            logger.info(f"시스템 가동 시간: {uptime:.1f}시간")
            
        except Exception as e:
            logger.error(f"시스템 상태 확인 실패: {e}")
    
    def generate_final_report(self):
        """최종 보고서 생성"""
        try:
            report = self.monitor.generate_report()
            
            if report:
                logger.info("=" * 50)
                logger.info("최종 거래 보고서")
                logger.info("=" * 50)
                logger.info(f"거래 기간: {report['trading_period']['duration_hours']:.1f}시간")
                logger.info(f"총 거래 횟수: {report['performance_summary']['total_trades']}")
                logger.info(f"승률: {report['performance_summary']['win_rate']:.1f}%")
                logger.info(f"총 수익: {report['performance_summary']['total_profit']:.2f} USDT")
                logger.info(f"최대 손실: {report['performance_summary']['max_drawdown']:.2f}%")
                logger.info("=" * 50)
            
        except Exception as e:
            logger.error(f"최종 보고서 생성 실패: {e}")

def main():
    """메인 함수"""
    try:
        # 거래 시스템 인스턴스 생성
        trading_system = TradingSystem()
        
        # 시스템 시작
        trading_system.start_system()
        
    except Exception as e:
        logger.error(f"시스템 실행 중 치명적 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
