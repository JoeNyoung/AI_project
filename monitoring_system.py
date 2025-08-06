# monitoring_system.py

import logging
import smtplib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
from pathlib import Path

class SystemMonitor:
    """시스템 모니터링 및 알림"""
    
    def __init__(self):
        self.log_file = Path("logs/system_health.log")
        self.alert_history = Path("logs/alert_history.json")
        self.thresholds = {
            'crawling_success_rate': 0.8,  # 80% 이하시 알림
            'gpt_analysis_success_rate': 0.9,  # 90% 이하시 알림
            'daily_article_min': 20,  # 하루 20개 미만시 알림
            'response_time_max': 10.0,  # 10초 초과시 알림
        }
        
        # 이메일 설정 (선택사항)
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'sender_email': os.getenv('SENDER_EMAIL', ''),
            'sender_password': os.getenv('SENDER_PASSWORD', ''),
            'recipients': os.getenv('ALERT_RECIPIENTS', '').split(',')
        }
    
    def log_operation(self, operation: str, success: bool, details: Dict = None):
        """작업 결과 로깅"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'success': success,
            'details': details or {}
        }
        
        # 파일에 로깅
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # 콘솔 로깅
        level = logging.INFO if success else logging.ERROR
        logging.log(level, f"{operation}: {'성공' if success else '실패'} - {details}")
    
    def check_crawling_health(self) -> Dict:
        """크롤링 상태 검사"""
        try:
            # 최근 24시간 크롤링 로그 분석
            recent_logs = self._get_recent_logs('crawling', hours=24)
            
            if not recent_logs:
                return {
                    'status': 'warning',
                    'message': '최근 24시간 크롤링 기록 없음',
                    'success_rate': 0.0,
                    'article_count': 0
                }
            
            success_count = sum(1 for log in recent_logs if log['success'])
            total_count = len(recent_logs)
            success_rate = success_count / total_count
            
            # 수집된 기사 수 계산
            article_count = sum(
                log['details'].get('article_count', 0) 
                for log in recent_logs if log['success']
            )
            
            status = 'healthy'
            messages = []
            
            if success_rate < self.thresholds['crawling_success_rate']:
                status = 'critical'
                messages.append(f'크롤링 성공률 {success_rate:.1%} (임계값: {self.thresholds["crawling_success_rate"]:.1%})')
            
            if article_count < self.thresholds['daily_article_min']:
                status = 'warning'
                messages.append(f'일간 기사 수 {article_count}개 (최소: {self.thresholds["daily_article_min"]}개)')
            
            return {
                'status': status,
                'message': '; '.join(messages) if messages else '정상',
                'success_rate': success_rate,
                'article_count': article_count,
                'details': {
                    'total_attempts': total_count,
                    'successful_attempts': success_count
                }
            }
            
        except Exception as e:
            logging.error(f"크롤링 상태 검사 실패: {e}")
            return {
                'status': 'error',
                'message': f'상태 검사 실패: {str(e)}',
                'success_rate': 0.0,
                'article_count': 0
            }
    
    def check_gpt_analysis_health(self) -> Dict:
        """GPT 분석 상태 검사"""
        try:
            recent_logs = self._get_recent_logs('gpt_analysis', hours=24)
            
            if not recent_logs:
                return {
                    'status': 'warning',
                    'message': '최근 24시간 GPT 분석 기록 없음',
                    'success_rate': 0.0
                }
            
            success_count = sum(1 for log in recent_logs if log['success'])
            total_count = len(recent_logs)
            success_rate = success_count / total_count
            
            # 평균 응답 시간 계산
            response_times = [
                log['details'].get('response_time', 0) 
                for log in recent_logs if log['success']
            ]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            status = 'healthy'
            messages = []
            
            if success_rate < self.thresholds['gpt_analysis_success_rate']:
                status = 'critical'
                messages.append(f'GPT 분석 성공률 {success_rate:.1%} (임계값: {self.thresholds["gpt_analysis_success_rate"]:.1%})')
            
            if avg_response_time > self.thresholds['response_time_max']:
                status = 'warning'
                messages.append(f'평균 응답시간 {avg_response_time:.1f}초 (임계값: {self.thresholds["response_time_max"]}초)')
            
            return {
                'status': status,
                'message': '; '.join(messages) if messages else '정상',
                'success_rate': success_rate,
                'avg_response_time': avg_response_time,
                'details': {
                    'total_requests': total_count,
                    'successful_requests': success_count
                }
            }
            
        except Exception as e:
            logging.error(f"GPT 분석 상태 검사 실패: {e}")
            return {
                'status': 'error',
                'message': f'상태 검사 실패: {str(e)}',
                'success_rate': 0.0
            }
    
    def check_system_resources(self) -> Dict:
        """시스템 리소스 상태 검사"""
        try:
            import psutil
            
            # CPU, 메모리, 디스크 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = 'healthy'
            messages = []
            
            if cpu_percent > 80:
                status = 'warning'
                messages.append(f'CPU 사용률 높음 ({cpu_percent:.1f}%)')
            
            if memory.percent > 85:
                status = 'warning'
                messages.append(f'메모리 사용률 높음 ({memory.percent:.1f}%)')
            
            if disk.percent > 90:
                status = 'critical'
                messages.append(f'디스크 사용률 높음 ({disk.percent:.1f}%)')
            
            return {
                'status': status,
                'message': '; '.join(messages) if messages else '정상',
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            }
            
        except ImportError:
            return {
                'status': 'info',
                'message': 'psutil 미설치로 리소스 모니터링 불가',
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'리소스 검사 실패: {str(e)}',
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0
            }
    
    def run_health_check(self) -> Dict:
        """전체 시스템 상태 검사"""
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {}
        }
        
        # 각 컴포넌트 검사
        checks = {
            'crawling': self.check_crawling_health,
            'gpt_analysis': self.check_gpt_analysis_health,
            'system_resources': self.check_system_resources
        }
        
        critical_count = 0
        warning_count = 0
        
        for component, check_func in checks.items():
            try:
                result = check_func()
                health_report['components'][component] = result
                
                if result['status'] == 'critical':
                    critical_count += 1
                elif result['status'] in ['warning', 'error']:
                    warning_count += 1
                    
            except Exception as e:
                health_report['components'][component] = {
                    'status': 'error',
                    'message': f'검사 실패: {str(e)}'
                }
                critical_count += 1
        
        # 전체 상태 결정
        if critical_count > 0:
            health_report['overall_status'] = 'critical'
        elif warning_count > 0:
            health_report['overall_status'] = 'warning'
        
        # 알림 필요시 발송
        if health_report['overall_status'] in ['critical', 'warning']:
            self._send_alert(health_report)
        
        return health_report
    
    def _get_recent_logs(self, operation: str, hours: int = 24) -> List[Dict]:
        """최근 로그 가져오기"""
        if not self.log_file.exists():
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = datetime.fromisoformat(log_entry['timestamp'])
                        
                        if (log_time >= cutoff_time and 
                            log_entry['operation'] == operation):
                            recent_logs.append(log_entry)
                            
                    except (json.JSONDecodeError, ValueError):
                        continue
                        
        except Exception as e:
            logging.error(f"로그 파일 읽기 실패: {e}")
        
        return recent_logs
    
    def _send_alert(self, health_report: Dict):
        """알림 발송 (이메일/로그)"""
        alert_message = self._format_alert_message(health_report)
        
        # 콘솔 및 로그 파일에 알림
        logging.warning(f"시스템 알림: {health_report['overall_status'].upper()}")
        logging.warning(alert_message)
        
        # 알림 기록 저장
        self._save_alert_history(health_report)
        
        # 이메일 알림 (설정되어 있는 경우)
        if self._is_email_configured():
            try:
                self._send_email_alert(alert_message, health_report['overall_status'])
                logging.info("이메일 알림 발송 완료")
            except Exception as e:
                logging.error(f"이메일 알림 발송 실패: {e}")
    
    def _format_alert_message(self, health_report: Dict) -> str:
        """알림 메시지 포맷팅"""
        status = health_report['overall_status']
        timestamp = health_report['timestamp']
        
        message = f"🚨 시스템 상태 알림 - {status.upper()}\n"
        message += f"시간: {timestamp}\n\n"
        
        for component, result in health_report['components'].items():
            status_emoji = {
                'healthy': '✅',
                'warning': '⚠️',
                'critical': '🔴',
                'error': '❌',
                'info': 'ℹ️'
            }.get(result['status'], '❓')
            
            message += f"{status_emoji} {component}: {result['message']}\n"
        
        return message
    
    def _save_alert_history(self, health_report: Dict):
        """알림 기록 저장"""
        try:
            alert_record = {
                'timestamp': health_report['timestamp'],
                'status': health_report['overall_status'],
                'components': {
                    comp: result['status'] 
                    for comp, result in health_report['components'].items()
                }
            }
            
            # 기존 기록 읽기
            if self.alert_history.exists():
                with open(self.alert_history, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []
            
            # 새 기록 추가
            history.append(alert_record)
            
            # 최근 100개만 유지
            if len(history) > 100:
                history = history[-100:]
            
            # 저장
            with open(self.alert_history, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging.error(f"알림 기록 저장 실패: {e}")
    
    def _is_email_configured(self) -> bool:
        """이메일 설정 확인"""
        return (
            self.email_config['sender_email'] and 
            self.email_config['sender_password'] and 
            any(self.email_config['recipients'])
        )
    
    def _send_email_alert(self, message: str, status: str):
        """이메일 알림 발송"""
        if not self._is_email_configured():
            return
        
        # 이메일 구성
        msg = MIMEMultipart()
        msg['From'] = self.email_config['sender_email']
        msg['To'] = ', '.join(self.email_config['recipients'])
        msg['Subject'] = f"[해운뉴스시스템] {status.upper()} 알림"
        
        # HTML 메시지 구성
        html_message = f"""
        <html>
        <body>
            <h2>시스템 상태 알림</h2>
            <div style="background-color: {'#ffebee' if status == 'critical' else '#fff3e0'}; 
                        padding: 15px; border-radius: 5px; margin: 10px 0;">
                <pre style="font-family: Arial, sans-serif; white-space: pre-wrap;">
{message}
                </pre>
            </div>
            <p><small>이 알림은 해운뉴스 RAG 시스템에서 자동 발송되었습니다.</small></p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_message, 'html', 'utf-8'))
        
        # SMTP 발송
        try:
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['sender_email'], self.email_config['sender_password'])
            server.send_message(msg)
            server.quit()
        except Exception as e:
            raise Exception(f"SMTP 발송 실패: {e}")
    
    def get_alert_history(self, days: int = 7) -> List[Dict]:
        """최근 알림 기록 조회"""
        if not self.alert_history.exists():
            return []
        
        try:
            with open(self.alert_history, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 최근 N일 필터링
            cutoff_time = datetime.now() - timedelta(days=days)
            recent_alerts = []
            
            for alert in history:
                alert_time = datetime.fromisoformat(alert['timestamp'])
                if alert_time >= cutoff_time:
                    recent_alerts.append(alert)
            
            return recent_alerts
            
        except Exception as e:
            logging.error(f"알림 기록 조회 실패: {e}")
            return []

# 전역 모니터 인스턴스
system_monitor = SystemMonitor()

# 데코레이터로 작업 모니터링
def monitor_operation(operation_name: str):
    """작업 모니터링 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 성공 로깅
                system_monitor.log_operation(
                    operation_name, 
                    True, 
                    {
                        'duration': duration,
                        'result_count': len(result) if isinstance(result, (list, dict)) else 1
                    }
                )
                return result
                
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 실패 로깅
                system_monitor.log_operation(
                    operation_name, 
                    False, 
                    {
                        'duration': duration,
                        'error': str(e),
                        'error_type': type(e).__name__
                    }
                )
                raise
        return wrapper
    return decorator

# 사용 예시: 기존 함수들에 모니터링 추가
"""
# crawler_utils.py에 추가
@monitor_operation('crawling')
def crawl_tradewinds(max_articles):
    # 기존 코드...

# analyzer.py에 추가  
@monitor_operation('gpt_analysis')
def analyze_article(article):
    # 기존 코드...
"""