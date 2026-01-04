"""
Streamlit App para Cálculo de Paridade - Açúcar VHP
Interface focada no cálculo detalhado do açúcar VHP.
"""

import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Paridade Açúcar VHP", layout="wide")

# Arquivo para salvar os valores da sidebar
SIDEBAR_CONFIG_FILE = "sidebar_config.json"

# ============================================================================
# CONSTANTES
# ============================================================================

# Fator de conversão de c/lb para toneladas
FATOR_CONVERSAO_CENTS_LB_PARA_TON = 22.0462

# Sacas por tonelada
SACAS_POR_TON = 20

# Fator de conversão para etanol anidro (litros por saca de açúcar)
FATOR_ETANOL_ANIDRO_LITROS_POR_SACA = 32.669

# Fator de conversão para etanol hidratado (litros por saca de açúcar)
FATOR_ETANOL_HIDRATADO_LITROS_POR_SACA = 31.304

# Fator de conversão para etanol anidro mercado interno (litros por saca de açúcar)
FATOR_ETANOL_ANIDRO_MI_LITROS_POR_SACA = 33.712

# Fator de conversão para etanol hidratado mercado interno (litros por saca de açúcar)
FATOR_ETANOL_HIDRATADO_MI_LITROS_POR_SACA = 31.504

# Fator de conversão hidratado (percentual)
FATOR_CONVERSAO_HIDRATADO = 0.0769

# Fator CBIO anidro
FATOR_CBIO_FC_ANIDRO = 712.4

# Fator CBIO hidratado
FATOR_CBIO_FC_HIDRATADO = 749.75

# Crédito tributário
CREDITO_TRIBUTARIO = 240

# Fator de ajuste para etanol
FATOR_AJUSTE_ETANOL = 1.042

# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

def fmt_br(valor, casas=2):
    """
    Formata número no padrão brasileiro: 1.234.567,89
    
    Args:
        valor: Número a formatar
        casas: Número de casas decimais
    
    Returns:
        str: Número formatado no padrão brasileiro
    """
    if valor is None:
        return ""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

def load_sidebar_config():
    """
    Carrega os valores salvos da sidebar de um arquivo JSON.
    
    Returns:
        dict: Dicionário com os valores salvos ou valores padrão
    """
    default_values = {
        'cambio_brl_usd': 5.35,
        'acucar_ny_cents_lb': 15.8,
        'premio_desconto_vhp': -0.1,
        'premio_pol_vhp': 4.2,
        'custo_terminal_vhp_usd_ton': 12.5,
        'frete_vhp_brl_ton': 202.0,
        'preco_esalq_brl_saca': 115.67,
        'imposto_esalq': 9.85,
        'frete_santos_usina_brl_ton': 202.0,
        'custo_fobizacao_container_brl_ton': 198.0,
        'custo_vhp_para_cristal': 9.25,
        'premio_fisico_mi': 0.0,
        'premio_fisico_exportacao': 0.0,
        'premio_fisico_exportacao_malha30': 0.0,
        'preco_anidro_fob_usd': 0.0,
        'frete_etanol_porto_usina': 0.0,
        'custo_terminal_etanol': 0.0,
        'custo_supervisao_documentos': 0.0,
        'custos_adicionais_demurrage': 0.0,
        'preco_hidratado_fob_usd': 0.0,
        'preco_anidro_com_impostos_brl': 0.0,
        'pis_cofins_brl': 0.0,
        'contribuicao_agroindustria': 0.0,
        'valor_cbio_bruto': 0.0,
        'preco_hidratado_com_impostos_brl': 0.0,
        'icms_percentual': 0.0,
    }
    
    if os.path.exists(SIDEBAR_CONFIG_FILE):
        try:
            with open(SIDEBAR_CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_values = json.load(f)
                # Mescla valores salvos com padrões (para garantir que novos campos tenham valores padrão)
                default_values.update(saved_values)
                return default_values
        except Exception as e:
            st.warning(f"Erro ao carregar configurações salvas: {e}")
    
    return default_values

def save_sidebar_config(values):
    """
    Salva os valores da sidebar em um arquivo JSON.
    
    Args:
        values: dict com os valores a serem salvos
    """
    try:
        with open(SIDEBAR_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(values, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Erro ao salvar configurações: {e}")

# ============================================================================
# FUNÇÃO DE CÁLCULO DO AÇÚCAR VHP
# ============================================================================

def calc_acucar_vhp_detalhado(inputs, globais):
    """
    Calcula o açúcar VHP com desenvolvimento detalhado do cálculo.
    
    Args:
        inputs: dict com:
            - acucar_ny_cents_lb: Preço do açúcar NY em c/lb (centavos por libra)
            - premio_desconto: Prêmio/desconto em c/lb (pode ser decimal ou inteiro)
            - premio_pol: Prêmio de pol (número que será tratado como percentual)
            - custo_terminal_usd_ton: Custo de terminal em USD/ton
            - frete_brl_ton: Frete em BRL/ton
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
    
    Returns:
        dict: {
            'values': {
                'sugar_ny_mais_pol_cents_lb': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'desenvolvimento': {...}  # Detalhamento do cálculo
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    desenvolvimento = {}
    
    try:
        # Entradas
        acucar_ny_cents_lb = inputs.get('acucar_ny_cents_lb', 0)
        premio_desconto = inputs.get('premio_desconto', 0)
        premio_pol = inputs.get('premio_pol', 0)  # Será tratado como percentual
        custo_terminal_usd_ton = inputs.get('custo_terminal_usd_ton', 0)
        frete_brl_ton = inputs.get('frete_brl_ton', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # ====================================================================
        # PASSO 1: Calcular Sugar NY + Pol
        # Fórmula: (Açúcar NY + prêmio/desconto) * (1 + prêmio pol%)
        # ====================================================================
        
        # Converte prêmio de pol para percentual (se > 1, assume que está em %, senão assume decimal)
        premio_pol_percentual = premio_pol / 100 if premio_pol > 1 else premio_pol
        
        # Calcula Sugar NY + Pol
        sugar_ny_mais_pol_cents_lb = (acucar_ny_cents_lb + premio_desconto) * (1 + premio_pol_percentual)
        
        # Armazena desenvolvimento do Passo 1
        desenvolvimento['passo1'] = {
            'descricao': 'Cálculo Sugar NY + Pol',
            'formula': '(Açúcar NY + Prêmio/Desconto) × (1 + Prêmio Pol%)',
            'valores': {
                'acucar_ny_cents_lb': acucar_ny_cents_lb,
                'premio_desconto_cents_lb': premio_desconto,
                'premio_pol_percentual': premio_pol_percentual,
                'soma_ny_premio': acucar_ny_cents_lb + premio_desconto,
                'fator_pol': 1 + premio_pol_percentual,
                'resultado_cents_lb': sugar_ny_mais_pol_cents_lb
            }
        }
        
        # ====================================================================
        # PASSO 2: Calcular Equivalente VHP Reais/saca PVU
        # Fórmula: (((Sugar NY+pol * 22.0462) - custo de terminal - (frete Reais por ton/câmbio))/20) * Câmbio
        # ====================================================================
        
        # 1. Conversão de c/lb para USD/ton
        sugar_ny_mais_pol_usd_ton = sugar_ny_mais_pol_cents_lb * FATOR_CONVERSAO_CENTS_LB_PARA_TON
        
        # 2. Conversão do frete de BRL/ton para USD/ton
        frete_usd_ton = frete_brl_ton / cambio_brl_usd
        
        # 3. Cálculo do valor líquido em USD/ton
        valor_usd_ton = sugar_ny_mais_pol_usd_ton - custo_terminal_usd_ton - frete_usd_ton
        
        # 4. Divisão por 20 (sacas por tonelada) para obter USD/saca
        valor_usd_saca = valor_usd_ton / SACAS_POR_TON
        
        # 5. Conversão para BRL/saca multiplicando pelo câmbio
        equivalente_vhp_reais_saca_pvu = valor_usd_saca * cambio_brl_usd
        
        # Armazena desenvolvimento do Passo 2
        desenvolvimento['passo2'] = {
            'descricao': 'Cálculo Equivalente VHP Reais/saca PVU',
            'formula': '(((Sugar NY+pol × 22.0462) - Custo Terminal - (Frete BRL/ton ÷ Câmbio)) ÷ 20) × Câmbio',
            'valores': {
                'sugar_ny_mais_pol_cents_lb': sugar_ny_mais_pol_cents_lb,
                'fator_conversao': FATOR_CONVERSAO_CENTS_LB_PARA_TON,
                'sugar_ny_mais_pol_usd_ton': sugar_ny_mais_pol_usd_ton,
                'custo_terminal_usd_ton': custo_terminal_usd_ton,
                'frete_brl_ton': frete_brl_ton,
                'cambio_brl_usd': cambio_brl_usd,
                'frete_usd_ton': frete_usd_ton,
                'valor_usd_ton': valor_usd_ton,
                'sacas_por_ton': SACAS_POR_TON,
                'valor_usd_saca': valor_usd_saca,
                'resultado_brl_saca': equivalente_vhp_reais_saca_pvu
            }
        }
        
        # ====================================================================
        # PASSO 3: Calcular Equivalente VHP c/lb PVU
        # Fórmula: ((Equivalente VHP Reais/saca PVU * 20) / 22.0462) / câmbio
        # ====================================================================
        
        equivalente_vhp_cents_lb_pvu = ((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd
        
        desenvolvimento['passo3'] = {
            'descricao': 'Cálculo Equivalente VHP c/lb PVU',
            'formula': '((Equivalente VHP Reais/saca PVU × 20) ÷ 22.0462) ÷ Câmbio',
            'valores': {
                'equivalente_vhp_reais_saca_pvu': equivalente_vhp_reais_saca_pvu,
                'sacas_por_ton': SACAS_POR_TON,
                'fator_conversao': FATOR_CONVERSAO_CENTS_LB_PARA_TON,
                'cambio_brl_usd': cambio_brl_usd,
                'resultado_cents_lb_pvu': equivalente_vhp_cents_lb_pvu
            }
        }
        
        # ====================================================================
        # PASSO 4: Equivalente VHP c/lb FOB
        # Fórmula: igual ao Sugar NY + Pol
        # ====================================================================
        
        equivalente_vhp_cents_lb_fob = sugar_ny_mais_pol_cents_lb
        
        desenvolvimento['passo4'] = {
            'descricao': 'Equivalente VHP c/lb FOB',
            'formula': 'Igual ao Sugar NY + Pol',
            'valores': {
                'sugar_ny_mais_pol_cents_lb': sugar_ny_mais_pol_cents_lb,
                'resultado_cents_lb_fob': equivalente_vhp_cents_lb_fob
            }
        }
        
        # Armazena resultados
        values['sugar_ny_mais_pol_cents_lb'] = sugar_ny_mais_pol_cents_lb
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['desenvolvimento'] = desenvolvimento
        
    except Exception as e:
        errors.append(f"Erro ao calcular açúcar VHP: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_acucar_cristal_esalq(inputs, globais):
    """
    Calcula o açúcar cristal ESALQ com desenvolvimento detalhado do cálculo.
    
    Args:
        inputs: dict com:
            - preco_esalq_brl_saca: Preço ESALQ em R$/saca
            - imposto: Imposto (número que será tratado como percentual)
            - frete_santos_usina_brl_ton: Frete Santos-Usina em R$/Ton
            - custo_fobizacao_container_brl_ton: Custo de Fobização do container em R$/Ton
            - custo_vhp_para_cristal: Custo para transformar VHP em Cristal
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - custo_terminal_usd_ton: Custo de terminal em USD/ton (do açúcar VHP)
    
    Returns:
        dict: {
            'values': {
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        preco_esalq_brl_saca = inputs.get('preco_esalq_brl_saca', 0)
        imposto = inputs.get('imposto', 0)  # Será tratado como percentual
        frete_santos_usina_brl_ton = inputs.get('frete_santos_usina_brl_ton', 0)
        custo_fobizacao_container_brl_ton = inputs.get('custo_fobizacao_container_brl_ton', 0)
        custo_vhp_para_cristal = inputs.get('custo_vhp_para_cristal', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # Converte imposto para percentual (se > 1, assume que está em %, senão assume decimal)
        imposto_percentual = imposto / 100 if imposto > 1 else imposto
        
        # 1. Equivalente Cristal R$/Saca PVU
        equivalente_cristal_reais_saca_pvu = preco_esalq_brl_saca * (1 - imposto_percentual)
        
        # 2. Equivalente VHP R$/Saca PVU
        equivalente_vhp_reais_saca_pvu = equivalente_cristal_reais_saca_pvu - custo_vhp_para_cristal
        
        # 3. Equivalente VHP Cents/lb PVU
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 4. Equivalente VHP Cents/lb FOB
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_santos_usina_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd))
        
        # 5. Equivalente Cristal c/lb PVU
        equivalente_cristal_cents_lb_pvu = (((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) - (15 / FATOR_CONVERSAO_CENTS_LB_PARA_TON / cambio_brl_usd)
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Usa 22.04622 conforme especificado na fórmula
        equivalente_cristal_cents_lb_fob = (((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON) + frete_santos_usina_brl_ton + custo_fobizacao_container_brl_ton) / 22.04622) / cambio_brl_usd
        
        # Armazena resultados
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular açúcar cristal ESALQ: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_paridade_comercializacao_mi_ny(inputs, globais):
    """
    Calcula a paridade de comercialização mercado interno e externo NY.
    
    Args:
        inputs: dict com:
            - acucar_ny_cents_lb: Valor do açúcar NY em c/lb (do campo do açúcar VHP)
            - premio_fisico_mi: Prêmio/desconto de físico
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - custo_terminal_usd_ton: Custo de terminal em USD/ton
            - frete_santos_usina_brl_ton: Frete Santos-Usina em R$/Ton
            - custo_fobizacao_container_brl_ton: Custo de fobização em R$/Ton
            - custo_vhp_para_cristal: Custo para transformar VHP em Cristal
    
    Returns:
        dict: {
            'values': {
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        acucar_ny_cents_lb = inputs.get('acucar_ny_cents_lb', 0)
        premio_fisico_mi = inputs.get('premio_fisico_mi', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        frete_santos_usina_brl_ton = globais.get('frete_santos_usina_brl_ton', 0)
        custo_fobizacao_container_brl_ton = globais.get('custo_fobizacao_container_brl_ton', 0)
        custo_vhp_para_cristal = globais.get('custo_vhp_para_cristal', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # 1. Equivalente Cristal R$/Saca PVU
        # Fórmula: (((Valor do açúcar em c/lb * 22,04622) + Prêmio de físico) * Câmbio) / 20
        acucar_ny_usd_ton = acucar_ny_cents_lb * 22.04622
        acucar_com_premio_usd_ton = acucar_ny_usd_ton + premio_fisico_mi
        acucar_com_premio_brl_ton = acucar_com_premio_usd_ton * cambio_brl_usd
        equivalente_cristal_reais_saca_pvu = acucar_com_premio_brl_ton / SACAS_POR_TON
        
        # 2. Equivalente VHP R$/saca PVU
        equivalente_vhp_reais_saca_pvu = equivalente_cristal_reais_saca_pvu - custo_vhp_para_cristal
        
        # 3. Equivalente VHP Cents/lb PVU
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 4. Equivalente VHP Cents/lb FOB
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_santos_usina_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd))
        
        # 5. Equivalente Cristal c/lb PVU
        equivalente_cristal_cents_lb_pvu = ((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Fórmula: ((Equivalente Cristal R$/Saca PVU * 20 + Custo de fobização + Frete Santos-Usina R$/ton) / 22,0462) / Câmbio
        equivalente_cristal_cents_lb_fob = ((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON + custo_fobizacao_container_brl_ton + frete_santos_usina_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd
        
        # Armazena resultados
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular custo de comercialização açúcar cristal MI: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_acucar_cristal_exportacao(inputs, globais):
    """
    Calcula o açúcar cristal para exportação.
    
    Args:
        inputs: dict com:
            - acucar_ny_cents_lb: Valor do açúcar NY em c/lb (do campo do açúcar VHP)
            - premio_fisico_exportacao: Prêmio/desconto de físico de exportação
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - custo_terminal_usd_ton: Custo de terminal em USD/ton
            - frete_brl_ton: Frete em R$/Ton
            - custo_fobizacao_container_brl_ton: Custo de fobização em R$/Ton
            - custo_vhp_para_cristal: Custo para transformar VHP em Cristal
    
    Returns:
        dict: {
            'values': {
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        acucar_ny_cents_lb = inputs.get('acucar_ny_cents_lb', 0)
        premio_fisico_exportacao = inputs.get('premio_fisico_exportacao', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_fobizacao_container_brl_ton = globais.get('custo_fobizacao_container_brl_ton', 0)
        custo_vhp_para_cristal = globais.get('custo_vhp_para_cristal', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # 1. Equivalente Cristal R$/Saca PVU
        # Fórmula: (((Valor em c/lb * 22,04622) + Prêmio/Desconto de Físico de exportação) * Câmbio - Custo de fobização - custo de frete R$/Ton) / 20
        acucar_ny_usd_ton = acucar_ny_cents_lb * 22.04622
        acucar_com_premio_usd_ton = acucar_ny_usd_ton + premio_fisico_exportacao
        acucar_com_premio_brl_ton = acucar_com_premio_usd_ton * cambio_brl_usd
        equivalente_cristal_reais_saca_pvu = (acucar_com_premio_brl_ton - custo_fobizacao_container_brl_ton - frete_brl_ton) / SACAS_POR_TON
        
        # 2. Equivalente VHP R$/saca PVU
        equivalente_vhp_reais_saca_pvu = equivalente_cristal_reais_saca_pvu - custo_vhp_para_cristal
        
        # 3. Equivalente VHP Cents/lb PVU
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 4. Equivalente VHP Cents/lb FOB
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd))
        
        # 5. Equivalente Cristal c/lb PVU
        equivalente_cristal_cents_lb_pvu = ((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Fórmula: (((Valor em c/lb * 22,04622) + Prêmio/Desconto de Físico de exportação) / 22,0462
        equivalente_cristal_cents_lb_fob = ((acucar_ny_cents_lb * 22.04622) + premio_fisico_exportacao) / 22.0462
        
        # Armazena resultados
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular açúcar cristal exportação: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_acucar_cristal_exportacao_malha30(inputs, globais):
    """
    Calcula o açúcar cristal para exportação malha 30.
    Os cálculos são idênticos aos do açúcar cristal exportação, mas com prêmio diferente.
    
    Args:
        inputs: dict com:
            - acucar_ny_cents_lb: Valor do açúcar NY em c/lb (do campo do açúcar VHP)
            - premio_fisico_exportacao_malha30: Prêmio/desconto de físico de exportação malha 30
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - custo_terminal_usd_ton: Custo de terminal em USD/ton
            - frete_brl_ton: Frete em R$/Ton
            - custo_fobizacao_container_brl_ton: Custo de fobização em R$/Ton
            - custo_vhp_para_cristal: Custo para transformar VHP em Cristal
    
    Returns:
        dict: {
            'values': {
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        acucar_ny_cents_lb = inputs.get('acucar_ny_cents_lb', 0)
        premio_fisico_exportacao_malha30 = inputs.get('premio_fisico_exportacao_malha30', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_fobizacao_container_brl_ton = globais.get('custo_fobizacao_container_brl_ton', 0)
        custo_vhp_para_cristal = globais.get('custo_vhp_para_cristal', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # 1. Equivalente Cristal R$/Saca PVU
        # Fórmula: (((Valor em c/lb * 22,04622) + Prêmio/Desconto de Físico de exportação) * Câmbio - Custo de fobização - custo de frete R$/Ton) / 20
        acucar_ny_usd_ton = acucar_ny_cents_lb * 22.04622
        acucar_com_premio_usd_ton = acucar_ny_usd_ton + premio_fisico_exportacao_malha30
        acucar_com_premio_brl_ton = acucar_com_premio_usd_ton * cambio_brl_usd
        equivalente_cristal_reais_saca_pvu = (acucar_com_premio_brl_ton - custo_fobizacao_container_brl_ton - frete_brl_ton) / SACAS_POR_TON
        
        # 2. Equivalente VHP R$/saca PVU
        equivalente_vhp_reais_saca_pvu = equivalente_cristal_reais_saca_pvu - custo_vhp_para_cristal
        
        # 3. Equivalente VHP Cents/lb PVU
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 4. Equivalente VHP Cents/lb FOB
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd))
        
        # 5. Equivalente Cristal c/lb PVU
        equivalente_cristal_cents_lb_pvu = ((equivalente_cristal_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Fórmula: (((Valor em c/lb * 22,04622) + Prêmio/Desconto de Físico de exportação) / 22,0462
        equivalente_cristal_cents_lb_fob = ((acucar_ny_cents_lb * 22.04622) + premio_fisico_exportacao_malha30) / 22.0462
        
        # Armazena resultados
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular açúcar cristal exportação malha 30: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_etanol_anidro_exportacao(inputs, globais):
    """
    Calcula o etanol anidro para exportação.
    
    Args:
        inputs: dict com:
            - preco_anidro_fob_usd: Preço anidro FOB em USD
            - frete_etanol_porto_usina: Frete para etanol Porto/Usina
            - custo_terminal_etanol: Custo de terminal
            - custo_supervisao_documentos: Custo de supervisão de documentos
            - custos_adicionais_demurrage: Custos adicionais demurrage (se houver)
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - frete_brl_ton: Frete em R$/Ton (do cálculo do açúcar VHP)
            - custo_terminal_usd_ton: Custo de terminal em USD/ton (do cálculo do açúcar VHP)
    
    Returns:
        dict: {
            'values': {
                'preco_liquido_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        preco_anidro_fob_usd = inputs.get('preco_anidro_fob_usd', 0)
        frete_etanol_porto_usina = inputs.get('frete_etanol_porto_usina', 0)
        custo_terminal_etanol = inputs.get('custo_terminal_etanol', 0)
        custo_supervisao_documentos = inputs.get('custo_supervisao_documentos', 0)
        custos_adicionais_demurrage = inputs.get('custos_adicionais_demurrage', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # 1. Preço líquido PVU
        # Fórmula: ((Preço do Anidro USD * Câmbio) - Custo de frete de etanol - Custo de terminal - custo de supervisão - Custos adicionais)
        preco_anidro_brl = preco_anidro_fob_usd * cambio_brl_usd
        preco_liquido_pvu = preco_anidro_brl - frete_etanol_porto_usina - custo_terminal_etanol - custo_supervisao_documentos - custos_adicionais_demurrage
        
        # 2. Equivalente VHP R$/Saca PVU
        # Fórmula: Preço líquido PVU / 32,669
        equivalente_vhp_reais_saca_pvu = preco_liquido_pvu / FATOR_ETANOL_ANIDRO_LITROS_POR_SACA
        
        # 3. Equivalente Cents/lb PVU
        # Fórmula: ((Equivalente VHP R$/Saca PVU * 20) / 22,0462) / Câmbio / 1,042
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL
        
        # 4. Equivalente Cents/lb FOB
        # Fórmula: ((((((Preço líquido PVU) / 32,669) * 20) + Frete R$/ton adicionado no cálculo do sugar VHP + (Custo de terminal dólar por ton adicionado no cálculo do sugar VHP * Câmbio)) / 22,0462 / Câmbio) / 1,042)
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL)
        
        # Armazena resultados
        values['preco_liquido_pvu'] = preco_liquido_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular etanol anidro exportação: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_etanol_hidratado_exportacao(inputs, globais):
    """
    Calcula o etanol hidratado para exportação.
    Os cálculos são idênticos aos do etanol anidro, apenas mudando o preço do produto.
    
    Args:
        inputs: dict com:
            - preco_hidratado_fob_usd: Preço hidratado FOB em USD
            - frete_etanol_porto_usina: Frete para etanol Porto/Usina
            - custo_terminal_etanol: Custo de terminal
            - custo_supervisao_documentos: Custo de supervisão de documentos
            - custos_adicionais_demurrage: Custos adicionais demurrage (se houver)
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - frete_brl_ton: Frete em R$/Ton (do cálculo do açúcar VHP)
            - custo_terminal_usd_ton: Custo de terminal em USD/ton (do cálculo do açúcar VHP)
    
    Returns:
        dict: {
            'values': {
                'preco_liquido_pvu': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        preco_hidratado_fob_usd = inputs.get('preco_hidratado_fob_usd', 0)
        frete_etanol_porto_usina = inputs.get('frete_etanol_porto_usina', 0)
        custo_terminal_etanol = inputs.get('custo_terminal_etanol', 0)
        custo_supervisao_documentos = inputs.get('custo_supervisao_documentos', 0)
        custos_adicionais_demurrage = inputs.get('custos_adicionais_demurrage', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # 1. Preço líquido PVU
        # Fórmula: ((Preço do Hidratado USD * Câmbio) - Custo de frete de etanol - Custo de terminal - custo de supervisão - Custos adicionais)
        preco_hidratado_brl = preco_hidratado_fob_usd * cambio_brl_usd
        preco_liquido_pvu = preco_hidratado_brl - frete_etanol_porto_usina - custo_terminal_etanol - custo_supervisao_documentos - custos_adicionais_demurrage
        
        # 2. Equivalente VHP R$/Saca PVU
        # Fórmula: Preço líquido PVU / 31,304
        equivalente_vhp_reais_saca_pvu = preco_liquido_pvu / FATOR_ETANOL_HIDRATADO_LITROS_POR_SACA
        
        # 3. Equivalente Cents/lb PVU
        # Fórmula: ((Equivalente VHP R$/Saca PVU * 20) / 22,0462) / Câmbio / 1,042
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL
        
        # 4. Equivalente Cents/lb FOB
        # Fórmula: ((((((Preço líquido PVU) / 31,304) * 20) + Frete R$/ton adicionado no cálculo do sugar VHP + (Custo de terminal dólar por ton adicionado no cálculo do sugar VHP * Câmbio)) / 22,0462 / Câmbio) / 1,042)
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL)
        
        # Armazena resultados
        values['preco_liquido_pvu'] = preco_liquido_pvu
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular etanol hidratado exportação: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_etanol_anidro_mercado_interno(inputs, globais):
    """
    Calcula o etanol anidro para mercado interno.
    
    Args:
        inputs: dict com:
            - preco_anidro_com_impostos_brl: Preço do anidro com impostos em R$
            - pis_cofins_brl: Pis/Cofins em R$
            - contribuicao_agroindustria: Contribuição da agroindústria (em percentual)
            - valor_cbio_bruto: Valor do CBIO bruto
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - frete_brl_ton: Frete em R$/Ton (do cálculo do açúcar VHP)
            - custo_terminal_usd_ton: Custo de terminal em USD/ton (do cálculo do açúcar VHP)
            - premio_fisico_mi: Prêmio/desconto de físico mercado interno
            - custo_fobizacao_container_brl_ton: Custo de fobização em R$/Ton
    
    Returns:
        dict: {
            'values': {
                'preco_liquido_pvu': ...,
                'cbio_liquido_impostos': ...,
                'preco_liquido_pvu_mais_cbio': ...,
                'equivalente_hidratado': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        preco_anidro_com_impostos_brl = inputs.get('preco_anidro_com_impostos_brl', 0)
        pis_cofins_brl = inputs.get('pis_cofins_brl', 0)
        contribuicao_agroindustria = inputs.get('contribuicao_agroindustria', 0)
        valor_cbio_bruto = inputs.get('valor_cbio_bruto', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        premio_fisico_mi = globais.get('premio_fisico_mi', 0)
        custo_fobizacao_container_brl_ton = globais.get('custo_fobizacao_container_brl_ton', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # Converte contribuição da agroindústria para percentual (se > 1, assume que está em %, senão assume decimal)
        contribuicao_percentual = contribuicao_agroindustria / 100 if contribuicao_agroindustria > 1 else contribuicao_agroindustria
        
        # ====================================================================
        # VALORES INTERMEDIÁRIOS (não são equivalências, aparecem de forma discreta)
        # ====================================================================
        
        # 1. Preço líquido PVU
        # Fórmula: ((Preço do anidro com impostos*(1-Contribuição da agroindustria))-Pis/cofins)
        preco_liquido_pvu = (preco_anidro_com_impostos_brl * (1 - contribuicao_percentual)) - pis_cofins_brl
        
        # 2. CBIO líquido de impostos
        # Fórmula: (valor do CBIO*0,7575)*0,6
        cbio_liquido_impostos = (valor_cbio_bruto * 0.7575) * 0.6
        
        # 3. Preço líquido PVU + CBIO (FC 712,40)
        # Fórmula: Preço líquido PVU+((CBIO líquido de impostos/712,4)*1000)
        preco_liquido_pvu_mais_cbio = preco_liquido_pvu + ((cbio_liquido_impostos / FATOR_CBIO_FC_ANIDRO) * 1000)
        
        # 4. Equivalente Hidratado - 7,69% Fator Conv.
        # Fórmula: Preço líquido PVU/(1+0,0769)
        equivalente_hidratado = preco_liquido_pvu / (1 + FATOR_CONVERSAO_HIDRATADO)
        
        # ====================================================================
        # EQUIVALÊNCIAS (devem ser enfatizadas)
        # ====================================================================
        
        # 1. Equivalente VHP BRL/saco PVU
        # Fórmula: (Preço líquido PVU + CBIO (FC 712,40)/33,712)
        equivalente_vhp_reais_saca_pvu = preco_liquido_pvu_mais_cbio / FATOR_ETANOL_ANIDRO_MI_LITROS_POR_SACA
        
        # 2. Equivalente VHP Cents/lb PVU
        # Fórmula: (((Equivalente VHP BRL/saco PVU*20)/22,0462)/Câmbio)
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 3. Equivalente VHP Cents/lb FOB
        # Fórmula: (((((((Preço líquido PVU + CBIO (FC 712,40))/33,712)*20)+Frete utilizado em Sugar VHP+(Custo de terminal USD/ton utilizado em sugar VHP*Câmbio))/22,0462/Câmbio)/1,042)
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_ANIDRO_MI_LITROS_POR_SACA * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL)
        
        # 4. Equivalente Cristal Cents/lb PVU
        # Fórmula: (((((((Preço líquido PVU + CBIO (FC 712,40))/33,712)*20)+(Prêmio/desconto de físico utilizado no açúcar mercado interno*Câmbio))/22,0462/Câmbio))
        premio_fisico_brl_ton = premio_fisico_mi * cambio_brl_usd
        equivalente_cristal_cents_lb_pvu = ((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_ANIDRO_MI_LITROS_POR_SACA * SACAS_POR_TON) + premio_fisico_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 5. Equivalente Cristal BRL/Saca PVU
        # Fórmula: (Equivalente Cristal Cents/lb PVU*22,0462/20)*Câmbio
        equivalente_cristal_reais_saca_pvu = (equivalente_cristal_cents_lb_pvu * FATOR_CONVERSAO_CENTS_LB_PARA_TON / SACAS_POR_TON) * cambio_brl_usd
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Fórmula: ((((((((Preço líquido PVU + CBIO (FC 712,40))/33,712)*20)+Frete utilizado em SUGAR VHP+Custo de fobização já utilizado)+(Prêmio/desconto de físico utilizado no mercado interno açúcar*Câmbio))/22,0462/Câmbio))
        equivalente_cristal_cents_lb_fob = (((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_ANIDRO_MI_LITROS_POR_SACA * SACAS_POR_TON) + frete_brl_ton + custo_fobizacao_container_brl_ton) + premio_fisico_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # Armazena resultados
        # Valores intermediários (discretos)
        values['preco_liquido_pvu'] = preco_liquido_pvu
        values['cbio_liquido_impostos'] = cbio_liquido_impostos
        values['preco_liquido_pvu_mais_cbio'] = preco_liquido_pvu_mais_cbio
        values['equivalente_hidratado'] = equivalente_hidratado
        
        # Equivalências (enfatizadas)
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular etanol anidro mercado interno: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

def calc_etanol_hidratado_mercado_interno(inputs, globais):
    """
    Calcula o etanol hidratado para mercado interno.
    
    Args:
        inputs: dict com:
            - preco_hidratado_com_impostos_brl: Preço do hidratado com impostos em R$
            - pis_cofins_brl: Pis/Cofins em R$ (reutiliza do anidro MI)
            - icms_percentual: Preço do ICMS em percentual
            - contribuicao_agroindustria: Contribuição da agroindústria (em percentual, reutiliza do anidro MI)
            - valor_cbio_bruto: Valor do CBIO bruto (reutiliza do anidro MI)
        globais: dict com parâmetros globais:
            - cambio_brl_usd: Câmbio USD/BRL
            - frete_brl_ton: Frete em R$/Ton (do cálculo do açúcar VHP)
            - custo_terminal_usd_ton: Custo de terminal em USD/ton (do cálculo do açúcar VHP)
            - premio_fisico_mi: Prêmio/desconto de físico mercado interno
            - custo_fobizacao_container_brl_ton: Custo de fobização em R$/Ton
    
    Returns:
        dict: {
            'values': {
                'preco_liquido_pvu': ...,
                'preco_liquido_pvu_mais_cbio': ...,
                'equivalente_anidro': ...,
                'preco_liquido_pvu_mais_cbio_mais_credito': ...,
                'equivalente_vhp_reais_saca_pvu': ...,
                'equivalente_vhp_cents_lb_pvu': ...,
                'equivalente_vhp_cents_lb_fob': ...,
                'equivalente_cristal_cents_lb_pvu': ...,
                'equivalente_cristal_reais_saca_pvu': ...,
                'equivalente_cristal_cents_lb_fob': ...,
            },
            'errors': [...]
        }
    """
    errors = []
    values = {}
    
    try:
        # Entradas
        preco_hidratado_com_impostos_brl = inputs.get('preco_hidratado_com_impostos_brl', 0)
        pis_cofins_brl = inputs.get('pis_cofins_brl', 0)
        icms_percentual = inputs.get('icms_percentual', 0)
        contribuicao_agroindustria = inputs.get('contribuicao_agroindustria', 0)
        valor_cbio_bruto = inputs.get('valor_cbio_bruto', 0)
        
        cambio_brl_usd = globais.get('cambio_brl_usd', 1)
        frete_brl_ton = globais.get('frete_brl_ton', 0)
        custo_terminal_usd_ton = globais.get('custo_terminal_usd_ton', 0)
        premio_fisico_mi = globais.get('premio_fisico_mi', 0)
        custo_fobizacao_container_brl_ton = globais.get('custo_fobizacao_container_brl_ton', 0)
        
        # Validações
        if cambio_brl_usd <= 0:
            errors.append("Câmbio deve ser maior que zero")
            return {'values': values, 'errors': errors}
        
        # Converte percentuais (se > 1, assume que está em %, senão assume decimal)
        icms_percentual_val = icms_percentual / 100 if icms_percentual > 1 else icms_percentual
        contribuicao_percentual = contribuicao_agroindustria / 100 if contribuicao_agroindustria > 1 else contribuicao_agroindustria
        
        # Calcula CBIO líquido de impostos (mesma fórmula do anidro)
        cbio_liquido_impostos = (valor_cbio_bruto * 0.7575) * 0.6
        
        # ====================================================================
        # VALORES INTERMEDIÁRIOS (não são equivalências, aparecem de forma discreta)
        # ====================================================================
        
        # 1. Preço líquido PVU
        # Fórmula: ((Preço do hidratado com impostos*(1-Contribuição da agroindustria))*(1-ICMS)-PIS/COFINS)
        preco_liquido_pvu = ((preco_hidratado_com_impostos_brl * (1 - contribuicao_percentual)) * (1 - icms_percentual_val)) - pis_cofins_brl
        
        # 2. Preço líquido PVU + CBIO (FC 749,75)
        # Fórmula: Preço líquido PVU+((Valor líquido do CBIOS/749,75)*1000)
        preco_liquido_pvu_mais_cbio = preco_liquido_pvu + ((cbio_liquido_impostos / FATOR_CBIO_FC_HIDRATADO) * 1000)
        
        # 3. Equivalente Anidro - 7,69% Fator Conv.
        # Fórmula: Preço líquido PVU*(1+0,0769)
        equivalente_anidro = preco_liquido_pvu * (1 + FATOR_CONVERSAO_HIDRATADO)
        
        # 4. Preço Líquido PVU + CBIO + Crédito Trib. (0,24)
        # Fórmula: Preço líquido PVU + CBIO (FC 749,75) +240
        preco_liquido_pvu_mais_cbio_mais_credito = preco_liquido_pvu_mais_cbio + CREDITO_TRIBUTARIO
        
        # ====================================================================
        # EQUIVALÊNCIAS (devem ser enfatizadas)
        # ====================================================================
        
        # 1. Equivalente VHP BRL/saco PVU
        # Fórmula: (Preço líquido PVU + CBIO (FC 749,75)/31,504)
        equivalente_vhp_reais_saca_pvu = preco_liquido_pvu_mais_cbio / FATOR_ETANOL_HIDRATADO_MI_LITROS_POR_SACA
        
        # 2. Equivalente VHP Cents/lb PVU
        # Fórmula: (((Equivalente VHP BRL/saco PVU*20)/22,0462)/Câmbio)
        equivalente_vhp_cents_lb_pvu = (((equivalente_vhp_reais_saca_pvu * SACAS_POR_TON) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 3. Equivalente VHP Cents/lb FOB
        # Fórmula: (((((((Preço líquido PVU + CBIO (FC 749,75))/31,504)*20)+Frete utilizado em sugar VHP+(Custo de terminal em USD utilizado em sugar VHP*Câmbio))/22,0462/Câmbio)/1,042)
        custo_terminal_brl_ton = custo_terminal_usd_ton * cambio_brl_usd
        equivalente_vhp_cents_lb_fob = (((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_HIDRATADO_MI_LITROS_POR_SACA * SACAS_POR_TON) + frete_brl_ton + custo_terminal_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd) / FATOR_AJUSTE_ETANOL)
        
        # 4. Equivalente Cristal Cents/lb PVU
        # Fórmula: (((((((Preço líquido PVU + CBIO (FC 749,75))/31,504)*20)+(Prêmio de físico utilizado no Açúcar MI*Câmbio))/22,0462/Câmbio))
        premio_fisico_brl_ton = premio_fisico_mi * cambio_brl_usd
        equivalente_cristal_cents_lb_pvu = ((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_HIDRATADO_MI_LITROS_POR_SACA * SACAS_POR_TON) + premio_fisico_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # 5. Equivalente Cristal BRL/Saca PVU
        # Fórmula: (Equivalente Cristal Cents/lb PVU*22,0462/20)*Câmbio
        equivalente_cristal_reais_saca_pvu = (equivalente_cristal_cents_lb_pvu * FATOR_CONVERSAO_CENTS_LB_PARA_TON / SACAS_POR_TON) * cambio_brl_usd
        
        # 6. Equivalente Cristal Cents/lb FOB
        # Fórmula: ((((((((Preço líquido PVU + CBIO (FC 749,75))/31,504)*20)+Custo de frete utilizado em SUGAR VHP+Custo de fobização já utilizado)+(Prêmio/Desconto MI*Câmbio))/22,0462/Câmbio))
        equivalente_cristal_cents_lb_fob = (((((preco_liquido_pvu_mais_cbio / FATOR_ETANOL_HIDRATADO_MI_LITROS_POR_SACA * SACAS_POR_TON) + frete_brl_ton + custo_fobizacao_container_brl_ton) + premio_fisico_brl_ton) / FATOR_CONVERSAO_CENTS_LB_PARA_TON) / cambio_brl_usd)
        
        # Armazena resultados
        # Valores intermediários (discretos)
        values['preco_liquido_pvu'] = preco_liquido_pvu
        values['preco_liquido_pvu_mais_cbio'] = preco_liquido_pvu_mais_cbio
        values['equivalente_anidro'] = equivalente_anidro
        values['preco_liquido_pvu_mais_cbio_mais_credito'] = preco_liquido_pvu_mais_cbio_mais_credito
        
        # Equivalências (enfatizadas)
        values['equivalente_vhp_reais_saca_pvu'] = equivalente_vhp_reais_saca_pvu
        values['equivalente_vhp_cents_lb_pvu'] = equivalente_vhp_cents_lb_pvu
        values['equivalente_vhp_cents_lb_fob'] = equivalente_vhp_cents_lb_fob
        values['equivalente_cristal_cents_lb_pvu'] = equivalente_cristal_cents_lb_pvu
        values['equivalente_cristal_reais_saca_pvu'] = equivalente_cristal_reais_saca_pvu
        values['equivalente_cristal_cents_lb_fob'] = equivalente_cristal_cents_lb_fob
        
    except Exception as e:
        errors.append(f"Erro ao calcular etanol hidratado mercado interno: {str(e)}")
    
    return {
        'values': values,
        'errors': errors
    }

# ============================================================================
# SIDEBAR - INPUTS
# ============================================================================

# Carrega valores salvos
saved_config = load_sidebar_config()

with st.sidebar:
    st.title("⚙️ Parâmetros")
    
    # Câmbio (usado em todos os cálculos) - sempre visível
    st.markdown("---")
    st.markdown("### 💱 Câmbio")
    cambio_brl_usd = st.number_input(
        "Câmbio USD/BRL",
        value=saved_config.get('cambio_brl_usd', 5.35),
        step=0.01,
        format="%.4f",
        help="Taxa de câmbio real equiparado ao dólar",
        key="cambio_sidebar"
    )
    st.markdown("---")
    
    # ========================================================================
    # AÇÚCAR
    # ========================================================================
    st.markdown("### 🍬 Açúcar")
    
    # Açúcar VHP
    with st.expander("📝 Açúcar VHP", expanded=True):
        acucar_ny_cents_lb = st.number_input(
            "Açúcar NY (c/lb)",
            value=saved_config.get('acucar_ny_cents_lb', 15.8),
            step=0.1,
            format="%.2f",
            help="Valor do açúcar na bolsa em dólar por libra peso",
            key="acucar_ny_sidebar"
        )
        premio_desconto_vhp = st.number_input(
            "Prêmio/Desconto (c/lb)",
            value=saved_config.get('premio_desconto_vhp', -0.1),
            step=0.1,
            format="%.2f",
            help="Prêmio ou desconto em centavos por libra",
            key="premio_desconto_vhp_sidebar"
        )
        premio_pol_vhp = st.number_input(
            "Prêmio de Pol (%)",
            value=saved_config.get('premio_pol_vhp', 4.2),
            step=0.1,
            format="%.2f",
            help="Prêmio de pol (percentual)",
            key="premio_pol_vhp_sidebar"
        )
        custo_terminal_vhp_usd_ton = st.number_input(
            "Custo Terminal (USD/ton)",
            value=saved_config.get('custo_terminal_vhp_usd_ton', 12.5),
            step=0.1,
            format="%.2f",
            help="Custo de terminal em dólar por tonelada",
            key="custo_terminal_vhp_sidebar"
        )
        frete_vhp_brl_ton = st.number_input(
            "Frete (BRL/ton)",
            value=saved_config.get('frete_vhp_brl_ton', 202.0),
            step=1.0,
            format="%.2f",
            help="Frete em reais por tonelada",
            key="frete_vhp_sidebar"
        )
    
    # Açúcar Cristal ESALQ
    with st.expander("📝 Açúcar Cristal ESALQ"):
        preco_esalq_brl_saca = st.number_input(
            "Preço ESALQ (R$/saca)",
            value=saved_config.get('preco_esalq_brl_saca', 115.67),
            step=0.1,
            format="%.2f",
            help="Preço ESALQ em reais por saca",
            key="preco_esalq_sidebar"
        )
        imposto_esalq = st.number_input(
            "Imposto (%)",
            value=saved_config.get('imposto_esalq', 9.85),
            step=0.1,
            format="%.2f",
            help="Imposto (percentual)",
            key="imposto_esalq_sidebar"
        )
        frete_santos_usina_brl_ton = st.number_input(
            "Frete Santos-Usina (R$/Ton)",
            value=saved_config.get('frete_santos_usina_brl_ton', 202.0),
            step=1.0,
            format="%.2f",
            help="Frete Santos-Usina em reais por tonelada",
            key="frete_santos_usina_sidebar"
        )
        custo_fobizacao_container_brl_ton = st.number_input(
            "Custo Fobização Container (R$/Ton)",
            value=saved_config.get('custo_fobizacao_container_brl_ton', 198.0),
            step=1.0,
            format="%.2f",
            help="Custo de fobização do container",
            key="custo_fobizacao_sidebar"
        )
        custo_vhp_para_cristal = st.number_input(
            "Custo VHP → Cristal",
            value=saved_config.get('custo_vhp_para_cristal', 9.25),
            step=0.1,
            format="%.2f",
            help="Custo para transformar VHP em Cristal",
            key="custo_vhp_cristal_sidebar"
        )
    
    # Prêmios de Exportação
    with st.expander("📝 Prêmios de Exportação"):
        premio_fisico_mi = st.number_input(
            "Prêmio Físico MI",
            value=saved_config.get('premio_fisico_mi', 0.0),
            step=0.1,
            format="%.2f",
            help="Prêmio/desconto de físico - mercado interno",
            key="premio_fisico_mi_sidebar"
        )
        premio_fisico_exportacao = st.number_input(
            "Prêmio Físico Exportação",
            value=saved_config.get('premio_fisico_exportacao', 0.0),
            step=0.1,
            format="%.2f",
            help="Prêmio/desconto de físico para exportação",
            key="premio_fisico_exportacao_sidebar"
        )
        premio_fisico_exportacao_malha30 = st.number_input(
            "Prêmio Físico Exportação Malha 30",
            value=saved_config.get('premio_fisico_exportacao_malha30', 0.0),
            step=0.1,
            format="%.2f",
            help="Prêmio/desconto de físico para exportação malha 30",
            key="premio_fisico_exportacao_malha30_sidebar"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # ETANOL
    # ========================================================================
    st.markdown("### ⛽ Etanol")
    
    # Etanol Anidro Exportação
    with st.expander("📝 Etanol Anidro Exportação"):
        preco_anidro_fob_usd = st.number_input(
            "Preço Anidro FOB (USD)",
            value=saved_config.get('preco_anidro_fob_usd', 0.0),
            step=0.01,
            format="%.2f",
            help="Preço anidro FOB em USD",
            key="preco_anidro_fob_usd_sidebar"
        )
        frete_etanol_porto_usina = st.number_input(
            "Frete Porto/Usina",
            value=saved_config.get('frete_etanol_porto_usina', 0.0),
            step=0.01,
            format="%.2f",
            help="Frete para etanol Porto/Usina",
            key="frete_etanol_porto_usina_sidebar"
        )
        custo_terminal_etanol = st.number_input(
            "Custo Terminal",
            value=saved_config.get('custo_terminal_etanol', 0.0),
            step=0.01,
            format="%.2f",
            help="Custo de terminal",
            key="custo_terminal_etanol_sidebar"
        )
        custo_supervisao_documentos = st.number_input(
            "Custo Supervisão Documentos",
            value=saved_config.get('custo_supervisao_documentos', 0.0),
            step=0.01,
            format="%.2f",
            help="Custo de supervisão de documentos",
            key="custo_supervisao_documentos_sidebar"
        )
        custos_adicionais_demurrage = st.number_input(
            "Custos Adicionais Demurrage",
            value=saved_config.get('custos_adicionais_demurrage', 0.0),
            step=0.01,
            format="%.2f",
            help="Custos adicionais demurrage (se houver)",
            key="custos_adicionais_demurrage_sidebar"
        )
    
    # Etanol Hidratado Exportação
    with st.expander("📝 Etanol Hidratado Exportação"):
        st.caption("Usa os mesmos custos do Etanol Anidro Exportação")
        preco_hidratado_fob_usd = st.number_input(
            "Preço Hidratado FOB (USD)",
            value=saved_config.get('preco_hidratado_fob_usd', 0.0),
            step=0.01,
            format="%.2f",
            help="Preço hidratado FOB em USD",
            key="preco_hidratado_fob_usd_sidebar"
        )
    
    # Etanol Anidro Mercado Interno
    with st.expander("📝 Etanol Anidro Mercado Interno"):
        preco_anidro_com_impostos_brl = st.number_input(
            "Preço Anidro com Impostos (R$)",
            value=saved_config.get('preco_anidro_com_impostos_brl', 0.0),
            step=0.01,
            format="%.2f",
            help="Preço do anidro com impostos em R$",
            key="preco_anidro_com_impostos_brl_sidebar"
        )
        pis_cofins_brl = st.number_input(
            "Pis/Cofins (R$)",
            value=saved_config.get('pis_cofins_brl', 0.0),
            step=0.01,
            format="%.2f",
            help="Pis/Cofins em R$",
            key="pis_cofins_brl_sidebar"
        )
        contribuicao_agroindustria = st.number_input(
            "Contribuição da Agroindústria (%)",
            value=saved_config.get('contribuicao_agroindustria', 0.0),
            step=0.1,
            format="%.2f",
            help="Contribuição da agroindústria (em percentual)",
            key="contribuicao_agroindustria_sidebar"
        )
        valor_cbio_bruto = st.number_input(
            "Valor do CBIO Bruto",
            value=saved_config.get('valor_cbio_bruto', 0.0),
            step=0.01,
            format="%.2f",
            help="Valor do CBIO bruto",
            key="valor_cbio_bruto_sidebar"
        )
    
    # Etanol Hidratado Mercado Interno
    with st.expander("📝 Etanol Hidratado Mercado Interno"):
        st.caption("Reutiliza Pis/Cofins, Contribuição da Agroindústria e CBIO do Anidro MI")
        preco_hidratado_com_impostos_brl = st.number_input(
            "Preço Hidratado com Impostos (R$)",
            value=saved_config.get('preco_hidratado_com_impostos_brl', 0.0),
            step=0.01,
            format="%.2f",
            help="Preço do hidratado com impostos em R$",
            key="preco_hidratado_com_impostos_brl_sidebar"
        )
        icms_percentual = st.number_input(
            "ICMS (%)",
            value=saved_config.get('icms_percentual', 0.0),
            step=0.1,
            format="%.2f",
            help="Preço do ICMS em percentual",
            key="icms_percentual_sidebar"
        )
    
    # Salva os valores quando houver mudanças
    current_values = {
        'cambio_brl_usd': cambio_brl_usd,
        'acucar_ny_cents_lb': acucar_ny_cents_lb,
        'premio_desconto_vhp': premio_desconto_vhp,
        'premio_pol_vhp': premio_pol_vhp,
        'custo_terminal_vhp_usd_ton': custo_terminal_vhp_usd_ton,
        'frete_vhp_brl_ton': frete_vhp_brl_ton,
        'preco_esalq_brl_saca': preco_esalq_brl_saca,
        'imposto_esalq': imposto_esalq,
        'frete_santos_usina_brl_ton': frete_santos_usina_brl_ton,
        'custo_fobizacao_container_brl_ton': custo_fobizacao_container_brl_ton,
        'custo_vhp_para_cristal': custo_vhp_para_cristal,
        'premio_fisico_mi': premio_fisico_mi,
        'premio_fisico_exportacao': premio_fisico_exportacao,
        'premio_fisico_exportacao_malha30': premio_fisico_exportacao_malha30,
        'preco_anidro_fob_usd': preco_anidro_fob_usd,
        'frete_etanol_porto_usina': frete_etanol_porto_usina,
        'custo_terminal_etanol': custo_terminal_etanol,
        'custo_supervisao_documentos': custo_supervisao_documentos,
        'custos_adicionais_demurrage': custos_adicionais_demurrage,
        'preco_hidratado_fob_usd': preco_hidratado_fob_usd,
        'preco_anidro_com_impostos_brl': preco_anidro_com_impostos_brl,
        'pis_cofins_brl': pis_cofins_brl,
        'contribuicao_agroindustria': contribuicao_agroindustria,
        'valor_cbio_bruto': valor_cbio_bruto,
        'preco_hidratado_com_impostos_brl': preco_hidratado_com_impostos_brl,
        'icms_percentual': icms_percentual,
    }
    
    # Salva apenas se os valores mudaram
    if 'last_saved_values' not in st.session_state or st.session_state.last_saved_values != current_values:
        save_sidebar_config(current_values)
        st.session_state.last_saved_values = current_values

# ============================================================================
# CÁLCULOS
# ============================================================================

# Prepara inputs
inputs_acucar_vhp = {
    'acucar_ny_cents_lb': acucar_ny_cents_lb,
    'premio_desconto': premio_desconto_vhp,
    'premio_pol': premio_pol_vhp,
    'custo_terminal_usd_ton': custo_terminal_vhp_usd_ton,
    'frete_brl_ton': frete_vhp_brl_ton,
}

globais = {
    'cambio_brl_usd': cambio_brl_usd,
    'custo_terminal_usd_ton': custo_terminal_vhp_usd_ton,
    'frete_santos_usina_brl_ton': frete_santos_usina_brl_ton,
    'frete_brl_ton': frete_vhp_brl_ton,
    'custo_fobizacao_container_brl_ton': custo_fobizacao_container_brl_ton,
    'custo_vhp_para_cristal': custo_vhp_para_cristal,
}

# Executa cálculos
result_acucar_vhp = calc_acucar_vhp_detalhado(inputs_acucar_vhp, globais)

# Prepara inputs para açúcar cristal ESALQ
inputs_acucar_cristal_esalq = {
    'preco_esalq_brl_saca': preco_esalq_brl_saca,
    'imposto': imposto_esalq,
    'frete_santos_usina_brl_ton': frete_santos_usina_brl_ton,
    'custo_fobizacao_container_brl_ton': custo_fobizacao_container_brl_ton,
    'custo_vhp_para_cristal': custo_vhp_para_cristal,
}

# Executa cálculo do açúcar cristal ESALQ
result_acucar_cristal_esalq = calc_acucar_cristal_esalq(inputs_acucar_cristal_esalq, globais)

# Prepara inputs para custo de comercialização açúcar cristal MI
inputs_paridade_mi_ny = {
    'acucar_ny_cents_lb': acucar_ny_cents_lb,  # Usa o mesmo valor do açúcar VHP
    'premio_fisico_mi': premio_fisico_mi,
}

# Executa cálculo do custo de comercialização açúcar cristal MI
result_paridade_mi_ny = calc_paridade_comercializacao_mi_ny(inputs_paridade_mi_ny, globais)

# Prepara inputs para açúcar cristal exportação
inputs_acucar_cristal_exportacao = {
    'acucar_ny_cents_lb': acucar_ny_cents_lb,  # Usa o mesmo valor do açúcar VHP
    'premio_fisico_exportacao': premio_fisico_exportacao,
}

# Executa cálculo do açúcar cristal exportação
result_acucar_cristal_exportacao = calc_acucar_cristal_exportacao(inputs_acucar_cristal_exportacao, globais)

# Prepara inputs para açúcar cristal exportação malha 30
inputs_acucar_cristal_exportacao_malha30 = {
    'acucar_ny_cents_lb': acucar_ny_cents_lb,  # Usa o mesmo valor do açúcar VHP
    'premio_fisico_exportacao_malha30': premio_fisico_exportacao_malha30,
}

# Executa cálculo do açúcar cristal exportação malha 30
result_acucar_cristal_exportacao_malha30 = calc_acucar_cristal_exportacao_malha30(inputs_acucar_cristal_exportacao_malha30, globais)

# Prepara inputs para etanol anidro exportação
inputs_etanol_anidro_exportacao = {
    'preco_anidro_fob_usd': preco_anidro_fob_usd,
    'frete_etanol_porto_usina': frete_etanol_porto_usina,
    'custo_terminal_etanol': custo_terminal_etanol,
    'custo_supervisao_documentos': custo_supervisao_documentos,
    'custos_adicionais_demurrage': custos_adicionais_demurrage,
}

# Executa cálculo do etanol anidro exportação
result_etanol_anidro_exportacao = calc_etanol_anidro_exportacao(inputs_etanol_anidro_exportacao, globais)

# Prepara inputs para etanol hidratado exportação
# Reutiliza os mesmos custos do etanol anidro
inputs_etanol_hidratado_exportacao = {
    'preco_hidratado_fob_usd': preco_hidratado_fob_usd,
    'frete_etanol_porto_usina': frete_etanol_porto_usina,
    'custo_terminal_etanol': custo_terminal_etanol,
    'custo_supervisao_documentos': custo_supervisao_documentos,
    'custos_adicionais_demurrage': custos_adicionais_demurrage,
}

# Executa cálculo do etanol hidratado exportação
result_etanol_hidratado_exportacao = calc_etanol_hidratado_exportacao(inputs_etanol_hidratado_exportacao, globais)

# Prepara inputs para etanol anidro mercado interno
inputs_etanol_anidro_mi = {
    'preco_anidro_com_impostos_brl': preco_anidro_com_impostos_brl,
    'pis_cofins_brl': pis_cofins_brl,
    'contribuicao_agroindustria': contribuicao_agroindustria,
    'valor_cbio_bruto': valor_cbio_bruto,
}

# Atualiza globais para incluir premio_fisico_mi e custo_fobizacao
globais_mi = globais.copy()
globais_mi['premio_fisico_mi'] = premio_fisico_mi
globais_mi['custo_fobizacao_container_brl_ton'] = custo_fobizacao_container_brl_ton

# Executa cálculo do etanol anidro mercado interno
result_etanol_anidro_mi = calc_etanol_anidro_mercado_interno(inputs_etanol_anidro_mi, globais_mi)

# Prepara inputs para etanol hidratado mercado interno
inputs_etanol_hidratado_mi = {
    'preco_hidratado_com_impostos_brl': preco_hidratado_com_impostos_brl,
    'pis_cofins_brl': pis_cofins_brl,  # Reutiliza do anidro MI
    'icms_percentual': icms_percentual,
    'contribuicao_agroindustria': contribuicao_agroindustria,  # Reutiliza do anidro MI
    'valor_cbio_bruto': valor_cbio_bruto,  # Reutiliza do anidro MI
}

# Executa cálculo do etanol hidratado mercado interno
result_etanol_hidratado_mi = calc_etanol_hidratado_mercado_interno(inputs_etanol_hidratado_mi, globais_mi)

# ============================================================================
# EXIBIÇÃO DOS RESULTADOS
# ============================================================================

st.title("📊 Paridades & Arbitragens")
st.caption("Dashboard comparativo de paridades para análise de oportunidades")

# Exibe erros se houver
all_errors = (result_acucar_vhp.get('errors', []) + 
              result_acucar_cristal_esalq.get('errors', []) +
              result_paridade_mi_ny.get('errors', []) +
              result_acucar_cristal_exportacao.get('errors', []) +
              result_acucar_cristal_exportacao_malha30.get('errors', []) +
              result_etanol_anidro_exportacao.get('errors', []) +
              result_etanol_hidratado_exportacao.get('errors', []) +
              result_etanol_anidro_mi.get('errors', []) +
              result_etanol_hidratado_mi.get('errors', []))
if all_errors:
    st.error("⚠️ Erros encontrados:")
    for error in all_errors:
        st.write(f"- {error}")

# ============================================================================
# DASHBOARD COMPARATIVO DE PARIDADES (PRINCIPAL)
# ============================================================================

# Coleta todos os dados para o dashboard
dashboard_data = []

# Açúcar VHP
if result_acucar_vhp.get('values'):
    v = result_acucar_vhp['values']
    dashboard_data.append({
        'Produto': 'Açúcar VHP',
        'Categoria': 'VHP',
        'Tipo': 'Açúcar',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': None,
        'Cristal c/lb PVU': None,
        'Cristal c/lb FOB': None,
    })

# Açúcar Cristal ESALQ
if result_acucar_cristal_esalq.get('values'):
    v = result_acucar_cristal_esalq['values']
    dashboard_data.append({
        'Produto': 'Açúcar Cristal ESALQ',
        'Categoria': 'Cristal',
        'Tipo': 'Açúcar',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

# Açúcar Cristal MI
if result_paridade_mi_ny.get('values'):
    v = result_paridade_mi_ny['values']
    dashboard_data.append({
        'Produto': 'Açúcar Cristal MI',
        'Categoria': 'Cristal',
        'Tipo': 'Açúcar',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

# Açúcar Cristal Exportação
if result_acucar_cristal_exportacao.get('values'):
    v = result_acucar_cristal_exportacao['values']
    dashboard_data.append({
        'Produto': 'Açúcar Cristal Exportação',
        'Categoria': 'Cristal',
        'Tipo': 'Açúcar',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

# Açúcar Cristal Exportação Malha 30
if result_acucar_cristal_exportacao_malha30.get('values'):
    v = result_acucar_cristal_exportacao_malha30['values']
    dashboard_data.append({
        'Produto': 'Açúcar Cristal Exportação Malha 30',
        'Categoria': 'Cristal',
        'Tipo': 'Açúcar',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

# Etanol Anidro Exportação
if result_etanol_anidro_exportacao.get('values'):
    v = result_etanol_anidro_exportacao['values']
    dashboard_data.append({
        'Produto': 'Etanol Anidro Exportação',
        'Categoria': 'VHP',
        'Tipo': 'Etanol',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': None,
        'Cristal c/lb PVU': None,
        'Cristal c/lb FOB': None,
    })

# Etanol Hidratado Exportação
if result_etanol_hidratado_exportacao.get('values'):
    v = result_etanol_hidratado_exportacao['values']
    dashboard_data.append({
        'Produto': 'Etanol Hidratado Exportação',
        'Categoria': 'VHP',
        'Tipo': 'Etanol',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': None,
        'Cristal c/lb PVU': None,
        'Cristal c/lb FOB': None,
    })

# Etanol Anidro Mercado Interno
if result_etanol_anidro_mi.get('values'):
    v = result_etanol_anidro_mi['values']
    dashboard_data.append({
        'Produto': 'Etanol Anidro MI',
        'Categoria': 'Cristal',
        'Tipo': 'Etanol',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

# Etanol Hidratado Mercado Interno
if result_etanol_hidratado_mi.get('values'):
    v = result_etanol_hidratado_mi['values']
    dashboard_data.append({
        'Produto': 'Etanol Hidratado MI',
        'Categoria': 'Cristal',
        'Tipo': 'Etanol',
        'VHP R$/saca PVU': v.get('equivalente_vhp_reais_saca_pvu', 0),
        'VHP c/lb PVU': v.get('equivalente_vhp_cents_lb_pvu', 0),
        'VHP c/lb FOB': v.get('equivalente_vhp_cents_lb_fob', 0),
        'Cristal R$/saca PVU': v.get('equivalente_cristal_reais_saca_pvu', 0),
        'Cristal c/lb PVU': v.get('equivalente_cristal_cents_lb_pvu', 0),
        'Cristal c/lb FOB': v.get('equivalente_cristal_cents_lb_fob', 0),
    })

if dashboard_data:
    # CSS para os cards do dashboard
    st.markdown("""
    <style>
    .dashboard-card {
        background: rgba(26, 32, 44, 0.8);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        border-left: 5px solid;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    .dashboard-card-green {
        border-left-color: #10b981;
        background: rgba(16, 185, 129, 0.1);
    }
    .dashboard-card-red {
        border-left-color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
    }
    .dashboard-card-blue {
        border-left-color: #3b82f6;
        background: rgba(59, 130, 246, 0.1);
    }
    .dashboard-card-orange {
        border-left-color: #f59e0b;
        background: rgba(245, 158, 11, 0.1);
    }
    .dashboard-card-purple {
        border-left-color: #8b5cf6;
        background: rgba(139, 92, 246, 0.1);
    }
    .dashboard-card-yellow {
        border-left-color: #eab308;
        background: rgba(234, 179, 8, 0.1);
    }
    .dashboard-title {
        font-size: 1rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .dashboard-price {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        margin: 0.75rem 0;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .dashboard-metric {
        font-size: 0.9rem;
        color: #94a3b8;
        margin: 0.4rem 0;
    }
    .dashboard-metric-label {
        font-weight: 500;
        color: #cbd5e1;
    }
    .dashboard-metric-value {
        font-weight: 600;
        color: #ffffff;
    }
    .dashboard-arbitrage {
        font-size: 0.85rem;
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(255,255,255,0.15);
    }
    .dashboard-arbitrage-label {
        font-size: 0.7rem;
        color: #94a3b8;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .dashboard-arbitrage-value {
        font-size: 1.1rem;
        font-weight: 700;
    }
    .dashboard-arbitrage-positive {
        color: #10b981;
    }
    .dashboard-arbitrage-negative {
        color: #ef4444;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Cards principais - Top 3 produtos por categoria
    st.markdown("### 🎯 Resumo Executivo")
    
    # Explicação sobre Arbitragem Implícita
    with st.expander("ℹ️ O que é Arbitragem Implícita?", expanded=False):
        st.markdown("""
        **Arbitragem Implícita** representa a diferença entre o equivalente em **Cristal** e **VHP** (em c/lb).
        
        - **Valor positivo (verde)**: O Cristal vale mais que o VHP, indicando oportunidade de transformação
        - **Valor negativo (vermelho)**: O VHP vale mais que o Cristal
        
        Esta métrica ajuda a identificar qual produto é mais vantajoso produzir.
        """)
    
    # Filtro de produtos
    todos_produtos = [d['Produto'] for d in dashboard_data]
    produtos_filtrados = st.multiselect(
        "🔍 Filtrar Produtos (deixe vazio para mostrar todos)",
        options=todos_produtos,
        default=todos_produtos,
        help="Selecione os produtos que deseja visualizar. Remova os produtos que não quer comparar."
    )
    
    # Filtra os dados baseado na seleção
    if produtos_filtrados:
        dashboard_data_filtrado = [d for d in dashboard_data if d['Produto'] in produtos_filtrados]
    else:
        dashboard_data_filtrado = dashboard_data
        st.info("ℹ️ Selecione pelo menos um produto para visualizar")
    
    # Encontra os melhores valores (com filtro)
    vhp_saca_list = [(d['Produto'], d['VHP R$/saca PVU']) for d in dashboard_data_filtrado if d['VHP R$/saca PVU'] is not None]
    cristal_saca_list = [(d['Produto'], d['Cristal R$/saca PVU']) for d in dashboard_data_filtrado if d['Cristal R$/saca PVU'] is not None]
    
    # Top 3 VHP (usando dados filtrados)
    if vhp_saca_list:
        vhp_saca_list_sorted = sorted(vhp_saca_list, key=lambda x: x[1], reverse=True)
        top_vhp = vhp_saca_list_sorted[:3]
        
        cols = st.columns(3)
        # Cores mais intuitivas: verde para melhor, laranja para médio, azul para terceiro
        colors = ['green', 'orange', 'blue']
        for idx, (produto, valor) in enumerate(top_vhp):
            if idx < 3:
                # Encontra dados completos do produto
                produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
                if produto_data:
                    with cols[idx]:
                        # Calcula arbitragem (diferença entre VHP e Cristal se disponível) em c/lb
                        arbitragem = None
                        if produto_data['Cristal c/lb PVU'] is not None and produto_data['VHP c/lb PVU'] is not None:
                            arbitragem = produto_data['Cristal c/lb PVU'] - produto_data['VHP c/lb PVU']
                        
                        # Atribui cor baseada na posição: melhor = verde, segundo = laranja, terceiro = azul
                        if idx == 0:
                            color_class = 'green'
                        elif idx == 1:
                            color_class = 'orange'
                        else:
                            color_class = 'blue'
                        st.markdown(f"""
                        <div class="dashboard-card dashboard-card-{color_class}">
                            <div class="dashboard-title">{produto}</div>
                            <div class="dashboard-price">R$ {fmt_br(valor)}</div>
                            <div class="dashboard-metric">
                                <span class="dashboard-metric-label">PVU:</span> 
                                <span class="dashboard-metric-value">{fmt_br(produto_data['VHP c/lb PVU'])} c/lb</span>
                            </div>
                            <div class="dashboard-metric">
                                <span class="dashboard-metric-label">FOB:</span> 
                                <span class="dashboard-metric-value">{fmt_br(produto_data['VHP c/lb FOB'])} c/lb</span>
                            </div>
                            {f'<div class="dashboard-arbitrage"><div class="dashboard-arbitrage-label">Arbitragem Implícita</div><div class="dashboard-arbitrage-value dashboard-arbitrage-{"positive" if arbitragem and arbitragem > 0 else "negative"}">{fmt_br(arbitragem)} c/lb</div></div>' if arbitragem is not None else ''}
                        </div>
                        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Gráfico ranqueado - VHP
    if vhp_saca_list:
        st.markdown("### 📈 Ranking - Equivalente VHP R$/saca PVU")
        st.caption("💡 Este gráfico mostra quanto cada produto vale quando convertido para equivalente em **Açúcar VHP** (em R$/saca na Porta da Usina)")
        vhp_saca_list.sort(key=lambda x: x[1], reverse=True)
        
        # Cria DataFrame para o gráfico com informações de tipo
        produtos_vhp = [p[0] for p in vhp_saca_list]
        valores_vhp = [p[1] for p in vhp_saca_list]
        
        # Define cores baseadas no tipo de produto
        cores_vhp = []
        for produto in produtos_vhp:
            produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
            if produto_data:
                if produto_data['Tipo'] == 'Etanol':
                    cores_vhp.append('#3b82f6')  # Azul para etanol
                else:
                    cores_vhp.append('#f59e0b')  # Laranja para açúcar
            else:
                cores_vhp.append('#6b7280')  # Cinza padrão
        
        df_vhp_ranking = pd.DataFrame({
            'Produto': produtos_vhp,
            'Equivalente VHP (R$/saca)': valores_vhp
        })
        
        # Gráfico de barras horizontal estilizado com Plotly
        cores_vhp_list = []
        for produto in produtos_vhp:
            produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
            if produto_data:
                if produto_data['Tipo'] == 'Etanol':
                    cores_vhp_list.append('#3b82f6')  # Azul para etanol
                else:
                    cores_vhp_list.append('#f59e0b')  # Laranja para açúcar
            else:
                cores_vhp_list.append('#6b7280')
        
        fig_vhp = go.Figure(data=[go.Bar(
            y=produtos_vhp,
            x=valores_vhp,
            orientation='h',
            marker=dict(color=cores_vhp_list),
            text=[f"R$ {fmt_br(v)}" for v in valores_vhp],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Equivalente VHP: R$ %{x:,.2f}/saca<extra></extra>'
        )])
        
        fig_vhp.update_layout(
            title=dict(text="Ranking - Equivalente VHP (R$/saca PVU)", font=dict(size=16, color='#ffffff')),
            xaxis_title="Equivalente VHP (R$/saca)",
            yaxis_title="",
            height=400,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', size=12),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', showgrid=True),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', showgrid=False)
        )
        
        st.plotly_chart(fig_vhp, use_container_width=True)
        
        # Adiciona legenda de cores
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🔵 **Etanol**")
        with col2:
            st.markdown("🟠 **Açúcar**")
        
        st.markdown("---")
    
    # Tabela comparativa completa
    st.markdown("### 📊 Comparativo Completo - Equivalente VHP R$/saca PVU")
    st.caption("💡 Cada card mostra o valor equivalente em **Açúcar VHP** (em R$/saca na Porta da Usina). Quanto maior o valor, melhor a paridade.")
    
    if vhp_saca_list:
        # Ordena por valor
        vhp_saca_list.sort(key=lambda x: x[1], reverse=True)
        max_valor = vhp_saca_list[0][1]
        
        # Cria cards em grid
        num_cols = 3
        rows = [vhp_saca_list[i:i+num_cols] for i in range(0, len(vhp_saca_list), num_cols)]
        
        for row in rows:
            cols = st.columns(num_cols)
            for idx, (produto, valor) in enumerate(row):
                if idx < len(cols):
                    produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
                    if produto_data:
                        is_best = valor == max_valor
                        # Melhor visualização: verde para melhor, azul para etanol, laranja para açúcar
                        if is_best:
                            color = 'green'
                        elif produto_data['Tipo'] == 'Etanol':
                            color = 'blue'
                        else:
                            color = 'orange'
                        
                        with cols[idx]:
                            highlight_style = 'box-shadow: 0 0 20px rgba(16, 185, 129, 0.5); border: 2px solid #10b981;' if is_best else ''
                            st.markdown(f"""
                            <div class="dashboard-card dashboard-card-{color}" style="{highlight_style}">
                                <div class="dashboard-title">{produto}</div>
                                <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; font-weight: 500;">EQUIVALENTE VHP</div>
                                <div class="dashboard-price">R$ {fmt_br(valor)}</div>
                                <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 0.75rem; font-style: italic;">Equivalente em Açúcar VHP (R$/saca PVU)</div>
                                <div class="dashboard-metric">
                                    <span class="dashboard-metric-label">VHP PVU:</span> 
                                    <span class="dashboard-metric-value">{fmt_br(produto_data['VHP c/lb PVU'])} c/lb</span>
                                </div>
                                <div class="dashboard-metric">
                                    <span class="dashboard-metric-label">VHP FOB:</span> 
                                    <span class="dashboard-metric-value">{fmt_br(produto_data['VHP c/lb FOB'])} c/lb</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        
        if max_valor:
            melhor = next((d for d in dashboard_data_filtrado if d['VHP R$/saca PVU'] == max_valor), None)
            if melhor:
                st.success(f"🏆 **Melhor Paridade:** {melhor['Produto']} - R$ {fmt_br(max_valor)}/saca")
    
    st.markdown("---")
    
    # Gráfico ranqueado - Cristal
    if cristal_saca_list:
        st.markdown("### 📈 Ranking - Equivalente Cristal R$/saca PVU")
        st.caption("💡 Este gráfico mostra quanto cada produto vale quando convertido para equivalente em **Açúcar Cristal** (em R$/saca na Porta da Usina)")
        cristal_saca_list.sort(key=lambda x: x[1], reverse=True)
        
        # Cria DataFrame para o gráfico com informações de tipo
        produtos_cristal = [p[0] for p in cristal_saca_list]
        valores_cristal = [p[1] for p in cristal_saca_list]
        
        # Define cores baseadas no tipo de produto
        cores_cristal = []
        for produto in produtos_cristal:
            produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
            if produto_data:
                if produto_data['Tipo'] == 'Etanol':
                    cores_cristal.append('#3b82f6')  # Azul para etanol
                else:
                    cores_cristal.append('#f59e0b')  # Laranja para açúcar
            else:
                cores_cristal.append('#6b7280')  # Cinza padrão
        
        df_cristal_ranking = pd.DataFrame({
            'Produto': produtos_cristal,
            'Equivalente Cristal (R$/saca)': valores_cristal
        })
        
        # Gráfico de barras horizontal estilizado com Plotly
        cores_cristal_list = []
        for produto in produtos_cristal:
            produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
            if produto_data:
                if produto_data['Tipo'] == 'Etanol':
                    cores_cristal_list.append('#3b82f6')  # Azul para etanol
                else:
                    cores_cristal_list.append('#f59e0b')  # Laranja para açúcar
            else:
                cores_cristal_list.append('#6b7280')
        
        fig_cristal = go.Figure(data=[go.Bar(
            y=produtos_cristal,
            x=valores_cristal,
            orientation='h',
            marker=dict(color=cores_cristal_list),
            text=[f"R$ {fmt_br(v)}" for v in valores_cristal],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Equivalente Cristal: R$ %{x:,.2f}/saca<extra></extra>'
        )])
        
        fig_cristal.update_layout(
            title=dict(text="Ranking - Equivalente Cristal (R$/saca PVU)", font=dict(size=16, color='#ffffff')),
            xaxis_title="Equivalente Cristal (R$/saca)",
            yaxis_title="",
            height=400,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#ffffff', size=12),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)', showgrid=True),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)', showgrid=False)
        )
        
        st.plotly_chart(fig_cristal, use_container_width=True)
        
        # Adiciona legenda de cores
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("🔵 **Etanol**")
        with col2:
            st.markdown("🟠 **Açúcar**")
        
        st.markdown("---")
    
    # Comparativo Cristal
    if cristal_saca_list:
        st.markdown("### 🍬 Comparativo Completo - Equivalente Cristal R$/saca PVU")
        st.caption("💡 Cada card mostra o valor equivalente em **Açúcar Cristal** (em R$/saca na Porta da Usina). Quanto maior o valor, melhor a paridade.")
        
        cristal_saca_list.sort(key=lambda x: x[1], reverse=True)
        max_cristal = cristal_saca_list[0][1]
        
        num_cols = 3
        rows = [cristal_saca_list[i:i+num_cols] for i in range(0, len(cristal_saca_list), num_cols)]
        
        for row in rows:
            cols = st.columns(num_cols)
            for idx, (produto, valor) in enumerate(row):
                if idx < len(cols):
                    produto_data = next((d for d in dashboard_data_filtrado if d['Produto'] == produto), None)
                    if produto_data:
                        is_best = valor == max_cristal
                        # Melhor visualização: verde para melhor, azul para etanol, laranja para açúcar
                        if is_best:
                            color = 'green'
                        elif produto_data['Tipo'] == 'Etanol':
                            color = 'blue'
                        else:
                            color = 'orange'
                        
                        with cols[idx]:
                            # Calcula arbitragem VHP em c/lb
                            arbitragem_vhp = None
                            if produto_data['VHP c/lb PVU'] is not None and produto_data['Cristal c/lb PVU'] is not None:
                                arbitragem_vhp = produto_data['Cristal c/lb PVU'] - produto_data['VHP c/lb PVU']
                            
                            highlight_style = 'box-shadow: 0 0 20px rgba(16, 185, 129, 0.5); border: 2px solid #10b981;' if is_best else ''
                            st.markdown(f"""
                            <div class="dashboard-card dashboard-card-{color}" style="{highlight_style}">
                                <div class="dashboard-title">{produto}</div>
                                <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.5rem; font-weight: 500;">EQUIVALENTE CRISTAL</div>
                                <div class="dashboard-price">R$ {fmt_br(valor)}</div>
                                <div style="font-size: 0.7rem; color: #64748b; margin-bottom: 0.75rem; font-style: italic;">Equivalente em Açúcar Cristal (R$/saca PVU)</div>
                                <div class="dashboard-metric">
                                    <span class="dashboard-metric-label">Cristal PVU:</span> 
                                    <span class="dashboard-metric-value">{fmt_br(produto_data['Cristal c/lb PVU'])} c/lb</span>
                                </div>
                                <div class="dashboard-metric">
                                    <span class="dashboard-metric-label">Cristal FOB:</span> 
                                    <span class="dashboard-metric-value">{fmt_br(produto_data['Cristal c/lb FOB'])} c/lb</span>
                                </div>
                                {f'<div class="dashboard-arbitrage"><div class="dashboard-arbitrage-label">Arbitragem: Cristal vs VHP</div><div class="dashboard-arbitrage-value dashboard-arbitrage-{"positive" if arbitragem_vhp and arbitragem_vhp > 0 else "negative"}">{fmt_br(arbitragem_vhp)} c/lb</div></div>' if arbitragem_vhp is not None else ''}
                            </div>
                            """, unsafe_allow_html=True)
        
        if max_cristal:
            melhor = next((d for d in dashboard_data_filtrado if d['Cristal R$/saca PVU'] == max_cristal), None)
            if melhor:
                st.success(f"🏆 **Melhor Paridade:** {melhor['Produto']} - R$ {fmt_br(max_cristal)}/saca")
    
    st.markdown("---")
    
    # Seção de detalhes (discreta no final)
    with st.expander("📋 Detalhes dos Cálculos (Para Verificação)", expanded=False):
        st.markdown("### Detalhamento Completo das Paridades")
        
        # Exibe resultados detalhados
        # Container estilizado para as equivalências
        st.markdown("""
        <style>
        .equivalencia-container {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin: 1.5rem 0;
        }
        .equivalencia-card {
            border-left: 4px solid;
            padding: 1.25rem 1.5rem;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .equivalencia-card-red {
            border-left-color: #dc3545;
        }
        .equivalencia-card-green {
            border-left-color: #28a745;
        }
        .equivalencia-card-dark {
            border-left-color: #0d6efd;
        }
        .equivalencia-label {
            font-size: 1rem;
            font-weight: 500;
            flex: 1;
        }
        .equivalencia-label-red {
            color: #dc3545;
        }
        .equivalencia-label-green {
            color: #28a745;
        }
        .equivalencia-label-dark {
            color: #0d6efd;
        }
        .equivalencia-value {
            font-size: 1.75rem;
            font-weight: bold;
            margin-left: 1.5rem;
        }
        .equivalencia-value-red {
            color: #dc3545;
        }
        .equivalencia-value-green {
            color: #28a745;
        }
        .equivalencia-value-dark {
            color: #0d6efd;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if result_acucar_vhp.get('values'):
            valores_vhp = result_acucar_vhp['values']
            
            # Seção Açúcar VHP
            st.header("🍬 Açúcar VHP")
            
            # Equivalências em formato de cartões
            st.markdown("""
            <div class="equivalencia-container">
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
            </div>
            """.format(
                fmt_br(valores_vhp.get('equivalente_vhp_reais_saca_pvu', 0)),
                fmt_br(valores_vhp.get('equivalente_vhp_cents_lb_pvu', 0)),
                fmt_br(valores_vhp.get('equivalente_vhp_cents_lb_fob', 0))
            ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Açúcar Cristal ESALQ
        if result_acucar_cristal_esalq.get('values'):
            valores_esalq = result_acucar_cristal_esalq['values']
            
            st.header("🍬 Açúcar Cristal ESALQ")
            
            # Equivalências em formato de cartões
            st.markdown("""
            <div class="equivalencia-container">
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal R$/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal c/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
            </div>
            """.format(
                fmt_br(valores_esalq.get('equivalente_vhp_reais_saca_pvu', 0)),
                fmt_br(valores_esalq.get('equivalente_vhp_cents_lb_pvu', 0)),
                fmt_br(valores_esalq.get('equivalente_vhp_cents_lb_fob', 0)),
                fmt_br(valores_esalq.get('equivalente_cristal_reais_saca_pvu', 0)),
                fmt_br(valores_esalq.get('equivalente_cristal_cents_lb_pvu', 0)),
                fmt_br(valores_esalq.get('equivalente_cristal_cents_lb_fob', 0))
            ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Custo de Comercialização Açúcar Cristal MI
        if result_paridade_mi_ny.get('values'):
            valores_mi_ny = result_paridade_mi_ny['values']
            
            st.header("🍬 Custo de Comercialização Açúcar Cristal MI")
            
            # Equivalências em formato de cartões
            st.markdown("""
        <div class="equivalencia-container">
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal R$/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal c/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
        </div>
        """.format(
            fmt_br(valores_mi_ny.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_mi_ny.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_mi_ny.get('equivalente_vhp_cents_lb_fob', 0)),
            fmt_br(valores_mi_ny.get('equivalente_cristal_reais_saca_pvu', 0)),
            fmt_br(valores_mi_ny.get('equivalente_cristal_cents_lb_pvu', 0)),
            fmt_br(valores_mi_ny.get('equivalente_cristal_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Açúcar Cristal Exportação
        if result_acucar_cristal_exportacao.get('values'):
            valores_exportacao = result_acucar_cristal_exportacao['values']
            
            st.header("🍬 Açúcar Cristal Exportação")
            
            # Equivalências em formato de cartões
            st.markdown("""
        <div class="equivalencia-container">
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal R$/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal c/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
        </div>
        """.format(
            fmt_br(valores_exportacao.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_exportacao.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_exportacao.get('equivalente_vhp_cents_lb_fob', 0)),
            fmt_br(valores_exportacao.get('equivalente_cristal_reais_saca_pvu', 0)),
            fmt_br(valores_exportacao.get('equivalente_cristal_cents_lb_pvu', 0)),
            fmt_br(valores_exportacao.get('equivalente_cristal_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Açúcar Cristal Exportação Malha 30
        if result_acucar_cristal_exportacao_malha30.get('values'):
            valores_exportacao_malha30 = result_acucar_cristal_exportacao_malha30['values']
            
            st.header("🍬 Açúcar Cristal Exportação Malha 30")
            
            # Equivalências em formato de cartões
            st.markdown("""
        <div class="equivalencia-container">
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal R$/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal c/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
        </div>
        """.format(
            fmt_br(valores_exportacao_malha30.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_exportacao_malha30.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_exportacao_malha30.get('equivalente_vhp_cents_lb_fob', 0)),
            fmt_br(valores_exportacao_malha30.get('equivalente_cristal_reais_saca_pvu', 0)),
            fmt_br(valores_exportacao_malha30.get('equivalente_cristal_cents_lb_pvu', 0)),
            fmt_br(valores_exportacao_malha30.get('equivalente_cristal_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Etanol Anidro Exportação
        if result_etanol_anidro_exportacao.get('values'):
            valores_etanol_anidro = result_etanol_anidro_exportacao['values']
            
            st.header("⛽ Etanol Anidro Exportação")
            
            # Equivalências em formato de cartões
            st.markdown("""
        <div class="equivalencia-container">
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Preço Líquido PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente VHP BRL/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-green">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente VHP Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-red">{} c/lb</div>
            </div>
        </div>
        """.format(
            fmt_br(valores_etanol_anidro.get('preco_liquido_pvu', 0)),
            fmt_br(valores_etanol_anidro.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_etanol_anidro.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_etanol_anidro.get('equivalente_vhp_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Etanol Hidratado Mercado Interno
        if result_etanol_hidratado_mi.get('values'):
            valores_hidratado_mi = result_etanol_hidratado_mi['values']
            
            st.header("⛽ Etanol Hidratado Mercado Interno")
            
            # Valores intermediários (discretos)
            st.markdown("#### 📊 Valores Intermediários")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Preço Líquido PVU", f"R$ {fmt_br(valores_hidratado_mi.get('preco_liquido_pvu', 0))}")
                st.metric("Preço Líquido PVU + CBIO", f"R$ {fmt_br(valores_hidratado_mi.get('preco_liquido_pvu_mais_cbio', 0))}")
            with col2:
                st.metric("Equivalente Anidro", f"R$ {fmt_br(valores_hidratado_mi.get('equivalente_anidro', 0))}")
                st.metric("Preço Líquido PVU + CBIO + Crédito Trib.", f"R$ {fmt_br(valores_hidratado_mi.get('preco_liquido_pvu_mais_cbio_mais_credito', 0))}")
            
            st.divider()
            
            # Equivalências (enfatizadas)
            st.markdown("### 🎯 Equivalências")
            st.markdown("""
            <div class="equivalencia-container">
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
            </div>
            """.format(
                fmt_br(valores_hidratado_mi.get('equivalente_vhp_reais_saca_pvu', 0)),
                fmt_br(valores_hidratado_mi.get('equivalente_vhp_cents_lb_pvu', 0)),
                fmt_br(valores_hidratado_mi.get('equivalente_vhp_cents_lb_fob', 0)),
                fmt_br(valores_hidratado_mi.get('equivalente_cristal_reais_saca_pvu', 0)),
                fmt_br(valores_hidratado_mi.get('equivalente_cristal_cents_lb_pvu', 0)),
                fmt_br(valores_hidratado_mi.get('equivalente_cristal_cents_lb_fob', 0))
            ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Etanol Hidratado Exportação
        if result_etanol_hidratado_exportacao.get('values'):
            valores_etanol_hidratado = result_etanol_hidratado_exportacao['values']
            
            st.header("⛽ Etanol Hidratado Exportação")
            
            # Equivalências em formato de cartões
            st.markdown("""
        <div class="equivalencia-container">
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Preço Líquido PVU</div>
                <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-green">
                <div class="equivalencia-label equivalencia-label-green">Equivalente VHP BRL/saca PVU</div>
                <div class="equivalencia-value equivalencia-value-green">R$ {}</div>
            </div>
            <div class="equivalencia-card equivalencia-card-dark">
                <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb PVU</div>
                <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
            </div>
            <div class="equivalencia-card equivalencia-card-red">
                <div class="equivalencia-label equivalencia-label-red">Equivalente VHP Cents/lb FOB</div>
                <div class="equivalencia-value equivalencia-value-red">{} c/lb</div>
            </div>
        </div>
        """.format(
            fmt_br(valores_etanol_hidratado.get('preco_liquido_pvu', 0)),
            fmt_br(valores_etanol_hidratado.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_etanol_hidratado.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_etanol_hidratado.get('equivalente_vhp_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
            
            st.divider()
        
        # Seção Etanol Anidro Mercado Interno
        if result_etanol_anidro_mi.get('values'):
            valores_anidro_mi = result_etanol_anidro_mi['values']
            
            st.header("⛽ Etanol Anidro Mercado Interno")
            
            # Valores intermediários (discretos)
            st.markdown("#### 📊 Valores Intermediários")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Preço Líquido PVU", f"R$ {fmt_br(valores_anidro_mi.get('preco_liquido_pvu', 0))}")
                st.metric("CBIO Líquido de Impostos", f"R$ {fmt_br(valores_anidro_mi.get('cbio_liquido_impostos', 0))}")
            with col2:
                st.metric("Preço Líquido PVU + CBIO", f"R$ {fmt_br(valores_anidro_mi.get('preco_liquido_pvu_mais_cbio', 0))}")
                st.metric("Equivalente Hidratado", f"R$ {fmt_br(valores_anidro_mi.get('equivalente_hidratado', 0))}")
            
            st.divider()
            
            # Equivalências (enfatizadas)
            st.markdown("### 🎯 Equivalências")
            st.markdown("""
            <div class="equivalencia-container">
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente VHP BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente VHP Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente VHP Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-red">
                    <div class="equivalencia-label equivalencia-label-red">Equivalente Cristal BRL/saca PVU</div>
                    <div class="equivalencia-value equivalencia-value-red">R$ {}</div>
                </div>
                <div class="equivalencia-card equivalencia-card-green">
                    <div class="equivalencia-label equivalencia-label-green">Equivalente Cristal Cents/lb PVU</div>
                    <div class="equivalencia-value equivalencia-value-green">{} c/lb</div>
                </div>
                <div class="equivalencia-card equivalencia-card-dark">
                    <div class="equivalencia-label equivalencia-label-dark">Equivalente Cristal Cents/lb FOB</div>
                    <div class="equivalencia-value equivalencia-value-dark">{} c/lb</div>
                </div>
            </div>
            """.format(
            fmt_br(valores_anidro_mi.get('equivalente_vhp_reais_saca_pvu', 0)),
            fmt_br(valores_anidro_mi.get('equivalente_vhp_cents_lb_pvu', 0)),
            fmt_br(valores_anidro_mi.get('equivalente_vhp_cents_lb_fob', 0)),
            fmt_br(valores_anidro_mi.get('equivalente_cristal_reais_saca_pvu', 0)),
            fmt_br(valores_anidro_mi.get('equivalente_cristal_cents_lb_pvu', 0)),
            fmt_br(valores_anidro_mi.get('equivalente_cristal_cents_lb_fob', 0))
        ), unsafe_allow_html=True)
        
        st.divider()
