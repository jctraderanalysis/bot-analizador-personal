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

st.title("📊 Escáner Multitemporal Avanzado (Personal)")

st.sidebar.header("⚙️ Configuración del Sistema")
token_telegram = st.sidebar.text_input("Telegram Bot Token", value=st.secrets.get("TELEGRAM_TOKEN", ""), type="password")
chat_id_telegram = st.sidebar.text_input("Telegram Chat ID", value=st.secrets.get("TELEGRAM_CHAT_ID", ""), type="password")

acciones_input = st.sidebar.text_area("Acciones", "AAPL,MSFT,NVDA,TSLA,AMD,AMZN")
forex_input = st.sidebar.text_area("Forex", "EURUSD=X,GBPUSD=X,AUDUSD=X")
crypto_input = st.sidebar.text_area("Crypto", "BTC-USD,ETH-USD")

lista_acciones = [x.strip() for x in acciones_input.split(",") if x.strip()]
lista_forex = [x.strip() for x in forex_input.split(",") if x.strip()]
lista_crypto = [x.strip() for x in crypto_input.split(",") if x.strip()]

def enviar_telegram(mensaje):
    if token_telegram and chat_id_telegram:
        url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
        payload = {"chat_id": chat_id_telegram, "text": mensaje, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload)
        except Exception: pass

def calcular_indicadores_nativos(df):
    # Cálculo matemático de tus 4 EMAs sin librerías externas
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # MACD Estándar (12, 26, 9) hecho de forma nativa
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    return df

if st.sidebar.button("🚀 INICIAR ESCANEO DE MERCADOS", use_container_width=True):
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔥 Alertas de Entrada Confirmadas (H1)")
        alertas_encontradas = []
        todos_los_activos = [("Acciones", x) for x in lista_acciones] + [("Forex", x) for x in lista_forex] + [("Crypto", x) for x in lista_crypto]
        
        progreso = st.progress(0)
        total = len(todos_los_activos)
        
        for idx, (cat, activo) in enumerate(todos_los_activos):
            progreso.progress((idx + 1) / total)
            try:
                ticker = yf.Ticker(activo)
                df_h1 = ticker.history(period="15d", interval="1h")
                if df_h1.empty or len(df_h1) < 200: continue
                
                df_h1 = calcular_indicadores_nativos(df_h1)
                last_h1 = df_h1.iloc[-1]
                prev_h1 = df_h1.iloc[-2]
                
                # Tu estrategia: alineación en abanico de las 4 EMAs
                alcista_h1 = last_h1['EMA30'] > last_h1['EMA50'] > last_h1['EMA100'] > last_h1['EMA200']
                bajista_h1 = last_h1['EMA30'] < last_h1['EMA50'] < last_h1['EMA100'] < last_h1['EMA200']
                
                # Tu estrategia: cruce de la línea cero del MACD
                cruce_positivo_macd = (prev_h1['MACD'] < 0) and (last_h1['MACD'] > 0)
                cruce_negativo_macd = (prev_h1['MACD'] > 0) and (last_h1['MACD'] < 0)
                
                if alcista_h1 and cruce_positivo_macd:
                    st.success(f"🟢 **COMPRA EN {activo} ({cat})**: EMAs en abanico alcista y MACD cruzando el nivel 0 a positivo.")
                    alertas_encontradas.append(f"🟢 *COMPRA* en {activo} - EMAs & MACD en 0+")
                elif bajista_h1 and cruce_negativo_macd:
                    st.error(f"🔴 **VENTA EN {activo} ({cat})**: EMAs en abanico bajista y MACD cruzando el nivel 0 a negativo.")
                    alertas_encontradas.append(f"🔴 *VENTA* en {activo} - EMAs & MACD en 0-")
            except Exception:
                pass
                
        if not alertas_encontradas:
            st.info("Monitoreo completado. No se detectaron cruces exactos en esta vela.")
        else:
            enviar_telegram("🔥 *ALERTAS MULTITEMPORALES* 🔥\n\n" + "\n".join(alertas_encontradas))
            
    with col2:
        st.subheader("📊 Control Operativo")
        st.metric("Último Escaneo Realizado", datetime.now().strftime("%H:%M:%S"))
else:
    st.info("Presiona el botón en la barra lateral para escanear tus mercados con tu estrategia.")
