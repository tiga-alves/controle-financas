import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

# Arquivo para armazenar as transações
TRANSACTIONS_FILE = "transacoes.csv"

# Definindo as subcategorias
SUBCATEGORIAS = {
    "Despesa": ["Gastos Essenciais", "Dívidas", "Outros gastos"],
    "Receita": ["Salário Regular", "Adto. Salarial", "Outra Fonte"]
}

def carregar_transacoes():
    if os.path.exists(TRANSACTIONS_FILE):
        df = pd.read_csv(TRANSACTIONS_FILE)
        df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%Y-%m-%d')
        return df
    else:
        return pd.DataFrame({
            'Data': pd.Series(dtype='str'),
            'Descrição': pd.Series(dtype='str'),
            'Tipo': pd.Series(dtype='str'),
            'Subcategoria': pd.Series(dtype='str'),
            'Valor': pd.Series(dtype='float64')
        })

def salvar_transacoes(transacoes):
    transacoes.to_csv(TRANSACTIONS_FILE, index=False)

def filtrar_mes_atual(df):
    hoje = pd.Timestamp.now()
    df['Data'] = pd.to_datetime(df['Data'])
    resultado = df[df['Data'].dt.to_period('M') == hoje.to_period('M')]
    resultado['Data'] = resultado['Data'].dt.strftime('%Y-%m-%d')
    return resultado

def filtrar_ultimos_12_meses(df):
    hoje = pd.Timestamp.now()
    doze_meses_atras = hoje - pd.DateOffset(months=11)
    df['Data'] = pd.to_datetime(df['Data'])
    resultado = df[df['Data'] >= doze_meses_atras]
    resultado['Data'] = resultado['Data'].dt.strftime('%Y-%m-%d')
    return resultado

# Inicializar o estado da sessão
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_transacoes()

def adicionar_transacao():
    data = pd.to_datetime(st.session_state.data).strftime('%Y-%m-%d')
    descricao = st.session_state.descricao
    valor = float(st.session_state.valor)
    tipo_transacao = st.session_state.tipo_transacao
    subcategoria = st.session_state.subcategoria
    
    nova_transacao = pd.DataFrame({
        'Data': [data],
        'Descrição': [descricao],
        'Tipo': [tipo_transacao],
        'Subcategoria': [subcategoria],
        'Valor': [valor]
    })
    st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
    salvar_transacoes(st.session_state.transacoes)

def remover_transacao():
    indice_remover = st.session_state.indice_remover
    if 0 <= indice_remover < len(st.session_state.transacoes):
        st.session_state.transacoes = st.session_state.transacoes.drop(indice_remover).reset_index(drop=True)
        salvar_transacoes(st.session_state.transacoes)
        st.success("Transação removida com sucesso!")
    else:
        st.error("Índice inválido. Por favor, insira um índice válido para remover.")

def main():
    st.title("Finanças Pessoais")

    # Barra lateral para adicionar transações
    st.sidebar.header("Adicionar Transação")
    st.sidebar.date_input("Data", key="data")
    st.sidebar.text_input("Descrição", key="descricao")
    st.sidebar.number_input("Valor", min_value=0.01, step=0.01, key="valor")
    tipo_transacao = st.sidebar.selectbox("Tipo", ["Despesa", "Receita"], key="tipo_transacao")
    subcategoria = st.sidebar.selectbox("Subcategoria", SUBCATEGORIAS[tipo_transacao], key="subcategoria")
    st.sidebar.button("Adicionar Transação", on_click=adicionar_transacao)

    # Barra lateral para remover transações
    st.sidebar.header("Remover Transação")
    st.sidebar.number_input("Índice para remover", min_value=0, step=1, key="indice_remover")
    st.sidebar.button("Remover Transação", on_click=remover_transacao)

    # Filtrar transações para o mês atual
    transacoes_mes_atual = filtrar_mes_atual(st.session_state.transacoes)

    # Área principal para exibir transações do mês atual
    st.header("Transações do Mês Atual")
    st.dataframe(transacoes_mes_atual)

    # Estatísticas resumidas do mês atual
    if not transacoes_mes_atual.empty:
        total_despesas = transacoes_mes_atual[transacoes_mes_atual['Tipo'] == 'Despesa']['Valor'].sum()
        total_receitas = transacoes_mes_atual[transacoes_mes_atual['Tipo'] == 'Receita']['Valor'].sum()
        saldo = total_receitas - total_despesas

        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Despesas (Mês Atual)", f"R$ {total_despesas:.2f}")
        col2.metric("Total de Receitas (Mês Atual)", f"R$ {total_receitas:.2f}")
        col3.metric("Saldo (Mês Atual)", f"R$ {saldo:.2f}")

        # Gráfico de barras agrupadas de despesas e receitas dos últimos 12 meses
        transacoes_12_meses = filtrar_ultimos_12_meses(st.session_state.transacoes)
        transacoes_12_meses['Mês'] = pd.to_datetime(transacoes_12_meses['Data']).dt.to_period('M')
        dados_mensais = transacoes_12_meses.groupby(['Mês', 'Tipo'])['Valor'].sum().unstack(fill_value=0).reset_index()
        dados_mensais['Mês'] = dados_mensais['Mês'].astype(str)

        if not dados_mensais.empty and 'Despesa' in dados_mensais.columns and 'Receita' in dados_mensais.columns:
            fig_barras = go.Figure(data=[
                go.Bar(name='Despesas', x=dados_mensais['Mês'], y=dados_mensais['Despesa'], marker_color='#FF9999'),  # Vermelho claro
                go.Bar(name='Receitas', x=dados_mensais['Mês'], y=dados_mensais['Receita'], marker_color='#90EE90')  # Verde claro
            ])
            fig_barras.update_layout(title='Despesas e Receitas dos Últimos 12 Meses', barmode='group', xaxis_title='Mês', yaxis_title='Valor')
            st.plotly_chart(fig_barras)
        
        # Gráfico de pizza das despesas por subcategoria (mês atual)
        despesas_por_subcategoria = transacoes_mes_atual[transacoes_mes_atual['Tipo'] == 'Despesa']
        if not despesas_por_subcategoria.empty:
            fig_pizza = px.pie(despesas_por_subcategoria, values='Valor', names='Subcategoria', title='Despesas por Subcategoria (Mês Atual)')
            fig_pizza.update_traces(marker=dict(colors=['#FF9999', '#FFCC99', '#FFFF99']))  # Cores diferentes para cada subcategoria
            st.plotly_chart(fig_pizza)

        

if __name__ == "__main__":
    main()