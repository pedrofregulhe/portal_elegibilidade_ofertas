import streamlit as st
import pandas as pd
from datetime import datetime
import re

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
# 2. ESTILOS CSS CUSTOMIZADOS
# ==========================================
estilo_customizado = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    .titulo-painel { font-size: 26px; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; padding-bottom: 0px; }
    .subtitulo-painel { font-size: 14px; color: #6B7280; margin-bottom: 20px; }
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
        df['InstallDate'] = pd.to_datetime(df['InstallDate'], errors='coerce')
        
        # Trata o código do item (Contrato)
        if 'FOZ_CodigoItem__c' in df.columns:
            df['FOZ_CodigoItem__c'] = df['FOZ_CodigoItem__c'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        
        # Cria uma coluna de CNPJ/CPF limpa (só números) para facilitar a busca
        if 'Account.CNPJ__c' in df.columns:
            df['CNPJ_Limpo'] = df['Account.CNPJ__c'].astype(str).str.replace(r'[^0-9]', '', regex=True)
        else:
            df['CNPJ_Limpo'] = ""
            
        # Trata os meses de desconto
        if 'FOZ_Periodo_de_Desconto_Restante__c' in df.columns:
            df['FOZ_Periodo_de_Desconto_Restante__c'] = pd.to_numeric(df['FOZ_Periodo_de_Desconto_Restante__c'], errors='coerce').fillna(0)
        else:
            df['FOZ_Periodo_de_Desconto_Restante__c'] = 0
            
        return df
    except FileNotFoundError:
        return None

def formatar_endereco(row):
    """Monta o endereço ignorando campos vazios (NaN)."""
    partes = []
    logradouro = str(row.get('FOZ_EnderecoEntrega__r.FOZ_Logradouro__c', ''))
    compl = str(row.get('FOZ_EnderecoEntrega__r.EndCompl__c', ''))
    bairro = str(row.get('FOZ_EnderecoEntrega__r.Bairro__c', ''))
    cidade = str(row.get('FOZ_EnderecoEntrega__r.FOZ_Cidade__c', ''))
    uf = str(row.get('FOZ_EnderecoEntrega__r.UF__c', ''))

    if logradouro != 'nan' and logradouro.strip(): partes.append(logradouro)
    if compl != 'nan' and compl.strip(): partes.append(compl)
    if bairro != 'nan' and bairro.strip(): partes.append(bairro)
    
    endereco_base = ", ".join(partes)
    
    # Adiciona Cidade e UF no final
    if cidade != 'nan' and uf != 'nan':
        endereco_base += f" - {cidade}/{uf}"
    
    return endereco_base if endereco_base else "Endereço não informado"

df_clientes = carregar_base()

# ==========================================
# 4. INTERFACE VISUAL (CABEÇALHO)
# ==========================================
st.markdown('<div class="titulo-painel">📞 Portal de Elegibilidade de Ofertas</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-painel">Verificação rápida de travas contratuais para retenção</div>', unsafe_allow_html=True)
st.divider()

if df_clientes is None:
    st.error("⚠️ Arquivo 'base_ativa.xlsx' não encontrado na pasta. Peça ao suporte para adicionar o arquivo.")
else:
    # ==========================================
    # 5. LAYOUT E BUSCA
    # ==========================================
    col_busca, col_espaco, col_resultado = st.columns([3, 0.5, 8])

    # --- ÁREA DE BUSCA (ESQUERDA) ---
    with col_busca:
        with st.container(border=True):
            st.markdown("#### 🔍 Consulta de Cliente")
            termo_input = st.text_input("Contrato, CPF ou CNPJ:", placeholder="Apenas números...").strip()
            buscar = st.button("Buscar", type="primary", use_container_width=True)

    # --- ÁREA DE RESULTADOS (DIREITA) ---
    with col_resultado:
        if buscar:
            if termo_input == "":
                st.warning("⚠️ Por favor, digite um número para buscar.")
            else:
                # Limpa o input do usuário (deixa só números para comparar com CPF/CNPJ)
                termo_limpo = re.sub(r'[^0-9]', '', termo_input)
                
                # Procura no Contrato (exato) OU no CNPJ Limpo (se existir a coluna)
                mask_contrato = df_clientes['FOZ_CodigoItem__c'] == termo_input
                mask_cnpj = df_clientes['CNPJ_Limpo'] == termo_limpo if termo_limpo != "" else False
                
                clientes_encontrados = df_clientes[mask_contrato | mask_cnpj]

                if clientes_encontrados.empty:
                    st.error(f"❌ Nenhum contrato ou documento encontrado para **{termo_input}** na base ativa.")
                else:
                    st.markdown(f"### 🔎 Encontramos **{len(clientes_encontrados)}** item(ns) ativo(s):")
                    
                    # Itera sobre todos os itens encontrados (útil para quando busca por CPF)
                    for index, row in clientes_encontrados.iterrows():
                        nome_cliente = row.get('Account.Name', 'Nome não disponível')
                        if str(nome_cliente) == 'nan': nome_cliente = 'Nome não disponível'
                        
                        documento = row.get('Account.CNPJ__c', '')
                        contrato = row['FOZ_CodigoItem__c']
                        endereco_completo = formatar_endereco(row)

                        with st.container(border=True):
                            # Cabeçalho do Card
                            st.markdown(f"#### 📄 Contrato: {contrato} | {nome_cliente}")
                            st.caption(f"**Doc:** {documento} &nbsp; | &nbsp; 📍 **Endereço:** {endereco_completo}")
                            
                            # Dados para cálculos
                            data_instalacao = row['InstallDate']
                            # Tratamento para caso a data de instalação seja nula
                            if pd.isna(data_instalacao):
                                dias_contrato = 0
                            else:
                                dias_contrato = (datetime.now() - data_instalacao).days
                                
                            valor_mensalidade = float(row.get('FOZ_ValorTotal__c', 0))
                            meses_desconto = float(row.get('FOZ_Periodo_de_Desconto_Restante__c', 0))

                            # Métricas
                            m1, m2, m3 = st.columns(3)
                            with m1:
                                st.metric("⏳ Tempo Instalado", f"{dias_contrato} dias")
                            with m2:
                                st.metric("💲 Mensalidade", f"R$ {valor_mensalidade:.2f}")
                            with m3:
                                st.metric("🏷️ Desconto Restante", f"{int(meses_desconto)} meses")
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            # --- LÓGICA DE TRAVAS ---
                            trava_tempo = dias_contrato > 90
                            trava_valor = valor_mensalidade > 70.00
                            trava_oferta_ativa = meses_desconto <= 0

                            if trava_tempo and trava_valor and trava_oferta_ativa:
                                st.success("✅ **Elegível para Retenção!** Pode seguir com as ofertas no SalesForce.")
                            else:
                                motivos = []
                                if not trava_tempo:
                                    motivos.append("Tempo de contrato inferior a 90 dias.")
                                if not trava_valor:
                                    motivos.append("Mensalidade não atinge R$ 70,00.")
                                if not trava_oferta_ativa:
                                    motivos.append(f"Já possui oferta ativa ({int(meses_desconto)} meses restantes).")
                                
                                motivos_formatados = "\n".join([f"- {m}" for m in motivos])
                                st.error(f"⛔ **NÃO Elegível para Ofertas de Retenção.**\n\n**Motivos:**\n{motivos_formatados}")