
# app_streamlit.py — TechFix Informática
# Sistema administrativo integrado ao Supabase

import os
import re
import hmac

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(
    page_title="TechFix | Administração",
    page_icon="🔧",
    layout="wide",
)

STATUS = [
    "Aberto",
    "Em análise",
    "Aguardando peça",
    "Concluído",
    "Entregue",
]


@st.cache_resource
def conectar():
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY")

    if not url or not chave:
        raise RuntimeError("Credenciais do Supabase não configuradas.")

    return create_client(url, chave)


def executar(operacao):
    """Executa uma operação sem expor detalhes internos ao usuário."""
    try:
        return operacao(), None
    except Exception:
        return None, "Não foi possível concluir a operação no banco de dados."


def validar_cliente(nome, endereco, email, celular):
    nome = nome.strip()
    endereco = endereco.strip()
    email = email.strip().lower()
    celular = re.sub(r"\D", "", celular)

    if not nome or not endereco:
        return None, "Nome e endereço são obrigatórios."

    if not re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        email,
    ):
        return None, "Informe um e-mail válido."

    if not 10 <= len(celular) <= 13:
        return None, "O celular deve conter entre 10 e 13 dígitos."

    return {
        "nome": nome,
        "endereco": endereco,
        "email": email,
        "celular_whatsapp": celular,
    }, None


def autenticar():
    senha_correta = os.getenv("ADMIN_PASSWORD")

    if not senha_correta:
        st.error("ADMIN_PASSWORD não configurada no arquivo .env.")
        st.stop()

    if st.session_state.get("autenticado", False):
        return

    st.title("🔧 TechFix Informática")
    st.subheader("Acesso administrativo")

    with st.form("login"):
        senha = st.text_input("Senha administrativa", type="password")
        entrar = st.form_submit_button("Entrar", type="primary")

    if entrar:
        if hmac.compare_digest(senha, senha_correta):
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Senha incorreta.")

    st.stop()


autenticar()
db = conectar()

with st.sidebar:
    st.title("🔧 TechFix")
    st.caption("Painel administrativo")

    if st.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

    st.divider()

    filtro_nome = st.text_input("Filtrar por nome ou e-mail")
    filtro_status = st.selectbox(
        "Filtrar por status",
        ["Todos"] + STATUS,
    )

st.title("Administração de ordens de serviço")
st.caption("Clientes, equipamentos e acompanhamento de atendimentos")


def carregar_dados():
    clientes, erro_clientes = executar(
        lambda: db.table("clientes")
        .select("*")
        .order("id")
        .execute()
    )

    ordens, erro_ordens = executar(
        lambda: db.table("ordens_servico")
        .select("*")
        .order("id", desc=True)
        .execute()
    )

    if erro_clientes or erro_ordens:
        st.error("Não foi possível carregar os dados do Supabase.")
        st.stop()

    return clientes.data or [], ordens.data or []


clientes, ordens = carregar_dados()

clientes_por_id = {c["id"]: c for c in clientes}

registros = []

for ordem in ordens:
    cliente = clientes_por_id.get(ordem["cliente_id"], {})

    registros.append({
        "OS": ordem["id"],
        "Cliente ID": ordem["cliente_id"],
        "Cliente": cliente.get("nome", ""),
        "E-mail": cliente.get("email", ""),
        "Celular": cliente.get("celular_whatsapp", ""),
        "Modelo": ordem["modelo_computador"],
        "Problema": ordem["problema_relatado"],
        "Status": ordem["status"],
        "Abertura": ordem.get("data_abertura", ""),
    })

df = pd.DataFrame(registros)

aba_consultar, aba_cadastrar, aba_editar, aba_indicadores = st.tabs(
    ["Consultar", "Cadastrar", "Editar / Excluir", "Indicadores"]
)

# ---------------------------------------------------------
# ABA 1 — CONSULTAR
# ---------------------------------------------------------

with aba_consultar:
    st.subheader("Consultar ordens de serviço")

    if df.empty:
        st.info("Nenhuma ordem de serviço cadastrada.")
    else:
        filtrado = df.copy()

        if filtro_nome.strip():
            busca = filtro_nome.strip()
            filtro = (
                filtrado["Cliente"].str.contains(
                    busca, case=False, regex=False, na=False
                )
                | filtrado["E-mail"].str.contains(
                    busca, case=False, regex=False, na=False
                )
            )
            filtrado = filtrado[filtro]

        if filtro_status != "Todos":
            filtrado = filtrado[filtrado["Status"] == filtro_status]

        st.dataframe(
            filtrado,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Baixar consulta em CSV",
            data=filtrado.to_csv(index=False).encode("utf-8-sig"),
            file_name="techfix_ordens_servico.csv",
            mime="text/csv",
        )

    with st.expander("Visualizar tabela de clientes"):
        if clientes:
            st.dataframe(
                pd.DataFrame(clientes),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhum cliente cadastrado.")

# ---------------------------------------------------------
# ABA 2 — CADASTRAR
# ---------------------------------------------------------

with aba_cadastrar:
    st.subheader("Cadastrar cliente")

    with st.form("form_novo_cliente"):
        nome = st.text_input("Nome completo")
        endereco = st.text_input("Endereço")
        email = st.text_input("E-mail")
        celular = st.text_input("Celular / WhatsApp")

        salvar_cliente = st.form_submit_button(
            "Salvar cliente", type="primary"
        )

    if salvar_cliente:
        dados, erro = validar_cliente(nome, endereco, email, celular)

        if erro:
            st.error(erro)
        else:
            resultado, erro_banco = executar(
                lambda: db.table("clientes").insert(dados).execute()
            )

            if erro_banco:
                st.error(
                    "Não foi possível cadastrar. "
                    "Verifique se o e-mail já está registrado."
                )
            else:
                st.success("Cliente cadastrado com sucesso.")
                st.rerun()

    st.divider()
    st.subheader("Abrir nova ordem de serviço")

    if not clientes:
        st.info("Cadastre um cliente antes de abrir uma ordem.")
    else:
        opcoes_clientes = {
            f'{c["nome"]} — {c["email"]} (ID {c["id"]})': c["id"]
            for c in clientes
        }

        with st.form("form_nova_os"):
            cliente_escolhido = st.selectbox(
                "Cliente", list(opcoes_clientes.keys())
            )
            modelo = st.text_input("Modelo do computador")
            problema = st.text_area("Problema relatado")

            salvar_os = st.form_submit_button(
                "Criar ordem de serviço", type="primary"
            )

        if salvar_os:
            if not modelo.strip() or not problema.strip():
                st.error("Informe o modelo e o problema relatado.")
            else:
                resultado, erro_banco = executar(
                    lambda: db.table("ordens_servico").insert({
                        "cliente_id": opcoes_clientes[cliente_escolhido],
                        "modelo_computador": modelo.strip(),
                        "problema_relatado": problema.strip(),
                        "status": "Aberto",
                    }).execute()
                )

                if erro_banco:
                    st.error("Não foi possível criar a ordem de serviço.")
                else:
                    st.success(
                        f'Ordem de serviço nº '
                        f'{resultado.data[0]["id"]} criada com sucesso.'
                    )

# ---------------------------------------------------------
# ABA 3 — EDITAR / EXCLUIR
# ---------------------------------------------------------

with aba_editar:
    st.subheader("Editar ordem de serviço")

    if not ordens:
        st.info("Nenhuma ordem de serviço disponível.")
    else:
        opcoes_os = {
            f'OS nº {o["id"]} — '
            f'{clientes_por_id.get(o["cliente_id"], {}).get("nome", "")}':
            o
            for o in ordens
        }

        escolha_os = st.selectbox(
            "Selecione a ordem de serviço",
            list(opcoes_os.keys()),
        )

        os_atual = opcoes_os[escolha_os]

        with st.form("editar_os"):
            modelo_editado = st.text_input(
                "Modelo do computador",
                value=os_atual["modelo_computador"],
            )
            problema_editado = st.text_area(
                "Problema relatado",
                value=os_atual["problema_relatado"],
            )
            status_editado = st.selectbox(
                "Status",
                STATUS,
                index=STATUS.index(os_atual["status"]),
            )

            salvar_edicao = st.form_submit_button(
                "Salvar alterações", type="primary"
            )

        if salvar_edicao:
            if not modelo_editado.strip() or not problema_editado.strip():
                st.error("Modelo e problema são obrigatórios.")
            else:
                _, erro = executar(
                    lambda: db.table("ordens_servico")
                    .update({
                        "modelo_computador": modelo_editado.strip(),
                        "problema_relatado": problema_editado.strip(),
                        "status": status_editado,
                    })
                    .eq("id", os_atual["id"])
                    .execute()
                )

                if erro:
                    st.error(erro)
                else:
                    st.success("Ordem de serviço atualizada.")
                    st.rerun()

        st.divider()
        st.warning("A exclusão de uma ordem de serviço é definitiva.")

        confirmar_os = st.checkbox(
            f'Confirmo a exclusão da OS nº {os_atual["id"]}',
            key=f'excluir_os_{os_atual["id"]}',
        )

        if st.button(
            "Excluir ordem de serviço",
            disabled=not confirmar_os,
        ):
            _, erro = executar(
                lambda: db.table("ordens_servico")
                .delete()
                .eq("id", os_atual["id"])
                .execute()
            )

            if erro:
                st.error(erro)
            else:
                st.success("Ordem de serviço excluída.")
                st.rerun()

    st.divider()
    st.subheader("Editar dados de cliente")

    if clientes:
        opcoes_edicao = {
            f'{c["nome"]} — ID {c["id"]}': c
            for c in clientes
        }

        escolha_cliente = st.selectbox(
            "Selecione o cliente",
            list(opcoes_edicao.keys()),
        )

        cliente_atual = opcoes_edicao[escolha_cliente]

        with st.form("editar_cliente"):
            nome_editado = st.text_input(
                "Nome completo", value=cliente_atual["nome"]
            )
            endereco_editado = st.text_input(
                "Endereço", value=cliente_atual["endereco"]
            )
            email_editado = st.text_input(
                "E-mail", value=cliente_atual["email"]
            )
            celular_editado = st.text_input(
                "Celular / WhatsApp",
                value=cliente_atual["celular_whatsapp"],
            )

            salvar_cliente_editado = st.form_submit_button(
                "Salvar dados do cliente"
            )

        if salvar_cliente_editado:
            dados, erro = validar_cliente(
                nome_editado,
                endereco_editado,
                email_editado,
                celular_editado,
            )

            if erro:
                st.error(erro)
            else:
                _, erro_banco = executar(
                    lambda: db.table("clientes")
                    .update(dados)
                    .eq("id", cliente_atual["id"])
                    .execute()
                )

                if erro_banco:
                    st.error(
                        "Não foi possível atualizar o cliente. "
                        "Verifique se o e-mail já existe."
                    )
                else:
                    st.success("Dados do cliente atualizados.")
                    st.rerun()

        st.divider()

        possui_ordens = any(
            o["cliente_id"] == cliente_atual["id"]
            for o in ordens
        )

        if possui_ordens:
            st.info(
                "Este cliente possui ordens de serviço. "
                "Exclua primeiro as ordens vinculadas para "
                "poder excluir o cliente."
            )
        else:
            confirmar_cliente = st.checkbox(
                f'Confirmo a exclusão de {cliente_atual["nome"]}',
                key=f'excluir_cliente_{cliente_atual["id"]}',
            )

            if st.button(
                "Excluir cliente",
                disabled=not confirmar_cliente,
            ):
                _, erro = executar(
                    lambda: db.table("clientes")
                    .delete()
                    .eq("id", cliente_atual["id"])
                    .execute()
                )

                if erro:
                    st.error(erro)
                else:
                    st.success("Cliente excluído.")
                    st.rerun()

# ---------------------------------------------------------
# ABA 4 — INDICADORES
# ---------------------------------------------------------

with aba_indicadores:
    st.subheader("Indicadores de atendimento")

    total_clientes = len(clientes)
    total_ordens = len(ordens)
    abertas = sum(o["status"] == "Aberto" for o in ordens)
    concluidas = sum(
        o["status"] in ("Concluído", "Entregue")
        for o in ordens
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Clientes cadastrados", total_clientes)
    col2.metric("Total de ordens", total_ordens)
    col3.metric("Ordens abertas", abertas)
    col4.metric("Concluídas / entregues", concluidas)

    contagem = pd.DataFrame({
        "Status": STATUS,
        "Quantidade": [
            sum(o["status"] == status for o in ordens)
            for status in STATUS
        ],
    })

    st.subheader("Ordens de serviço por status")

    st.bar_chart(
        contagem.set_index("Status"),
        y="Quantidade",
    )

    st.caption(
        "Indicadores calculados com os registros disponíveis "
        "no banco de dados Supabase."
    )
