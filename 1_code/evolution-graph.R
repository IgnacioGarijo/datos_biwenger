source("1_code/main.R")

df<- read.csv(file.path(datos, "jornadas.csv"))

library(plotly)

# Crear mapeo entre equipos y colores
team_colors <- data.frame(
  name = c("Los vengadores", "Karlox F.C.", "Arregui", "Ricardo J", "Víctor Orta", "CD Cornisa Azul", "Julia"),
  color = c("#D32F2F", "#FFB300", "#1976D2", "#424242", "#D4A574", "#388E3C", "#E91E63"),
  stringsAsFactors = FALSE
)

df_sorted <- df |>
  arrange(jornada) |>
  mutate(jornada = as.numeric(jornada))

# Crear ranking dinámico por jornada
df_animation <- df_sorted |>
  group_by(jornada) |>
  mutate(rank = rank(-points, ties.method = "first")) |>
  ungroup()

# Unir con los colores
df_animation <- df_animation |>
  left_join(team_colors, by = "name")

# Crear gráfico con colores personalizados
fig <- df_animation |>
  plot_ly(
    x = ~points,
    y = ~rank,
    color = ~name,
    colors = setNames(team_colors$color, team_colors$name),
    type = "bar",
    orientation = "h",
    frame = ~jornada,
    showlegend = FALSE,
    text = ~name,
    textposition = "inside",
    textfont = list(size = 12, color = "white"),
    hovertemplate = "<b>%{text}</b><br>Puntos: %{x}<extra></extra>",
    marker = list(line = list(color = "white", width = 1))
  ) |>
  layout(
    title = "Carrera de Puntos por Jornada",
    xaxis = list(title = "Puntos Totales"),
    yaxis = list(title = "Ranking", autorange = "reversed"),
    showlegend = FALSE
  ) |>
  animation_opts(
    frame = 800,
    transition = 400,
    redraw = TRUE
  )

fig