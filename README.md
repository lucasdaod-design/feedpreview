# Feed Planner Streamlit MVP

App simples em Python + Streamlit para controlar prévia de feed em grade 3xN.

## Funções

- Upload de várias fotos.
- Grade 3xN parecida com o feed do Instagram.
- Mover fotos para esquerda/direita.
- Editar legenda interna.
- Editar data planejada.
- Status: Rascunho, Agendado ou Postado.
- Salvar projeto local em JSON.
- Carregar projeto salvo.
- Exportar preview em PNG.

## Como rodar no VS Code

### 1. Criar ambiente virtual

No terminal, dentro da pasta do projeto:

```bash
py -m venv .venv
```

### 2. Ativar ambiente virtual no Windows

```bash
.venv\Scripts\activate
```

Se estiver no Mac ou Linux:

```bash
source .venv/bin/activate
```

### 3. Instalar bibliotecas

```bash
pip install -r requirements.txt
```

### 4. Rodar o app

```bash
streamlit run app.py
```

O app vai abrir no navegador.

## Estrutura de pastas

```text
feed_planner_streamlit/
├── app.py
├── requirements.txt
├── README.md
└── data/
    ├── images/
    └── projects/
```

As pastas `data/images` e `data/projects` são criadas automaticamente quando o app roda.

## Observação

Esse é um MVP local. Ele ainda não tem login, nuvem, integração com Instagram nem arrastar-e-soltar verdadeiro. 
A organização das fotos é feita pelos botões de mover.
