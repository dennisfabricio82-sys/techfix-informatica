
# app_gradio.py — TechFix Informática
# Formulário de cadastro de clientes e ordens de serviço

import os
import re

import gradio as gr
from dotenv import load_dotenv
from supabase import create_client


# ---------------------------------------------------------
# CONFIGURAÇÃO DO SUPABASE
# ---------------------------------------------------------

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env."
    )

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------
# CADASTRO DE CLIENTES E ORDENS DE SERVIÇO
# ---------------------------------------------------------

def cadastrar_ordem(
    nome,
    endereco,
    email,
    celular,
    modelo_computador,
    problema_relatado,
):
    """Valida os dados e registra uma ordem de serviço."""

    nome = (nome or "").strip()
    endereco = (endereco or "").strip()
    email = (email or "").strip().lower()
    celular = re.sub(r"\D", "", celular or "")
    modelo_computador = (modelo_computador or "").strip()
    problema_relatado = (problema_relatado or "").strip()

    if not all([
        nome,
        endereco,
        email,
        celular,
        modelo_computador,
        problema_relatado,
    ]):
        return "❌ Preencha todos os campos obrigatórios."

    if not re.fullmatch(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        email,
    ):
        return "❌ Informe um e-mail válido."

    if not 10 <= len(celular) <= 13:
        return "❌ O celular deve conter entre 10 e 13 dígitos."

    try:
        consulta = (
            supabase.table("clientes")
            .select("id")
            .eq("email", email)
            .limit(1)
            .execute()
        )

        if consulta.data:
            cliente_id = consulta.data[0]["id"]
            cliente_existente = True

        else:
            novo_cliente = (
                supabase.table("clientes")
                .insert({
                    "nome": nome,
                    "endereco": endereco,
                    "email": email,
                    "celular_whatsapp": celular,
                })
                .execute()
            )

            cliente_id = novo_cliente.data[0]["id"]
            cliente_existente = False

        nova_ordem = (
            supabase.table("ordens_servico")
            .insert({
                "cliente_id": cliente_id,
                "modelo_computador": modelo_computador,
                "problema_relatado": problema_relatado,
                "status": "Aberto",
            })
            .execute()
        )

        numero_os = nova_ordem.data[0]["id"]

        observacao = (
            "Cliente já cadastrado, identificado pelo e-mail."
            if cliente_existente
            else "Novo cliente cadastrado com sucesso."
        )

        return (
            f"### ✅ Ordem de serviço nº {numero_os} registrada!\n\n"
            f"**Cliente:** {nome}\n\n"
            f"**Status:** Aberto\n\n"
            f"{observacao}"
        )

    except Exception:
        return (
            "❌ Não foi possível registrar a ordem de serviço. "
            "Verifique os dados ou procure o responsável pelo sistema."
        )


# ---------------------------------------------------------
# LIMPAR FORMULÁRIO
# ---------------------------------------------------------

def limpar_formulario():
    return ("", "", "", "", "", "", "")


# ---------------------------------------------------------
# INTERFACE GRADIO
# ---------------------------------------------------------

with gr.Blocks(title="TechFix Informática") as demo:

    gr.Markdown(
        """
        # 🔧 TechFix Informática
        ### Cadastro de clientes e ordens de serviço

        Preencha os dados abaixo para solicitar atendimento técnico.
        """
    )

    with gr.Row():

        with gr.Column():

            nome = gr.Textbox(
                label="Nome completo",
                placeholder="Digite o nome do cliente",
            )

            endereco = gr.Textbox(
                label="Endereço",
                placeholder="Rua, número, bairro e cidade",
            )

            email = gr.Textbox(
                label="E-mail",
                placeholder="exemplo@email.com",
            )

            celular = gr.Textbox(
                label="Celular / WhatsApp",
                placeholder="11999999999",
            )

        with gr.Column():

            modelo = gr.Textbox(
                label="Modelo do computador",
                placeholder="Ex.: Dell Inspiron 15",
            )

            problema = gr.Textbox(
                label="Problema apresentado",
                placeholder="Descreva o defeito do equipamento",
                lines=6,
            )

    with gr.Row():

        cadastrar = gr.Button(
            "Cadastrar ordem de serviço",
            variant="primary",
        )

        limpar = gr.Button("Limpar")

    resultado = gr.Markdown()

    cadastrar.click(
        fn=cadastrar_ordem,
        inputs=[
            nome,
            endereco,
            email,
            celular,
            modelo,
            problema,
        ],
        outputs=resultado,
    )

    limpar.click(
        fn=limpar_formulario,
        inputs=[],
        outputs=[
            nome,
            endereco,
            email,
            celular,
            modelo,
            problema,
            resultado,
        ],
    )


# ---------------------------------------------------------
# EXECUÇÃO DO GRADIO — LINK PÚBLICO
# ---------------------------------------------------------

if __name__ == "__main__":

    usuario = os.getenv("GRADIO_USER")
    senha = os.getenv("GRADIO_PASSWORD")

    if not usuario or not senha:
        raise RuntimeError(
            "Configure GRADIO_USER e GRADIO_PASSWORD no arquivo .env."
        )

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=True,
        auth=(usuario, senha),
        show_error=False,
    )



