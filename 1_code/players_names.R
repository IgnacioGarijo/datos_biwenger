source("1_code/main.R")

response <- GET(url_players)

if (status_code(response) == 200) {
  text <- content(response, as = "text", encoding = "UTF-8")
  
  # Eliminar el callback para extraer JSON puro
  json_text <- str_remove(text, "^jsonp_\\d+\\(")
  json_text <- str_remove(json_text, "\\);?$")
  
  data <- fromJSON(json_text, flatten = TRUE)
  
  # data$data$players es una lista nombrada con IDs como nombres
  players_list <- data$data$players
  
  # Convertir la lista en dataframe
  # Cada elemento es una lista con atributos del jugador
  players_df <- bind_rows(lapply(players_list, function(player) {
    tibble(
      id = player$id,
      name = player$name,
      teamID = player$teamID,
      position = player$position,
      points = player$points,
      pointsHome = player$pointsHome,
      pointsAway = player$pointsAway,
      price = player$price,
      fantasyPrice = player$fantasyPrice
    )
  }))
  
  
} else {
  cat("Error en la petición:", status_code(response), "\n")
}

write.csv(players_df, file.path(datos, "players.csv"))
