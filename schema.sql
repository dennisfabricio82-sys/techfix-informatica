
-- ============================================================
-- TECHFIX INFORMÁTICA
-- Sistema de Ordens de Serviço
-- Banco de dados: Supabase / PostgreSQL
-- Arquivo: sql/schema.sql
-- ============================================================

-- 1. TABELA DE CLIENTES
-- Armazena os dados cadastrais de cada cliente.
-- O e-mail é único para evitar cadastros duplicados.

CREATE TABLE public.clientes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    nome TEXT NOT NULL
        CHECK (length(trim(nome)) > 0),

    endereco TEXT NOT NULL
        CHECK (length(trim(endereco)) > 0),

    email TEXT NOT NULL UNIQUE
        CHECK (
            email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        ),

    celular_whatsapp TEXT NOT NULL
        CHECK (
            celular_whatsapp ~ '^[0-9]{10,13}$'
        ),

    data_cadastro TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. TABELA DE ORDENS DE SERVIÇO
-- Cada ordem pertence a um cliente.
-- Um cliente pode possuir várias ordens de serviço.
-- ON DELETE RESTRICT impede excluir um cliente que ainda
-- possua ordens de serviço vinculadas.

CREATE TABLE public.ordens_servico (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cliente_id BIGINT NOT NULL
        REFERENCES public.clientes(id)
        ON DELETE RESTRICT,

    modelo_computador TEXT NOT NULL
        CHECK (length(trim(modelo_computador)) > 0),

    problema_relatado TEXT NOT NULL
        CHECK (length(trim(problema_relatado)) > 0),

    status TEXT NOT NULL DEFAULT 'Aberto'
        CHECK (
            status IN (
                'Aberto',
                'Em análise',
                'Aguardando peça',
                'Concluído',
                'Entregue'
            )
        ),

    data_abertura TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    data_atualizacao TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. ÍNDICES
-- Melhoram a eficiência das consultas e dos filtros.
-- O campo email já possui índice criado pelo UNIQUE.

CREATE INDEX idx_os_cliente
    ON public.ordens_servico(cliente_id);

CREATE INDEX idx_os_status
    ON public.ordens_servico(status);

CREATE INDEX idx_clientes_nome
    ON public.clientes(nome);

-- 4. ATUALIZAÇÃO AUTOMÁTICA DA DATA
-- Sempre que uma ordem de serviço for alterada,
-- data_atualizacao receberá a data e hora atuais.

CREATE OR REPLACE FUNCTION public.atualizar_data_os()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.data_atualizacao = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_atualizar_data_os
BEFORE UPDATE ON public.ordens_servico
FOR EACH ROW
EXECUTE FUNCTION public.atualizar_data_os();

-- 5. SEGURANÇA: ROW LEVEL SECURITY
-- Habilita o controle de acesso por linha nas tabelas.

ALTER TABLE public.clientes
    ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.ordens_servico
    ENABLE ROW LEVEL SECURITY;

-- 6. RESTRIÇÃO DE ACESSO À API
-- Impede que usuários anônimos ou autenticados acessem
-- diretamente as tabelas sem autorização adicional.
-- Não criamos políticas públicas de leitura ou escrita.

REVOKE ALL ON TABLE public.clientes
    FROM anon, authenticated;

REVOKE ALL ON TABLE public.ordens_servico
    FROM anon, authenticated;

REVOKE ALL ON SEQUENCE public.clientes_id_seq
    FROM anon, authenticated;

REVOKE ALL ON SEQUENCE public.ordens_servico_id_seq
    FROM anon, authenticated;

-- 7. PERMISSÕES DO BACKEND
-- As aplicações Python usarão uma chave secreta
-- exclusivamente no servidor, nunca no navegador.
-- O acesso administrativo fica restrito ao service_role.

GRANT SELECT, INSERT, UPDATE, DELETE
    ON public.clientes, public.ordens_servico
    TO service_role;

GRANT USAGE, SELECT
    ON SEQUENCE public.clientes_id_seq,
                public.ordens_servico_id_seq
    TO service_role;

-- ============================================================
-- FIM DO SCRIPT
-- ============================================================
