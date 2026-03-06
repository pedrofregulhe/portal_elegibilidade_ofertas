import streamlit as st
import pandas as pd
from datetime import datetime
import re
from simple_salesforce import Salesforce

# ==========================================
# CONEXÃO COM SALESFORCE (Crie st.secrets no Streamlit)
# ==========================================
@st.cache_resource
def conectar_sf():
    # O ideal é colocar esses dados no st.secrets do Streamlit para segurança
    return Salesforce(
        username='seu_usuario@empresa.com', 
        password='sua_senha', 
        security_token='seu_token_de_seguranca'
    )

sf = conectar_sf()

# ... (Mantenha seus estilos CSS e configurações da página iguais) ...

def formatar_endereco(row):
    # Sua função de endereço continua exatamente igual
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
    if cidade != 'nan' and uf != 'nan':
        endereco_base += f" - {cidade}/{uf}"
    
    return endereco_base if endereco_base else "Endereço não informado"

# ==========================================
# INTERFACE E BUSCA ONLINE
# ==========================================
st.markdown('<div class="titulo-painel">📞 Portal de Elegibilidade de Ofertas</div>', unsafe_allow_html=True)
st.divider()

col_busca, col_espaco, col_resultado = st.columns([3, 0.5, 8])

with col_busca:
    with st.container(border=True):
        st.markdown("#### 🔍 Consulta de Cliente")
        termo_input = st.text_input("Contrato, CPF ou CNPJ:", placeholder="Ex: 123456 ou 7802827876").strip()
        data_auditoria = st.date_input("Data do Atendimento a ser validado:", datetime.now())
        buscar = st.button("Buscar no Salesforce", type="primary", use_container_width=True)

with col_resultado:
    if buscar:
        if termo_input == "":
            st.warning("⚠️ Por favor, digite um número para buscar.")
        else:
            termo_limpo = re.sub(r'[^0-9]', '', termo_input).lstrip('0')
            
            # Montando a Query SOQL filtrada apenas para o que o usuário digitou
            # NOTA: Estou assumindo que a tabela principal seja 'Asset' (Ativo/Equipamento). 
            # Se for um objeto customizado, troque 'Asset' para 'FOZ_Contrato__c' ou similar.
            query_soql = f"""
                SELECT FOZ_CodigoItem__c, SerialNumber, Status, Name, AccountId, InstallDate, 
                       FOZ_Contrato_Anterior__c, FOZ_EndFranquiaForm__c, FOZ_ValorTotal__c, 
                       FOZ_Periodo_de_Desconto_Restante__c, Account.Name, Account.CNPJ__c, 
                       FOZ_EnderecoEntrega__r.FOZ_Logradouro__c, FOZ_EnderecoEntrega__r.Bairro__c, 
                       FOZ_EnderecoEntrega__r.EndCompl__c, FOZ_EnderecoEntrega__r.FOZ_Cidade__c, 
                       FOZ_EnderecoEntrega__r.UF__c
                FROM Asset
                WHERE FOZ_CodigoItem__c = '{termo_input}' 
                   OR Account.CNPJ__c = '{termo_input}' 
                   OR Account.CNPJ__c = '{termo_limpo}'
            """
            
            with st.spinner("Consultando Salesforce..."):
                try:
                    resultado_sf = sf.query_all(query_soql)
                    registros = resultado_sf['records']
                except Exception as e:
                    st.error(f"Erro ao conectar com o Salesforce: {e}")
                    registros = []

            if not registros:
                st.error(f"❌ Nenhum contrato ou documento encontrado para **{termo_input}**.")
            else:
                # O pd.json_normalize achata os dicionários aninhados que o SF retorna (ex: Account.Name)
                clientes_encontrados = pd.json_normalize(registros)
                
                # Tratamento de datas vindo do banco
                clientes_encontrados['InstallDate'] = pd.to_datetime(clientes_encontrados['InstallDate'], errors='coerce')
                
                # Tratamento de nulos para o desconto
                if 'FOZ_Periodo_de_Desconto_Restante__c' in clientes_encontrados.columns:
                    clientes_encontrados['FOZ_Periodo_de_Desconto_Restante__c'] = pd.to_numeric(clientes_encontrados['FOZ_Periodo_de_Desconto_Restante__c'], errors='coerce').fillna(0)
                else:
                    clientes_encontrados['FOZ_Periodo_de_Desconto_Restante__c'] = 0

                st.markdown(f"### 🔎 Encontramos **{len(clientes_encontrados)}** item(ns):")
                
                for index, row in clientes_encontrados.iterrows():
                    # A lógica de exibição das métricas e validação da regra (trava de tempo e valor)
                    # entra aqui exatamente igual ao seu código original.
                    
                    nome_cliente = row.get('Account.Name', 'Nome não disponível')
                    # ... resto do seu layout de cards e checagem de regras ...