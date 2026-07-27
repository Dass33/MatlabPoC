from streamlit_dnd import apply_move, dnd

import streamlit as st


@st.dialog("Edit item")
def edit_item(item: str):
    st.text_input("Name", value=item, key=f"name_{item}")
    st.selectbox("Group", ["A", "B"], key=f"grp_{item}")
    st.checkbox("Visible", True)
    if st.button("Save", type="primary"):
        # mutate st.session_state.config_layout here
        st.rerun()


def page_preset_editor():
    st.header("Preset editor")
    st.selectbox(label="Select preset to edit", options=["Hi", "no"])
    LAYOUT = "layout"
    if "config_layout" not in st.session_state:
        st.session_state.config_layout = {LAYOUT: ["Ax", "By", "Cz"]}

    with st.container(key=LAYOUT, border=True):
        for it in st.session_state.config_layout[LAYOUT]:
            with st.container(key=it):
                name, group, edit = st.columns(
                    [0.52, 0.3, 0.18], vertical_alignment="center"
                )
                visible = it != "Ax"
                with name:
                    if visible:
                        st.write(f"**{it}**")
                    else:
                        st.write(f":gray[:material/visibility_off: {it}]")
                with group:
                    st.text("Group todo")
                with edit:
                    if st.button(label="Edit", key=f"btn_{it}"):
                        edit_item(it)

    event = dnd(LAYOUT, indicator="ghost", handle=True)

    if event:
        apply_move(event, st.session_state.config_layout)
        st.rerun()

    st.button(label="Publish", type="primary")
