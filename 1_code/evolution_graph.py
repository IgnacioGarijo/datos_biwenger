import plotly.graph_objects as go
import pandas as pd
import os
import base64

datos = "0_data"
img_path = os.path.join(datos, "img")

# Cargar el CSV
df = pd.read_csv(os.path.join(datos, "jornadas.csv"))

# Mapeo entre equipos e imágenes
team_image_map = {
    "Los vengadores": "vengadores.png",
    "Karlox F.C.": "karlox.png",
    "Arregui": "arregui.png",
    "Ricardo J": "ricardo.svg",
    "Víctor Orta": "ignacio.webp",
    "CD Cornisa Azul": "alfonso.avif",
    "Julia": "julia.jpg"
}

# Función para convertir imagen a base64
def image_to_base64(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

# Función para obtener tipo MIME
def get_mime_type(filename):
    ext = filename.split(".")[-1].lower()
    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "webp": "image/webp",
        "avif": "image/avif",
        "svg": "image/svg+xml"
    }
    return mime_types.get(ext, "image/png")

# Preparar datos
df_sorted = df.sort_values("jornada").copy()
df_sorted["jornada"] = df_sorted["jornada"].astype(int)
df_animation = df_sorted.copy()

# Agregar imágenes en base64
df_animation["image_file"] = df_animation["name"].map(team_image_map)
df_animation["image_path"] = df_animation["image_file"].apply(
    lambda x: os.path.join(img_path, x) if x else None
)
df_animation["image_base64"] = df_animation["image_path"].apply(image_to_base64)
df_animation["mime_type"] = df_animation["image_file"].apply(get_mime_type)

# Crear figuras para cada frame
frames = []
jornadas = sorted(df_animation["jornada"].unique())

for jornada in jornadas:
    data_jornada = df_animation[df_animation["jornada"] == jornada].copy()
    data_jornada = data_jornada.sort_values("points", ascending=True)
    
    # Calcular máximo de puntos para esta jornada
    max_points = data_jornada["points"].max()
    
    # Crear data URI para las imágenes
    customdata = []
    for _, row in data_jornada.iterrows():
        if row["image_base64"]:
            img_html = f"<img src='data:{row['mime_type']};base64,{row['image_base64']}' style='height:40px;margin-right:10px;'>"
        else:
            img_html = ""
        customdata.append(img_html)
    
    frame = go.Frame(
        data=[go.Bar(
            y=data_jornada["name"],
            x=data_jornada["points"],
            orientation="h",
            marker=dict(color="black"),
            text=data_jornada["points"],
            textposition="outside",
            textfont=dict(color="black", size=11),
            customdata=customdata,
            hovertemplate="<b>%{y}</b><br>Puntos: %{x}<br>%{customdata}<extra></extra>",
            showlegend=False
        )],
        name=str(jornada),
        layout=go.Layout(
            xaxis=dict(range=[0, max_points * 1.2])
        )
    )
    frames.append(frame)

# Datos iniciales
data_inicial = df_animation[df_animation["jornada"] == jornadas[0]].copy()
data_inicial = data_inicial.sort_values("points", ascending=True)

customdata_inicial = []
for _, row in data_inicial.iterrows():
    if row["image_base64"]:
        img_html = f"<img src='data:{row['mime_type']};base64,{row['image_base64']}' style='height:40px;margin-right:10px;'>"
    else:
        img_html = ""
    customdata_inicial.append(img_html)

max_points_inicial = data_inicial["points"].max()

# Crear figura
fig = go.Figure(
    data=[go.Bar(
        y=data_inicial["name"],
        x=data_inicial["points"],
        orientation="h",
        marker=dict(color="black"),
        text=data_inicial["points"],
        textposition="outside",
        textfont=dict(color="black", size=11),
        customdata=customdata_inicial,
        hovertemplate="<b>%{y}</b><br>Puntos: %{x}<br>%{customdata}<extra></extra>",
        showlegend=False
    )],
    frames=frames
)

# Agregar animación
fig.update_layout(
    title="Carrera de Puntos por Jornada",
    xaxis=dict(
        title="Puntos Totales",
        range=[0, max_points_inicial * 1.2]
    ),
    yaxis=dict(title="Equipo"),
    showlegend=False,
    height=600,
    width=1200,
    updatemenus=[dict(
        type="buttons",
        showactive=False,
        buttons=[
            dict(label="▶ Play", method="animate", args=[None, {
                "frame": {"duration": 500, "redraw": True},
                "fromcurrent": True,
                "transition": {"duration": 300}
            }]),
            dict(label="⏸ Pause", method="animate", args=[[None], {
                "frame": {"duration": 0, "redraw": True},
                "mode": "immediate",
                "transition": {"duration": 0}
            }])
        ]
    )],
    sliders=[dict(
        active=0,
        steps=[dict(args=[[f.name], {
            "frame": {"duration": 0, "redraw": True},
            "mode": "immediate",
            "transition": {"duration": 0}
        }], label=f"Jornada {f.name}") for f in frames]
    )]
)

fig.show()