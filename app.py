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

st.title("📊 Escáner Multitemporal de Precisión (M5 | H1 | H4)")

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
    # Estructura de tus 4 EMAs
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # MACD
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
    # Evalúa si las EMAs están en abanico
    alcista = last_row['EMA30'] > last_row['EMA50'] > last_row['EMA100'] > last_row['EMA200']
    bajista = last_row['EMA30'] < last_row['EMA50'] < last_row['EMA100'] < last_row['EMA200']
    if alcista: return "ALCISTA"
    if bajista: return "BAJISTA"
    return "NEUTRO"

if st.sidebar.button("🚀 INICIAR ESCANEO MULTITEMPORAL", use_container_width=True):
    filas_monitoreo = []
    todos_los_activos = [("Acciones", x) for x in lista_acciones] + [("Forex", x) for x in lista_forex] + [("Crypto", x) for x in lista_crypto]
    
    progreso = st.progress(0)
    total = len(todos_los_activos)
    
    for idx, (cat, activo) in enumerate(todos_los_activos):
        progreso.progress((idx + 1) / total)
        try:
            ticker = yf.Ticker(activo)
            
            # 1. Descarga y cálculo de marcos de tiempo (H4, H1, M5)
            df_h4 = calcular_indicadores(ticker.history(period="60d", interval="4h"))
            df_h1 = calcular_indicadores(ticker.history(period="15d", interval="1h"))
            df_m5 = calcular_indicadores(ticker.history(period="2d", interval="5m"))
            
            if df_h4 is None or df_h1 is None or df_m5 is None:
                continue
                
            last_h4 = df_h4.iloc[-1]
            last_h1 = df_h1.iloc[-1]
            last_m5 = df_m5.iloc[-1]
            
            # Determinación de las piernas dominantes por alineación de EMAs
            pierna_h4 = evaluar_direccion(last_h4)
            pierna_h1 = evaluar_direccion(last_h1)
            pierna_m5 = evaluar_direccion(last_m5)
            
            # 2. Lógica Algorítmica de Recomendación de Entrada
            # Compra: Tendencias mayores acompañan y M5 confirma el trigger o el quiebre
            if pierna_h4 == "ALCISTA" and pierna_h1 == "ALCISTA" and pierna_m5 == "ALCISTA" and last_m5['RSI'] < 70:
                recomendacion = "🟢 COMPRA CONFIRMADA"
            elif pierna_h4 == "BAJISTA" and pierna_h1 == "BAJISTA" and pierna_m5 == "BAJISTA" and last_m5['RSI'] > 30:
                recomendacion = "🔴 VENTA CONFIRMADA"
            # Contratendencia o rebotes controlados
            elif pierna_h1 == "ALCISTA" and pierna_m5 == "ALCISTA":
                recomendacion = "🟡 COMPRA RIESGO (H4 Neutro/Abajo)"
            elif pierna_h1 == "BAJISTA" and pierna_m5 == "BAJISTA":
                recomendacion = "🟡 VENTA RIESGO (H4 Neutro/Arriba)"
            else:
                recomendacion = "⚪ NEUTRO (Esperar Alineación)"
                
            dec = 4 if cat == "Forex" else 2
            
            filas_monitoreo.append({
                "Activo": activo,
                "C/C (Cierre)": round(last_m5['Close'], dec),
                "Pierna H4": "🟢 ALC" if pierna_h4 == "ALCISTA" else ("🔴 BAJ" if pierna_h4 == "BAJISTA" else "🟡 MIX"),
                "Pierna H1": "🟢 ALC" if pierna_h1 == "ALCISTA" else ("🔴 BAJ" if pierna_h1 == "BAJISTA" else "🟡 MIX"),
                "Estado M5": "🟢 ALC" if pierna_m5 == "ALCISTA" else ("🔴 BAJ" if pierna_m5 == "BAJISTA" else "🟡 MIX"),
                "RSI M5": round(last_m5['RSI'], 1),
                "MACD M5": round(last_m5['MACD'], dec),
                "RECOMENDACIÓN": recomendacion
            })
        except Exception:
            pass

    # --- INTERFAZ ---
    st.subheader("📋 Matriz de Decisión Multitemporal en Tiempo Real")
    if filas_monitoreo:
        df_vis = pd.DataFrame(filas_monitoreo)
        
        # Estilos visuales dinámicos para la columna de Recomendación
        def color_recomendacion(val):
            if "🟢" in val: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
            if "🔴" in val: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
            if "🟡" in val: return 'background-color: #fff3cd; color: #856404;'
            return 'color: #6c757d;'

        # CÓDIGO NUEVO (Corregido):
st.dataframe(df_vis.style.map(color_recomendacion, subset=['RECOMENDACIÓN']), use_container_width=True, hide_index=True)
        st.metric("Última Actualización", datetime.now().strftime("%H:%M:%S"))
    else:
        st.error("No se pudieron recopilar suficientes datos de los servidores. Reintenta el escaneo.")
else:
    st.info("Presiona el botón en la barra lateral para procesar el análisis de pantallas H4 -> H1 -> M5.")
