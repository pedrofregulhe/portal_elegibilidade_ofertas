import streamlit as st
import pandas as pd
from datetime import datetime
import re
from simple_salesforce import Salesforce

# ==========================================
# 0. CONSTANTES 
# ==========================================
# Objeto correto no Salesforce
OBJETO_SALESFORCE = "Asset" 

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
# 3. CONEXÃO SALESFORCE E LÓGICA DE DADOS
# ==========================================
@st.cache_resource
def iniciar_conexao_sf():
    """Inicia a conexão com o Salesforce de forma segura usando st.secrets"""
    try:
        sf = Salesforce(
            username=st.secrets["salesforce"]["username"],
            password=st.secrets["salesforce"]["password"],
            security_token=st.secrets["salesforce"]["security_token"],
            domain=st.secrets["salesforce"].get("domain", "login")
        )
        return sf
    except Exception as e:
        st.error(f"Erro ao conectar no Salesforce: Verifique as credenciais no st.secrets. Detalhe: {e}")
        return None

def formatar_mascara_doc(termo_limpo):
    """Aplica a máscara padrão de CPF ou CNPJ baseada no tamanho."""
    if len(termo_limpo) == 11:
        return f"{termo_limpo[:3]}.{termo_limpo[3:6]}.{termo_limpo[6:9]}-{termo_limpo[9:]}"
    elif len(termo_limpo) == 14:
        return f"{termo_limpo[:2]}.{termo_limpo[2:5]}.{termo_limpo[5:8]}/{termo_limpo[8:12]}-{termo_limpo[12:]}"
    return termo_limpo

def buscar_cliente_sf(sf, termo_busca):
    """Faz a query no Salesforce considerando as variações de digitação."""
    
    termo_limpo = re.sub(r'[^0-9]', '', termo_busca)
    
    if not termo_limpo:
        return pd.DataFrame()

    doc_mascarado = formatar_mascara_doc(termo_limpo)
    
    query = f"""
        SELECT 
            FOZ_CodigoItem__c, SerialNumber, Status, Name, AccountId, InstallDate, 
            FOZ_Contrato_Anterior__c, FOZ_EndFranquiaForm__c, FOZ_ValorTotal__c, 
            FOZ_Periodo_de_Desconto_Restante__c, 
            Account.Name, Account.CNPJ__c, 
            FOZ_EnderecoEntrega__r.FOZ_Logradouro__c, FOZ_EnderecoEntrega__r.Bairro__c, 
            FOZ_EnderecoEntrega__r.EndCompl__c, FOZ_EnderecoEntrega__r.FOZ_Cidade__c, 
            FOZ_EnderecoEntrega__r.UF__c
        FROM {OBJETO_SALESFORCE}
        WHERE 
            FOZ_CodigoItem__c LIKE '%{termo_limpo}' 
            OR Account.CNPJ__c = '{termo_limpo}' 
            OR Account.CNPJ__c = '{doc_mascarado}'
    """
    
    try:
        resultado = sf.query(query)
        if resultado['totalSize'] == 0:
            return pd.DataFrame()
        
        df = pd.json_normalize(resultado['records'])
        
        if 'InstallDate' in df.columns:
            df['InstallDate'] = pd.to_datetime(df['InstallDate'], errors='coerce')
            
        if 'FOZ_Periodo_de_Desconto_Restante__c' in df.columns:
            df['FOZ_Periodo_de_Desconto_Restante__c'] = pd.to_numeric(df['FOZ_Periodo_de_Desconto_Restante__c'], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Erro na query SOQL: {e}")
        return pd.DataFrame()

def formatar_endereco(row):
    """Monta o endereço de forma segura com os dados da API."""
    partes = []
    logradouro = str(row.get('FOZ_EnderecoEntrega__r.FOZ_Logradouro__c', ''))
    compl = str(row.get('FOZ_EnderecoEntrega__r.EndCompl__c', ''))
    bairro = str(row.get('FOZ_EnderecoEntrega__r.Bairro__c', ''))
    cidade = str(row.get('FOZ_EnderecoEntrega__r.FOZ_Cidade__c', ''))
    uf = str(row.get('FOZ_EnderecoEntrega__r.UF__c', ''))

    for p in [logradouro, compl, bairro]:
        if p and p.lower() != 'nan' and p.lower() != 'none':
            partes.append(p)
            
    endereco_base = ", ".join(partes)
    
    if cidade and uf and cidade.lower() != 'nan' and uf.lower() != 'nan':
        endereco_base += f" - {cidade}/{uf}"
    
    return endereco_base if endereco_base else "Endereço não informado"

# ==========================================
# 4. INTERFACE VISUAL (CABEÇALHO)
# ==========================================
st.markdown('<div class="titulo-painel">📞 Portal de Elegibilidade de Ofertas</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitulo-painel">Verificação rápida e online (Salesforce) para retenção</div>', unsafe_allow_html=True)
st.divider()

sf_conexao = iniciar_conexao_sf()

if not sf_conexao:
    st.warning("⚠️ Aguardando configuração das credenciais no Streamlit Cloud (Secrets) para conectar ao Salesforce.")
    st.stop() 

# ==========================================
# 5. LAYOUT E BUSCA
# ==========================================
col_busca, col_espaco, col_resultado = st.columns([3, 0.5, 8])

with col_busca:
    with st.container(border=True):
        st.markdown("#### 🔍 Consulta de Cliente")
        termo_input = st.text_input("Contrato, CPF ou CNPJ:", placeholder="Ex: 1466 ou 7802827876").strip()
        buscar = st.button("Buscar no Salesforce", type="primary", use_container_width=True)

with col_resultado:
    if buscar:
        if termo_input == "":
            st.warning("⚠️ Por favor, digite um número para buscar.")
        else:
            with st.spinner("Consultando dados em tempo real no Salesforce..."):
                clientes_encontrados = buscar_cliente_sf(sf_conexao, termo_input)

            if clientes_encontrados.empty:
                st.error(f"❌ Nenhum contrato ou documento encontrado para **{termo_input}** no Salesforce.")
            else:
                st.markdown(f"### 🔎 Encontramos **{len(clientes_encontrados)}** item(ns):")
                
                for index, row in clientes_encontrados.iterrows():
                    nome_cliente = row.get('Account.Name', 'Nome não disponível')
                    if pd.isna(nome_cliente): nome_cliente = 'Nome não disponível'
                    
                    documento = row.get('Account.CNPJ__c', 'Doc não informado')
                    if pd.isna(documento): documento = 'Doc não informado'
                        
                    contrato = row.get('FOZ_CodigoItem__c', 'S/N')
                    endereco_completo = formatar_endereco(row)

                    with st.container(border=True):
                        st.markdown(f"#### 📄 Nº Item do Contrato: {contrato} | {nome_cliente}")
                        st.caption(f"**Doc:** {documento} &nbsp; | &nbsp; 📍 **Endereço:** {endereco_completo}")
                        
                        data_instalacao = row.get('InstallDate')
                        if pd.isna(data_instalacao):
                            dias_contrato = 0
                        else:
                            data_instalacao = data_instalacao.tz_localize(None) 
                            dias_contrato = (datetime.now() - data_instalacao).days
                            
                        valor_mensalidade = float(row.get('FOZ_ValorTotal__c', 0) or 0)
                        meses_desconto = float(row.get('FOZ_Periodo_de_Desconto_Restante__c', 0) or 0)

                        m1, m2, m3 = st.columns(3)
                        with m1:
                            st.metric("⏳ Tempo Instalado", f"{dias_contrato} dias")
                        with m2:
                            st.metric("💲 Mensalidade", f"R$ {valor_mensalidade:.2f}")
                        with m3:
                            st.metric("🏷️ Desconto Restante", f"{int(meses_desconto)} meses")
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        trava_tempo = dias_contrato > 90
                        trava_valor = valor_mensalidade > 70.00
                        trava_oferta_ativa = meses_desconto <= 0

                        if trava_tempo and trava_valor and trava_oferta_ativa:
                            st.success("✅ **Cliente Elegível para Retenção!**")
                            st.info("🎯 Você pode seguir com as ofertas que aparecerem no **Salesforce**.")
                        else:
                            st.error("⛔ **Cliente NÃO Elegível para Ofertas de Retenção.**")
                            
                            motivos = []
                            if not trava_tempo:
                                motivos.append("Tempo de contrato inferior a 90 dias.")
                            if not trava_valor:
                                motivos.append("Valor da mensalidade não atinge o mínimo de R$ 70,00.")
                            if not trava_oferta_ativa:
                                motivos.append(f"Cliente já possui oferta ativa ({int(meses_desconto)} meses restantes).")
                            
                            motivos_formatados = "\n".join([f"- {m}" for m in motivos])
                            st.warning(f"**Motivos do bloqueio:**\n{motivos_formatados}\n\n⚠️ **É necessário seguir o fluxo de retenção por argumentação.**")
