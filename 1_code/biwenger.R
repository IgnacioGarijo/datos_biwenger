source("1_code/main.R")

jornada_ids <- 4484:4509
lista_dfs <- list()

for (x in jornada_ids) {
  
  x_name <- x - 4483
  
  url <- paste0("https://biwenger.as.com/api/v2/rounds/league/", x)
  
  headers <- add_headers(
    Authorization = paste("Bearer", token),
    Accept = "application/json",
    `User-Agent` = "Mozilla/5.0 (compatible; scraping-script/1.0)",
    `X-League` = x_league,
    `X-User` = x_user
  )
  
  response <- GET(url, headers)
  
  if (status_code(response) == 200) {
    
    data <- fromJSON(
      content(response, as = "text", encoding = "UTF-8"),
      flatten = TRUE
    )
    
    standings <- data$data$league$standings
    
    if (!is.null(standings)) {
      
      # Comprobar si 'lineup.points' existe
      if ("lineup.points" %in% names(standings)) {
        
        df <- standings %>%
          mutate(
            jornada = x_name,
            jornada_id = x,
            jornada_points = lineup.points
          ) %>%
          select(
            jornada, jornada_id, id, name, points,
            jornada_points, teamValue, position,
            lineup.type, lineup.players
          ) %>%
          unnest_wider(lineup.players, names_sep = "_")
        
      } else {
        
        df <- standings %>%
          mutate(
            jornada = x_name,
            jornada_id = x,
            jornada_points = NA_real_
          ) %>%
          select(
            jornada, jornada_id, id, name, points,
            jornada_points, teamValue, position,
            lineup.type, lineup.players
          ) %>%
          unnest_wider(lineup.players, names_sep = "_")
      }
      
      lista_dfs[[as.character(x)]] <- df
      cat("Jornada", x, "procesada correctamente.\n")
      
    } else {
      cat("No se encontraron standings en la jornada", x, "\n")
    }
    
  } else {
    cat("Error en la petición para jornada", x, ":", status_code(response), "\n")
    cat(content(response, as = "text"), "\n")
  }
}

df_final <- bind_rows(lista_dfs)

write.csv(df_final, file.path(datos,"jornadas.csv"), row.names = FALSE)
