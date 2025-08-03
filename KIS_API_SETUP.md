# 한국투자증권 API 설정 가이드

이 가이드는 Smart Trading Dashboard에서 실시간 한국 주식 데이터를 사용하기 위한 한국투자증권 API 설정 방법을 설명합니다.

## 🔑 API 발급 절차

### 1단계: 한국투자증권 계좌 준비
- **실계좌** 또는 **모의투자 계좌** 필요
- 모의투자 계좌는 온라인에서 간단히 개설 가능

### 2단계: KIS Developers 가입
1. [KIS Developers 포털](https://apiportal.koreainvestment.com) 접속
2. 회원가입 및 로그인
3. "앱 등록" 메뉴에서 새 앱 생성
4. **App Key**와 **App Secret** 발급 받기

### 3단계: 계좌 연동 신청
1. 개발자 포털에서 "계좌 연동" 신청
2. 승인까지 1-2일 소요

## 💻 로컬 개발 설정

### 환경 변수 설정 (.env)
```bash
# 프로젝트 루트에 .env 파일 생성
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_BASE_URL=https://openapi.koreainvestment.com:9443

# 모의투자의 경우
# KIS_BASE_URL=https://openapivts.koreainvestment.com:29443
```

### 라이브러리 설치
```bash
pip install python-dotenv
```

## ☁️ Streamlit Cloud 배포 설정

### Secrets 설정
Streamlit Cloud 앱 설정에서 다음 secrets를 추가:

```toml
[kis]
app_key = "your_app_key_here"
app_secret = "your_app_secret_here"
base_url = "https://openapi.koreainvestment.com:9443"
```

## 🚀 기능 확인

API가 올바르게 설정되면:
- ✅ "한국투자증권 API 연결됨 (실시간 데이터)" 메시지 표시
- 🔴 실시간 주가 데이터 제공
- 📋 실시간 호가창 표시

API 설정이 없으면:
- ⚠️ "지연 데이터 사용" 메시지 표시
- 🟡 Yahoo Finance 데이터 사용 (15-20분 지연)

## 🔧 문제 해결

### 토큰 발급 실패
- App Key/Secret 재확인
- 계좌 연동 승인 상태 확인
- 모의투자/실계좌 URL 확인

### 네트워크 오류
- 방화벽 설정 확인
- VPN 연결 확인

### 호가 데이터 없음
- 장중 시간 확인 (평일 09:00-15:30)
- 종목 코드 정확성 확인

## 📞 지원

- 한국투자증권 API 문의: [KIS Developers 지원센터](https://apiportal.koreainvestment.com)
- 앱 관련 문의: GitHub Issues

---

⚠️ **주의사항**: API 사용량 제한이 있으므로 과도한 요청은 피해주세요.