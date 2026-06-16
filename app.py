from __future__ import annotations

import json
import re
import uuid
from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageOps


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
IMAGE_DIR = DATA_DIR / "images"
PROJECT_DIR = DATA_DIR / "projects"

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
PROJECT_DIR.mkdir(parents=True, exist_ok=True)

STATUS_LABELS = {
    "Rascunho": "⚪ Rascunho",
    "Agendado": "🔵 Agendado",
    "Postado": "🟢 Postado",
}


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9áéíóúâêôãõçüñ -]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text or "meu-feed"


def empty_project() -> dict:
    return {
        "name": "Meu Feed",
        "posts": [],
        "created_with": "Feed Planner Streamlit MVP",
    }


def new_post(image_path: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "image_path": image_path,
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


def save_uploaded_image(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in [".jpg", ".jpeg", ".png", ".webp"]:
        suffix = ".jpg"

    filename = f"{uuid.uuid4()}{suffix}"
    output_path = IMAGE_DIR / filename

    image = Image.open(uploaded_file).convert("RGB")
    image.thumbnail((1600, 1600))
    image.save(output_path, quality=88)

    return str(output_path.relative_to(BASE_DIR))


def get_absolute_image_path(relative_path: str) -> Path:
    return BASE_DIR / relative_path


def save_project() -> Path:
    project_name = st.session_state.project.get("name", "Meu Feed")
    filename = f"{slugify(project_name)}.json"
    path = PROJECT_DIR / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(st.session_state.project, file, ensure_ascii=False, indent=2)

    st.session_state.last_saved_path = str(path.relative_to(BASE_DIR))
    return path


def load_project(path: Path) -> None:
    with path.open("r", encoding="utf-8") as file:
        st.session_state.project = json.load(file)

    st.session_state.selected_index = None
    st.session_state.last_saved_path = str(path.relative_to(BASE_DIR))


def move_post(index: int, direction: int) -> None:
    posts = st.session_state.project["posts"]
    new_index = index + direction

    if new_index < 0 or new_index >= len(posts):
        return

    posts[index], posts[new_index] = posts[new_index], posts[index]
    st.session_state.selected_index = new_index


def delete_post(index: int) -> None:
    posts = st.session_state.project["posts"]

    if 0 <= index < len(posts):
        posts.pop(index)

    st.session_state.selected_index = None


def create_feed_preview(posts: list[dict], empty_slots: int = 0, cell_size: int = 900) -> BytesIO:
    total_items = len(posts) + empty_slots
    total_items = max(total_items, 9)
    cols = 3
    rows = (total_items + cols - 1) // cols

    canvas = Image.new("RGB", (cols * cell_size, rows * cell_size), "white")
    draw = ImageDraw.Draw(canvas)

    for index in range(total_items):
        x = (index % cols) * cell_size
        y = (index // cols) * cell_size

        draw.rectangle([x, y, x + cell_size, y + cell_size], fill=(243, 244, 246))

        if index < len(posts):
            path = get_absolute_image_path(posts[index]["image_path"])

            if path.exists():
                img = Image.open(path).convert("RGB")
                img = ImageOps.fit(img, (cell_size, cell_size), method=Image.Resampling.LANCZOS)
                canvas.paste(img, (x, y))

        draw.rectangle([x, y, x + cell_size, y + cell_size], outline="white", width=8)

    output = BytesIO()
    canvas.save(output, format="PNG")
    output.seek(0)
    return output


def render_feed_grid(posts: list[dict], empty_slots: int) -> None:
    total_items = len(posts) + empty_slots
    total_items = max(total_items, 9)

    for start in range(0, total_items, 3):
        cols = st.columns(3, gap="small")

        for offset, col in enumerate(cols):
            index = start + offset

            with col:
                if index < len(posts):
                    post = posts[index]
                    path = get_absolute_image_path(post["image_path"])

                    with st.container(border=True):
                        if path.exists():
                            st.image(str(path), use_container_width=True)
                        else:
                            st.warning("Imagem não encontrada.")

                        st.caption(f"{index + 1:02d} · {STATUS_LABELS.get(post['status'], post['status'])}")

                        if post.get("planned_date"):
                            st.caption(f"📅 {post['planned_date']}")

                        button_cols = st.columns(3)

                        with button_cols[0]:
                            if st.button("⬅️", key=f"left_{post['id']}", help="Mover para a esquerda"):
                                move_post(index, -1)
                                st.rerun()

                        with button_cols[1]:
                            if st.button("✏️", key=f"edit_{post['id']}", help="Editar"):
                                st.session_state.selected_index = index
                                st.rerun()

                        with button_cols[2]:
                            if st.button("➡️", key=f"right_{post['id']}", help="Mover para a direita"):
                                move_post(index, 1)
                                st.rerun()

                else:
                    with st.container(border=True):
                        st.markdown(
                            """
                            <div style="
                                aspect-ratio: 1 / 1;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                background: #f3f4f6;
                                border-radius: 10px;
                                color: #9ca3af;
                                font-size: 42px;
                                font-weight: 700;">
                                +
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.caption("Espaço vazio")


def render_editor() -> None:
    selected_index = st.session_state.selected_index
    posts = st.session_state.project["posts"]

    if selected_index is None or selected_index >= len(posts):
        st.info("Clique no botão ✏️ de uma foto para editar legenda, data e status.")
        return

    post = posts[selected_index]
    st.subheader(f"Editar post {selected_index + 1}")

    path = get_absolute_image_path(post["image_path"])

    if path.exists():
        st.image(str(path), use_container_width=True)

    with st.form(key=f"edit_form_{post['id']}"):
        caption = st.text_area("Legenda interna", value=post.get("caption", ""), height=120)

        current_date_value = None
        if post.get("planned_date"):
            try:
                current_date_value = date.fromisoformat(post["planned_date"])
            except ValueError:
                current_date_value = None

        planned_date = st.date_input(
            "Data planejada",
            value=current_date_value,
            format="DD/MM/YYYY",
        )

        status = st.selectbox(
            "Status",
            list(STATUS_LABELS.keys()),
            index=list(STATUS_LABELS.keys()).index(post.get("status", "Rascunho")),
        )

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
        st.success("Post atualizado.")
        st.rerun()

    if delete_clicked:
        delete_post(selected_index)
        save_project()
        st.success("Post excluído.")
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Feed Planner",
        page_icon="📸",
        layout="wide",
    )

    init_state()

    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
        }
        [data-testid="stImage"] img {
            aspect-ratio: 1 / 1;
            object-fit: cover;
            border-radius: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("📸 Feed Planner")
    st.write("Pré-visualize seu feed em grade 3xN antes de postar no Instagram.")

    with st.sidebar:
        st.header("Projeto")

        project_name = st.text_input("Nome do projeto", value=st.session_state.project["name"])
        st.session_state.project["name"] = project_name

        saved_projects = sorted(PROJECT_DIR.glob("*.json"))

        if saved_projects:
            project_options = {path.stem: path for path in saved_projects}
            selected_project_name = st.selectbox("Projetos salvos", list(project_options.keys()))

            if st.button("Carregar projeto salvo", use_container_width=True):
                load_project(project_options[selected_project_name])
                st.success("Projeto carregado.")
                st.rerun()

        if st.button("Novo projeto", use_container_width=True):
            st.session_state.project = empty_project()
            st.session_state.selected_index = None
            st.session_state.last_saved_path = ""
            st.rerun()

        st.divider()

        st.header("Fotos")

        uploaded_files = st.file_uploader(
            "Adicionar fotos",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )

        if uploaded_files and st.button("Inserir fotos no feed", use_container_width=True):
            for uploaded_file in uploaded_files:
                image_path = save_uploaded_image(uploaded_file)
                st.session_state.project["posts"].append(new_post(image_path))

            save_project()
            st.success(f"{len(uploaded_files)} foto(s) adicionada(s).")
            st.rerun()

        empty_slots = st.number_input(
            "Espaços vazios para preview",
            min_value=0,
            max_value=60,
            value=max(9 - len(st.session_state.project["posts"]), 0),
            step=3,
        )

        st.divider()

        if st.button("Salvar projeto", use_container_width=True):
            path = save_project()
            st.success(f"Projeto salvo em: {path.relative_to(BASE_DIR)}")

        preview_png = create_feed_preview(st.session_state.project["posts"], int(empty_slots))

        st.download_button(
            "Baixar preview PNG",
            data=preview_png,
            file_name=f"{slugify(st.session_state.project['name'])}-preview.png",
            mime="image/png",
            use_container_width=True,
        )

        if st.session_state.last_saved_path:
            st.caption(f"Último arquivo salvo: {st.session_state.last_saved_path}")

    left, right = st.columns([2.2, 1], gap="large")

    with left:
        st.subheader("Prévia do feed")
        render_feed_grid(st.session_state.project["posts"], int(empty_slots))

    with right:
        render_editor()


if __name__ == "__main__":
    main()
