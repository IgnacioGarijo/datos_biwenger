library(httr)
library(jsonlite)
library(tidyverse)
library(stringr)

wd<- "C:/Users/ignac/OneDrive/Documentos/GitHub/datos_biwenger/"

setwd(wd)

datos<- file.path(wd, "0_data")
codigo<- file.path(wd, "1_code")
output<- file.path(wd, "2_output")

token <- "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOjI2MDU5NjQ3LCJpYXQiOjE3NzIzMjAyNjl9.q22yHy36FPevqadAEsSBxztgbjSte3lSD_uBV2cqYNo"
x_league <- "1131687"
x_user <- "6826480"

url_players <- "https://cf.biwenger.com/api/v2/competitions/la-liga/data?lang=es&score=1&callback=jsonp_1465365482"
