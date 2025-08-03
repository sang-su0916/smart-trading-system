# 🚀 Smart Trading Dashboard v4.0

실시간 한국 주식 데이터를 지원하는 AI 기반 종합 투자 분석 도구

## 🌐 온라인 체험

**👉 [https://smart-trading-system.streamlit.app](https://smart-trading-system.streamlit.app)**

실시간으로 체험해보세요! 한국투자증권 API 설정 없이도 지연 데이터로 모든 기능을 이용할 수 있습니다.

## ✨ 주요 특징

### 🔴 실시간 데이터 지원 (NEW!)
- **한국투자증권 API** 연동으로 실시간 주가 데이터
- **실시간 호가창** (10단계 매수/매도 호가)
- **하이브리드 시스템**: API 없어도 지연 데이터로 동작

### 📊 5가지 기술적 지표 종합 분석
- **RSI**: 과매수/과매도 분석
- **MACD**: 모멘텀 추세 분석  
- **볼린저 밴드**: 변동성 및 가격 채널 분석
- **스토캐스틱**: 단기 반전 신호 분석
- **이동평균**: 추세 방향 및 지지/저항 분석

### ⚖️ 공정가치 분석
- AI 기반 종합 점수 (0-100점)
- 매수/관망/매도 추천
- 신뢰도 및 근거 제시

### 🏭 업종 비교 분석
- 동종업계 평균 대비 성과
- 상대적 강도 분석
- 업종 순위 및 벤치마크

### 🚦 실시간 매매 신호
- 진입/청산 타이밍 제안
- 목표가 및 손절가 설정
- 위험도 기반 포지션 사이징

### 📚 투자 교육 기능
- 모든 용어와 지표 상세 설명
- 투자 가이드 및 FAQ
- 단계별 사용법 안내

## 🎯 화면 구성

### 메인 대시보드
1. **실시간 현재가** - 변동률, 거래량, 고저가
2. **호가창** - 10단계 실시간 매수/매도 호가 (API 연동시)
3. **주가 차트** - 캔들스틱 + 기술적 지표 오버레이
4. **공정가치 분석** - 종합 점수 및 투자 추천
5. **업종 비교** - 동종업계 상대 성과
6. **매매 신호** - 구체적 진입/청산 전략
7. **투자 가이드** - 용어 설명 및 활용법

## 🛠 로컬 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/sang-su0916/smart-trading-system.git
cd smart-trading-system
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 앱 실행
```bash
streamlit run streamlit_app.py
```

### 4. 브라우저 접속
```
http://localhost:8501
```

## 🔑 실시간 데이터 설정 (선택사항)

### 한국투자증권 API 발급
1. [KIS Developers](https://apiportal.koreainvestment.com) 가입
2. 앱 등록 후 App Key/Secret 발급
3. 계좌 연동 신청

### 로컬 환경 설정
```bash
# .env 파일 생성
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
```

### Streamlit Cloud 배포시 설정
앱 설정 → Secrets에 다음 추가:
```toml
[kis]
app_key = "your_app_key_here"
app_secret = "your_app_secret_here" 
base_url = "https://openapi.koreainvestment.com:9443"
```

자세한 설정 방법은 [`KIS_API_SETUP.md`](KIS_API_SETUP.md)를 참고하세요.

## 📱 지원 기능

### 데이터 소스
- ✅ **실시간**: 한국투자증권 API (호가창 포함)
- ✅ **지연**: Yahoo Finance (15-20분 지연)
- ✅ **자동 백업**: API 실패시 자동 전환

### 지원 종목
- 🇰🇷 **한국 주식**: 코스피/코스닥 주요 종목
- 📈 **실시간 검색**: 종목명/코드로 빠른 검색
- 🔄 **자동 업데이트**: 최신 종목 리스트

### 기술적 분석
- 📊 **차트 분석**: 캔들스틱 + 기술적 지표
- 🎯 **신호 통합**: 5개 지표 종합 판단
- 📈 **트렌드 분석**: 단기/중기/장기 추세
- ⚠️ **리스크 관리**: 손절가/목표가 자동 계산

## 🎨 사용자 인터페이스

### 반응형 디자인
- 💻 **데스크톱**: 4컬럼 레이아웃 최적화
- 📱 **모바일**: 1컬럼 세로 스크롤
- 🎨 **다크/라이트**: 테마 자동 감지

### 실시간 업데이트
- 🔄 **1분 캐시**: 현재가 자동 갱신
- ⚡ **30초 캐시**: 호가창 실시간 업데이트
- 📊 **5분 캐시**: 차트 데이터 최적화

## 📊 성능 및 안정성

### 캐싱 시스템
- 🚀 **Streamlit 캐싱**: 중복 요청 방지
- ⏱️ **TTL 관리**: 시간 기반 캐시 무효화
- 💾 **메모리 최적화**: 효율적 데이터 관리

### 오류 복원력
- 🔄 **자동 재시도**: 네트워크 오류 복구
- 🛡️ **예외 처리**: 모든 API 호출 보호
- 📱 **사용자 알림**: 명확한 상태 메시지

## 🔧 기술 스택

### Frontend
- **Streamlit**: 웹 앱 프레임워크
- **Plotly**: 인터랙티브 차트
- **Pandas**: 데이터 처리

### Backend
- **yfinance**: 주가 데이터 API
- **한국투자증권 API**: 실시간 데이터
- **requests**: HTTP 통신

### 배포
- **Streamlit Cloud**: 클라우드 호스팅
- **GitHub**: 소스 코드 관리
- **CI/CD**: 자동 배포

## 📈 업데이트 이력

### v4.0 (2025-01-13)
- 🔴 한국투자증권 API 통합
- 📋 실시간 호가창 추가
- 🔄 하이브리드 데이터 시스템
- 🛡️ 향상된 오류 처리

### v3.0 (2024-12-xx)
- ⚖️ 공정가치 분석 시스템
- 🏭 업종 비교 분석
- 🚦 매매 신호 시스템
- 📚 투자 교육 콘텐츠

### v2.0 (2024-11-xx)
- 📊 5가지 기술적 지표 통합
- 🎨 UI/UX 대폭 개선
- 📱 모바일 최적화

### v1.0 (2024-10-xx)
- 🚀 초기 버전 출시
- 📈 기본 차트 기능
- 🔍 종목 검색

## ⚠️ 면책 조항

이 대시보드는 **교육 및 정보 제공 목적**으로만 사용됩니다.

- 📚 **교육 도구**: 투자 학습용 참고 자료
- 🚫 **투자 권유 아님**: 매매 추천이 아닙니다
- 📊 **과거 데이터 기반**: 미래 수익 보장 불가
- 💰 **투자 책임**: 모든 투자 결정은 본인 책임

### 투자 시 유의사항
- 여유자금으로만 투자하세요
- 충분한 공부 후 투자하세요  
- 분산투자로 리스크를 관리하세요
- 본인만의 투자 원칙을 세우세요

## 📞 지원 및 문의

### 🐛 버그 리포트
- **GitHub Issues**: [문제 신고](https://github.com/sang-su0916/smart-trading-system/issues)
- **상세 정보**: 에러 메시지, 브라우저, OS 정보 포함

### 💡 기능 제안
- **GitHub Discussions**: [아이디어 공유](https://github.com/sang-su0916/smart-trading-system/discussions)
- **Feature Request**: 새로운 기능 요청

### 📖 사용법 문의
- **Wiki**: [상세 가이드](https://github.com/sang-su0916/smart-trading-system/wiki)
- **FAQ**: 자주 묻는 질문들

---

<div align="center">

**🎯 스마트한 투자 분석의 시작**

[🌐 온라인 체험](https://smart-trading-system.streamlit.app) | [📖 사용 가이드](KIS_API_SETUP.md) | [🐛 문제 신고](https://github.com/sang-su0916/smart-trading-system/issues)

⭐ **유용하다면 GitHub Star를 눌러주세요!** ⭐

</div>