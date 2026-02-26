import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Portal de Elegibilidade", 
    page_icon="📞", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. ESTILOS CSS CUSTOMIZADOS (BELEZA DO SISTEMA)
# ==========================================
estilo_customizado = """
    <style>
    /* Esconde o menu hamburguer e rodapé padrão */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Reduz o espaço em branco enorme no topo da página */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }
    
    /* Título menor e mais elegante */
    .titulo-painel {
        font-size: 26px;
        font-weight: 700;
        color: #1E3A8A; /* Azul escuro elegante */
        margin-bottom: 0px;
        padding-bottom: 0px;
    }
    
    /* Subtítulo discreto */
    .subtitulo-painel {
        font-size: 14px;
        color: #6B7280; /* Cinza suave */
        margin-bottom: 20px;
    }
    </style>
"""
st.markdown(estilo_customizado, unsafe_allow_html=True)

# ==========================================
# 3. LÓGICA DE DADOS
# ==========================================
@st.cache_data
def carregar_base():
    """Lê a base de dados do Excel e trata as colunas."""
    try:
        df = pd.read_excel("base_ativa.xlsx")
        df['InstallDate'] = pd.to_datetime(df['InstallDate'])
        df['FOZ_CodigoItem__c'] = df['FOZ_CodigoItem__c'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        if 'FOZ_Periodo_de_Desconto_Restante__c' in df.columns:
            df['FOZ_Periodo_de_Desconto_Restante__c'] = pd.to_numeric(df['FOZ_Periodo_de_Desconto_Restante__c'], errors='coerce').fillna(0)
        else:
            df['FOZ_Periodo_de_Desconto_Restante__c'] = 0
            
        return df
    except FileNotFoundError:
        return None

df_clientes = carregar_base()

# ==========================================
# 4. INTERFACE VISUAL (CABEÇALHO)
# ==========================================
st.markdown('<div class="titulo-painel">📞 Portal de Elegibilidade de Ofertas</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-painel">Verificação rápida de travas contratuais para retenção</div>', unsafe_allow_html=True)
st.divider() # Linha sutil separando o cabeçalho do conteúdo

if df_clientes is None:
    st.error("⚠️ Arquivo 'base_ativa.xlsx' não encontrado na pasta. Peça ao suporte para adicionar o arquivo.")
else:
    # ==========================================
    # 5. LAYOUT: DIVISÃO DA TELA
    # ==========================================
    # Criamos 3 colunas: Busca (tamanho 3), Espaço vazio (tamanho 0.5) e Resultados (tamanho 8)
    col_busca, col_espaco, col_resultado = st.columns([3, 0.5, 8])

    # --- ÁREA DE BUSCA (ESQUERDA) ---
    with col_busca:
        with st.container(border=True):
            st.markdown("#### 🔍 Consulta de Contrato")
            contrato_input = st.text_input("Número do Asset (Contrato):", placeholder="Ex: 123456").strip()
            # type="primary" deixa o botão azul e em destaque
            buscar = st.button("Verificar Elegibilidade", type="primary", use_container_width=True)

    # --- ÁREA DE RESULTADOS (DIREITA) ---
    with col_resultado:
        if buscar:
            if contrato_input == "":
                st.warning("⚠️ Por favor, digite um número de contrato.")
            else:
                cliente = df_clientes[df_clientes['FOZ_CodigoItem__c'] == contrato_input]

                if cliente.empty:
                    st.error(f"❌ Contrato **{contrato_input}** não encontrado na base ativa.")
                else:
                    data_instalacao = cliente.iloc[0]['InstallDate']
                    valor_mensalidade = float(cliente.iloc[0]['FOZ_ValorTotal__c'])
                    meses_desconto = float(cliente.iloc[0]['FOZ_Periodo_de_Desconto_Restante__c'])
                    dias_contrato = (datetime.now() - data_instalacao).days

                    st.markdown(f"#### 📊 Resumo do Contrato: **{contrato_input}**")
                    
                    # Métricas em caixas separadas e estilizadas
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        with st.container(border=True):
                            st.metric("⏳ Tempo Instalado", f"{dias_contrato} dias")
                    with m2:
                        with st.container(border=True):
                            st.metric("💲 Mensalidade", f"R$ {valor_mensalidade:.2f}")
                    with m3:
                        with st.container(border=True):
                            st.metric("🏷️ Desconto Restante", f"{int(meses_desconto)} meses")

                    st.markdown("<br>", unsafe_allow_html=True) # Dá um pequeno respiro (espaço)
                    
                    # --- LÓGICA DE TRAVAS E RESULTADO FINAL ---
                    trava_tempo = dias_contrato > 90
                    trava_valor = valor_mensalidade > 70.00
                    trava_oferta_ativa = meses_desconto <= 0

                    if trava_tempo and trava_valor and trava_oferta_ativa:
                        st.success("✅ **Cliente Elegível para Retenção!**")
                        st.info("🎯 Você pode seguir com as ofertas que aparecerem no **SalesForce**.")
                    else:
                        st.error("⛔ **Cliente NÃO Elegível para Ofertas de Retenção.**")
                        
                        motivos = []
                        if not trava_tempo:
                            motivos.append("Tempo de contrato inferior a 90 dias.")
                        if not trava_valor:
                            motivos.append("Valor da mensalidade não atinge o mínimo de R$ 70,00.")
                        if not trava_oferta_ativa:
                            motivos.append(f"Cliente já possui oferta ativa ({int(meses_desconto)} meses restantes).")
                        
                        # Mostra os motivos em uma caixa de aviso amarela limpa
                        motivos_formatados = "\n".join([f"- {m}" for m in motivos])
                        st.warning(f"**Motivos do bloqueio:**\n{motivos_formatados}\n\n⚠️ **É necessário seguir o fluxo de retenção por argumentação.**")