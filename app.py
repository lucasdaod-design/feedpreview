import uuid
from datetime import date
from io import BytesIO

import streamlit as st
from PIL import Image, ImageDraw, ImageOps
import requests
from supabase import create_client, Client

# --- CONFIGURAÇÃO DO SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def init_connection() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

STATUS_LABELS = {
    "Rascunho": "⚪ Rascunho",
    "Agendado": "🔵 Agendado",
    "Postado": "🟢 Postado",
}

# --- FUNÇÕES DE BANCO DE DADOS E NUVEM ---

def save_uploaded_image(uploaded_file) -> str | None:
    try:
        image = Image.open(uploaded_file).convert("RGB")
    except Exception:
        st.error(f"Não consegui abrir este arquivo como imagem: {uploaded_file.name}")
        return None

    filename = f"{uuid.uuid4()}.jpg"
    
    # --- NOVA LÓGICA DE PROPORÇÃO 4:5 (VERTICAL INSTAGRAM) ---
    target_width = 1080
    target_height = 1350
    
    # Corta e centraliza a imagem automaticamente para 1080x1350
    image = ImageOps.fit(image, (target_width, target_height), method=Image.Resampling.LANCZOS)
    
    output = BytesIO()
    image.save(output, format="JPEG", quality=88)
    file_bytes = output.getvalue()
    
    try:
        # Sobe para o bucket
        supabase.storage.from_("feed-images").upload(
            file=file_bytes,
            path=filename,
            file_options={"content-type": "image/jpeg"}
        )
        # Pega o link público
        public_url = supabase.storage.from_("feed-images").get_public_url(filename)
        return public_url
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")
        return None

    filename = f"{uuid.uuid4()}.jpg"
    
    # Reduz a imagem antes de subir
    output = BytesIO()
    image.thumbnail((1600, 1600))
    image.save(output, format="JPEG", quality=88)
    file_bytes = output.getvalue()
    
    try:
        # Sobe para o bucket
        supabase.storage.from_("feed-images").upload(
            file=file_bytes,
            path=filename,
            file_options={"content-type": "image/jpeg"}
        )
        # Pega o link público
        public_url = supabase.storage.from_("feed-images").get_public_url(filename)
        return public_url
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")
        return None

def save_project():
    project_name = st.session_state.project.get("name", "Meu Feed")
    posts = st.session_state.project["posts"]
    
    # Deleta os posts antigos deste projeto para atualizar
    supabase.table("posts").delete().eq("project_name", project_name).execute()
    
    if posts:
        data_to_insert = []
        for i, p in enumerate(posts):
            data_to_insert.append({
                "project_name": project_name,
                "image_url": p["image_url"],
                "caption": p.get("caption", ""),
                "planned_date": p.get("planned_date", ""),
                "status": p.get("status", "Rascunho"),
                "order_index": i
            })
        supabase.table("posts").insert(data_to_insert).execute()
    
    st.session_state.last_saved_path = f"Salvo na nuvem: {project_name}"

def load_project(project_name: str):
    response = supabase.table("posts").select("*").eq("project_name", project_name).order("order_index").execute()
    
    loaded_posts = []
    for row in response.data:
        loaded_posts.append({
            "id": str(uuid.uuid4()),
            "image_url": row["image_url"],
            "caption": row.get("caption", ""),
            "planned_date": row.get("planned_date", ""),
            "status": row.get("status", "Rascunho"),
        })
        
    st.session_state.project = {
        "name": project_name,
        "posts": loaded_posts,
    }
    st.session_state.selected_index = None

def get_saved_projects():
    response = supabase.table("posts").select("project_name").execute()
    projects = list(set([row["project_name"] for row in response.data]))
    return sorted(projects)

# --- LÓGICA DO APP ---

def empty_project() -> dict:
    return {"name": "Novo Projeto", "posts": []}

def new_post(image_url: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "image_url": image_url,
        "caption": "",
        "planned_date": "",
        "status": "Rascunho",
    }

def init_state() -> None:
    if "project" not in st.session_state:
        st.session_state.project = empty_project()
    if "selected_index" not in st.session_state:
        st.session_state.selected_index = None
    if "last_saved_path" not in st.session_state:
        st.session_state.last_saved_path = ""

def move_post(index: int, direction: int) -> None:
    posts = st.session_state.project["posts"]
    new_index = index + direction
    if 0 <= new_index < len(posts):
        posts[index], posts[new_index] = posts[new_index], posts[index]
        st.session_state.selected_index = new_index

def delete_post(index: int) -> None:
    posts = st.session_state.project["posts"]
    if 0 <= index < len(posts):
        posts.pop(index)
    st.session_state.selected_index = None

# --- INTERFACE ---

def render_feed_grid(posts: list[dict], empty_slots: int, is_client_view: bool) -> None:
    total_items = len(posts) + empty_slots
    total_items = max(total_items, 9)

    for start in range(0, total_items, 3):
        cols = st.columns(3, gap="small")
        for offset, col in enumerate(cols):
            index = start + offset

            with col:
                if index < len(posts):
                    post = posts[index]
                    with st.container(border=True):
                        st.image(post["image_url"], use_container_width=True)
                        
                        if is_client_view:
                            # VISÃO DO CLIENTE: Mostra legenda e data direto, sem botões
                            if post.get("planned_date"):
                                st.markdown(f"**📅 Para:** {post['planned_date']}")
                            if post.get("caption"):
                                st.caption(post["caption"])
                        else:
                            # SUA VISÃO: Botões de edição e mover
                            st.caption(f"{index + 1:02d} · {STATUS_LABELS.get(post['status'], post['status'])}")
                            if post.get("planned_date"):
                                st.caption(f"📅 {post['planned_date']}")
                            
                            b_cols = st.columns(3)
                            with b_cols[0]:
                                if st.button("⬅️", key=f"left_{post['id']}"):
                                    move_post(index, -1)
                                    st.rerun()
                            with b_cols[1]:
                                if st.button("✏️", key=f"edit_{post['id']}"):
                                    st.session_state.selected_index = index
                                    st.rerun()
                            with b_cols[2]:
                                if st.button("➡️", key=f"right_{post['id']}"):
                                    move_post(index, 1)
                                    st.rerun()
                else:
                    with st.container(border=True):
                        st.markdown(
                            """<div style="aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center; background: #f3f4f6; border-radius: 10px; color: #9ca3af; font-size: 42px; font-weight: 700;">+</div>""",
                            unsafe_allow_html=True,
                        )

def render_editor() -> None:
    selected_index = st.session_state.selected_index
    posts = st.session_state.project["posts"]

    if selected_index is None or selected_index >= len(posts):
        st.info("Clique no botão ✏️ de uma foto para editar legenda, data e status.")
        return

    post = posts[selected_index]
    st.subheader(f"Editar post {selected_index + 1}")
    st.image(post["image_url"], use_container_width=True)

    with st.form(key=f"edit_form_{post['id']}"):
        caption = st.text_area("Legenda interna", value=post.get("caption", ""), height=120)
        
        current_date_value = None
        if post.get("planned_date"):
            try:
                current_date_value = date.fromisoformat(post["planned_date"])
            except ValueError:
                pass

        planned_date = st.date_input("Data planejada", value=current_date_value, format="DD/MM/YYYY")
        status = st.selectbox("Status", list(STATUS_LABELS.keys()), index=list(STATUS_LABELS.keys()).index(post.get("status", "Rascunho")))
        save_col, delete_col = st.columns(2)

        with save_col:
            save_clicked = st.form_submit_button("Salvar edição", use_container_width=True)
        with delete_col:
            delete_clicked = st.form_submit_button("Excluir post", use_container_width=True)

    if save_clicked:
        post["caption"] = caption
        post["planned_date"] = planned_date.isoformat() if planned_date else ""
        post["status"] = status
        save_project()
        st.success("Post atualizado!")
        st.rerun()

    if delete_clicked:
        delete_post(selected_index)
        save_project()
        st.success("Post excluído!")
        st.rerun()

def main() -> None:
    st.set_page_config(page_title="Feed Planner", page_icon="📸", layout="wide")
    init_state()

    # Verifica se a URL tem ?view=cliente
    is_client_view = st.query_params.get("view") == "cliente"

    if is_client_view:
        st.title(f"📸 Previsão de Feed: {st.session_state.project['name']}")
        st.write("Acompanhe abaixo a prévia visual e as legendas programadas para o seu perfil.")
        render_feed_grid(st.session_state.project["posts"], empty_slots=0, is_client_view=True)
        return  # Encerra o app aqui para o cliente não ver o resto!

    # --- TELA DE ADMINISTRAÇÃO (Sua Tela) ---
    st.title("📸 Feed Planner Pro")
    
    with st.sidebar:
        st.header("Projeto")
        project_name = st.text_input("Nome do projeto (ex: Marca X)", value=st.session_state.project["name"])
        st.session_state.project["name"] = project_name

        saved_projects = get_saved_projects()
        if saved_projects:
            selected_project = st.selectbox("Projetos na Nuvem", saved_projects)
            if st.button("Carregar Projeto", use_container_width=True):
                load_project(selected_project)
                st.success(f"{selected_project} carregado com sucesso!")
                st.rerun()

        if st.button("Novo projeto", use_container_width=True):
            st.session_state.project = empty_project()
            st.session_state.selected_index = None
            st.rerun()

        st.divider()
        st.header("Fotos")
        uploaded_files = st.file_uploader("Adicionar fotos", accept_multiple_files=True)

        if uploaded_files and st.button("Subir fotos para a nuvem", use_container_width=True):
            with st.spinner("Enviando imagens..."):
                for uploaded_file in uploaded_files:
                    image_url = save_uploaded_image(uploaded_file)
                    if image_url:
                        st.session_state.project["posts"].append(new_post(image_url))
                save_project()
            st.rerun()

        empty_slots = st.number_input("Espaços vazios", min_value=0, max_value=60, value=max(9 - len(st.session_state.project["posts"]), 0), step=3)
        st.divider()

        if st.button("Salvar alterações na Nuvem", use_container_width=True):
            save_project()
            st.success("Tudo salvo!")
            # ... (código existente da sidebar)

        # --- NOVO BLOCO: LINK DE COMPARTILHAMENTO ---
        st.divider()
        st.header("🔗 Link para o Cliente")
        st.write("Copie o link abaixo e envie para aprovação:")
        
        # Substitua "seu-app" pelo nome real que o Streamlit te der quando publicarmos
        link_cliente = "https://feedpreview-hrmqly8wuwbvgjrtcjbrbb.streamlit.app/?view=cliente"
        
        st.code(link_cliente, language="text")

    left, right = st.columns([2.2, 1], gap="large")
    with left:
        st.subheader("Prévia do feed")
        render_feed_grid(st.session_state.project["posts"], int(empty_slots), is_client_view=False)
    with right:
        render_editor()

if __name__ == "__main__":
    main()