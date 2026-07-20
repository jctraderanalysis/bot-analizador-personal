import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(
    page_title="Analizador Personal",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Cuadro de Mando Multitemporal Avanzado")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Configuración del Sistema")
token_telegram = st.sidebar.text_input("Telegram Bot Token", value=st.secrets.get("TELEGRAM_TOKEN", ""), type="password")
chat_id_telegram = st.sidebar.text_input("Telegram Chat ID", value=st.secrets.get("TELEGRAM_CHAT_ID", ""), type="password")

acciones_input = st.sidebar.text_area("Acciones", "AAPL,MSFT,NVDA,TSLA,AMD,AMZN")
forex_input = st.sidebar.text_area("Forex", "EURUSD=X,GBPUSD=X,AUDUSD=X")
crypto_input = st.sidebar.text_area("Crypto", "BTC-USD,ETH-USD")

lista_acciones = [x.strip() for x in acciones_input.split(",") if x.strip()]
lista_forex = [x.strip() for x in forex_input.split(",") if x.strip()]
lista_crypto = [x.strip() for x in crypto_input.split(",") if x.strip()]

def calcular_indicadores(df):
    if df.empty or len(df) < 200:
        return None
    # Tus 4 EMAs
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # MACD Nativo
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    # RSI 14
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def evaluar_direccion(last_row):
    alcista = last_row['EMA30'] > last_row['EMA50'] > last_row['EMA100'] > last_row['EMA200']
    bajista = last_row['EMA30'] < last_row['EMA50'] < last_row['EMA100'] < last_row['EMA200']
    if alcista: return "🟢 ALCISTA"
    if bajista: return "🔴 BAJISTA"
    return "🟡 NEUTRO"

if st.sidebar.button("🚀 INICIAR ESCANEO MULTITEMPORAL", use_container_width=True):
    datos_h4 = []
    datos_h1 = []
    datos_m5 = []
    
    todos_los_activos = [("Acciones", x) for x in lista_acciones] + [("Forex", x) for x in lista_forex] + [("Crypto", x) for x in lista_crypto]
    
    progreso = st.progress(0)
    total = len(todos_los_activos)
    
    for idx, (cat, activo) in enumerate(todos_los_activos):
        progreso.progress((idx + 1) / total)
        try:
            ticker = yf.Ticker(activo)
            
            # Descarga de datos
            df_h4 = calcular_indicadores(ticker.history(period="60d", interval="4h"))
            df_h1 = calcular_indicadores(ticker.history(period="15d", interval="1h"))
            df_m5 = calcular_indicadores(ticker.history(period="2d", interval="5m"))
            
            if df_h4 is None or df_h1 is None or df_m5 is None:
                continue
                
            lh4, ph4 = df_h4.iloc[-1], df_h4.iloc[-2]
            lh1, ph1 = df_h1.iloc[-1], df_h1.iloc[-2]
            lm5, pm5 = df_m5.iloc[-1], df_m5.iloc[-2]
            
            dec = 4 if cat == "Forex" else 2
            
            # --- TABLA 1: DATOS H4 (TENDENCIA MACRO) ---
            tendencia_h4 = evaluar_direccion(lh4)
            datos_h4.append({
                "Activo": activo, "C/C H4": round(lh4['Close'], dec),
                "Tendencia H4": tendencia_h4, "EMA 30": round(lh4['EMA30'], dec),
                "EMA 50": round(lh4['EMA50'], dec), "EMA 100": round(lh4['EMA100'], dec),
                "EMA 200": round(lh4['EMA200'], dec), "RSI H4": round(lh4['RSI'], 1),
                "MACD H4": round(lh4['MACD'], dec)
            })
            
            # --- TABLA 2: DATOS H1 (ESTRUCTURA INTERMEDIA) ---
            tendencia_h1 = evaluar_direccion(lh1)
            datos_h1.append({
                "Activo": activo, "C/C H1": round(lh1['Close'], dec),
                "Tendencia H1": tendencia_h1, "EMA 30": round(lh1['EMA30'], dec),
                "EMA 50": round(lh1['EMA50'], dec), "EMA 100": round(lh1['EMA100'], dec),
                "EMA 200": round(lh1['EMA200'], dec), "RSI H1": round(lh1['RSI'], 1),
                "MACD H1": round(lh1['MACD'], dec)
            })
            
            # --- TABLA 3: DATOS M5 (DISPARADOR & RECOMENDACIÓN) ---
            tendencia_m5 = evaluar_direccion(lm5)
            
            # Lógica de alineación de piernas
            t_h4_pura = tendencia_h4.split(" ")[1]
            t_h1_pura = tendencia_h1.split(" ")[1]
            t_m5_pura = tendencia_m5.split(" ")[1]
            
            if t_h4_pura == "ALCISTA" and t_h1_pura == "ALCISTA" and t_m5_pura == "ALCISTA" and lm5['RSI'] < 70:
                recom = "🟢 COMPRA CONFIRMADA"
            elif t_h4_pura == "BAJISTA" and t_h1_pura == "BAJISTA" and t_m5_pura == "BAJISTA" and lm5['RSI'] > 30:
                recom = "🔴 VENTA CONFIRMADA"
            elif t_h1_pura == "ALCISTA" and t_m5_pura == "ALCISTA":
                recom = "🟡 COMPRA RIESGO (H4 Neutro/Bajista)"
            elif t_h1_pura == "BAJISTA" and t_m5_pura == "BAJISTA":
                recom = "🟡 VENTA RIESGO (H4 Neutro/Alcista)"
            else:
                recom = "⚪ NEUTRO (Esperar Alineación)"
                
            datos_m5.append({
                "Activo": activo, "C/C M5": round(lm5['Close'], dec),
                "Gatillo M5": tendencia_m5, "EMA 30": round(lm5['EMA30'], dec),
                "EMA 50": round(lm5['EMA50'], dec), "EMA 100": round(lm5['EMA100'], dec),
                "EMA 200": round(lm5['EMA200'], dec), "RSI M5": round(lm5['RSI'], 1),
                "MACD M5": round(lm5['MACD'], dec), "RECOMENDACIÓN OPE": recom
            })
        except Exception:
            pass

    # --- RENDERIZADO DE LAS TRES TABLAS ---
    def color_filas(val):
        if "🟢" in str(val): return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        if "🔴" in str(val): return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        if "🟡" in str(val): return 'background-color: #fff3cd; color: #856404;'
        return ''

    st.markdown("### 🏛️ 1. Matriz de Tendencia Macro (H4)")
    if datos_h4:
        df_h4 = pd.DataFrame(datos_h4)
        st.dataframe(df_h4.style.map(color_filas, subset=['Tendencia H4']), use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.markdown("### 📈 2. Matriz de Estructura Intermedia (H1)")
    if datos_h1:
        df_h1 = pd.DataFrame(datos_h1)
        st.dataframe(df_h1.style.map(color_filas, subset=['Tendencia H1']), use_container_width=True, hide_index=True)
        
    st.markdown("---")
    st.markdown("### ⚡ 3. Matriz de Gatillo y Ejecución Operativa (M5)")
    if datos_m5:
        df_m5 = pd.DataFrame(datos_m5)
        st.dataframe(df_m5.style.map(color_filas, subset=['Gatillo M5', 'RECOMENDACIÓN OPE']), use_container_width=True, hide_index=True)

    st.caption(f"Última actualización general de mercado a las: {datetime.now().strftime('%H:%M:%S')}")
else:
    st.info("Presiona el botón en la barra lateral para procesar y dividir el análisis en sus 3 tablas correspondientes.")
