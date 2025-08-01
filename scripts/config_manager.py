#!/usr/bin/env python3
"""
매개변수 설정 파일 생성 및 관리 시스템
설정 파일 생성, 읽기, 수정, 검증 기능
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# 상위 디렉토리 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class ConfigManager:
    """설정 파일 관리자"""
    
    def __init__(self, config_dir='config'):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.default_config_file = self.config_dir / 'default_config.json'
        self.user_config_file = self.config_dir / 'user_config.json'
        self.backup_dir = self.config_dir / 'backups'
        self.backup_dir.mkdir(exist_ok=True)
    
    def load_config(self, config_file: Optional[Path] = None) -> Dict[str, Any]:
        """설정 파일 로드"""
        if config_file is None:
            # 사용자 설정이 있으면 우선 사용, 없으면 기본 설정 사용
            if self.user_config_file.exists():
                config_file = self.user_config_file
            else:
                config_file = self.default_config_file
        
        try:
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"⚠️ 설정 파일이 없습니다: {config_file}")
                return {}
        except Exception as e:
            print(f"❌ 설정 파일 로드 오류: {str(e)}")
            return {}
    
    def save_config(self, config: Dict[str, Any], config_file: Optional[Path] = None) -> bool:
        """설정 파일 저장"""
        if config_file is None:
            config_file = self.user_config_file
        
        try:
            # 기존 파일 백업
            if config_file.exists():
                self.backup_config(config_file)
            
            # 새 설정 저장
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 설정이 저장되었습니다: {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ 설정 저장 오류: {str(e)}")
            return False
    
    def backup_config(self, config_file: Path) -> bool:
        """설정 파일 백업"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{config_file.stem}_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            # 백업 파일 복사
            import shutil
            shutil.copy2(config_file, backup_path)
            
            print(f"💾 설정 파일이 백업되었습니다: {backup_path}")
            return True
            
        except Exception as e:
            print(f"⚠️ 백업 실패: {str(e)}")
            return False
    
    def get_config_value(self, key_path: str, default=None) -> Any:
        """설정 값 조회 (점 표기법 지원)"""
        config = self.load_config()
        
        keys = key_path.split('.')
        value = config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_config_value(self, key_path: str, value: Any) -> bool:
        """설정 값 수정 (점 표기법 지원)"""
        config = self.load_config()
        
        keys = key_path.split('.')
        current = config
        
        try:
            # 중간 경로까지 이동
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # 최종 값 설정
            current[keys[-1]] = value
            
            return self.save_config(config)
            
        except Exception as e:
            print(f"❌ 설정 값 수정 오류: {str(e)}")
            return False
    
    def validate_config(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """설정 검증"""
        if config is None:
            config = self.load_config()
        
        issues = []
        warnings = []
        
        # 필수 섹션 확인
        required_sections = [
            'trading_system', 'database', 'data_collection',
            'technical_analysis', 'trading_signals', 'risk_management'
        ]
        
        for section in required_sections:
            if section not in config:
                issues.append(f"필수 섹션이 없습니다: {section}")
        
        # 데이터베이스 설정 검증
        if 'database' in config:
            db_config = config['database']
            if 'path' not in db_config:
                issues.append("데이터베이스 경로가 설정되지 않았습니다")
            elif not db_config['path'].endswith('.db'):
                warnings.append("데이터베이스 파일 확장자가 .db가 아닙니다")
        
        # 리스크 관리 설정 검증
        if 'risk_management' in config:
            risk_config = config['risk_management']
            
            if risk_config.get('max_position_size_percent', 0) > 50:
                warnings.append("최대 포지션 크기가 50%를 초과합니다")
            
            if risk_config.get('stop_loss_percent', 0) > 20:
                warnings.append("손절매 비율이 20%를 초과합니다")
        
        # 기술적 분석 설정 검증
        if 'technical_analysis' in config:
            ta_config = config['technical_analysis']
            
            if 'rsi' in ta_config:
                rsi_config = ta_config['rsi']
                overbought = rsi_config.get('overbought', 70)
                oversold = rsi_config.get('oversold', 30)
                
                if overbought <= oversold:
                    issues.append("RSI 과매수 임계값이 과매도 임계값보다 작거나 같습니다")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        }
    
    def create_user_config(self, overrides: Optional[Dict[str, Any]] = None) -> bool:
        """사용자 설정 파일 생성"""
        try:
            # 기본 설정 로드
            default_config = self.load_config(self.default_config_file)
            
            if not default_config:
                print("❌ 기본 설정 파일을 찾을 수 없습니다")
                return False
            
            # 사용자 커스터마이징 적용
            user_config = default_config.copy()
            
            if overrides:
                user_config.update(overrides)
            
            # 메타데이터 추가
            user_config['_metadata'] = {
                'created': datetime.now().isoformat(),
                'source': 'user_customization',
                'version': '1.0.0'
            }
            
            return self.save_config(user_config, self.user_config_file)
            
        except Exception as e:
            print(f"❌ 사용자 설정 생성 오류: {str(e)}")
            return False
    
    def reset_to_default(self) -> bool:
        """기본 설정으로 재설정"""
        try:
            # 현재 사용자 설정 백업
            if self.user_config_file.exists():
                self.backup_config(self.user_config_file)
                self.user_config_file.unlink()
            
            print("✅ 사용자 설정이 기본값으로 재설정되었습니다")
            return True
            
        except Exception as e:
            print(f"❌ 기본 설정 재설정 오류: {str(e)}")
            return False
    
    def list_backups(self) -> list:
        """백업 파일 목록 조회"""
        try:
            backups = []
            for backup_file in self.backup_dir.glob('*_backup_*.json'):
                stat = backup_file.stat()
                backups.append({
                    'name': backup_file.name,
                    'path': str(backup_file),
                    'size_kb': stat.st_size / 1024,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            # 최신순 정렬
            backups.sort(key=lambda x: x['modified'], reverse=True)
            return backups
            
        except Exception as e:
            print(f"❌ 백업 목록 조회 오류: {str(e)}")
            return []
    
    def show_config_summary(self) -> None:
        """설정 요약 정보 표시"""
        config = self.load_config()
        
        if not config:
            print("❌ 설정을 로드할 수 없습니다")
            return
        
        print("\n" + "="*60)
        print("⚙️ 시스템 설정 요약")
        print("="*60)
        
        # 기본 정보
        if 'trading_system' in config:
            ts = config['trading_system']
            print(f"📊 시스템: {ts.get('name', 'Unknown')} v{ts.get('version', '1.0.0')}")
        
        # 데이터베이스
        if 'database' in config:
            db = config['database']
            print(f"💾 데이터베이스: {db.get('path', 'Not configured')}")
        
        # 추적 종목
        if 'data_collection' in config:
            dc = config['data_collection']
            symbols = dc.get('default_symbols', [])
            print(f"📈 기본 종목: {len(symbols)}개 ({', '.join(symbols[:3])}{'...' if len(symbols) > 3 else ''})")
        
        # 신호 설정
        if 'trading_signals' in config:
            ts = config['trading_signals']
            print(f"🚨 신호 임계값: {ts.get('confidence_threshold', 0.7):.1f}")
            print(f"🔢 최소 지표수: {ts.get('min_indicators', 3)}개")
        
        # 리스크 관리
        if 'risk_management' in config:
            rm = config['risk_management']
            print(f"⚠️ 최대 포지션: {rm.get('max_position_size_percent', 10)}%")
            print(f"🛑 손절매: {rm.get('stop_loss_percent', 5)}%")
            print(f"💰 익절매: {rm.get('take_profit_percent', 15)}%")
        
        # 기술적 분석
        if 'technical_analysis' in config:
            ta = config['technical_analysis']
            enabled_indicators = []
            
            for indicator, settings in ta.items():
                if isinstance(settings, dict) and settings.get('enabled', False):
                    enabled_indicators.append(indicator.replace('_', ' ').title())
            
            print(f"📊 활성 지표: {', '.join(enabled_indicators) if enabled_indicators else '없음'}")
        
        # 설정 검증
        validation = self.validate_config(config)
        print(f"\n🏥 설정 상태: {'✅ 정상' if validation['valid'] else '❌ 오류'}")
        
        if validation['issues']:
            print("🚨 문제점:")
            for issue in validation['issues']:
                print(f"  • {issue}")
        
        if validation['warnings']:
            print("⚠️ 주의사항:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
        
        print("="*60)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="설정 관리 시스템")
    parser.add_argument('--action', '-a', 
                       choices=['show', 'get', 'set', 'validate', 'create', 'reset', 'backups'],
                       default='show',
                       help='실행할 작업')
    parser.add_argument('--key', '-k', help='설정 키 (점 표기법)')
    parser.add_argument('--value', '-v', help='설정 값')
    parser.add_argument('--config-dir', default='config', help='설정 디렉토리')
    
    args = parser.parse_args()
    
    # 설정 관리자 초기화
    try:
        config_manager = ConfigManager(config_dir=args.config_dir)
    except Exception as e:
        print(f"❌ 설정 관리자 초기화 실패: {str(e)}")
        sys.exit(1)
    
    # 작업별 실행
    success = True
    
    if args.action == 'show':
        config_manager.show_config_summary()
    
    elif args.action == 'get':
        if not args.key:
            print("❌ --key 옵션이 필요합니다")
            sys.exit(1)
        
        value = config_manager.get_config_value(args.key)
        if value is not None:
            print(f"{args.key}: {value}")
        else:
            print(f"⚠️ 설정 키를 찾을 수 없습니다: {args.key}")
            success = False
    
    elif args.action == 'set':
        if not args.key or args.value is None:
            print("❌ --key와 --value 옵션이 모두 필요합니다")
            sys.exit(1)
        
        # 값 타입 자동 변환 시도
        try:
            # JSON 파싱 시도 (숫자, 불린, 배열, 객체)
            parsed_value = json.loads(args.value)
        except json.JSONDecodeError:
            # 파싱 실패하면 문자열로 처리
            parsed_value = args.value
        
        success = config_manager.set_config_value(args.key, parsed_value)
    
    elif args.action == 'validate':
        validation = config_manager.validate_config()
        print(f"🏥 설정 검증 결과: {'✅ 정상' if validation['valid'] else '❌ 오류'}")
        
        if validation['issues']:
            print("🚨 문제점:")
            for issue in validation['issues']:
                print(f"  • {issue}")
        
        if validation['warnings']:
            print("⚠️ 주의사항:")
            for warning in validation['warnings']:
                print(f"  • {warning}")
        
        success = validation['valid']
    
    elif args.action == 'create':
        print("👤 사용자 설정 파일 생성 중...")
        success = config_manager.create_user_config()
    
    elif args.action == 'reset':
        print("🔄 기본 설정으로 재설정 중...")
        success = config_manager.reset_to_default()
    
    elif args.action == 'backups':
        backups = config_manager.list_backups()
        
        if backups:
            print(f"💾 백업 파일 목록 ({len(backups)}개):")
            print("-" * 60)
            
            for backup in backups[:10]:  # 최근 10개만 표시
                print(f"📄 {backup['name']}")
                print(f"   크기: {backup['size_kb']:.1f}KB")
                print(f"   수정: {backup['modified']}")
                print()
            
            if len(backups) > 10:
                print(f"... 총 {len(backups)}개 중 최근 10개만 표시")
        else:
            print("💾 백업 파일이 없습니다")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()