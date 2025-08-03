#!/usr/bin/env python3
"""
간단한 GUI 버전 - .exe 파일 생성용
tkinter를 사용한 데스크톱 애플리케이션
"""
import tkinter as tk
from tkinter import ttk, messagebox
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
plt.rcParams['font.family'] = ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif']

class SmartTradingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("📊 Smart Trading Dashboard")
        self.root.geometry("1200x800")
        
        # 변수 초기화
        self.current_data = None
        self.current_symbol = tk.StringVar(value="005930.KS")
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI 구성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 상단 컨트롤 패널
        control_frame = ttk.LabelFrame(main_frame, text="📋 설정", padding="5")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 종목 선택
        ttk.Label(control_frame, text="종목:").grid(row=0, column=0, padx=(0, 5))
        
        symbol_combo = ttk.Combobox(control_frame, textvariable=self.current_symbol, width=15)
        symbol_combo['values'] = (
            '005930.KS (삼성전자)',
            '000660.KS (SK하이닉스)', 
            '035420.KS (네이버)',
            '005380.KS (현대차)',
            '055550.KS (신한지주)'
        )
        symbol_combo.grid(row=0, column=1, padx=(0, 10))
        
        # 분석 버튼
        analyze_btn = ttk.Button(control_frame, text="🔍 분석 시작", command=self.start_analysis)
        analyze_btn.grid(row=0, column=2, padx=(0, 10))
        
        # 새로고침 버튼
        refresh_btn = ttk.Button(control_frame, text="🔄 새로고침", command=self.refresh_data)
        refresh_btn.grid(row=0, column=3)
        
        # 진행 상태 바
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.grid(row=0, column=4, padx=(10, 0), sticky=(tk.W, tk.E))
        
        # 왼쪽 패널 - 정보 표시
        left_frame = ttk.LabelFrame(main_frame, text="📊 종목 정보", padding="5")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # 기본 정보 트리뷰
        self.info_tree = ttk.Treeview(left_frame, columns=('value',), show='tree headings', height=15)
        self.info_tree.heading('#0', text='항목')
        self.info_tree.heading('value', text='값')
        self.info_tree.column('#0', width=150)
        self.info_tree.column('value', width=150)
        self.info_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 스크롤바
        info_scroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.info_tree.yview)
        info_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_tree.configure(yscrollcommand=info_scroll.set)
        
        # 오른쪽 패널 - 차트
        right_frame = ttk.LabelFrame(main_frame, text="📈 주가 차트", padding="5")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # matplotlib 차트 영역
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, right_frame)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 하단 상태바
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.status_var = tk.StringVar(value="준비 완료")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=0, sticky=tk.W)
        
        # 그리드 가중치 설정
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
    def start_analysis(self):
        """분석 시작 (백그라운드에서 실행)"""
        # UI 비활성화
        self.progress.start()
        self.status_var.set("데이터 수집 중...")
        
        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=self.analyze_stock)
        thread.daemon = True
        thread.start()
        
    def analyze_stock(self):
        """주식 분석 실행"""
        try:
            # 종목 코드 추출
            symbol_text = self.current_symbol.get()
            symbol = symbol_text.split()[0] if ' ' in symbol_text else symbol_text
            
            # 데이터 수집
            self.root.after(0, lambda: self.status_var.set(f"{symbol} 데이터 수집 중..."))
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1y")
            
            if data.empty:
                raise Exception("데이터를 가져올 수 없습니다")
            
            self.current_data = data
            
            # 기술적 지표 계산
            self.root.after(0, lambda: self.status_var.set("기술적 지표 계산 중..."))
            data = self.calculate_indicators(data)
            
            # UI 업데이트 (메인 스레드에서)
            self.root.after(0, lambda: self.update_display(symbol, data))
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(str(e)))
        finally:
            self.root.after(0, self.finish_analysis)
    
    def calculate_indicators(self, data):
        """기술적 지표 계산"""
        # 이동평균선
        data['MA_5'] = data['Close'].rolling(window=5).mean()
        data['MA_20'] = data['Close'].rolling(window=20).mean()
        data['MA_60'] = data['Close'].rolling(window=60).mean()
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # 볼린저 밴드
        data['BB_Middle'] = data['Close'].rolling(window=20).mean()
        bb_std = data['Close'].rolling(window=20).std()
        data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
        data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
        
        return data
    
    def update_display(self, symbol, data):
        """화면 업데이트"""
        # 정보 트리 업데이트
        self.update_info_tree(symbol, data)
        
        # 차트 업데이트
        self.update_chart(data)
        
        self.status_var.set(f"{symbol} 분석 완료")
    
    def update_info_tree(self, symbol, data):
        """정보 트리뷰 업데이트"""
        # 기존 데이터 클리어
        for item in self.info_tree.get_children():
            self.info_tree.delete(item)
        
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest
        
        # 기본 정보
        basic_info = self.info_tree.insert('', 'end', text='📊 기본 정보')
        self.info_tree.insert(basic_info, 'end', text='종목 코드', values=(symbol,))
        self.info_tree.insert(basic_info, 'end', text='현재가', values=(f"{latest['Close']:,.0f}원",))
        
        change = latest['Close'] - prev['Close']
        change_pct = (change / prev['Close']) * 100
        change_text = f"{change:+,.0f}원 ({change_pct:+.2f}%)"
        self.info_tree.insert(basic_info, 'end', text='전일대비', values=(change_text,))
        self.info_tree.insert(basic_info, 'end', text='거래량', values=(f"{latest['Volume']:,.0f}주",))
        
        # 기술적 지표
        tech_info = self.info_tree.insert('', 'end', text='📈 기술적 지표')
        self.info_tree.insert(tech_info, 'end', text='5일 평균', values=(f"{latest['MA_5']:,.0f}원",))
        self.info_tree.insert(tech_info, 'end', text='20일 평균', values=(f"{latest['MA_20']:,.0f}원",))
        self.info_tree.insert(tech_info, 'end', text='60일 평균', values=(f"{latest['MA_60']:,.0f}원",))
        self.info_tree.insert(tech_info, 'end', text='RSI', values=(f"{latest['RSI']:.1f}",))
        
        # 매매 신호
        signals = self.generate_signals(data)
        signal_info = self.info_tree.insert('', 'end', text='🚨 매매 신호')
        
        if not signals:
            self.info_tree.insert(signal_info, 'end', text='현재 신호', values=('중립',))
        else:
            for signal in signals:
                signal_text = f"{signal['type']} ({signal['confidence']:.1%})"
                self.info_tree.insert(signal_info, 'end', text='추천', values=(signal_text,))
        
        # 트리 확장
        self.info_tree.item(basic_info, open=True)
        self.info_tree.item(tech_info, open=True)
        self.info_tree.item(signal_info, open=True)
    
    def generate_signals(self, data):
        """간단한 매매 신호 생성"""
        if len(data) < 60:
            return []
        
        signals = []
        latest = data.iloc[-1]
        
        buy_conditions = 0
        sell_conditions = 0
        
        # 이동평균 조건
        if latest['Close'] > latest['MA_5'] > latest['MA_20']:
            buy_conditions += 1
        elif latest['Close'] < latest['MA_5'] < latest['MA_20']:
            sell_conditions += 1
        
        # RSI 조건  
        if latest['RSI'] < 30:
            buy_conditions += 1
        elif latest['RSI'] > 70:
            sell_conditions += 1
        
        # 볼린저 밴드 조건
        if latest['Close'] < latest['BB_Lower']:
            buy_conditions += 1
        elif latest['Close'] > latest['BB_Upper']:
            sell_conditions += 1
        
        # 신호 생성
        if buy_conditions >= 2:
            signals.append({'type': 'BUY', 'confidence': min(buy_conditions * 0.3, 1.0)})
        elif sell_conditions >= 2:
            signals.append({'type': 'SELL', 'confidence': min(sell_conditions * 0.3, 1.0)})
        
        return signals
    
    def update_chart(self, data):
        """차트 업데이트"""
        self.ax.clear()
        
        # 최근 3개월 데이터만 표시
        recent_data = data.tail(90)
        
        # 캔들스틱 대신 라인 차트
        self.ax.plot(recent_data.index, recent_data['Close'], label='종가', linewidth=2)
        self.ax.plot(recent_data.index, recent_data['MA_5'], label='MA5', alpha=0.7)
        self.ax.plot(recent_data.index, recent_data['MA_20'], label='MA20', alpha=0.7)
        
        self.ax.set_title('주가 차트 (최근 3개월)')
        self.ax.set_ylabel('가격 (원)')
        self.ax.legend()
        self.ax.grid(True, alpha=0.3)
        
        # 날짜 포맷 조정
        self.fig.autofmt_xdate()
        
        # 차트 새로고침
        self.canvas.draw()
    
    def refresh_data(self):
        """데이터 새로고침"""
        if self.current_data is not None:
            self.start_analysis()
        else:
            messagebox.showinfo("정보", "먼저 분석을 시작해주세요.")
    
    def show_error(self, error_message):
        """에러 메시지 표시"""
        messagebox.showerror("에러", f"분석 중 오류가 발생했습니다:\n{error_message}")
        self.status_var.set("오류 발생")
    
    def finish_analysis(self):
        """분석 완료 처리"""
        self.progress.stop()

def main():
    """메인 실행 함수"""
    root = tk.Tk()
    app = SmartTradingGUI(root)
    
    # 창 아이콘 설정 (선택사항)
    try:
        root.iconbitmap('icon.ico')  # 아이콘 파일이 있는 경우
    except:
        pass
    
    root.mainloop()

if __name__ == "__main__":
    main()