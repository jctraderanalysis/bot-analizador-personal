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

def enviar_telegram(mensaje):
    if token_telegram and chat_id_telegram:
        url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
        payload = {"chat_id": chat_id_telegram, "text": mensaje, "parse_mode": "Markdown"}
        try: requests.post(url, json=payload)
        except Exception: pass

def calcular_indicadores_completos(df):
    # Tus 4 EMAs
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    # MACD Nativo
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    
    # RSI Nativo de 14 períodos
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

if st.sidebar.button("🚀 INICIAR ESCANEO DE MERCADOS", use_container_width=True):
    alertas_encontradas = []
    filas_monitoreo = []
    todos_los_activos = [("Acciones", x) for x in lista_acciones] + [("Forex", x) for x in lista_forex] + [("Crypto", x) for x in lista_crypto]
    
    progreso = st.progress(0)
    total = len(todos_los_activos)
    
    for idx, (cat, activo) in enumerate(todos_los_activos):
        progreso.progress((idx + 1) / total)
        try:
            ticker = yf.Ticker(activo)
            df_h1 = ticker.history(period="15d", interval="1h")
            if df_h1.empty or len(df_h1) < 200: continue
            
            df_h1 = calcular_indicadores_completos(df_h1)
            last_h1 = df_h1.iloc[-1]
            prev_h1 = df_h1.iloc[-2]
            
            # Evaluación matemática de tu estrategia
            alcista_h1 = last_h1['EMA30'] > last_h1['EMA50'] > last_h1['EMA100'] > last_h1['EMA200']
            bajista_h1 = last_h1['EMA30'] < last_h1['EMA50'] < last_h1['EMA100'] < last_h1['EMA200']
            
            # Definir estado visual de las EMAs
            estado_emas = "🟢 Alcistas" if alcista_h1 else ("🔴 Bajistas" if bajista_h1 else "🟡 Entrelazadas")
            
            cruce_positivo_macd = (prev_h1['MACD'] < 0) and (last_h1['MACD'] > 0)
            cruce_negativo_macd = (prev_h1['MACD'] > 0) and (last_h1['MACD'] < 0)
            
            estado_macd = "🔥 Cruce Alcista 0+" if cruce_positivo_macd else ("💥 Cruce Bajista 0-" if cruce_negativo_macd else f"{last_h1['MACD']:.4f}")
            
            # Guardar datos para la tabla informativa
            filas_monitoreo.append({
                "Mercado": cat,
                "Activo": activo,
                "Precio Actual": round(last_h1['Close'], 4),
                "Estructura EMAs": estado_emas,
                "RSI (14)": round(last_h1['RSI'], 2),
                "Estado MACD": estado_macd
            })
            
            # Gatillos de alertas
            if alcista_h1 and cruce_positivo_macd:
                alertas_encontradas.append((activo, cat, "🟢 COMPRA", "EMAs alineadas + Cruce MACD 0+"))
            elif bajista_h1 and cruce_negativo_macd:
                alertas_encontradas.append((activo, cat, "🔴 VENTA", "EMAs bajistas + Cruce MACD 0-"))
        except Exception:
            pass
            
    # --- RENDERIZADO DE LA INFORMACIÓN EN PANTALLA ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔥 Alertas de Entrada Inmediatas")
        if alertas_encontradas:
            for act, cat, tipo, det in alertas_encontradas:
                if "COMPRA" in tipo:
                    st.success(f"**{tipo} en {act} ({cat})**: {det}")
                else:
                    st.error(f"**{tipo} en {act} ({cat})**: {det}")
            
            # Enviar aviso rápido a Telegram
            msg_tele = "🔥 *ALERTAS DETECTADAS* 🔥\n\n" + "\n".join([f"{t} en {a}" for a, c, t, d in alertas_encontradas])
            enviar_telegram(msg_tele)
        else:
            st.info("No se detectaron cruces de confirmación exactos en la vela actual.")
            
    with col2:
        st.subheader("📊 Control Operativo")
        st.metric("Último Escaneo Realizado", datetime.now().strftime("%H:%M:%S"))
        
    # --- NUEVA SECCIÓN: MATRIZ DE DATOS EN TIEMPO REAL ---
    st.markdown("---")
    st.subheader("📋 Matriz de Datos Técnicos en Vivo (H1)")
    if filas_monitoreo:
        df_vis = pd.DataFrame(filas_monitoreo)
        st.dataframe(df_vis, use_container_width=True, hide_index=True)
else:
    st.info("Presiona el botón en la barra lateral para escanear tus mercados con tu estrategia.")
